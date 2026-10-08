from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from models.OS_models import OrdemServico


router = APIRouter(prefix="/os-validacao", tags=["Validação de OS antigas"])

SEED_PATH = (
    Path(__file__).resolve().parent.parent
    / "dados"
    / "os_validacao_importacao_20261002.json"
)

OS_FIELDS = (
    "numero_os", "numero_si", "numero_ss", "id_subestacao", "id_ativo",
    "id_grupo_ativo", "id_funcao_operacao", "escopo_ativo",
    "id_plano_manutencao", "id_plano_item", "id_plano_execucao",
    "id_frente_servico", "origem", "especie", "numero_apr", "instalacao",
    "localizacao", "complemento", "origens", "defeito", "esquema_servicos",
    "prioridade", "responsavel", "responsavel_manutencao",
    "responsavel_operacao", "substituto", "data_inicio_programado",
    "data_fim_programado", "descricao_servicos", "observacoes",
    "causa_primaria", "causa_secundaria", "emissor", "editado_por",
    "data_abertura_ss", "data_inicio_execucao", "data_fim_execucao",
    "centro_custos", "status", "criado_em",
)

INTEGER_FIELDS = {
    "id_subestacao", "id_ativo", "id_grupo_ativo", "id_funcao_operacao",
    "id_plano_manutencao", "id_plano_item", "id_plano_execucao",
    "id_frente_servico",
}
DATETIME_FIELDS = {
    "data_inicio_programado", "data_fim_programado", "data_abertura_ss",
    "data_inicio_execucao", "data_fim_execucao", "criado_em",
}
STATUS_VALIDACAO = {
    "PENDENTE", "EM_REVISAO", "CONFIRMADA", "REJEITADA", "ENVIADA", "ERRO",
}


class ValidacaoOsUpdate(BaseModel):
    dados_os: dict[str, Any]
    observacao_validacao: Optional[str] = None
    validado_por: Optional[str] = None


class ValidacaoOsAcao(BaseModel):
    observacao_validacao: Optional[str] = None
    validado_por: Optional[str] = None


def garantir_estrutura_validacao(db: Session) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS os_validacao_importacao (
            id_validacao INT NOT NULL AUTO_INCREMENT,
            chave_origem VARCHAR(190) NOT NULL,
            tipo_registro VARCHAR(30) NOT NULL,
            fonte VARCHAR(80) NULL,
            linha_controle INT NULL,
            numero_os VARCHAR(30) NOT NULL,
            id_os_destino INT NULL,
            bloqueios LONGTEXT NOT NULL,
            avisos LONGTEXT NOT NULL,
            contexto LONGTEXT NOT NULL,
            dados_os LONGTEXT NOT NULL,
            status_validacao VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
            observacao_validacao TEXT NULL,
            validado_por VARCHAR(120) NULL,
            erro_envio TEXT NULL,
            criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            validado_em DATETIME NULL,
            enviado_em DATETIME NULL,
            PRIMARY KEY (id_validacao),
            UNIQUE KEY uq_os_validacao_chave_origem (chave_origem),
            KEY idx_os_validacao_status (status_validacao),
            KEY idx_os_validacao_numero (numero_os),
            KEY idx_os_validacao_tipo (tipo_registro),
            KEY idx_os_validacao_destino (id_os_destino)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
    """))
    db.commit()


def semear_validacoes(db: Session) -> None:
    total = db.execute(text("SELECT COUNT(*) FROM os_validacao_importacao")).scalar() or 0
    if total or not SEED_PATH.exists():
        return

    registros = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    sql = text("""
        INSERT IGNORE INTO os_validacao_importacao (
            chave_origem, tipo_registro, fonte, linha_controle, numero_os,
            id_os_destino, bloqueios, avisos, contexto, dados_os
        ) VALUES (
            :chave_origem, :tipo_registro, :fonte, :linha_controle, :numero_os,
            :id_os_destino, :bloqueios, :avisos, :contexto, :dados_os
        )
    """)
    for registro in registros:
        db.execute(sql, {
            "chave_origem": registro["chave_origem"],
            "tipo_registro": registro["tipo_registro"],
            "fonte": registro.get("fonte"),
            "linha_controle": registro.get("linha_controle"),
            "numero_os": registro["numero_os"],
            "id_os_destino": registro.get("id_os_destino"),
            "bloqueios": json.dumps(registro.get("bloqueios") or [], ensure_ascii=False),
            "avisos": json.dumps(registro.get("avisos") or [], ensure_ascii=False),
            "contexto": json.dumps(registro.get("contexto") or {}, ensure_ascii=False),
            "dados_os": json.dumps(registro.get("dados_os") or {}, ensure_ascii=False),
        })
    db.commit()


def preparar_validacao(db: Session) -> None:
    garantir_estrutura_validacao(db)
    semear_validacoes(db)


def carregar_json(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def serializar_linha(row: Any, incluir_dados: bool = True) -> dict[str, Any]:
    item = dict(row)
    item["bloqueios"] = carregar_json(item.get("bloqueios"), [])
    item["avisos"] = carregar_json(item.get("avisos"), [])
    item["contexto"] = carregar_json(item.get("contexto"), {})
    dados = carregar_json(item.get("dados_os"), {})
    if incluir_dados:
        item["dados_os"] = dados
    else:
        item.pop("dados_os", None)
        item["resumo_os"] = {
            "instalacao": dados.get("instalacao"),
            "id_subestacao": dados.get("id_subestacao"),
            "id_ativo": dados.get("id_ativo"),
            "id_grupo_ativo": dados.get("id_grupo_ativo"),
            "id_plano_manutencao": dados.get("id_plano_manutencao"),
            "emissor": dados.get("emissor"),
            "descricao_servicos": dados.get("descricao_servicos"),
            "data_inicio_programado": dados.get("data_inicio_programado"),
            "status": dados.get("status"),
        }
    for campo in ("criado_em", "atualizado_em", "validado_em", "enviado_em"):
        if isinstance(item.get(campo), datetime):
            item[campo] = item[campo].isoformat()
    return item


def buscar_validacao(db: Session, id_validacao: int):
    row = db.execute(text("""
        SELECT * FROM os_validacao_importacao WHERE id_validacao = :id_validacao
    """), {"id_validacao": id_validacao}).mappings().first()
    if not row:
        raise HTTPException(404, "Registro de validação não encontrado")
    return row


def limpar_dados_os(dados: dict[str, Any]) -> dict[str, Any]:
    desconhecidos = sorted(set(dados) - set(OS_FIELDS))
    if desconhecidos:
        raise HTTPException(400, f"Campos de OS não reconhecidos: {', '.join(desconhecidos)}")

    resultado: dict[str, Any] = {}
    for campo in OS_FIELDS:
        value = dados.get(campo)
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                value = None
        if campo in INTEGER_FIELDS and value is not None:
            try:
                value = int(value)
            except (TypeError, ValueError) as exc:
                raise HTTPException(400, f"{campo} deve ser um número inteiro") from exc
        resultado[campo] = value
    return resultado


def parse_datetime(value: Any, campo: str) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError as exc:
        raise HTTPException(400, f"Data inválida no campo {campo}") from exc


def validar_dados_para_confirmacao(dados: dict[str, Any]) -> None:
    obrigatorios = {
        "numero_os": "Número da OS",
        "id_subestacao": "Instalação",
        "esquema_servicos": "Esquema de serviços",
        "prioridade": "Prioridade",
        "descricao_servicos": "Descrição dos serviços",
        "data_inicio_programado": "Início programado",
        "data_fim_programado": "Fim programado",
        "status": "Status",
    }
    ausentes = [rotulo for campo, rotulo in obrigatorios.items() if dados.get(campo) in (None, "")]
    if ausentes:
        raise HTTPException(400, "Preencha antes de confirmar: " + ", ".join(ausentes))

    inicio = parse_datetime(dados.get("data_inicio_programado"), "data_inicio_programado")
    fim = parse_datetime(dados.get("data_fim_programado"), "data_fim_programado")
    if inicio and fim and fim < inicio:
        raise HTTPException(400, "O fim programado não pode ser anterior ao início")

    inicio_exec = parse_datetime(dados.get("data_inicio_execucao"), "data_inicio_execucao")
    fim_exec = parse_datetime(dados.get("data_fim_execucao"), "data_fim_execucao")
    if inicio_exec and fim_exec and fim_exec < inicio_exec:
        raise HTTPException(400, "O fim da execução não pode ser anterior ao início")


def dados_para_modelo(dados: dict[str, Any], criando: bool) -> dict[str, Any]:
    payload = limpar_dados_os(dados)
    for campo in DATETIME_FIELDS:
        payload[campo] = parse_datetime(payload.get(campo), campo)
    if criando and payload.get("criado_em") is None:
        payload.pop("criado_em", None)
    return payload


@router.get("")
def listar_validacoes(
    busca: str = Query(""),
    status: str = Query("TODOS"),
    fonte: str = Query("TODAS"),
    tipo: str = Query("TODOS"),
    bloqueio: str = Query("TODOS"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    preparar_validacao(db)
    filtros = ["1 = 1"]
    params: dict[str, Any] = {}
    if busca.strip():
        filtros.append("(numero_os LIKE :busca OR dados_os LIKE :busca OR contexto LIKE :busca)")
        params["busca"] = f"%{busca.strip()}%"
    if status != "TODOS":
        if status not in STATUS_VALIDACAO:
            raise HTTPException(400, "Status de validação inválido")
        filtros.append("status_validacao = :status")
        params["status"] = status
    if fonte != "TODAS":
        filtros.append("fonte = :fonte")
        params["fonte"] = fonte
    if tipo != "TODOS":
        filtros.append("tipo_registro = :tipo")
        params["tipo"] = tipo
    if bloqueio != "TODOS":
        filtros.append("bloqueios LIKE :bloqueio")
        params["bloqueio"] = f'%"{bloqueio}"%'

    where = " AND ".join(filtros)
    total = db.execute(text(f"SELECT COUNT(*) FROM os_validacao_importacao WHERE {where}"), params).scalar() or 0
    params_paginados = {**params, "limit": page_size, "offset": (page - 1) * page_size}
    rows = db.execute(text(f"""
        SELECT * FROM os_validacao_importacao
        WHERE {where}
        ORDER BY
            CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(numero_os, '-', 3), '-', -1) AS UNSIGNED) DESC,
            numero_os DESC,
            id_validacao DESC
        LIMIT :limit OFFSET :offset
    """), params_paginados).mappings().all()

    resumo = {
        row["status_validacao"]: row["total"]
        for row in db.execute(text("""
            SELECT status_validacao, COUNT(*) AS total
            FROM os_validacao_importacao GROUP BY status_validacao
        """)).mappings()
    }
    fontes = [
        row[0] for row in db.execute(text("""
            SELECT DISTINCT fonte FROM os_validacao_importacao
            WHERE fonte IS NOT NULL ORDER BY fonte
        """)).all()
    ]
    bloqueios = sorted({
        bloqueio_item
        for row in db.execute(text("SELECT bloqueios FROM os_validacao_importacao")).all()
        for bloqueio_item in carregar_json(row[0], [])
    })
    return {
        "items": [serializar_linha(row, incluir_dados=False) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "resumo": resumo,
        "fontes": fontes,
        "bloqueios": bloqueios,
    }


@router.get("/opcoes")
def opcoes_validacao(db: Session = Depends(get_db)):
    preparar_validacao(db)
    subestacoes = db.execute(text("""
        SELECT id_subestacao, nome FROM subestacao ORDER BY nome
    """)).mappings().all()
    ativos = db.execute(text("""
        SELECT a.id_ativo, a.id_subestacao, a.id_grupo_ativo, a.id_funcao_operacao,
               a.codigo_ativo, a.bay, a.fase, a.especie, t.nome AS tipo_ativo
        FROM ativo a
        LEFT JOIN tipo_ativo t ON t.id_tipo_ativo = a.id_tipo_ativo
        ORDER BY a.id_subestacao, a.codigo_ativo, a.fase
    """)).mappings().all()
    grupos = db.execute(text("""
        SELECT g.id_grupo_ativo, g.id_subestacao, g.id_funcao_operacao,
               g.codigo_ativo, g.bay, g.descricao, t.nome AS tipo_ativo
        FROM grupo_ativo g
        LEFT JOIN tipo_ativo t ON t.id_tipo_ativo = g.id_tipo_ativo
        ORDER BY g.id_subestacao, g.codigo_ativo
    """)).mappings().all()
    planos = db.execute(text("""
        SELECT p.id_plano_manutencao, p.id_tipo_ativo, p.descricao_geral,
               t.nome AS tipo_ativo
        FROM plano_manutencao p
        LEFT JOIN tipo_ativo t ON t.id_tipo_ativo = p.id_tipo_ativo
        ORDER BY p.id_plano_manutencao
    """)).mappings().all()
    return {
        "subestacoes": [dict(row) for row in subestacoes],
        "ativos": [dict(row) for row in ativos],
        "grupos": [dict(row) for row in grupos],
        "planos": [dict(row) for row in planos],
    }


@router.get("/{id_validacao}")
def obter_validacao(id_validacao: int, db: Session = Depends(get_db)):
    preparar_validacao(db)
    return serializar_linha(buscar_validacao(db, id_validacao), incluir_dados=True)


@router.patch("/{id_validacao}")
def salvar_validacao(
    id_validacao: int,
    payload: ValidacaoOsUpdate,
    db: Session = Depends(get_db),
):
    preparar_validacao(db)
    atual = serializar_linha(buscar_validacao(db, id_validacao), incluir_dados=True)
    if atual["status_validacao"] == "ENVIADA":
        raise HTTPException(409, "Esta OS já foi enviada e não pode mais ser alterada nesta fila")

    dados = limpar_dados_os(payload.dados_os)
    db.execute(text("""
        UPDATE os_validacao_importacao
        SET dados_os = :dados_os,
            numero_os = :numero_os,
            observacao_validacao = :observacao,
            validado_por = COALESCE(:validado_por, validado_por),
            status_validacao = 'EM_REVISAO',
            erro_envio = NULL
        WHERE id_validacao = :id_validacao
    """), {
        "dados_os": json.dumps(dados, ensure_ascii=False),
        "numero_os": dados.get("numero_os") or atual["numero_os"],
        "observacao": payload.observacao_validacao,
        "validado_por": payload.validado_por,
        "id_validacao": id_validacao,
    })
    db.commit()
    return serializar_linha(buscar_validacao(db, id_validacao), incluir_dados=True)


@router.post("/{id_validacao}/confirmar")
def confirmar_validacao(
    id_validacao: int,
    payload: ValidacaoOsAcao,
    db: Session = Depends(get_db),
):
    preparar_validacao(db)
    atual = serializar_linha(buscar_validacao(db, id_validacao), incluir_dados=True)
    if atual["status_validacao"] == "ENVIADA":
        raise HTTPException(409, "Esta OS já foi enviada")
    validar_dados_para_confirmacao(atual["dados_os"])
    db.execute(text("""
        UPDATE os_validacao_importacao
        SET status_validacao = 'CONFIRMADA', observacao_validacao = :observacao,
            validado_por = :validado_por, validado_em = NOW(), erro_envio = NULL
        WHERE id_validacao = :id_validacao
    """), {
        "observacao": payload.observacao_validacao,
        "validado_por": payload.validado_por,
        "id_validacao": id_validacao,
    })
    db.commit()
    return {"mensagem": "OS confirmada para envio"}


@router.post("/{id_validacao}/rejeitar")
def rejeitar_validacao(
    id_validacao: int,
    payload: ValidacaoOsAcao,
    db: Session = Depends(get_db),
):
    preparar_validacao(db)
    atual = serializar_linha(buscar_validacao(db, id_validacao), incluir_dados=True)
    if atual["status_validacao"] == "ENVIADA":
        raise HTTPException(409, "Esta OS já foi enviada")
    db.execute(text("""
        UPDATE os_validacao_importacao
        SET status_validacao = 'REJEITADA', observacao_validacao = :observacao,
            validado_por = :validado_por, validado_em = NOW(), erro_envio = NULL
        WHERE id_validacao = :id_validacao
    """), {
        "observacao": payload.observacao_validacao,
        "validado_por": payload.validado_por,
        "id_validacao": id_validacao,
    })
    db.commit()
    return {"mensagem": "OS marcada como rejeitada"}


@router.post("/{id_validacao}/reabrir")
def reabrir_validacao(id_validacao: int, db: Session = Depends(get_db)):
    preparar_validacao(db)
    atual = serializar_linha(buscar_validacao(db, id_validacao), incluir_dados=True)
    if atual["status_validacao"] == "ENVIADA":
        raise HTTPException(409, "Esta OS já foi enviada")
    db.execute(text("""
        UPDATE os_validacao_importacao
        SET status_validacao = 'EM_REVISAO', validado_em = NULL, erro_envio = NULL
        WHERE id_validacao = :id_validacao
    """), {"id_validacao": id_validacao})
    db.commit()
    return {"mensagem": "OS reaberta para edição"}


@router.post("/{id_validacao}/enviar")
def enviar_validacao(id_validacao: int, db: Session = Depends(get_db)):
    preparar_validacao(db)
    atual = serializar_linha(buscar_validacao(db, id_validacao), incluir_dados=True)
    if atual["status_validacao"] != "CONFIRMADA":
        raise HTTPException(409, "Confirme a OS antes de enviá-la")

    validar_dados_para_confirmacao(atual["dados_os"])
    try:
        if atual["tipo_registro"] == "ATUALIZAR_EXISTENTE":
            ordem = db.query(OrdemServico).filter(
                OrdemServico.id_os == atual["id_os_destino"]
            ).first()
            if not ordem:
                raise HTTPException(404, "OS de destino não encontrada")
            dados_modelo = dados_para_modelo(atual["dados_os"], criando=False)
            for campo, value in dados_modelo.items():
                setattr(ordem, campo, value)
        else:
            numero_os = atual["dados_os"].get("numero_os")
            existente = db.query(OrdemServico).filter(
                OrdemServico.numero_os == numero_os
            ).first()
            if existente:
                raise HTTPException(
                    409,
                    f"A OS {numero_os} já existe no cadastro com ID {existente.id_os}",
                )
            ordem = OrdemServico(**dados_para_modelo(atual["dados_os"], criando=True))
            db.add(ordem)
            db.flush()

        db.execute(text("""
            UPDATE os_validacao_importacao
            SET status_validacao = 'ENVIADA', id_os_destino = :id_os_destino,
                enviado_em = NOW(), erro_envio = NULL
            WHERE id_validacao = :id_validacao
        """), {"id_os_destino": ordem.id_os, "id_validacao": id_validacao})
        db.commit()
        return {
            "mensagem": "OS atualizada com sucesso" if atual["tipo_registro"] == "ATUALIZAR_EXISTENTE" else "OS cadastrada com sucesso",
            "id_os": ordem.id_os,
            "numero_os": ordem.numero_os,
        }
    except HTTPException:
        db.rollback()
        raise
    except (IntegrityError, SQLAlchemyError, ValueError) as exc:
        db.rollback()
        mensagem = str(getattr(exc, "orig", exc))[:1000]
        garantir_estrutura_validacao(db)
        db.execute(text("""
            UPDATE os_validacao_importacao
            SET status_validacao = 'ERRO', erro_envio = :erro
            WHERE id_validacao = :id_validacao
        """), {"erro": mensagem, "id_validacao": id_validacao})
        db.commit()
        raise HTTPException(400, f"Não foi possível enviar a OS: {mensagem}") from exc
