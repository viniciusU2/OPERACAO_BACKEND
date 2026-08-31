"""Orquestração transacional e idempotente da importação."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import insert, select, update

from ..database.connection import get_engine
from ..database.models import EtlImportacao, EtlParametroNaoClassificado, FatoEvento
from ..database.repository import _db_value, get_or_create_equipamento
from ..parsers.measures_parser import measures_metadata, parse_measures
from ..parsers.param_parser import parse_param
from ..transformations.classification import equipment_dimension
from ..transformations.dimensional_model import build_dimensional_model
from .dimension_loader import load_alarm_types, load_channels, load_grandezas
from .fact_loader import load_alarms, load_configuration, load_counters, load_measurements, load_states, load_timestamps


@dataclass
class ImportResult:
    status: str
    message: str
    nome_arquivo: str
    hash_arquivo: str
    id_importacao: int | None = None
    id_evento: int | None = None
    equipamento: str | None = None
    medicoes_inseridas: int = 0
    alarmes_inseridos: int = 0
    estados_inseridos: int = 0
    contadores_inseridos: int = 0
    timestamps_inseridos: int = 0
    parametros_nao_classificados: int = 0
    tempo_segundos: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> datetime:
    return datetime.now()


def _insert_audit(engine, filename: str, digest: str, rows: int) -> int:
    with engine.begin() as connection:
        result = connection.execute(insert(EtlImportacao).values(nome_arquivo=filename, hash_arquivo=digest, data_inicio=_now(), status="PROCESSANDO", linhas_xml=rows))
        return int(result.inserted_primary_key[0])


def _finish_audit(engine, import_id: int, result: ImportResult, error: str | None = None) -> None:
    values = {"data_fim": _now(), "status": "ERRO" if error else result.status, "medicoes_inseridas": result.medicoes_inseridas, "alarmes_inseridos": result.alarmes_inseridos, "estados_inseridos": result.estados_inseridos, "contadores_inseridos": result.contadores_inseridos, "timestamps_inseridos": result.timestamps_inseridos, "mensagem_erro": error or result.message}
    with engine.begin() as connection:
        connection.execute(update(EtlImportacao).where(EtlImportacao.id_importacao == import_id).values(**values))


def _metadata_value(frame, name: str):
    rows = frame.loc[frame["parametro"].eq(name), "valor_datetime"].dropna()
    return rows.iloc[0] if not rows.empty else None


def _string_value(frame, names: tuple[str, ...]):
    for name in names:
        rows = frame.loc[frame["parametro"].eq(name), "valor_original"].dropna()
        if not rows.empty:
            return rows.iloc[0]
    return None


def processar_importacao(param_file: str | Path, measures_file: str | Path, engine=None) -> ImportResult:
    """Importa um par param/measures de forma atômica e idempotente."""
    started = datetime.now()
    measures_file = Path(measures_file)
    param_file = Path(param_file)
    if not param_file.exists() or not measures_file.exists():
        raise FileNotFoundError("param.xml e measures.xml precisam existir")
    engine = engine or get_engine()
    measures = parse_measures(measures_file)
    param = parse_param(param_file)
    metadata = measures_metadata(measures_file, measures)
    digest = metadata["hash_arquivo"]
    result = ImportResult(status="PROCESSANDO", message="", nome_arquivo=measures_file.name, hash_arquivo=digest)
    result.id_importacao = _insert_audit(engine, measures_file.name, digest, len(measures) + len(param))

    try:
        with engine.begin() as connection:
            existing_event = connection.execute(select(FatoEvento.id_evento).where(FatoEvento.hash_arquivo == digest)).scalar_one_or_none()
            if existing_event is not None:
                result.status = "SUCESSO"
                result.message = "Arquivo já processado."
                result.id_evento = int(existing_event)
                result.equipamento = _string_value(measures, ("information_substation", "information_bay_number"))
                connection.execute(update(EtlImportacao).where(EtlImportacao.id_importacao == result.id_importacao).values(data_fim=_now(), status="SUCESSO", mensagem_erro=result.message, medicoes_inseridas=0, alarmes_inseridos=0, estados_inseridos=0, contadores_inseridos=0, timestamps_inseridos=0))
                result.tempo_segundos = (datetime.now() - started).total_seconds()
                return result

            model = build_dimensional_model(param, measures)
            equipment = equipment_dimension(param, measures)
            equipment_id = get_or_create_equipamento(connection, equipment)
            result.equipamento = equipment.get("substation") or equipment.get("bay_number")
            channel_map = load_channels(connection, model["canais"])
            grandeza_map = load_grandezas(connection, [model["medicoes"], model["contadores"]])
            alarm_map = load_alarm_types(connection, model["alarmes"])
            event_values = {"id_equipamento": equipment_id, "nome_arquivo": measures_file.name, "hash_arquivo": digest, "archive_type": metadata.get("archive_type"), "archive_creation_date_utc": metadata.get("archive_creation_date_utc"), "archive_creation_date_local": metadata.get("archive_creation_date_local"), "switching_program": metadata.get("switching_program"), "phase_ref_open": metadata.get("phase_ref_open"), "phase_ref_close": metadata.get("phase_ref_close"), "timestamp_open_order": _metadata_value(measures, "timestamp_open_order"), "timestamp_close_order": _metadata_value(measures, "timestamp_close_order")}
            event_result = connection.execute(insert(FatoEvento).values(**event_values))
            event_id = int(event_result.inserted_primary_key[0])
            result.id_evento = event_id
            result.medicoes_inseridas = load_measurements(connection, model["medicoes"], event_id, equipment_id, grandeza_map, channel_map)
            result.alarmes_inseridos = load_alarms(connection, model["alarmes"], event_id, equipment_id, alarm_map, channel_map)
            result.estados_inseridos = load_states(connection, model["estados"], event_id, equipment_id, channel_map)
            result.contadores_inseridos = load_counters(connection, model["contadores"], event_id, equipment_id, grandeza_map, channel_map)
            result.timestamps_inseridos = load_timestamps(connection, model["timestamps"], event_id, equipment_id, channel_map)
            load_configuration(connection, model["configuracao"], equipment_id)
            unknown = model["configuracao"].loc[model["configuracao"]["nao_classificado"]].copy()
            result.parametros_nao_classificados = len(unknown)
            if not unknown.empty:
                rows = [{"id_importacao": result.id_importacao, "parametro": row.parametro, "valor_original": _db_value(row.valor_original), "unidade": _db_value(row.unidade)} for row in unknown.itertuples(index=False)]
                connection.execute(insert(EtlParametroNaoClassificado), rows)
            result.status = "SUCESSO"
            result.message = "Importação concluída."
            connection.execute(update(EtlImportacao).where(EtlImportacao.id_importacao == result.id_importacao).values(data_fim=_now(), status="SUCESSO", medicoes_inseridas=result.medicoes_inseridas, alarmes_inseridos=result.alarmes_inseridos, estados_inseridos=result.estados_inseridos, contadores_inseridos=result.contadores_inseridos, timestamps_inseridos=result.timestamps_inseridos, mensagem_erro=result.message))
    except Exception as exc:
        _finish_audit(engine, result.id_importacao, result, str(exc))
        raise
    result.tempo_segundos = (datetime.now() - started).total_seconds()
    return result
