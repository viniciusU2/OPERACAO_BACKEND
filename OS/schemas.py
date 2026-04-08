
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, Literal

# ======================================================
# ORDEM DE SERVIÇO
# ======================================================

class OrdemServicoCreate(BaseModel):
    # ================= IDENTIFICAÇÃO =================
    numero_os: str = Field(..., min_length=1)
    numero_si: Optional[str] = None

    id_subestacao: Optional[int] = Field(None, gt=0)
    id_ativo: Optional[int] = Field(None, gt=0)

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
    prioridade: Optional[Literal["BAIXA", "MEDIA", "ALTA"]] = "MEDIA"
    responsavel: Optional[str] = None
    responsavel_manutencao: Optional[str] = None
    responsavel_operacao: Optional[str] = None

    emissor: Optional[str] = None
    substituto: Optional[str] = None

    centro_custos: Optional[str] = None
    status: Literal[
        "ABERTA",
        "PROGRAMADA",
        "EM_EXECUCAO",
        "ENCERRADA"
    ] = "ABERTA"

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

    class Config:
        from_attributes = True
        
class OrdemServicoUpdate(BaseModel):
    numero_os: Optional[str]
    numero_si: Optional[str]

    id_subestacao: Optional[int]
    id_ativo: Optional[int]

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
    id_tipo_ativo: str                     # EAT, SPCS, TELECON, etc.

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

    prioridade: str = "MEDIA"
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