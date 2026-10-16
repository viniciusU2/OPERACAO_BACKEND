from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user, require_roles
from database import get_db
from models.auth_models import Usuario

from . import schemas, service, service_alteracoes, service_config, service_engenharia, service_ocorrencias


router = APIRouter(prefix="/engenharia-protecao", tags=["Engenharia de Proteção"])


# Limite padrao das colecoes por IED/ocorrencia. As rotas aceitam `offset` e
# `limite` para paginacao (evita payloads ilimitados) sem quebrar o contrato de
# lista ja consumido pelo frontend.
LIMITE_COLECAO_PADRAO = 200
LIMITE_COLECAO_MAX = 500


def _paginar(itens: list, offset: int, limite: int) -> list:
    if offset <= 0 and limite >= len(itens):
        return itens
    return itens[offset : offset + limite]


def garantir_catalogo_funcoes_ansi(db: Session) -> None:
    """Popula o catálogo ANSI na subida da aplicação (idempotente)."""
    service_config.garantir_catalogo_funcoes_ansi(db)


@router.get("/dashboard", response_model=schemas.DashboardOut)
def obter_dashboard(
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service.dashboard(db)


@router.get("/modelos", response_model=schemas.ModeloIEDLista)
def listar_modelos(
    busca: str | None = None,
    somente_ativos: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service.listar_modelos(db, busca, somente_ativos, page, page_size)


@router.get("/modelos/{id_modelo_ied}", response_model=schemas.ModeloIEDOut)
def obter_modelo(
    id_modelo_ied: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service.obter_modelo(db, id_modelo_ied)


@router.post("/modelos", response_model=schemas.ModeloIEDOut, status_code=status.HTTP_201_CREATED)
def criar_modelo(
    dados: schemas.ModeloIEDCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_roles("admin", "mantenedor")),
):
    return service.criar_modelo(db, dados, usuario.id)


@router.put("/modelos/{id_modelo_ied}", response_model=schemas.ModeloIEDOut)
def atualizar_modelo(
    id_modelo_ied: int,
    dados: schemas.ModeloIEDUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_roles("admin", "mantenedor")),
):
    return service.atualizar_modelo(db, id_modelo_ied, dados, usuario.id)


@router.get("/ieds", response_model=schemas.IEDLista)
def listar_ieds(
    busca: str | None = None,
    id_subestacao: int | None = None,
    id_modelo_ied: int | None = None,
    status_operacional: str | None = None,
    somente_ativos: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service.listar_ieds(
        db,
        busca,
        id_subestacao,
        id_modelo_ied,
        status_operacional,
        somente_ativos,
        page,
        page_size,
    )


@router.post("/ieds", response_model=schemas.IEDDetalhe, status_code=status.HTTP_201_CREATED)
def criar_ied(
    dados: schemas.IEDCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_roles("admin", "mantenedor")),
):
    return service.criar_ied(db, dados, usuario.id)


@router.get("/ieds/{id_ied}", response_model=schemas.IEDDetalhe)
def obter_ied(
    id_ied: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service.obter_ied(db, id_ied)


@router.put("/ieds/{id_ied}", response_model=schemas.IEDDetalhe)
def atualizar_ied(
    id_ied: int,
    dados: schemas.IEDUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_roles("admin", "mantenedor")),
):
    return service.atualizar_ied(db, id_ied, dados, usuario.id)


@router.delete("/ieds/{id_ied}", response_model=schemas.IEDRemocaoOut)
def remover_ied(
    id_ied: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(require_roles("admin")),
):
    """Remove o IED e todos os dados do módulo. Operação restrita ao perfil admin."""
    return service.remover_ied(db, id_ied)


@router.post("/ieds/{id_ied}/movimentacoes", response_model=schemas.IEDDetalhe)
def movimentar_ied(
    id_ied: int,
    dados: schemas.TransferenciaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_roles("admin", "mantenedor")),
):
    return service.transferir_ied(db, id_ied, dados, usuario.id)


@router.post("/ieds/{id_ied}/modulos", response_model=schemas.ModuloOut, status_code=status.HTTP_201_CREATED)
def adicionar_modulo(
    id_ied: int,
    dados: schemas.ModuloCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_roles("admin", "mantenedor")),
):
    return service.adicionar_modulo(db, id_ied, dados, usuario.id)


@router.post("/ieds/{id_ied}/firmwares", response_model=schemas.FirmwareOut, status_code=status.HTTP_201_CREATED)
def registrar_firmware(
    id_ied: int,
    dados: schemas.FirmwareCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_roles("admin", "mantenedor")),
):
    return service.registrar_firmware(db, id_ied, dados, usuario.id)


@router.post("/ieds/{id_ied}/equipamentos", response_model=schemas.IEDDetalhe, status_code=status.HTTP_201_CREATED)
def associar_equipamento(
    id_ied: int,
    dados: schemas.EquipamentoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_roles("admin", "mantenedor")),
):
    return service.associar_equipamento(db, id_ied, dados, usuario.id)


@router.delete("/ieds/{id_ied}/equipamentos/{id_ied_equipamento}", response_model=schemas.IEDDetalhe)
def encerrar_associacao_equipamento(
    id_ied: int,
    id_ied_equipamento: int,
    data_fim: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(require_roles("admin", "mantenedor")),
):
    return service.encerrar_associacao_equipamento(db, id_ied, id_ied_equipamento, data_fim)


# --------------------------------------------------------------------------- #
# Fase 2 - Funcoes de protecao, ajustes, configuracoes e backups
# --------------------------------------------------------------------------- #

ESCRITA = require_roles("admin", "mantenedor")


@router.get("/funcoes-ansi", response_model=schemas.FuncaoANSILista)
def listar_funcoes_ansi(
    busca: str | None = None,
    somente_ativos: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_config.listar_funcoes_ansi(db, busca, somente_ativos, page, page_size)


@router.post("/funcoes-ansi", response_model=schemas.FuncaoANSIOut, status_code=status.HTTP_201_CREATED)
def criar_funcao_ansi(
    dados: schemas.FuncaoANSICreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_config.criar_funcao_ansi(db, dados, usuario.id)


@router.put("/funcoes-ansi/{id_funcao_ansi}", response_model=schemas.FuncaoANSIOut)
def atualizar_funcao_ansi(
    id_funcao_ansi: int,
    dados: schemas.FuncaoANSIUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_config.atualizar_funcao_ansi(db, id_funcao_ansi, dados, usuario.id)


@router.get("/parametros-definicao", response_model=list[schemas.ParametroDefinicaoOut])
def listar_parametros(
    id_funcao_ansi: int | None = None,
    busca: str | None = None,
    somente_ativos: bool = True,
    offset: int = Query(0, ge=0),
    limite: int = Query(LIMITE_COLECAO_PADRAO, ge=1, le=LIMITE_COLECAO_MAX),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    itens = service_config.listar_parametros(db, id_funcao_ansi, busca, somente_ativos)
    return _paginar(itens, offset, limite)


@router.post(
    "/funcoes-ansi/{id_funcao_ansi}/parametros",
    response_model=schemas.ParametroDefinicaoOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_parametro(
    id_funcao_ansi: int,
    dados: schemas.ParametroDefinicaoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_config.criar_parametro(db, id_funcao_ansi, dados, usuario.id)


@router.put("/parametros-definicao/{id_parametro}", response_model=schemas.ParametroDefinicaoOut)
def atualizar_parametro(
    id_parametro: int,
    dados: schemas.ParametroDefinicaoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_config.atualizar_parametro(db, id_parametro, dados, usuario.id)


@router.get("/ieds/{id_ied}/funcoes", response_model=list[schemas.IEDFuncaoOut])
def listar_ied_funcoes(
    id_ied: int,
    offset: int = Query(0, ge=0),
    limite: int = Query(LIMITE_COLECAO_PADRAO, ge=1, le=LIMITE_COLECAO_MAX),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    itens = service_config.listar_ied_funcoes(db, id_ied)
    return _paginar(itens, offset, limite)


@router.post("/ieds/{id_ied}/funcoes", response_model=schemas.IEDFuncaoOut, status_code=status.HTTP_201_CREATED)
def adicionar_ied_funcao(
    id_ied: int,
    dados: schemas.IEDFuncaoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_config.adicionar_ied_funcao(db, id_ied, dados, usuario.id)


@router.put("/ieds/{id_ied}/funcoes/{id_ied_funcao}", response_model=schemas.IEDFuncaoOut)
def atualizar_ied_funcao(
    id_ied: int,
    id_ied_funcao: int,
    dados: schemas.IEDFuncaoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_config.atualizar_ied_funcao(db, id_ied, id_ied_funcao, dados, usuario.id)


@router.delete("/ieds/{id_ied}/funcoes/{id_ied_funcao}", status_code=status.HTTP_204_NO_CONTENT)
def remover_ied_funcao(
    id_ied: int,
    id_ied_funcao: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(ESCRITA),
):
    service_config.remover_ied_funcao(db, id_ied, id_ied_funcao)


@router.get("/ieds/{id_ied}/grupos-ajuste", response_model=list[schemas.IEDGrupoAjusteOut])
def listar_grupos_ajuste(
    id_ied: int,
    offset: int = Query(0, ge=0),
    limite: int = Query(LIMITE_COLECAO_PADRAO, ge=1, le=LIMITE_COLECAO_MAX),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    itens = service_config.listar_grupos_ajuste(db, id_ied)
    return _paginar(itens, offset, limite)


@router.post(
    "/ieds/{id_ied}/grupos-ajuste",
    response_model=schemas.IEDGrupoAjusteOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_grupo_ajuste(
    id_ied: int,
    dados: schemas.IEDGrupoAjusteCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_config.criar_grupo_ajuste(db, id_ied, dados, usuario.id)


@router.put("/ieds/{id_ied}/grupos-ajuste/{id_grupo}", response_model=schemas.IEDGrupoAjusteOut)
def atualizar_grupo_ajuste(
    id_ied: int,
    id_grupo: int,
    dados: schemas.IEDGrupoAjusteUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_config.atualizar_grupo_ajuste(db, id_ied, id_grupo, dados, usuario.id)


@router.get("/grupos-ajuste/{id_grupo}/parametros", response_model=schemas.GrupoParametrosOut)
def obter_grupo_parametros(
    id_grupo: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_config.obter_grupo_parametros(db, id_grupo)


@router.put("/grupos-ajuste/{id_grupo}/parametros", response_model=schemas.GrupoParametrosOut)
def definir_parametros_grupo(
    id_grupo: int,
    dados: schemas.ConfigParametroLote,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_config.definir_parametros_grupo(db, id_grupo, dados, usuario.id)


@router.get("/configuracoes/resumo", response_model=schemas.ResumoConfiguracaoOut)
def resumo_configuracao(
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_config.resumo_configuracao(db)


@router.get("/ieds/{id_ied}/configuracoes", response_model=schemas.ConfiguracaoLista)
def listar_configuracoes(
    id_ied: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_config.listar_configuracoes(db, id_ied, page, page_size)


@router.post(
    "/ieds/{id_ied}/configuracoes",
    response_model=schemas.ConfiguracaoOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_configuracao(
    id_ied: int,
    dados: schemas.ConfiguracaoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_config.criar_configuracao(db, id_ied, dados, usuario.id)


@router.get("/configuracoes/{id_configuracao}", response_model=schemas.ConfiguracaoOut)
def obter_configuracao(
    id_configuracao: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_config.obter_configuracao(db, id_configuracao)


@router.post(
    "/configuracoes/{id_configuracao}/arquivos",
    response_model=schemas.ConfiguracaoOut,
    status_code=status.HTTP_201_CREATED,
)
async def anexar_arquivo_configuracao(
    id_configuracao: int,
    arquivo: UploadFile = File(...),
    papel: schemas.PapelArquivo = Form("PRINCIPAL"),
    categoria: str | None = Form(None),
    descricao: str | None = Form(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    conteudo = await arquivo.read(service_config.MAX_ARQUIVO_BYTES + 1)
    if len(conteudo) > service_config.MAX_ARQUIVO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"O arquivo excede o limite de {service_config.MAX_ARQUIVO_BYTES // (1024 * 1024)} MB",
        )
    return service_config.anexar_arquivo(
        db,
        id_configuracao,
        conteudo,
        arquivo.filename or "",
        arquivo.content_type,
        papel,
        categoria,
        descricao,
        usuario.id,
    )


@router.delete(
    "/configuracoes/{id_configuracao}/arquivos/{id_arquivo}",
    response_model=schemas.ConfiguracaoOut,
)
def remover_arquivo_configuracao(
    id_configuracao: int,
    id_arquivo: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_config.remover_arquivo_configuracao(db, id_configuracao, id_arquivo, usuario.id)


@router.post(
    "/configuracoes/{id_configuracao}/validacoes",
    response_model=schemas.ConfiguracaoOut,
    status_code=status.HTTP_201_CREATED,
)
def validar_configuracao(
    id_configuracao: int,
    dados: schemas.ValidacaoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_config.validar_configuracao(db, id_configuracao, dados, usuario.id)


@router.get("/arquivos/{id_arquivo}/download")
def baixar_arquivo(
    id_arquivo: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    arquivo, caminho = service_config.caminho_download(db, id_arquivo)
    return FileResponse(
        path=str(caminho),
        filename=arquivo.nome_original,
        media_type=arquivo.mime_type or "application/octet-stream",
    )


# --------------------------------------------------------------------------- #
# Fase 3 - Gestao de alteracoes e comparador de configuracoes
# --------------------------------------------------------------------------- #


@router.get("/alteracoes/resumo", response_model=schemas.ResumoAlteracaoOut)
def resumo_alteracoes(
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_alteracoes.resumo_alteracoes(db)


@router.get("/alteracoes", response_model=schemas.SolicitacaoAlteracaoLista)
def listar_alteracoes(
    id_ied: int | None = None,
    status: str | None = None,
    tipo: str | None = None,
    prioridade: str | None = None,
    busca: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_alteracoes.listar_alteracoes(
        db, id_ied, status, tipo, prioridade, busca, page, page_size
    )


@router.post("/alteracoes", response_model=schemas.SolicitacaoAlteracaoDetalhe, status_code=status.HTTP_201_CREATED)
def criar_alteracao(
    dados: schemas.SolicitacaoAlteracaoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_alteracoes.criar_alteracao(db, dados, usuario.id)


@router.get("/alteracoes/{id_solicitacao}", response_model=schemas.SolicitacaoAlteracaoDetalhe)
def obter_alteracao(
    id_solicitacao: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_alteracoes.obter_alteracao(db, id_solicitacao)


@router.put("/alteracoes/{id_solicitacao}", response_model=schemas.SolicitacaoAlteracaoDetalhe)
def atualizar_alteracao(
    id_solicitacao: int,
    dados: schemas.SolicitacaoAlteracaoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_alteracoes.atualizar_alteracao(db, id_solicitacao, dados, usuario.id)


@router.post(
    "/alteracoes/{id_solicitacao}/itens",
    response_model=schemas.SolicitacaoAlteracaoDetalhe,
    status_code=status.HTTP_201_CREATED,
)
def adicionar_alteracao_item(
    id_solicitacao: int,
    dados: schemas.AlteracaoItemCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_alteracoes.adicionar_item(db, id_solicitacao, dados, usuario.id)


@router.put(
    "/alteracoes/{id_solicitacao}/itens/{id_alteracao_item}",
    response_model=schemas.SolicitacaoAlteracaoDetalhe,
)
def atualizar_alteracao_item(
    id_solicitacao: int,
    id_alteracao_item: int,
    dados: schemas.AlteracaoItemUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_alteracoes.atualizar_item(db, id_solicitacao, id_alteracao_item, dados, usuario.id)


@router.delete(
    "/alteracoes/{id_solicitacao}/itens/{id_alteracao_item}",
    response_model=schemas.SolicitacaoAlteracaoDetalhe,
)
def remover_alteracao_item(
    id_solicitacao: int,
    id_alteracao_item: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_alteracoes.remover_item(db, id_solicitacao, id_alteracao_item, usuario.id)


@router.post(
    "/alteracoes/{id_solicitacao}/itens/importar",
    response_model=schemas.SolicitacaoAlteracaoDetalhe,
)
def importar_itens_alteracao(
    id_solicitacao: int,
    dados: schemas.ImportarItensAlteracao,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_alteracoes.importar_itens(db, id_solicitacao, dados, usuario.id)


@router.post("/alteracoes/{id_solicitacao}/submeter", response_model=schemas.SolicitacaoAlteracaoDetalhe)
def submeter_alteracao(
    id_solicitacao: int,
    dados: schemas.TransicaoAlteracao,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_alteracoes.submeter(db, id_solicitacao, dados, usuario.id)


@router.post("/alteracoes/{id_solicitacao}/aprovar", response_model=schemas.SolicitacaoAlteracaoDetalhe)
def aprovar_alteracao(
    id_solicitacao: int,
    dados: schemas.TransicaoAlteracao,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_alteracoes.aprovar(db, id_solicitacao, dados, usuario.id)


@router.post("/alteracoes/{id_solicitacao}/rejeitar", response_model=schemas.SolicitacaoAlteracaoDetalhe)
def rejeitar_alteracao(
    id_solicitacao: int,
    dados: schemas.TransicaoAlteracao,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_alteracoes.rejeitar(db, id_solicitacao, dados, usuario.id)


@router.post("/alteracoes/{id_solicitacao}/cancelar", response_model=schemas.SolicitacaoAlteracaoDetalhe)
def cancelar_alteracao(
    id_solicitacao: int,
    dados: schemas.TransicaoAlteracao,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_alteracoes.cancelar(db, id_solicitacao, dados, usuario.id)


@router.post("/alteracoes/{id_solicitacao}/implantar", response_model=schemas.SolicitacaoAlteracaoDetalhe)
def implantar_alteracao(
    id_solicitacao: int,
    dados: schemas.ImplantacaoAlteracao,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_alteracoes.implantar(db, id_solicitacao, dados, usuario.id)


@router.post("/alteracoes/{id_solicitacao}/validar", response_model=schemas.SolicitacaoAlteracaoDetalhe)
def validar_alteracao(
    id_solicitacao: int,
    dados: schemas.ValidacaoAlteracao,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_alteracoes.validar(db, id_solicitacao, dados, usuario.id)


@router.get("/comparacoes/grupos", response_model=schemas.ComparacaoGruposOut)
def comparar_grupos(
    id_grupo_base: int,
    id_grupo_destino: int,
    somente_diferencas: bool = True,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_alteracoes.comparar_grupos(db, id_grupo_base, id_grupo_destino, somente_diferencas)


@router.get("/comparacoes/configuracoes", response_model=schemas.ComparacaoGruposOut)
def comparar_configuracoes(
    id_configuracao_base: int,
    id_configuracao_destino: int,
    somente_diferencas: bool = True,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_alteracoes.comparar_configuracoes(
        db, id_configuracao_base, id_configuracao_destino, somente_diferencas
    )


# --------------------------------------------------------------------------- #
# Fase 4 - Engenharia de protecao (comunicacao, circuitos/sinais e ensaios)
# --------------------------------------------------------------------------- #


@router.get("/engenharia/resumo", response_model=schemas.ResumoEngenhariaOut)
def resumo_engenharia(
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_engenharia.resumo_engenharia(db)


@router.get("/ieds/{id_ied}/interfaces", response_model=list[schemas.InterfaceComunicacaoOut])
def listar_interfaces(
    id_ied: int,
    offset: int = Query(0, ge=0),
    limite: int = Query(LIMITE_COLECAO_PADRAO, ge=1, le=LIMITE_COLECAO_MAX),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    itens = service_engenharia.listar_interfaces(db, id_ied)
    return _paginar(itens, offset, limite)


@router.post(
    "/ieds/{id_ied}/interfaces",
    response_model=schemas.InterfaceComunicacaoOut,
    status_code=status.HTTP_201_CREATED,
)
def criar_interface(
    id_ied: int,
    dados: schemas.InterfaceComunicacaoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.criar_interface(db, id_ied, dados, usuario.id)


@router.put("/interfaces/{id_interface}", response_model=schemas.InterfaceComunicacaoOut)
def atualizar_interface(
    id_interface: int,
    dados: schemas.InterfaceComunicacaoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.atualizar_interface(db, id_interface, dados, usuario.id)


@router.delete("/interfaces/{id_interface}", status_code=status.HTTP_204_NO_CONTENT)
def remover_interface(
    id_interface: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    service_engenharia.remover_interface(db, id_interface)


@router.post(
    "/interfaces/{id_interface}/protocolos",
    response_model=schemas.InterfaceComunicacaoOut,
    status_code=status.HTTP_201_CREATED,
)
def adicionar_protocolo(
    id_interface: int,
    dados: schemas.ProtocoloComunicacaoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.adicionar_protocolo(db, id_interface, dados, usuario.id)


@router.put("/protocolos/{id_protocolo}", response_model=schemas.InterfaceComunicacaoOut)
def atualizar_protocolo(
    id_protocolo: int,
    dados: schemas.ProtocoloComunicacaoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.atualizar_protocolo(db, id_protocolo, dados, usuario.id)


@router.delete("/protocolos/{id_protocolo}", response_model=schemas.InterfaceComunicacaoOut)
def remover_protocolo(
    id_protocolo: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.remover_protocolo(db, id_protocolo)


@router.get("/ieds/{id_ied}/goose", response_model=list[schemas.GooseControleOut])
def listar_goose(
    id_ied: int,
    offset: int = Query(0, ge=0),
    limite: int = Query(LIMITE_COLECAO_PADRAO, ge=1, le=LIMITE_COLECAO_MAX),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    itens = service_engenharia.listar_goose(db, id_ied)
    return _paginar(itens, offset, limite)


@router.post("/ieds/{id_ied}/goose", response_model=schemas.GooseControleOut, status_code=status.HTTP_201_CREATED)
def criar_goose(
    id_ied: int,
    dados: schemas.GooseControleCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.criar_goose(db, id_ied, dados, usuario.id)


@router.put("/goose/{id_goose}", response_model=schemas.GooseControleOut)
def atualizar_goose(
    id_goose: int,
    dados: schemas.GooseControleUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.atualizar_goose(db, id_goose, dados, usuario.id)


@router.delete("/goose/{id_goose}", status_code=status.HTTP_204_NO_CONTENT)
def remover_goose(
    id_goose: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    service_engenharia.remover_goose(db, id_goose)


@router.get("/ieds/{id_ied}/circuitos", response_model=list[schemas.CircuitoOut])
def listar_circuitos(
    id_ied: int,
    offset: int = Query(0, ge=0),
    limite: int = Query(LIMITE_COLECAO_PADRAO, ge=1, le=LIMITE_COLECAO_MAX),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    itens = service_engenharia.listar_circuitos(db, id_ied)
    return _paginar(itens, offset, limite)


@router.post("/ieds/{id_ied}/circuitos", response_model=schemas.CircuitoOut, status_code=status.HTTP_201_CREATED)
def criar_circuito(
    id_ied: int,
    dados: schemas.CircuitoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.criar_circuito(db, id_ied, dados, usuario.id)


@router.put("/circuitos/{id_circuito}", response_model=schemas.CircuitoOut)
def atualizar_circuito(
    id_circuito: int,
    dados: schemas.CircuitoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.atualizar_circuito(db, id_circuito, dados, usuario.id)


@router.delete("/circuitos/{id_circuito}", status_code=status.HTTP_204_NO_CONTENT)
def remover_circuito(
    id_circuito: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    service_engenharia.remover_circuito(db, id_circuito)


@router.get("/ieds/{id_ied}/sinais", response_model=list[schemas.SinalOut])
def listar_sinais(
    id_ied: int,
    tipo: str | None = None,
    estado: str | None = None,
    id_ied_circuito: int | None = None,
    offset: int = Query(0, ge=0),
    limite: int = Query(LIMITE_COLECAO_PADRAO, ge=1, le=LIMITE_COLECAO_MAX),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    itens = service_engenharia.listar_sinais(db, id_ied, tipo, estado, id_ied_circuito)
    return _paginar(itens, offset, limite)


@router.post("/ieds/{id_ied}/sinais", response_model=schemas.SinalOut, status_code=status.HTTP_201_CREATED)
def criar_sinal(
    id_ied: int,
    dados: schemas.SinalCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.criar_sinal(db, id_ied, dados, usuario.id)


@router.put("/sinais/{id_sinal}", response_model=schemas.SinalOut)
def atualizar_sinal(
    id_sinal: int,
    dados: schemas.SinalUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.atualizar_sinal(db, id_sinal, dados, usuario.id)


@router.delete("/sinais/{id_sinal}", status_code=status.HTTP_204_NO_CONTENT)
def remover_sinal(
    id_sinal: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    service_engenharia.remover_sinal(db, id_sinal)


@router.get("/ensaios", response_model=schemas.EnsaioLista)
def listar_ensaios(
    id_ied: int | None = None,
    status: str | None = None,
    tipo: str | None = None,
    busca: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_engenharia.listar_ensaios(db, id_ied, status, tipo, busca, page, page_size)


@router.post("/ieds/{id_ied}/ensaios", response_model=schemas.EnsaioDetalhe, status_code=status.HTTP_201_CREATED)
def criar_ensaio(
    id_ied: int,
    dados: schemas.EnsaioCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.criar_ensaio(db, id_ied, dados, usuario.id)


@router.get("/ensaios/{id_ensaio}", response_model=schemas.EnsaioDetalhe)
def obter_ensaio(
    id_ensaio: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_engenharia.obter_ensaio(db, id_ensaio)


@router.put("/ensaios/{id_ensaio}", response_model=schemas.EnsaioDetalhe)
def atualizar_ensaio(
    id_ensaio: int,
    dados: schemas.EnsaioUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.atualizar_ensaio(db, id_ensaio, dados, usuario.id)


@router.post(
    "/ensaios/{id_ensaio}/itens",
    response_model=schemas.EnsaioDetalhe,
    status_code=status.HTTP_201_CREATED,
)
def adicionar_ensaio_item(
    id_ensaio: int,
    dados: schemas.EnsaioItemCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.adicionar_item(db, id_ensaio, dados, usuario.id)


@router.put("/ensaios/{id_ensaio}/itens/{id_item}", response_model=schemas.EnsaioDetalhe)
def atualizar_ensaio_item(
    id_ensaio: int,
    id_item: int,
    dados: schemas.EnsaioItemUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.atualizar_item(db, id_ensaio, id_item, dados, usuario.id)


@router.delete("/ensaios/{id_ensaio}/itens/{id_item}", response_model=schemas.EnsaioDetalhe)
def remover_ensaio_item(
    id_ensaio: int,
    id_item: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.remover_item(db, id_ensaio, id_item)


@router.post(
    "/ensaios/{id_ensaio}/arquivos",
    response_model=schemas.EnsaioDetalhe,
    status_code=status.HTTP_201_CREATED,
)
async def anexar_ensaio_arquivo(
    id_ensaio: int,
    arquivo: UploadFile = File(...),
    descricao: str | None = Form(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    conteudo = await arquivo.read()
    return service_engenharia.anexar_arquivo(
        db, id_ensaio, conteudo, arquivo.filename or "", arquivo.content_type, descricao, usuario.id
    )


@router.delete("/ensaio-arquivos/{id_ensaio_arquivo}", response_model=schemas.EnsaioDetalhe)
def remover_ensaio_arquivo(
    id_ensaio_arquivo: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_engenharia.remover_arquivo(db, id_ensaio_arquivo)


@router.get("/ensaio-arquivos/{id_ensaio_arquivo}/download")
def baixar_ensaio_arquivo(
    id_ensaio_arquivo: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    arquivo, caminho = service_engenharia.caminho_download_ensaio(db, id_ensaio_arquivo)
    return FileResponse(
        path=str(caminho),
        filename=arquivo.nome_original,
        media_type=arquivo.mime_type or "application/octet-stream",
    )


# --------------------------------------------------------------------------- #
# Fase 5 - Ocorrencias e indicadores (eventos, oscilografias e relatorios)
# --------------------------------------------------------------------------- #


@router.get("/ocorrencias/resumo", response_model=schemas.ResumoOcorrenciaOut)
def resumo_ocorrencias(
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_ocorrencias.resumo_ocorrencias(db)


@router.get("/ocorrencias/auditoria", response_model=list[schemas.AuditoriaOut])
def listar_auditoria_ocorrencias(
    id_ied: int | None = None,
    id_ocorrencia: int | None = None,
    acao: str | None = None,
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_ocorrencias.listar_auditoria(db, id_ied, id_ocorrencia, acao, limite, offset)


@router.get("/ocorrencias", response_model=schemas.OcorrenciaLista)
def listar_ocorrencias(
    id_ied: int | None = None,
    tipo: str | None = None,
    severidade: str | None = None,
    status_ocorrencia: str | None = Query(None, alias="status"),
    busca: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_ocorrencias.listar_ocorrencias(
        db, id_ied, tipo, severidade, status_ocorrencia, busca, page, page_size
    )


@router.get("/ieds/{id_ied}/ocorrencias", response_model=list[schemas.OcorrenciaOut])
def listar_ocorrencias_ied(
    id_ied: int,
    offset: int = Query(0, ge=0),
    limite: int = Query(LIMITE_COLECAO_PADRAO, ge=1, le=LIMITE_COLECAO_MAX),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    itens = service_ocorrencias.listar_ocorrencias_ied(db, id_ied)
    return _paginar(itens, offset, limite)


@router.post("/ieds/{id_ied}/ocorrencias", response_model=schemas.OcorrenciaDetalhe, status_code=status.HTTP_201_CREATED)
def criar_ocorrencia(
    id_ied: int,
    dados: schemas.OcorrenciaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_ocorrencias.criar_ocorrencia(db, id_ied, dados, usuario.id)


@router.get("/ocorrencias/{id_ocorrencia}", response_model=schemas.OcorrenciaDetalhe)
def obter_ocorrencia(
    id_ocorrencia: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_ocorrencias.obter_ocorrencia(db, id_ocorrencia)


@router.put("/ocorrencias/{id_ocorrencia}", response_model=schemas.OcorrenciaDetalhe)
def atualizar_ocorrencia(
    id_ocorrencia: int,
    dados: schemas.OcorrenciaUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_ocorrencias.atualizar_ocorrencia(db, id_ocorrencia, dados, usuario.id)


@router.delete("/ocorrencias/{id_ocorrencia}", status_code=status.HTTP_204_NO_CONTENT)
def remover_ocorrencia(
    id_ocorrencia: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    service_ocorrencias.remover_ocorrencia(db, id_ocorrencia)


@router.post("/ocorrencias/{id_ocorrencia}/encerrar", response_model=schemas.OcorrenciaDetalhe)
def encerrar_ocorrencia(
    id_ocorrencia: int,
    dados: schemas.EncerramentoOcorrencia | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_ocorrencias.encerrar_ocorrencia(db, id_ocorrencia, dados, usuario.id)


@router.post(
    "/ocorrencias/{id_ocorrencia}/arquivos",
    response_model=schemas.OcorrenciaDetalhe,
    status_code=status.HTTP_201_CREATED,
)
async def anexar_arquivo_ocorrencia(
    id_ocorrencia: int,
    arquivo: UploadFile = File(...),
    descricao: str | None = Form(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    conteudo = await arquivo.read()
    return service_ocorrencias.anexar_arquivo_ocorrencia(
        db, id_ocorrencia, conteudo, arquivo.filename or "", arquivo.content_type, descricao, usuario.id
    )


@router.delete("/ocorrencia-arquivos/{id_ocorrencia_arquivo}", response_model=schemas.OcorrenciaDetalhe)
def remover_arquivo_ocorrencia(
    id_ocorrencia_arquivo: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_ocorrencias.remover_arquivo_ocorrencia(db, id_ocorrencia_arquivo, usuario.id)


@router.get("/ocorrencia-arquivos/{id_ocorrencia_arquivo}/download")
def baixar_arquivo_ocorrencia(
    id_ocorrencia_arquivo: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    arquivo, caminho = service_ocorrencias.caminho_download_ocorrencia(db, id_ocorrencia_arquivo)
    return FileResponse(
        path=str(caminho),
        filename=arquivo.nome_original,
        media_type=arquivo.mime_type or "application/octet-stream",
    )


@router.get("/oscilografias", response_model=schemas.OscilografiaLista)
def listar_oscilografias(
    id_ied: int | None = None,
    tipo: str | None = None,
    id_ocorrencia: int | None = None,
    busca: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_ocorrencias.listar_oscilografias(db, id_ied, tipo, id_ocorrencia, busca, page, page_size)


@router.get("/ieds/{id_ied}/oscilografias", response_model=list[schemas.OscilografiaOut])
def listar_oscilografias_ied(
    id_ied: int,
    offset: int = Query(0, ge=0),
    limite: int = Query(LIMITE_COLECAO_PADRAO, ge=1, le=LIMITE_COLECAO_MAX),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    itens = service_ocorrencias.listar_oscilografias_ied(db, id_ied)
    return _paginar(itens, offset, limite)


@router.post(
    "/ieds/{id_ied}/oscilografias", response_model=schemas.OscilografiaDetalhe, status_code=status.HTTP_201_CREATED
)
def criar_oscilografia(
    id_ied: int,
    dados: schemas.OscilografiaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_ocorrencias.criar_oscilografia(db, id_ied, dados, usuario.id)


@router.get("/oscilografias/{id_oscilografia}", response_model=schemas.OscilografiaDetalhe)
def obter_oscilografia(
    id_oscilografia: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_ocorrencias.obter_oscilografia(db, id_oscilografia)


@router.put("/oscilografias/{id_oscilografia}", response_model=schemas.OscilografiaDetalhe)
def atualizar_oscilografia(
    id_oscilografia: int,
    dados: schemas.OscilografiaUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_ocorrencias.atualizar_oscilografia(db, id_oscilografia, dados, usuario.id)


@router.delete("/oscilografias/{id_oscilografia}", status_code=status.HTTP_204_NO_CONTENT)
def remover_oscilografia(
    id_oscilografia: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    service_ocorrencias.remover_oscilografia(db, id_oscilografia)


@router.post(
    "/oscilografias/{id_oscilografia}/arquivos",
    response_model=schemas.OscilografiaDetalhe,
    status_code=status.HTTP_201_CREATED,
)
async def anexar_arquivo_oscilografia(
    id_oscilografia: int,
    arquivo: UploadFile = File(...),
    descricao: str | None = Form(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    conteudo = await arquivo.read()
    return service_ocorrencias.anexar_arquivo_oscilografia(
        db, id_oscilografia, conteudo, arquivo.filename or "", arquivo.content_type, descricao, usuario.id
    )


@router.delete("/oscilografia-arquivos/{id_oscilografia_arquivo}", response_model=schemas.OscilografiaDetalhe)
def remover_arquivo_oscilografia(
    id_oscilografia_arquivo: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_ocorrencias.remover_arquivo_oscilografia(db, id_oscilografia_arquivo)


@router.get("/oscilografia-arquivos/{id_oscilografia_arquivo}/download")
def baixar_arquivo_oscilografia(
    id_oscilografia_arquivo: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    arquivo, caminho = service_ocorrencias.caminho_download_oscilografia(db, id_oscilografia_arquivo)
    return FileResponse(
        path=str(caminho),
        filename=arquivo.nome_original,
        media_type=arquivo.mime_type or "application/octet-stream",
    )


@router.get("/relatorios", response_model=schemas.RelatorioLista)
def listar_relatorios(
    id_ied: int | None = None,
    tipo: str | None = None,
    status_relatorio: str | None = Query(None, alias="status"),
    id_ocorrencia: int | None = None,
    busca: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_ocorrencias.listar_relatorios(
        db, id_ied, tipo, status_relatorio, id_ocorrencia, busca, page, page_size
    )


@router.get("/ieds/{id_ied}/relatorios", response_model=list[schemas.RelatorioOut])
def listar_relatorios_ied(
    id_ied: int,
    offset: int = Query(0, ge=0),
    limite: int = Query(LIMITE_COLECAO_PADRAO, ge=1, le=LIMITE_COLECAO_MAX),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    itens = service_ocorrencias.listar_relatorios_ied(db, id_ied)
    return _paginar(itens, offset, limite)


@router.post("/ieds/{id_ied}/relatorios", response_model=schemas.RelatorioDetalhe, status_code=status.HTTP_201_CREATED)
def criar_relatorio(
    id_ied: int,
    dados: schemas.RelatorioCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_ocorrencias.criar_relatorio(db, id_ied, dados, usuario.id)


@router.get("/relatorios/{id_relatorio}", response_model=schemas.RelatorioDetalhe)
def obter_relatorio(
    id_relatorio: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    return service_ocorrencias.obter_relatorio(db, id_relatorio)


@router.put("/relatorios/{id_relatorio}", response_model=schemas.RelatorioDetalhe)
def atualizar_relatorio(
    id_relatorio: int,
    dados: schemas.RelatorioUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_ocorrencias.atualizar_relatorio(db, id_relatorio, dados, usuario.id)


@router.delete("/relatorios/{id_relatorio}", status_code=status.HTTP_204_NO_CONTENT)
def remover_relatorio(
    id_relatorio: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    service_ocorrencias.remover_relatorio(db, id_relatorio)


@router.post(
    "/relatorios/{id_relatorio}/arquivos",
    response_model=schemas.RelatorioDetalhe,
    status_code=status.HTTP_201_CREATED,
)
async def anexar_arquivo_relatorio(
    id_relatorio: int,
    arquivo: UploadFile = File(...),
    descricao: str | None = Form(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    conteudo = await arquivo.read()
    return service_ocorrencias.anexar_arquivo_relatorio(
        db, id_relatorio, conteudo, arquivo.filename or "", arquivo.content_type, descricao, usuario.id
    )


@router.delete("/relatorio-arquivos/{id_relatorio_arquivo}", response_model=schemas.RelatorioDetalhe)
def remover_arquivo_relatorio(
    id_relatorio_arquivo: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(ESCRITA),
):
    return service_ocorrencias.remover_arquivo_relatorio(db, id_relatorio_arquivo)


@router.get("/relatorio-arquivos/{id_relatorio_arquivo}/download")
def baixar_arquivo_relatorio(
    id_relatorio_arquivo: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
):
    arquivo, caminho = service_ocorrencias.caminho_download_relatorio(db, id_relatorio_arquivo)
    return FileResponse(
        path=str(caminho),
        filename=arquivo.nome_original,
        media_type=arquivo.mime_type or "application/octet-stream",
    )
