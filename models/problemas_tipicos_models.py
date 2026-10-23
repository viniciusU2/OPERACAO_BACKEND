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
    PREVENCAO = "PREVENCAO"


class RiscoOperacional(str, enum.Enum):
    BAIXO = "BAIXO"
    MEDIO = "MEDIO"
    ALTO = "ALTO"


class CondicaoIntervencao(str, enum.Enum):
    ENERGIZADO = "ENERGIZADO"
    DESENERGIZADO = "DESENERGIZADO"
    INDIFERENTE = "INDIFERENTE"


class StatusValidacaoProblema(str, enum.Enum):
    """Estágio de curadoria técnica do registro de referência."""

    PENDENTE = "PENDENTE"
    EM_REVISAO = "EM_REVISAO"
    VALIDADO = "VALIDADO"
    REPROVADO = "REPROVADO"


class OrigemRegistroProblema(str, enum.Enum):
    """Distingue conhecimento de referência de ocorrência real registrada."""

    REFERENCIA_TECNICA = "REFERENCIA_TECNICA"
    OCORRENCIA_REAL = "OCORRENCIA_REAL"


class ProblemaTipico(Base):
    __tablename__ = "problema_tipico"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_problema_codigo"),
        UniqueConstraint("id_tipo_ativo", "titulo", name="uq_problema_tipo_titulo"),
        Index("ix_problema_filtros", "sistema", "categoria", "criticidade_padrao", "ativo"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id_problema = Column(Integer, primary_key=True, autoincrement=True)
    # Chave natural estável: permite idempotência da seed e citação do problema.
    codigo = Column(String(80), nullable=False, index=True)
    id_tipo_ativo = Column(Integer, ForeignKey("tipo_ativo.id_tipo_ativo", ondelete="RESTRICT"), nullable=False, index=True)
    sistema = Column(String(50), nullable=False, index=True)
    categoria = Column(String(50), nullable=False, index=True)
    titulo = Column(String(150), nullable=False)
    descricao = Column(Text)
    criticidade_padrao = Column(Enum(CriticidadeProblema), nullable=False, index=True)
    modo_falha = Column(Text)
    efeito_falha = Column(Text)
    risco_operacional = Column(Enum(RiscoOperacional), index=True)
    detectabilidade = Column(Enum(DetectabilidadeProblema))
    especialidade = Column(String(100), index=True)
    requer_desligamento = Column(Boolean, nullable=False, default=False)
    condicao_intervencao = Column(Enum(CondicaoIntervencao))
    requer_equipe_especializada = Column(Boolean, nullable=False, default=False)
    alerta_seguranca = Column(Text)
    referencias_tecnicas = Column(Text)
    status_validacao = Column(
        Enum(StatusValidacaoProblema),
        nullable=False,
        default=StatusValidacaoProblema.PENDENTE,
        index=True,
    )
    origem_registro = Column(
        Enum(OrigemRegistroProblema),
        nullable=False,
        default=OrigemRegistroProblema.REFERENCIA_TECNICA,
        index=True,
    )
    validado_por = Column(String(150))
    validado_em = Column(DateTime)
    ativo = Column(Boolean, nullable=False, default=True, index=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    atualizado_em = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    tipo_ativo = relationship("TipoAtivo", back_populates="problemas_tipicos")
    sintomas = relationship("SintomaProblema", cascade="all, delete-orphan", back_populates="problema", order_by="SintomaProblema.id")
    causas = relationship("CausaProblema", cascade="all, delete-orphan", back_populates="problema", order_by="CausaProblema.id")
    acoes_recomendadas = relationship("AcaoRecomendada", cascade="all, delete-orphan", back_populates="problema", order_by="AcaoRecomendada.id")
    metodos_deteccao = relationship("MetodoDeteccaoProblema", cascade="all, delete-orphan", back_populates="problema", order_by="MetodoDeteccaoProblema.id")
    alarmes = relationship("AlarmeProblema", cascade="all, delete-orphan", back_populates="problema", order_by="AlarmeProblema.id")
    palavras_chave = relationship("PalavraChaveProblema", cascade="all, delete-orphan", back_populates="problema", order_by="PalavraChaveProblema.id")
    instrumentos = relationship("InstrumentoProblema", cascade="all, delete-orphan", back_populates="problema", order_by="InstrumentoProblema.id")
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
    metodo = Column(String(400), nullable=False)
    problema = relationship("ProblemaTipico", back_populates="metodos_deteccao")


class AlarmeProblema(Base):
    __tablename__ = "alarme_problema"
    id = Column(Integer, primary_key=True)
    id_problema = Column(Integer, ForeignKey("problema_tipico.id_problema", ondelete="CASCADE"), nullable=False, index=True)
    alarme = Column(String(300), nullable=False)
    problema = relationship("ProblemaTipico", back_populates="alarmes")


class PalavraChaveProblema(Base):
    __tablename__ = "palavra_chave_problema"
    id = Column(Integer, primary_key=True)
    id_problema = Column(Integer, ForeignKey("problema_tipico.id_problema", ondelete="CASCADE"), nullable=False, index=True)
    palavra_chave = Column(String(80), nullable=False, index=True)
    problema = relationship("ProblemaTipico", back_populates="palavras_chave")


class InstrumentoProblema(Base):
    __tablename__ = "instrumento_problema"
    id = Column(Integer, primary_key=True)
    id_problema = Column(Integer, ForeignKey("problema_tipico.id_problema", ondelete="CASCADE"), nullable=False, index=True)
    instrumento = Column(String(150), nullable=False)
    problema = relationship("ProblemaTipico", back_populates="instrumentos")


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
