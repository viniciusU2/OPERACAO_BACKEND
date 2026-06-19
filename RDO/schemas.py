from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel


class RdoConfiguracaoBase(BaseModel):
    periodo_inicio: time
    periodo_fim: time
    subestacao: Optional[str] = None
    equipamento: str
    estado: str
    ordem: int = 0


class RdoConfiguracaoCreate(RdoConfiguracaoBase):
    pass


class RdoConfiguracaoUpdate(BaseModel):
    periodo_inicio: Optional[time] = None
    periodo_fim: Optional[time] = None
    subestacao: Optional[str] = None
    equipamento: Optional[str] = None
    estado: Optional[str] = None
    ordem: Optional[int] = None


class RdoConfiguracaoResponse(RdoConfiguracaoBase):
    id_configuracao: int
    id_rdo: int

    class Config:
        from_attributes = True


class RdoEventoBase(BaseModel):
    categoria: str
    sistema: Optional[str] = None
    subestacao: Optional[str] = None
    hora_inicio: Optional[time] = None
    hora_fim: Optional[time] = None
    titulo: Optional[str] = None
    descricao: str
    status_evento: str = "INFORMATIVO"
    ordem: int = 0


class RdoEventoCreate(RdoEventoBase):
    pass


class RdoEventoUpdate(BaseModel):
    categoria: Optional[str] = None
    sistema: Optional[str] = None
    subestacao: Optional[str] = None
    hora_inicio: Optional[time] = None
    hora_fim: Optional[time] = None
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    status_evento: Optional[str] = None
    ordem: Optional[int] = None


class RdoEventoResponse(RdoEventoBase):
    id_evento: int
    id_rdo: int
    criado_por: Optional[int] = None
    editado_por: Optional[int] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class RdoBase(BaseModel):
    data_rdo: date
    titulo: str = "RDO - RELATORIO DIARIO DA OPERACAO"
    codigo_procedimento: str = "PR-OP.COS.002"
    revisao: str = "00"
    sistema: str = "RIALMA V"
    emissor: str
    arquivo_pdf: Optional[str] = None
    status: str = "RASCUNHO"


class RdoCreate(RdoBase):
    configuracoes: list[RdoConfiguracaoCreate] = []
    eventos: list[RdoEventoCreate] = []


class RdoUpdate(BaseModel):
    data_rdo: Optional[date] = None
    titulo: Optional[str] = None
    codigo_procedimento: Optional[str] = None
    revisao: Optional[str] = None
    sistema: Optional[str] = None
    emissor: Optional[str] = None
    arquivo_pdf: Optional[str] = None
    status: Optional[str] = None


class RdoResponse(RdoBase):
    id_rdo: int
    criado_por: Optional[int] = None
    editado_por: Optional[int] = None
    validado_por: Optional[int] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None
    validado_em: Optional[datetime] = None
    configuracoes: list[RdoConfiguracaoResponse] = []
    eventos: list[RdoEventoResponse] = []

    class Config:
        from_attributes = True


class RdoResumoResponse(RdoBase):
    id_rdo: int
    criado_por: Optional[int] = None
    editado_por: Optional[int] = None
    validado_por: Optional[int] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None
    validado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class RdoHistoricoResponse(BaseModel):
    id_historico: int
    id_rdo: int
    id_usuario: Optional[int] = None
    acao: str
    campo_alterado: Optional[str] = None
    valor_anterior: Optional[str] = None
    valor_novo: Optional[str] = None
    observacao: Optional[str] = None
    criado_em: datetime

    class Config:
        from_attributes = True
