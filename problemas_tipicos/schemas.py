from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from models.problemas_tipicos_models import (
    CondicaoIntervencao,
    CriticidadeProblema,
    DetectabilidadeProblema,
    OrigemRegistroProblema,
    RiscoOperacional,
    StatusValidacaoProblema,
    TipoAcao,
)

class SintomaIn(BaseModel): sintoma: str = Field(min_length=2, max_length=500)
class CausaIn(BaseModel): causa: str = Field(min_length=2, max_length=500)
class MetodoIn(BaseModel): metodo: str = Field(min_length=2, max_length=400)
class AlarmeIn(BaseModel): alarme: str = Field(min_length=2, max_length=300)
class PalavraChaveIn(BaseModel): palavra_chave: str = Field(min_length=2, max_length=80)
class InstrumentoIn(BaseModel): instrumento: str = Field(min_length=2, max_length=150)
class AcaoIn(BaseModel):
    tipo_acao: TipoAcao = TipoAcao.INVESTIGACAO
    descricao: str = Field(min_length=2, max_length=500)
    prioridade: Optional[str] = None
    prazo_recomendado: Optional[str] = None

class ProblemaBase(BaseModel):
    # Chave natural. Opcional na entrada para não quebrar clientes antigos:
    # quando omitida, o service gera um código único.
    codigo: Optional[str] = Field(default=None, max_length=80)
    id_tipo_ativo: int
    sistema: str = Field(min_length=2, max_length=50)
    categoria: str = Field(min_length=2, max_length=50)
    titulo: str = Field(min_length=3, max_length=150)
    descricao: Optional[str] = None
    criticidade_padrao: CriticidadeProblema
    modo_falha: Optional[str] = None
    efeito_falha: Optional[str] = None
    risco_operacional: Optional[RiscoOperacional] = None
    detectabilidade: Optional[DetectabilidadeProblema] = None
    especialidade: Optional[str] = None
    requer_desligamento: bool = False
    condicao_intervencao: Optional[CondicaoIntervencao] = None
    requer_equipe_especializada: bool = False
    alerta_seguranca: Optional[str] = None
    referencias_tecnicas: Optional[str] = None
    status_validacao: StatusValidacaoProblema = StatusValidacaoProblema.PENDENTE
    origem_registro: OrigemRegistroProblema = OrigemRegistroProblema.REFERENCIA_TECNICA
    validado_por: Optional[str] = None
    validado_em: Optional[datetime] = None
    ativo: bool = True
    sintomas: list[SintomaIn] = []
    causas: list[CausaIn] = []
    acoes_recomendadas: list[AcaoIn] = []
    metodos_deteccao: list[MetodoIn] = []
    alarmes: list[AlarmeIn] = []
    palavras_chave: list[PalavraChaveIn] = []
    instrumentos: list[InstrumentoIn] = []

class ProblemaCreate(ProblemaBase): pass
class ProblemaUpdate(ProblemaBase): pass
class ProblemaResponse(ProblemaBase):
    id_problema: int
    criado_em: datetime
    atualizado_em: datetime
    model_config = ConfigDict(from_attributes=True)

class OpcoesProblema(BaseModel):
    sistemas: list[str]
    categorias: list[str]
    especialidades: list[str]
    status_validacao: list[str]
    riscos_operacionais: list[str]

class ContagemCategoria(BaseModel):
    categoria: str
    total: int

class EstatisticasProblema(BaseModel):
    total: int
    por_categoria: list[ContagemCategoria]
    por_criticidade: dict[str, int]
    por_status_validacao: dict[str, int]

class SSProblemaIn(BaseModel):
    id_problema: int
    observacao: Optional[str] = None
    criticidade_identificada: Optional[CriticidadeProblema] = None
    confirmado: bool = False

class SSProblemaResponse(SSProblemaIn):
    id: int
    criado_em: datetime
    problema: ProblemaResponse
    model_config = ConfigDict(from_attributes=True)
