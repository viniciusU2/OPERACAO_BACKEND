from sqlalchemy import Column, Integer, String, Date, DECIMAL, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


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
    bay = Column(String(50))
    fase = Column(String(50))
    codigo_linha = Column(String(100))
    estrutura_operacional = Column(String(50))
    vao_vante_m = Column(DECIMAL(10, 3))
    sentido = Column(String(50))
    tipo_estrutura = Column(String(100))

    # RELATIONSHIPS
    subestacao = relationship("Subestacao", back_populates="ativos")
    tipo_ativo = relationship("TipoAtivo", back_populates="ativos")

    ordens = relationship("OrdemServico", back_populates="ativo")

    inspecoes = relationship(
        "Inspecao",
        back_populates="ativo",
        cascade="all, delete-orphan"
    )

    plano_items = relationship(
        "PlanoItem",
        back_populates="ativo",
        cascade="all, delete-orphan"
    )

    execucoes = relationship(
        "PlanoExecucao",
        back_populates="ativo",
        cascade="all, delete-orphan"
    )
