from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from auth.dependencies import get_current_user, require_roles
from database import get_db
from models.auth_models import Usuario
from models.rdo_models import (
    Rdo,
    RdoConfiguracaoSistema,
    RdoEvento,
    RdoHistoricoEdicao,
)
from RDO.schemas import (
    RdoConfiguracaoCreate,
    RdoConfiguracaoResponse,
    RdoConfiguracaoUpdate,
    RdoCreate,
    RdoEventoCreate,
    RdoEventoResponse,
    RdoEventoUpdate,
    RdoHistoricoResponse,
    RdoResponse,
    RdoResumoResponse,
    RdoUpdate,
)
from RDO.pdf_export import gerar_pdf_rdo

router = APIRouter(prefix="/rdo", tags=["RDO"])


def registrar_historico(
    db: Session,
    id_rdo: int,
    usuario: Optional[Usuario],
    acao: str,
    campo_alterado: Optional[str] = None,
    valor_anterior: Optional[str] = None,
    valor_novo: Optional[str] = None,
    observacao: Optional[str] = None,
):
    db.add(
        RdoHistoricoEdicao(
            id_rdo=id_rdo,
            id_usuario=usuario.id if usuario else None,
            acao=acao,
            campo_alterado=campo_alterado,
            valor_anterior=valor_anterior,
            valor_novo=valor_novo,
            observacao=observacao,
        )
    )


def buscar_rdo_ou_404(db: Session, id_rdo: int) -> Rdo:
    rdo = (
        db.query(Rdo)
        .options(
            selectinload(Rdo.configuracoes),
            selectinload(Rdo.eventos),
        )
        .filter(Rdo.id_rdo == id_rdo)
        .first()
    )
    if not rdo:
        raise HTTPException(status_code=404, detail="RDO nao encontrado")
    return rdo


def serializar_configuracao(configuracao: RdoConfiguracaoSistema):
    return {
        "id_configuracao": configuracao.id_configuracao,
        "id_rdo": configuracao.id_rdo,
        "periodo_inicio": configuracao.periodo_inicio,
        "periodo_fim": configuracao.periodo_fim,
        "subestacao": configuracao.subestacao,
        "equipamento": configuracao.equipamento,
        "estado": configuracao.estado,
        "ordem": configuracao.ordem or 0,
    }


def serializar_evento(evento: RdoEvento):
    return {
        "id_evento": evento.id_evento,
        "id_rdo": evento.id_rdo,
        "categoria": evento.categoria,
        "sistema": evento.sistema,
        "subestacao": evento.subestacao,
        "hora_inicio": evento.hora_inicio,
        "hora_fim": evento.hora_fim,
        "titulo": evento.titulo,
        "descricao": evento.descricao,
        "status_evento": evento.status_evento,
        "ordem": evento.ordem or 0,
        "criado_por": evento.criado_por,
        "editado_por": evento.editado_por,
        "criado_em": evento.criado_em,
        "atualizado_em": evento.atualizado_em,
    }


def serializar_rdo(rdo: Rdo):
    return {
        "id_rdo": rdo.id_rdo,
        "data_rdo": rdo.data_rdo,
        "titulo": rdo.titulo,
        "codigo_procedimento": rdo.codigo_procedimento,
        "revisao": rdo.revisao,
        "sistema": rdo.sistema,
        "emissor": rdo.emissor,
        "arquivo_pdf": rdo.arquivo_pdf,
        "status": rdo.status,
        "criado_por": rdo.criado_por,
        "editado_por": rdo.editado_por,
        "validado_por": rdo.validado_por,
        "criado_em": rdo.criado_em,
        "atualizado_em": rdo.atualizado_em,
        "validado_em": rdo.validado_em,
        "configuracoes": [
            serializar_configuracao(configuracao)
            for configuracao in sorted(
                rdo.configuracoes,
                key=lambda item: (item.ordem or 0, item.id_configuracao or 0),
            )
        ],
        "eventos": [
            serializar_evento(evento)
            for evento in sorted(
                rdo.eventos,
                key=lambda item: (item.ordem or 0, item.id_evento or 0),
            )
        ],
    }


@router.get("/", response_model=list[RdoResumoResponse])
def listar_rdos(
    data: Optional[str] = None,
    sistema: Optional[str] = None,
    status: Optional[str] = None,
    busca: Optional[str] = None,
    db: Session = Depends(get_db),
    _usuario=Depends(require_roles("admin", "mantenedor", "operador")),
):
    query = db.query(Rdo)

    if data:
        try:
            data_inicio = datetime.strptime(data, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Data invalida. Use YYYY-MM-DD")
        query = query.filter(Rdo.data_rdo == data_inicio)

    if sistema and sistema != "all":
        query = query.filter(Rdo.sistema == sistema)

    if status and status != "all":
        query = query.filter(Rdo.status == status)

    if busca:
        termo = f"%{busca}%"
        query = query.filter(
            (Rdo.emissor.like(termo))
            | (Rdo.titulo.like(termo))
            | (Rdo.codigo_procedimento.like(termo))
        )

    return query.order_by(Rdo.data_rdo.desc(), Rdo.id_rdo.desc()).all()


@router.get("/{id_rdo}", response_model=RdoResponse)
def buscar_rdo(
    id_rdo: int,
    db: Session = Depends(get_db),
    _usuario=Depends(require_roles("admin", "mantenedor", "operador")),
):
    return serializar_rdo(buscar_rdo_ou_404(db, id_rdo))


@router.get("/{id_rdo}/pdf")
def exportar_rdo_pdf(
    id_rdo: int,
    db: Session = Depends(get_db),
    _usuario=Depends(require_roles("admin", "mantenedor", "operador")),
):
    rdo = buscar_rdo_ou_404(db, id_rdo)
    arquivo = gerar_pdf_rdo(rdo)
    return FileResponse(
        path=str(arquivo),
        media_type="application/pdf",
        filename=arquivo.name,
    )


@router.post("/", response_model=RdoResponse)
def criar_rdo(
    dados: RdoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    payload = dados.model_dump(exclude={"configuracoes", "eventos"})
    novo = Rdo(**payload, criado_por=usuario.id, editado_por=usuario.id)

    for configuracao in dados.configuracoes:
        novo.configuracoes.append(RdoConfiguracaoSistema(**configuracao.model_dump()))

    for evento in dados.eventos:
        novo.eventos.append(
            RdoEvento(**evento.model_dump(), criado_por=usuario.id, editado_por=usuario.id)
        )

    db.add(novo)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Ja existe RDO para esta data e sistema",
        )

    registrar_historico(db, novo.id_rdo, usuario, "CRIACAO", observacao="RDO criado")
    db.commit()
    db.refresh(novo)
    return serializar_rdo(buscar_rdo_ou_404(db, novo.id_rdo))


@router.put("/{id_rdo}", response_model=RdoResponse)
def atualizar_rdo(
    id_rdo: int,
    dados: RdoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    rdo = buscar_rdo_ou_404(db, id_rdo)
    payload = dados.model_dump(exclude_unset=True)

    for campo, valor in payload.items():
        anterior = getattr(rdo, campo)
        if anterior != valor:
            setattr(rdo, campo, valor)
            registrar_historico(
                db,
                id_rdo,
                usuario,
                "EDICAO",
                campo_alterado=campo,
                valor_anterior=str(anterior) if anterior is not None else None,
                valor_novo=str(valor) if valor is not None else None,
            )

    rdo.editado_por = usuario.id
    rdo.atualizado_em = datetime.utcnow()

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Ja existe RDO para esta data e sistema",
        )

    return serializar_rdo(buscar_rdo_ou_404(db, id_rdo))


@router.post("/{id_rdo}/validar", response_model=RdoResponse)
def validar_rdo(
    id_rdo: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    rdo = buscar_rdo_ou_404(db, id_rdo)
    rdo.status = "VALIDADO"
    rdo.validado_por = usuario.id
    rdo.editado_por = usuario.id
    rdo.validado_em = datetime.utcnow()
    rdo.atualizado_em = datetime.utcnow()
    registrar_historico(db, id_rdo, usuario, "VALIDACAO", observacao="RDO validado")
    db.commit()
    return serializar_rdo(buscar_rdo_ou_404(db, id_rdo))


@router.post("/{id_rdo}/configuracoes", response_model=RdoConfiguracaoResponse)
def criar_configuracao(
    id_rdo: int,
    dados: RdoConfiguracaoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    rdo = buscar_rdo_ou_404(db, id_rdo)
    configuracao = RdoConfiguracaoSistema(id_rdo=id_rdo, **dados.model_dump())
    rdo.editado_por = usuario.id
    rdo.atualizado_em = datetime.utcnow()
    db.add(configuracao)
    registrar_historico(
        db,
        id_rdo,
        usuario,
        "EDICAO",
        campo_alterado="configuracoes",
        observacao="Configuracao do sistema adicionada",
    )
    db.commit()
    db.refresh(configuracao)
    return configuracao


@router.put("/configuracoes/{id_configuracao}", response_model=RdoConfiguracaoResponse)
def atualizar_configuracao(
    id_configuracao: int,
    dados: RdoConfiguracaoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    configuracao = (
        db.query(RdoConfiguracaoSistema)
        .filter(RdoConfiguracaoSistema.id_configuracao == id_configuracao)
        .first()
    )
    if not configuracao:
        raise HTTPException(status_code=404, detail="Configuracao nao encontrada")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(configuracao, campo, valor)

    rdo = db.query(Rdo).filter(Rdo.id_rdo == configuracao.id_rdo).first()
    if rdo:
        rdo.editado_por = usuario.id
        rdo.atualizado_em = datetime.utcnow()
        registrar_historico(
            db,
            rdo.id_rdo,
            usuario,
            "EDICAO",
            campo_alterado="configuracoes",
            observacao="Configuracao do sistema atualizada",
        )

    db.commit()
    db.refresh(configuracao)
    return configuracao


@router.delete("/configuracoes/{id_configuracao}")
def excluir_configuracao(
    id_configuracao: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    configuracao = (
        db.query(RdoConfiguracaoSistema)
        .filter(RdoConfiguracaoSistema.id_configuracao == id_configuracao)
        .first()
    )
    if not configuracao:
        raise HTTPException(status_code=404, detail="Configuracao nao encontrada")

    id_rdo = configuracao.id_rdo
    db.delete(configuracao)
    registrar_historico(
        db,
        id_rdo,
        usuario,
        "EDICAO",
        campo_alterado="configuracoes",
        observacao="Configuracao do sistema removida",
    )
    db.commit()
    return {"message": "Configuracao removida"}


@router.post("/{id_rdo}/eventos", response_model=RdoEventoResponse)
def criar_evento(
    id_rdo: int,
    dados: RdoEventoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    rdo = buscar_rdo_ou_404(db, id_rdo)
    evento = RdoEvento(
        id_rdo=id_rdo,
        **dados.model_dump(),
        criado_por=usuario.id,
        editado_por=usuario.id,
    )
    rdo.editado_por = usuario.id
    rdo.atualizado_em = datetime.utcnow()
    db.add(evento)
    registrar_historico(
        db,
        id_rdo,
        usuario,
        "EDICAO",
        campo_alterado="eventos",
        observacao="Evento adicionado",
    )
    db.commit()
    db.refresh(evento)
    return evento


@router.put("/eventos/{id_evento}", response_model=RdoEventoResponse)
def atualizar_evento(
    id_evento: int,
    dados: RdoEventoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    evento = db.query(RdoEvento).filter(RdoEvento.id_evento == id_evento).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento nao encontrado")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(evento, campo, valor)

    evento.editado_por = usuario.id
    evento.atualizado_em = datetime.utcnow()

    rdo = db.query(Rdo).filter(Rdo.id_rdo == evento.id_rdo).first()
    if rdo:
        rdo.editado_por = usuario.id
        rdo.atualizado_em = datetime.utcnow()
        registrar_historico(
            db,
            rdo.id_rdo,
            usuario,
            "EDICAO",
            campo_alterado="eventos",
            observacao="Evento atualizado",
        )

    db.commit()
    db.refresh(evento)
    return evento


@router.delete("/eventos/{id_evento}")
def excluir_evento(
    id_evento: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    evento = db.query(RdoEvento).filter(RdoEvento.id_evento == id_evento).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento nao encontrado")

    id_rdo = evento.id_rdo
    db.delete(evento)
    registrar_historico(
        db,
        id_rdo,
        usuario,
        "EDICAO",
        campo_alterado="eventos",
        observacao="Evento removido",
    )
    db.commit()
    return {"message": "Evento removido"}


@router.get("/{id_rdo}/historico", response_model=list[RdoHistoricoResponse])
def listar_historico(
    id_rdo: int,
    db: Session = Depends(get_db),
    _usuario=Depends(require_roles("admin", "mantenedor", "operador")),
):
    buscar_rdo_ou_404(db, id_rdo)
    return (
        db.query(RdoHistoricoEdicao)
        .filter(RdoHistoricoEdicao.id_rdo == id_rdo)
        .order_by(RdoHistoricoEdicao.criado_em.desc())
        .all()
    )

