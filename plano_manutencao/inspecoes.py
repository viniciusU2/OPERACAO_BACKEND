from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text as QueryText
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.plano_manutencao_models import (
    PlanoManutencao,
    Inspecao,
    PlanoExecucao,
    PlanoItem,
    ResultadoItemInspecao,
)
from models.Ativo import Ativo
from plano_manutencao.schemas import (
    InspecaoCreate,
    InspecaoRead,
    InspecaoReadFull,
    InspecaoUpdate,
    PlanoExecucaoRead,
    PlanoItemRead,
)

router = APIRouter(prefix="/inspecoes", tags=["inspecoes"])


def garantir_colunas_inspecao(db: Session):
    colunas = {
        row[0]
        for row in db.execute(
            QueryText(
                """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'resultado_item_inspecao'
                """
            )
        ).fetchall()
    }

    if "id_plano_item" not in colunas:
        db.execute(QueryText("ALTER TABLE resultado_item_inspecao ADD COLUMN id_plano_item INT NULL"))
    if "nome_item" not in colunas:
        db.execute(QueryText("ALTER TABLE resultado_item_inspecao ADD COLUMN nome_item VARCHAR(200) NULL"))
    if "valor_referencia" not in colunas:
        db.execute(QueryText("ALTER TABLE resultado_item_inspecao ADD COLUMN valor_referencia DECIMAL(12, 4) NULL"))
    if "tolerancia" not in colunas:
        db.execute(QueryText("ALTER TABLE resultado_item_inspecao ADD COLUMN tolerancia DECIMAL(12, 4) NULL"))
    if "id_item_template" in colunas:
        db.execute(QueryText("ALTER TABLE resultado_item_inspecao MODIFY COLUMN id_item_template INT NULL"))


def calcular_proxima_execucao(data_base, periodicidade, intervalo):
    periodicidade = getattr(periodicidade, "value", periodicidade)
    if periodicidade == "SEMANAL":
        return data_base + timedelta(weeks=intervalo)
    if periodicidade == "MENSAL":
        return data_base + timedelta(days=30 * intervalo)
    if periodicidade == "BIMESTRAL":
        return data_base + timedelta(days=60 * intervalo)
    if periodicidade == "TRIMESTRAL":
        return data_base + timedelta(days=90 * intervalo)
    if periodicidade == "SEMESTRAL":
        return data_base + timedelta(days=180 * intervalo)
    if periodicidade == "3_ANOS":
        return data_base + timedelta(days=365 * 3 * intervalo)
    if periodicidade == "5_ANOS":
        return data_base + timedelta(days=365 * 5 * intervalo)
    if periodicidade == "6_ANOS":
        return data_base + timedelta(days=365 * 6 * intervalo)
    return data_base


def atualizar_resultados(db: Session, inspecao: Inspecao, resultados):
    status_geral = "OK" if resultados else "NA"

    for resultado in list(inspecao.resultados):
        db.delete(resultado)
    db.flush()

    for res in resultados:
        plano_item = (
            db.query(PlanoItem)
            .filter(PlanoItem.id_plano_item == res.id_plano_item)
            .first()
        )
        if not plano_item:
            raise HTTPException(
                status_code=400,
                detail=f"PlanoItem {res.id_plano_item} nao encontrado",
            )

        db.add(
            ResultadoItemInspecao(
                id_inspecao=inspecao.id_inspecao,
                id_plano_item=plano_item.id_plano_item,
                nome_item=plano_item.nome_item,
                valor_referencia=plano_item.valor_referencia,
                tolerancia=plano_item.tolerancia,
                valor_medido=res.valor_medido,
                status_item=res.status_item,
                observacao_item=res.observacao_item,
            )
        )

        if res.status_item == "NOK":
            status_geral = "NOK"

        proxima = calcular_proxima_execucao(
            inspecao.data_inspecao,
            plano_item.periodicidade,
            plano_item.intervalo or 1,
        )
        execucao = (
            db.query(PlanoExecucao)
            .filter(
                PlanoExecucao.id_plano_item == plano_item.id_plano_item,
                PlanoExecucao.id_ativo == inspecao.id_ativo,
            )
            .first()
        )
        if execucao:
            execucao.ultima_execucao = inspecao.data_inspecao
            execucao.proxima_execucao = proxima
            execucao.id_inspecao = inspecao.id_inspecao
        else:
            db.add(
                PlanoExecucao(
                    id_plano_item=plano_item.id_plano_item,
                    id_ativo=inspecao.id_ativo,
                    ultima_execucao=inspecao.data_inspecao,
                    proxima_execucao=proxima,
                    id_inspecao=inspecao.id_inspecao,
                )
            )

    inspecao.status_geral = status_geral


def carregar_inspecao(db: Session, inspecao_id: int):
    inspecao = (
        db.query(Inspecao)
        .options(
            joinedload(Inspecao.ativo),
            joinedload(Inspecao.ordem_servico),
            joinedload(Inspecao.resultados).joinedload(ResultadoItemInspecao.plano_item),
        )
        .filter(Inspecao.id_inspecao == inspecao_id)
        .first()
    )
    if not inspecao:
        raise HTTPException(status_code=404, detail="Inspecao nao encontrada")
    return inspecao


@router.get("/ativo/{ativo_id}", response_model=List[InspecaoReadFull])
def listar_por_ativo(ativo_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Inspecao)
        .options(
            joinedload(Inspecao.ativo),
            joinedload(Inspecao.ordem_servico),
            joinedload(Inspecao.resultados),
        )
        .filter(Inspecao.id_ativo == ativo_id)
        .order_by(Inspecao.data_inspecao.desc())
        .all()
    )


@router.get("/pendentes/{ativo_id}", response_model=List[PlanoItemRead])
def itens_pendentes(
    ativo_id: int,
    periodicidade: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    ativo = db.query(Ativo).filter(Ativo.id_ativo == ativo_id).first()
    if not ativo:
        raise HTTPException(status_code=404, detail="Ativo nao encontrado")

    query = (
        db.query(PlanoItem)
        .join(PlanoManutencao, PlanoManutencao.id_plano_manutencao == PlanoItem.id_plano_manutencao)
        .filter(
            (PlanoItem.id_ativo == ativo_id)
            | ((PlanoItem.id_ativo.is_(None)) & (PlanoManutencao.id_tipo_ativo == ativo.id_tipo_ativo))
        )
    )
    if periodicidade:
        query = query.filter(PlanoItem.periodicidade == periodicidade)
    return query.order_by(PlanoItem.ordem).all()


@router.get("/agenda/{ativo_id}", response_model=List[PlanoExecucaoRead])
def agenda_execucao(ativo_id: int, db: Session = Depends(get_db)):
    return (
        db.query(PlanoExecucao)
        .filter(PlanoExecucao.id_ativo == ativo_id)
        .order_by(PlanoExecucao.proxima_execucao)
        .all()
    )


@router.get("/atrasados/{ativo_id}", response_model=List[PlanoExecucaoRead])
def itens_atrasados(ativo_id: int, db: Session = Depends(get_db)):
    agora = datetime.now(timezone.utc)
    return (
        db.query(PlanoExecucao)
        .filter(
            PlanoExecucao.id_ativo == ativo_id,
            PlanoExecucao.proxima_execucao < agora,
        )
        .all()
    )


@router.get("", response_model=List[InspecaoRead])
@router.get("/", response_model=List[InspecaoRead])
def listar_todas(
    skip: int = 0,
    limit: int = 200,
    status: Optional[str] = Query(default=None),
    periodicidade: Optional[str] = Query(default=None),
    id_ativo: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Inspecao).options(
        joinedload(Inspecao.ativo),
        joinedload(Inspecao.ordem_servico),
    )
    if status and status != "all":
        query = query.filter(Inspecao.status_geral == status)
    if periodicidade and periodicidade != "all":
        query = query.filter(Inspecao.periodicidade == periodicidade)
    if id_ativo:
        query = query.filter(Inspecao.id_ativo == id_ativo)
    return (
        query.order_by(Inspecao.data_inspecao.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("", response_model=InspecaoReadFull, status_code=201)
@router.post("/", response_model=InspecaoReadFull, status_code=201)
def criar_inspecao(inspecao_in: InspecaoCreate, db: Session = Depends(get_db)):
    db_inspecao = Inspecao(
        id_ativo=inspecao_in.id_ativo,
        id_os=inspecao_in.id_os,
        data_inspecao=inspecao_in.data_inspecao or datetime.now(timezone.utc),
        data_proxima_inspecao=inspecao_in.data_proxima_inspecao,
        periodicidade=inspecao_in.periodicidade,
        responsavel=inspecao_in.responsavel,
        observacao_geral=inspecao_in.observacao_geral or "",
    )
    db.add(db_inspecao)
    db.flush()

    atualizar_resultados(db, db_inspecao, inspecao_in.resultados)
    db.commit()

    return carregar_inspecao(db, db_inspecao.id_inspecao)


@router.get("/{inspecao_id}", response_model=InspecaoReadFull)
def buscar_inspecao(inspecao_id: int, db: Session = Depends(get_db)):
    return carregar_inspecao(db, inspecao_id)


@router.put("/{inspecao_id}", response_model=InspecaoReadFull)
def atualizar_inspecao(
    inspecao_id: int,
    dados: InspecaoUpdate,
    db: Session = Depends(get_db),
):
    inspecao = carregar_inspecao(db, inspecao_id)
    payload = dados.model_dump(exclude_unset=True)
    resultados = payload.pop("resultados", None)

    for campo, valor in payload.items():
        setattr(inspecao, campo, valor)

    if resultados is not None:
        atualizar_resultados(db, inspecao, dados.resultados or [])

    db.commit()
    return carregar_inspecao(db, inspecao_id)


@router.delete("/{inspecao_id}", status_code=204)
def excluir_inspecao(inspecao_id: int, db: Session = Depends(get_db)):
    inspecao = carregar_inspecao(db, inspecao_id)
    db.delete(inspecao)
    db.commit()
    return None
