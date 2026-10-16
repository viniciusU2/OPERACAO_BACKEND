"""Fase 5 - Ocorrencias e indicadores: eventos, oscilografias (COMTRADE) e relatorios."""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.OS_models import OrdemServico
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
    validar_conteudo,
)

STATUS_OCORRENCIA_FINAL = ("ENCERRADA", "CANCELADA")


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


def _aplicar(registro, dados, excluir: set[str] | None = None, anulaveis: set[str] | None = None) -> None:
    """Aplica um Update do pydantic; ``anulaveis`` traz campos que não aceitam nulo."""
    excluir = excluir or set()
    anulaveis = anulaveis or set()
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        if campo in excluir:
            continue
        if valor is None and campo in anulaveis:
            continue
        setattr(registro, campo, _texto(valor) if isinstance(valor, str) else valor)


def _ocorrencia(db: Session, id_ocorrencia: int) -> models.IEDOcorrencia:
    item = (
        db.query(models.IEDOcorrencia)
        .filter(models.IEDOcorrencia.id_ied_ocorrencia == id_ocorrencia)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada")
    return item


def _oscilografia(db: Session, id_oscilografia: int) -> models.IEDOscilografia:
    item = (
        db.query(models.IEDOscilografia)
        .filter(models.IEDOscilografia.id_ied_oscilografia == id_oscilografia)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Oscilografia não encontrada")
    return item


def _relatorio(db: Session, id_relatorio: int) -> models.IEDRelatorio:
    item = (
        db.query(models.IEDRelatorio)
        .filter(models.IEDRelatorio.id_ied_relatorio == id_relatorio)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    return item


def _ocorrencia_do_ied(db: Session, id_ied: int, id_ocorrencia: int) -> models.IEDOcorrencia:
    item = _ocorrencia(db, id_ocorrencia)
    if item.id_ied != id_ied:
        raise HTTPException(status_code=400, detail="A ocorrência informada não pertence ao IED")
    return item


def _ied_tag(db: Session, id_ied: int) -> str | None:
    return db.query(models.IED.tag_operacional).filter(models.IED.id_ied == id_ied).scalar()


def _proximo_numero(db: Session, modelo, id_ied: int, campo_id_ied) -> int:
    atual = db.query(func.max(modelo.numero)).filter(campo_id_ied == id_ied).scalar() or 0
    return atual + 1


def _historico(
    db: Session,
    ocorrencia: models.IEDOcorrencia,
    acao: str,
    descricao: str | None,
    id_usuario: int | None,
) -> None:
    db.add(
        models.IEDOcorrenciaHistorico(
            id_ied_ocorrencia=ocorrencia.id_ied_ocorrencia,
            id_ied=ocorrencia.id_ied,
            acao=acao,
            descricao=_texto(descricao),
            id_usuario=id_usuario,
        )
    )


def _os_obrigatoria(db: Session, id_os: int | None) -> None:
    if id_os and not db.query(OrdemServico.id_os).filter(OrdemServico.id_os == id_os).first():
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")


# --------------------------------------------------------------------------- #
# Arquivos (evidencias / evidencia COMTRADE)
# --------------------------------------------------------------------------- #


def _preparar_arquivo(
    conteudo: bytes,
    nome_original: str,
    mime_type: str | None,
    descricao: str | None,
    id_usuario: int,
) -> tuple[models.Arquivo, Path]:
    nome_original = Path(nome_original or "").name
    if not nome_original:
        raise HTTPException(status_code=400, detail="Informe o nome do arquivo")
    extensao = Path(nome_original).suffix.lower()
    if extensao not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensão '{extensao or '(sem extensão)'}' não permitida. "
            f"Opções: {', '.join(sorted(EXTENSOES_PERMITIDAS))}",
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
    return arquivo, destino


def _liberar_arquivo(db: Session, id_arquivo: int) -> None:
    """Remove o arquivo físico e o registro quando não há mais vínculos."""
    ainda_usado = (
        db.query(models.ConfiguracaoArquivo.id_configuracao_arquivo)
        .filter(models.ConfiguracaoArquivo.id_arquivo == id_arquivo)
        .first()
        or db.query(models.IEDEnsaioArquivo.id_ied_ensaio_arquivo)
        .filter(models.IEDEnsaioArquivo.id_arquivo == id_arquivo)
        .first()
        or db.query(models.IEDOcorrenciaArquivo.id_ied_ocorrencia_arquivo)
        .filter(models.IEDOcorrenciaArquivo.id_arquivo == id_arquivo)
        .first()
        or db.query(models.IEDOscilografiaArquivo.id_ied_oscilografia_arquivo)
        .filter(models.IEDOscilografiaArquivo.id_arquivo == id_arquivo)
        .first()
        or db.query(models.IEDRelatorioArquivo.id_ied_relatorio_arquivo)
        .filter(models.IEDRelatorioArquivo.id_arquivo == id_arquivo)
        .first()
    )
    if ainda_usado:
        return
    arquivo = db.query(models.Arquivo).filter(models.Arquivo.id_arquivo == id_arquivo).first()
    if not arquivo:
        return
    try:
        Path(arquivo.caminho).unlink(missing_ok=True)
    except OSError:
        pass
    db.delete(arquivo)


def _caminho_download(db: Session, id_arquivo: int):
    arquivo = db.query(models.Arquivo).filter(models.Arquivo.id_arquivo == id_arquivo).first()
    if not arquivo:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    caminho = Path(arquivo.caminho).resolve()
    if caminho.parent != PASTA_UPLOADS:
        raise HTTPException(status_code=500, detail="Caminho do arquivo fora da pasta permitida")
    if not caminho.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no armazenamento")
    return arquivo, caminho


# --------------------------------------------------------------------------- #
# Construtores de saida
# --------------------------------------------------------------------------- #


def _arquivo_out(vinculo, arquivo: models.Arquivo | None) -> dict:
    return dict(
        id_arquivo=vinculo.id_arquivo,
        nome_original=arquivo.nome_original if arquivo else "",
        tamanho_bytes=arquivo.tamanho_bytes if arquivo else 0,
        mime_type=arquivo.mime_type if arquivo else None,
        extensao=arquivo.extensao if arquivo else None,
        sha256=arquivo.sha256 if arquivo else None,
        descricao=vinculo.descricao,
        id_usuario_upload=vinculo.id_usuario_upload,
    )


def _ocorrencia_arquivo_out(db: Session, vinculo: models.IEDOcorrenciaArquivo) -> schemas.OcorrenciaArquivoOut:
    arquivo = db.query(models.Arquivo).filter(models.Arquivo.id_arquivo == vinculo.id_arquivo).first()
    return schemas.OcorrenciaArquivoOut(
        id_ied_ocorrencia_arquivo=vinculo.id_ied_ocorrencia_arquivo,
        nome_usuario_upload=_usuario_nome(db, vinculo.id_usuario_upload),
        criado_em=vinculo.criado_em,
        **_arquivo_out(vinculo, arquivo),
    )


def _oscilografia_arquivo_out(
    db: Session, vinculo: models.IEDOscilografiaArquivo
) -> schemas.OscilografiaArquivoOut:
    arquivo = db.query(models.Arquivo).filter(models.Arquivo.id_arquivo == vinculo.id_arquivo).first()
    return schemas.OscilografiaArquivoOut(
        id_ied_oscilografia_arquivo=vinculo.id_ied_oscilografia_arquivo,
        nome_usuario_upload=_usuario_nome(db, vinculo.id_usuario_upload),
        criado_em=vinculo.criado_em,
        **_arquivo_out(vinculo, arquivo),
    )


def _relatorio_arquivo_out(db: Session, vinculo: models.IEDRelatorioArquivo) -> schemas.RelatorioArquivoOut:
    arquivo = db.query(models.Arquivo).filter(models.Arquivo.id_arquivo == vinculo.id_arquivo).first()
    return schemas.RelatorioArquivoOut(
        id_ied_relatorio_arquivo=vinculo.id_ied_relatorio_arquivo,
        nome_usuario_upload=_usuario_nome(db, vinculo.id_usuario_upload),
        criado_em=vinculo.criado_em,
        **_arquivo_out(vinculo, arquivo),
    )


def _ocorrencia_kwargs(db: Session, registro: models.IEDOcorrencia) -> dict:
    quantidade_arquivos = (
        db.query(func.count(models.IEDOcorrenciaArquivo.id_ied_ocorrencia_arquivo))
        .filter(models.IEDOcorrenciaArquivo.id_ied_ocorrencia == registro.id_ied_ocorrencia)
        .scalar()
        or 0
    )
    quantidade_oscilografias = (
        db.query(func.count(models.IEDOscilografia.id_ied_oscilografia))
        .filter(models.IEDOscilografia.id_ocorrencia == registro.id_ied_ocorrencia)
        .scalar()
        or 0
    )
    return dict(
        id_ied_ocorrencia=registro.id_ied_ocorrencia,
        id_ied=registro.id_ied,
        ied_tag=_ied_tag(db, registro.id_ied),
        numero=registro.numero,
        titulo=registro.titulo,
        tipo=registro.tipo,
        severidade=registro.severidade,
        status=registro.status,
        data_hora=registro.data_hora,
        descricao=registro.descricao,
        causa_provavel=registro.causa_provavel,
        acao_tomada=registro.acao_tomada,
        id_os=registro.id_os,
        id_usuario_responsavel=registro.id_usuario_registro,
        observacoes=registro.observacoes,
        id_usuario_registro=registro.id_usuario_registro,
        nome_usuario_registro=_usuario_nome(db, registro.id_usuario_registro),
        id_usuario_encerramento=registro.id_usuario_encerramento,
        nome_usuario_encerramento=_usuario_nome(db, registro.id_usuario_encerramento),
        data_encerramento=registro.data_encerramento,
        quantidade_arquivos=quantidade_arquivos,
        quantidade_oscilografias=quantidade_oscilografias,
        versao=registro.versao,
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )


def _ocorrencia_out(db: Session, registro: models.IEDOcorrencia) -> schemas.OcorrenciaOut:
    return schemas.OcorrenciaOut(**_ocorrencia_kwargs(db, registro))


def _ocorrencia_detalhe(db: Session, registro: models.IEDOcorrencia) -> schemas.OcorrenciaDetalhe:
    arquivos = (
        db.query(models.IEDOcorrenciaArquivo)
        .filter(models.IEDOcorrenciaArquivo.id_ied_ocorrencia == registro.id_ied_ocorrencia)
        .order_by(models.IEDOcorrenciaArquivo.id_ied_ocorrencia_arquivo)
        .all()
    )
    historico = (
        db.query(models.IEDOcorrenciaHistorico)
        .filter(models.IEDOcorrenciaHistorico.id_ied_ocorrencia == registro.id_ied_ocorrencia)
        .order_by(models.IEDOcorrenciaHistorico.id_ied_ocorrencia_historico.desc())
        .all()
    )
    return schemas.OcorrenciaDetalhe(
        **_ocorrencia_kwargs(db, registro),
        arquivos=[_ocorrencia_arquivo_out(db, item) for item in arquivos],
        historico=[_historico_out(db, item) for item in historico],
    )


def _historico_out(db: Session, registro: models.IEDOcorrenciaHistorico) -> schemas.OcorrenciaHistoricoOut:
    return schemas.OcorrenciaHistoricoOut(
        id_ied_ocorrencia_historico=registro.id_ied_ocorrencia_historico,
        id_ied_ocorrencia=registro.id_ied_ocorrencia,
        acao=registro.acao,
        descricao=registro.descricao,
        id_usuario=registro.id_usuario,
        nome_usuario=_usuario_nome(db, registro.id_usuario),
        criado_em=registro.criado_em,
    )


def _ocorrencia_titulo(db: Session, id_ocorrencia: int | None) -> str | None:
    if not id_ocorrencia:
        return None
    return db.query(models.IEDOcorrencia.titulo).filter(models.IEDOcorrencia.id_ied_ocorrencia == id_ocorrencia).scalar()


def _oscilografia_kwargs(db: Session, registro: models.IEDOscilografia) -> dict:
    quantidade = (
        db.query(func.count(models.IEDOscilografiaArquivo.id_ied_oscilografia_arquivo))
        .filter(models.IEDOscilografiaArquivo.id_ied_oscilografia == registro.id_ied_oscilografia)
        .scalar()
        or 0
    )
    return dict(
        id_ied_oscilografia=registro.id_ied_oscilografia,
        id_ied=registro.id_ied,
        ied_tag=_ied_tag(db, registro.id_ied),
        id_ocorrencia=registro.id_ocorrencia,
        ocorrencia_titulo=_ocorrencia_titulo(db, registro.id_ocorrencia),
        numero=registro.numero,
        nome=registro.nome,
        tipo=registro.tipo,
        data_hora=registro.data_hora,
        duracao_ms=registro.duracao_ms,
        frequencia_amostragem_hz=registro.frequencia_amostragem_hz,
        numero_canais=registro.numero_canais,
        origem=registro.origem,
        observacoes=registro.observacoes,
        quantidade_arquivos=quantidade,
        versao=registro.versao,
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )


def _oscilografia_out(db: Session, registro: models.IEDOscilografia) -> schemas.OscilografiaOut:
    return schemas.OscilografiaOut(**_oscilografia_kwargs(db, registro))


def _oscilografia_detalhe(db: Session, registro: models.IEDOscilografia) -> schemas.OscilografiaDetalhe:
    arquivos = (
        db.query(models.IEDOscilografiaArquivo)
        .filter(models.IEDOscilografiaArquivo.id_ied_oscilografia == registro.id_ied_oscilografia)
        .order_by(models.IEDOscilografiaArquivo.id_ied_oscilografia_arquivo)
        .all()
    )
    return schemas.OscilografiaDetalhe(
        **_oscilografia_kwargs(db, registro),
        arquivos=[_oscilografia_arquivo_out(db, item) for item in arquivos],
    )


def _relatorio_kwargs(db: Session, registro: models.IEDRelatorio) -> dict:
    quantidade = (
        db.query(func.count(models.IEDRelatorioArquivo.id_ied_relatorio_arquivo))
        .filter(models.IEDRelatorioArquivo.id_ied_relatorio == registro.id_ied_relatorio)
        .scalar()
        or 0
    )
    return dict(
        id_ied_relatorio=registro.id_ied_relatorio,
        id_ied=registro.id_ied,
        ied_tag=_ied_tag(db, registro.id_ied),
        id_ocorrencia=registro.id_ocorrencia,
        ocorrencia_titulo=_ocorrencia_titulo(db, registro.id_ocorrencia),
        numero=registro.numero,
        titulo=registro.titulo,
        tipo=registro.tipo,
        status=registro.status,
        data_emissao=registro.data_emissao,
        periodo_inicio=registro.periodo_inicio,
        periodo_fim=registro.periodo_fim,
        resumo=registro.resumo,
        observacoes=registro.observacoes,
        id_usuario_emissao=registro.id_usuario_emissao,
        nome_usuario_emissao=_usuario_nome(db, registro.id_usuario_emissao),
        quantidade_arquivos=quantidade,
        versao=registro.versao,
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )


def _relatorio_out(db: Session, registro: models.IEDRelatorio) -> schemas.RelatorioOut:
    return schemas.RelatorioOut(**_relatorio_kwargs(db, registro))


def _relatorio_detalhe(db: Session, registro: models.IEDRelatorio) -> schemas.RelatorioDetalhe:
    arquivos = (
        db.query(models.IEDRelatorioArquivo)
        .filter(models.IEDRelatorioArquivo.id_ied_relatorio == registro.id_ied_relatorio)
        .order_by(models.IEDRelatorioArquivo.id_ied_relatorio_arquivo)
        .all()
    )
    return schemas.RelatorioDetalhe(
        **_relatorio_kwargs(db, registro),
        arquivos=[_relatorio_arquivo_out(db, item) for item in arquivos],
    )


# --------------------------------------------------------------------------- #
# Ocorrencias
# --------------------------------------------------------------------------- #


def listar_ocorrencias(
    db: Session,
    id_ied: int | None,
    tipo: str | None,
    severidade: str | None,
    status_ocorrencia: str | None,
    busca: str | None,
    page: int,
    page_size: int,
) -> schemas.OcorrenciaLista:
    consulta = db.query(models.IEDOcorrencia)
    if id_ied:
        consulta = consulta.filter(models.IEDOcorrencia.id_ied == id_ied)
    if tipo:
        consulta = consulta.filter(models.IEDOcorrencia.tipo == tipo)
    if severidade:
        consulta = consulta.filter(models.IEDOcorrencia.severidade == severidade)
    if status_ocorrencia:
        consulta = consulta.filter(models.IEDOcorrencia.status == status_ocorrencia)
    if busca:
        termo = f"%{busca.strip()}%"
        consulta = consulta.filter(
            or_(
                models.IEDOcorrencia.titulo.ilike(termo),
                models.IEDOcorrencia.descricao.ilike(termo),
                models.IEDOcorrencia.causa_provavel.ilike(termo),
            )
        )
    total = consulta.count()
    registros = (
        consulta.order_by(models.IEDOcorrencia.data_hora.desc(), models.IEDOcorrencia.id_ied_ocorrencia.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return schemas.OcorrenciaLista(
        total=total, page=page, page_size=page_size, items=[_ocorrencia_out(db, r) for r in registros]
    )


def listar_ocorrencias_ied(db: Session, id_ied: int) -> list[schemas.OcorrenciaOut]:
    _ied(db, id_ied)
    registros = (
        db.query(models.IEDOcorrencia)
        .filter(models.IEDOcorrencia.id_ied == id_ied)
        .order_by(models.IEDOcorrencia.data_hora.desc(), models.IEDOcorrencia.id_ied_ocorrencia.desc())
        .all()
    )
    return [_ocorrencia_out(db, r) for r in registros]


def obter_ocorrencia(db: Session, id_ocorrencia: int) -> schemas.OcorrenciaDetalhe:
    return _ocorrencia_detalhe(db, _ocorrencia(db, id_ocorrencia))


def criar_ocorrencia(
    db: Session, id_ied: int, dados: schemas.OcorrenciaCreate, id_usuario: int
) -> schemas.OcorrenciaDetalhe:
    _ied(db, id_ied)
    _os_obrigatoria(db, dados.id_os)
    numero = _proximo_numero(db, models.IEDOcorrencia, id_ied, models.IEDOcorrencia.id_ied)
    registro = models.IEDOcorrencia(
        id_ied=id_ied,
        numero=numero,
        status="ABERTA",
        titulo=dados.titulo.strip(),
        tipo=dados.tipo,
        severidade=dados.severidade,
        data_hora=dados.data_hora or datetime.now(),
        descricao=_texto(dados.descricao),
        causa_provavel=_texto(dados.causa_provavel),
        acao_tomada=_texto(dados.acao_tomada),
        id_os=dados.id_os,
        id_usuario_registro=id_usuario,
        observacoes=_texto(dados.observacoes),
        id_usuario_criacao=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    db.add(registro)
    try:
        db.flush()
        _historico(db, registro, "CRIACAO", f"Ocorrência registrada ({dados.severidade})", id_usuario)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível registrar a ocorrência") from exc
    db.refresh(registro)
    return _ocorrencia_detalhe(db, registro)


def atualizar_ocorrencia(
    db: Session, id_ocorrencia: int, dados: schemas.OcorrenciaUpdate, id_usuario: int
) -> schemas.OcorrenciaDetalhe:
    registro = _ocorrencia(db, id_ocorrencia)
    _verificar_versao(registro, dados.versao, "A ocorrência")
    _os_obrigatoria(db, dados.id_os)
    payload = dados.model_dump(exclude_unset=True)
    campos = {campo: valor for campo, valor in payload.items() if campo not in ("versao", "id_usuario_responsavel")}
    if campos.get("data_hora") is None:
        campos.pop("data_hora", None)
    status_anterior = registro.status
    status_novo = campos.get("status", status_anterior)
    for campo, valor in campos.items():
        setattr(registro, campo, _texto(valor) if isinstance(valor, str) else valor)
    if "id_usuario_responsavel" in payload:
        registro.id_usuario_registro = payload["id_usuario_responsavel"]
    if status_novo == "ENCERRADA":
        registro.data_encerramento = registro.data_encerramento or datetime.now()
        registro.id_usuario_encerramento = id_usuario
        acao, descricao = "ENCERRAMENTO", f"Status: {status_anterior} → {status_novo}"
    elif status_novo == "CANCELADA":
        acao, descricao = "CANCELAMENTO", f"Status: {status_anterior} → {status_novo}"
    elif status_anterior in STATUS_OCORRENCIA_FINAL and status_novo not in STATUS_OCORRENCIA_FINAL:
        registro.data_encerramento = None
        registro.id_usuario_encerramento = None
        acao, descricao = "REABERTURA", f"Status: {status_anterior} → {status_novo}"
    else:
        acao = "ATUALIZACAO"
        descricao = f"Status: {status_anterior} → {status_novo}" if status_novo != status_anterior else "Dados atualizados"
    registro.versao += 1
    registro.id_usuario_atualizacao = id_usuario
    _historico(db, registro, acao, descricao, id_usuario)
    _commit(db, "Não foi possível atualizar a ocorrência")
    db.refresh(registro)
    return _ocorrencia_detalhe(db, registro)


def remover_ocorrencia(db: Session, id_ocorrencia: int) -> None:
    registro = _ocorrencia(db, id_ocorrencia)
    ids_arquivos = [
        linha[0]
        for linha in db.query(models.IEDOcorrenciaArquivo.id_arquivo)
        .filter(models.IEDOcorrenciaArquivo.id_ied_ocorrencia == id_ocorrencia)
        .all()
    ]
    ids_oscilografias = [
        linha[0]
        for linha in db.query(models.IEDOscilografia.id_ied_oscilografia)
        .filter(models.IEDOscilografia.id_ocorrencia == id_ocorrencia)
        .all()
    ]
    for id_oscilografia in ids_oscilografias:
        ids_arquivos.extend(
            linha[0]
            for linha in db.query(models.IEDOscilografiaArquivo.id_arquivo)
            .filter(models.IEDOscilografiaArquivo.id_ied_oscilografia == id_oscilografia)
            .all()
        )
    db.delete(registro)
    db.flush()
    for id_arquivo in ids_arquivos:
        _liberar_arquivo(db, id_arquivo)
    _commit(db, "Não foi possível remover a ocorrência")


def encerrar_ocorrencia(
    db: Session, id_ocorrencia: int, dados: schemas.EncerramentoOcorrencia | None, id_usuario: int
) -> schemas.OcorrenciaDetalhe:
    registro = _ocorrencia(db, id_ocorrencia)
    if registro.status in STATUS_OCORRENCIA_FINAL:
        raise HTTPException(status_code=400, detail="A ocorrência já está encerrada ou cancelada")
    registro.status = "ENCERRADA"
    registro.data_encerramento = datetime.now()
    registro.id_usuario_encerramento = id_usuario
    registro.versao += 1
    registro.id_usuario_atualizacao = id_usuario
    _historico(db, registro, "ENCERRAMENTO", (dados.comentario if dados else None) or "Ocorrência encerrada", id_usuario)
    _commit(db, "Não foi possível encerrar a ocorrência")
    db.refresh(registro)
    return _ocorrencia_detalhe(db, registro)


def anexar_arquivo_ocorrencia(
    db: Session,
    id_ocorrencia: int,
    conteudo: bytes,
    nome_original: str,
    mime_type: str | None,
    descricao: str | None,
    id_usuario: int,
) -> schemas.OcorrenciaDetalhe:
    ocorrencia = _ocorrencia(db, id_ocorrencia)
    arquivo, destino = _preparar_arquivo(conteudo, nome_original, mime_type, descricao, id_usuario)
    try:
        db.add(arquivo)
        db.flush()
        db.add(
            models.IEDOcorrenciaArquivo(
                id_ied_ocorrencia=id_ocorrencia,
                id_arquivo=arquivo.id_arquivo,
                descricao=_texto(descricao),
                id_usuario_upload=id_usuario,
            )
        )
        ocorrencia.id_usuario_atualizacao = id_usuario
        _historico(db, ocorrencia, "ANEXO", f"Evidência anexada: {arquivo.nome_original}", id_usuario)
        db.commit()
    except Exception:
        db.rollback()
        destino.unlink(missing_ok=True)
        raise
    db.refresh(ocorrencia)
    return _ocorrencia_detalhe(db, ocorrencia)


def remover_arquivo_ocorrencia(
    db: Session, id_arquivo_vinculo: int, id_usuario: int | None = None
) -> schemas.OcorrenciaDetalhe:
    vinculo = (
        db.query(models.IEDOcorrenciaArquivo)
        .filter(models.IEDOcorrenciaArquivo.id_ied_ocorrencia_arquivo == id_arquivo_vinculo)
        .first()
    )
    if not vinculo:
        raise HTTPException(status_code=404, detail="Arquivo da ocorrência não encontrado")
    ocorrencia = _ocorrencia(db, vinculo.id_ied_ocorrencia)
    id_arquivo = vinculo.id_arquivo
    db.delete(vinculo)
    db.flush()
    _liberar_arquivo(db, id_arquivo)
    _historico(db, ocorrencia, "REMOCAO_ARQUIVO", "Evidência removida", id_usuario)
    _commit(db, "Não foi possível remover o arquivo da ocorrência")
    db.refresh(ocorrencia)
    return _ocorrencia_detalhe(db, ocorrencia)


def caminho_download_ocorrencia(db: Session, id_arquivo_vinculo: int):
    vinculo = (
        db.query(models.IEDOcorrenciaArquivo)
        .filter(models.IEDOcorrenciaArquivo.id_ied_ocorrencia_arquivo == id_arquivo_vinculo)
        .first()
    )
    if not vinculo:
        raise HTTPException(status_code=404, detail="Arquivo da ocorrência não encontrado")
    return _caminho_download(db, vinculo.id_arquivo)


# --------------------------------------------------------------------------- #
# Oscilografias (COMTRADE)
# --------------------------------------------------------------------------- #


def listar_oscilografias(
    db: Session,
    id_ied: int | None,
    tipo: str | None,
    id_ocorrencia: int | None,
    busca: str | None,
    page: int,
    page_size: int,
) -> schemas.OscilografiaLista:
    consulta = db.query(models.IEDOscilografia)
    if id_ied:
        consulta = consulta.filter(models.IEDOscilografia.id_ied == id_ied)
    if tipo:
        consulta = consulta.filter(models.IEDOscilografia.tipo == tipo)
    if id_ocorrencia:
        consulta = consulta.filter(models.IEDOscilografia.id_ocorrencia == id_ocorrencia)
    if busca:
        termo = f"%{busca.strip()}%"
        consulta = consulta.filter(
            or_(
                models.IEDOscilografia.nome.ilike(termo),
                models.IEDOscilografia.origem.ilike(termo),
                models.IEDOscilografia.observacoes.ilike(termo),
            )
        )
    total = consulta.count()
    registros = (
        consulta.order_by(models.IEDOscilografia.data_hora.desc(), models.IEDOscilografia.id_ied_oscilografia.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return schemas.OscilografiaLista(
        total=total, page=page, page_size=page_size, items=[_oscilografia_out(db, r) for r in registros]
    )


def listar_oscilografias_ied(db: Session, id_ied: int) -> list[schemas.OscilografiaOut]:
    _ied(db, id_ied)
    registros = (
        db.query(models.IEDOscilografia)
        .filter(models.IEDOscilografia.id_ied == id_ied)
        .order_by(models.IEDOscilografia.data_hora.desc(), models.IEDOscilografia.id_ied_oscilografia.desc())
        .all()
    )
    return [_oscilografia_out(db, r) for r in registros]


def obter_oscilografia(db: Session, id_oscilografia: int) -> schemas.OscilografiaDetalhe:
    return _oscilografia_detalhe(db, _oscilografia(db, id_oscilografia))


def criar_oscilografia(
    db: Session, id_ied: int, dados: schemas.OscilografiaCreate, id_usuario: int
) -> schemas.OscilografiaDetalhe:
    _ied(db, id_ied)
    ocorrencia = None
    if dados.id_ocorrencia:
        ocorrencia = _ocorrencia_do_ied(db, id_ied, dados.id_ocorrencia)
    numero = _proximo_numero(db, models.IEDOscilografia, id_ied, models.IEDOscilografia.id_ied)
    registro = models.IEDOscilografia(
        id_ied=id_ied,
        numero=numero,
        nome=dados.nome.strip(),
        tipo=dados.tipo,
        data_hora=dados.data_hora or datetime.now(),
        duracao_ms=dados.duracao_ms,
        frequencia_amostragem_hz=dados.frequencia_amostragem_hz,
        numero_canais=dados.numero_canais,
        origem=_texto(dados.origem),
        id_ocorrencia=dados.id_ocorrencia,
        observacoes=_texto(dados.observacoes),
        id_usuario_criacao=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    db.add(registro)
    if ocorrencia:
        db.flush()
        _historico(db, ocorrencia, "OSCILOGRAFIA", f"Oscilografia vinculada: {registro.nome}", id_usuario)
    _commit(db, "Não foi possível registrar a oscilografia")
    db.refresh(registro)
    return _oscilografia_detalhe(db, registro)


def atualizar_oscilografia(
    db: Session, id_oscilografia: int, dados: schemas.OscilografiaUpdate, id_usuario: int
) -> schemas.OscilografiaDetalhe:
    registro = _oscilografia(db, id_oscilografia)
    _verificar_versao(registro, dados.versao, "A oscilografia")
    if dados.id_ocorrencia:
        _ocorrencia_do_ied(db, registro.id_ied, dados.id_ocorrencia)
    _aplicar(registro, dados, excluir={"versao"}, anulaveis={"data_hora"})
    registro.versao += 1
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível atualizar a oscilografia")
    db.refresh(registro)
    return _oscilografia_detalhe(db, registro)


def remover_oscilografia(db: Session, id_oscilografia: int) -> None:
    registro = _oscilografia(db, id_oscilografia)
    ids_arquivos = [
        linha[0]
        for linha in db.query(models.IEDOscilografiaArquivo.id_arquivo)
        .filter(models.IEDOscilografiaArquivo.id_ied_oscilografia == id_oscilografia)
        .all()
    ]
    db.delete(registro)
    db.flush()
    for id_arquivo in ids_arquivos:
        _liberar_arquivo(db, id_arquivo)
    _commit(db, "Não foi possível remover a oscilografia")


def anexar_arquivo_oscilografia(
    db: Session,
    id_oscilografia: int,
    conteudo: bytes,
    nome_original: str,
    mime_type: str | None,
    descricao: str | None,
    id_usuario: int,
) -> schemas.OscilografiaDetalhe:
    oscilografia = _oscilografia(db, id_oscilografia)
    arquivo, destino = _preparar_arquivo(conteudo, nome_original, mime_type, descricao, id_usuario)
    try:
        db.add(arquivo)
        db.flush()
        db.add(
            models.IEDOscilografiaArquivo(
                id_ied_oscilografia=id_oscilografia,
                id_arquivo=arquivo.id_arquivo,
                descricao=_texto(descricao),
                id_usuario_upload=id_usuario,
            )
        )
        oscilografia.id_usuario_atualizacao = id_usuario
        db.commit()
    except Exception:
        db.rollback()
        destino.unlink(missing_ok=True)
        raise
    db.refresh(oscilografia)
    return _oscilografia_detalhe(db, oscilografia)


def remover_arquivo_oscilografia(db: Session, id_arquivo_vinculo: int) -> schemas.OscilografiaDetalhe:
    vinculo = (
        db.query(models.IEDOscilografiaArquivo)
        .filter(models.IEDOscilografiaArquivo.id_ied_oscilografia_arquivo == id_arquivo_vinculo)
        .first()
    )
    if not vinculo:
        raise HTTPException(status_code=404, detail="Arquivo da oscilografia não encontrado")
    oscilografia = _oscilografia(db, vinculo.id_ied_oscilografia)
    id_arquivo = vinculo.id_arquivo
    db.delete(vinculo)
    db.flush()
    _liberar_arquivo(db, id_arquivo)
    _commit(db, "Não foi possível remover o arquivo da oscilografia")
    db.refresh(oscilografia)
    return _oscilografia_detalhe(db, oscilografia)


def caminho_download_oscilografia(db: Session, id_arquivo_vinculo: int):
    vinculo = (
        db.query(models.IEDOscilografiaArquivo)
        .filter(models.IEDOscilografiaArquivo.id_ied_oscilografia_arquivo == id_arquivo_vinculo)
        .first()
    )
    if not vinculo:
        raise HTTPException(status_code=404, detail="Arquivo da oscilografia não encontrado")
    return _caminho_download(db, vinculo.id_arquivo)


# --------------------------------------------------------------------------- #
# Relatorios
# --------------------------------------------------------------------------- #


def listar_relatorios(
    db: Session,
    id_ied: int | None,
    tipo: str | None,
    status_relatorio: str | None,
    id_ocorrencia: int | None,
    busca: str | None,
    page: int,
    page_size: int,
) -> schemas.RelatorioLista:
    consulta = db.query(models.IEDRelatorio)
    if id_ied:
        consulta = consulta.filter(models.IEDRelatorio.id_ied == id_ied)
    if tipo:
        consulta = consulta.filter(models.IEDRelatorio.tipo == tipo)
    if status_relatorio:
        consulta = consulta.filter(models.IEDRelatorio.status == status_relatorio)
    if id_ocorrencia:
        consulta = consulta.filter(models.IEDRelatorio.id_ocorrencia == id_ocorrencia)
    if busca:
        termo = f"%{busca.strip()}%"
        consulta = consulta.filter(
            or_(models.IEDRelatorio.titulo.ilike(termo), models.IEDRelatorio.resumo.ilike(termo))
        )
    total = consulta.count()
    registros = (
        consulta.order_by(models.IEDRelatorio.criado_em.desc(), models.IEDRelatorio.id_ied_relatorio.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return schemas.RelatorioLista(
        total=total, page=page, page_size=page_size, items=[_relatorio_out(db, r) for r in registros]
    )


def listar_relatorios_ied(db: Session, id_ied: int) -> list[schemas.RelatorioOut]:
    _ied(db, id_ied)
    registros = (
        db.query(models.IEDRelatorio)
        .filter(models.IEDRelatorio.id_ied == id_ied)
        .order_by(models.IEDRelatorio.criado_em.desc(), models.IEDRelatorio.id_ied_relatorio.desc())
        .all()
    )
    return [_relatorio_out(db, r) for r in registros]


def obter_relatorio(db: Session, id_relatorio: int) -> schemas.RelatorioDetalhe:
    return _relatorio_detalhe(db, _relatorio(db, id_relatorio))


def criar_relatorio(
    db: Session, id_ied: int, dados: schemas.RelatorioCreate, id_usuario: int
) -> schemas.RelatorioDetalhe:
    _ied(db, id_ied)
    ocorrencia = None
    if dados.id_ocorrencia:
        ocorrencia = _ocorrencia_do_ied(db, id_ied, dados.id_ocorrencia)
    numero = _proximo_numero(db, models.IEDRelatorio, id_ied, models.IEDRelatorio.id_ied)
    registro = models.IEDRelatorio(
        id_ied=id_ied,
        numero=numero,
        titulo=dados.titulo.strip(),
        tipo=dados.tipo,
        status="RASCUNHO",
        data_emissao=dados.data_emissao,
        periodo_inicio=dados.periodo_inicio,
        periodo_fim=dados.periodo_fim,
        resumo=_texto(dados.resumo),
        id_ocorrencia=dados.id_ocorrencia,
        observacoes=_texto(dados.observacoes),
        id_usuario_emissao=id_usuario,
        id_usuario_criacao=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    db.add(registro)
    if ocorrencia:
        db.flush()
        _historico(db, ocorrencia, "RELATORIO", f"Relatório vinculado: {registro.titulo}", id_usuario)
    _commit(db, "Não foi possível registrar o relatório")
    db.refresh(registro)
    return _relatorio_detalhe(db, registro)


def atualizar_relatorio(
    db: Session, id_relatorio: int, dados: schemas.RelatorioUpdate, id_usuario: int
) -> schemas.RelatorioDetalhe:
    registro = _relatorio(db, id_relatorio)
    _verificar_versao(registro, dados.versao, "O relatório")
    if dados.id_ocorrencia:
        _ocorrencia_do_ied(db, registro.id_ied, dados.id_ocorrencia)
    campos = dados.model_dump(exclude_unset=True, exclude={"versao"})
    status_novo = campos.get("status")
    for campo, valor in campos.items():
        setattr(registro, campo, _texto(valor) if isinstance(valor, str) else valor)
    if status_novo in ("EMITIDO", "APROVADO") and not registro.data_emissao:
        registro.data_emissao = date.today()
    registro.versao += 1
    registro.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível atualizar o relatório")
    db.refresh(registro)
    return _relatorio_detalhe(db, registro)


def remover_relatorio(db: Session, id_relatorio: int) -> None:
    registro = _relatorio(db, id_relatorio)
    ids_arquivos = [
        linha[0]
        for linha in db.query(models.IEDRelatorioArquivo.id_arquivo)
        .filter(models.IEDRelatorioArquivo.id_ied_relatorio == id_relatorio)
        .all()
    ]
    db.delete(registro)
    db.flush()
    for id_arquivo in ids_arquivos:
        _liberar_arquivo(db, id_arquivo)
    _commit(db, "Não foi possível remover o relatório")


def anexar_arquivo_relatorio(
    db: Session,
    id_relatorio: int,
    conteudo: bytes,
    nome_original: str,
    mime_type: str | None,
    descricao: str | None,
    id_usuario: int,
) -> schemas.RelatorioDetalhe:
    relatorio = _relatorio(db, id_relatorio)
    arquivo, destino = _preparar_arquivo(conteudo, nome_original, mime_type, descricao, id_usuario)
    try:
        db.add(arquivo)
        db.flush()
        db.add(
            models.IEDRelatorioArquivo(
                id_ied_relatorio=id_relatorio,
                id_arquivo=arquivo.id_arquivo,
                descricao=_texto(descricao),
                id_usuario_upload=id_usuario,
            )
        )
        relatorio.id_usuario_atualizacao = id_usuario
        db.commit()
    except Exception:
        db.rollback()
        destino.unlink(missing_ok=True)
        raise
    db.refresh(relatorio)
    return _relatorio_detalhe(db, relatorio)


def remover_arquivo_relatorio(db: Session, id_arquivo_vinculo: int) -> schemas.RelatorioDetalhe:
    vinculo = (
        db.query(models.IEDRelatorioArquivo)
        .filter(models.IEDRelatorioArquivo.id_ied_relatorio_arquivo == id_arquivo_vinculo)
        .first()
    )
    if not vinculo:
        raise HTTPException(status_code=404, detail="Arquivo do relatório não encontrado")
    relatorio = _relatorio(db, vinculo.id_ied_relatorio)
    id_arquivo = vinculo.id_arquivo
    db.delete(vinculo)
    db.flush()
    _liberar_arquivo(db, id_arquivo)
    _commit(db, "Não foi possível remover o arquivo do relatório")
    db.refresh(relatorio)
    return _relatorio_detalhe(db, relatorio)


def caminho_download_relatorio(db: Session, id_arquivo_vinculo: int):
    vinculo = (
        db.query(models.IEDRelatorioArquivo)
        .filter(models.IEDRelatorioArquivo.id_ied_relatorio_arquivo == id_arquivo_vinculo)
        .first()
    )
    if not vinculo:
        raise HTTPException(status_code=404, detail="Arquivo do relatório não encontrado")
    return _caminho_download(db, vinculo.id_arquivo)


# --------------------------------------------------------------------------- #
# Auditoria e indicadores
# --------------------------------------------------------------------------- #


def listar_auditoria(
    db: Session,
    id_ied: int | None,
    id_ocorrencia: int | None,
    acao: str | None,
    limite: int,
    offset: int = 0,
) -> list[schemas.AuditoriaOut]:
    consulta = (
        db.query(models.IEDOcorrenciaHistorico, models.IEDOcorrencia, Usuario)
        .join(
            models.IEDOcorrencia,
            models.IEDOcorrencia.id_ied_ocorrencia == models.IEDOcorrenciaHistorico.id_ied_ocorrencia,
        )
        .outerjoin(Usuario, Usuario.id == models.IEDOcorrenciaHistorico.id_usuario)
    )
    if id_ied:
        consulta = consulta.filter(models.IEDOcorrenciaHistorico.id_ied == id_ied)
    if id_ocorrencia:
        consulta = consulta.filter(models.IEDOcorrenciaHistorico.id_ied_ocorrencia == id_ocorrencia)
    if acao:
        consulta = consulta.filter(models.IEDOcorrenciaHistorico.acao == acao)
    linhas = (
        consulta.order_by(
            models.IEDOcorrenciaHistorico.criado_em.desc(),
            models.IEDOcorrenciaHistorico.id_ied_ocorrencia_historico.desc(),
        )
        .offset(max(offset, 0))
        .limit(limite)
        .all()
    )
    return [
        schemas.AuditoriaOut(
            id_ied_ocorrencia_historico=historico.id_ied_ocorrencia_historico,
            id_ied_ocorrencia=historico.id_ied_ocorrencia,
            id_ied=historico.id_ied,
            ied_tag=_ied_tag(db, historico.id_ied),
            numero_ocorrencia=ocorrencia.numero,
            ocorrencia_titulo=ocorrencia.titulo,
            acao=historico.acao,
            descricao=historico.descricao,
            id_usuario=historico.id_usuario,
            nome_usuario=usuario.nome if usuario else None,
            criado_em=historico.criado_em,
        )
        for historico, ocorrencia, usuario in linhas
    ]


def resumo_ocorrencias(db: Session) -> schemas.ResumoOcorrenciaOut:
    total_ocorrencias = db.query(func.count(models.IEDOcorrencia.id_ied_ocorrencia)).scalar() or 0
    abertas = (
        db.query(func.count(models.IEDOcorrencia.id_ied_ocorrencia))
        .filter(models.IEDOcorrencia.status.in_(("ABERTA", "EM_ANALISE")))
        .scalar()
        or 0
    )
    criticas = (
        db.query(func.count(models.IEDOcorrencia.id_ied_ocorrencia))
        .filter(models.IEDOcorrencia.severidade == "CRITICA")
        .scalar()
        or 0
    )
    encerradas = (
        db.query(func.count(models.IEDOcorrencia.id_ied_ocorrencia))
        .filter(models.IEDOcorrencia.status == "ENCERRADA")
        .scalar()
        or 0
    )
    total_oscilografias = db.query(func.count(models.IEDOscilografia.id_ied_oscilografia)).scalar() or 0
    total_relatorios = db.query(func.count(models.IEDRelatorio.id_ied_relatorio)).scalar() or 0
    relatorios_aguardando = (
        db.query(func.count(models.IEDRelatorio.id_ied_relatorio))
        .filter(models.IEDRelatorio.status == "RASCUNHO")
        .scalar()
        or 0
    )
    ids_ativos = {linha[0] for linha in db.query(models.IED.id_ied).filter(models.IED.ativo.is_(True)).all()}
    ids_ocorrencias = {linha[0] for linha in db.query(models.IEDOcorrencia.id_ied).distinct().all()}
    ids_relatorios = {linha[0] for linha in db.query(models.IEDRelatorio.id_ied).distinct().all()}
    por_tipo = [
        schemas.DashboardItem(rotulo=rotulo, quantidade=quantidade)
        for rotulo, quantidade in db.query(models.IEDOcorrencia.tipo, func.count(models.IEDOcorrencia.id_ied_ocorrencia))
        .group_by(models.IEDOcorrencia.tipo)
        .order_by(func.count(models.IEDOcorrencia.id_ied_ocorrencia).desc())
        .all()
    ]
    por_severidade = [
        schemas.DashboardItem(rotulo=rotulo, quantidade=quantidade)
        for rotulo, quantidade in db.query(
            models.IEDOcorrencia.severidade, func.count(models.IEDOcorrencia.id_ied_ocorrencia)
        )
        .group_by(models.IEDOcorrencia.severidade)
        .all()
    ]
    por_status = [
        schemas.DashboardItem(rotulo=rotulo, quantidade=quantidade)
        for rotulo, quantidade in db.query(
            models.IEDOcorrencia.status, func.count(models.IEDOcorrencia.id_ied_ocorrencia)
        )
        .group_by(models.IEDOcorrencia.status)
        .all()
    ]
    return schemas.ResumoOcorrenciaOut(
        total_ocorrencias=total_ocorrencias,
        ocorrencias_abertas=abertas,
        ocorrencias_criticas=criticas,
        ocorrencias_encerradas=encerradas,
        total_oscilografias=total_oscilografias,
        total_relatorios=total_relatorios,
        relatorios_aguardando=relatorios_aguardando,
        ieds_sem_ocorrencia=len(ids_ativos - ids_ocorrencias),
        ieds_sem_relatorio=len(ids_ativos - ids_relatorios),
        por_tipo=por_tipo,
        por_severidade=por_severidade,
        por_status=por_status,
    )
