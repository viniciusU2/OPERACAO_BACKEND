from fastapi import APIRouter, Depends, HTTPException
from pymysql import IntegrityError
from sqlalchemy.orm import Session
from database import get_db
from ATIVO  import schemas
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.Ativo import Ativo
from typing import List
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import pandas as pd


router = APIRouter(prefix="", tags=["ATIVO"])


# ---------------- ATIVO ----------------
@router.post("/ativo", response_model=schemas.AtivoResponse)
def criar_ativo(
    ativo: schemas.AtivoCreate,
    db: Session = Depends(get_db)
):
    novo = Ativo(**ativo.dict())
    db.add(novo)
    db.commit()
    db.refresh(novo)  # 👈 MUITO IMPORTANTE
    return novo
@router.get("/ativo", response_model=List[schemas.AtivoResponse])
def listar_subestacoes(db: Session = Depends(get_db)):
    return db.query(Ativo).all()

@router.get("/ativos/{id_subestacao}")
def listar_ativos(
    id_subestacao: int,
    db: Session = Depends(get_db)
):
    query = db.query(Ativo)

    if id_subestacao:
        query = query.filter(
            Ativo.id_subestacao == id_subestacao
        )

    return query.all()




@router.get("/ativo/{id_ativo}")
def buscar_ativo_por_id(
    id_ativo: int,
    db: Session = Depends(get_db)
):
    ativo = (
        db.query(Ativo)
        .filter(Ativo.id_ativo == id_ativo)
        .first()
    )

    if not ativo:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    return ativo




@router.put("/ativos/{id_ativo}")
def editar_ativo(
    id_ativo: int,
    dados: dict,
    db: Session = Depends(get_db)
):
    ativo_db = (
        db.query(Ativo)
        .filter(Ativo.id_ativo == id_ativo)
        .first()
    )

    if not ativo_db:
        raise HTTPException(
            status_code=404,
            detail="Ordem de Serviço não encontrada"
        )

    # Atualiza apenas os campos enviados
    for campo, valor in dados.items():
        if hasattr(ativo_db, campo):
            setattr(ativo_db, campo, valor)

    try:
        db.commit()
        db.refresh(ativo_db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Número da OS já existe"
        )

    return ativo_db







@router.post("/ativos/importar-xlsx")
async def importar_ativos(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        df = pd.read_excel(file.file)

        # 🔴 Validar colunas obrigatórias
        colunas_obrigatorias = [
            "id_subestacao",
            "id_tipo_ativo",
            "codigo_ativo",
            "vao",
            "fase"
        ]

        for col in colunas_obrigatorias:
            if col not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Coluna obrigatória ausente: {col}"
                )

        ativos = []

        for i, row in df.iterrows():
            # ⚠️ ignorar linhas vazias
            if pd.isna(row["codigo_ativo"]):
                continue

            ativo = Ativo(
                id_subestacao=int(row["id_subestacao"]),
                id_tipo_ativo=int(row["id_tipo_ativo"]),
                codigo_ativo=str(row["codigo_ativo"]),
                vao=str(row["vao"]) if pd.notna(row["vao"]) else None,
                numero_serie=str(row["numero_serie"]) if pd.notna(row["numero_serie"]) else None,
                fabricante=str(row["fabricante"]) if pd.notna(row["fabricante"]) else None,


                fase=str(row["fase"]) if pd.notna(row["fase"]) else None,
                status="OPERANTE"
            )

            ativos.append(ativo)

        # 🚀 inserção em lote (mais rápido)
        db.bulk_save_objects(ativos)
        db.commit()

        return {
            "msg": f"{len(ativos)} ativos importados com sucesso"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
