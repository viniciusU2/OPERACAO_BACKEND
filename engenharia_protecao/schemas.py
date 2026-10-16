from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


StatusIED = Literal[
    "EM_OPERACAO",
    "SOBRESSALENTE",
    "EM_MANUTENCAO",
    "RETIRADO",
    "DESCARTADO",
]
TipoMovimentacao = Literal["INSTALACAO", "TRANSFERENCIA", "SUBSTITUICAO", "RETIRADA"]


class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class ModeloIEDBase(SchemaBase):
    fabricante: str = Field(min_length=2, max_length=100)
    familia: str | None = Field(default=None, max_length=100)
    modelo: str = Field(min_length=1, max_length=100)
    aplicacao: str | None = Field(default=None, max_length=300)
    descricao: str | None = None
    ativo: bool = True


class ModeloIEDCreate(ModeloIEDBase):
    pass


class ModeloIEDUpdate(SchemaBase):
    fabricante: str | None = Field(default=None, min_length=2, max_length=100)
    familia: str | None = Field(default=None, max_length=100)
    modelo: str | None = Field(default=None, min_length=1, max_length=100)
    aplicacao: str | None = Field(default=None, max_length=300)
    descricao: str | None = None
    ativo: bool | None = None


class ModeloIEDOut(ModeloIEDBase):
    id_modelo_ied: int
    quantidade_ieds: int = 0
    criado_em: datetime
    atualizado_em: datetime


class ModeloIEDLista(SchemaBase):
    total: int
    page: int
    page_size: int
    items: list[ModeloIEDOut]


class IEDBase(SchemaBase):
    tag_operacional: str = Field(min_length=1, max_length=100)
    id_ativo: int = Field(gt=0)
    id_modelo_ied: int = Field(gt=0)
    id_subestacao: int = Field(gt=0)
    id_funcao_operacao: int | None = Field(default=None, gt=0)
    painel_instalacao: str = Field(min_length=1, max_length=150)
    numero_serie: str | None = Field(default=None, max_length=150)
    codigo_produto: str | None = Field(default=None, max_length=150)
    versao_hardware: str | None = Field(default=None, max_length=100)
    versao_firmware: str | None = Field(default=None, max_length=100)
    data_instalacao: date
    status_operacional: StatusIED = "EM_OPERACAO"
    observacoes_tecnicas: str | None = None

    @field_validator("status_operacional", mode="before")
    @classmethod
    def normalizar_status(cls, value):
        return str(value).strip().upper() if value is not None else value


class IEDCreate(IEDBase):
    id_ativos_protegidos: list[int] = Field(default_factory=list)


class IEDUpdate(SchemaBase):
    versao: int = Field(gt=0)
    tag_operacional: str | None = Field(default=None, min_length=1, max_length=100)
    id_modelo_ied: int | None = Field(default=None, gt=0)
    numero_serie: str | None = Field(default=None, max_length=150)
    codigo_produto: str | None = Field(default=None, max_length=150)
    versao_hardware: str | None = Field(default=None, max_length=100)
    status_operacional: StatusIED | None = None
    observacoes_tecnicas: str | None = None
    ativo: bool | None = None


class IEDResumo(SchemaBase):
    id_ied: int
    codigo_uuid: str
    tag_operacional: str
    id_ativo: int
    ativo_codigo: str
    id_modelo_ied: int
    modelo_nome: str
    fabricante: str
    familia: str | None = None
    id_subestacao: int
    subestacao_nome: str
    id_funcao_operacao: int | None = None
    funcao_operacao_codigo: str | None = None
    painel_instalacao: str
    numero_serie: str | None = None
    codigo_produto: str | None = None
    versao_hardware: str | None = None
    versao_firmware: str | None = None
    data_instalacao: date
    status_operacional: StatusIED
    observacoes_tecnicas: str | None = None
    ativo: bool
    versao: int
    quantidade_equipamentos: int = 0
    criado_em: datetime
    atualizado_em: datetime


class IEDLista(SchemaBase):
    total: int
    page: int
    page_size: int
    items: list[IEDResumo]


class IEDRemocaoOut(SchemaBase):
    id_ied: int
    tag_operacional: str
    arquivos_removidos: int


class InstalacaoOut(SchemaBase):
    id_ied_instalacao: int
    id_subestacao: int
    subestacao_nome: str
    id_funcao_operacao: int | None = None
    funcao_operacao_codigo: str | None = None
    painel_instalacao: str
    tipo_movimentacao: TipoMovimentacao
    data_inicio: date
    data_fim: date | None = None
    motivo: str | None = None
    observacoes: str | None = None
    criado_em: datetime


class TransferenciaCreate(SchemaBase):
    id_subestacao: int = Field(gt=0)
    id_funcao_operacao: int | None = Field(default=None, gt=0)
    painel_instalacao: str = Field(min_length=1, max_length=150)
    tipo_movimentacao: Literal["TRANSFERENCIA", "SUBSTITUICAO"] = "TRANSFERENCIA"
    data_inicio: date
    motivo: str = Field(min_length=3, max_length=300)
    observacoes: str | None = None


class ModuloCreate(SchemaBase):
    tipo_modulo: str = Field(min_length=2, max_length=100)
    slot: str | None = Field(default=None, max_length=50)
    codigo_produto: str | None = Field(default=None, max_length=150)
    numero_serie: str | None = Field(default=None, max_length=150)
    versao_hardware: str | None = Field(default=None, max_length=100)
    status_operacional: str = Field(default="INSTALADO", max_length=30)
    data_instalacao: date | None = None
    observacoes: str | None = None


class ModuloOut(ModuloCreate):
    id_ied_modulo: int
    data_retirada: date | None = None
    criado_em: datetime


class FirmwareCreate(SchemaBase):
    versao_firmware: str = Field(min_length=1, max_length=100)
    data_inicio: date
    motivo: str | None = Field(default=None, max_length=300)
    id_os: int | None = Field(default=None, gt=0)
    observacoes: str | None = None


class FirmwareOut(FirmwareCreate):
    id_ied_firmware_historico: int
    data_fim: date | None = None
    criado_em: datetime


class EquipamentoCreate(SchemaBase):
    id_ativo: int = Field(gt=0)
    principal: bool = False
    data_inicio: date
    observacoes: str | None = None


class EquipamentoOut(SchemaBase):
    id_ied_equipamento: int
    id_ativo: int
    codigo_ativo: str
    tipo_ativo_nome: str | None = None
    principal: bool
    data_inicio: date
    data_fim: date | None = None
    observacoes: str | None = None
    criado_em: datetime


class IEDDetalhe(IEDResumo):
    instalacoes: list[InstalacaoOut]
    modulos: list[ModuloOut]
    firmwares: list[FirmwareOut]
    equipamentos: list[EquipamentoOut]


class DashboardItem(SchemaBase):
    rotulo: str
    quantidade: int


class DashboardOut(SchemaBase):
    total_ieds: int
    em_operacao: int
    sem_funcao_operacao: int
    sem_firmware: int
    por_modelo: list[DashboardItem]
    por_subestacao: list[DashboardItem]
    por_status: list[DashboardItem]
    firmware_distribuicao: list[DashboardItem]


# --------------------------------------------------------------------------- #
# Fase 2 - Funcoes de protecao, ajustes, configuracoes e backups
# --------------------------------------------------------------------------- #

TipoDadoParametro = Literal["NUMERICO", "TEMPO", "BOOLEANO", "TEXTO"]
MotivoConfiguracao = Literal[
    "BACKUP_PERIODICO",
    "ALTERACAO_AJUSTE",
    "PRE_MANUTENCAO",
    "POS_MANUTENCAO",
    "POS_FIRMWARE",
    "OUTRO",
]
StatusValidacaoBackup = Literal["PENDENTE", "VALIDADA", "REJEITADA"]
ResultadoValidacao = Literal["APROVADO", "REPROVADO"]
PapelArquivo = Literal["PRINCIPAL", "EXPORT_PARAMETROS", "SCL", "DOCUMENTO", "COMPLEMENTAR"]


class FuncaoANSIBase(SchemaBase):
    codigo: str = Field(min_length=1, max_length=20)
    nome: str = Field(min_length=2, max_length=150)
    categoria: str | None = Field(default=None, max_length=60)
    descricao: str | None = None
    ativo: bool = True

    @field_validator("codigo", mode="before")
    @classmethod
    def normalizar_codigo(cls, value):
        return str(value).strip().upper() if value is not None else value


class FuncaoANSICreate(FuncaoANSIBase):
    pass


class FuncaoANSIUpdate(SchemaBase):
    codigo: str | None = Field(default=None, min_length=1, max_length=20)
    nome: str | None = Field(default=None, min_length=2, max_length=150)
    categoria: str | None = Field(default=None, max_length=60)
    descricao: str | None = None
    ativo: bool | None = None


class FuncaoANSIOut(FuncaoANSIBase):
    id_funcao_ansi: int
    quantidade_parametros: int = 0
    quantidade_ieds: int = 0
    criado_em: datetime
    atualizado_em: datetime


class FuncaoANSILista(SchemaBase):
    total: int
    page: int
    page_size: int
    items: list[FuncaoANSIOut]


class ParametroDefinicaoBase(SchemaBase):
    codigo: str = Field(min_length=1, max_length=60)
    nome: str = Field(min_length=2, max_length=150)
    unidade: str | None = Field(default=None, max_length=30)
    tipo_dado: TipoDadoParametro = "NUMERICO"
    identificador_fabricante: str | None = Field(default=None, max_length=100)
    valor_minimo: str | None = Field(default=None, max_length=60)
    valor_maximo: str | None = Field(default=None, max_length=60)
    descricao: str | None = None
    ativo: bool = True

    @field_validator("tipo_dado", mode="before")
    @classmethod
    def normalizar_tipo(cls, value):
        return str(value).strip().upper() if value is not None else value


class ParametroDefinicaoCreate(ParametroDefinicaoBase):
    pass


class ParametroDefinicaoUpdate(SchemaBase):
    codigo: str | None = Field(default=None, min_length=1, max_length=60)
    nome: str | None = Field(default=None, min_length=2, max_length=150)
    unidade: str | None = Field(default=None, max_length=30)
    tipo_dado: TipoDadoParametro | None = None
    identificador_fabricante: str | None = Field(default=None, max_length=100)
    valor_minimo: str | None = Field(default=None, max_length=60)
    valor_maximo: str | None = Field(default=None, max_length=60)
    descricao: str | None = None
    ativo: bool | None = None


class ParametroDefinicaoOut(ParametroDefinicaoBase):
    id_parametro_definicao: int
    id_funcao_ansi: int
    funcao_codigo: str | None = None
    funcao_nome: str | None = None
    criado_em: datetime
    atualizado_em: datetime


class IEDFuncaoCreate(SchemaBase):
    id_funcao_ansi: int = Field(gt=0)
    instancia: int = Field(default=1, ge=1, le=99)
    habilitada: bool = True
    observacoes: str | None = None


class IEDFuncaoUpdate(SchemaBase):
    instancia: int | None = Field(default=None, ge=1, le=99)
    habilitada: bool | None = None
    observacoes: str | None = None


class IEDFuncaoOut(SchemaBase):
    id_ied_funcao: int
    id_ied: int
    id_funcao_ansi: int
    codigo: str
    nome: str
    categoria: str | None = None
    instancia: int
    habilitada: bool
    observacoes: str | None = None
    criado_em: datetime
    atualizado_em: datetime


class IEDGrupoAjusteCreate(SchemaBase):
    numero: int = Field(ge=1, le=99)
    nome: str | None = Field(default=None, max_length=100)
    ativo: bool = True
    descricao: str | None = None


class IEDGrupoAjusteUpdate(SchemaBase):
    numero: int | None = Field(default=None, ge=1, le=99)
    nome: str | None = Field(default=None, max_length=100)
    ativo: bool | None = None
    descricao: str | None = None


class IEDGrupoAjusteOut(SchemaBase):
    id_ied_grupo_ajuste: int
    id_ied: int
    numero: int
    nome: str | None = None
    ativo: bool
    descricao: str | None = None
    quantidade_parametros: int = 0
    versao: int
    criado_em: datetime
    atualizado_em: datetime


class ConfigParametroItem(SchemaBase):
    id_parametro_definicao: int = Field(gt=0)
    valor: str = Field(min_length=1, max_length=255)
    ajustado_em: date | None = None
    observacoes: str | None = None


class ConfigParametroLote(SchemaBase):
    parametros: list[ConfigParametroItem] = Field(default_factory=list)


class ConfigParametroOut(SchemaBase):
    id_config_parametro: int
    id_parametro_definicao: int
    id_funcao_ansi: int
    funcao_codigo: str
    funcao_nome: str
    codigo: str
    nome: str
    unidade: str | None = None
    tipo_dado: TipoDadoParametro
    valor: str
    ajustado_em: date | None = None
    observacoes: str | None = None
    atualizado_em: datetime


class GrupoParametrosOut(SchemaBase):
    grupo: IEDGrupoAjusteOut
    itens: list[ConfigParametroOut]


class ArquivoOut(SchemaBase):
    id_arquivo: int
    nome_original: str
    tamanho_bytes: int
    mime_type: str | None = None
    extensao: str | None = None
    sha256: str
    categoria: str
    descricao: str | None = None
    criado_em: datetime


class ConfiguracaoCreate(SchemaBase):
    rotulo: str = Field(min_length=2, max_length=150)
    motivo: MotivoConfiguracao = "OUTRO"
    versao_digsi: str | None = Field(default=None, max_length=60)
    versao_firmware: str | None = Field(default=None, max_length=100)
    data_coleta: date
    id_grupo_ajuste: int | None = Field(default=None, gt=0)
    id_os: int | None = Field(default=None, gt=0)
    observacoes: str | None = None


class ConfiguracaoArquivoOut(SchemaBase):
    id_configuracao_arquivo: int
    papel: PapelArquivo
    arquivo: ArquivoOut


class ValidacaoCreate(SchemaBase):
    resultado: ResultadoValidacao
    observacoes: str | None = None
    data_validacao: date | None = None


class ValidacaoOut(SchemaBase):
    id_ied_backup_validacao: int
    resultado: ResultadoValidacao
    observacoes: str | None = None
    id_usuario_validacao: int
    nome_usuario: str | None = None
    data_validacao: date
    criado_em: datetime


class ConfiguracaoOut(SchemaBase):
    id_ied_configuracao: int
    id_ied: int
    versao: int
    rotulo: str
    motivo: MotivoConfiguracao
    status_validacao: StatusValidacaoBackup
    versao_digsi: str | None = None
    versao_firmware: str | None = None
    data_coleta: date
    id_grupo_ajuste: int | None = None
    grupo_ajuste_nome: str | None = None
    id_os: int | None = None
    hash_configuracao: str | None = None
    observacoes: str | None = None
    ativo: bool
    id_usuario_coleta: int
    nome_usuario_coleta: str | None = None
    quantidade_arquivos: int = 0
    arquivos: list[ConfiguracaoArquivoOut] = Field(default_factory=list)
    validacoes: list[ValidacaoOut] = Field(default_factory=list)
    criado_em: datetime
    atualizado_em: datetime


class ConfiguracaoLista(SchemaBase):
    total: int
    page: int
    page_size: int
    items: list[ConfiguracaoOut]


class ResumoConfiguracaoOut(SchemaBase):
    total_funcoes_ansi: int
    total_parametros_definicao: int
    total_ied_funcoes: int
    total_grupos_ajuste: int
    total_configuracoes: int
    aguardando_validacao: int
    ieds_sem_configuracao: int
    por_motivo: list[DashboardItem]


# --------------------------------------------------------------------------- #
# Fase 3 - Gestao de alteracoes e comparador de configuracoes
# --------------------------------------------------------------------------- #

StatusAlteracao = Literal[
    "RASCUNHO",
    "SUBMETIDA",
    "APROVADA",
    "REJEITADA",
    "IMPLANTADA",
    "VALIDADA",
    "NAO_VALIDADA",
    "CANCELADA",
]
TipoAlteracao = Literal["AJUSTE", "FIRMWARE", "HARDWARE", "COMUNICACAO", "CORRECAO", "OUTRO"]
PrioridadeAlteracao = Literal["BAIXA", "MEDIA", "ALTA", "CRITICA"]
AcaoAlteracao = Literal[
    "CRIACAO",
    "ATUALIZACAO",
    "SUBMISSAO",
    "APROVACAO",
    "REJEICAO",
    "IMPLANTACAO",
    "VALIDACAO",
    "REJEICAO_VALIDACAO",
    "CANCELAMENTO",
]
SituacaoComparacao = Literal["ADICIONADO", "REMOVIDO", "ALTERADO", "IGUAL"]


class SolicitacaoAlteracaoBase(SchemaBase):
    titulo: str = Field(min_length=2, max_length=200)
    descricao: str | None = None
    tipo: TipoAlteracao = "AJUSTE"
    prioridade: PrioridadeAlteracao = "MEDIA"
    id_configuracao_origem: int | None = Field(default=None, gt=0)
    id_grupo_ajuste: int | None = Field(default=None, gt=0)
    id_os: int | None = Field(default=None, gt=0)
    justificativa: str | None = None
    observacoes: str | None = None
    data_necessidade: date | None = None


class SolicitacaoAlteracaoCreate(SolicitacaoAlteracaoBase):
    id_ied: int = Field(gt=0)
    id_usuario_solicitante: int | None = Field(default=None, gt=0)


class SolicitacaoAlteracaoUpdate(SchemaBase):
    versao: int = Field(gt=0)
    titulo: str | None = Field(default=None, min_length=2, max_length=200)
    descricao: str | None = None
    tipo: TipoAlteracao | None = None
    prioridade: PrioridadeAlteracao | None = None
    id_configuracao_origem: int | None = Field(default=None, gt=0)
    id_grupo_ajuste: int | None = Field(default=None, gt=0)
    id_os: int | None = Field(default=None, gt=0)
    justificativa: str | None = None
    observacoes: str | None = None
    data_necessidade: date | None = None


class AlteracaoItemBase(SchemaBase):
    id_parametro_definicao: int = Field(gt=0)
    valor_atual: str | None = Field(default=None, max_length=255)
    valor_proposto: str | None = Field(default=None, max_length=255)
    observacoes: str | None = None


class AlteracaoItemCreate(AlteracaoItemBase):
    pass


class AlteracaoItemUpdate(SchemaBase):
    valor_atual: str | None = Field(default=None, max_length=255)
    valor_proposto: str | None = Field(default=None, max_length=255)
    observacoes: str | None = None


class AlteracaoItemOut(AlteracaoItemBase):
    id_alteracao_item: int
    id_solicitacao_alteracao: int
    id_funcao_ansi: int
    funcao_codigo: str
    funcao_nome: str
    codigo: str
    nome: str
    unidade: str | None = None
    tipo_dado: TipoDadoParametro
    situacao: SituacaoComparacao = "ALTERADO"
    criado_em: datetime
    atualizado_em: datetime


class AlteracaoHistoricoOut(SchemaBase):
    id_alteracao_historico: int
    acao: AcaoAlteracao
    status_anterior: StatusAlteracao | None = None
    status_novo: StatusAlteracao | None = None
    comentario: str | None = None
    id_usuario: int
    nome_usuario: str | None = None
    criado_em: datetime


class SolicitacaoAlteracaoOut(SchemaBase):
    id_solicitacao_alteracao: int
    numero: int
    id_ied: int
    titulo: str
    descricao: str | None = None
    tipo: TipoAlteracao
    prioridade: PrioridadeAlteracao
    status: StatusAlteracao
    id_configuracao_origem: int | None = None
    id_configuracao_resultante: int | None = None
    id_grupo_ajuste: int | None = None
    grupo_ajuste_nome: str | None = None
    id_os: int | None = None
    justificativa: str | None = None
    observacoes: str | None = None
    data_necessidade: date | None = None
    data_implantacao: date | None = None
    data_validacao: date | None = None
    resultado_validacao: ResultadoValidacao | None = None
    id_usuario_solicitante: int
    nome_solicitante: str | None = None
    id_usuario_aprovador: int | None = None
    nome_aprovador: str | None = None
    id_usuario_validador: int | None = None
    nome_validador: str | None = None
    quantidade_itens: int = 0
    versao: int
    criado_em: datetime
    atualizado_em: datetime


class SolicitacaoAlteracaoDetalhe(SolicitacaoAlteracaoOut):
    itens: list[AlteracaoItemOut] = Field(default_factory=list)
    historico: list[AlteracaoHistoricoOut] = Field(default_factory=list)


class SolicitacaoAlteracaoLista(SchemaBase):
    total: int
    page: int
    page_size: int
    items: list[SolicitacaoAlteracaoOut]


class ComparacaoParametroOut(SchemaBase):
    id_parametro_definicao: int
    id_funcao_ansi: int
    funcao_codigo: str
    funcao_nome: str
    codigo: str
    nome: str
    unidade: str | None = None
    tipo_dado: TipoDadoParametro
    valor_base: str | None = None
    valor_destino: str | None = None
    situacao: SituacaoComparacao


class ComparacaoGruposOut(SchemaBase):
    id_grupo_base: int | None = None
    id_grupo_destino: int | None = None
    rotulo_base: str | None = None
    rotulo_destino: str | None = None
    total_base: int
    total_destino: int
    adicionados: int
    removidos: int
    alterados: int
    iguais: int
    itens: list[ComparacaoParametroOut]


class TransicaoAlteracao(SchemaBase):
    comentario: str | None = None


class ImplantacaoAlteracao(SchemaBase):
    id_configuracao_resultante: int | None = Field(default=None, gt=0)
    data_implantacao: date | None = None
    comentario: str | None = None


class ValidacaoAlteracao(SchemaBase):
    aprovado: bool
    id_configuracao_validada: int | None = Field(default=None, gt=0)
    data_validacao: date | None = None
    comentario: str | None = None


class ImportarItensAlteracao(SchemaBase):
    id_grupo_base: int = Field(gt=0)
    id_grupo_destino: int = Field(gt=0)
    incluir_iguais: bool = False


class ResumoAlteracaoOut(SchemaBase):
    total: int
    aguardando_aprovacao: int
    aguardando_implantacao: int
    aguardando_validacao: int
    por_status: list[DashboardItem]
    por_tipo: list[DashboardItem]
    por_prioridade: list[DashboardItem]


# --------------------------------------------------------------------------- #
# Fase 4 - Engenharia de protecao (comunicacao, circuitos/sinais e ensaios)
# --------------------------------------------------------------------------- #

TipoInterfaceComunicacao = Literal["ETHERNET", "SERIAL", "FIBRA_OPTICA", "PROCESS_BUS", "WIRELESS"]
ProtocoloComunicacao = Literal[
    "IEC61850_MMS",
    "IEC61850_GOOSE",
    "IEC61850_SV",
    "DNP3",
    "MODBUS_RTU",
    "MODBUS_TCP",
    "IEC60870_5_101",
    "IEC60870_5_104",
    "PROFIBUS",
    "SNTP",
    "NTP",
    "PRP",
    "HSR",
    "OUTRO",
]
PapelProtocolo = Literal["SERVIDOR", "CLIENTE", "PUBLICADOR", "ASSINANTE", "AMBOS"]
TipoGooseControle = Literal["GOOSE", "SV"]
DirecaoGoose = Literal["PUBLICADO", "ASSINADO"]
TipoCircuito = Literal[
    "TRIP", "FECHAMENTO", "BLOQUEIO", "SINALIZACAO", "MEDICAO", "ALARME", "SUPERVISAO", "OUTRO"
]
TipoSinal = Literal["DIGITAL_ENTRADA", "DIGITAL_SAIDA", "ANALOGICA_ENTRADA", "ANALOGICA_SAIDA"]
EstadoSinal = Literal["PENDENTE", "COMISSIONADO", "INATIVO", "DESATIVADO"]
TipoEnsaio = Literal[
    "COMISSIONAMENTO", "ACEITACAO", "ROTINA", "PERIODICO", "POS_EVENTO", "POS_REPARO", "OUTRO"
]
StatusEnsaio = Literal["PLANEJADO", "EM_ANDAMENTO", "APROVADO", "REPROVADO", "CANCELADO"]
ResultadoItemEnsaio = Literal["APROVADO", "REPROVADO", "NAO_APLICAVEL"]


class InterfaceComunicacaoBase(SchemaBase):
    nome: str = Field(min_length=2, max_length=60)
    tipo: TipoInterfaceComunicacao = "ETHERNET"
    meio: str | None = Field(default=None, max_length=30)
    mac_address: str | None = Field(default=None, max_length=32)
    endereco_ip: str | None = Field(default=None, max_length=45)
    mascara: str | None = Field(default=None, max_length=45)
    gateway: str | None = Field(default=None, max_length=45)
    vlan: str | None = Field(default=None, max_length=30)
    velocidade: str | None = Field(default=None, max_length=20)
    conectada: bool = True
    descricao: str | None = None
    observacoes: str | None = None


class InterfaceComunicacaoCreate(InterfaceComunicacaoBase):
    pass


class InterfaceComunicacaoUpdate(SchemaBase):
    versao: int = Field(gt=0)
    nome: str | None = Field(default=None, min_length=2, max_length=60)
    tipo: TipoInterfaceComunicacao | None = None
    meio: str | None = Field(default=None, max_length=30)
    mac_address: str | None = Field(default=None, max_length=32)
    endereco_ip: str | None = Field(default=None, max_length=45)
    mascara: str | None = Field(default=None, max_length=45)
    gateway: str | None = Field(default=None, max_length=45)
    vlan: str | None = Field(default=None, max_length=30)
    velocidade: str | None = Field(default=None, max_length=20)
    conectada: bool | None = None
    descricao: str | None = None
    observacoes: str | None = None


class ProtocoloComunicacaoBase(SchemaBase):
    protocolo: ProtocoloComunicacao
    papel: PapelProtocolo = "SERVIDOR"
    porta: str | None = Field(default=None, max_length=20)
    endereco_destino: str | None = Field(default=None, max_length=60)
    habilitado: bool = True
    observacoes: str | None = None


class ProtocoloComunicacaoCreate(ProtocoloComunicacaoBase):
    pass


class ProtocoloComunicacaoUpdate(SchemaBase):
    protocolo: ProtocoloComunicacao | None = None
    papel: PapelProtocolo | None = None
    porta: str | None = Field(default=None, max_length=20)
    endereco_destino: str | None = Field(default=None, max_length=60)
    habilitado: bool | None = None
    observacoes: str | None = None


class ProtocoloComunicacaoOut(ProtocoloComunicacaoBase):
    id_ied_protocolo_comunicacao: int
    id_ied_interface_comunicacao: int
    criado_em: datetime
    atualizado_em: datetime


class InterfaceComunicacaoOut(InterfaceComunicacaoBase):
    id_ied_interface_comunicacao: int
    id_ied: int
    versao: int
    quantidade_protocolos: int = 0
    protocolos: list[ProtocoloComunicacaoOut] = Field(default_factory=list)
    criado_em: datetime
    atualizado_em: datetime


class GooseControleBase(SchemaBase):
    tipo: TipoGooseControle = "GOOSE"
    direcao: DirecaoGoose = "PUBLICADO"
    nome_controle: str = Field(min_length=2, max_length=150)
    id_ied_interface_comunicacao: int | None = Field(default=None, gt=0)
    dataset: str | None = Field(default=None, max_length=150)
    appid: str | None = Field(default=None, max_length=20)
    mac_destino: str | None = Field(default=None, max_length=32)
    vlan: str | None = Field(default=None, max_length=30)
    conf_rev: int | None = Field(default=None, ge=0)
    tempo_retransmissao_ms: int | None = Field(default=None, ge=0)
    habilitado: bool = True
    observacoes: str | None = None


class GooseControleCreate(GooseControleBase):
    pass


class GooseControleUpdate(SchemaBase):
    versao: int = Field(gt=0)
    tipo: TipoGooseControle | None = None
    direcao: DirecaoGoose | None = None
    nome_controle: str | None = Field(default=None, min_length=2, max_length=150)
    id_ied_interface_comunicacao: int | None = Field(default=None, gt=0)
    dataset: str | None = Field(default=None, max_length=150)
    appid: str | None = Field(default=None, max_length=20)
    mac_destino: str | None = Field(default=None, max_length=32)
    vlan: str | None = Field(default=None, max_length=30)
    conf_rev: int | None = Field(default=None, ge=0)
    tempo_retransmissao_ms: int | None = Field(default=None, ge=0)
    habilitado: bool | None = None
    observacoes: str | None = None


class GooseControleOut(GooseControleBase):
    id_ied_goose_controle: int
    id_ied: int
    interface_nome: str | None = None
    versao: int
    criado_em: datetime
    atualizado_em: datetime


class CircuitoBase(SchemaBase):
    codigo: str = Field(min_length=1, max_length=60)
    nome: str = Field(min_length=2, max_length=150)
    tipo: TipoCircuito = "SINALIZACAO"
    id_funcao_ansi: int | None = Field(default=None, gt=0)
    id_ied_equipamento: int | None = Field(default=None, gt=0)
    descricao: str | None = None
    observacoes: str | None = None
    ativo: bool = True


class CircuitoCreate(CircuitoBase):
    pass


class CircuitoUpdate(SchemaBase):
    versao: int = Field(gt=0)
    codigo: str | None = Field(default=None, min_length=1, max_length=60)
    nome: str | None = Field(default=None, min_length=2, max_length=150)
    tipo: TipoCircuito | None = None
    id_funcao_ansi: int | None = Field(default=None, gt=0)
    id_ied_equipamento: int | None = Field(default=None, gt=0)
    descricao: str | None = None
    observacoes: str | None = None
    ativo: bool | None = None


class CircuitoOut(CircuitoBase):
    id_ied_circuito: int
    id_ied: int
    funcao_codigo: str | None = None
    funcao_nome: str | None = None
    equipamento_nome: str | None = None
    quantidade_sinais: int = 0
    versao: int
    criado_em: datetime
    atualizado_em: datetime


class SinalBase(SchemaBase):
    tipo: TipoSinal = "DIGITAL_ENTRADA"
    mnemonico: str = Field(min_length=1, max_length=60)
    descricao: str = Field(min_length=2, max_length=300)
    id_ied_circuito: int | None = Field(default=None, gt=0)
    id_funcao_ansi: int | None = Field(default=None, gt=0)
    id_ied_equipamento: int | None = Field(default=None, gt=0)
    numero_terminal: str | None = Field(default=None, max_length=40)
    unidade: str | None = Field(default=None, max_length=30)
    valor_nominal: str | None = Field(default=None, max_length=60)
    estado: EstadoSinal = "PENDENTE"
    observacoes: str | None = None


class SinalCreate(SinalBase):
    pass


class SinalUpdate(SchemaBase):
    versao: int = Field(gt=0)
    tipo: TipoSinal | None = None
    mnemonico: str | None = Field(default=None, min_length=1, max_length=60)
    descricao: str | None = Field(default=None, min_length=2, max_length=300)
    id_ied_circuito: int | None = Field(default=None, gt=0)
    id_funcao_ansi: int | None = Field(default=None, gt=0)
    id_ied_equipamento: int | None = Field(default=None, gt=0)
    numero_terminal: str | None = Field(default=None, max_length=40)
    unidade: str | None = Field(default=None, max_length=30)
    valor_nominal: str | None = Field(default=None, max_length=60)
    estado: EstadoSinal | None = None
    observacoes: str | None = None


class SinalOut(SinalBase):
    id_ied_sinal: int
    id_ied: int
    circuito_codigo: str | None = None
    funcao_codigo: str | None = None
    funcao_nome: str | None = None
    equipamento_nome: str | None = None
    versao: int
    criado_em: datetime
    atualizado_em: datetime


class EnsaioBase(SchemaBase):
    titulo: str = Field(min_length=2, max_length=200)
    tipo: TipoEnsaio = "ROTINA"
    descricao: str | None = None
    data_prevista: date | None = None
    id_os: int | None = Field(default=None, gt=0)
    id_usuario_executor: int | None = Field(default=None, gt=0)
    instrumentos: str | None = None
    observacoes: str | None = None


class EnsaioCreate(EnsaioBase):
    pass


class EnsaioUpdate(SchemaBase):
    versao: int = Field(gt=0)
    titulo: str | None = Field(default=None, min_length=2, max_length=200)
    tipo: TipoEnsaio | None = None
    status: StatusEnsaio | None = None
    descricao: str | None = None
    data_prevista: date | None = None
    data_execucao: date | None = None
    id_os: int | None = Field(default=None, gt=0)
    id_usuario_executor: int | None = Field(default=None, gt=0)
    instrumentos: str | None = None
    resultado: str | None = None
    observacoes: str | None = None


class EnsaioItemBase(SchemaBase):
    descricao: str = Field(min_length=2, max_length=300)
    id_funcao_ansi: int | None = Field(default=None, gt=0)
    id_ied_sinal: int | None = Field(default=None, gt=0)
    ordem: int = Field(default=0, ge=0)
    valor_esperado: str | None = Field(default=None, max_length=120)
    valor_medido: str | None = Field(default=None, max_length=120)
    unidade: str | None = Field(default=None, max_length=30)
    resultado: ResultadoItemEnsaio | None = None
    observacoes: str | None = None


class EnsaioItemCreate(EnsaioItemBase):
    pass


class EnsaioItemUpdate(SchemaBase):
    descricao: str | None = Field(default=None, min_length=2, max_length=300)
    id_funcao_ansi: int | None = Field(default=None, gt=0)
    id_ied_sinal: int | None = Field(default=None, gt=0)
    ordem: int | None = Field(default=None, ge=0)
    valor_esperado: str | None = Field(default=None, max_length=120)
    valor_medido: str | None = Field(default=None, max_length=120)
    unidade: str | None = Field(default=None, max_length=30)
    resultado: ResultadoItemEnsaio | None = None
    observacoes: str | None = None


class EnsaioItemOut(EnsaioItemBase):
    id_ied_ensaio_item: int
    id_ied_ensaio: int
    funcao_codigo: str | None = None
    funcao_nome: str | None = None
    sinal_mnemonico: str | None = None
    criado_em: datetime
    atualizado_em: datetime


class EnsaioArquivoOut(SchemaBase):
    id_ied_ensaio_arquivo: int
    id_arquivo: int
    nome_original: str
    tamanho_bytes: int
    mime_type: str | None = None
    extensao: str | None = None
    sha256: str | None = None
    descricao: str | None = None
    id_usuario_upload: int
    nome_usuario_upload: str | None = None
    criado_em: datetime


class EnsaioOut(EnsaioBase):
    id_ied_ensaio: int
    id_ied: int
    ied_tag: str | None = None
    numero: int
    status: StatusEnsaio
    data_execucao: date | None = None
    resultado: str | None = None
    nome_executor: str | None = None
    quantidade_itens: int = 0
    quantidade_arquivos: int = 0
    versao: int
    criado_em: datetime
    atualizado_em: datetime


class EnsaioDetalhe(EnsaioOut):
    itens: list[EnsaioItemOut] = Field(default_factory=list)
    arquivos: list[EnsaioArquivoOut] = Field(default_factory=list)


class EnsaioLista(SchemaBase):
    total: int
    page: int
    page_size: int
    items: list[EnsaioOut]


class ResumoEngenhariaOut(SchemaBase):
    total_interfaces: int
    total_protocolos: int
    total_goose: int
    total_circuitos: int
    total_sinais: int
    sinais_pendentes: int
    total_ensaios: int
    ensaios_aguardando: int
    ensaios_reprovados: int
    ieds_sem_comunicacao: int
    ieds_sem_sinais: int
    ieds_sem_ensaios: int
    por_tipo_sinal: list[DashboardItem]
    por_status_ensaio: list[DashboardItem]


# --------------------------------------------------------------------------- #
# Fase 5 - Ocorrencias e indicadores (eventos, oscilografias e relatorios)
# --------------------------------------------------------------------------- #

TipoOcorrencia = Literal[
    "DISPARO",
    "REARME",
    "ATUACAO_PROTECAO",
    "ALARME",
    "FALHA_COMUNICACAO",
    "SOBRECORRENTE",
    "SOBRETENSAO",
    "SUBTENSAO",
    "FALTA_ENERGIA",
    "OSCILACAO",
    "OUTRO",
]
SeveridadeOcorrencia = Literal["BAIXA", "MEDIA", "ALTA", "CRITICA"]
StatusOcorrencia = Literal["ABERTA", "EM_ANALISE", "ENCERRADA", "CANCELADA"]
TipoOscilografia = Literal["OSCILOGRAFIA", "PERTURBACAO", "RELIGAMENTO", "FALTA", "OUTRO"]
TipoRelatorio = Literal["OCORRENCIA", "INSPECAO", "ENSAIO", "MANUTENCAO", "ANALISE", "PERIODICO", "OUTRO"]
StatusRelatorio = Literal["RASCUNHO", "EMITIDO", "APROVADO", "CANCELADO"]
AcaoOcorrencia = Literal[
    "CRIACAO",
    "ATUALIZACAO",
    "ANEXO",
    "REMOCAO_ARQUIVO",
    "ENCERRAMENTO",
    "CANCELAMENTO",
    "REABERTURA",
    "OSCILOGRAFIA",
    "RELATORIO",
]


class OcorrenciaBase(SchemaBase):
    titulo: str = Field(min_length=2, max_length=200)
    tipo: TipoOcorrencia = "ALARME"
    severidade: SeveridadeOcorrencia = "MEDIA"
    data_hora: datetime | None = None
    descricao: str | None = None
    causa_provavel: str | None = None
    acao_tomada: str | None = None
    id_os: int | None = Field(default=None, gt=0)
    id_usuario_responsavel: int | None = Field(default=None, gt=0)
    observacoes: str | None = None


class OcorrenciaCreate(OcorrenciaBase):
    pass


class OcorrenciaUpdate(SchemaBase):
    versao: int = Field(gt=0)
    titulo: str | None = Field(default=None, min_length=2, max_length=200)
    tipo: TipoOcorrencia | None = None
    severidade: SeveridadeOcorrencia | None = None
    status: StatusOcorrencia | None = None
    data_hora: datetime | None = None
    descricao: str | None = None
    causa_provavel: str | None = None
    acao_tomada: str | None = None
    id_os: int | None = Field(default=None, gt=0)
    id_usuario_responsavel: int | None = Field(default=None, gt=0)
    observacoes: str | None = None


class EncerramentoOcorrencia(SchemaBase):
    comentario: str | None = None


class OcorrenciaArquivoOut(SchemaBase):
    id_ied_ocorrencia_arquivo: int
    id_arquivo: int
    nome_original: str
    tamanho_bytes: int
    mime_type: str | None = None
    extensao: str | None = None
    sha256: str | None = None
    descricao: str | None = None
    id_usuario_upload: int
    nome_usuario_upload: str | None = None
    criado_em: datetime


class OcorrenciaHistoricoOut(SchemaBase):
    id_ied_ocorrencia_historico: int
    id_ied_ocorrencia: int
    acao: AcaoOcorrencia
    descricao: str | None = None
    id_usuario: int | None = None
    nome_usuario: str | None = None
    criado_em: datetime


class OcorrenciaOut(OcorrenciaBase):
    id_ied_ocorrencia: int
    id_ied: int
    ied_tag: str | None = None
    numero: int
    status: StatusOcorrencia
    data_hora: datetime
    id_usuario_registro: int | None = None
    nome_usuario_registro: str | None = None
    id_usuario_encerramento: int | None = None
    nome_usuario_encerramento: str | None = None
    data_encerramento: datetime | None = None
    quantidade_arquivos: int = 0
    quantidade_oscilografias: int = 0
    versao: int
    criado_em: datetime
    atualizado_em: datetime


class OcorrenciaDetalhe(OcorrenciaOut):
    arquivos: list[OcorrenciaArquivoOut] = Field(default_factory=list)
    historico: list[OcorrenciaHistoricoOut] = Field(default_factory=list)


class OcorrenciaLista(SchemaBase):
    total: int
    page: int
    page_size: int
    items: list[OcorrenciaOut]


class OscilografiaBase(SchemaBase):
    nome: str = Field(min_length=2, max_length=150)
    tipo: TipoOscilografia = "OSCILOGRAFIA"
    data_hora: datetime | None = None
    duracao_ms: int | None = Field(default=None, ge=0)
    frequencia_amostragem_hz: int | None = Field(default=None, ge=0)
    numero_canais: int | None = Field(default=None, ge=0)
    origem: str | None = Field(default=None, max_length=150)
    id_ocorrencia: int | None = Field(default=None, gt=0)
    observacoes: str | None = None


class OscilografiaCreate(OscilografiaBase):
    pass


class OscilografiaUpdate(SchemaBase):
    versao: int = Field(gt=0)
    nome: str | None = Field(default=None, min_length=2, max_length=150)
    tipo: TipoOscilografia | None = None
    data_hora: datetime | None = None
    duracao_ms: int | None = Field(default=None, ge=0)
    frequencia_amostragem_hz: int | None = Field(default=None, ge=0)
    numero_canais: int | None = Field(default=None, ge=0)
    origem: str | None = Field(default=None, max_length=150)
    id_ocorrencia: int | None = Field(default=None, gt=0)
    observacoes: str | None = None


class OscilografiaArquivoOut(SchemaBase):
    id_ied_oscilografia_arquivo: int
    id_arquivo: int
    nome_original: str
    tamanho_bytes: int
    mime_type: str | None = None
    extensao: str | None = None
    sha256: str | None = None
    descricao: str | None = None
    id_usuario_upload: int
    nome_usuario_upload: str | None = None
    criado_em: datetime


class OscilografiaOut(OscilografiaBase):
    id_ied_oscilografia: int
    id_ied: int
    ied_tag: str | None = None
    numero: int
    data_hora: datetime
    ocorrencia_titulo: str | None = None
    quantidade_arquivos: int = 0
    versao: int
    criado_em: datetime
    atualizado_em: datetime


class OscilografiaDetalhe(OscilografiaOut):
    arquivos: list[OscilografiaArquivoOut] = Field(default_factory=list)


class OscilografiaLista(SchemaBase):
    total: int
    page: int
    page_size: int
    items: list[OscilografiaOut]


class RelatorioBase(SchemaBase):
    titulo: str = Field(min_length=2, max_length=200)
    tipo: TipoRelatorio = "OCORRENCIA"
    data_emissao: date | None = None
    periodo_inicio: date | None = None
    periodo_fim: date | None = None
    resumo: str | None = None
    id_ocorrencia: int | None = Field(default=None, gt=0)
    observacoes: str | None = None


class RelatorioCreate(RelatorioBase):
    pass


class RelatorioUpdate(SchemaBase):
    versao: int = Field(gt=0)
    titulo: str | None = Field(default=None, min_length=2, max_length=200)
    tipo: TipoRelatorio | None = None
    status: StatusRelatorio | None = None
    data_emissao: date | None = None
    periodo_inicio: date | None = None
    periodo_fim: date | None = None
    resumo: str | None = None
    id_ocorrencia: int | None = Field(default=None, gt=0)
    observacoes: str | None = None


class RelatorioArquivoOut(SchemaBase):
    id_ied_relatorio_arquivo: int
    id_arquivo: int
    nome_original: str
    tamanho_bytes: int
    mime_type: str | None = None
    extensao: str | None = None
    sha256: str | None = None
    descricao: str | None = None
    id_usuario_upload: int
    nome_usuario_upload: str | None = None
    criado_em: datetime


class RelatorioOut(RelatorioBase):
    id_ied_relatorio: int
    id_ied: int
    ied_tag: str | None = None
    numero: int
    status: StatusRelatorio
    ocorrencia_titulo: str | None = None
    id_usuario_emissao: int | None = None
    nome_usuario_emissao: str | None = None
    quantidade_arquivos: int = 0
    versao: int
    criado_em: datetime
    atualizado_em: datetime


class RelatorioDetalhe(RelatorioOut):
    arquivos: list[RelatorioArquivoOut] = Field(default_factory=list)


class RelatorioLista(SchemaBase):
    total: int
    page: int
    page_size: int
    items: list[RelatorioOut]


class AuditoriaOut(SchemaBase):
    id_ied_ocorrencia_historico: int
    id_ied_ocorrencia: int
    id_ied: int
    ied_tag: str | None = None
    numero_ocorrencia: int | None = None
    ocorrencia_titulo: str | None = None
    acao: AcaoOcorrencia
    descricao: str | None = None
    id_usuario: int | None = None
    nome_usuario: str | None = None
    criado_em: datetime


class ResumoOcorrenciaOut(SchemaBase):
    total_ocorrencias: int
    ocorrencias_abertas: int
    ocorrencias_criticas: int
    ocorrencias_encerradas: int
    total_oscilografias: int
    total_relatorios: int
    relatorios_aguardando: int
    ieds_sem_ocorrencia: int
    ieds_sem_relatorio: int
    por_tipo: list[DashboardItem]
    por_severidade: list[DashboardItem]
    por_status: list[DashboardItem]
