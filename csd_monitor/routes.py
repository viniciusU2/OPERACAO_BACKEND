from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import text

from auth.dependencies import get_current_user, require_roles
from database import engine
from csd_monitor.loaders.etl_loader import processar_importacao


router = APIRouter(prefix="/csd-monitor", tags=["CSD Monitor"])


def _rows(sql: str, params: dict | None = None) -> list[dict]:
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(text(sql), params or {}).mappings().all()]


def _one(sql: str, params: dict | None = None) -> dict:
    rows = _rows(sql, params)
    return rows[0] if rows else {}


@router.post("/importar")
async def importar_csd(
    param_file: UploadFile = File(...),
    measures_file: UploadFile = File(...),
    _usuario=Depends(require_roles("admin", "mantenedor")),
):
    for arquivo, esperado in ((param_file, "param"), (measures_file, "measures")):
        if not (arquivo.filename or "").lower().endswith(".xml"):
            raise HTTPException(400, f"O arquivo {esperado} deve estar no formato XML.")

    param_bytes = await param_file.read()
    measures_bytes = await measures_file.read()
    if not param_bytes or not measures_bytes:
        raise HTTPException(400, "Os dois arquivos XML precisam conter dados.")

    with tempfile.TemporaryDirectory(prefix="csd_monitor_") as temporary:
        param_path = Path(temporary) / "param.xml"
        measures_path = Path(temporary) / "measures.xml"
        param_path.write_bytes(param_bytes)
        measures_path.write_bytes(measures_bytes)
        try:
            return processar_importacao(param_path, measures_path, engine=engine).as_dict()
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(500, f"Falha na importação; a transação foi revertida: {exc}") from exc


@router.get("/dashboard")
def dashboard_csd(_usuario=Depends(get_current_user)):
    resumo = _one("""
        SELECT
            (SELECT COUNT(*) FROM dim_equipamento) AS equipamentos,
            (SELECT COUNT(*) FROM fato_evento) AS eventos,
            (SELECT COUNT(*) FROM fato_medicao) AS medicoes,
            (SELECT COUNT(*) FROM fato_alarme) AS alarmes,
            (SELECT COUNT(*) FROM fato_alarme WHERE estado_alarme = 1) AS alarmes_ativos,
            (SELECT MAX(data_fim) FROM etl_importacao WHERE status = 'SUCESSO') AS ultima_importacao
    """)
    equipamentos = _rows("""
        SELECT eq.id_equipamento, eq.substation, eq.bay_number, eq.csd_serial_number,
               eq.cb_model, eq.voltage_level_kv, eq.frequency_hz,
               MAX(e.archive_creation_date_utc) AS ultimo_evento,
               COALESCE(SUM(CASE WHEN g.codigo = 'counter_opening_controlled' THEN fc.valor ELSE 0 END), 0) AS abertura_controlada,
               COALESCE(SUM(CASE WHEN g.codigo = 'counter_opening_uncontrolled' THEN fc.valor ELSE 0 END), 0) AS abertura_nao_controlada
        FROM dim_equipamento eq
        LEFT JOIN fato_evento e ON e.id_equipamento = eq.id_equipamento
        LEFT JOIN fato_contador fc ON fc.id_evento = e.id_evento
        LEFT JOIN dim_grandeza g ON g.id_grandeza = fc.id_grandeza
        GROUP BY eq.id_equipamento, eq.substation, eq.bay_number, eq.csd_serial_number,
                 eq.cb_model, eq.voltage_level_kv, eq.frequency_hz
        ORDER BY eq.substation, eq.bay_number
    """)
    contadores = _rows("""
        SELECT eq.id_equipamento, eq.substation, eq.bay_number,
               CASE WHEN g.codigo LIKE 'counter_closing_%' THEN 'Close' ELSE 'Open' END AS operacao,
               COALESCE(c.fase, 'Geral') AS fase,
               CASE
                   WHEN g.codigo IN ('counter_closing_controlled', 'counter_opening_controlled') THEN 'Operações controladas'
                   WHEN g.codigo IN ('counter_closing_uncontrolled', 'counter_opening_uncontrolled') THEN 'Operações não controladas'
                   WHEN g.codigo = 'counter_reignition' THEN 'Reignição controlada'
                   WHEN g.codigo = 'counter_reignition_wo_csd' THEN 'Reignição não controlada'
                   ELSE g.codigo
               END AS contador,
               MAX(fc.valor) AS valor
        FROM fato_contador fc
        JOIN fato_evento e ON e.id_evento = fc.id_evento
        JOIN dim_equipamento eq ON eq.id_equipamento = e.id_equipamento
        JOIN dim_grandeza g ON g.id_grandeza = fc.id_grandeza
        LEFT JOIN dim_canal c ON c.id_canal = fc.id_canal
        WHERE g.codigo LIKE 'counter_%'
        GROUP BY eq.id_equipamento, eq.substation, eq.bay_number, operacao, fase, contador
        ORDER BY eq.bay_number, operacao, fase, contador
    """)
    alarmes = _rows("""
        SELECT a.id_alarme, eq.substation, eq.bay_number, ta.codigo AS alarme,
               COALESCE(c.fase, 'Geral') AS fase, a.estado_alarme,
               a.timestamp_on, a.timestamp_off, a.duracao_segundos,
               e.archive_creation_date_utc AS data_evento
        FROM fato_alarme a
        JOIN fato_evento e ON e.id_evento = a.id_evento
        JOIN dim_equipamento eq ON eq.id_equipamento = a.id_equipamento
        JOIN dim_tipo_alarme ta ON ta.id_tipo_alarme = a.id_tipo_alarme
        LEFT JOIN dim_canal c ON c.id_canal = a.id_canal
        ORDER BY COALESCE(a.timestamp_on, e.archive_creation_date_utc) DESC, a.id_alarme DESC
        LIMIT 200
    """)
    eventos = _rows("""
        SELECT e.id_evento, e.nome_arquivo, e.archive_type,
               e.archive_creation_date_utc, e.switching_program,
               eq.substation, eq.bay_number, eq.csd_serial_number,
               e.data_importacao
        FROM fato_evento e
        JOIN dim_equipamento eq ON eq.id_equipamento = e.id_equipamento
        ORDER BY COALESCE(e.archive_creation_date_utc, e.data_importacao) DESC, e.id_evento DESC
        LIMIT 100
    """)
    medidas = _rows("""
        SELECT e.id_evento, e.archive_creation_date_utc AS data_evento,
               e.archive_type, eq.substation, eq.bay_number, c.fase,
               g.codigo AS grandeza, g.categoria, g.unidade, m.valor,
               m.source_parameter
        FROM fato_medicao m
        JOIN fato_evento e ON e.id_evento = m.id_evento
        JOIN dim_equipamento eq ON eq.id_equipamento = m.id_equipamento
        JOIN dim_grandeza g ON g.id_grandeza = m.id_grandeza
        LEFT JOIN dim_canal c ON c.id_canal = m.id_canal
        ORDER BY e.archive_creation_date_utc DESC, m.id_medicao DESC
        LIMIT 1000
    """)
    timeline = _rows("""
        SELECT DATE(e.archive_creation_date_utc) AS data_evento,
               COUNT(*) AS eventos,
               COUNT(DISTINCT e.id_equipamento) AS equipamentos
        FROM fato_evento e
        GROUP BY DATE(e.archive_creation_date_utc)
        ORDER BY data_evento DESC
        LIMIT 30
    """)
    importacoes = _rows("""
        SELECT id_importacao, nome_arquivo, data_inicio, data_fim, status,
               linhas_xml, medicoes_inseridas, alarmes_inseridos,
               estados_inseridos, contadores_inseridos, timestamps_inseridos,
               mensagem_erro
        FROM etl_importacao
        ORDER BY id_importacao DESC
        LIMIT 30
    """)
    return {"resumo": resumo, "equipamentos": equipamentos, "contadores": contadores, "alarmes": alarmes, "eventos": eventos, "medidas": medidas, "timeline": timeline, "importacoes": importacoes}


@router.get("/importacoes")
def listar_importacoes(limite: int = Query(50, ge=1, le=500), _usuario=Depends(get_current_user)):
    return _rows("""
        SELECT id_importacao, nome_arquivo, data_inicio, data_fim, status,
               linhas_xml, medicoes_inseridas, alarmes_inseridos,
               estados_inseridos, contadores_inseridos, timestamps_inseridos,
               mensagem_erro
        FROM etl_importacao ORDER BY id_importacao DESC LIMIT :limite
    """, {"limite": limite})


@router.get("/historico-operacoes")
def historico_operacoes(_usuario=Depends(get_current_user)):
    return _rows("""
        SELECT eq.id_equipamento, eq.substation, eq.bay_number,
               DATE(COALESCE(e.archive_creation_date_utc, e.data_importacao)) AS data_operacao,
               CASE
                   WHEN g.codigo IN ('counter_opening_controlled', 'counter_closing_controlled') THEN 'Operações controladas'
                   WHEN g.codigo IN ('counter_opening_uncontrolled', 'counter_closing_uncontrolled') THEN 'Operações não controladas'
                   WHEN g.codigo = 'counter_reignition' THEN 'Reignição controlada'
                   WHEN g.codigo = 'counter_reignition_wo_csd' THEN 'Reignição não controlada'
                   ELSE NULL
               END AS categoria,
               MAX(fc.valor) AS valor
        FROM fato_contador fc
        JOIN fato_evento e ON e.id_evento = fc.id_evento
        JOIN dim_equipamento eq ON eq.id_equipamento = e.id_equipamento
        JOIN dim_grandeza g ON g.id_grandeza = fc.id_grandeza
        WHERE g.codigo IN ('counter_opening_controlled', 'counter_closing_controlled', 'counter_opening_uncontrolled', 'counter_closing_uncontrolled', 'counter_reignition', 'counter_reignition_wo_csd')
        GROUP BY eq.id_equipamento, eq.substation, eq.bay_number,
                 DATE(COALESCE(e.archive_creation_date_utc, e.data_importacao)), categoria
        ORDER BY eq.substation, eq.bay_number, data_operacao
    """)


@router.delete("/importacoes/{importacao_id}")
def excluir_importacao(importacao_id: int, _usuario=Depends(require_roles("admin", "mantenedor"))):
    """Exclui a auditoria e os fatos do evento, preservando dimensões compartilhadas."""
    with engine.begin() as connection:
        imported = connection.execute(text("""
            SELECT id_importacao, hash_arquivo
            FROM etl_importacao
            WHERE id_importacao = :importacao_id
            FOR UPDATE
        """), {"importacao_id": importacao_id}).mappings().first()
        if not imported:
            raise HTTPException(404, "Importação não encontrada.")

        digest = imported["hash_arquivo"]
        if digest:
            other_imports = connection.execute(text("""
                SELECT COUNT(*) FROM etl_importacao
                WHERE hash_arquivo = :hash_arquivo AND id_importacao <> :importacao_id
            """), {"hash_arquivo": digest, "importacao_id": importacao_id}).scalar_one()
            if not other_imports:
                for table in ("fato_medicao", "fato_alarme", "fato_estado", "fato_contador", "fato_timestamp"):
                    connection.execute(text(f"""
                        DELETE child FROM {table} child
                        INNER JOIN fato_evento AS fe ON fe.id_evento = child.id_evento
                        WHERE fe.hash_arquivo = :hash_arquivo
                    """), {"hash_arquivo": digest})
                connection.execute(text("DELETE FROM fato_evento WHERE hash_arquivo = :hash_arquivo"), {"hash_arquivo": digest})

        connection.execute(text("DELETE FROM etl_parametro_nao_classificado WHERE id_importacao = :importacao_id"), {"importacao_id": importacao_id})
        connection.execute(text("DELETE FROM etl_importacao WHERE id_importacao = :importacao_id"), {"importacao_id": importacao_id})

    return {"message": "Importação excluída.", "id_importacao": importacao_id}





