from sqlalchemy import Column, Integer, String, Date
from sqlalchemy import DECIMAL, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

# =========================================================
# ATIVO
# =========================================================

class Ativo(Base):
    __tablename__ = "ativo"

    id_ativo = Column(Integer, primary_key=True, index=True)

    id_subestacao = Column(
        Integer,
        ForeignKey("subestacao.id_subestacao"),
        nullable=False
    )

    id_tipo_ativo = Column(
        Integer,
        ForeignKey("tipo_ativo.id_tipo_ativo"),
        nullable=False
    )

    codigo_ativo = Column(String(50), nullable=False)
    fabricante = Column(String(100))
    modelo = Column(String(100))
    especie = Column(String(100))
    numero_serie = Column(String(100))
    tensao_nominal_kv = Column(DECIMAL(6, 2))
    data_instalacao = Column(Date)
    status = Column(String(30), default="OPERANTE")
    vao = Column(String(50))
    fase = Column(String(50))


    subestacao = relationship("Subestacao", back_populates="ativos")
    tipo_ativo = relationship("TipoAtivo", back_populates="ativos")
    ordens = relationship("OrdemServico", back_populates="ativo")
    inspecoes = relationship("Inspecao", back_populates="ativo")


