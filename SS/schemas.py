from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


# BASE
class SolicitacaoServicoBase(BaseModel):

    numero_ss: str

    data_hora_solicitacao: Optional[datetime] = None
    data_hora_abertura: Optional[datetime] = None
    data_hora_limite: Optional[datetime] = None

    solicitante: Optional[str] = None
    matricula: Optional[str] = None
    funcao: Optional[str] = None

    telefone: Optional[str] = None
    email: Optional[str] = None
    orgao: Optional[str] = None

    instalacao: Optional[str] = None
    localizacao: Optional[str] = None
    complemento: Optional[str] = None

    id_ativo: int

    esquema_servico: Optional[str] = None
    centro_custo: Optional[str] = None

    causa: Optional[str] = None
    causa_secundaria: Optional[str] = None

    equipe: Optional[str] = None

    descricao_problema: Optional[str] = None

    prioridade: Optional[str] = None

    status: Optional[str] = None


# CREATE
class SolicitacaoServicoCreate(SolicitacaoServicoBase):
    pass


# UPDATE (todos opcionais)
class SolicitacaoServicoUpdate(BaseModel):

    numero_ss: Optional[str] = None

    data_hora_solicitacao: Optional[datetime] = None
    data_hora_abertura: Optional[datetime] = None
    data_hora_limite: Optional[datetime] = None

    solicitante: Optional[str] = None
    matricula: Optional[str] = None
    funcao: Optional[str] = None

    telefone: Optional[str] = None
    email: Optional[str] = None
    orgao: Optional[str] = None

    instalacao: Optional[str] = None
    localizacao: Optional[str] = None
    complemento: Optional[str] = None

    id_ativo: Optional[int] = None

    esquema_servico: Optional[str] = None
    centro_custo: Optional[str] = None

    causa: Optional[str] = None
    causa_secundaria: Optional[str] = None

    equipe: Optional[str] = None

    descricao_problema: Optional[str] = None

    prioridade: Optional[str] = None

    status: Optional[str] = None


# RESPONSE
class SolicitacaoServicoResponse(SolicitacaoServicoBase):

    id: int

    model_config = ConfigDict(from_attributes=True)