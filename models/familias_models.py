

import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    ForeignKey,
    Text,
    DECIMAL,
    Boolean
)

from sqlalchemy.orm import relationship
from sqlalchemy.types import Enum

from database import Base


# =========================================================
# TIPO ATIVO
# =========================================================

class TipoAtivo(Base):
    __tablename__ = "tipo_ativo"
    __table_args__ = {'extend_existing': True}

    id_tipo_ativo = Column(Integer, primary_key=True, index=True)
    nome = Column(String(50), unique=True, nullable=False)
    descricao = Column(String(300))

    ativos = relationship("Ativo", back_populates="tipo_ativo")
    itens_template = relationship("ItemInspecaoTemplate", back_populates="tipo_ativo")
    


   
