from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from models.problemas_tipicos_models import CriticidadeProblema, DetectabilidadeProblema, TipoAcao

class SintomaIn(BaseModel): sintoma: str = Field(min_length=2, max_length=500)
class CausaIn(BaseModel): causa: str = Field(min_length=2, max_length=500)
class MetodoIn(BaseModel): metodo: str = Field(min_length=2, max_length=150)
class AcaoIn(BaseModel):
    tipo_acao: TipoAcao = TipoAcao.INVESTIGACAO
    descricao: str = Field(min_length=2, max_length=500)
    prioridade: Optional[str] = None
    prazo_recomendado: Optional[str] = None

class ProblemaBase(BaseModel):
    id_tipo_ativo: int
    sistema: str = Field(min_length=2, max_length=50)
    categoria: str = Field(min_length=2, max_length=50)
    titulo: str = Field(min_length=3, max_length=150)
    descricao: Optional[str] = None
    criticidade_padrao: CriticidadeProblema
    modo_falha: Optional[str] = None
    efeito_falha: Optional[str] = None
    detectabilidade: Optional[DetectabilidadeProblema] = None
    especialidade: Optional[str] = None
    requer_desligamento: bool = False
    ativo: bool = True
    sintomas: list[SintomaIn] = []
    causas: list[CausaIn] = []
    acoes_recomendadas: list[AcaoIn] = []
    metodos_deteccao: list[MetodoIn] = []

class ProblemaCreate(ProblemaBase): pass
class ProblemaUpdate(ProblemaBase): pass
class ProblemaResponse(ProblemaBase):
    id_problema: int
    criado_em: datetime
    atualizado_em: datetime
    model_config = ConfigDict(from_attributes=True)

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
