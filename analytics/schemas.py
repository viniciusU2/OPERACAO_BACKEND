from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CategoriaRecurso = Literal[
    "MAO_DE_OBRA", "INSTRUMENTO", "VEICULO", "EQUIPAMENTO", "MATERIAL", "EPI", "EPC"
]


class RecursoBase(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    categoria: CategoriaRecurso
    unidade: str = Field(min_length=1, max_length=30)
    quantidade_disponivel: Decimal | None = Field(default=None, ge=0)
    controla_disponibilidade: bool = False
    ativo: bool = True
    observacao: str | None = None


class RecursoCreate(RecursoBase):
    pass


class RecursoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=160)
    categoria: CategoriaRecurso | None = None
    unidade: str | None = Field(default=None, min_length=1, max_length=30)
    quantidade_disponivel: Decimal | None = Field(default=None, ge=0)
    controla_disponibilidade: bool | None = None
    ativo: bool | None = None
    observacao: str | None = None


class RecursoRead(RecursoBase):
    model_config = ConfigDict(from_attributes=True)
    id_recurso: int
    criado_em: datetime
    atualizado_em: datetime


class PlanoRecursoInput(BaseModel):
    id_recurso: int
    quantidade: Decimal = Field(gt=0)
    horas_por_recurso: Decimal | None = Field(default=None, gt=0)
    consumivel: bool = False
    obrigatorio: bool = True
    observacao: str | None = None


class PlanoEquipeInput(BaseModel):
    id_equipe: int
    prioridade: int = Field(default=1, gt=0)
    observacao: str | None = None


class PlanoPlanejamentoUpdate(BaseModel):
    duracao_estimada_horas: Decimal | None = Field(default=None, gt=0)
    observacao: str | None = None
    recursos: list[PlanoRecursoInput] = Field(default_factory=list)
    equipes: list[PlanoEquipeInput] = Field(default_factory=list)


class EquipeCapacidadeCreate(BaseModel):
    data_inicio: date
    data_fim: date
    horas_disponiveis: Decimal = Field(ge=0)
    fonte: str | None = Field(default=None, max_length=80)
    observacao: str | None = None

    @model_validator(mode="after")
    def validar_periodo(self):
        if self.data_fim < self.data_inicio:
            raise ValueError("data_fim deve ser maior ou igual a data_inicio")
        return self


class EquipeCapacidadeRead(EquipeCapacidadeCreate):
    model_config = ConfigDict(from_attributes=True)
    id_equipe_capacidade: int
    id_equipe: int
    criado_em: datetime
    atualizado_em: datetime
