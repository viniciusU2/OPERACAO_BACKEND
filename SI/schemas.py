from pydantic import BaseModel
from typing import Optional, Literal
from datetime import date, datetime


class SIBase(BaseModel):
    numero_si: Optional[str] = None
    numero_sgi: Optional[str] = None
    id_subestacao: Optional[int] = None
    id_ativo: Optional[int] = None
    id_grupo_ativo: Optional[int] = None
    id_funcao_operacao: Optional[int] = None
    escopo_ativo: Optional[Literal["FUNCAO", "GRUPO", "FASE"]] = None
    especie: Optional[str] = None
    numero_os: Optional[str] = None
    numero_apr: Optional[str] = None
    prioridade: Optional[str] = "NIVEL_3"
    natureza: Optional[str] = None
    caracteristica_intervencao: Optional[str] = None
    tipo: Optional[str] = None
    documentos_referencia: Optional[str] = None

    data_inicio_preriodo_total: Optional[datetime] = None
    data_fim_preriodo_total: Optional[datetime] = None
    data_inicio_preriodo_manutencao: Optional[datetime] = None
    data_fim_preriodo_manutencao: Optional[datetime] = None

    justificativa: Optional[str] = None
    responsavel: Optional[str] = None
    substituto: Optional[str] = None

    aproveitamento: Optional[str] = "NÃƒO"
    inclusao_servico: Optional[str] = "NÃƒO"

    acarreta_risco_perdas_multiplas: Optional[str] = "NAO"

    orgaos: Optional[str] = None
    tipo_progrmacao: Optional[str] = "DIARIO"
    tipo_progrmacao_diario: Optional[str] = None

    descricao_servicos: Optional[str] = None
    observacoes: Optional[str] = None
    cabo_aterramento: Optional[str] = None
    risco_desligamento: Optional[str] = None
    condicoes_climaticas: Optional[str] = None
    execucao_periodo_noturno: Optional[str] = None
    postergacao_traz_risco: Optional[str] = "NAO"
    quais_risco_desligamento: Optional[str] = None
    quais_condicoes_climaticas: Optional[str] = None
    quais_execucao_periodo_noturno: Optional[str] = None

    # manutenÃ§Ã£o
    responsavel_ons_manutencao: Optional[str] = None
    responsavel_cot_manutencao: Optional[str] = None
    responsavel_se_manutencao: Optional[str] = None
    emissor: Optional[str] = None
    editado_por: Optional[str] = None
    editado_por: Optional[str] = None

    
    responsavel_data_ons_manutencao: Optional[datetime] = None
    responsavel_data_cot_manutencao: Optional[datetime] = None
    responsavel_data_se_manutencao: Optional[datetime] = None
    status_manutencao: Optional[str] = "ABERTA"

    # operaÃ§Ã£o
    responsavel_ons_operacao: Optional[str] = None
    responsavel_cot_operacao: Optional[str] = None
    responsavel_se_operacao: Optional[str] = None


    tipo_programacao: Optional[str] = None
    dias_excecao: Optional[str] = None
    tempo_retorno: Optional[str] = None
    disponivel: Optional[str] = None


    responsavel_data_ons_operacao: Optional[datetime] = None
    responsavel_data_cot_operacao: Optional[datetime] = None
    responsavel_data_se_operacao: Optional[datetime] = None

    status_operacao: Optional[str] = "ABERTA"


class SICreate(SIBase):
    pass


class SIUpdate(SIBase):
    # tudo opcional pra ediÃ§Ã£o
    numero_si: Optional[str] = None
    numero_sgi: Optional[str] = None
    id_subestacao: Optional[int] = None
    id_ativo: Optional[int] = None
    id_grupo_ativo: Optional[int] = None
    id_funcao_operacao: Optional[int] = None
    escopo_ativo: Optional[Literal["FUNCAO", "GRUPO", "FASE"]] = None
    especie: Optional[str] = None
    numero_os: Optional[str] = None
    numero_apr: Optional[str] = None
    prioridade: Optional[str] = None
    natureza: Optional[str] = None
    caracteristica_intervencao: Optional[str] = None
    tipo: Optional[str] = None
    documentos_referencia: Optional[str] = None
    descricao_servicos: Optional[str] = None
    observacoes: Optional[str] = None
    emissor: Optional[str] = None


class SIResponse(SIBase):
    id_si: int
    criado_em: datetime
    codigo_ativo: Optional[str] = None

    class Config:
        from_attributes = True


class SIPaginadaResponse(BaseModel):
    items: list[SIResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SILiberacaoManutencaoCreate(BaseModel):
    data_utilizacao: Optional[date] = None
    data_hora_liberacao: Optional[datetime] = None
    operador_liberou: Optional[str] = None
    observacoes: Optional[str] = None


class SILiberacaoOperacaoUpdate(BaseModel):
    data_hora_devolucao: Optional[datetime] = None
    operador_recebeu_devolucao: Optional[str] = None
    observacoes: Optional[str] = None


class SILiberacaoCancelarUpdate(BaseModel):
    observacoes: Optional[str] = None


class SILiberacaoResponse(BaseModel):
    id_liberacao: int
    id_si: int
    data_utilizacao: date
    data_hora_liberacao: datetime
    usuario_solicitou_id: Optional[int] = None
    usuario_solicitou: str
    operador_liberou: Optional[str] = None
    data_hora_devolucao: Optional[datetime] = None
    usuario_devolveu_id: Optional[int] = None
    usuario_devolveu: Optional[str] = None
    operador_recebeu_devolucao: Optional[str] = None
    observacoes: Optional[str] = None
    status: str
    criado_em: datetime
    atualizado_em: Optional[datetime] = None

    class Config:
        from_attributes = True

