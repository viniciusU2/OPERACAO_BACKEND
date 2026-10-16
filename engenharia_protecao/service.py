from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from models.Ativo import Ativo
from models.OS_models import OrdemServico
from models.familias_models import TipoAtivo
from models.fo import FuncaoOperacao
from models.instalacao_models import Subestacao

from . import models, schemas
from .service_config import _remover_arquivo_orfao


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


def _modelo(db: Session, id_modelo_ied: int, somente_ativo: bool = False) -> models.ModeloIED:
    query = db.query(models.ModeloIED).filter(models.ModeloIED.id_modelo_ied == id_modelo_ied)
    if somente_ativo:
        query = query.filter(models.ModeloIED.ativo.is_(True))
    item = query.first()
    if not item:
        raise HTTPException(status_code=404, detail="Modelo de IED não encontrado")
    return item


def _ied(db: Session, id_ied: int) -> models.IED:
    item = db.query(models.IED).filter(models.IED.id_ied == id_ied).first()
    if not item:
        raise HTTPException(status_code=404, detail="IED não encontrado")
    return item


def _subestacao(db: Session, id_subestacao: int) -> Subestacao:
    item = db.query(Subestacao).filter(Subestacao.id_subestacao == id_subestacao).first()
    if not item:
        raise HTTPException(status_code=404, detail="Subestação não encontrada")
    return item


def _validar_funcao(db: Session, id_subestacao: int, id_funcao_operacao: int | None) -> FuncaoOperacao | None:
    if not id_funcao_operacao:
        return None
    item = db.query(FuncaoOperacao).filter(FuncaoOperacao.id_funcao_operacao == id_funcao_operacao).first()
    if not item:
        raise HTTPException(status_code=404, detail="Função operacional não encontrada")
    if item.id_subestacao != id_subestacao:
        raise HTTPException(status_code=400, detail="A função operacional não pertence à subestação informada")
    return item


def _validar_identificadores_ied(
    db: Session,
    tag_operacional: str,
    numero_serie: str | None,
    ignorar_id: int | None = None,
):
    tag_query = db.query(models.IED).filter(func.lower(models.IED.tag_operacional) == tag_operacional.lower())
    if ignorar_id:
        tag_query = tag_query.filter(models.IED.id_ied != ignorar_id)
    if tag_query.first():
        raise HTTPException(status_code=409, detail="Já existe IED com esta TAG operacional")

    if numero_serie:
        serial_query = db.query(models.IED).filter(func.lower(models.IED.numero_serie) == numero_serie.lower())
        if ignorar_id:
            serial_query = serial_query.filter(models.IED.id_ied != ignorar_id)
        if serial_query.first():
            raise HTTPException(status_code=409, detail="Já existe IED com este número de série")


def _modelo_saida(db: Session, item: models.ModeloIED) -> schemas.ModeloIEDOut:
    quantidade = db.query(func.count(models.IED.id_ied)).filter(models.IED.id_modelo_ied == item.id_modelo_ied).scalar() or 0
    return schemas.ModeloIEDOut(
        id_modelo_ied=item.id_modelo_ied,
        fabricante=item.fabricante,
        familia=item.familia,
        modelo=item.modelo,
        aplicacao=item.aplicacao,
        descricao=item.descricao,
        ativo=item.ativo,
        quantidade_ieds=quantidade,
        criado_em=item.criado_em,
        atualizado_em=item.atualizado_em,
    )


def listar_modelos(db: Session, busca: str | None, somente_ativos: bool, page: int, page_size: int):
    query = db.query(models.ModeloIED)
    if somente_ativos:
        query = query.filter(models.ModeloIED.ativo.is_(True))
    if busca:
        termo = f"%{busca.strip()}%"
        query = query.filter(
            or_(
                models.ModeloIED.fabricante.ilike(termo),
                models.ModeloIED.familia.ilike(termo),
                models.ModeloIED.modelo.ilike(termo),
                models.ModeloIED.aplicacao.ilike(termo),
            )
        )
    total = query.count()
    itens = query.order_by(models.ModeloIED.fabricante, models.ModeloIED.modelo).offset((page - 1) * page_size).limit(page_size).all()
    return schemas.ModeloIEDLista(total=total, page=page, page_size=page_size, items=[_modelo_saida(db, item) for item in itens])


def obter_modelo(db: Session, id_modelo_ied: int):
    return _modelo_saida(db, _modelo(db, id_modelo_ied))


def criar_modelo(db: Session, dados: schemas.ModeloIEDCreate, id_usuario: int):
    existente = db.query(models.ModeloIED).filter(
        func.lower(models.ModeloIED.fabricante) == dados.fabricante.lower(),
        func.lower(models.ModeloIED.modelo) == dados.modelo.lower(),
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Já existe este modelo para o fabricante informado")
    item = models.ModeloIED(
        **dados.model_dump(),
        id_usuario_criacao=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    db.add(item)
    _commit(db, "Não foi possível cadastrar o modelo; verifique os campos únicos")
    db.refresh(item)
    return _modelo_saida(db, item)


def atualizar_modelo(db: Session, id_modelo_ied: int, dados: schemas.ModeloIEDUpdate, id_usuario: int):
    item = _modelo(db, id_modelo_ied)
    payload = dados.model_dump(exclude_unset=True)
    fabricante = payload.get("fabricante", item.fabricante)
    modelo = payload.get("modelo", item.modelo)
    conflito = db.query(models.ModeloIED).filter(
        models.ModeloIED.id_modelo_ied != id_modelo_ied,
        func.lower(models.ModeloIED.fabricante) == fabricante.lower(),
        func.lower(models.ModeloIED.modelo) == modelo.lower(),
    ).first()
    if conflito:
        raise HTTPException(status_code=409, detail="Já existe este modelo para o fabricante informado")
    for campo, valor in payload.items():
        setattr(item, campo, valor)
    item.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível atualizar o modelo")
    db.refresh(item)
    return _modelo_saida(db, item)


def _consulta_ieds(db: Session):
    ativo_ied = aliased(Ativo, name="ativo_inventario_ied")
    quantidade_equipamentos = (
        db.query(func.count(models.IEDEquipamento.id_ied_equipamento))
        .filter(
            models.IEDEquipamento.id_ied == models.IED.id_ied,
            models.IEDEquipamento.data_fim.is_(None),
        )
        .correlate(models.IED)
        .scalar_subquery()
    )
    return (
        db.query(
            models.IED,
            ativo_ied,
            models.ModeloIED,
            Subestacao,
            FuncaoOperacao,
            quantidade_equipamentos.label("quantidade_equipamentos"),
        )
        .join(ativo_ied, ativo_ied.id_ativo == models.IED.id_ativo)
        .join(models.ModeloIED, models.ModeloIED.id_modelo_ied == models.IED.id_modelo_ied)
        .join(Subestacao, Subestacao.id_subestacao == models.IED.id_subestacao)
        .outerjoin(FuncaoOperacao, FuncaoOperacao.id_funcao_operacao == models.IED.id_funcao_operacao)
    ), ativo_ied


def _ied_resumo(linha) -> schemas.IEDResumo:
    ied, ativo_ied, modelo, subestacao, funcao_operacao, quantidade = linha
    return schemas.IEDResumo(
        id_ied=ied.id_ied,
        codigo_uuid=ied.codigo_uuid,
        tag_operacional=ied.tag_operacional,
        id_ativo=ied.id_ativo,
        ativo_codigo=ativo_ied.codigo_ativo,
        id_modelo_ied=ied.id_modelo_ied,
        modelo_nome=modelo.modelo,
        fabricante=modelo.fabricante,
        familia=modelo.familia,
        id_subestacao=ied.id_subestacao,
        subestacao_nome=subestacao.nome,
        id_funcao_operacao=ied.id_funcao_operacao,
        funcao_operacao_codigo=funcao_operacao.codigo if funcao_operacao else None,
        painel_instalacao=ied.painel_instalacao,
        numero_serie=ied.numero_serie,
        codigo_produto=ied.codigo_produto,
        versao_hardware=ied.versao_hardware,
        versao_firmware=ied.versao_firmware,
        data_instalacao=ied.data_instalacao,
        status_operacional=ied.status_operacional,
        observacoes_tecnicas=ied.observacoes_tecnicas,
        ativo=ied.ativo,
        versao=ied.versao,
        quantidade_equipamentos=quantidade or 0,
        criado_em=ied.criado_em,
        atualizado_em=ied.atualizado_em,
    )


def listar_ieds(
    db: Session,
    busca: str | None,
    id_subestacao: int | None,
    id_modelo_ied: int | None,
    status_operacional: str | None,
    somente_ativos: bool,
    page: int,
    page_size: int,
):
    query, ativo_ied = _consulta_ieds(db)
    if somente_ativos:
        query = query.filter(models.IED.ativo.is_(True))
    if busca:
        termo = f"%{busca.strip()}%"
        query = query.filter(
            or_(
                models.IED.tag_operacional.ilike(termo),
                models.IED.numero_serie.ilike(termo),
                models.IED.codigo_produto.ilike(termo),
                ativo_ied.codigo_ativo.ilike(termo),
                models.ModeloIED.modelo.ilike(termo),
                models.ModeloIED.fabricante.ilike(termo),
            )
        )
    if id_subestacao:
        query = query.filter(models.IED.id_subestacao == id_subestacao)
    if id_modelo_ied:
        query = query.filter(models.IED.id_modelo_ied == id_modelo_ied)
    if status_operacional:
        query = query.filter(models.IED.status_operacional == status_operacional.upper())

    total = query.count()
    linhas = query.order_by(models.IED.tag_operacional).offset((page - 1) * page_size).limit(page_size).all()
    return schemas.IEDLista(total=total, page=page, page_size=page_size, items=[_ied_resumo(linha) for linha in linhas])


def criar_ied(db: Session, dados: schemas.IEDCreate, id_usuario: int):
    _modelo(db, dados.id_modelo_ied, somente_ativo=True)
    _subestacao(db, dados.id_subestacao)
    _validar_funcao(db, dados.id_subestacao, dados.id_funcao_operacao)
    _validar_identificadores_ied(db, dados.tag_operacional, _texto(dados.numero_serie))

    ativo_inventario = db.query(Ativo).filter(Ativo.id_ativo == dados.id_ativo).first()
    if not ativo_inventario:
        raise HTTPException(status_code=404, detail="Ativo correspondente ao IED não encontrado")
    if ativo_inventario.id_subestacao != dados.id_subestacao:
        raise HTTPException(status_code=400, detail="O ativo do IED não pertence à subestação informada")
    if ativo_inventario.id_funcao_operacao and dados.id_funcao_operacao and ativo_inventario.id_funcao_operacao != dados.id_funcao_operacao:
        raise HTTPException(status_code=400, detail="A função operacional do IED diverge da função cadastrada no ativo")
    if db.query(models.IED).filter(models.IED.id_ativo == dados.id_ativo).first():
        raise HTTPException(status_code=409, detail="Este ativo já está vinculado a outro IED")

    payload = dados.model_dump(exclude={"id_ativos_protegidos"})
    if not payload.get("id_funcao_operacao") and ativo_inventario.id_funcao_operacao:
        payload["id_funcao_operacao"] = ativo_inventario.id_funcao_operacao
    payload["numero_serie"] = _texto(payload.get("numero_serie"))
    item = models.IED(
        **payload,
        id_usuario_criacao=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    db.add(item)
    try:
        db.flush()
        db.add(
            models.IEDInstalacao(
                id_ied=item.id_ied,
                id_subestacao=item.id_subestacao,
                id_funcao_operacao=item.id_funcao_operacao,
                painel_instalacao=item.painel_instalacao,
                tipo_movimentacao="INSTALACAO",
                data_inicio=item.data_instalacao,
                motivo="Cadastro inicial",
                id_usuario_registro=id_usuario,
            )
        )
        if item.versao_firmware:
            db.add(
                models.IEDFirmwareHistorico(
                    id_ied=item.id_ied,
                    versao_firmware=item.versao_firmware,
                    data_inicio=item.data_instalacao,
                    motivo="Firmware informado no cadastro inicial",
                    id_usuario_registro=id_usuario,
                )
            )
        for indice, id_ativo in enumerate(dict.fromkeys(dados.id_ativos_protegidos)):
            if id_ativo == item.id_ativo:
                raise HTTPException(status_code=400, detail="O ativo do próprio IED não pode ser cadastrado como equipamento protegido")
            ativo = db.query(Ativo).filter(Ativo.id_ativo == id_ativo).first()
            if not ativo:
                raise HTTPException(status_code=404, detail=f"Ativo #{id_ativo} não encontrado")
            if ativo.id_subestacao != item.id_subestacao:
                raise HTTPException(status_code=400, detail=f"O ativo {ativo.codigo_ativo} não pertence à subestação do IED")
            db.add(
                models.IEDEquipamento(
                    id_ied=item.id_ied,
                    id_ativo=id_ativo,
                    principal=indice == 0,
                    data_inicio=item.data_instalacao,
                    id_usuario_registro=id_usuario,
                )
            )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível cadastrar o IED; verifique TAG e número de série") from exc
    return obter_ied(db, item.id_ied)


def atualizar_ied(db: Session, id_ied: int, dados: schemas.IEDUpdate, id_usuario: int):
    item = _ied(db, id_ied)
    if item.versao != dados.versao:
        raise HTTPException(status_code=409, detail="O IED foi alterado por outro usuário; recarregue os dados")
    payload = dados.model_dump(exclude_unset=True, exclude={"versao"})
    tag = payload.get("tag_operacional", item.tag_operacional)
    serial = _texto(payload.get("numero_serie", item.numero_serie))
    _validar_identificadores_ied(db, tag, serial, ignorar_id=id_ied)
    if payload.get("id_modelo_ied"):
        _modelo(db, payload["id_modelo_ied"], somente_ativo=True)
    if "numero_serie" in payload:
        payload["numero_serie"] = serial
    for campo, valor in payload.items():
        setattr(item, campo, valor)
    item.versao += 1
    item.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível atualizar o IED")
    return obter_ied(db, id_ied)


def transferir_ied(db: Session, id_ied: int, dados: schemas.TransferenciaCreate, id_usuario: int):
    item = _ied(db, id_ied)
    _subestacao(db, dados.id_subestacao)
    _validar_funcao(db, dados.id_subestacao, dados.id_funcao_operacao)
    atual = db.query(models.IEDInstalacao).filter(
        models.IEDInstalacao.id_ied == id_ied,
        models.IEDInstalacao.data_fim.is_(None),
    ).order_by(models.IEDInstalacao.data_inicio.desc()).first()
    if atual and dados.data_inicio < atual.data_inicio:
        raise HTTPException(status_code=400, detail="A data da movimentação não pode anteceder a instalação atual")
    if atual:
        atual.data_fim = dados.data_inicio
    db.add(
        models.IEDInstalacao(
            id_ied=id_ied,
            id_subestacao=dados.id_subestacao,
            id_funcao_operacao=dados.id_funcao_operacao,
            painel_instalacao=dados.painel_instalacao,
            tipo_movimentacao=dados.tipo_movimentacao,
            data_inicio=dados.data_inicio,
            motivo=dados.motivo,
            observacoes=dados.observacoes,
            id_usuario_registro=id_usuario,
        )
    )
    item.id_subestacao = dados.id_subestacao
    item.id_funcao_operacao = dados.id_funcao_operacao
    item.painel_instalacao = dados.painel_instalacao
    item.data_instalacao = dados.data_inicio
    item.versao += 1
    item.id_usuario_atualizacao = id_usuario
    ativo_inventario = db.query(Ativo).filter(Ativo.id_ativo == item.id_ativo).first()
    if ativo_inventario:
        ativo_inventario.id_subestacao = dados.id_subestacao
        ativo_inventario.id_funcao_operacao = dados.id_funcao_operacao
        ativo_inventario.id_grupo_ativo = None
    _commit(db, "Não foi possível registrar a movimentação do IED")
    return obter_ied(db, id_ied)


def adicionar_modulo(db: Session, id_ied: int, dados: schemas.ModuloCreate, id_usuario: int):
    _ied(db, id_ied)
    item = models.IEDModulo(id_ied=id_ied, **dados.model_dump(), id_usuario_registro=id_usuario)
    db.add(item)
    _commit(db, "Não foi possível registrar o módulo")
    db.refresh(item)
    return item


def registrar_firmware(db: Session, id_ied: int, dados: schemas.FirmwareCreate, id_usuario: int):
    item = _ied(db, id_ied)
    if dados.id_os and not db.query(OrdemServico).filter(OrdemServico.id_os == dados.id_os).first():
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")
    atual = db.query(models.IEDFirmwareHistorico).filter(
        models.IEDFirmwareHistorico.id_ied == id_ied,
        models.IEDFirmwareHistorico.data_fim.is_(None),
    ).order_by(models.IEDFirmwareHistorico.data_inicio.desc()).first()
    if atual and dados.data_inicio < atual.data_inicio:
        raise HTTPException(status_code=400, detail="A data do firmware não pode anteceder a versão vigente")
    if atual:
        atual.data_fim = dados.data_inicio
    historico = models.IEDFirmwareHistorico(id_ied=id_ied, **dados.model_dump(), id_usuario_registro=id_usuario)
    db.add(historico)
    item.versao_firmware = dados.versao_firmware
    item.versao += 1
    item.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível registrar o firmware")
    db.refresh(historico)
    return historico


def associar_equipamento(db: Session, id_ied: int, dados: schemas.EquipamentoCreate, id_usuario: int):
    item = _ied(db, id_ied)
    ativo = db.query(Ativo).filter(Ativo.id_ativo == dados.id_ativo).first()
    if not ativo:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")
    if ativo.id_subestacao != item.id_subestacao:
        raise HTTPException(status_code=400, detail="O ativo não pertence à subestação atual do IED")
    existente = db.query(models.IEDEquipamento).filter(
        models.IEDEquipamento.id_ied == id_ied,
        models.IEDEquipamento.id_ativo == dados.id_ativo,
        models.IEDEquipamento.data_fim.is_(None),
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Este ativo já está associado ao IED")
    if dados.principal:
        db.query(models.IEDEquipamento).filter(
            models.IEDEquipamento.id_ied == id_ied,
            models.IEDEquipamento.data_fim.is_(None),
        ).update({models.IEDEquipamento.principal: False}, synchronize_session=False)
    vinculo = models.IEDEquipamento(id_ied=id_ied, **dados.model_dump(), id_usuario_registro=id_usuario)
    db.add(vinculo)
    _commit(db, "Não foi possível associar o equipamento")
    return obter_ied(db, id_ied)


def encerrar_associacao_equipamento(db: Session, id_ied: int, id_ied_equipamento: int, data_fim: date):
    vinculo = db.query(models.IEDEquipamento).filter(
        models.IEDEquipamento.id_ied_equipamento == id_ied_equipamento,
        models.IEDEquipamento.id_ied == id_ied,
        models.IEDEquipamento.data_fim.is_(None),
    ).first()
    if not vinculo:
        raise HTTPException(status_code=404, detail="Associação ativa não encontrada")
    if data_fim < vinculo.data_inicio:
        raise HTTPException(status_code=400, detail="A data final não pode anteceder a associação")
    vinculo.data_fim = data_fim
    _commit(db, "Não foi possível encerrar a associação")
    return obter_ied(db, id_ied)


def obter_ied(db: Session, id_ied: int):
    query, _ativo_ied = _consulta_ieds(db)
    linha = query.filter(models.IED.id_ied == id_ied).first()
    if not linha:
        raise HTTPException(status_code=404, detail="IED não encontrado")
    resumo = _ied_resumo(linha).model_dump()

    instalacoes = (
        db.query(models.IEDInstalacao, Subestacao, FuncaoOperacao)
        .join(Subestacao, Subestacao.id_subestacao == models.IEDInstalacao.id_subestacao)
        .outerjoin(FuncaoOperacao, FuncaoOperacao.id_funcao_operacao == models.IEDInstalacao.id_funcao_operacao)
        .filter(models.IEDInstalacao.id_ied == id_ied)
        .order_by(models.IEDInstalacao.data_inicio.desc())
        .all()
    )
    instalacoes_saida = [
        schemas.InstalacaoOut(
            id_ied_instalacao=registro.id_ied_instalacao,
            id_subestacao=registro.id_subestacao,
            subestacao_nome=subestacao.nome,
            id_funcao_operacao=registro.id_funcao_operacao,
            funcao_operacao_codigo=funcao.codigo if funcao else None,
            painel_instalacao=registro.painel_instalacao,
            tipo_movimentacao=registro.tipo_movimentacao,
            data_inicio=registro.data_inicio,
            data_fim=registro.data_fim,
            motivo=registro.motivo,
            observacoes=registro.observacoes,
            criado_em=registro.criado_em,
        )
        for registro, subestacao, funcao in instalacoes
    ]
    modulos = db.query(models.IEDModulo).filter(models.IEDModulo.id_ied == id_ied).order_by(models.IEDModulo.id_ied_modulo.desc()).all()
    firmwares = db.query(models.IEDFirmwareHistorico).filter(models.IEDFirmwareHistorico.id_ied == id_ied).order_by(models.IEDFirmwareHistorico.data_inicio.desc()).all()
    equipamentos = (
        db.query(models.IEDEquipamento, Ativo, TipoAtivo)
        .join(Ativo, Ativo.id_ativo == models.IEDEquipamento.id_ativo)
        .outerjoin(TipoAtivo, TipoAtivo.id_tipo_ativo == Ativo.id_tipo_ativo)
        .filter(models.IEDEquipamento.id_ied == id_ied)
        .order_by(models.IEDEquipamento.data_fim.is_(None).desc(), models.IEDEquipamento.principal.desc(), Ativo.codigo_ativo)
        .all()
    )
    equipamentos_saida = [
        schemas.EquipamentoOut(
            id_ied_equipamento=vinculo.id_ied_equipamento,
            id_ativo=ativo.id_ativo,
            codigo_ativo=ativo.codigo_ativo,
            tipo_ativo_nome=tipo.nome if tipo else None,
            principal=vinculo.principal,
            data_inicio=vinculo.data_inicio,
            data_fim=vinculo.data_fim,
            observacoes=vinculo.observacoes,
            criado_em=vinculo.criado_em,
        )
        for vinculo, ativo, tipo in equipamentos
    ]
    return schemas.IEDDetalhe(
        **resumo,
        instalacoes=instalacoes_saida,
        modulos=modulos,
        firmwares=firmwares,
        equipamentos=equipamentos_saida,
    )


def _arquivos_do_ied(db: Session, id_ied: int) -> set[int]:
    """Coleta os arquivos vinculados ao IED antes da remoção em cascata."""
    consultas = (
        db.query(models.ConfiguracaoArquivo.id_arquivo)
        .join(
            models.IEDConfiguracao,
            models.IEDConfiguracao.id_ied_configuracao == models.ConfiguracaoArquivo.id_ied_configuracao,
        )
        .filter(models.IEDConfiguracao.id_ied == id_ied),
        db.query(models.IEDEnsaioArquivo.id_arquivo)
        .join(models.IEDEnsaio, models.IEDEnsaio.id_ied_ensaio == models.IEDEnsaioArquivo.id_ied_ensaio)
        .filter(models.IEDEnsaio.id_ied == id_ied),
        db.query(models.IEDOcorrenciaArquivo.id_arquivo)
        .join(
            models.IEDOcorrencia,
            models.IEDOcorrencia.id_ied_ocorrencia == models.IEDOcorrenciaArquivo.id_ied_ocorrencia,
        )
        .filter(models.IEDOcorrencia.id_ied == id_ied),
        db.query(models.IEDOscilografiaArquivo.id_arquivo)
        .join(
            models.IEDOscilografia,
            models.IEDOscilografia.id_ied_oscilografia == models.IEDOscilografiaArquivo.id_ied_oscilografia,
        )
        .filter(models.IEDOscilografia.id_ied == id_ied),
        db.query(models.IEDRelatorioArquivo.id_arquivo)
        .join(
            models.IEDRelatorio,
            models.IEDRelatorio.id_ied_relatorio == models.IEDRelatorioArquivo.id_ied_relatorio,
        )
        .filter(models.IEDRelatorio.id_ied == id_ied),
    )
    ids: set[int] = set()
    for consulta in consultas:
        ids.update(linha[0] for linha in consulta.all())
    return ids


def remover_ied(db: Session, id_ied: int) -> schemas.IEDRemocaoOut:
    """Remove um IED e todos os dados do módulo ligados a ele (não remove o ativo).

    As chaves estrangeiras do módulo usam ON DELETE CASCADE, então a remoção do
    registro em ``ied`` propaga para instalações, módulos, firmwares, equipamentos,
    funções, grupos e parâmetros, configurações, alterações, comunicação, circuitos,
    sinais, ensaios, ocorrências, oscilografias e relatórios. Os arquivos (tabela
    ``arquivo``) não participam da cascata e são limpos aqui.
    """
    ied = _ied(db, id_ied)
    tag = ied.tag_operacional
    arquivos = _arquivos_do_ied(db, id_ied)
    db.query(models.IED).filter(models.IED.id_ied == id_ied).delete(synchronize_session=False)
    db.commit()
    removidos = sum(1 for id_arquivo in arquivos if _remover_arquivo_orfao(db, id_arquivo))
    if removidos:
        db.commit()
    return schemas.IEDRemocaoOut(id_ied=id_ied, tag_operacional=tag, arquivos_removidos=removidos)


def arquivar_ied(db: Session, id_ied: int, id_usuario: int) -> schemas.IEDRemocaoOut:
    """Arquiva o IED (``ativo = false``) sem apagar histórico técnico ou arquivos.

    Alternativa reversível à exclusão definitiva: o IED sai do inventário vigente,
    as instalações em aberto são encerradas e o ativo do ENGVI permanece vinculado
    (por isso o mesmo ativo só pode voltar a receber um IED após ``reativar_ied``
    ou a exclusão definitiva). Os arquivos são preservados.
    """
    ied = _ied(db, id_ied)
    tag = ied.tag_operacional
    ied.ativo = False
    ied.status_operacional = "RETIRADO"
    ied.versao += 1
    ied.id_usuario_atualizacao = id_usuario
    db.query(models.IEDInstalacao).filter(
        models.IEDInstalacao.id_ied == id_ied,
        models.IEDInstalacao.data_fim.is_(None),
    ).update({models.IEDInstalacao.data_fim: date.today()}, synchronize_session=False)
    db.commit()
    return schemas.IEDRemocaoOut(id_ied=id_ied, tag_operacional=tag, arquivos_removidos=0)


def reativar_ied(db: Session, id_ied: int, id_usuario: int) -> schemas.IEDDetalhe:
    """Devolve um IED arquivado ao inventário vigente (``ativo = true``)."""
    ied = _ied(db, id_ied)
    if ied.ativo:
        raise HTTPException(status_code=400, detail="O IED já está ativo no inventário")
    ied.ativo = True
    if ied.status_operacional == "RETIRADO":
        ied.status_operacional = "EM_OPERACAO"
    ied.versao += 1
    ied.id_usuario_atualizacao = id_usuario
    db.commit()
    return obter_ied(db, id_ied)


def dashboard(
    db: Session,
    id_subestacao: int | None = None,
    id_modelo_ied: int | None = None,
    id_funcao_operacao: int | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
):
    base = db.query(models.IED).filter(models.IED.ativo.is_(True))
    if id_subestacao:
        base = base.filter(models.IED.id_subestacao == id_subestacao)
    if id_modelo_ied:
        base = base.filter(models.IED.id_modelo_ied == id_modelo_ied)
    if id_funcao_operacao:
        base = base.filter(models.IED.id_funcao_operacao == id_funcao_operacao)
    if data_inicio:
        base = base.filter(models.IED.data_instalacao >= data_inicio)
    if data_fim:
        base = base.filter(models.IED.data_instalacao <= data_fim)
    ids = base.with_entities(models.IED.id_ied).subquery()
    total = base.count()
    em_operacao = base.filter(models.IED.status_operacional == "EM_OPERACAO").count()
    sem_funcao = base.filter(models.IED.id_funcao_operacao.is_(None)).count()
    sem_firmware = base.filter(or_(models.IED.versao_firmware.is_(None), models.IED.versao_firmware == "")).count()

    ultima_validada = (
        db.query(
            models.IEDConfiguracao.id_ied.label("id_ied"),
            func.max(models.IEDConfiguracao.data_coleta).label("ultima_data"),
        )
        .filter(models.IEDConfiguracao.status_validacao == "VALIDADA")
        .group_by(models.IEDConfiguracao.id_ied)
        .subquery()
    )
    sem_backup_validado = (
        db.query(func.count(ids.c.id_ied))
        .outerjoin(ultima_validada, ultima_validada.c.id_ied == ids.c.id_ied)
        .filter(ultima_validada.c.id_ied.is_(None))
        .scalar()
        or 0
    )
    limite_backup = date.today() - timedelta(days=180)
    backups_desatualizados = (
        db.query(func.count(ids.c.id_ied))
        .join(ultima_validada, ultima_validada.c.id_ied == ids.c.id_ied)
        .filter(ultima_validada.c.ultima_data < limite_backup)
        .scalar()
        or 0
    )
    alteracoes_pendentes = (
        db.query(func.count(models.SolicitacaoAlteracao.id_solicitacao_alteracao))
        .join(ids, ids.c.id_ied == models.SolicitacaoAlteracao.id_ied)
        .filter(models.SolicitacaoAlteracao.status.in_(("SUBMETIDA", "EM_ANALISE", "APROVADA", "IMPLANTADA", "EM_VALIDACAO")))
        .scalar()
        or 0
    )
    implantadas_nao_validadas = (
        db.query(func.count(models.SolicitacaoAlteracao.id_solicitacao_alteracao))
        .join(ids, ids.c.id_ied == models.SolicitacaoAlteracao.id_ied)
        .filter(models.SolicitacaoAlteracao.status.in_(("IMPLANTADA", "EM_VALIDACAO")))
        .scalar()
        or 0
    )
    ensaios_vencidos = (
        db.query(func.count(models.IEDEnsaio.id_ied_ensaio))
        .join(ids, ids.c.id_ied == models.IEDEnsaio.id_ied)
        .filter(models.IEDEnsaio.data_prevista < date.today(), models.IEDEnsaio.status.in_(("PLANEJADO", "EM_ANDAMENTO")))
        .scalar()
        or 0
    )
    ocorrencias_abertas = (
        db.query(func.count(models.IEDOcorrencia.id_ied_ocorrencia))
        .join(ids, ids.c.id_ied == models.IEDOcorrencia.id_ied)
        .filter(models.IEDOcorrencia.status.in_(("ABERTA", "EM_ANALISE")))
        .scalar()
        or 0
    )

    por_fabricante = (
        db.query(models.ModeloIED.fabricante, func.count(models.IED.id_ied))
        .join(models.IED, models.IED.id_modelo_ied == models.ModeloIED.id_modelo_ied)
        .join(ids, ids.c.id_ied == models.IED.id_ied)
        .group_by(models.ModeloIED.fabricante)
        .order_by(func.count(models.IED.id_ied).desc())
        .all()
    )

    por_modelo = (
        db.query(models.ModeloIED.modelo, func.count(models.IED.id_ied))
        .join(models.IED, models.IED.id_modelo_ied == models.ModeloIED.id_modelo_ied)
        .join(ids, ids.c.id_ied == models.IED.id_ied)
        .group_by(models.ModeloIED.id_modelo_ied, models.ModeloIED.modelo)
        .order_by(func.count(models.IED.id_ied).desc())
        .all()
    )
    por_subestacao = (
        db.query(Subestacao.nome, func.count(models.IED.id_ied))
        .join(models.IED, models.IED.id_subestacao == Subestacao.id_subestacao)
        .join(ids, ids.c.id_ied == models.IED.id_ied)
        .group_by(Subestacao.id_subestacao, Subestacao.nome)
        .order_by(func.count(models.IED.id_ied).desc())
        .all()
    )
    por_status = db.query(models.IED.status_operacional, func.count(models.IED.id_ied)).join(ids, ids.c.id_ied == models.IED.id_ied).group_by(models.IED.status_operacional).all()
    por_firmware = (
        db.query(func.coalesce(func.nullif(models.IED.versao_firmware, ""), "Não informado"), func.count(models.IED.id_ied))
        .join(ids, ids.c.id_ied == models.IED.id_ied)
        .group_by(func.coalesce(func.nullif(models.IED.versao_firmware, ""), "Não informado"))
        .order_by(func.count(models.IED.id_ied).desc())
        .all()
    )

    itens = lambda linhas: [schemas.DashboardItem(rotulo=str(rotulo), quantidade=quantidade) for rotulo, quantidade in linhas]
    return schemas.DashboardOut(
        total_ieds=total,
        em_operacao=em_operacao,
        sem_funcao_operacao=sem_funcao,
        sem_firmware=sem_firmware,
        backups_desatualizados=backups_desatualizados,
        sem_backup_validado=sem_backup_validado,
        alteracoes_pendentes=alteracoes_pendentes,
        implantadas_nao_validadas=implantadas_nao_validadas,
        ensaios_vencidos=ensaios_vencidos,
        ocorrencias_abertas=ocorrencias_abertas,
        por_fabricante=itens(por_fabricante),
        por_modelo=itens(por_modelo),
        por_subestacao=itens(por_subestacao),
        por_status=itens(por_status),
        firmware_distribuicao=itens(por_firmware),
    )
