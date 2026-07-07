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

    @property
    def sigla(self):
        siglas_por_id = {1: "BJD", 2: "GOR", 3: "JAB"}
        if self.id_subestacao in siglas_por_id:
            return siglas_por_id[self.id_subestacao]

        nome = (self.nome or "").strip()
        if not nome:
            return None

        partes = [parte for parte in nome.replace("-", " ").split() if parte]
        return "".join(parte[0] for parte in partes[:3]).upper()

    ativos = relationship("Ativo", back_populates="subestacao")
    ordens = relationship("OrdemServico", back_populates="subestacao")
    solicitacao_intervencao = relationship("solicitacao_intervencao", back_populates="subestacao")





