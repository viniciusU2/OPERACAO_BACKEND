# models/inspecao_models.py

import enum
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, ForeignKey, Text,
    DECIMAL, Boolean, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum

from database import Base
from pydantic import BaseModel, ConfigDict


# ====================== CONFIG PADRÃO MYSQL 🔥 ======================
MYSQL_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_uca1400_ai_ci"
}


# ====================== ENUMS ======================
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


# ====================== MODELS ======================

class ItemInspecaoTemplate(Base):
    __tablename__ = "item_inspecao_template"
    __table_args__ = MYSQL_ARGS

    id_item_template = Column(Integer, primary_key=True, autoincrement=True)

    id_tipo_ativo = Column(
        Integer,
        ForeignKey("tipo_ativo.id_tipo_ativo", ondelete="CASCADE"),
        nullable=False
    )

    nome_item = Column(String(200), nullable=False)
    descricao = Column(Text, nullable=True)

    periodicidade = Column(
        SQLEnum(PeriodicidadeEnum, name="periodicidade_enum"),
        nullable=False
    )

    unidade = Column(String(30), nullable=True)
    valor_referencia = Column(DECIMAL(12, 4), nullable=True)
    tolerancia = Column(DECIMAL(12, 4), nullable=True)

    ativo = Column(Boolean, default=True)

    tipo_ativo = relationship("TipoAtivo", back_populates="itens_template")


# --------------------------------------------------

class Inspecao(Base):
    __tablename__ = "inspecao"
    __table_args__ = MYSQL_ARGS

    id_inspecao = Column(Integer, primary_key=True, autoincrement=True)

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

    data_inspecao = Column(DateTime, default=datetime.utcnow, nullable=False)
    data_proxima_inspecao = Column(Date, nullable=True)

    periodicidade = Column(
        SQLEnum(PeriodicidadeEnum, name="periodicidade_enum"),
        nullable=False
    )

    responsavel = Column(String(100), nullable=True)
    observacao_geral = Column(Text, default="")

    status_geral = Column(
        SQLEnum(StatusItemEnum, name="status_item_enum"),
        default=StatusItemEnum.NA
    )

    ativo = relationship("Ativo", back_populates="inspecoes")
    ordem_servico = relationship("OrdemServico", back_populates="inspecao")

    resultados = relationship(
        "ResultadoItemInspecao",
        back_populates="inspecao",
        cascade="all, delete-orphan"
    )


# --------------------------------------------------

class ResultadoItemInspecao(Base):
    __tablename__ = "resultado_item_inspecao"
    __table_args__ = (
        UniqueConstraint('id_inspecao', 'id_item_template', name='uq_inspecao_item'),
        *[MYSQL_ARGS]
    )

    id_resultado = Column(Integer, primary_key=True, autoincrement=True)

    id_inspecao = Column(
        Integer,
        ForeignKey("inspecao.id_inspecao", ondelete="CASCADE"),
        nullable=False
    )

    id_item_template = Column(
        Integer,
        ForeignKey("item_inspecao_template.id_item_template", ondelete="RESTRICT"),
        nullable=False
    )

    valor_medido = Column(DECIMAL(12, 4), nullable=True)

    status_item = Column(
        SQLEnum(StatusItemEnum, name="status_item_enum"),
        nullable=False
    )

    observacao_item = Column(Text, nullable=True)

    inspecao = relationship("Inspecao", back_populates="resultados")
    item_template = relationship("ItemInspecaoTemplate")


# ====================== SCHEMAS ======================

class ResultadoItemCreate(BaseModel):
    id_item_template: int
    valor_medido: Optional[Decimal] = None
    status_item: StatusItemEnum
    observacao_item: Optional[str] = None


class InspecaoCreate(BaseModel):
    id_ativo: int
    id_os: Optional[int] = None
    data_inspecao: Optional[datetime] = None
    data_proxima_inspecao: Optional[date] = None
    periodicidade: PeriodicidadeEnum
    responsavel: Optional[str] = None
    observacao_geral: Optional[str] = ""

    resultados: List[ResultadoItemCreate]


class InspecaoRead(BaseModel):
    id_inspecao: int
    id_ativo: int
    id_os: Optional[int] = None
    data_inspecao: datetime
    data_proxima_inspecao: Optional[date] = None
    periodicidade: PeriodicidadeEnum
    responsavel: Optional[str] = None
    observacao_geral: Optional[str] = ""
    status_geral: StatusItemEnum

    model_config = ConfigDict(from_attributes=True)


class ResultadoItemInspecaoRead(BaseModel):
    id_resultado: int
    id_item_template: int
    valor_medido: Optional[Decimal] = None
    status_item: StatusItemEnum
    observacao_item: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InspecaoReadFull(InspecaoRead):
    resultados: List[ResultadoItemInspecaoRead]

    model_config = ConfigDict(from_attributes=True)


InspecaoReadFull.model_rebuild()