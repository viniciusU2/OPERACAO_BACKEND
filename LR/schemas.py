
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, model_validator


# =========================
# 🔵 PYDANTIC SCHEMAS
# =========================

class LivroRegistroBase(BaseModel):
    tipo: str
    descricao: str

    id_os: Optional[int] = None
    id_subestacao: Optional[int] = None

    foto: Optional[str] = None
    usuario: str

    data_registro_inicio: Optional[datetime] = None
    data_registro_fim: Optional[datetime] = None


# =========================
# CREATE
# =========================

class LivroRegistroCreate(LivroRegistroBase):

    @model_validator(mode="after")
    def validar_datas(self):
        if self.tipo == "termino_os" and not self.data_registro_fim:
            raise ValueError("data_registro_fim é obrigatória para término de OS")
        return self


# =========================
# UPDATE
# =========================

class LivroRegistroUpdate(BaseModel):
    tipo: Optional[str] = None
    descricao: Optional[str] = None

    id_os: Optional[int] = None
    id_subestacao: Optional[int] = None

    foto: Optional[str] = None

    data_registro_inicio: Optional[datetime] = None
    data_registro_fim: Optional[datetime] = None


# =========================
# RESPONSE
# =========================

class LivroRegistroResponse(LivroRegistroBase):
    id: int
    data_registro_inicio: datetime

    class Config:
        from_attributes = True  # Pydantic v2