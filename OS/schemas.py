
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Literal

# ======================================================
# ORDEM DE SERVIÇO
# ======================================================

class OrdemServicoCreate(BaseModel):
    # ================= IDENTIFICAÇÃO =================
    numero_os: Optional[str] = None
    numero_si: Optional[str] = None
    numero_ss: Optional[str] = None

    id_subestacao: Optional[int] = None
    id_ativo: Optional[int] = None
    id_plano_manutencao: Optional[int] = None
    id_plano_item: Optional[int] = None
    id_plano_execucao: Optional[int] = None
    origem: Optional[str] = None

    especie: Optional[str] = None
    codigo_ativo: Optional[str] = None
    numero_apr: Optional[str] = None

    # ================= LOCALIZAÇÃO =================
    instalacao: Optional[str] = None
    localizacao: Optional[str] = None
    complemento: Optional[str] = None

    # ================= DESCRIÇÃO =================
    origens: Optional[str] = None
    defeito: Optional[str] = None
    esquema_servicos: Optional[str] = None
    descricao_servicos: Optional[str] = None
    observacoes: Optional[str] = None

    # ================= CAUSAS =================
    causa_primaria: Optional[str] = None
    causa_secundaria: Optional[str] = None

    # ================= CONTROLE =================
    prioridade: Optional[str] = "NIVEL_3"
    responsavel: Optional[str] = None
    responsavel_manutencao: Optional[str] = None
    responsavel_operacao: Optional[str] = None

    emissor: Optional[str] = None
    substituto: Optional[str] = None

    centro_custos: Optional[str] = None
    status: Optional[str] = "ABERTA"

    # ================= DATAS =================
    data_abertura_ss: Optional[datetime] = None
    data_inicio_programado: Optional[datetime] = None
    data_fim_programado: Optional[datetime] = None

    data_inicio_execucao: Optional[datetime] = None
    data_fim_execucao: Optional[datetime] = None


class OrdemServicoCreate(OrdemServicoCreate):
    pass


class OrdemServicoResponse(OrdemServicoCreate):
    id_os: int
    criado_em: Optional[datetime] = None
    id_tipo_ativo: Optional[int] = None
    tipo_ativo: Optional[str] = None
    codigo_ativo: Optional[str] = None
    fase: Optional[str] = None

    class Config:
        from_attributes = True
        
class OrdemServicoUpdate(BaseModel):
    numero_os: Optional[str]
    numero_si: Optional[str]
    numero_ss: Optional[str] = None

    id_subestacao: Optional[int]
    id_ativo: Optional[int]
    id_plano_manutencao: Optional[int] = None
    id_plano_item: Optional[int] = None
    id_plano_execucao: Optional[int] = None
    origem: Optional[str] = None

    especie: Optional[str]
    numero_apr: Optional[str]

    instalacao: Optional[str]
    localizacao: Optional[str]
    complemento: Optional[str]

    origens: Optional[str]
    defeito: Optional[str]
    esquema_servicos: Optional[str]

    prioridade: Optional[str]
    responsavel: Optional[str]
    responsavel_manutencao: Optional[str] = None
    responsavel_operacao: Optional[str] = None
    substituto: Optional[str]
    emissor: Optional[str]

    data_inicio_programado: Optional[datetime]
    data_fim_programado: Optional[datetime]

    descricao_servicos: Optional[str]
    observacoes: Optional[str]

    causa_primaria: Optional[str]
    causa_secundaria: Optional[str]

    data_abertura_ss: Optional[datetime]
    data_inicio_execucao: Optional[datetime]
    data_fim_execucao: Optional[datetime]

    centro_custos: Optional[str]
    status: Optional[str]



class OrdemServicoCreateLote(BaseModel):
    id_subestacao: int
    id_tipo_ativo: Optional[int] = None
    codigo_ativo: Optional[str] = None
    incluir_reserva: bool = False

    numero_si: Optional[str] = None
    numero_os: Optional[str] = None

    numero_apr: Optional[str] = None
    instalacao: Optional[str] = None
    localizacao: Optional[str] = None
    complemento: Optional[str] = None
    emissor: Optional[str] = None

    origens: Optional[str] = None
    defeito: Optional[str] = None
    esquema_servicos: Optional[str] = None
    especie: Optional[str] = None

    causa_primaria: Optional[str] = None
    causa_secundaria: Optional[str] = None

    prioridade: str = "NIVEL_3"
    responsavel: Optional[str] = None
    responsavel_manutencao: Optional[str] = None
    responsavel_operacao: Optional[str] = None
    substituto: Optional[str] = None

    data_abertura_ss: Optional[datetime] = None
    data_inicio_programado: Optional[datetime] = None
    data_fim_programado: Optional[datetime] = None

    data_abertura_ss: Optional[datetime]
    data_inicio_execucao: Optional[datetime]
    data_fim_execucao: Optional[datetime]

    descricao_servicos: Optional[str] = None
    observacoes: Optional[str] = None
    centro_custos: str = "RIALMA TRANSMISSORA V"
    status: str = "ABERTA"


class BaixaOSLoteTipoAtivo(BaseModel):
    id_tipo_ativo: int
    id_subestacao: Optional[int] = None
    bays: Optional[list[str]] = None
    status_origem: Optional[list[str]] = None
    status_destino: str = "ENCERRADA"
    data_inicio_execucao: datetime
    data_fim_execucao: Optional[datetime] = None
    incremento_minutos_por_fase: int = 0
    responsavel_manutencao: Optional[str] = None
    responsavel_operacao: Optional[str] = None
    derivar_responsaveis: bool = True
    observacao_baixa: Optional[str] = None


class BaixaOSLoteItemResponse(BaseModel):
    id_os: int
    numero_os: str
    codigo_ativo: Optional[str] = None
    bay: Optional[str] = None
    fase: Optional[str] = None
    status: Optional[str] = None
    data_inicio_execucao: Optional[datetime] = None
    data_fim_execucao: Optional[datetime] = None
    responsavel_manutencao: Optional[str] = None
    responsavel_operacao: Optional[str] = None


class BaixaOSLoteResponse(BaseModel):
    mensagem: str
    total: int
    por_bay: dict[str, int]
    ordens: list[BaixaOSLoteItemResponse]


class GerarOsPlanosRequest(BaseModel):
    data_simulacao: Optional[datetime] = None
    simular: bool = False
