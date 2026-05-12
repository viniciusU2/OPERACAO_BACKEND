# routers/inspecoes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone, timedelta

from database import get_db

# Models
from models.plano_manutencao_models import (
    Inspecao,
    ResultadoItemInspecao,
    PlanoItem
)

from plano_manutencao.schemas import (
    InspecaoCreate,
    InspecaoRead,
    InspecaoReadFull
)


from models.plano_manutencao_models import (
    Inspecao,
    ResultadoItemInspecao,
    PlanoItem,
    PlanoExecucao
)



router = APIRouter(prefix="/inspecoes", tags=["inspecoes"])


# =========================================================
# FUNÇÃO: CALCULAR PRÓXIMA EXECUÇÃO
# =========================================================
def calcular_proxima_execucao(data_base, periodicidade, intervalo):

    if periodicidade == "SEMANAL":
        return data_base + timedelta(weeks=intervalo)

    elif periodicidade == "MENSAL":
        return data_base + timedelta(days=30 * intervalo)

    elif periodicidade == "BIMESTRAL":
        return data_base + timedelta(days=60 * intervalo)

    elif periodicidade == "TRIMESTRAL":
        return data_base + timedelta(days=90 * intervalo)

    elif periodicidade == "SEMESTRAL":
        return data_base + timedelta(days=180 * intervalo)

    elif periodicidade == "3_ANOS":
        return data_base + timedelta(days=365 * 3 * intervalo)

    elif periodicidade == "5_ANOS":
        return data_base + timedelta(days=365 * 5 * intervalo)

    elif periodicidade == "6_ANOS":
        return data_base + timedelta(days=365 * 6 * intervalo)

    return data_base


# =========================================================
# CRIAR INSPEÇÃO
# =========================================================
@router.post("/", response_model=InspecaoRead, status_code=201)
def criar_inspecao(inspecao_in: InspecaoCreate, db: Session = Depends(get_db)):

    db_inspecao = Inspecao(
        id_ativo=inspecao_in.id_ativo,
        id_os=inspecao_in.id_os,
        data_inspecao=datetime.now(timezone.utc),
        periodicidade=inspecao_in.periodicidade,
        responsavel=getattr(inspecao_in, "responsavel", None),
        observacao_geral=getattr(inspecao_in, "observacao_geral", None),
    )

    db.add(db_inspecao)
    db.flush()

    status_geral = "OK"

    for res in inspecao_in.resultados:

        plano_item = db.query(PlanoItem).filter(
            PlanoItem.id_plano_item == res.id_plano_item,
            PlanoItem.ativo == True
        ).first()

        if not plano_item:
            raise HTTPException(
                status_code=400,
                detail=f"PlanoItem {res.id_plano_item} não encontrado"
            )

        # ================= RESULTADO =================
        db_resultado = ResultadoItemInspecao(
            id_inspecao=db_inspecao.id_inspecao,
            id_plano_item=plano_item.id_plano_item,
            nome_item=plano_item.nome_item,
            valor_referencia=plano_item.valor_referencia,
            tolerancia=plano_item.tolerancia,
            valor_medido=res.valor_medido,
            status_item=res.status_item,
            observacao_item=res.observacao_item,
        )

        db.add(db_resultado)

        if res.status_item == "NOK":
            status_geral = "NOK"

        # ================= EXECUÇÃO =================
        execucao = db.query(PlanoExecucao).filter(
            PlanoExecucao.id_plano_item == plano_item.id_plano_item,
            PlanoExecucao.id_ativo == db_inspecao.id_ativo
        ).first()

        proxima = calcular_proxima_execucao(
            db_inspecao.data_inspecao,
            plano_item.periodicidade,
            plano_item.intervalo
        )

        if execucao:
            execucao.ultima_execucao = db_inspecao.data_inspecao
            execucao.proxima_execucao = proxima
            execucao.id_inspecao = db_inspecao.id_inspecao
        else:
            db.add(PlanoExecucao(
                id_plano_item=plano_item.id_plano_item,
                id_ativo=db_inspecao.id_ativo,
                ultima_execucao=db_inspecao.data_inspecao,
                proxima_execucao=proxima,
                id_inspecao=db_inspecao.id_inspecao
            ))

    db_inspecao.status_geral = status_geral

    db.commit()
    db.refresh(db_inspecao)

    return db_inspecao


# =========================================================
# BUSCAR INSPEÇÃO
# =========================================================
@router.get("/{inspecao_id}", response_model=InspecaoReadFull)
def buscar_inspecao(inspecao_id: int, db: Session = Depends(get_db)):
    inspecao = db.query(Inspecao).filter(
        Inspecao.id_inspecao == inspecao_id
    ).first()

    if not inspecao:
        raise HTTPException(status_code=404, detail="Inspeção não encontrada")

    return inspecao


# =========================================================
# LISTAR POR ATIVO
# =========================================================
@router.get("/ativo/{ativo_id}", response_model=List[InspecaoReadFull])
def listar_por_ativo(ativo_id: int, db: Session = Depends(get_db)):
    return db.query(Inspecao)\
        .filter(Inspecao.id_ativo == ativo_id)\
        .order_by(Inspecao.data_inspecao.desc())\
        .all()


# =========================================================
# LISTAR TODAS
# =========================================================
@router.get("/", response_model=List[InspecaoRead])
def listar_todas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Inspecao)\
        .order_by(Inspecao.data_inspecao.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()


# =========================================================
# ITENS PENDENTES (MANTIDO!)
# =========================================================
@router.get("/pendentes/{ativo_id}")
def itens_pendentes(ativo_id: int, db: Session = Depends(get_db)):
    return db.query(PlanoItem)\
        .filter(
            PlanoItem.id_ativo == ativo_id,
            PlanoItem.ativo == True
        )\
        .order_by(PlanoItem.ordem)\
        .all()


# =========================================================
# AGENDA
# =========================================================
@router.get("/agenda/{ativo_id}")
def agenda_execucao(ativo_id: int, db: Session = Depends(get_db)):
    return db.query(PlanoExecucao)\
        .filter(
            PlanoExecucao.id_ativo == ativo_id,
            PlanoExecucao.ativo == True
        )\
        .order_by(PlanoExecucao.proxima_execucao)\
        .all()


# =========================================================
# ATRASADOS
# =========================================================
@router.get("/atrasados/{ativo_id}")
def itens_atrasados(ativo_id: int, db: Session = Depends(get_db)):

    agora = datetime.now(timezone.utc)

    return db.query(PlanoExecucao)\
        .filter(
            PlanoExecucao.id_ativo == ativo_id,
            PlanoExecucao.proxima_execucao < agora,
            PlanoExecucao.ativo == True
        )\
        .all()