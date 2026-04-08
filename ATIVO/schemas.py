from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, Literal, List
from pydantic import ConfigDict

from decimal import Decimal

# ======================================================
# ATIVO
# ======================================================

class AtivoBase(BaseModel):
    id_subestacao: int
    codigo_ativo: str
    id_tipo_ativo: int
    fabricante: Optional[str] = None
    modelo: Optional[str] = None
    especie: Optional[str] = None
    numero_serie: Optional[str] = None
    tensao_nominal_kv: Optional[float] = None
    data_instalacao: Optional[date] = None
    status: Optional[Literal["ATIVO", "INATIVO"]] = "ATIVO"
    vao: Optional[str] = None
    fase: Optional[str] = None





class AtivoCreate(AtivoBase):
    pass

class AtivoResponse(BaseModel):
    id_ativo: int
    id_subestacao: int
    codigo_ativo: str
    id_tipo_ativo: int
    numero_serie: Optional[str] = None
    fabricante: Optional[str] = None
    modelo: Optional[str] = None
    tensao_nominal_kv: Optional[Decimal] = None
    data_instalacao: Optional[date] = None
    status: str
    vao: Optional[str] = None
    fase: Optional[str] = None

    class Config:
        orm_mode = True

