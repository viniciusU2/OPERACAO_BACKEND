from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class RelatorioManutencaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_relatorio_manutencao: int
    id_subestacao: int
    id_tipo_ativo: int
    periodicidade: str
    data_referencia: date
    observacao: str | None
    texto_introducao: str | None
    corpo_tecnico_json: str | None
    numero_os: str | None
    numero_apr: str | None
    periodo_capa: str | None
    concessao: str | None
    hora_inicio: str | None
    hora_fim: str | None
    temperatura_inicio: str | None
    temperatura_fim: str | None
    frequencia_inicio: str | None
    frequencia_fim: str | None
    tensao_inicio: str | None
    tensao_fim: str | None
    nome_arquivo_original: str
    tamanho_bytes: int
    quantidade_fotos: int
    status: str
    erro_processamento: str | None
    id_usuario_envio: int
    id_usuario_edicao: int | None
    emissor: str | None
    editado_por: str | None
    criado_em: datetime
    atualizado_em: datetime


class RelatorioManutencaoPaginadoResponse(BaseModel):
    items: list[RelatorioManutencaoResponse]
    total: int
    page: int
    page_size: int


class CorpoTecnicoImportacao(BaseModel):
    nome: str
    funcao: str


class RelatorioDeInspecoesRequest(BaseModel):
    """Dados da capa para gerar o relatorio a partir das inspecoes."""

    ids_inspecao: list[int]
    observacao: str | None = None
    texto_introducao: str | None = None
    corpo_tecnico: list[CorpoTecnicoImportacao]
    numero_os: str | None = None
    numero_apr: str | None = None
    periodo_capa: str | None = None
    concessao: str | None = None
    data_referencia: date | None = None
    hora_inicio: str
    hora_fim: str
    temperatura_inicio: str
    temperatura_fim: str
    frequencia_inicio: str
    frequencia_fim: str
    tensao_inicio: str
    tensao_fim: str





