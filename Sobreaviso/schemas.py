from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class EquipeSobreavisoBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    ativo: bool = True


class EquipeSobreavisoCreate(EquipeSobreavisoBase):
    pass


class EquipeSobreavisoUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    ativo: Optional[bool] = None


class EquipeSobreavisoResponse(EquipeSobreavisoBase):
    id_equipe: int
    criado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class ColaboradorSobreavisoBase(BaseModel):
    nome: str
    matricula: str
    email: str
    cargo: Optional[str] = None
    telefone: Optional[str] = None
    id_equipe: int
    id_subestacao: Optional[int] = None
    id_usuario: Optional[int] = None
    ativo: bool = True


class ColaboradorSobreavisoCreate(ColaboradorSobreavisoBase):
    pass


class ColaboradorSobreavisoUpdate(BaseModel):
    nome: Optional[str] = None
    matricula: Optional[str] = None
    email: Optional[str] = None
    cargo: Optional[str] = None
    telefone: Optional[str] = None
    id_equipe: Optional[int] = None
    id_subestacao: Optional[int] = None
    id_usuario: Optional[int] = None
    ativo: Optional[bool] = None


class ColaboradorSobreavisoResponse(ColaboradorSobreavisoBase):
    id_colaborador: int
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class SobreavisoBase(BaseModel):
    id_colaborador: int
    inicio: datetime
    fim: datetime
    status: str = "PENDENTE"
    origem: str = "GESTOR"
    justificativa: Optional[str] = None

    @model_validator(mode="after")
    def validar_periodo(self):
        if self.fim <= self.inicio:
            raise ValueError("O fim deve ser maior que o inicio")
        return self


class SobreavisoCreate(SobreavisoBase):
    pass


class SobreavisoUpdate(BaseModel):
    id_colaborador: Optional[int] = None
    inicio: Optional[datetime] = None
    fim: Optional[datetime] = None
    status: Optional[str] = None
    origem: Optional[str] = None
    justificativa: Optional[str] = None

    @model_validator(mode="after")
    def validar_periodo(self):
        if self.inicio and self.fim and self.fim <= self.inicio:
            raise ValueError("O fim deve ser maior que o inicio")
        return self


class SobreavisoResponse(SobreavisoBase):
    id_sobreaviso: int
    total_horas: Decimal
    criado_por: Optional[int] = None
    atualizado_por: Optional[int] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None
    colaborador: Optional[ColaboradorSobreavisoResponse] = None

    class Config:
        from_attributes = True


class SolicitacaoAjusteCreate(BaseModel):
    inicio_solicitado: datetime
    fim_solicitado: datetime
    justificativa: str = Field(min_length=1)

    @model_validator(mode="after")
    def validar_periodo(self):
        if self.fim_solicitado <= self.inicio_solicitado:
            raise ValueError("O fim solicitado deve ser maior que o inicio solicitado")
        return self


class SolicitacaoAjusteResponse(SolicitacaoAjusteCreate):
    id_solicitacao: int
    id_sobreaviso: int
    solicitado_por: Optional[int] = None
    status: str
    avaliado_por: Optional[int] = None
    avaliado_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class HistoricoSobreavisoResponse(BaseModel):
    id_historico: int
    entidade: str
    entidade_id: int
    acao: str
    dados_anteriores: Optional[str] = None
    dados_novos: Optional[str] = None
    justificativa: Optional[str] = None
    alterado_por: Optional[int] = None
    criado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResumoSobreavisoResponse(BaseModel):
    total_horas: Decimal
    total_aprovadas: Decimal
    pendentes: int
    planejados: int
    colaboradores: int
