import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


class CriticidadeProblema(str, enum.Enum):
    BAIXA = "BAIXA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    CRITICA = "CRITICA"


class DetectabilidadeProblema(str, enum.Enum):
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAIXA = "BAIXA"


class TipoAcao(str, enum.Enum):
    INSPECAO = "INSPECAO"
    ENSAIO = "ENSAIO"
    CORRECAO = "CORRECAO"
    SUBSTITUICAO = "SUBSTITUICAO"
    MONITORAMENTO = "MONITORAMENTO"
    INVESTIGACAO = "INVESTIGACAO"


class ProblemaTipico(Base):
    __tablename__ = "problema_tipico"
    __table_args__ = (
        UniqueConstraint("id_tipo_ativo", "titulo", name="uq_problema_tipo_titulo"),
        Index("ix_problema_filtros", "sistema", "categoria", "criticidade_padrao", "ativo"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id_problema = Column(Integer, primary_key=True, autoincrement=True)
    id_tipo_ativo = Column(Integer, ForeignKey("tipo_ativo.id_tipo_ativo", ondelete="RESTRICT"), nullable=False, index=True)
    sistema = Column(String(50), nullable=False, index=True)
    categoria = Column(String(50), nullable=False, index=True)
    titulo = Column(String(150), nullable=False)
    descricao = Column(Text)
    criticidade_padrao = Column(Enum(CriticidadeProblema), nullable=False, index=True)
    modo_falha = Column(Text)
    efeito_falha = Column(Text)
    detectabilidade = Column(Enum(DetectabilidadeProblema))
    especialidade = Column(String(100), index=True)
    requer_desligamento = Column(Boolean, nullable=False, default=False)
    ativo = Column(Boolean, nullable=False, default=True, index=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    atualizado_em = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    tipo_ativo = relationship("TipoAtivo", back_populates="problemas_tipicos")
    sintomas = relationship("SintomaProblema", cascade="all, delete-orphan", back_populates="problema", order_by="SintomaProblema.id")
    causas = relationship("CausaProblema", cascade="all, delete-orphan", back_populates="problema", order_by="CausaProblema.id")
    acoes_recomendadas = relationship("AcaoRecomendada", cascade="all, delete-orphan", back_populates="problema", order_by="AcaoRecomendada.id")
    metodos_deteccao = relationship("MetodoDeteccaoProblema", cascade="all, delete-orphan", back_populates="problema", order_by="MetodoDeteccaoProblema.id")
    ocorrencias_ss = relationship("SSProblema", back_populates="problema")


class SintomaProblema(Base):
    __tablename__ = "sintoma_problema"
    id = Column(Integer, primary_key=True)
    id_problema = Column(Integer, ForeignKey("problema_tipico.id_problema", ondelete="CASCADE"), nullable=False, index=True)
    sintoma = Column(String(500), nullable=False)
    problema = relationship("ProblemaTipico", back_populates="sintomas")


class CausaProblema(Base):
    __tablename__ = "causa_problema"
    id = Column(Integer, primary_key=True)
    id_problema = Column(Integer, ForeignKey("problema_tipico.id_problema", ondelete="CASCADE"), nullable=False, index=True)
    causa = Column(String(500), nullable=False)
    problema = relationship("ProblemaTipico", back_populates="causas")


class MetodoDeteccaoProblema(Base):
    __tablename__ = "metodo_deteccao_problema"
    id = Column(Integer, primary_key=True)
    id_problema = Column(Integer, ForeignKey("problema_tipico.id_problema", ondelete="CASCADE"), nullable=False, index=True)
    metodo = Column(String(150), nullable=False)
    problema = relationship("ProblemaTipico", back_populates="metodos_deteccao")


class AcaoRecomendada(Base):
    __tablename__ = "acao_recomendada"
    id = Column(Integer, primary_key=True)
    id_problema = Column(Integer, ForeignKey("problema_tipico.id_problema", ondelete="CASCADE"), nullable=False, index=True)
    tipo_acao = Column(Enum(TipoAcao), nullable=False, default=TipoAcao.INVESTIGACAO)
    descricao = Column(String(500), nullable=False)
    prioridade = Column(String(30))
    prazo_recomendado = Column(String(100))
    problema = relationship("ProblemaTipico", back_populates="acoes_recomendadas")


class SSProblema(Base):
    __tablename__ = "ss_problema"
    __table_args__ = (UniqueConstraint("id_ss", "id_problema", name="uq_ss_problema"),)
    id = Column(Integer, primary_key=True)
    id_ss = Column(Integer, ForeignKey("solicitacao_servico.id", ondelete="CASCADE"), nullable=False, index=True)
    id_problema = Column(Integer, ForeignKey("problema_tipico.id_problema", ondelete="RESTRICT"), nullable=False, index=True)
    observacao = Column(Text)
    criticidade_identificada = Column(Enum(CriticidadeProblema))
    confirmado = Column(Boolean, nullable=False, default=False)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    ss = relationship("SolicitacaoServico", back_populates="problemas")
    problema = relationship("ProblemaTipico", back_populates="ocorrencias_ss")
