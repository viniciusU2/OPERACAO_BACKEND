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
    bay: Optional[str] = None
    fase: Optional[str] = None
    codigo_linha: Optional[str] = None
    estrutura_operacional: Optional[str] = None
    vao_vante_m: Optional[float] = None
    sentido: Optional[str] = None
    tipo_estrutura: Optional[str] = None





class AtivoCreate(AtivoBase):
    pass


class SubestacaoAtivoResponse(BaseModel):
    id_subestacao: int
    nome: str
    sigla: Optional[str] = None

    class Config:
        orm_mode = True


class TipoAtivoAtivoResponse(BaseModel):
    id_tipo_ativo: int
    nome: str

    class Config:
        orm_mode = True


class AtivoResponse(BaseModel):
    id_ativo: int
    id_subestacao: int
    codigo_ativo: str
    id_tipo_ativo: int
    numero_serie: Optional[str] = None
    fabricante: Optional[str] = None
    modelo: Optional[str] = None
    especie: Optional[str] = None
    tensao_nominal_kv: Optional[Decimal] = None
    data_instalacao: Optional[date] = None
    status: str
    bay: Optional[str] = None
    fase: Optional[str] = None
    codigo_linha: Optional[str] = None
    estrutura_operacional: Optional[str] = None
    vao_vante_m: Optional[Decimal] = None
    sentido: Optional[str] = None
    tipo_estrutura: Optional[str] = None
    subestacao: Optional[SubestacaoAtivoResponse] = None
    tipo_ativo: Optional[TipoAtivoAtivoResponse] = None

    class Config:
        orm_mode = True

