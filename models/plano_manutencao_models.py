import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, ForeignKey, Text,
    DECIMAL, Boolean, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum

from database import Base


MYSQL_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_uca1400_ai_ci"
}


# ================= ENUMS =================
class PeriodicidadeEnum(str, enum.Enum):
    SEMANAL = "SEMANAL"
    MENSAL = "MENSAL"
    BIMESTRAL = "BIMESTRAL"
    TRIMESTRAL = "TRIMESTRAL"
    SEMESTRAL = "SEMESTRAL"
    TRES_ANOS = "3_ANOS"
    CINCO_ANOS = "5_ANOS"
    SEIS_ANOS = "6_ANOS"


class StatusItemEnum(str, enum.Enum):
    OK = "OK"
    NOK = "NOK"
    NA = "NA"


# ================= PLANO ITEM =================
class PlanoItem(Base):
    __tablename__ = "plano_item"
    __table_args__ = MYSQL_ARGS

    id_plano_item = Column(Integer, primary_key=True)

    id_plano_manutencao = Column(
        Integer,
        ForeignKey("plano_manutencao.id_plano_manutencao", ondelete="CASCADE"),
        nullable=False
    )

    id_ativo = Column(
        Integer,
        ForeignKey("ativo.id_ativo", ondelete="SET NULL"),
        nullable=True
    )

    nome_item = Column(String(200), nullable=False)
    descricao = Column(Text)

    periodicidade = Column(
        SQLEnum(PeriodicidadeEnum, name="periodicidade_enum_plano_item"),
        nullable=False
    )

    unidade = Column(String(30))
    valor_referencia = Column(DECIMAL(12, 4))
    tolerancia = Column(DECIMAL(12, 4))

    data_inicio = Column(Date)
    intervalo = Column(Integer, default=1)
    antecedencia = Column(Integer, default=0)

    ordem = Column(Integer, default=1)
  

    # RELATIONSHIPS
    plano = relationship("PlanoManutencao", back_populates="itens")

    ativo = relationship("Ativo", back_populates="plano_items")

    inspecoes = relationship(
        "ResultadoItemInspecao",
        back_populates="plano_item"
    )

    execucoes = relationship(
        "PlanoExecucao",
        back_populates="plano_item",
        cascade="all, delete-orphan"
    )


# ================= PLANO =================
class PlanoManutencao(Base):
    __tablename__ = "plano_manutencao"
    __table_args__ = MYSQL_ARGS

    id_plano_manutencao = Column(Integer, primary_key=True)

    id_tipo_ativo = Column(
        Integer,
        ForeignKey("tipo_ativo.id_tipo_ativo", ondelete="CASCADE"),
        nullable=False
    )

    descricao_geral = Column(Text, default="")
    materiais_previstos = Column(Text, default="")
    procedimentos_instrucoes = Column(Text, default="")
    requisitos_de_seguranca = Column(Text, default="")
    observacao_geral = Column(Text, default="")

    tipo_ativo = relationship("TipoAtivo", back_populates="planos_manutencao")

    itens = relationship(
        "PlanoItem",
        back_populates="plano",
        cascade="all, delete-orphan"
    )


# ================= EXECUÇÃO =================
class PlanoExecucao(Base):
    __tablename__ = "plano_execucao"
    __table_args__ = (
        Index("idx_execucao_proxima", "proxima_execucao"),
        MYSQL_ARGS
    )

    id_execucao = Column(Integer, primary_key=True)

    id_plano_item = Column(
        Integer,
        ForeignKey("plano_item.id_plano_item", ondelete="CASCADE"),
        nullable=False
    )

    id_ativo = Column(
        Integer,
        ForeignKey("ativo.id_ativo", ondelete="CASCADE"),
        nullable=False
    )

    id_os = Column(
        Integer,
        ForeignKey("ordem_servico.id_os", ondelete="SET NULL"),
        nullable=True
    )

    ultima_execucao = Column(DateTime)
    proxima_execucao = Column(DateTime, nullable=False)

   

    plano_item = relationship("PlanoItem", back_populates="execucoes")

    ativo = relationship("Ativo", back_populates="execucoes")


# ================= INSPEÇÃO =================
class Inspecao(Base):
    __tablename__ = "inspecao"
    __table_args__ = MYSQL_ARGS

    id_inspecao = Column(Integer, primary_key=True)

    id_ativo = Column(
        Integer,
        ForeignKey("ativo.id_ativo", ondelete="CASCADE"),
        nullable=False
    )

    id_os = Column(
        Integer,
        ForeignKey("ordem_servico.id_os", ondelete="SET NULL"),
        nullable=True
    )

    data_inspecao = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    data_proxima_inspecao = Column(Date)

    periodicidade = Column(
        SQLEnum(PeriodicidadeEnum, name="periodicidade_enum_inspecao"),
        nullable=False
    )

    responsavel = Column(String(100))
    observacao_geral = Column(Text, default="")

    status_geral = Column(
        SQLEnum(StatusItemEnum, name="status_item_enum_inspecao"),
        default=StatusItemEnum.NA
    )

    ativo = relationship("Ativo", back_populates="inspecoes")

    ordem_servico = relationship("OrdemServico", back_populates="inspecao")

    resultados = relationship(
        "ResultadoItemInspecao",
        back_populates="inspecao",
        cascade="all, delete-orphan"
    )

    @property
    def codigo_ativo(self):
        return self.ativo.codigo_ativo if self.ativo else None

    @property
    def fase(self):
        return self.ativo.fase if self.ativo else None

    @property
    def vao(self):
        return self.ativo.vao if self.ativo else None

    @property
    def fabricante(self):
        return self.ativo.fabricante if self.ativo else None

    @property
    def modelo(self):
        return self.ativo.modelo if self.ativo else None

    @property
    def instalacao(self):
        return self.ativo.subestacao.nome if self.ativo and self.ativo.subestacao else None

    @property
    def tipo_ativo(self):
        return self.ativo.tipo_ativo.nome if self.ativo and self.ativo.tipo_ativo else None

    @property
    def numero_os(self):
        return self.ordem_servico.numero_os if self.ordem_servico else None

    @property
    def numero_apr(self):
        return self.ordem_servico.numero_apr if self.ordem_servico else None


# ================= RESULTADO =================
class ResultadoItemInspecao(Base):
    __tablename__ = "resultado_item_inspecao"
    __table_args__ = (
        UniqueConstraint('id_inspecao', 'id_plano_item'),
        MYSQL_ARGS
    )

    id_resultado = Column(Integer, primary_key=True)

    id_inspecao = Column(
        Integer,
        ForeignKey("inspecao.id_inspecao", ondelete="CASCADE"),
        nullable=False
    )

    id_item_template = Column(Integer, nullable=True)

    id_plano_item = Column(
        Integer,
        ForeignKey("plano_item.id_plano_item", ondelete="RESTRICT"),
        nullable=True
    )

    nome_item = Column(String(200), nullable=False)

    valor_referencia = Column(DECIMAL(12, 4))
    tolerancia = Column(DECIMAL(12, 4))
    valor_medido = Column(DECIMAL(12, 4))

    status_item = Column(
        SQLEnum(StatusItemEnum, name="status_item_enum_resultado"),
        nullable=False
    )

    observacao_item = Column(Text)

    inspecao = relationship("Inspecao", back_populates="resultados")

    plano_item = relationship("PlanoItem", back_populates="inspecoes")

    @property
    def unidade(self):
        return self.plano_item.unidade if self.plano_item else None
