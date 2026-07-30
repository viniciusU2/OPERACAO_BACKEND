
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class FrenteServico(Base):
    __tablename__ = "frente_servico"

    id_frente_servico = Column(Integer, primary_key=True, index=True)
    codigo_frente = Column(String(50), unique=True, nullable=False)
    origem = Column(String(50), nullable=False)
    id_subestacao = Column(Integer, ForeignKey("subestacao.id_subestacao"), nullable=True)
    sigla_subestacao = Column(String(20), nullable=True)
    descricao_atividade = Column(Text, nullable=True)
    periodo_inicio = Column(DateTime, nullable=True)
    periodo_fim = Column(DateTime, nullable=True)
    responsavel = Column(String(100), nullable=True)
    substituto = Column(String(100), nullable=True)
    status = Column(String(30), default="ABERTA")
    criado_por = Column(Text, nullable=True)
    editado_por = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    apr = relationship("APR", back_populates="frente_servico", uselist=False)
    ordens = relationship("FrenteServicoOS", back_populates="frente_servico", cascade="all, delete-orphan")


class APR(Base):
    __tablename__ = "apr"

    id_apr = Column(Integer, primary_key=True, index=True)
    id_frente_servico = Column(Integer, ForeignKey("frente_servico.id_frente_servico"), nullable=False, index=True)
    numero_apr = Column(String(50), unique=True, nullable=False)
    caminho_arquivo = Column(Text, nullable=True)
    modelo_versao = Column(String(50), default="MODELO_APR.xlsm")
    status = Column(String(30), default="GERADA")
    gerada_por = Column(Text, nullable=True)
    editado_por = Column(Text, nullable=True)
    gerada_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    frente_servico = relationship("FrenteServico", back_populates="apr")
    historicos = relationship("APRHistorico", back_populates="apr", cascade="all, delete-orphan")


class FrenteServicoOS(Base):
    __tablename__ = "frente_servico_os"

    id = Column(Integer, primary_key=True, index=True)
    id_frente_servico = Column(Integer, ForeignKey("frente_servico.id_frente_servico"), nullable=False, index=True)
    id_os = Column(Integer, ForeignKey("ordem_servico.id_os"), nullable=False, index=True)
    ordem = Column(Integer, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    frente_servico = relationship("FrenteServico", back_populates="ordens")


class APRHistorico(Base):
    __tablename__ = "apr_historico"

    id_historico = Column(Integer, primary_key=True, index=True)
    id_apr = Column(Integer, ForeignKey("apr.id_apr"), nullable=False, index=True)
    acao = Column(String(40), nullable=False)
    usuario = Column(Text, nullable=True)
    data_hora = Column(DateTime, default=datetime.utcnow)
    observacao = Column(Text, nullable=True)

    apr = relationship("APR", back_populates="historicos")
