from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional

from database import get_db
from models.livro_registro import LivroRegistro
from models.OS_models import OrdemServico

from LR.schemas  import LivroRegistroCreate, LivroRegistroUpdate, LivroRegistroResponse

router = APIRouter(
    prefix="/livro",
    tags=["Livro de Registro"]
)

@router.post("/", response_model=LivroRegistroResponse)
def criar_registro(
    dados: LivroRegistroCreate,
    db: Session = Depends(get_db)
):
    novo = LivroRegistro(**dados.dict())

    db.add(novo)
    db.commit()
    db.refresh(novo)

    return novo

@router.get("/", response_model=List[LivroRegistroResponse])
def listar_registros(
    data: Optional[str] = None,
    id_os: Optional[int] = None,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(LivroRegistro)

    if data:
        data_inicio = datetime.strptime(data, "%Y-%m-%d")
        data_fim = data_inicio + timedelta(days=1)

        query = query.filter(
            LivroRegistro.data_registro_inicio >= data_inicio,
            LivroRegistro.data_registro_inicio < data_fim
        )

    if id_os:
        query = query.filter(LivroRegistro.id_os == id_os)

    if tipo:
        query = query.filter(LivroRegistro.tipo == tipo)

    return query.order_by(LivroRegistro.data_registro_inicio.desc()).all()

@router.get("/{id}", response_model=LivroRegistroResponse)
def buscar_registro(id: int, db: Session = Depends(get_db)):
    registro = db.query(LivroRegistro).filter(LivroRegistro.id == id).first()

    if not registro:
        raise HTTPException(status_code=404, detail="Registro não encontrado")

    return registro


@router.put("/{id}", response_model=LivroRegistroResponse)
def atualizar_registro(
    id: int,
    dados: LivroRegistroUpdate,
    db: Session = Depends(get_db)
):
    registro = db.query(LivroRegistro).filter(LivroRegistro.id == id).first()

    if not registro:
        raise HTTPException(status_code=404, detail="Registro não encontrado")

    for key, value in dados.dict(exclude_unset=True).items():
        setattr(registro, key, value)

    db.commit()
    db.refresh(registro)

    return registro

@router.post("/iniciar-os/{id_os}")
def iniciar_os(
    id_os: int,
    usuario: str,
    db: Session = Depends(get_db)
):
    os = db.query(OrdemServico).filter(OrdemServico.id_os == id_os).first()

    if not os:
        raise HTTPException(status_code=404, detail="OS não encontrada")

    registro = LivroRegistro(
        tipo="inicio_os",
        descricao=f"Início da OS {id_os}",
        id_os=id_os,
        usuario=usuario,
        data_registro_inicio=datetime.utcnow()
    )

    db.add(registro)
    db.commit()

    return {"message": "OS iniciada"}

@router.post("/finalizar-os/{id_os}")
def finalizar_os(
    id_os: int,
    usuario: str,
    db: Session = Depends(get_db)
):
    os = db.query(OrdemServico).filter(OrdemServico.id_os == id_os).first()

    if not os:
        raise HTTPException(status_code=404, detail="OS não encontrada")

    registro = LivroRegistro(
        tipo="termino_os",
        descricao=f"Término da OS {id_os}",
        id_os=id_os,
        usuario=usuario,
        data_registro_inicio=datetime.utcnow(),
        data_registro_fim=datetime.utcnow()
    )

    db.add(registro)
    db.commit()

    return {"message": "OS finalizada"}