from __future__ import annotations

import logging

from fastapi import Request
from jose import JWTError, jwt
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from auth.dependencies import get_secret_key
from database import SessionLocal
from models.auth_models import Usuario

from . import models, schemas

LOGGER = logging.getLogger("engenharia_protecao.auditoria")
PREFIXO = "/engenharia-protecao"


def _identidade(request: Request, db: Session) -> int | None:
    autorizacao = request.headers.get("authorization", "")
    if not autorizacao.lower().startswith("bearer "):
        return None
    try:
        payload = jwt.decode(autorizacao.split(" ", 1)[1], get_secret_key(), algorithms=["HS256"])
        email = payload.get("sub")
        if not email:
            return None
        return db.query(Usuario.id).filter(Usuario.email == email).scalar()
    except JWTError:
        return None


ACOES_POR_SUFIXO = {
    "arquivar": "ARQUIVAMENTO",
    "reativar": "REATIVACAO",
    "encerrar": "ENCERRAMENTO",
    "submeter": "SUBMISSAO",
    "aprovar": "APROVACAO",
    "rejeitar": "REJEICAO",
    "cancelar": "CANCELAMENTO",
    "implantar": "IMPLANTACAO",
    "validar": "VALIDACAO",
    "iniciar-analise": "ANALISE",
    "iniciar-validacao": "INICIO_VALIDACAO",
    "reverter": "REVERSAO",
    "movimentacoes": "MOVIMENTACAO",
    "importar": "IMPORTACAO",
}


def _classificar(request: Request) -> tuple[str, str | None, str | None] | None:
    caminho = request.url.path
    metodo = request.method.upper()
    download = metodo == "GET" and caminho.endswith("/download")
    if metodo not in {"POST", "PUT", "PATCH", "DELETE"} and not download:
        return None
    partes = [parte for parte in caminho[len(PREFIXO):].split("/") if parte]
    recurso = partes[0] if partes else None
    id_recurso = next((parte for parte in partes[1:] if parte.isdigit()), None)
    if download:
        acao = "DOWNLOAD"
    elif metodo == "POST" and partes and partes[-1] in ACOES_POR_SUFIXO:
        acao = ACOES_POR_SUFIXO[partes[-1]]
    else:
        acao = {"POST": "CRIACAO", "PUT": "ATUALIZACAO", "PATCH": "ATUALIZACAO", "DELETE": "REMOCAO"}[metodo]
    return acao, recurso, id_recurso


class EngenhariaProtecaoAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        classificacao = _classificar(request) if request.url.path.startswith(PREFIXO) else None
        response = await call_next(request)
        if not classificacao:
            return response
        acao, recurso, id_recurso = classificacao
        db = SessionLocal()
        try:
            db.add(
                models.EngenhariaProtecaoAuditoria(
                    id_usuario=_identidade(request, db),
                    acao=acao,
                    metodo=request.method.upper(),
                    caminho=request.url.path[:500],
                    recurso=recurso,
                    id_recurso=id_recurso,
                    status_http=response.status_code,
                    endereco_ip=(request.client.host if request.client else None),
                    user_agent=(request.headers.get("user-agent") or "")[:300] or None,
                    detalhes=(request.url.query or None),
                )
            )
            db.commit()
        except Exception as exc:  # auditoria nunca deve mascarar a resposta principal
            db.rollback()
            LOGGER.warning("Falha ao registrar auditoria de %s: %s", request.url.path, exc)
        finally:
            db.close()
        return response


def listar_auditoria(
    db: Session,
    acao: str | None,
    recurso: str | None,
    id_usuario: int | None,
    page: int,
    page_size: int,
) -> schemas.AuditoriaGeralLista:
    query = db.query(models.EngenhariaProtecaoAuditoria, Usuario.nome).outerjoin(
        Usuario, Usuario.id == models.EngenhariaProtecaoAuditoria.id_usuario
    )
    if acao:
        query = query.filter(models.EngenhariaProtecaoAuditoria.acao == acao.upper())
    if recurso:
        query = query.filter(models.EngenhariaProtecaoAuditoria.recurso == recurso)
    if id_usuario:
        query = query.filter(models.EngenhariaProtecaoAuditoria.id_usuario == id_usuario)
    total = query.with_entities(func.count(models.EngenhariaProtecaoAuditoria.id_engenharia_protecao_auditoria)).scalar() or 0
    linhas = (
        query.order_by(models.EngenhariaProtecaoAuditoria.id_engenharia_protecao_auditoria.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        schemas.AuditoriaGeralOut(
            id_engenharia_protecao_auditoria=item.id_engenharia_protecao_auditoria,
            id_usuario=item.id_usuario,
            nome_usuario=nome,
            acao=item.acao,
            metodo=item.metodo,
            caminho=item.caminho,
            recurso=item.recurso,
            id_recurso=item.id_recurso,
            status_http=item.status_http,
            endereco_ip=item.endereco_ip,
            detalhes=item.detalhes,
            criado_em=item.criado_em,
        )
        for item, nome in linhas
    ]
    return schemas.AuditoriaGeralLista(total=total, page=page, page_size=page_size, items=items)
