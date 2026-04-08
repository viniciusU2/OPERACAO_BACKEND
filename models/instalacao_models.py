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
# SUBESTAÇÃO
# =========================================================

class Subestacao(Base):
    __tablename__ = "subestacao"

    id_subestacao = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    tensao_kv = Column(DECIMAL(6, 2))
    localizacao = Column(String(150))
    concessionaria = Column(String(100))
    status = Column(String(30), default="ATIVA")
    criado_em = Column(DateTime, default=datetime.utcnow)

    ativos = relationship("Ativo", back_populates="subestacao")
    ordens = relationship("OrdemServico", back_populates="subestacao")
    solicitacao_intervencao = relationship("solicitacao_intervencao", back_populates="subestacao")





