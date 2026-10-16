"""Fase 3 - Gestao de alteracoes e comparador de configuracoes."""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.OS_models import OrdemServico
from models.auth_models import Usuario

from . import models, schemas

STATUS_ABERTOS_EDICAO = ("RASCUNHO", "SUBMETIDA")
STATUS_CANCELAVEIS = ("RASCUNHO", "SUBMETIDA", "EM_ANALISE", "APROVADA")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _texto(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


def _commit(db: Session, mensagem_conflito: str):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=mensagem_conflito) from exc


def _ied(db: Session, id_ied: int) -> models.IED:
    item = db.query(models.IED).filter(models.IED.id_ied == id_ied).first()
    if not item:
        raise HTTPException(status_code=404, detail="IED não encontrado")
    return item


def _grupo(db: Session, id_grupo: int) -> models.IEDGrupoAjuste:
    item = (
        db.query(models.IEDGrupoAjuste)
        .filter(models.IEDGrupoAjuste.id_ied_grupo_ajuste == id_grupo)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Grupo de ajuste não encontrado")
    return item


def _configuracao(db: Session, id_configuracao: int) -> models.IEDConfiguracao:
    item = (
        db.query(models.IEDConfiguracao)
        .filter(models.IEDConfiguracao.id_ied_configuracao == id_configuracao)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    return item


def _nome_usuario(db: Session, id_usuario: int | None) -> str | None:
    if not id_usuario:
        return None
    usuario = db.query(Usuario).filter(Usuario.id == id_usuario).first()
    return usuario.nome if usuario else None


def _solicitacao(db: Session, id_solicitacao: int) -> models.SolicitacaoAlteracao:
    item = (
        db.query(models.SolicitacaoAlteracao)
        .filter(models.SolicitacaoAlteracao.id_solicitacao_alteracao == id_solicitacao)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Solicitação de alteração não encontrada")
    return item


def _parametro(db: Session, id_parametro: int) -> models.ParametroDefinicao:
    item = (
        db.query(models.ParametroDefinicao)
        .filter(models.ParametroDefinicao.id_parametro_definicao == id_parametro)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Parâmetro não encontrado")
    return item


def _item(db: Session, id_solicitacao: int, id_item: int) -> models.AlteracaoItem:
    item = (
        db.query(models.AlteracaoItem)
        .filter(
            models.AlteracaoItem.id_alteracao_item == id_item,
            models.AlteracaoItem.id_solicitacao_alteracao == id_solicitacao,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item da solicitação não encontrado")
    return item


# --------------------------------------------------------------------------- #
# Construtores de saida
# --------------------------------------------------------------------------- #


def _situacao(valor_atual: str | None, valor_proposto: str | None) -> str:
    if valor_proposto is None:
        return "REMOVIDO"
    if valor_atual is None:
        return "ADICIONADO"
    if valor_atual.strip() == valor_proposto.strip():
        return "IGUAL"
    return "ALTERADO"


def _item_out(
    item: models.AlteracaoItem,
    parametro: models.ParametroDefinicao,
    funcao: models.FuncaoANSI | None,
) -> schemas.AlteracaoItemOut:
    return schemas.AlteracaoItemOut(
        id_alteracao_item=item.id_alteracao_item,
        id_solicitacao_alteracao=item.id_solicitacao_alteracao,
        id_parametro_definicao=item.id_parametro_definicao,
        id_funcao_ansi=parametro.id_funcao_ansi,
        funcao_codigo=funcao.codigo if funcao else "",
        funcao_nome=funcao.nome if funcao else "",
        codigo=parametro.codigo,
        nome=parametro.nome,
        unidade=parametro.unidade,
        tipo_dado=parametro.tipo_dado,
        valor_atual=item.valor_atual,
        valor_proposto=item.valor_proposto,
        observacoes=item.observacoes,
        situacao=_situacao(item.valor_atual, item.valor_proposto),
        criado_em=item.criado_em,
        atualizado_em=item.atualizado_em,
    )


def _itens_out(db: Session, id_solicitacao: int) -> list[schemas.AlteracaoItemOut]:
    linhas = (
        db.query(models.AlteracaoItem, models.ParametroDefinicao, models.FuncaoANSI)
        .join(
            models.ParametroDefinicao,
            models.ParametroDefinicao.id_parametro_definicao == models.AlteracaoItem.id_parametro_definicao,
        )
        .join(models.FuncaoANSI, models.FuncaoANSI.id_funcao_ansi == models.ParametroDefinicao.id_funcao_ansi)
        .filter(models.AlteracaoItem.id_solicitacao_alteracao == id_solicitacao)
        .order_by(models.FuncaoANSI.codigo, models.ParametroDefinicao.codigo)
        .all()
    )
    return [_item_out(item, parametro, funcao) for item, parametro, funcao in linhas]


def _historico_out(db: Session, registros: list[models.AlteracaoHistorico]) -> list[schemas.AlteracaoHistoricoOut]:
    return [
        schemas.AlteracaoHistoricoOut(
            id_alteracao_historico=registro.id_alteracao_historico,
            acao=registro.acao,
            status_anterior=registro.status_anterior,
            status_novo=registro.status_novo,
            comentario=registro.comentario,
            id_usuario=registro.id_usuario,
            nome_usuario=_nome_usuario(db, registro.id_usuario),
            criado_em=registro.criado_em,
        )
        for registro in registros
    ]


def _solicitacao_out(
    db: Session,
    registro: models.SolicitacaoAlteracao,
    qtd_itens: int | None = None,
    detalhado: bool = False,
):
    if qtd_itens is None:
        qtd_itens = (
            db.query(func.count(models.AlteracaoItem.id_alteracao_item))
            .filter(models.AlteracaoItem.id_solicitacao_alteracao == registro.id_solicitacao_alteracao)
            .scalar()
            or 0
        )
    grupo = _grupo(db, registro.id_grupo_ajuste) if registro.id_grupo_ajuste else None
    base = schemas.SolicitacaoAlteracaoOut(
        id_solicitacao_alteracao=registro.id_solicitacao_alteracao,
        numero=registro.numero,
        id_ied=registro.id_ied,
        titulo=registro.titulo,
        descricao=registro.descricao,
        tipo=registro.tipo,
        prioridade=registro.prioridade,
        status=registro.status,
        id_configuracao_origem=registro.id_configuracao_origem,
        id_configuracao_resultante=registro.id_configuracao_resultante,
        id_grupo_ajuste=registro.id_grupo_ajuste,
        grupo_ajuste_nome=grupo.nome if grupo else None,
        id_os=registro.id_os,
        justificativa=registro.justificativa,
        observacoes=registro.observacoes,
        data_necessidade=registro.data_necessidade,
        data_implantacao=registro.data_implantacao,
        data_validacao=registro.data_validacao,
        resultado_validacao=registro.resultado_validacao,
        id_usuario_solicitante=registro.id_usuario_solicitante,
        nome_solicitante=_nome_usuario(db, registro.id_usuario_solicitante),
        id_usuario_aprovador=registro.id_usuario_aprovador,
        nome_aprovador=_nome_usuario(db, registro.id_usuario_aprovador),
        id_usuario_implantador=registro.id_usuario_implantador,
        nome_implantador=_nome_usuario(db, registro.id_usuario_implantador),
        id_usuario_validador=registro.id_usuario_validador,
        nome_validador=_nome_usuario(db, registro.id_usuario_validador),
        id_usuario_reversao=registro.id_usuario_reversao,
        nome_usuario_reversao=_nome_usuario(db, registro.id_usuario_reversao),
        id_configuracao_rollback=registro.id_configuracao_rollback,
        data_reversao=registro.data_reversao,
        evidencia_implantacao=registro.evidencia_implantacao,
        quantidade_itens=qtd_itens,
        versao=registro.versao,
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )
    if not detalhado:
        return base
    historico = (
        db.query(models.AlteracaoHistorico)
        .filter(models.AlteracaoHistorico.id_solicitacao_alteracao == registro.id_solicitacao_alteracao)
        .order_by(models.AlteracaoHistorico.id_alteracao_historico)
        .all()
    )
    return schemas.SolicitacaoAlteracaoDetalhe(
        **base.model_dump(),
        itens=_itens_out(db, registro.id_solicitacao_alteracao),
        historico=_historico_out(db, historico),
    )


def _registrar_historico(
    db: Session,
    registro: models.SolicitacaoAlteracao,
    acao: schemas.AcaoAlteracao,
    status_novo: str | None,
    id_usuario: int,
    comentario: str | None = None,
) -> None:
    db.add(
        models.AlteracaoHistorico(
            id_solicitacao_alteracao=registro.id_solicitacao_alteracao,
            acao=acao,
            status_anterior=registro.status,
            status_novo=status_novo,
            comentario=_texto(comentario),
            id_usuario=id_usuario,
        )
    )


def _validar_configuracao_do_ied(db: Session, id_configuracao: int, id_ied: int) -> models.IEDConfiguracao:
    config = _configuracao(db, id_configuracao)
    if config.id_ied != id_ied:
        raise HTTPException(status_code=400, detail="A configuração não pertence a este IED")
    return config


# --------------------------------------------------------------------------- #
# CRUD da solicitacao
# --------------------------------------------------------------------------- #


def listar_alteracoes(
    db: Session,
    id_ied: int | None,
    status: str | None,
    tipo: str | None,
    prioridade: str | None,
    busca: str | None,
    page: int,
    page_size: int,
) -> schemas.SolicitacaoAlteracaoLista:
    query = db.query(models.SolicitacaoAlteracao)
    if id_ied:
        query = query.filter(models.SolicitacaoAlteracao.id_ied == id_ied)
    if status:
        query = query.filter(models.SolicitacaoAlteracao.status == status)
    if tipo:
        query = query.filter(models.SolicitacaoAlteracao.tipo == tipo)
    if prioridade:
        query = query.filter(models.SolicitacaoAlteracao.prioridade == prioridade)
    if busca:
        termo = f"%{busca.strip()}%"
        filtros = [
            models.SolicitacaoAlteracao.titulo.ilike(termo),
            models.SolicitacaoAlteracao.descricao.ilike(termo),
        ]
        if busca.strip().isdigit():
            filtros.append(models.SolicitacaoAlteracao.numero == int(busca.strip()))
        query = query.filter(or_(*filtros))
    total = query.count()
    linhas = (
        query.order_by(models.SolicitacaoAlteracao.numero.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    ids = [linha.id_solicitacao_alteracao for linha in linhas]
    contagem: dict[int, int] = {}
    if ids:
        contagem = dict(
            db.query(models.AlteracaoItem.id_solicitacao_alteracao, func.count(models.AlteracaoItem.id_alteracao_item))
            .filter(models.AlteracaoItem.id_solicitacao_alteracao.in_(ids))
            .group_by(models.AlteracaoItem.id_solicitacao_alteracao)
            .all()
        )
    itens = [
        _solicitacao_out(db, linha, contagem.get(linha.id_solicitacao_alteracao, 0))
        for linha in linhas
    ]
    return schemas.SolicitacaoAlteracaoLista(total=total, page=page, page_size=page_size, items=itens)


def obter_alteracao(db: Session, id_solicitacao: int) -> schemas.SolicitacaoAlteracaoDetalhe:
    return _solicitacao_out(db, _solicitacao(db, id_solicitacao), detalhado=True)


def criar_alteracao(
    db: Session, dados: schemas.SolicitacaoAlteracaoCreate, id_usuario: int
) -> schemas.SolicitacaoAlteracaoDetalhe:
    _ied(db, dados.id_ied)
    if dados.id_grupo_ajuste:
        grupo = _grupo(db, dados.id_grupo_ajuste)
        if grupo.id_ied != dados.id_ied:
            raise HTTPException(status_code=400, detail="O grupo de ajuste não pertence a este IED")
    if dados.id_configuracao_origem:
        _validar_configuracao_do_ied(db, dados.id_configuracao_origem, dados.id_ied)
    if dados.id_os and not db.query(OrdemServico.id_os).filter(OrdemServico.id_os == dados.id_os).first():
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")
    if dados.id_usuario_solicitante and not db.query(Usuario.id).filter(Usuario.id == dados.id_usuario_solicitante).first():
        raise HTTPException(status_code=404, detail="Usuário solicitante não encontrado")

    ultimo = db.query(func.max(models.SolicitacaoAlteracao.numero)).scalar() or 0
    registro = models.SolicitacaoAlteracao(
        numero=ultimo + 1,
        id_ied=dados.id_ied,
        titulo=dados.titulo.strip(),
        descricao=_texto(dados.descricao),
        tipo=dados.tipo,
        prioridade=dados.prioridade,
        status="RASCUNHO",
        id_configuracao_origem=dados.id_configuracao_origem,
        id_grupo_ajuste=dados.id_grupo_ajuste,
        id_os=dados.id_os,
        justificativa=_texto(dados.justificativa),
        observacoes=_texto(dados.observacoes),
        data_necessidade=dados.data_necessidade,
        id_usuario_solicitante=dados.id_usuario_solicitante or id_usuario,
        id_usuario_criacao=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    db.add(registro)
    db.flush()
    _registrar_historico(db, registro, "CRIACAO", "RASCUNHO", id_usuario, "Solicitação criada")
    _commit(db, "Não foi possível registrar a solicitação de alteração")
    db.refresh(registro)
    return _solicitacao_out(db, registro, detalhado=True)


def atualizar_alteracao(
    db: Session, id_solicitacao: int, dados: schemas.SolicitacaoAlteracaoUpdate, id_usuario: int
) -> schemas.SolicitacaoAlteracaoDetalhe:
    registro = _solicitacao(db, id_solicitacao)
    if registro.versao != dados.versao:
        raise HTTPException(
            status_code=409,
            detail="A solicitação foi alterada por outro usuário. Recarregue os dados.",
        )
    if registro.status not in STATUS_ABERTOS_EDICAO:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível editar uma solicitação com status {registro.status}",
        )
    payload = dados.model_dump(exclude_unset=True, exclude={"versao"})
    if "id_grupo_ajuste" in payload and payload["id_grupo_ajuste"]:
        grupo = _grupo(db, payload["id_grupo_ajuste"])
        if grupo.id_ied != registro.id_ied:
            raise HTTPException(status_code=400, detail="O grupo de ajuste não pertence a este IED")
    if "id_configuracao_origem" in payload and payload["id_configuracao_origem"]:
        _validar_configuracao_do_ied(db, payload["id_configuracao_origem"], registro.id_ied)
    if "id_os" in payload and payload["id_os"]:
        if not db.query(OrdemServico.id_os).filter(OrdemServico.id_os == payload["id_os"]).first():
            raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")
    if "titulo" in payload and payload["titulo"]:
        payload["titulo"] = payload["titulo"].strip()
    for campo in ("descricao", "justificativa", "observacoes"):
        if campo in payload:
            payload[campo] = _texto(payload[campo])
    for campo, valor in payload.items():
        setattr(registro, campo, valor)
    registro.versao += 1
    registro.id_usuario_atualizacao = id_usuario
    _registrar_historico(db, registro, "ATUALIZACAO", registro.status, id_usuario, "Dados da solicitação atualizados")
    _commit(db, "Não foi possível atualizar a solicitação")
    db.refresh(registro)
    return _solicitacao_out(db, registro, detalhado=True)


# --------------------------------------------------------------------------- #
# Itens da solicitacao
# --------------------------------------------------------------------------- #


def adicionar_item(
    db: Session, id_solicitacao: int, dados: schemas.AlteracaoItemCreate, id_usuario: int
) -> schemas.SolicitacaoAlteracaoDetalhe:
    registro = _solicitacao(db, id_solicitacao)
    if registro.status not in STATUS_ABERTOS_EDICAO:
        raise HTTPException(status_code=400, detail=f"Solicitação com status {registro.status} não aceita novos itens")
    _parametro(db, dados.id_parametro_definicao)
    item = models.AlteracaoItem(
        id_solicitacao_alteracao=id_solicitacao,
        id_parametro_definicao=dados.id_parametro_definicao,
        valor_atual=_texto(dados.valor_atual),
        valor_proposto=_texto(dados.valor_proposto),
        observacoes=_texto(dados.observacoes),
        id_usuario_criacao=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    db.add(item)
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Este parâmetro já foi incluído na solicitação")
    db.refresh(registro)
    return _solicitacao_out(db, registro, detalhado=True)


def atualizar_item(
    db: Session, id_solicitacao: int, id_item: int, dados: schemas.AlteracaoItemUpdate, id_usuario: int
) -> schemas.SolicitacaoAlteracaoDetalhe:
    registro = _solicitacao(db, id_solicitacao)
    if registro.status not in STATUS_ABERTOS_EDICAO:
        raise HTTPException(status_code=400, detail=f"Solicitação com status {registro.status} não pode ser editada")
    item = _item(db, id_solicitacao, id_item)
    payload = dados.model_dump(exclude_unset=True)
    for campo in ("valor_atual", "valor_proposto", "observacoes"):
        if campo in payload:
            payload[campo] = _texto(payload[campo])
    for campo, valor in payload.items():
        setattr(item, campo, valor)
    item.id_usuario_atualizacao = id_usuario
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível atualizar o item")
    db.refresh(registro)
    return _solicitacao_out(db, registro, detalhado=True)


def remover_item(db: Session, id_solicitacao: int, id_item: int, id_usuario: int) -> schemas.SolicitacaoAlteracaoDetalhe:
    registro = _solicitacao(db, id_solicitacao)
    if registro.status not in STATUS_ABERTOS_EDICAO:
        raise HTTPException(status_code=400, detail=f"Solicitação com status {registro.status} não pode ser editada")
    item = _item(db, id_solicitacao, id_item)
    db.delete(item)
    registro.id_usuario_atualizacao = id_usuario
    db.commit()
    db.refresh(registro)
    return _solicitacao_out(db, registro, detalhado=True)


def importar_itens(
    db: Session, id_solicitacao: int, dados: schemas.ImportarItensAlteracao, id_usuario: int
) -> schemas.SolicitacaoAlteracaoDetalhe:
    registro = _solicitacao(db, id_solicitacao)
    if registro.status not in STATUS_ABERTOS_EDICAO:
        raise HTTPException(status_code=400, detail=f"Solicitação com status {registro.status} não pode ser editada")
    grupo_base = _grupo(db, dados.id_grupo_base)
    grupo_destino = _grupo(db, dados.id_grupo_destino)
    if grupo_base.id_ied != registro.id_ied or grupo_destino.id_ied != registro.id_ied:
        raise HTTPException(status_code=400, detail="Os grupos informados não pertencem a este IED")

    comparacao = comparar_grupos(db, dados.id_grupo_base, dados.id_grupo_destino, somente_diferencas=False)
    atuais = {
        item.id_parametro_definicao: item
        for item in db.query(models.AlteracaoItem)
        .filter(models.AlteracaoItem.id_solicitacao_alteracao == id_solicitacao)
        .all()
    }
    importados = 0
    for linha in comparacao.itens:
        if linha.situacao == "IGUAL" and not dados.incluir_iguais:
            continue
        existente = atuais.get(linha.id_parametro_definicao)
        if existente is None:
            db.add(
                models.AlteracaoItem(
                    id_solicitacao_alteracao=id_solicitacao,
                    id_parametro_definicao=linha.id_parametro_definicao,
                    valor_atual=linha.valor_base,
                    valor_proposto=linha.valor_destino,
                    id_usuario_criacao=id_usuario,
                    id_usuario_atualizacao=id_usuario,
                )
            )
        else:
            existente.valor_atual = linha.valor_base
            existente.valor_proposto = linha.valor_destino
            existente.id_usuario_atualizacao = id_usuario
        importados += 1
    registro.id_grupo_ajuste = dados.id_grupo_destino
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível importar os itens da comparação")
    db.refresh(registro)
    return _solicitacao_out(db, registro, detalhado=True)


# --------------------------------------------------------------------------- #
# Transicoes de status
# --------------------------------------------------------------------------- #


def submeter(
    db: Session, id_solicitacao: int, dados: schemas.TransicaoAlteracao, id_usuario: int
) -> schemas.SolicitacaoAlteracaoDetalhe:
    registro = _solicitacao(db, id_solicitacao)
    if registro.status != "RASCUNHO":
        raise HTTPException(status_code=400, detail="Somente solicitações em rascunho podem ser submetidas")
    total_itens = (
        db.query(func.count(models.AlteracaoItem.id_alteracao_item))
        .filter(models.AlteracaoItem.id_solicitacao_alteracao == id_solicitacao)
        .scalar()
        or 0
    )
    if total_itens == 0:
        raise HTTPException(status_code=400, detail="Inclua ao menos um item antes de submeter a solicitação")
    _registrar_historico(db, registro, "SUBMISSAO", "SUBMETIDA", id_usuario, dados.comentario)
    registro.status = "SUBMETIDA"
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível submeter a solicitação")
    db.refresh(registro)
    return _solicitacao_out(db, registro, detalhado=True)


def aprovar(
    db: Session, id_solicitacao: int, dados: schemas.TransicaoAlteracao, id_usuario: int
) -> schemas.SolicitacaoAlteracaoDetalhe:
    registro = _solicitacao(db, id_solicitacao)
    if registro.status not in ("SUBMETIDA", "EM_ANALISE"):
        raise HTTPException(status_code=400, detail="Somente solicitações em análise podem ser aprovadas")
    if registro.id_usuario_solicitante == id_usuario:
        raise HTTPException(status_code=403, detail="O solicitante não pode aprovar a própria alteração")
    _registrar_historico(db, registro, "APROVACAO", "APROVADA", id_usuario, dados.comentario)
    registro.status = "APROVADA"
    registro.id_usuario_aprovador = id_usuario
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível aprovar a solicitação")
    db.refresh(registro)
    return _solicitacao_out(db, registro, detalhado=True)


def rejeitar(
    db: Session, id_solicitacao: int, dados: schemas.TransicaoAlteracao, id_usuario: int
) -> schemas.SolicitacaoAlteracaoDetalhe:
    registro = _solicitacao(db, id_solicitacao)
    if registro.status not in ("SUBMETIDA", "EM_ANALISE"):
        raise HTTPException(status_code=400, detail="Somente solicitações em análise podem ser rejeitadas")
    if registro.id_usuario_solicitante == id_usuario:
        raise HTTPException(status_code=403, detail="O solicitante não pode rejeitar a própria alteração")
    _registrar_historico(db, registro, "REJEICAO", "REJEITADA", id_usuario, dados.comentario)
    registro.status = "REJEITADA"
    registro.id_usuario_aprovador = id_usuario
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível rejeitar a solicitação")
    db.refresh(registro)
    return _solicitacao_out(db, registro, detalhado=True)


def cancelar(
    db: Session, id_solicitacao: int, dados: schemas.TransicaoAlteracao, id_usuario: int
) -> schemas.SolicitacaoAlteracaoDetalhe:
    registro = _solicitacao(db, id_solicitacao)
    if registro.status not in STATUS_CANCELAVEIS:
        raise HTTPException(status_code=400, detail=f"Solicitação com status {registro.status} não pode ser cancelada")
    _registrar_historico(db, registro, "CANCELAMENTO", "CANCELADA", id_usuario, dados.comentario)
    registro.status = "CANCELADA"
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível cancelar a solicitação")
    db.refresh(registro)
    return _solicitacao_out(db, registro, detalhado=True)


def implantar(
    db: Session, id_solicitacao: int, dados: schemas.ImplantacaoAlteracao, id_usuario: int
) -> schemas.SolicitacaoAlteracaoDetalhe:
    registro = _solicitacao(db, id_solicitacao)
    if registro.status != "APROVADA":
        raise HTTPException(status_code=400, detail="Somente solicitações aprovadas podem ser implantadas")
    if dados.id_configuracao_resultante:
        _validar_configuracao_do_ied(db, dados.id_configuracao_resultante, registro.id_ied)
        registro.id_configuracao_resultante = dados.id_configuracao_resultante
    if registro.prioridade == "CRITICA" and not _texto(dados.evidencia_implantacao):
        raise HTTPException(status_code=400, detail="Alterações críticas exigem evidência de implantação")
    _registrar_historico(db, registro, "IMPLANTACAO", "IMPLANTADA", id_usuario, dados.comentario)
    registro.status = "IMPLANTADA"
    registro.data_implantacao = dados.data_implantacao or date.today()
    registro.id_usuario_implantador = id_usuario
    registro.evidencia_implantacao = _texto(dados.evidencia_implantacao)
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível registrar a implantação")
    db.refresh(registro)
    return _solicitacao_out(db, registro, detalhado=True)


def validar(
    db: Session, id_solicitacao: int, dados: schemas.ValidacaoAlteracao, id_usuario: int
) -> schemas.SolicitacaoAlteracaoDetalhe:
    registro = _solicitacao(db, id_solicitacao)
    if registro.status not in ("IMPLANTADA", "EM_VALIDACAO"):
        raise HTTPException(status_code=400, detail="Somente solicitações implantadas podem ser validadas")
    if id_usuario in {registro.id_usuario_solicitante, registro.id_usuario_aprovador}:
        raise HTTPException(
            status_code=403,
            detail="A validação deve ser executada por usuário diferente do solicitante e do aprovador",
        )
    if dados.id_configuracao_validada:
        _validar_configuracao_do_ied(db, dados.id_configuracao_validada, registro.id_ied)
        registro.id_configuracao_resultante = dados.id_configuracao_validada
    status_novo = "CONCLUIDA" if dados.aprovado else "NAO_VALIDADA"
    _registrar_historico(
        db,
        registro,
        "CONCLUSAO" if dados.aprovado else "REJEICAO_VALIDACAO",
        status_novo,
        id_usuario,
        dados.comentario,
    )
    registro.status = status_novo
    registro.resultado_validacao = "APROVADO" if dados.aprovado else "REPROVADO"
    registro.data_validacao = dados.data_validacao or date.today()
    registro.id_usuario_validador = id_usuario
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível registrar a validação")
    db.refresh(registro)
    return _solicitacao_out(db, registro, detalhado=True)


def iniciar_analise(
    db: Session, id_solicitacao: int, dados: schemas.TransicaoAlteracao, id_usuario: int
) -> schemas.SolicitacaoAlteracaoDetalhe:
    registro = _solicitacao(db, id_solicitacao)
    if registro.status != "SUBMETIDA":
        raise HTTPException(status_code=400, detail="Somente solicitações submetidas podem entrar em análise")
    if registro.id_usuario_solicitante == id_usuario:
        raise HTTPException(status_code=403, detail="O solicitante não pode conduzir a própria análise")
    _registrar_historico(db, registro, "ANALISE", "EM_ANALISE", id_usuario, dados.comentario)
    registro.status = "EM_ANALISE"
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível iniciar a análise")
    db.refresh(registro)
    return _solicitacao_out(db, registro, detalhado=True)


def iniciar_validacao(
    db: Session, id_solicitacao: int, dados: schemas.TransicaoAlteracao, id_usuario: int
) -> schemas.SolicitacaoAlteracaoDetalhe:
    registro = _solicitacao(db, id_solicitacao)
    if registro.status != "IMPLANTADA":
        raise HTTPException(status_code=400, detail="Somente solicitações implantadas podem entrar em validação")
    if id_usuario in {registro.id_usuario_solicitante, registro.id_usuario_aprovador}:
        raise HTTPException(status_code=403, detail="A validação exige segregação entre solicitante e aprovador")
    _registrar_historico(db, registro, "INICIO_VALIDACAO", "EM_VALIDACAO", id_usuario, dados.comentario)
    registro.status = "EM_VALIDACAO"
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível iniciar a validação")
    db.refresh(registro)
    return _solicitacao_out(db, registro, detalhado=True)


def reverter(
    db: Session, id_solicitacao: int, dados: schemas.ReversaoAlteracao, id_usuario: int
) -> schemas.SolicitacaoAlteracaoDetalhe:
    registro = _solicitacao(db, id_solicitacao)
    if registro.status not in ("IMPLANTADA", "EM_VALIDACAO", "CONCLUIDA", "NAO_VALIDADA"):
        raise HTTPException(status_code=400, detail="A alteração ainda não pode ser revertida")
    _validar_configuracao_do_ied(db, dados.id_configuracao_rollback, registro.id_ied)
    _registrar_historico(db, registro, "REVERSAO", "REVERTIDA", id_usuario, dados.motivo)
    registro.status = "REVERTIDA"
    registro.id_configuracao_rollback = dados.id_configuracao_rollback
    registro.id_usuario_reversao = id_usuario
    registro.data_reversao = dados.data_reversao or date.today()
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível registrar a reversão")
    db.refresh(registro)
    return _solicitacao_out(db, registro, detalhado=True)


# --------------------------------------------------------------------------- #
# Comparador de configuracoes
# --------------------------------------------------------------------------- #


def _valores_do_grupo(db: Session, id_grupo: int) -> dict[int, str]:
    return {
        registro.id_parametro_definicao: registro.valor
        for registro in db.query(models.ConfigParametro)
        .filter(models.ConfigParametro.id_ied_grupo_ajuste == id_grupo)
        .all()
    }


def _rotulo_grupo(grupo: models.IEDGrupoAjuste) -> str:
    return f"Grupo {grupo.numero}" + (f" — {grupo.nome}" if grupo.nome else "")


def _comparar_mapas(
    db: Session,
    base: dict[int, str],
    destino: dict[int, str],
    rotulo_base: str | None,
    rotulo_destino: str | None,
    id_grupo_base: int | None,
    id_grupo_destino: int | None,
    somente_diferencas: bool,
) -> schemas.ComparacaoGruposOut:
    ids = sorted(set(base) | set(destino))
    metadados: dict[int, tuple[models.ParametroDefinicao, models.FuncaoANSI]] = {}
    if ids:
        linhas = (
            db.query(models.ParametroDefinicao, models.FuncaoANSI)
            .join(models.FuncaoANSI, models.FuncaoANSI.id_funcao_ansi == models.ParametroDefinicao.id_funcao_ansi)
            .filter(models.ParametroDefinicao.id_parametro_definicao.in_(ids))
            .all()
        )
        metadados = {parametro.id_parametro_definicao: (parametro, funcao) for parametro, funcao in linhas}

    itens: list[schemas.ComparacaoParametroOut] = []
    contagem = {"ADICIONADO": 0, "REMOVIDO": 0, "ALTERADO": 0, "IGUAL": 0}
    for id_parametro in ids:
        valor_base = base.get(id_parametro)
        valor_destino = destino.get(id_parametro)
        if valor_base is None and valor_destino is not None:
            situacao = "ADICIONADO"
        elif valor_base is not None and valor_destino is None:
            situacao = "REMOVIDO"
        elif (valor_base or "").strip() == (valor_destino or "").strip():
            situacao = "IGUAL"
        else:
            situacao = "ALTERADO"
        contagem[situacao] += 1
        if somente_diferencas and situacao == "IGUAL":
            continue
        parametro, funcao = metadados.get(id_parametro, (None, None))
        itens.append(
            schemas.ComparacaoParametroOut(
                id_parametro_definicao=id_parametro,
                id_funcao_ansi=parametro.id_funcao_ansi if parametro else 0,
                funcao_codigo=funcao.codigo if funcao else "",
                funcao_nome=funcao.nome if funcao else "",
                codigo=parametro.codigo if parametro else "",
                nome=parametro.nome if parametro else "",
                unidade=parametro.unidade if parametro else None,
                tipo_dado=parametro.tipo_dado if parametro else "TEXTO",
                valor_base=valor_base,
                valor_destino=valor_destino,
                situacao=situacao,
            )
        )
    itens.sort(key=lambda item: (item.funcao_codigo, item.codigo))
    return schemas.ComparacaoGruposOut(
        id_grupo_base=id_grupo_base,
        id_grupo_destino=id_grupo_destino,
        rotulo_base=rotulo_base,
        rotulo_destino=rotulo_destino,
        total_base=len(base),
        total_destino=len(destino),
        adicionados=contagem["ADICIONADO"],
        removidos=contagem["REMOVIDO"],
        alterados=contagem["ALTERADO"],
        iguais=contagem["IGUAL"],
        itens=itens,
    )


def comparar_grupos(
    db: Session, id_grupo_base: int, id_grupo_destino: int, somente_diferencas: bool = True
) -> schemas.ComparacaoGruposOut:
    grupo_base = _grupo(db, id_grupo_base)
    grupo_destino = _grupo(db, id_grupo_destino)
    return _comparar_mapas(
        db,
        _valores_do_grupo(db, id_grupo_base),
        _valores_do_grupo(db, id_grupo_destino),
        _rotulo_grupo(grupo_base),
        _rotulo_grupo(grupo_destino),
        id_grupo_base,
        id_grupo_destino,
        somente_diferencas,
    )


def comparar_configuracoes(
    db: Session, id_base: int, id_destino: int, somente_diferencas: bool = True
) -> schemas.ComparacaoGruposOut:
    config_base = _configuracao(db, id_base)
    config_destino = _configuracao(db, id_destino)
    if not config_base.id_grupo_ajuste or not config_destino.id_grupo_ajuste:
        raise HTTPException(
            status_code=400,
            detail="As configurações precisam estar vinculadas a um grupo de ajuste para serem comparadas",
        )
    grupo_base = _grupo(db, config_base.id_grupo_ajuste)
    grupo_destino = _grupo(db, config_destino.id_grupo_ajuste)
    return _comparar_mapas(
        db,
        _valores_do_grupo(db, grupo_base.id_ied_grupo_ajuste),
        _valores_do_grupo(db, grupo_destino.id_ied_grupo_ajuste),
        f"Configuração v{config_base.versao} — {config_base.rotulo}",
        f"Configuração v{config_destino.versao} — {config_destino.rotulo}",
        grupo_base.id_ied_grupo_ajuste,
        grupo_destino.id_ied_grupo_ajuste,
        somente_diferencas,
    )


# --------------------------------------------------------------------------- #
# Resumo
# --------------------------------------------------------------------------- #


def resumo_alteracoes(db: Session) -> schemas.ResumoAlteracaoOut:
    total = db.query(func.count(models.SolicitacaoAlteracao.id_solicitacao_alteracao)).scalar() or 0

    def por_status(status: str) -> int:
        return (
            db.query(func.count(models.SolicitacaoAlteracao.id_solicitacao_alteracao))
            .filter(models.SolicitacaoAlteracao.status == status)
            .scalar()
            or 0
        )

    def agrupar(coluna) -> list[schemas.DashboardItem]:
        linhas = (
            db.query(coluna, func.count(models.SolicitacaoAlteracao.id_solicitacao_alteracao))
            .group_by(coluna)
            .order_by(func.count(models.SolicitacaoAlteracao.id_solicitacao_alteracao).desc())
            .all()
        )
        return [schemas.DashboardItem(rotulo=str(rotulo), quantidade=quantidade) for rotulo, quantidade in linhas]

    return schemas.ResumoAlteracaoOut(
        total=total,
        aguardando_aprovacao=por_status("SUBMETIDA"),
        aguardando_implantacao=por_status("APROVADA"),
        aguardando_validacao=por_status("IMPLANTADA"),
        por_status=agrupar(models.SolicitacaoAlteracao.status),
        por_tipo=agrupar(models.SolicitacaoAlteracao.tipo),
        por_prioridade=agrupar(models.SolicitacaoAlteracao.prioridade),
    )
