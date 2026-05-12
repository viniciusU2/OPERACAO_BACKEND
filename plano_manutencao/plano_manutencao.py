# routers/inspecoes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from database import get_db
from plano_manutencao.schemas import (

    PlanoManutencaoCreate,
    PlanoManutencaoRead,
    PlanoManutencaoReadFull,
    PlanoItemCreate,
    PlanoItemRead,
 
)


from models.plano_manutencao_models import (
    PlanoManutencao,
    PlanoItem
)


router = APIRouter(prefix="/planos-manutencao", tags=["planos-manutencao"])


# ====================== CRIAR PLANO ======================
@router.post("/", response_model=PlanoManutencaoRead, status_code=201)
def criar_plano(plano_in: PlanoManutencaoCreate, db: Session = Depends(get_db)):

    db_plano = PlanoManutencao(
        id_tipo_ativo=plano_in.id_tipo_ativo,
        descricao_geral=plano_in.descricao_geral,
        materiais_previstos=plano_in.materiais_previstos,
        procedimentos_instrucoes=plano_in.procedimentos_instrucoes,
        requisitos_de_seguranca=plano_in.requisitos_de_seguranca,
        observacao_geral=plano_in.observacao_geral,
    )

    db.add(db_plano)
    db.flush()

    for item in plano_in.itens:
        db.add(PlanoItem(
            id_plano_manutencao=db_plano.id_plano_manutencao,
            **item.model_dump()
        ))

    db.commit()
    db.refresh(db_plano)

    return db_plano


# ====================== LISTAR ======================
@router.get("/", response_model=List[PlanoManutencaoRead])
def listar(db: Session = Depends(get_db)):
    return db.query(PlanoManutencao).all()


# ====================== BUSCAR ======================
@router.get("/{plano_id}", response_model=PlanoManutencaoReadFull)
def buscar(plano_id: int, db: Session = Depends(get_db)):
    plano = db.query(PlanoManutencao).filter(
        PlanoManutencao.id_plano_manutencao == plano_id
    ).first()

    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    return plano


# ====================== ITENS ======================
@router.get("/{plano_id}/itens", response_model=List[PlanoItemRead])
def itens(plano_id: int, db: Session = Depends(get_db)):
    return db.query(PlanoItem)\
        .filter(PlanoItem.id_plano_manutencao == plano_id)\
        .order_by(PlanoItem.ordem)\
        .all()


# ====================== CRIAR ITEM ======================
@router.post("/{plano_id}/itens", response_model=PlanoItemRead, status_code=201)
def criar_item(plano_id: int, item_in: PlanoItemCreate, db: Session = Depends(get_db)):

    plano = db.query(PlanoManutencao).filter(
        PlanoManutencao.id_plano_manutencao == plano_id
    ).first()

    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    db_item = PlanoItem(
        id_plano_manutencao=plano_id,
        **item_in.model_dump()
    )

    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    return db_item


# =========================================================
# ATUALIZAR PLANO (COM ITENS)
# =========================================================
@router.put("/{plano_id}", response_model=PlanoManutencaoRead)
def atualizar_plano(
    plano_id: int,
    plano_in: PlanoManutencaoCreate,
    db: Session = Depends(get_db)
):
    plano = db.query(PlanoManutencao).filter(
        PlanoManutencao.id_plano_manutencao == plano_id
    ).first()

    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    # Atualiza dados do plano
    plano.id_tipo_ativo = plano_in.id_tipo_ativo
    plano.descricao_geral = plano_in.descricao_geral
    plano.materiais_previstos = plano_in.materiais_previstos
    plano.procedimentos_instrucoes = plano_in.procedimentos_instrucoes
    plano.requisitos_de_seguranca = plano_in.requisitos_de_seguranca
    plano.observacao_geral = plano_in.observacao_geral

    # 🔥 Remove itens antigos
    db.query(PlanoItem).filter(
        PlanoItem.id_plano_manutencao == plano_id
    ).delete()

    # 🔥 Recria itens
    for item in plano_in.itens:
        db.add(PlanoItem(
            id_plano_manutencao=plano_id,
            **item.model_dump()
        ))

    db.commit()
    db.refresh(plano)

    return plano