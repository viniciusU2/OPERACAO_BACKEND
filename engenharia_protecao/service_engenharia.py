"""Fase 4 - Engenharia de protecao: comunicacao/IEC 61850, circuitos/sinais e ensaios."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.Ativo import Ativo
from models.auth_models import Usuario

from . import models, schemas
from .service_config import (
    EXTENSOES_PERMITIDAS,
    MAX_ARQUIVO_BYTES,
    PASTA_UPLOADS,
    _categoria_por_extensao,
    _texto,
    _usuario_nome,
    _ied,
    _funcao_ansi,
    validar_conteudo,
)

STATUS_ENSAIO_EDITAVEL = ("PLANEJADO", "EM_ANDAMENTO")
STATUS_ENSAIO_FINAL = ("APROVADO", "REPROVADO")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _commit(db: Session, mensagem_conflito: str):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=mensagem_conflito) from exc


def _verificar_versao(registro, versao: int, rotulo: str) -> None:
    if registro.versao != versao:
        raise HTTPException(
            status_code=409,
            detail=f"{rotulo} foi atualizado por outro usuário. Recarregue os dados e tente novamente.",
        )


def _aplicar(registro, dados, excluir: set[str] | None = None) -> None:
    excluir = excluir or set()
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        if campo in excluir:
            continue
        setattr(registro, campo, _texto(valor) if isinstance(valor, str) else valor)


def _interface(db: Session, id_interface: int) -> models.IEDInterfaceComunicacao:
    item = (
        db.query(models.IEDInterfaceComunicacao)
        .filter(models.IEDInterfaceComunicacao.id_ied_interface_comunicacao == id_interface)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Interface de comunicação não encontrada")
    return item


def _protocolo(db: Session, id_protocolo: int) -> models.IEDProtocoloComunicacao:
    item = (
        db.query(models.IEDProtocoloComunicacao)
        .filter(models.IEDProtocoloComunicacao.id_ied_protocolo_comunicacao == id_protocolo)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Protocolo de comunicação não encontrado")
    return item


def _goose(db: Session, id_goose: int) -> models.IEDGooseControle:
    item = (
        db.query(models.IEDGooseControle)
        .filter(models.IEDGooseControle.id_ied_goose_controle == id_goose)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Controle GOOSE/SV não encontrado")
    return item


def _circuito(db: Session, id_circuito: int) -> models.IEDCircuito:
    item = db.query(models.IEDCircuito).filter(models.IEDCircuito.id_ied_circuito == id_circuito).first()
    if not item:
        raise HTTPException(status_code=404, detail="Circuito não encontrado")
    return item


def _sinal(db: Session, id_sinal: int) -> models.IEDSinal:
    item = db.query(models.IEDSinal).filter(models.IEDSinal.id_ied_sinal == id_sinal).first()
    if not item:
        raise HTTPException(status_code=404, detail="Sinal não encontrado")
    return item


def _ensaio(db: Session, id_ensaio: int) -> models.IEDEnsaio:
    item = db.query(models.IEDEnsaio).filter(models.IEDEnsaio.id_ied_ensaio == id_ensaio).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ensaio não encontrado")
    return item


def _interface_do_ied(db: Session, id_ied: int, id_interface: int) -> models.IEDInterfaceComunicacao:
    item = _interface(db, id_interface)
    if item.id_ied != id_ied:
        raise HTTPException(status_code=400, detail="A interface informada não pertence ao IED")
    return item


def _circuito_do_ied(db: Session, id_ied: int, id_circuito: int) -> models.IEDCircuito:
    item = _circuito(db, id_circuito)
    if item.id_ied != id_ied:
        raise HTTPException(status_code=400, detail="O circuito informado não pertence ao IED")
    return item


def _sinal_do_ied(db: Session, id_ied: int, id_sinal: int) -> models.IEDSinal:
    item = _sinal(db, id_sinal)
    if item.id_ied != id_ied:
        raise HTTPException(status_code=400, detail="O sinal informado não pertence ao IED")
    return item


def _equipamento_do_ied(db: Session, id_ied: int, id_ied_equipamento: int) -> models.IEDEquipamento:
    item = (
        db.query(models.IEDEquipamento)
        .filter(models.IEDEquipamento.id_ied_equipamento == id_ied_equipamento)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Vínculo de equipamento não encontrado")
    if item.id_ied != id_ied:
        raise HTTPException(status_code=400, detail="O equipamento informado não pertence ao IED")
    return item


def _ativo_codigo(db: Session, id_ied_equipamento: int | None) -> str | None:
    if not id_ied_equipamento:
        return None
    linha = (
        db.query(Ativo.codigo_ativo)
        .join(models.IEDEquipamento, models.IEDEquipamento.id_ativo == Ativo.id_ativo)
        .filter(models.IEDEquipamento.id_ied_equipamento == id_ied_equipamento)
        .first()
    )
    return linha[0] if linha else None


def _funcao_rotulos(db: Session, id_funcao_ansi: int | None) -> tuple[str | None, str | None]:
    if not id_funcao_ansi:
        return None, None
    funcao = db.query(models.FuncaoANSI).filter(models.FuncaoANSI.id_funcao_ansi == id_funcao_ansi).first()
    return (funcao.codigo, funcao.nome) if funcao else (None, None)


# --------------------------------------------------------------------------- #
# Construtores de saida
# --------------------------------------------------------------------------- #


def _protocolo_out(registro: models.IEDProtocoloComunicacao) -> schemas.ProtocoloComunicacaoOut:
    return schemas.ProtocoloComunicacaoOut(
        id_ied_protocolo_comunicacao=registro.id_ied_protocolo_comunicacao,
        id_ied_interface_comunicacao=registro.id_ied_interface_comunicacao,
        protocolo=registro.protocolo,
        papel=registro.papel,
        porta=registro.porta,
        endereco_destino=registro.endereco_destino,
        habilitado=registro.habilitado,
        observacoes=registro.observacoes,
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )


def _interface_out(db: Session, registro: models.IEDInterfaceComunicacao) -> schemas.InterfaceComunicacaoOut:
    protocolos = (
        db.query(models.IEDProtocoloComunicacao)
        .filter(models.IEDProtocoloComunicacao.id_ied_interface_comunicacao == registro.id_ied_interface_comunicacao)
        .order_by(models.IEDProtocoloComunicacao.protocolo)
        .all()
    )
    return schemas.InterfaceComunicacaoOut(
        id_ied_interface_comunicacao=registro.id_ied_interface_comunicacao,
        id_ied=registro.id_ied,
        nome=registro.nome,
        tipo=registro.tipo,
        meio=registro.meio,
        mac_address=registro.mac_address,
        endereco_ip=registro.endereco_ip,
        mascara=registro.mascara,
        gateway=registro.gateway,
        vlan=registro.vlan,
        velocidade=registro.velocidade,
        conectada=registro.conectada,
        descricao=registro.descricao,
        observacoes=registro.observacoes,
        versao=registro.versao,
        quantidade_protocolos=len(protocolos),
        protocolos=[_protocolo_out(p) for p in protocolos],
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )


def _goose_out(db: Session, registro: models.IEDGooseControle) -> schemas.GooseControleOut:
    interface = (
        db.query(models.IEDInterfaceComunicacao.nome)
        .filter(
            models.IEDInterfaceComunicacao.id_ied_interface_comunicacao
            == registro.id_ied_interface_comunicacao
        )
        .first()
        if registro.id_ied_interface_comunicacao
        else None
    )
    return schemas.GooseControleOut(
        id_ied_goose_controle=registro.id_ied_goose_controle,
        id_ied=registro.id_ied,
        id_ied_interface_comunicacao=registro.id_ied_interface_comunicacao,
        tipo=registro.tipo,
        direcao=registro.direcao,
        nome_controle=registro.nome_controle,
        dataset=registro.dataset,
        appid=registro.appid,
        mac_destino=registro.mac_destino,
        vlan=registro.vlan,
        conf_rev=registro.conf_rev,
        tempo_retransmissao_ms=registro.tempo_retransmissao_ms,
        habilitado=registro.habilitado,
        observacoes=registro.observacoes,
        interface_nome=interface[0] if interface else None,
        versao=registro.versao,
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )


def _circuito_out(db: Session, registro: models.IEDCircuito) -> schemas.CircuitoOut:
    codigo, nome = _funcao_rotulos(db, registro.id_funcao_ansi)
    quantidade = (
        db.query(func.count(models.IEDSinal.id_ied_sinal))
        .filter(models.IEDSinal.id_ied_circuito == registro.id_ied_circuito)
        .scalar()
        or 0
    )
    return schemas.CircuitoOut(
        id_ied_circuito=registro.id_ied_circuito,
        id_ied=registro.id_ied,
        codigo=registro.codigo,
        nome=registro.nome,
        tipo=registro.tipo,
        id_funcao_ansi=registro.id_funcao_ansi,
        id_ied_equipamento=registro.id_ied_equipamento,
        descricao=registro.descricao,
        observacoes=registro.observacoes,
        ativo=registro.ativo,
        funcao_codigo=codigo,
        funcao_nome=nome,
        equipamento_nome=_ativo_codigo(db, registro.id_ied_equipamento),
        quantidade_sinais=quantidade,
        versao=registro.versao,
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )


def _sinal_out(db: Session, registro: models.IEDSinal) -> schemas.SinalOut:
    codigo, nome = _funcao_rotulos(db, registro.id_funcao_ansi)
    circuito_codigo = None
    if registro.id_ied_circuito:
        circuito_codigo = (
            db.query(models.IEDCircuito.codigo)
            .filter(models.IEDCircuito.id_ied_circuito == registro.id_ied_circuito)
            .scalar()
        )
    return schemas.SinalOut(
        id_ied_sinal=registro.id_ied_sinal,
        id_ied=registro.id_ied,
        id_ied_circuito=registro.id_ied_circuito,
        id_funcao_ansi=registro.id_funcao_ansi,
        id_ied_equipamento=registro.id_ied_equipamento,
        tipo=registro.tipo,
        mnemonico=registro.mnemonico,
        descricao=registro.descricao,
        numero_terminal=registro.numero_terminal,
        unidade=registro.unidade,
        valor_nominal=registro.valor_nominal,
        estado=registro.estado,
        observacoes=registro.observacoes,
        circuito_codigo=circuito_codigo,
        funcao_codigo=codigo,
        funcao_nome=nome,
        equipamento_nome=_ativo_codigo(db, registro.id_ied_equipamento),
        versao=registro.versao,
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )


def _ensaio_item_out(db: Session, registro: models.IEDEnsaioItem) -> schemas.EnsaioItemOut:
    codigo, nome = _funcao_rotulos(db, registro.id_funcao_ansi)
    mnemonico = None
    if registro.id_ied_sinal:
        mnemonico = (
            db.query(models.IEDSinal.mnemonico)
            .filter(models.IEDSinal.id_ied_sinal == registro.id_ied_sinal)
            .scalar()
        )
    return schemas.EnsaioItemOut(
        id_ied_ensaio_item=registro.id_ied_ensaio_item,
        id_ied_ensaio=registro.id_ied_ensaio,
        id_funcao_ansi=registro.id_funcao_ansi,
        id_ied_sinal=registro.id_ied_sinal,
        ordem=registro.ordem,
        descricao=registro.descricao,
        valor_esperado=registro.valor_esperado,
        valor_medido=registro.valor_medido,
        unidade=registro.unidade,
        resultado=registro.resultado,
        observacoes=registro.observacoes,
        funcao_codigo=codigo,
        funcao_nome=nome,
        sinal_mnemonico=mnemonico,
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )


def _ensaio_arquivo_out(db: Session, registro: models.IEDEnsaioArquivo) -> schemas.EnsaioArquivoOut:
    arquivo = db.query(models.Arquivo).filter(models.Arquivo.id_arquivo == registro.id_arquivo).first()
    return schemas.EnsaioArquivoOut(
        id_ied_ensaio_arquivo=registro.id_ied_ensaio_arquivo,
        id_arquivo=registro.id_arquivo,
        nome_original=arquivo.nome_original if arquivo else "",
        tamanho_bytes=arquivo.tamanho_bytes if arquivo else 0,
        mime_type=arquivo.mime_type if arquivo else None,
        extensao=arquivo.extensao if arquivo else None,
        sha256=arquivo.sha256 if arquivo else None,
        descricao=registro.descricao,
        id_usuario_upload=registro.id_usuario_upload,
        nome_usuario_upload=_usuario_nome(db, registro.id_usuario_upload),
        criado_em=registro.criado_em,
    )


def _ensaio_base_kwargs(db: Session, registro: models.IEDEnsaio) -> dict:
    ied_tag = (
        db.query(models.IED.tag_operacional).filter(models.IED.id_ied == registro.id_ied).scalar()
    )
    return dict(
        id_ied_ensaio=registro.id_ied_ensaio,
        id_ied=registro.id_ied,
        ied_tag=ied_tag,
        numero=registro.numero,
        titulo=registro.titulo,
        tipo=registro.tipo,
        status=registro.status,
        descricao=registro.descricao,
        data_prevista=registro.data_prevista,
        data_execucao=registro.data_execucao,
        id_os=registro.id_os,
        id_usuario_executor=registro.id_usuario_executor,
        instrumentos=registro.instrumentos,
        resultado=registro.resultado,
        observacoes=registro.observacoes,
        nome_executor=_usuario_nome(db, registro.id_usuario_executor),
        versao=registro.versao,
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )


def _ensaio_out(db: Session, registro: models.IEDEnsaio) -> schemas.EnsaioOut:
    quantidade_itens = (
        db.query(func.count(models.IEDEnsaioItem.id_ied_ensaio_item))
        .filter(models.IEDEnsaioItem.id_ied_ensaio == registro.id_ied_ensaio)
        .scalar()
        or 0
    )
    quantidade_arquivos = (
        db.query(func.count(models.IEDEnsaioArquivo.id_ied_ensaio_arquivo))
        .filter(models.IEDEnsaioArquivo.id_ied_ensaio == registro.id_ied_ensaio)
        .scalar()
        or 0
    )
    return schemas.EnsaioOut(
        **_ensaio_base_kwargs(db, registro),
        quantidade_itens=quantidade_itens,
        quantidade_arquivos=quantidade_arquivos,
    )


def _ensaio_detalhe(db: Session, registro: models.IEDEnsaio) -> schemas.EnsaioDetalhe:
    itens = (
        db.query(models.IEDEnsaioItem)
        .filter(models.IEDEnsaioItem.id_ied_ensaio == registro.id_ied_ensaio)
        .order_by(models.IEDEnsaioItem.ordem, models.IEDEnsaioItem.id_ied_ensaio_item)
        .all()
    )
    arquivos = (
        db.query(models.IEDEnsaioArquivo)
        .filter(models.IEDEnsaioArquivo.id_ied_ensaio == registro.id_ied_ensaio)
        .order_by(models.IEDEnsaioArquivo.id_ied_ensaio_arquivo)
        .all()
    )
    return schemas.EnsaioDetalhe(
        **_ensaio_base_kwargs(db, registro),
        quantidade_itens=len(itens),
        quantidade_arquivos=len(arquivos),
        itens=[_ensaio_item_out(db, item) for item in itens],
        arquivos=[_ensaio_arquivo_out(db, a) for a in arquivos],
    )


# --------------------------------------------------------------------------- #
# Comunicacao / IEC 61850
# --------------------------------------------------------------------------- #


def listar_interfaces(db: Session, id_ied: int) -> list[schemas.InterfaceComunicacaoOut]:
    _ied(db, id_ied)
    registros = (
        db.query(models.IEDInterfaceComunicacao)
        .filter(models.IEDInterfaceComunicacao.id_ied == id_ied)
        .order_by(models.IEDInterfaceComunicacao.nome)
        .all()
    )
    return [_interface_out(db, r) for r in registros]


def criar_interface(db: Session, id_ied: int, dados: schemas.InterfaceComunicacaoCreate, id_usuario: int):
    _ied(db, id_ied)
    registro = models.IEDInterfaceComunicacao(
        id_ied=id_ied,
        **dados.model_dump(),
        id_usuario_criacao=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    registro.nome = _texto(registro.nome)
    db.add(registro)
    _commit(db, "Já existe uma interface com esse nome neste IED")
    db.refresh(registro)
    return _interface_out(db, registro)


def atualizar_interface(
    db: Session, id_interface: int, dados: schemas.InterfaceComunicacaoUpdate, id_usuario: int
):
    registro = _interface(db, id_interface)
    _verificar_versao(registro, dados.versao, "A interface de comunicação")
    _aplicar(registro, dados, excluir={"versao"})
    registro.versao += 1
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Já existe uma interface com esse nome neste IED")
    db.refresh(registro)
    return _interface_out(db, registro)


def remover_interface(db: Session, id_interface: int) -> None:
    registro = _interface(db, id_interface)
    db.delete(registro)
    _commit(db, "Não foi possível remover a interface de comunicação")


def adicionar_protocolo(
    db: Session,
    id_interface: int,
    dados: schemas.ProtocoloComunicacaoCreate,
    id_usuario: int,
) -> schemas.InterfaceComunicacaoOut:
    interface = _interface(db, id_interface)
    db.add(
        models.IEDProtocoloComunicacao(
            id_ied_interface_comunicacao=id_interface,
            **dados.model_dump(),
            id_usuario_criacao=id_usuario,
            id_usuario_atualizacao=id_usuario,
        )
    )
    _commit(db, "Esse protocolo/papel já está cadastrado nesta interface")
    db.refresh(interface)
    return _interface_out(db, interface)


def atualizar_protocolo(
    db: Session,
    id_protocolo: int,
    dados: schemas.ProtocoloComunicacaoUpdate,
    id_usuario: int,
) -> schemas.InterfaceComunicacaoOut:
    registro = _protocolo(db, id_protocolo)
    _aplicar(registro, dados)
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Esse protocolo/papel já está cadastrado nesta interface")
    db.refresh(registro)
    return _interface_out(db, _interface(db, registro.id_ied_interface_comunicacao))


def remover_protocolo(db: Session, id_protocolo: int) -> schemas.InterfaceComunicacaoOut:
    registro = _protocolo(db, id_protocolo)
    id_interface = registro.id_ied_interface_comunicacao
    db.delete(registro)
    _commit(db, "Não foi possível remover o protocolo")
    return _interface_out(db, _interface(db, id_interface))


def listar_goose(db: Session, id_ied: int) -> list[schemas.GooseControleOut]:
    _ied(db, id_ied)
    registros = (
        db.query(models.IEDGooseControle)
        .filter(models.IEDGooseControle.id_ied == id_ied)
        .order_by(models.IEDGooseControle.tipo, models.IEDGooseControle.direcao, models.IEDGooseControle.nome_controle)
        .all()
    )
    return [_goose_out(db, r) for r in registros]


def criar_goose(db: Session, id_ied: int, dados: schemas.GooseControleCreate, id_usuario: int):
    _ied(db, id_ied)
    if dados.id_ied_interface_comunicacao:
        _interface_do_ied(db, id_ied, dados.id_ied_interface_comunicacao)
    registro = models.IEDGooseControle(
        id_ied=id_ied,
        **dados.model_dump(),
        id_usuario_criacao=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    db.add(registro)
    _commit(db, "Já existe um controle GOOSE/SV com esse nome neste IED")
    db.refresh(registro)
    return _goose_out(db, registro)


def atualizar_goose(db: Session, id_goose: int, dados: schemas.GooseControleUpdate, id_usuario: int):
    registro = _goose(db, id_goose)
    _verificar_versao(registro, dados.versao, "O controle GOOSE/SV")
    if dados.id_ied_interface_comunicacao:
        _interface_do_ied(db, registro.id_ied, dados.id_ied_interface_comunicacao)
    _aplicar(registro, dados, excluir={"versao"})
    registro.versao += 1
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Já existe um controle GOOSE/SV com esse nome neste IED")
    db.refresh(registro)
    return _goose_out(db, registro)


def remover_goose(db: Session, id_goose: int) -> None:
    registro = _goose(db, id_goose)
    db.delete(registro)
    _commit(db, "Não foi possível remover o controle GOOSE/SV")


# --------------------------------------------------------------------------- #
# Circuitos e sinais
# --------------------------------------------------------------------------- #


def listar_circuitos(db: Session, id_ied: int) -> list[schemas.CircuitoOut]:
    _ied(db, id_ied)
    registros = (
        db.query(models.IEDCircuito)
        .filter(models.IEDCircuito.id_ied == id_ied)
        .order_by(models.IEDCircuito.codigo)
        .all()
    )
    return [_circuito_out(db, r) for r in registros]


def criar_circuito(db: Session, id_ied: int, dados: schemas.CircuitoCreate, id_usuario: int):
    _ied(db, id_ied)
    if dados.id_funcao_ansi:
        _funcao_ansi(db, dados.id_funcao_ansi)
    if dados.id_ied_equipamento:
        _equipamento_do_ied(db, id_ied, dados.id_ied_equipamento)
    registro = models.IEDCircuito(
        id_ied=id_ied,
        **dados.model_dump(),
        id_usuario_criacao=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    db.add(registro)
    _commit(db, "Já existe um circuito com esse código neste IED")
    db.refresh(registro)
    return _circuito_out(db, registro)


def atualizar_circuito(db: Session, id_circuito: int, dados: schemas.CircuitoUpdate, id_usuario: int):
    registro = _circuito(db, id_circuito)
    _verificar_versao(registro, dados.versao, "O circuito")
    if dados.id_funcao_ansi:
        _funcao_ansi(db, dados.id_funcao_ansi)
    if dados.id_ied_equipamento:
        _equipamento_do_ied(db, registro.id_ied, dados.id_ied_equipamento)
    _aplicar(registro, dados, excluir={"versao"})
    registro.versao += 1
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Já existe um circuito com esse código neste IED")
    db.refresh(registro)
    return _circuito_out(db, registro)


def remover_circuito(db: Session, id_circuito: int) -> None:
    registro = _circuito(db, id_circuito)
    db.delete(registro)
    _commit(db, "Não foi possível remover o circuito")


def listar_sinais(
    db: Session,
    id_ied: int,
    tipo: str | None = None,
    estado: str | None = None,
    id_ied_circuito: int | None = None,
) -> list[schemas.SinalOut]:
    _ied(db, id_ied)
    consulta = db.query(models.IEDSinal).filter(models.IEDSinal.id_ied == id_ied)
    if tipo:
        consulta = consulta.filter(models.IEDSinal.tipo == tipo)
    if estado:
        consulta = consulta.filter(models.IEDSinal.estado == estado)
    if id_ied_circuito:
        consulta = consulta.filter(models.IEDSinal.id_ied_circuito == id_ied_circuito)
    registros = consulta.order_by(models.IEDSinal.mnemonico).all()
    return [_sinal_out(db, r) for r in registros]


def criar_sinal(db: Session, id_ied: int, dados: schemas.SinalCreate, id_usuario: int):
    _ied(db, id_ied)
    if dados.id_ied_circuito:
        _circuito_do_ied(db, id_ied, dados.id_ied_circuito)
    if dados.id_funcao_ansi:
        _funcao_ansi(db, dados.id_funcao_ansi)
    if dados.id_ied_equipamento:
        _equipamento_do_ied(db, id_ied, dados.id_ied_equipamento)
    registro = models.IEDSinal(
        id_ied=id_ied,
        **dados.model_dump(),
        id_usuario_criacao=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    db.add(registro)
    _commit(db, "Já existe um sinal com esse mnemônico neste IED")
    db.refresh(registro)
    return _sinal_out(db, registro)


def atualizar_sinal(db: Session, id_sinal: int, dados: schemas.SinalUpdate, id_usuario: int):
    registro = _sinal(db, id_sinal)
    _verificar_versao(registro, dados.versao, "O sinal")
    if dados.id_ied_circuito:
        _circuito_do_ied(db, registro.id_ied, dados.id_ied_circuito)
    if dados.id_funcao_ansi:
        _funcao_ansi(db, dados.id_funcao_ansi)
    if dados.id_ied_equipamento:
        _equipamento_do_ied(db, registro.id_ied, dados.id_ied_equipamento)
    _aplicar(registro, dados, excluir={"versao"})
    registro.versao += 1
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Já existe um sinal com esse mnemônico neste IED")
    db.refresh(registro)
    return _sinal_out(db, registro)


def remover_sinal(db: Session, id_sinal: int) -> None:
    registro = _sinal(db, id_sinal)
    db.delete(registro)
    _commit(db, "Não foi possível remover o sinal")


# --------------------------------------------------------------------------- #
# Ensaios
# --------------------------------------------------------------------------- #


def listar_ensaios(
    db: Session,
    id_ied: int | None,
    status: str | None,
    tipo: str | None,
    busca: str | None,
    page: int,
    page_size: int,
) -> schemas.EnsaioLista:
    consulta = db.query(models.IEDEnsaio)
    if id_ied:
        consulta = consulta.filter(models.IEDEnsaio.id_ied == id_ied)
    if status:
        consulta = consulta.filter(models.IEDEnsaio.status == status)
    if tipo:
        consulta = consulta.filter(models.IEDEnsaio.tipo == tipo)
    if busca:
        termo = f"%{busca.strip()}%"
        consulta = consulta.filter(
            or_(
                models.IEDEnsaio.titulo.ilike(termo),
                models.IEDEnsaio.descricao.ilike(termo),
                models.IEDEnsaio.instrumentos.ilike(termo),
            )
        )
    total = consulta.count()
    registros = (
        consulta.order_by(models.IEDEnsaio.criado_em.desc(), models.IEDEnsaio.id_ied_ensaio.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return schemas.EnsaioLista(
        total=total,
        page=page,
        page_size=page_size,
        items=[_ensaio_out(db, r) for r in registros],
    )


def obter_ensaio(db: Session, id_ensaio: int) -> schemas.EnsaioDetalhe:
    return _ensaio_detalhe(db, _ensaio(db, id_ensaio))


def criar_ensaio(db: Session, id_ied: int, dados: schemas.EnsaioCreate, id_usuario: int):
    _ied(db, id_ied)
    proximo = (
        db.query(func.max(models.IEDEnsaio.numero)).filter(models.IEDEnsaio.id_ied == id_ied).scalar() or 0
    ) + 1
    registro = models.IEDEnsaio(
        id_ied=id_ied,
        numero=proximo,
        status="PLANEJADO",
        **dados.model_dump(),
        id_usuario_criacao=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    db.add(registro)
    _commit(db, "Não foi possível registrar o ensaio")
    db.refresh(registro)
    return _ensaio_detalhe(db, registro)


def atualizar_ensaio(db: Session, id_ensaio: int, dados: schemas.EnsaioUpdate, id_usuario: int):
    registro = _ensaio(db, id_ensaio)
    _verificar_versao(registro, dados.versao, "O ensaio")
    campos = dados.model_dump(exclude_unset=True, exclude={"versao"})
    status_novo = campos.get("status")
    if status_novo in STATUS_ENSAIO_FINAL:
        quantidade = (
            db.query(func.count(models.IEDEnsaioItem.id_ied_ensaio_item))
            .filter(models.IEDEnsaioItem.id_ied_ensaio == id_ensaio)
            .scalar()
            or 0
        )
        if quantidade == 0:
            raise HTTPException(
                status_code=400,
                detail="Adicione ao menos um item de verificação antes de concluir o ensaio",
            )
        if not campos.get("data_execucao") and not registro.data_execucao:
            registro.data_execucao = date.today()
    _aplicar(registro, dados, excluir={"versao"})
    registro.versao += 1
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível atualizar o ensaio")
    db.refresh(registro)
    return _ensaio_detalhe(db, registro)


def adicionar_item(db: Session, id_ensaio: int, dados: schemas.EnsaioItemCreate, id_usuario: int):
    ensaio = _ensaio(db, id_ensaio)
    if ensaio.status not in STATUS_ENSAIO_EDITAVEL:
        raise HTTPException(
            status_code=400, detail="Só é possível editar itens em ensaios planejados ou em andamento"
        )
    if dados.id_funcao_ansi:
        _funcao_ansi(db, dados.id_funcao_ansi)
    if dados.id_ied_sinal:
        _sinal_do_ied(db, ensaio.id_ied, dados.id_ied_sinal)
    db.add(
        models.IEDEnsaioItem(
            id_ied_ensaio=id_ensaio,
            **dados.model_dump(),
            id_usuario_criacao=id_usuario,
            id_usuario_atualizacao=id_usuario,
        )
    )
    _commit(db, "Não foi possível adicionar o item do ensaio")
    db.refresh(ensaio)
    return _ensaio_detalhe(db, ensaio)


def atualizar_item(
    db: Session, id_ensaio: int, id_item: int, dados: schemas.EnsaioItemUpdate, id_usuario: int
):
    ensaio = _ensaio(db, id_ensaio)
    item = (
        db.query(models.IEDEnsaioItem)
        .filter(
            models.IEDEnsaioItem.id_ied_ensaio_item == id_item,
            models.IEDEnsaioItem.id_ied_ensaio == id_ensaio,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item do ensaio não encontrado")
    if ensaio.status not in STATUS_ENSAIO_EDITAVEL:
        raise HTTPException(
            status_code=400, detail="Só é possível editar itens em ensaios planejados ou em andamento"
        )
    if dados.id_funcao_ansi:
        _funcao_ansi(db, dados.id_funcao_ansi)
    if dados.id_ied_sinal:
        _sinal_do_ied(db, ensaio.id_ied, dados.id_ied_sinal)
    _aplicar(item, dados)
    item.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível atualizar o item do ensaio")
    db.refresh(ensaio)
    return _ensaio_detalhe(db, ensaio)


def remover_item(db: Session, id_ensaio: int, id_item: int) -> schemas.EnsaioDetalhe:
    ensaio = _ensaio(db, id_ensaio)
    item = (
        db.query(models.IEDEnsaioItem)
        .filter(
            models.IEDEnsaioItem.id_ied_ensaio_item == id_item,
            models.IEDEnsaioItem.id_ied_ensaio == id_ensaio,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item do ensaio não encontrado")
    if ensaio.status not in STATUS_ENSAIO_EDITAVEL:
        raise HTTPException(
            status_code=400, detail="Só é possível editar itens em ensaios planejados ou em andamento"
        )
    db.delete(item)
    _commit(db, "Não foi possível remover o item do ensaio")
    db.refresh(ensaio)
    return _ensaio_detalhe(db, ensaio)


def anexar_arquivo(
    db: Session,
    id_ensaio: int,
    conteudo: bytes,
    nome_original: str,
    mime_type: str | None,
    descricao: str | None,
    id_usuario: int,
) -> schemas.EnsaioDetalhe:
    ensaio = _ensaio(db, id_ensaio)
    if ensaio.status == "CANCELADO":
        raise HTTPException(status_code=400, detail="Não é possível anexar evidências a um ensaio cancelado")
    nome_original = Path(nome_original or "").name
    if not nome_original:
        raise HTTPException(status_code=400, detail="Informe o nome do arquivo")
    extensao = Path(nome_original).suffix.lower()
    if extensao not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensão '{extensao or '(sem extensão)'}' não permitida. Opções: {', '.join(sorted(EXTENSOES_PERMITIDAS))}",
        )
    if not conteudo:
        raise HTTPException(status_code=400, detail="O arquivo está vazio")
    if len(conteudo) > MAX_ARQUIVO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"O arquivo excede o limite de {MAX_ARQUIVO_BYTES // (1024 * 1024)} MB",
        )
    validar_conteudo(extensao, conteudo)
    sha256 = hashlib.sha256(conteudo).hexdigest()
    nome_armazenado = f"{uuid4().hex}{extensao}"
    PASTA_UPLOADS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_UPLOADS / nome_armazenado
    temporario = PASTA_UPLOADS / f".{nome_armazenado}.tmp"
    try:
        temporario.write_bytes(conteudo)
        temporario.replace(destino)
        arquivo = models.Arquivo(
            nome_original=nome_original,
            nome_armazenado=nome_armazenado,
            caminho=str(destino),
            tamanho_bytes=len(conteudo),
            mime_type=_texto(mime_type),
            extensao=extensao.lstrip("."),
            sha256=sha256,
            categoria=_categoria_por_extensao(extensao),
            descricao=_texto(descricao),
            id_usuario_upload=id_usuario,
        )
        db.add(arquivo)
        db.flush()
        db.add(
            models.IEDEnsaioArquivo(
                id_ied_ensaio=id_ensaio,
                id_arquivo=arquivo.id_arquivo,
                descricao=_texto(descricao),
                id_usuario_upload=id_usuario,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        destino.unlink(missing_ok=True)
        temporario.unlink(missing_ok=True)
        raise
    db.refresh(ensaio)
    return _ensaio_detalhe(db, ensaio)


def remover_arquivo(db: Session, id_ensaio_arquivo: int) -> schemas.EnsaioDetalhe:
    vinculo = (
        db.query(models.IEDEnsaioArquivo)
        .filter(models.IEDEnsaioArquivo.id_ied_ensaio_arquivo == id_ensaio_arquivo)
        .first()
    )
    if not vinculo:
        raise HTTPException(status_code=404, detail="Arquivo do ensaio não encontrado")
    ensaio = _ensaio(db, vinculo.id_ied_ensaio)
    id_arquivo = vinculo.id_arquivo
    db.delete(vinculo)
    db.flush()
    ainda_usado = (
        db.query(models.ConfiguracaoArquivo.id_configuracao_arquivo)
        .filter(models.ConfiguracaoArquivo.id_arquivo == id_arquivo)
        .first()
        or db.query(models.IEDEnsaioArquivo.id_ied_ensaio_arquivo)
        .filter(models.IEDEnsaioArquivo.id_arquivo == id_arquivo)
        .first()
    )
    if not ainda_usado:
        arquivo = db.query(models.Arquivo).filter(models.Arquivo.id_arquivo == id_arquivo).first()
        if arquivo:
            try:
                Path(arquivo.caminho).unlink(missing_ok=True)
            except OSError:
                pass
            db.delete(arquivo)
    _commit(db, "Não foi possível remover o arquivo do ensaio")
    db.refresh(ensaio)
    return _ensaio_detalhe(db, ensaio)


def caminho_download_ensaio(db: Session, id_ensaio_arquivo: int):
    vinculo = (
        db.query(models.IEDEnsaioArquivo)
        .filter(models.IEDEnsaioArquivo.id_ied_ensaio_arquivo == id_ensaio_arquivo)
        .first()
    )
    if not vinculo:
        raise HTTPException(status_code=404, detail="Arquivo do ensaio não encontrado")
    arquivo = db.query(models.Arquivo).filter(models.Arquivo.id_arquivo == vinculo.id_arquivo).first()
    if not arquivo:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    caminho = Path(arquivo.caminho).resolve()
    if caminho.parent != PASTA_UPLOADS:
        raise HTTPException(status_code=500, detail="Caminho do arquivo fora da pasta permitida")
    if not caminho.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no armazenamento")
    return arquivo, caminho


def resumo_engenharia(db: Session) -> schemas.ResumoEngenhariaOut:
    total_interfaces = db.query(func.count(models.IEDInterfaceComunicacao.id_ied_interface_comunicacao)).scalar() or 0
    total_protocolos = db.query(func.count(models.IEDProtocoloComunicacao.id_ied_protocolo_comunicacao)).scalar() or 0
    total_goose = db.query(func.count(models.IEDGooseControle.id_ied_goose_controle)).scalar() or 0
    total_circuitos = db.query(func.count(models.IEDCircuito.id_ied_circuito)).scalar() or 0
    total_sinais = db.query(func.count(models.IEDSinal.id_ied_sinal)).scalar() or 0
    sinais_pendentes = (
        db.query(func.count(models.IEDSinal.id_ied_sinal))
        .filter(models.IEDSinal.estado == "PENDENTE")
        .scalar()
        or 0
    )
    total_ensaios = db.query(func.count(models.IEDEnsaio.id_ied_ensaio)).scalar() or 0
    ensaios_aguardando = (
        db.query(func.count(models.IEDEnsaio.id_ied_ensaio))
        .filter(models.IEDEnsaio.status.in_(("PLANEJADO", "EM_ANDAMENTO")))
        .scalar()
        or 0
    )
    ensaios_reprovados = (
        db.query(func.count(models.IEDEnsaio.id_ied_ensaio))
        .filter(models.IEDEnsaio.status == "REPROVADO")
        .scalar()
        or 0
    )
    ids_ativos = {linha[0] for linha in db.query(models.IED.id_ied).filter(models.IED.ativo.is_(True)).all()}
    ids_interfaces = {linha[0] for linha in db.query(models.IEDInterfaceComunicacao.id_ied).distinct().all()}
    ids_sinais = {linha[0] for linha in db.query(models.IEDSinal.id_ied).distinct().all()}
    ids_ensaios = {linha[0] for linha in db.query(models.IEDEnsaio.id_ied).distinct().all()}
    por_tipo_sinal = [
        schemas.DashboardItem(rotulo=tipo, quantidade=quantidade)
        for tipo, quantidade in db.query(models.IEDSinal.tipo, func.count(models.IEDSinal.id_ied_sinal))
        .group_by(models.IEDSinal.tipo)
        .order_by(models.IEDSinal.tipo)
        .all()
    ]
    por_status_ensaio = [
        schemas.DashboardItem(rotulo=status_ensaio, quantidade=quantidade)
        for status_ensaio, quantidade in db.query(
            models.IEDEnsaio.status, func.count(models.IEDEnsaio.id_ied_ensaio)
        )
        .group_by(models.IEDEnsaio.status)
        .order_by(models.IEDEnsaio.status)
        .all()
    ]
    return schemas.ResumoEngenhariaOut(
        total_interfaces=total_interfaces,
        total_protocolos=total_protocolos,
        total_goose=total_goose,
        total_circuitos=total_circuitos,
        total_sinais=total_sinais,
        sinais_pendentes=sinais_pendentes,
        total_ensaios=total_ensaios,
        ensaios_aguardando=ensaios_aguardando,
        ensaios_reprovados=ensaios_reprovados,
        ieds_sem_comunicacao=len(ids_ativos - ids_interfaces),
        ieds_sem_sinais=len(ids_ativos - ids_sinais),
        ieds_sem_ensaios=len(ids_ativos - ids_ensaios),
        por_tipo_sinal=por_tipo_sinal,
        por_status_ensaio=por_status_ensaio,
    )
