from fastapi import HTTPException
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.Ativo import Ativo
from models.fo import FuncaoOperacao
from models.instalacao_models import Subestacao
from . import schemas


def garantir_estrutura_funcao_operacao(db: Session):
    tabela_fo = db.execute(text("SHOW TABLES LIKE 'funcao_operacao'")).first()
    if tabela_fo:
        colunas_fo = {
            row[0]
            for row in db.execute(text("SHOW COLUMNS FROM funcao_operacao")).fetchall()
        }
        if "id" in colunas_fo and "id_funcao_operacao" not in colunas_fo:
            db.execute(
                text(
                    "ALTER TABLE funcao_operacao "
                    "CHANGE COLUMN id id_funcao_operacao INT NOT NULL AUTO_INCREMENT"
                )
            )

        indice_unico = db.execute(
            text("SHOW INDEX FROM funcao_operacao WHERE Key_name = 'uq_funcao_operacao_subestacao_codigo'")
        ).first()
        if not indice_unico:
            try:
                db.execute(
                    text(
                        "CREATE UNIQUE INDEX uq_funcao_operacao_subestacao_codigo "
                        "ON funcao_operacao (id_subestacao, codigo)"
                    )
                )
            except Exception as exc:
                print("Falha ao criar indice unico de FO:", exc)

    coluna = db.execute(text("SHOW COLUMNS FROM ativo LIKE 'id_funcao_operacao'")).first()
    if not coluna:
        db.execute(text("ALTER TABLE ativo ADD COLUMN id_funcao_operacao INT NULL"))

    indice = db.execute(text("SHOW INDEX FROM ativo WHERE Key_name = 'idx_ativo_funcao_operacao'")).first()
    if not indice:
        db.execute(text("CREATE INDEX idx_ativo_funcao_operacao ON ativo (id_funcao_operacao)"))


def normalizar_codigo(codigo: str) -> str:
    return " ".join((codigo or "").strip().upper().split())


def normalizar_descricao(descricao: str | None) -> str | None:
    if descricao is None:
        return None
    texto = descricao.strip()
    return texto or None


def buscar_subestacao(db: Session, id_subestacao: int) -> Subestacao:
    subestacao = db.query(Subestacao).filter(Subestacao.id_subestacao == id_subestacao).first()
    if not subestacao:
        raise HTTPException(status_code=404, detail="Subestacao nao encontrada")
    return subestacao


def validar_codigo_unico(db: Session, id_subestacao: int, codigo: str, id_funcao_operacao: int | None = None):
    query = db.query(FuncaoOperacao).filter(
        FuncaoOperacao.id_subestacao == id_subestacao,
        FuncaoOperacao.codigo == codigo,
    )
    if id_funcao_operacao is not None:
        query = query.filter(FuncaoOperacao.id_funcao_operacao != id_funcao_operacao)

    if query.first():
        raise HTTPException(status_code=409, detail="Ja existe funcao de operacao com este codigo nesta subestacao")


def montar_saida(db: Session, funcao_operacao: FuncaoOperacao) -> schemas.FuncaoOperacaoOut:
    quantidade_ativos = (
        db.query(func.count(Ativo.id_ativo))
        .filter(Ativo.id_funcao_operacao == funcao_operacao.id_funcao_operacao)
        .scalar()
        or 0
    )
    return schemas.FuncaoOperacaoOut(
        id_funcao_operacao=funcao_operacao.id_funcao_operacao,
        id_subestacao=funcao_operacao.id_subestacao,
        codigo=funcao_operacao.codigo,
        descricao=funcao_operacao.descricao,
        subestacao_nome=funcao_operacao.subestacao.nome if funcao_operacao.subestacao else None,
        quantidade_ativos=quantidade_ativos,
    )


def criar_funcao_operacao(db: Session, dados: schemas.FuncaoOperacaoCreate):
    buscar_subestacao(db, dados.id_subestacao)
    codigo = normalizar_codigo(dados.codigo)
    validar_codigo_unico(db, dados.id_subestacao, codigo)

    funcao_operacao = FuncaoOperacao(
        id_subestacao=dados.id_subestacao,
        codigo=codigo,
        descricao=normalizar_descricao(dados.descricao),
    )
    db.add(funcao_operacao)

    try:
        db.commit()
        db.refresh(funcao_operacao)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ja existe funcao de operacao com este codigo nesta subestacao")

    return montar_saida(db, funcao_operacao)


def listar_funcoes_operacao(db: Session, id_subestacao: int | None = None):
    query = db.query(FuncaoOperacao).join(Subestacao)
    if id_subestacao:
        query = query.filter(FuncaoOperacao.id_subestacao == id_subestacao)

    funcoes = query.order_by(Subestacao.nome, FuncaoOperacao.codigo).all()
    return [montar_saida(db, item) for item in funcoes]


def buscar_funcao_operacao(db: Session, id_funcao_operacao: int) -> FuncaoOperacao:
    funcao_operacao = db.query(FuncaoOperacao).filter(FuncaoOperacao.id_funcao_operacao == id_funcao_operacao).first()
    if not funcao_operacao:
        raise HTTPException(status_code=404, detail="Funcao de operacao nao encontrada")
    return funcao_operacao


def obter_funcao_operacao(db: Session, id_funcao_operacao: int):
    return montar_saida(db, buscar_funcao_operacao(db, id_funcao_operacao))


def atualizar_funcao_operacao(db: Session, id_funcao_operacao: int, dados: schemas.FuncaoOperacaoUpdate):
    funcao_operacao = buscar_funcao_operacao(db, id_funcao_operacao)
    payload = dados.model_dump(exclude_unset=True)

    novo_id_subestacao = payload.get("id_subestacao", funcao_operacao.id_subestacao)
    novo_codigo = normalizar_codigo(payload.get("codigo", funcao_operacao.codigo))

    buscar_subestacao(db, novo_id_subestacao)
    validar_codigo_unico(db, novo_id_subestacao, novo_codigo, id_funcao_operacao)

    if payload.get("id_subestacao") is not None:
        funcao_operacao.id_subestacao = novo_id_subestacao
    if payload.get("codigo") is not None:
        funcao_operacao.codigo = novo_codigo
    if "descricao" in payload:
        funcao_operacao.descricao = normalizar_descricao(payload.get("descricao"))

    try:
        db.commit()
        db.refresh(funcao_operacao)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ja existe funcao de operacao com este codigo nesta subestacao")

    return montar_saida(db, funcao_operacao)


def excluir_funcao_operacao(db: Session, id_funcao_operacao: int):
    funcao_operacao = buscar_funcao_operacao(db, id_funcao_operacao)
    ativos_vinculados = (
        db.query(func.count(Ativo.id_ativo))
        .filter(Ativo.id_funcao_operacao == id_funcao_operacao)
        .scalar()
        or 0
    )
    if ativos_vinculados:
        raise HTTPException(status_code=409, detail="Nao e possivel excluir uma funcao de operacao vinculada a ativos")

    db.delete(funcao_operacao)
    db.commit()
    return {"mensagem": "Funcao de operacao excluida com sucesso"}


def listar_ativos_associados(db: Session, id_funcao_operacao: int):
    buscar_funcao_operacao(db, id_funcao_operacao)
    return db.query(Ativo).filter(Ativo.id_funcao_operacao == id_funcao_operacao).order_by(Ativo.codigo_ativo).all()


def validar_funcao_operacao_do_ativo(db: Session, id_subestacao: int, id_funcao_operacao: int | None):
    if not id_funcao_operacao:
        return

    funcao_operacao = buscar_funcao_operacao(db, id_funcao_operacao)
    if funcao_operacao.id_subestacao != id_subestacao:
        raise HTTPException(status_code=400, detail="A funcao de operacao selecionada nao pertence a subestacao do ativo")

