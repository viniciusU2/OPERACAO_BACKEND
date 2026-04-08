from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, Literal, List
from pydantic import ConfigDict

from decimal import Decimal

# ======================================================
# SUBESTAÇÃO
# ======================================================

class SubestacaoBase(BaseModel):
    nome: str
    tensao_kv: Optional[float] = None
    localizacao: Optional[str] = None
    concessionaria: Optional[str] = None
    status: Optional[Literal["ATIVA", "INATIVA"]] = "ATIVA"


class SubestacaoCreate(SubestacaoBase):
    pass


class SubestacaoResponse(SubestacaoBase):
    id_subestacao: int
    criado_em: Optional[datetime] = None

    class Config:
        from_attributes = True