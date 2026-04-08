from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, Literal, List
from pydantic import ConfigDict
from decimal import Decimal



class TipoAtivoBase(BaseModel):
    nome: str
    descricao: Optional[str] = None


class TipoAtivoCreate(TipoAtivoBase):
    pass


class TipoAtivoUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None


class TipoAtivoOut(TipoAtivoBase):
    id_tipo_ativo: int
    nome: str

    class Config:
        from_attributes = True

