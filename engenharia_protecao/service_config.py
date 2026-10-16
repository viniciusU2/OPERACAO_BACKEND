from __future__ import annotations

import hashlib
import os
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.OS_models import OrdemServico
from models.auth_models import Usuario

from . import models, schemas

PASTA_UPLOADS = Path(os.getenv("ENGENHARIA_PROTECAO_UPLOAD_DIR", "saida/engenharia_protecao")).resolve()
MAX_ARQUIVO_BYTES = int(os.getenv("ENGENHARIA_PROTECAO_MAX_ARQUIVO_MB", "100")) * 1024 * 1024
EXTENSOES_PERMITIDAS = {
    ".zip", ".xml", ".cid", ".scd", ".ssd", ".apc", ".pfd", ".eft",
    ".txt", ".csv", ".json", ".rtf", ".pdf", ".docx", ".xlsx",
    ".cfg", ".dat", ".cff", ".hdr", ".rep",
}

# Defesa em profundidade: para formatos com assinatura bem definida, valida o
# conteudo (magic bytes) alem da extensao. Formatos textuais/binarios ambiguos
# (COMTRADE .cfg/.dat/.cff/.hdr, DIGSI, .txt/.csv/.json) ficam de fora.
ASSINATURAS_CONTEUDO: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF-",),
    ".zip": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
}
EXTENSOES_XML = {".xml", ".scd", ".ssd"}


def validar_conteudo(extensao: str, conteudo: bytes) -> None:
    """Valida a assinatura do arquivo quando o formato permite."""
    assinaturas = ASSINATURAS_CONTEUDO.get(extensao)
    if assinaturas and not conteudo.startswith(assinaturas):
        raise HTTPException(
            status_code=400,
            detail=f"O conteudo do arquivo nao corresponde a assinatura da extensao '{extensao}'.",
        )
    if extensao in EXTENSOES_XML:
        amostra = conteudo[:64].lstrip(b"\xef\xbb\xbf \t\r\n")
        if not amostra.startswith(b"<"):
            raise HTTPException(
                status_code=400,
                detail=f"O conteudo do arquivo nao e um XML valido para a extensao '{extensao}'.",
            )


# --------------------------------------------------------------------------- #
# Catalogo ANSI (seed idempotente)
# --------------------------------------------------------------------------- #

CATALOGO_ANSI: list[tuple[str, str, str]] = [
    ("21", "Proteção de distância", "LINHA"),
    ("21N", "Proteção de distância de terra", "LINHA"),
    ("25", "Verificação de sincronismo", "BARRAMENTO"),
    ("27", "Subtensão", "TENSÃO"),
    ("32", "Potência reversa", "POTÊNCIA"),
    ("37", "Subcorrente / falta de corrente", "CORRENTE"),
    ("46", "Desequilíbrio de corrente (sequência negativa)", "CORRENTE"),
    ("49", "Sobrecarga térmica", "MÁQUINA"),
    ("50", "Sobrecorrente instantâneo de fase", "CORRENTE"),
    ("50N", "Sobrecorrente instantâneo de neutro", "CORRENTE"),
    ("50BF", "Falha de disjuntor", "BARRAMENTO"),
    ("51", "Sobrecorrente temporizado de fase", "CORRENTE"),
    ("51N", "Sobrecorrente temporizado de neutro", "CORRENTE"),
    ("59", "Sobretensão", "TENSÃO"),
    ("59N", "Sobretensão de neutro", "TENSÃO"),
    ("64", "Proteção de falta à terra", "TERRA"),
    ("67", "Sobrecorrente direcional", "CORRENTE"),
    ("67N", "Sobrecorrente direcional de neutro", "CORRENTE"),
    ("79", "Religamento automático", "LINHA"),
    ("81", "Proteção de frequência", "FREQUÊNCIA"),
    ("86", "Relé de bloqueio / rearme", "AUXILIAR"),
    ("87L", "Diferencial de linha", "LINHA"),
    ("87T", "Diferencial de transformador", "TRANSFORMADOR"),
    ("87B", "Diferencial de barra", "BARRAMENTO"),
]

SEED_PARAMETROS: dict[str, list[tuple[str, str, str | None, str]]] = {
    "21": [("Zona1", "Alcance da zona 1", "Ω", "NUMERICO"), ("Zona2", "Alcance da zona 2", "Ω", "NUMERICO")],
    "27": [("Pickup", "Tensão de partida (subtensão)", "V", "NUMERICO"), ("Tempo", "Tempo de atuação", "s", "TEMPO")],
    "50": [("Pickup", "Corrente de partida", "A", "NUMERICO"), ("Tempo", "Tempo de atuação", "s", "TEMPO")],
    "50N": [("Pickup", "Corrente de partida de neutro", "A", "NUMERICO"), ("Tempo", "Tempo de atuação", "s", "TEMPO")],
    "51": [
        ("Pickup", "Corrente de partida", "A", "NUMERICO"),
        ("Curva", "Curva de tempo", None, "TEXTO"),
        ("DialTempo", "Multiplicador de tempo (dial)", None, "NUMERICO"),
        ("Tempo", "Tempo mínimo de atuação", "s", "TEMPO"),
    ],
    "51N": [
        ("Pickup", "Corrente de partida de neutro", "A", "NUMERICO"),
        ("Curva", "Curva de tempo", None, "TEXTO"),
        ("DialTempo", "Multiplicador de tempo (dial)", None, "NUMERICO"),
    ],
    "59": [("Pickup", "Tensão de partida (sobretensão)", "V", "NUMERICO"), ("Tempo", "Tempo de atuação", "s", "TEMPO")],
    "59N": [("Pickup", "Tensão de partida de neutro", "V", "NUMERICO"), ("Tempo", "Tempo de atuação", "s", "TEMPO")],
    "67": [("Pickup", "Corrente de partida", "A", "NUMERICO"), ("Angulo", "Ângulo característico", "°", "NUMERICO")],
    "67N": [("Pickup", "Corrente de partida de neutro", "A", "NUMERICO"), ("Angulo", "Ângulo característico", "°", "NUMERICO")],
    "79": [("Tentativas", "Número de tentativas de religamento", "un", "NUMERICO"), ("TempoMorto", "Tempo morto entre religamentos", "s", "TEMPO")],
    "81": [("FreqMin", "Frequência mínima", "Hz", "NUMERICO"), ("FreqMax", "Frequência máxima", "Hz", "NUMERICO")],
    "87L": [("Pickup", "Corrente diferencial de partida", "A", "NUMERICO")],
    "87T": [
        ("Pickup", "Corrente diferencial de partida", "A", "NUMERICO"),
        ("Inclinacao", "Inclinação da característica", "%", "NUMERICO"),
    ],
}

_CATEGORIA_EXTENSAO = {
    ".cid": "DIGSI", ".apc": "DIGSI", ".pfd": "DIGSI",
    ".scd": "SCL", ".ssd": "SCL", ".xml": "SCL",
    ".zip": "PARAMETROS", ".eft": "PARAMETROS",
    ".cfg": "COMTRADE", ".dat": "COMTRADE", ".cff": "COMTRADE", ".hdr": "COMTRADE",
    ".rep": "OSCILOGRAFIA",
    ".pdf": "DOCUMENTO", ".docx": "DOCUMENTO", ".xlsx": "DOCUMENTO", ".rtf": "DOCUMENTO",
}


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


def _categoria_por_extensao(extensao: str) -> str:
    return _CATEGORIA_EXTENSAO.get(extensao, "OUTRO")


def garantir_catalogo_funcoes_ansi(db: Session) -> None:
    usuario = db.query(Usuario).order_by(Usuario.id).first()
    if not usuario:
        return
    try:
        for codigo, nome, categoria in CATALOGO_ANSI:
            existe = db.query(models.FuncaoANSI.id_funcao_ansi).filter(models.FuncaoANSI.codigo == codigo).first()
            if not existe:
                db.add(
                    models.FuncaoANSI(
                        codigo=codigo,
                        nome=nome,
                        categoria=categoria,
                        ativo=True,
                        id_usuario_criacao=usuario.id,
                        id_usuario_atualizacao=usuario.id,
                    )
                )
        db.flush()
        for codigo_funcao, itens in SEED_PARAMETROS.items():
            funcao = db.query(models.FuncaoANSI).filter(models.FuncaoANSI.codigo == codigo_funcao).first()
            if not funcao:
                continue
            existentes = {
                linha[0]
                for linha in db.query(models.ParametroDefinicao.codigo)
                .filter(models.ParametroDefinicao.id_funcao_ansi == funcao.id_funcao_ansi)
                .all()
            }
            for codigo, nome, unidade, tipo_dado in itens:
                if codigo in existentes:
                    continue
                db.add(
                    models.ParametroDefinicao(
                        id_funcao_ansi=funcao.id_funcao_ansi,
                        codigo=codigo,
                        nome=nome,
                        unidade=unidade,
                        tipo_dado=tipo_dado,
                        ativo=True,
                        id_usuario_criacao=usuario.id,
                        id_usuario_atualizacao=usuario.id,
                    )
                )
        db.commit()
    except IntegrityError:
        db.rollback()


# --------------------------------------------------------------------------- #
# Consultas auxiliares
# --------------------------------------------------------------------------- #


def _ied(db: Session, id_ied: int) -> models.IED:
    item = db.query(models.IED).filter(models.IED.id_ied == id_ied).first()
    if not item:
        raise HTTPException(status_code=404, detail="IED não encontrado")
    return item


def _funcao_ansi(db: Session, id_funcao_ansi: int) -> models.FuncaoANSI:
    item = db.query(models.FuncaoANSI).filter(models.FuncaoANSI.id_funcao_ansi == id_funcao_ansi).first()
    if not item:
        raise HTTPException(status_code=404, detail="Função ANSI não encontrada")
    return item


def _parametro_definicao(db: Session, id_parametro: int) -> models.ParametroDefinicao:
    item = (
        db.query(models.ParametroDefinicao)
        .filter(models.ParametroDefinicao.id_parametro_definicao == id_parametro)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Parâmetro não encontrado")
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


def _usuario_nome(db: Session, id_usuario: int | None) -> str | None:
    if not id_usuario:
        return None
    usuario = db.query(Usuario).filter(Usuario.id == id_usuario).first()
    return usuario.nome if usuario else None


# --------------------------------------------------------------------------- #
# Construtores de saida
# --------------------------------------------------------------------------- #


def _funcao_out(registro: models.FuncaoANSI, qtd_parametros: int = 0, qtd_ieds: int = 0) -> schemas.FuncaoANSIOut:
    return schemas.FuncaoANSIOut(
        id_funcao_ansi=registro.id_funcao_ansi,
        codigo=registro.codigo,
        nome=registro.nome,
        categoria=registro.categoria,
        descricao=registro.descricao,
        ativo=registro.ativo,
        quantidade_parametros=qtd_parametros,
        quantidade_ieds=qtd_ieds,
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )


def _parametro_out(
    registro: models.ParametroDefinicao, funcao: models.FuncaoANSI | None = None
) -> schemas.ParametroDefinicaoOut:
    funcao = funcao or registro.funcao
    return schemas.ParametroDefinicaoOut(
        id_parametro_definicao=registro.id_parametro_definicao,
        id_funcao_ansi=registro.id_funcao_ansi,
        codigo=registro.codigo,
        nome=registro.nome,
        unidade=registro.unidade,
        tipo_dado=registro.tipo_dado,
        identificador_fabricante=registro.identificador_fabricante,
        valor_minimo=registro.valor_minimo,
        valor_maximo=registro.valor_maximo,
        descricao=registro.descricao,
        ativo=registro.ativo,
        funcao_codigo=funcao.codigo if funcao else None,
        funcao_nome=funcao.nome if funcao else None,
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )


def _ied_funcao_out(registro: models.IEDFuncao, funcao: models.FuncaoANSI | None = None) -> schemas.IEDFuncaoOut:
    funcao = funcao or registro.funcao
    return schemas.IEDFuncaoOut(
        id_ied_funcao=registro.id_ied_funcao,
        id_ied=registro.id_ied,
        id_funcao_ansi=registro.id_funcao_ansi,
        codigo=funcao.codigo if funcao else "",
        nome=funcao.nome if funcao else "",
        categoria=funcao.categoria if funcao else None,
        instancia=registro.instancia,
        habilitada=registro.habilitada,
        observacoes=registro.observacoes,
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )


def _grupo_out(registro: models.IEDGrupoAjuste, qtd: int = 0) -> schemas.IEDGrupoAjusteOut:
    return schemas.IEDGrupoAjusteOut(
        id_ied_grupo_ajuste=registro.id_ied_grupo_ajuste,
        id_ied=registro.id_ied,
        numero=registro.numero,
        nome=registro.nome,
        ativo=registro.ativo,
        descricao=registro.descricao,
        quantidade_parametros=qtd,
        versao=registro.versao,
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )


def _config_parametro_out(
    registro: models.ConfigParametro,
    parametro: models.ParametroDefinicao,
    funcao: models.FuncaoANSI | None,
) -> schemas.ConfigParametroOut:
    return schemas.ConfigParametroOut(
        id_config_parametro=registro.id_config_parametro,
        id_parametro_definicao=registro.id_parametro_definicao,
        id_funcao_ansi=parametro.id_funcao_ansi,
        funcao_codigo=funcao.codigo if funcao else "",
        funcao_nome=funcao.nome if funcao else "",
        codigo=parametro.codigo,
        nome=parametro.nome,
        unidade=parametro.unidade,
        tipo_dado=parametro.tipo_dado,
        valor=registro.valor,
        ajustado_em=registro.ajustado_em,
        observacoes=registro.observacoes,
        atualizado_em=registro.atualizado_em,
    )


def _configuracao_out(db: Session, registro: models.IEDConfiguracao, detalhado: bool = True) -> schemas.ConfiguracaoOut:
    grupo = None
    if registro.id_grupo_ajuste:
        grupo = db.query(models.IEDGrupoAjuste).filter(
            models.IEDGrupoAjuste.id_ied_grupo_ajuste == registro.id_grupo_ajuste
        ).first()

    arquivos: list[schemas.ConfiguracaoArquivoOut] = []
    if detalhado:
        linhas = (
            db.query(models.ConfiguracaoArquivo, models.Arquivo)
            .join(models.Arquivo, models.Arquivo.id_arquivo == models.ConfiguracaoArquivo.id_arquivo)
            .filter(models.ConfiguracaoArquivo.id_ied_configuracao == registro.id_ied_configuracao)
            .order_by(models.ConfiguracaoArquivo.id_configuracao_arquivo)
            .all()
        )
        arquivos = [
            schemas.ConfiguracaoArquivoOut(
                id_configuracao_arquivo=vinculo.id_configuracao_arquivo,
                papel=vinculo.papel,
                arquivo=schemas.ArquivoOut.model_validate(arquivo),
            )
            for vinculo, arquivo in linhas
        ]

    validacoes: list[schemas.ValidacaoOut] = []
    if detalhado:
        linhas_validacao = (
            db.query(models.IEDBackupValidacao, Usuario)
            .outerjoin(Usuario, Usuario.id == models.IEDBackupValidacao.id_usuario_validacao)
            .filter(models.IEDBackupValidacao.id_ied_configuracao == registro.id_ied_configuracao)
            .order_by(models.IEDBackupValidacao.data_validacao.desc(), models.IEDBackupValidacao.id_ied_backup_validacao.desc())
            .all()
        )
        validacoes = [
            schemas.ValidacaoOut(
                id_ied_backup_validacao=validacao.id_ied_backup_validacao,
                resultado=validacao.resultado,
                observacoes=validacao.observacoes,
                id_usuario_validacao=validacao.id_usuario_validacao,
                nome_usuario=usuario.nome if usuario else None,
                data_validacao=validacao.data_validacao,
                criado_em=validacao.criado_em,
            )
            for validacao, usuario in linhas_validacao
        ]

    quantidade_arquivos = (
        db.query(func.count(models.ConfiguracaoArquivo.id_configuracao_arquivo))
        .filter(models.ConfiguracaoArquivo.id_ied_configuracao == registro.id_ied_configuracao)
        .scalar()
        or 0
    )

    return schemas.ConfiguracaoOut(
        id_ied_configuracao=registro.id_ied_configuracao,
        id_ied=registro.id_ied,
        versao=registro.versao,
        rotulo=registro.rotulo,
        motivo=registro.motivo,
        status_validacao=registro.status_validacao,
        versao_digsi=registro.versao_digsi,
        versao_firmware=registro.versao_firmware,
        data_coleta=registro.data_coleta,
        id_grupo_ajuste=registro.id_grupo_ajuste,
        grupo_ajuste_nome=grupo.nome if grupo else None,
        id_os=registro.id_os,
        hash_configuracao=registro.hash_configuracao,
        observacoes=registro.observacoes,
        ativo=registro.ativo,
        id_usuario_coleta=registro.id_usuario_coleta,
        nome_usuario_coleta=_usuario_nome(db, registro.id_usuario_coleta),
        quantidade_arquivos=quantidade_arquivos,
        arquivos=arquivos,
        validacoes=validacoes,
        criado_em=registro.criado_em,
        atualizado_em=registro.atualizado_em,
    )


# --------------------------------------------------------------------------- #
# Catalogo de funcoes ANSI
# --------------------------------------------------------------------------- #


def listar_funcoes_ansi(
    db: Session,
    busca: str | None,
    somente_ativos: bool,
    page: int,
    page_size: int,
) -> schemas.FuncaoANSILista:
    query = db.query(models.FuncaoANSI)
    if somente_ativos:
        query = query.filter(models.FuncaoANSI.ativo.is_(True))
    if busca:
        termo = f"%{busca.strip()}%"
        query = query.filter(
            or_(
                models.FuncaoANSI.codigo.ilike(termo),
                models.FuncaoANSI.nome.ilike(termo),
                models.FuncaoANSI.categoria.ilike(termo),
            )
        )
    total = query.count()
    linhas = query.order_by(models.FuncaoANSI.codigo).offset((page - 1) * page_size).limit(page_size).all()
    ids = [linha.id_funcao_ansi for linha in linhas]
    contagem_parametros: dict[int, int] = {}
    contagem_ieds: dict[int, int] = {}
    if ids:
        contagem_parametros = dict(
            db.query(models.ParametroDefinicao.id_funcao_ansi, func.count(models.ParametroDefinicao.id_parametro_definicao))
            .filter(models.ParametroDefinicao.id_funcao_ansi.in_(ids))
            .group_by(models.ParametroDefinicao.id_funcao_ansi)
            .all()
        )
        contagem_ieds = dict(
            db.query(models.IEDFuncao.id_funcao_ansi, func.count(models.IEDFuncao.id_ied_funcao))
            .filter(models.IEDFuncao.id_funcao_ansi.in_(ids))
            .group_by(models.IEDFuncao.id_funcao_ansi)
            .all()
        )
    itens = [
        _funcao_out(linha, contagem_parametros.get(linha.id_funcao_ansi, 0), contagem_ieds.get(linha.id_funcao_ansi, 0))
        for linha in linhas
    ]
    return schemas.FuncaoANSILista(total=total, page=page, page_size=page_size, items=itens)


def criar_funcao_ansi(db: Session, dados: schemas.FuncaoANSICreate, id_usuario: int) -> schemas.FuncaoANSIOut:
    item = models.FuncaoANSI(
        **dados.model_dump(),
        id_usuario_criacao=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    db.add(item)
    _commit(db, "Já existe uma função ANSI com este código")
    db.refresh(item)
    return _funcao_out(item)


def atualizar_funcao_ansi(
    db: Session, id_funcao_ansi: int, dados: schemas.FuncaoANSIUpdate, id_usuario: int
) -> schemas.FuncaoANSIOut:
    item = _funcao_ansi(db, id_funcao_ansi)
    payload = dados.model_dump(exclude_unset=True)
    if "codigo" in payload and payload["codigo"]:
        payload["codigo"] = payload["codigo"].strip().upper()
    for campo, valor in payload.items():
        setattr(item, campo, valor)
    item.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível atualizar a função ANSI")
    db.refresh(item)
    return _funcao_out(item)


# --------------------------------------------------------------------------- #
# Definicao de parametros
# --------------------------------------------------------------------------- #


def listar_parametros(
    db: Session,
    id_funcao_ansi: int | None,
    busca: str | None,
    somente_ativos: bool,
) -> list[schemas.ParametroDefinicaoOut]:
    query = db.query(models.ParametroDefinicao, models.FuncaoANSI).join(
        models.FuncaoANSI, models.FuncaoANSI.id_funcao_ansi == models.ParametroDefinicao.id_funcao_ansi
    )
    if id_funcao_ansi:
        query = query.filter(models.ParametroDefinicao.id_funcao_ansi == id_funcao_ansi)
    if somente_ativos:
        query = query.filter(models.ParametroDefinicao.ativo.is_(True))
    if busca:
        termo = f"%{busca.strip()}%"
        query = query.filter(
            or_(
                models.ParametroDefinicao.codigo.ilike(termo),
                models.ParametroDefinicao.nome.ilike(termo),
                models.FuncaoANSI.codigo.ilike(termo),
            )
        )
    linhas = query.order_by(models.FuncaoANSI.codigo, models.ParametroDefinicao.codigo).all()
    return [_parametro_out(parametro, funcao) for parametro, funcao in linhas]


def criar_parametro(
    db: Session, id_funcao_ansi: int, dados: schemas.ParametroDefinicaoCreate, id_usuario: int
) -> schemas.ParametroDefinicaoOut:
    funcao = _funcao_ansi(db, id_funcao_ansi)
    item = models.ParametroDefinicao(
        id_funcao_ansi=id_funcao_ansi,
        **dados.model_dump(),
        id_usuario_criacao=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    db.add(item)
    _commit(db, "Já existe um parâmetro com este código nesta função")
    db.refresh(item)
    return _parametro_out(item, funcao)


def atualizar_parametro(
    db: Session, id_parametro: int, dados: schemas.ParametroDefinicaoUpdate, id_usuario: int
) -> schemas.ParametroDefinicaoOut:
    item = _parametro_definicao(db, id_parametro)
    payload = dados.model_dump(exclude_unset=True)
    for campo, valor in payload.items():
        setattr(item, campo, valor)
    item.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível atualizar o parâmetro")
    db.refresh(item)
    return _parametro_out(item)


# --------------------------------------------------------------------------- #
# Funcoes habilitadas por IED
# --------------------------------------------------------------------------- #


def listar_ied_funcoes(db: Session, id_ied: int) -> list[schemas.IEDFuncaoOut]:
    _ied(db, id_ied)
    linhas = (
        db.query(models.IEDFuncao, models.FuncaoANSI)
        .join(models.FuncaoANSI, models.FuncaoANSI.id_funcao_ansi == models.IEDFuncao.id_funcao_ansi)
        .filter(models.IEDFuncao.id_ied == id_ied)
        .order_by(models.FuncaoANSI.codigo, models.IEDFuncao.instancia)
        .all()
    )
    return [_ied_funcao_out(registro, funcao) for registro, funcao in linhas]


def adicionar_ied_funcao(
    db: Session, id_ied: int, dados: schemas.IEDFuncaoCreate, id_usuario: int
) -> schemas.IEDFuncaoOut:
    _ied(db, id_ied)
    funcao = _funcao_ansi(db, dados.id_funcao_ansi)
    if not funcao.ativo:
        raise HTTPException(status_code=400, detail="A função ANSI está inativa")
    item = models.IEDFuncao(
        id_ied=id_ied,
        **dados.model_dump(),
        id_usuario_criacao=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    db.add(item)
    _commit(db, "Esta função já está habilitada nesta instância do IED")
    db.refresh(item)
    return _ied_funcao_out(item, funcao)


def atualizar_ied_funcao(
    db: Session, id_ied: int, id_ied_funcao: int, dados: schemas.IEDFuncaoUpdate, id_usuario: int
) -> schemas.IEDFuncaoOut:
    item = (
        db.query(models.IEDFuncao)
        .filter(models.IEDFuncao.id_ied_funcao == id_ied_funcao, models.IEDFuncao.id_ied == id_ied)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Função do IED não encontrada")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(item, campo, valor)
    item.versao += 1
    item.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível atualizar a função do IED")
    db.refresh(item)
    return _ied_funcao_out(item)


def remover_ied_funcao(db: Session, id_ied: int, id_ied_funcao: int) -> None:
    item = (
        db.query(models.IEDFuncao)
        .filter(models.IEDFuncao.id_ied_funcao == id_ied_funcao, models.IEDFuncao.id_ied == id_ied)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Função do IED não encontrada")
    db.delete(item)
    db.commit()


# --------------------------------------------------------------------------- #
# Grupos de ajuste e parametros configurados
# --------------------------------------------------------------------------- #


def listar_grupos_ajuste(db: Session, id_ied: int) -> list[schemas.IEDGrupoAjusteOut]:
    _ied(db, id_ied)
    linhas = (
        db.query(models.IEDGrupoAjuste)
        .filter(models.IEDGrupoAjuste.id_ied == id_ied)
        .order_by(models.IEDGrupoAjuste.numero)
        .all()
    )
    ids = [linha.id_ied_grupo_ajuste for linha in linhas]
    contagem: dict[int, int] = {}
    if ids:
        contagem = dict(
            db.query(models.ConfigParametro.id_ied_grupo_ajuste, func.count(models.ConfigParametro.id_config_parametro))
            .filter(models.ConfigParametro.id_ied_grupo_ajuste.in_(ids))
            .group_by(models.ConfigParametro.id_ied_grupo_ajuste)
            .all()
        )
    return [_grupo_out(linha, contagem.get(linha.id_ied_grupo_ajuste, 0)) for linha in linhas]


def criar_grupo_ajuste(
    db: Session, id_ied: int, dados: schemas.IEDGrupoAjusteCreate, id_usuario: int
) -> schemas.IEDGrupoAjusteOut:
    _ied(db, id_ied)
    item = models.IEDGrupoAjuste(
        id_ied=id_ied,
        **dados.model_dump(),
        id_usuario_criacao=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    db.add(item)
    _commit(db, "Já existe um grupo de ajuste com este número para o IED")
    db.refresh(item)
    return _grupo_out(item)


def atualizar_grupo_ajuste(
    db: Session, id_ied: int, id_grupo: int, dados: schemas.IEDGrupoAjusteUpdate, id_usuario: int
) -> schemas.IEDGrupoAjusteOut:
    item = _grupo(db, id_grupo)
    if item.id_ied != id_ied:
        raise HTTPException(status_code=404, detail="Grupo de ajuste não pertence ao IED")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(item, campo, valor)
    item.versao += 1
    item.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível atualizar o grupo de ajuste")
    db.refresh(item)
    quantidade = (
        db.query(func.count(models.ConfigParametro.id_config_parametro))
        .filter(models.ConfigParametro.id_ied_grupo_ajuste == id_grupo)
        .scalar()
        or 0
    )
    return _grupo_out(item, quantidade)


def obter_grupo_parametros(db: Session, id_grupo: int) -> schemas.GrupoParametrosOut:
    grupo = _grupo(db, id_grupo)
    linhas = (
        db.query(models.ConfigParametro, models.ParametroDefinicao, models.FuncaoANSI)
        .join(models.ParametroDefinicao, models.ParametroDefinicao.id_parametro_definicao == models.ConfigParametro.id_parametro_definicao)
        .join(models.FuncaoANSI, models.FuncaoANSI.id_funcao_ansi == models.ParametroDefinicao.id_funcao_ansi)
        .filter(models.ConfigParametro.id_ied_grupo_ajuste == id_grupo)
        .order_by(models.FuncaoANSI.codigo, models.ParametroDefinicao.codigo)
        .all()
    )
    itens = [_config_parametro_out(registro, parametro, funcao) for registro, parametro, funcao in linhas]
    return schemas.GrupoParametrosOut(
        grupo=_grupo_out(grupo, len(itens)),
        itens=itens,
    )


def definir_parametros_grupo(
    db: Session, id_grupo: int, dados: schemas.ConfigParametroLote, id_usuario: int
) -> schemas.GrupoParametrosOut:
    grupo = _grupo(db, id_grupo)
    atuais = {
        registro.id_parametro_definicao: registro
        for registro in db.query(models.ConfigParametro)
        .filter(models.ConfigParametro.id_ied_grupo_ajuste == id_grupo)
        .all()
    }
    for item in dados.parametros:
        parametro = _parametro_definicao(db, item.id_parametro_definicao)
        registro = atuais.get(item.id_parametro_definicao)
        if registro is None:
            registro = models.ConfigParametro(
                id_ied_grupo_ajuste=id_grupo,
                id_parametro_definicao=parametro.id_parametro_definicao,
                valor=item.valor.strip(),
                ajustado_em=item.ajustado_em,
                observacoes=_texto(item.observacoes),
                id_usuario_criacao=id_usuario,
                id_usuario_atualizacao=id_usuario,
            )
            db.add(registro)
            atuais[item.id_parametro_definicao] = registro
        else:
            registro.valor = item.valor.strip()
            registro.ajustado_em = item.ajustado_em
            registro.observacoes = _texto(item.observacoes)
            registro.versao += 1
            registro.id_usuario_atualizacao = id_usuario
    grupo.versao += 1
    grupo.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível salvar os parâmetros do grupo")
    return obter_grupo_parametros(db, id_grupo)


# --------------------------------------------------------------------------- #
# Configuracoes / backups
# --------------------------------------------------------------------------- #


def listar_configuracoes(
    db: Session, id_ied: int, page: int, page_size: int
) -> schemas.ConfiguracaoLista:
    _ied(db, id_ied)
    query = db.query(models.IEDConfiguracao).filter(models.IEDConfiguracao.id_ied == id_ied)
    total = query.count()
    linhas = (
        query.order_by(models.IEDConfiguracao.versao.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    itens = [_configuracao_out(db, linha, detalhado=False) for linha in linhas]
    return schemas.ConfiguracaoLista(total=total, page=page, page_size=page_size, items=itens)


def obter_configuracao(db: Session, id_configuracao: int) -> schemas.ConfiguracaoOut:
    return _configuracao_out(db, _configuracao(db, id_configuracao), detalhado=True)


def criar_configuracao(
    db: Session, id_ied: int, dados: schemas.ConfiguracaoCreate, id_usuario: int
) -> schemas.ConfiguracaoOut:
    item_ied = _ied(db, id_ied)
    if dados.id_grupo_ajuste:
        grupo = _grupo(db, dados.id_grupo_ajuste)
        if grupo.id_ied != id_ied:
            raise HTTPException(status_code=400, detail="O grupo de ajuste não pertence a este IED")
    if dados.id_os and not db.query(OrdemServico.id_os).filter(OrdemServico.id_os == dados.id_os).first():
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")
    ultima = (
        db.query(func.max(models.IEDConfiguracao.versao))
        .filter(models.IEDConfiguracao.id_ied == id_ied)
        .scalar()
    )
    versao = (ultima or 0) + 1
    item = models.IEDConfiguracao(
        id_ied=id_ied,
        versao=versao,
        rotulo=dados.rotulo.strip(),
        motivo=dados.motivo,
        status_validacao="PENDENTE",
        versao_digsi=_texto(dados.versao_digsi),
        versao_firmware=_texto(dados.versao_firmware) or item_ied.versao_firmware,
        data_coleta=dados.data_coleta,
        id_grupo_ajuste=dados.id_grupo_ajuste,
        id_os=dados.id_os,
        observacoes=_texto(dados.observacoes),
        id_usuario_coleta=id_usuario,
        id_usuario_atualizacao=id_usuario,
    )
    db.add(item)
    _commit(db, "Não foi possível registrar a configuração")
    db.refresh(item)
    return _configuracao_out(db, item, detalhado=True)


def anexar_arquivo(
    db: Session,
    id_configuracao: int,
    conteudo: bytes,
    nome_original: str,
    mime_type: str | None,
    papel: schemas.PapelArquivo,
    categoria: str | None,
    descricao: str | None,
    id_usuario: int,
) -> schemas.ConfiguracaoOut:
    config = _configuracao(db, id_configuracao)
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
    categoria_final = (_texto(categoria) or _categoria_por_extensao(extensao)).upper()
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
            categoria=categoria_final,
            descricao=_texto(descricao),
            id_usuario_upload=id_usuario,
        )
        db.add(arquivo)
        db.flush()
        db.add(
            models.ConfiguracaoArquivo(
                id_ied_configuracao=id_configuracao,
                id_arquivo=arquivo.id_arquivo,
                papel=papel,
            )
        )
        if papel == "PRINCIPAL":
            config.hash_configuracao = sha256
        config.id_usuario_atualizacao = id_usuario
        db.commit()
    except Exception:
        db.rollback()
        destino.unlink(missing_ok=True)
        temporario.unlink(missing_ok=True)
        raise
    return _configuracao_out(db, config, detalhado=True)


def validar_configuracao(
    db: Session, id_configuracao: int, dados: schemas.ValidacaoCreate, id_usuario: int
) -> schemas.ConfiguracaoOut:
    config = _configuracao(db, id_configuracao)
    if not config.hash_configuracao:
        raise HTTPException(
            status_code=400,
            detail="Anexe o arquivo principal (com hash SHA-256) antes de validar o backup",
        )
    db.add(
        models.IEDBackupValidacao(
            id_ied_configuracao=id_configuracao,
            resultado=dados.resultado,
            observacoes=_texto(dados.observacoes),
            id_usuario_validacao=id_usuario,
            data_validacao=dados.data_validacao or date.today(),
        )
    )
    config.status_validacao = "VALIDADA" if dados.resultado == "APROVADO" else "REJEITADA"
    config.id_usuario_atualizacao = id_usuario
    _commit(db, "Não foi possível registrar a validação do backup")
    db.refresh(config)
    return _configuracao_out(db, config, detalhado=True)


def _arquivo_em_uso(db: Session, id_arquivo: int) -> bool:
    """Verifica se o arquivo ainda esta vinculado a qualquer registro do modulo."""
    entidades = (
        models.ConfiguracaoArquivo,
        models.IEDEnsaioArquivo,
        models.IEDOcorrenciaArquivo,
        models.IEDOscilografiaArquivo,
        models.IEDRelatorioArquivo,
    )
    return any(
        db.query(entidade).filter(entidade.id_arquivo == id_arquivo).first() for entidade in entidades
    )


def _remover_arquivo_orfao(db: Session, id_arquivo: int) -> None:
    """Remove o arquivo fisico e o registro quando nao houver mais vinculos."""
    if _arquivo_em_uso(db, id_arquivo):
        return
    arquivo = db.query(models.Arquivo).filter(models.Arquivo.id_arquivo == id_arquivo).first()
    if not arquivo:
        return
    try:
        Path(arquivo.caminho).unlink(missing_ok=True)
    except OSError:
        pass
    db.delete(arquivo)


def remover_arquivo_configuracao(
    db: Session, id_configuracao: int, id_arquivo: int, id_usuario: int
) -> schemas.ConfiguracaoOut:
    """Remove o vinculo de um arquivo com a configuracao e limpa o arquivo orfao."""
    config = _configuracao(db, id_configuracao)
    vinculo = (
        db.query(models.ConfiguracaoArquivo)
        .filter(
            models.ConfiguracaoArquivo.id_ied_configuracao == id_configuracao,
            models.ConfiguracaoArquivo.id_arquivo == id_arquivo,
        )
        .first()
    )
    if not vinculo:
        raise HTTPException(status_code=404, detail="Arquivo nao esta vinculado a esta configuracao")
    papel = vinculo.papel
    db.delete(vinculo)
    db.flush()
    if papel == "PRINCIPAL" and config.hash_configuracao:
        config.hash_configuracao = None
    config.id_usuario_atualizacao = id_usuario
    _remover_arquivo_orfao(db, id_arquivo)
    _commit(db, "Nao foi possivel remover o arquivo da configuracao")
    db.refresh(config)
    return _configuracao_out(db, config, detalhado=True)


def caminho_download(db: Session, id_arquivo: int):
    arquivo = db.query(models.Arquivo).filter(models.Arquivo.id_arquivo == id_arquivo).first()
    if not arquivo:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    caminho = Path(arquivo.caminho).resolve()
    if caminho.parent != PASTA_UPLOADS:
        raise HTTPException(status_code=500, detail="Caminho do arquivo fora da pasta permitida")
    if not caminho.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no armazenamento")
    return arquivo, caminho


def resumo_configuracao(db: Session) -> schemas.ResumoConfiguracaoOut:
    total_funcoes = db.query(func.count(models.FuncaoANSI.id_funcao_ansi)).scalar() or 0
    total_parametros = db.query(func.count(models.ParametroDefinicao.id_parametro_definicao)).scalar() or 0
    total_ied_funcoes = db.query(func.count(models.IEDFuncao.id_ied_funcao)).scalar() or 0
    total_grupos = db.query(func.count(models.IEDGrupoAjuste.id_ied_grupo_ajuste)).scalar() or 0
    total_configuracoes = db.query(func.count(models.IEDConfiguracao.id_ied_configuracao)).scalar() or 0
    aguardando = (
        db.query(func.count(models.IEDConfiguracao.id_ied_configuracao))
        .filter(models.IEDConfiguracao.status_validacao == "PENDENTE")
        .scalar()
        or 0
    )
    ieds_ativos = db.query(func.count(models.IED.id_ied)).filter(models.IED.ativo.is_(True)).scalar() or 0
    ieds_com_config = (
        db.query(func.count(func.distinct(models.IEDConfiguracao.id_ied))).scalar() or 0
    )
    por_motivo = (
        db.query(models.IEDConfiguracao.motivo, func.count(models.IEDConfiguracao.id_ied_configuracao))
        .group_by(models.IEDConfiguracao.motivo)
        .order_by(func.count(models.IEDConfiguracao.id_ied_configuracao).desc())
        .all()
    )
    return schemas.ResumoConfiguracaoOut(
        total_funcoes_ansi=total_funcoes,
        total_parametros_definicao=total_parametros,
        total_ied_funcoes=total_ied_funcoes,
        total_grupos_ajuste=total_grupos,
        total_configuracoes=total_configuracoes,
        aguardando_validacao=aguardando,
        ieds_sem_configuracao=max(0, ieds_ativos - ieds_com_config),
        por_motivo=[schemas.DashboardItem(rotulo=str(rotulo), quantidade=quantidade) for rotulo, quantidade in por_motivo],
    )
