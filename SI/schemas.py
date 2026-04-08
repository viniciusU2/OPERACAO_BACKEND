from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SIBase(BaseModel):
    numero_si: str
    numero_sgi: Optional[str] = None
    id_subestacao: Optional[int] = None
    id_ativo: Optional[int] = None
    especie: Optional[str] = None
    numero_apr: Optional[str] = None
    tipo: Optional[str] = None
    documentos_referencia: Optional[str] = None

    data_inicio_preriodo_total: Optional[datetime] = None
    data_fim_preriodo_total: Optional[datetime] = None
    data_inicio_preriodo_manutencao: Optional[datetime] = None
    data_fim_preriodo_manutencao: Optional[datetime] = None

    justificativa: Optional[str] = None
    responsavel: Optional[str] = None
    substituto: Optional[str] = None

    aproveitamento: Optional[str] = "NÃO"
    inclusao_servico: Optional[str] = "NÃO"

    orgaos: Optional[str] = None
    tipo_progrmacao: Optional[str] = "DIARIO"
    tipo_progrmacao_diario: Optional[str] = None

    descricao_servicos: Optional[str] = None
    observacoes: Optional[str] = None
    cabo_aterramento: Optional[str] = None
    risco_desligamento: Optional[str] = None
    condicoes_climaticas: Optional[str] = None
    execucao_periodo_noturno: Optional[str] = None

    # manutenção
    responsavel_ons_manutencao: Optional[str] = None
    responsavel_cot_manutencao: Optional[str] = None
    responsavel_se_manutencao: Optional[str] = None
    emissor: Optional[str]

    
    responsavel_data_ons_manutencao: Optional[datetime] = None
    responsavel_data_cot_manutencao: Optional[datetime] = None
    responsavel_data_se_manutencao: Optional[datetime] = None
    status_manutencao: Optional[str] = "ABERTA"

    # operação
    responsavel_ons_operacao: Optional[str] = None
    responsavel_cot_operacao: Optional[str] = None
    responsavel_se_operacao: Optional[str] = None


    responsavel_data_ons_operacao: Optional[datetime] = None
    responsavel_data_cot_operacao: Optional[datetime] = None
    responsavel_data_se_operacao: Optional[datetime] = None

    status_operacao: Optional[str] = "ABERTA"


class SICreate(SIBase):
    pass


class SIUpdate(BaseModel):
    # tudo opcional pra edição
    numero_si: Optional[str] = None
    numero_sgi: Optional[str] = None
    id_subestacao: Optional[int] = None
    id_ativo: Optional[int] = None
    especie: Optional[str] = None
    numero_apr: Optional[str] = None
    tipo: Optional[str] = None
    documentos_referencia: Optional[str] = None
    descricao_servicos: Optional[str] = None
    observacoes: Optional[str] = None
    emissor: Optional[str]


class SIResponse(SIBase):
    id_si: int
    criado_em: datetime

    class Config:
        from_attributes = True