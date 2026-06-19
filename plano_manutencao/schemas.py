# schemas/inspecao.py
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

from familias.schemas import TipoAtivoOut
from models.plano_manutencao_models import PeriodicidadeEnum, StatusItemEnum   # Import dos Enums
from pydantic import BaseModel, ConfigDict, Field


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
    ficha_inspecao_url: Optional[str] = None
    observacao_geral: Optional[str] = ""

    resultados: List[ResultadoItemCreate]


class InspecaoRead(BaseModel):
    id_inspecao: int
    id_ativo: int
    id_subestacao: Optional[int] = None
    id_os: Optional[int] = None
    data_inspecao: datetime
    data_proxima_inspecao: Optional[date] = None
    periodicidade: PeriodicidadeEnum
    responsavel: Optional[str] = None
    ficha_inspecao_url: Optional[str] = None
    observacao_geral: Optional[str] = ""
    status_geral: StatusItemEnum
    codigo_ativo: Optional[str] = None
    fase: Optional[str] = None
    vao: Optional[str] = None
    instalacao: Optional[str] = None
    tipo_ativo: Optional[str] = None
    numero_os: Optional[str] = None
    numero_apr: Optional[str] = None

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





# ====================== SCHEMAS ======================

# --- PlanoItem ---
class PlanoItemBase(BaseModel):
    nome_item: str
    descricao: Optional[str] = None
    periodicidade: PeriodicidadeEnum
    unidade: Optional[str] = None
    valor_referencia: Optional[Decimal] = None
    tolerancia: Optional[Decimal] = None
    data_inicio: Optional[date] = None
    intervalo: int = 1
    antecedencia: int = 0
    ordem: int = 1
  


class PlanoItemCreate(PlanoItemBase):
    pass


class PlanoItemRead(PlanoItemBase):
    id_plano_item: int
    id_plano_manutencao: int
    id_ativo: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# --- PlanoManutencao ---
class PlanoManutencaoCreate(BaseModel):
    id_tipo_ativo: int
    descricao_geral: Optional[str] = ""
    materiais_previstos: Optional[str] = ""
    procedimentos_instrucoes: Optional[str] = ""
    requisitos_de_seguranca: Optional[str] = ""
    observacao_geral: Optional[str] = ""
    itens: List[PlanoItemCreate] = Field(default_factory=list)


class PlanoManutencaoRead(BaseModel):
    id_plano_manutencao: int
    id_tipo_ativo: int
    descricao_geral: str
    materiais_previstos: str
    procedimentos_instrucoes: str
    requisitos_de_seguranca: str
    observacao_geral: str

    model_config = ConfigDict(from_attributes=True)


class PlanoManutencaoReadFull(PlanoManutencaoRead):
    itens: List[PlanoItemRead] = Field(default_factory=list)
    tipo_ativo: Optional["TipoAtivoOut"] = None

    model_config = ConfigDict(from_attributes=True)


# --- PlanoExecucao ---
class PlanoExecucaoBase(BaseModel):
    id_plano_item: int
    id_ativo: int
    ultima_execucao: Optional[datetime] = None
    proxima_execucao: datetime
    ativo: bool = True


class PlanoExecucaoCreate(PlanoExecucaoBase):
    pass


class PlanoExecucaoRead(PlanoExecucaoBase):
    id_execucao: int

    model_config = ConfigDict(from_attributes=True)


class PlanoExecucaoUpdate(BaseModel):
    ultima_execucao: Optional[datetime] = None
    proxima_execucao: datetime


class PlanoExecucaoPlanilhaRead(BaseModel):
    id_execucao: int
    id_plano_item: int
    id_plano_manutencao: int
    id_ativo: int
    nome_item: str
    periodicidade: PeriodicidadeEnum
    intervalo: int
    antecedencia: int
    plano_descricao: Optional[str] = ""
    codigo_ativo: str
    instalacao: Optional[str] = None
    tipo_ativo: Optional[str] = None
    vao: Optional[str] = None
    fase: Optional[str] = None
    ultima_execucao: Optional[datetime] = None
    proxima_execucao: datetime


# --- Inspecao ---
class ResultadoItemCreate(BaseModel):
    id_plano_item: int
    valor_medido: Optional[Decimal] = None
    status_item: StatusItemEnum
    observacao_item: Optional[str] = None
    foto: Optional[str] = None


class InspecaoCreate(BaseModel):
    id_ativo: int
    id_os: Optional[int] = None
    data_inspecao: Optional[datetime] = None
    data_proxima_inspecao: Optional[date] = None
    periodicidade: PeriodicidadeEnum
    responsavel: Optional[str] = None
    ficha_inspecao_url: Optional[str] = None
    observacao_geral: Optional[str] = ""
    resultados: List[ResultadoItemCreate] = Field(default_factory=list)


class InspecaoUpdate(BaseModel):
    data_inspecao: Optional[datetime] = None
    data_proxima_inspecao: Optional[date] = None
    periodicidade: Optional[PeriodicidadeEnum] = None
    responsavel: Optional[str] = None
    ficha_inspecao_url: Optional[str] = None
    observacao_geral: Optional[str] = None
    resultados: Optional[List[ResultadoItemCreate]] = None


class ResultadoItemInspecaoRead(BaseModel):
    id_resultado: int
    id_plano_item: Optional[int] = None
    id_item_template: Optional[int] = None
    nome_item: Optional[str] = None
    valor_referencia: Optional[Decimal] = None
    tolerancia: Optional[Decimal] = None
    valor_medido: Optional[Decimal] = None
    unidade: Optional[str] = None
    status_item: StatusItemEnum
    observacao_item: Optional[str] = None
    foto: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InspecaoRead(BaseModel):
    id_inspecao: int
    id_ativo: int
    id_os: Optional[int] = None
    data_inspecao: datetime
    data_proxima_inspecao: Optional[date] = None
    periodicidade: PeriodicidadeEnum
    responsavel: Optional[str] = None
    ficha_inspecao_url: Optional[str] = None
    observacao_geral: Optional[str] = ""
    status_geral: StatusItemEnum
    id_subestacao: Optional[int] = None
    codigo_ativo: Optional[str] = None
    fase: Optional[str] = None
    vao: Optional[str] = None
    fabricante: Optional[str] = None
    modelo: Optional[str] = None
    instalacao: Optional[str] = None
    tipo_ativo: Optional[str] = None
    numero_os: Optional[str] = None
    numero_apr: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InspecaoReadFull(InspecaoRead):
    resultados: List[ResultadoItemInspecaoRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ====================== REBUILD ======================
PlanoManutencaoReadFull.model_rebuild()
InspecaoReadFull.model_rebuild()


# ====================== Para evitar erro de forward reference ======================
InspecaoReadFull.model_rebuild()
