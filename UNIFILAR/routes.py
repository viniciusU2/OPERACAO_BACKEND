"""Rotas HTTP do modulo Unifilar (/unifilar).

Leitura liberada para qualquer usuario autenticado; escrita apenas
admin e mantenedor. A subestacao deve existir (guia do diagrama).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user, require_roles
from database import get_db
from models.auth_models import Usuario

from . import schemas, service

router = APIRouter(prefix="/unifilar", tags=["Unifilar"])

ESCRITA = require_roles("admin", "mantenedor")


@router.get("/tipos", response_model=list[schemas.TipoComponenteSaida])
def listar_tipos(
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    """Catalogo de tipos de componente (espelho do catalogo do editor)."""
    return service.catalogo(db)


@router.get("/diagrama/{id_subestacao}", response_model=schemas.DiagramaSaida)
def carregar_diagrama(
    id_subestacao: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    """Diagrama salvo da subestacao (vazio quando nunca salvo)."""
    return service.carregar_diagrama(db, id_subestacao)


@router.put("/diagrama/{id_subestacao}", response_model=schemas.DiagramaSaida)
def salvar_diagrama(
    id_subestacao: int,
    diagrama: schemas.DiagramaEntrada,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    """Substitui o diagrama salvo da subestacao pelo estado enviado."""
    return service.salvar_diagrama(db, id_subestacao, diagrama, usuario.id)
