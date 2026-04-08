from typing import List
from fastapi import APIRouter, Depends, HTTPException
from models import familias_models
from pymysql import IntegrityError
from sqlalchemy.orm import Session
from database import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from familias import schemas

router = APIRouter(prefix="", tags=["Instalação"])


# ---------------- TIPO ATIVO ----------------

@router.post("/tipo-ativo", response_model=schemas.TipoAtivoOut)
def criar_tipo_ativo(
    tipo: schemas.TipoAtivoCreate,
    db: Session = Depends(get_db)
):
    novo = familias_models.TipoAtivo(**tipo.dict())
    db.add(novo)

    try:
        db.commit()
        db.refresh(novo)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Tipo de ativo já existe"
        )

    return novo


@router.get("/tipo-ativo", response_model=List[schemas.TipoAtivoOut])
def listar_tipos_ativos(db: Session = Depends(get_db)):
    return db.query(familias_models.TipoAtivo).all()


@router.put("/tipo-ativo/{id_tipo}", response_model=schemas.TipoAtivoOut)
def atualizar_tipo_ativo(
    id_tipo: int,
    dados: schemas.TipoAtivoCreate,
    db: Session = Depends(get_db)
):
    tipo = db.query(familias_models.TipoAtivo).filter(
        familias_models.TipoAtivo.id_tipo_ativo == id_tipo
    ).first()

    if not tipo:
        raise HTTPException(404, "Tipo não encontrado")

    tipo.nome = dados.nome

    db.commit()
    db.refresh(tipo)
    return tipo


@router.delete("/tipo-ativo/{id_tipo}")
def deletar_tipo_ativo(
    id_tipo: int,
    db: Session = Depends(get_db)
):
    tipo = db.query(familias_models.TipoAtivo).filter(
        familias_models.TipoAtivo.id_tipo_ativo == id_tipo
    ).first()

    if not tipo:
        raise HTTPException(404, "Tipo não encontrado")

    db.delete(tipo)
    db.commit()

    return {"mensagem": "Tipo deletado com sucesso"}
# ---------------- PLANO MANUTENÇÃO ----------------



# -------- Tipo Ativo --------
@router.post("/tipo-ativo", response_model=schemas.TipoAtivoOut)
def criar_tipo(tipo: schemas.TipoAtivoCreate, db: Session = Depends(get_db)):
    db_tipo = familias_models.TipoAtivo(**tipo.model_dump())
    db.add(db_tipo)
    db.commit()
    db.refresh(db_tipo)
    return db_tipo


@router.get("/tipo-ativo", response_model=list[schemas.TipoAtivoOut])
def listar_tipo(db: Session = Depends(get_db)):
    return db.query(familias_models.TipoAtivo).all()




