# routers/inspecoes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database import get_db

# Models
from models.plano_manutencao_models import Inspecao
from models.plano_manutencao_models import ResultadoItemInspecao
from models.plano_manutencao_models import ItemInspecaoTemplate

# Schemas
from plano_manutencao.schemas import (
    InspecaoCreate,
    InspecaoRead,
    InspecaoReadFull
)
from plano_manutencao.schemas import (
    ItemInspecaoTemplateCreate,
    ItemInspecaoTemplateRead
)

router = APIRouter(prefix="/inspecoes", tags=["inspecoes"])


# ====================== INSPEÇÕES ======================

@router.post("/", response_model=InspecaoRead, status_code=201)
def criar_inspecao(
    inspecao_in: InspecaoCreate, 
    db: Session = Depends(get_db)
):
    """Cria uma nova inspeção com seus respectivos resultados"""
    
    # Cria a inspeção principal
    db_inspecao = Inspecao(
        id_ativo=inspecao_in.id_ativo,
        id_os=inspecao_in.id_os,
        data_inspecao=inspecao_in.data_inspecao or datetime.utcnow(),
        data_proxima_inspecao=inspecao_in.data_proxima_inspecao,
        periodicidade=inspecao_in.periodicidade,
        responsavel=inspecao_in.responsavel,
        observacao_geral=inspecao_in.observacao_geral,
    )

    db.add(db_inspecao)
    db.commit()
    db.refresh(db_inspecao)

    # Cria os resultados dos itens
    for res in inspecao_in.resultados:
        db_resultado = ResultadoItemInspecao(
            id_inspecao=db_inspecao.id_inspecao,
            id_item_template=res.id_item_template,
            valor_medido=res.valor_medido,
            status_item=res.status_item,
            observacao_item=res.observacao_item,
        )
        db.add(db_resultado)

    db.commit()
    # Refresh final para retornar status_geral atualizado (se quiser calcular depois)
    db.refresh(db_inspecao)
    return db_inspecao


@router.get("/{inspecao_id}", response_model=InspecaoReadFull)
def buscar_inspecao(inspecao_id: int, db: Session = Depends(get_db)):
    """Busca uma inspeção completa com todos os resultados"""
    inspecao = db.query(Inspecao).filter(Inspecao.id_inspecao == inspecao_id).first()
    if not inspecao:
        raise HTTPException(status_code=404, detail="Inspeção não encontrada")
    return inspecao


@router.get("/ativo/{ativo_id}", response_model=List[InspecaoReadFull])
def listar_inspecoes_por_ativo(ativo_id: int, db: Session = Depends(get_db)):
    """Lista todas as inspeções de um ativo específico com detalhes completos"""
    inspecoes = db.query(Inspecao)\
                  .filter(Inspecao.id_ativo == ativo_id)\
                  .all()
    return inspecoes


@router.get("/", response_model=List[InspecaoRead])
def listar_todas_inspecoes(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Lista todas as inspeções (paginação básica)"""
    return db.query(Inspecao).offset(skip).limit(limit).all()


# ====================== ITEM TEMPLATES ======================

@router.post("/item-templates", response_model=ItemInspecaoTemplateRead, status_code=201)
def criar_item_template(
    template_in: ItemInspecaoTemplateCreate, 
    db: Session = Depends(get_db)
):
    """Cria um novo item de checklist (template)"""
    db_template = ItemInspecaoTemplate(**template_in.model_dump())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


@router.get("/item-templates/tipo/{tipo_ativo_id}", response_model=List[ItemInspecaoTemplateRead])
def listar_templates_por_tipo(
    tipo_ativo_id: int, 
    db: Session = Depends(get_db)
):
    """Lista todos os templates de um tipo de ativo específico"""
    templates = db.query(ItemInspecaoTemplate)\
                  .filter(
                      ItemInspecaoTemplate.id_tipo_ativo == tipo_ativo_id,
                      ItemInspecaoTemplate.ativo == True
                  )\
                  .all()
    return templates


@router.get("/item-templates", response_model=List[ItemInspecaoTemplateRead])
def listar_todos_templates(db: Session = Depends(get_db)):
    """Lista todos os templates ativos do sistema"""
    return db.query(ItemInspecaoTemplate)\
              .filter(ItemInspecaoTemplate.ativo == True)\
              .all()