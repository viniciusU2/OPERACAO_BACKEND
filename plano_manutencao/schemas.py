# schemas/inspecao.py
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

from models.plano_manutencao_models import PeriodicidadeEnum, StatusItemEnum   # Import dos Enums


# ====================== ITEM TEMPLATE (Checklist) ======================

class ItemInspecaoTemplateBase(BaseModel):
    id_tipo_ativo: int
    nome_item: str
    descricao: Optional[str] = None
    periodicidade: PeriodicidadeEnum
    unidade: Optional[str] = None
    valor_referencia: Optional[Decimal] = None
    tolerancia: Optional[Decimal] = None
    ativo: bool = True


class ItemInspecaoTemplateCreate(ItemInspecaoTemplateBase):
    pass


class ItemInspecaoTemplateRead(ItemInspecaoTemplateBase):
    id_item_template: int

    model_config = ConfigDict(from_attributes=True)


# ====================== INSPEÇÃO ======================

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


class InspecaoReadFull(InspecaoRead):
    """Usado quando queremos ver a inspeção com todos os resultados detalhados"""
    resultados: List["ResultadoItemInspecaoRead"]


# ====================== RESULTADO DO ITEM ======================

class ResultadoItemInspecaoRead(BaseModel):
    id_resultado: int
    id_item_template: int
    valor_medido: Optional[Decimal] = None
    status_item: StatusItemEnum
    observacao_item: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ====================== Para evitar erro de forward reference ======================
InspecaoReadFull.model_rebuild()