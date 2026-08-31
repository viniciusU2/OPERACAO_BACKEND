"""Conversão dos DataFrames normalizados em linhas de fatos."""

from __future__ import annotations

import pandas as pd

from ..database.models import DimConfiguracao, FatoAlarme, FatoContador, FatoEstado, FatoMedicao, FatoTimestamp
from ..database.repository import insert_many_ignore


def load_configuration(connection, frame: pd.DataFrame, equipment_id: int, import_id: int | None = None) -> int:
    rows = []
    for row in frame.itertuples(index=False):
        rows.append({
            "id_equipamento": equipment_id,
            "parametro": row.parametro,
            "categoria": row.categoria,
            "valor_original": row.valor_original,
            "valor_numerico": row.valor_numerico,
            "unidade": row.unidade,
            "source_file": row.source_file,
        })
    return insert_many_ignore(connection, DimConfiguracao.__table__, rows)


def load_measurements(connection, frame: pd.DataFrame, event_id: int, equipment_id: int, grandezas: dict, canais: dict) -> int:
    rows = []
    for row in frame.itertuples(index=False):
        unit = row.unidade or ""
        rows.append({"id_evento": event_id, "id_equipamento": equipment_id, "id_grandeza": grandezas[(row.codigo_grandeza, unit)], "id_canal": canais.get(row.indice_canal), "valor": row.valor_numerico, "source_parameter": row.parametro})
    return insert_many_ignore(connection, FatoMedicao.__table__, rows)


def load_alarms(connection, frame: pd.DataFrame, event_id: int, equipment_id: int, alarm_types: dict, canais: dict) -> int:
    rows = []
    for row in frame.itertuples(index=False):
        rows.append({"id_evento": event_id, "id_equipamento": equipment_id, "id_tipo_alarme": alarm_types[row.codigo_alarme], "id_canal": canais.get(row.indice_canal), "estado_alarme": row.valor_booleano, "timestamp_on": row.timestamp_on, "timestamp_off": row.timestamp_off, "duracao_segundos": row.duracao_segundos, "source_parameter": row.parametro})
    return insert_many_ignore(connection, FatoAlarme.__table__, rows)


def load_states(connection, frame: pd.DataFrame, event_id: int, equipment_id: int, canais: dict) -> int:
    rows = [{"id_evento": event_id, "id_equipamento": equipment_id, "id_canal": canais.get(row.indice_canal), "codigo_estado": row.parametro, "valor_estado": row.valor_original} for row in frame.itertuples(index=False)]
    return insert_many_ignore(connection, FatoEstado.__table__, rows)


def load_counters(connection, frame: pd.DataFrame, event_id: int, equipment_id: int, grandezas: dict, canais: dict) -> int:
    rows = [{"id_evento": event_id, "id_equipamento": equipment_id, "id_grandeza": grandezas[(row.codigo_grandeza, row.unidade or "")], "id_canal": canais.get(row.indice_canal), "valor": row.valor_numerico} for row in frame.itertuples(index=False)]
    return insert_many_ignore(connection, FatoContador.__table__, rows)


def load_timestamps(connection, frame: pd.DataFrame, event_id: int, equipment_id: int, canais: dict) -> int:
    rows = [{"id_evento": event_id, "id_equipamento": equipment_id, "id_canal": canais.get(row.indice_canal), "tipo_timestamp": row.tipo_timestamp, "timestamp_valor": row.valor_datetime, "source_parameter": row.parametro} for row in frame.itertuples(index=False)]
    return insert_many_ignore(connection, FatoTimestamp.__table__, rows)

