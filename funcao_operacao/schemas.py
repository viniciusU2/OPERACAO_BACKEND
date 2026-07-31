from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FuncaoOperacaoBase(BaseModel):
    id_subestacao: int
    codigo: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = Field(default=None, max_length=300)


class FuncaoOperacaoCreate(FuncaoOperacaoBase):
    pass


class FuncaoOperacaoUpdate(BaseModel):
    id_subestacao: Optional[int] = None
    codigo: Optional[str] = Field(default=None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(default=None, max_length=300)


class FuncaoOperacaoOut(FuncaoOperacaoBase):
    id_funcao_operacao: int
    subestacao_nome: Optional[str] = None
    quantidade_ativos: int = 0

    model_config = ConfigDict(from_attributes=True)


class FuncaoOperacaoAtivoOut(BaseModel):
    id_ativo: int
    codigo_ativo: str
    fabricante: Optional[str] = None
    modelo: Optional[str] = None
    bay: Optional[str] = None
    fase: Optional[str] = None
    status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
