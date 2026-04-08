from typing import List
from fastapi import APIRouter, Depends, HTTPException
from models import instalacao_models
from pymysql import IntegrityError
from sqlalchemy.orm import Session
from database import get_db
from models.OS_models import OrdemServico
from OS.schemas import OrdemServicoCreate, OrdemServicoResponse, OrdemServicoUpdate
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from Instalacao import schemas



router = APIRouter(prefix="", tags=["Instalação"])

# ---------------- SUBESTAÇÃO ----------------
@router.post("/subestacao")
def criar_subestacao(sub: schemas.SubestacaoCreate, db: Session = Depends(get_db)):
    nova = instalacao_models.Subestacao(**sub.dict())
    db.add(nova)
    db.commit()
    return nova

@router.get("/subestacao", response_model=List[schemas.SubestacaoResponse])
def listar_subestacoes(db: Session = Depends(get_db)):
    return db.query(instalacao_models.Subestacao).all()

@router.get("/subestacao/ativas", response_model=list[schemas.SubestacaoResponse])
def listar_subestacoes_ativas(db: Session = Depends(get_db)):
    return (
        db.query(instalacao_models.Subestacao)
        .filter(instalacao_models.Subestacao.status == "ATIVA")
        .all()
    )


@router.delete("/subestacao/{id_subestacao}")
def deletar_subestcao(id_subestacao: int, db: Session = Depends(get_db)):

    os = db.query(instalacao_models.Subestacao).filter(
        instalacao_models.Subestacao.id_subestacao== id_subestacao
    ).first()

    if not os:
        raise HTTPException(status_code=404, detail="SE não encontrada")

    db.delete(os)
    db.commit()

    return {"message": "SE excluída com sucesso"}