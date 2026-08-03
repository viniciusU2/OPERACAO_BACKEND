from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.Ativo import Ativo, GrupoAtivo
from models.fo import FuncaoOperacao
from models.instalacao_models import Subestacao


def garantir_estrutura_grupo_ativo(db: Session):
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS grupo_ativo (
            id_grupo_ativo INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            id_subestacao INT NOT NULL,
            id_funcao_operacao INT NULL,
            id_tipo_ativo INT NOT NULL,
            codigo_ativo VARCHAR(50) NOT NULL,
            bay VARCHAR(50) NULL,
            descricao VARCHAR(300) NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'ATIVO',
            INDEX idx_grupo_ativo_fo (id_funcao_operacao),
            INDEX idx_grupo_ativo_subestacao (id_subestacao)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """))
    for tabela in ("ativo", "ordem_servico", "solicitacao_intervencao", "solicitacao_servico"):
        colunas = {row[0] for row in db.execute(text(f"SHOW COLUMNS FROM {tabela}")).all()}
        if tabela == "ativo" and "id_grupo_ativo" not in colunas:
            db.execute(text("ALTER TABLE ativo ADD COLUMN id_grupo_ativo INT NULL, ADD INDEX idx_ativo_grupo_ativo (id_grupo_ativo)"))
        if tabela != "ativo":
            if "id_grupo_ativo" not in colunas:
                db.execute(text(f"ALTER TABLE {tabela} ADD COLUMN id_grupo_ativo INT NULL, ADD INDEX idx_{tabela}_grupo_ativo (id_grupo_ativo)"))
            if "id_funcao_operacao" not in colunas:
                db.execute(text(f"ALTER TABLE {tabela} ADD COLUMN id_funcao_operacao INT NULL, ADD INDEX idx_{tabela}_funcao_operacao (id_funcao_operacao)"))
            if "escopo_ativo" not in colunas:
                db.execute(text(f"ALTER TABLE {tabela} ADD COLUMN escopo_ativo VARCHAR(10) NULL"))


def sincronizar_grupos_ativos(db: Session):
    garantir_estrutura_grupo_ativo(db)
    ativos = db.query(Ativo).order_by(Ativo.id_ativo).all()
    grupos = {}
    for ativo in ativos:
        # Bay participa da chave quando preenchido; evita unir equipamentos homônimos instalados em bays distintos.
        chave = (ativo.id_subestacao, ativo.id_funcao_operacao, ativo.id_tipo_ativo, (ativo.codigo_ativo or "").strip().upper(), (ativo.bay or "").strip().upper() or None)
        grupo = grupos.get(chave)
        if not grupo:
            grupo = db.query(GrupoAtivo).filter_by(
                id_subestacao=chave[0], id_funcao_operacao=chave[1], id_tipo_ativo=chave[2], codigo_ativo=chave[3], bay=chave[4]
            ).first()
            if not grupo:
                grupo = GrupoAtivo(id_subestacao=chave[0], id_funcao_operacao=chave[1], id_tipo_ativo=chave[2], codigo_ativo=chave[3], bay=chave[4])
                db.add(grupo)
                db.flush()
            grupos[chave] = grupo
        ativo.id_grupo_ativo = grupo.id_grupo_ativo
    db.flush()


def grupos_por_funcao(db: Session, id_funcao_operacao: int):
    fo = db.query(FuncaoOperacao).filter(FuncaoOperacao.id_funcao_operacao == id_funcao_operacao).first()
    if not fo:
        raise HTTPException(404, "Função de transmissão não encontrada")
    sincronizar_grupos_ativos(db)
    grupos = db.query(GrupoAtivo).filter(GrupoAtivo.id_funcao_operacao == id_funcao_operacao, GrupoAtivo.status != "INATIVO").all()
    resultado = []
    for grupo in grupos:
        itens = db.query(Ativo).filter(Ativo.id_grupo_ativo == grupo.id_grupo_ativo).order_by(Ativo.fase, Ativo.id_ativo).all()
        tipo = itens[0].tipo_ativo.nome if itens and itens[0].tipo_ativo else None
        sem_fase = [item for item in itens if not (item.fase or "").strip()]
        resultado.append({
            "id_grupo_ativo": grupo.id_grupo_ativo,
            "chave_grupo": str(grupo.id_grupo_ativo),
            "id_subestacao": grupo.id_subestacao,
            "id_funcao_operacao": grupo.id_funcao_operacao,
            "id_tipo_ativo": grupo.id_tipo_ativo,
            "codigo_ativo": grupo.codigo_ativo,
            "tipo_ativo": tipo,
            "bay": grupo.bay,
            "quantidade_componentes": len(itens),
            "inconsistencia_sem_fase": len(itens) > 1 and len(sem_fase) > 0,
            "fases": [{"id_ativo": item.id_ativo, "fase": item.fase} for item in itens],
        })
    return resultado


def validar_selecao_ativo(db: Session, id_subestacao: int | None, id_funcao_operacao: int | None, id_grupo_ativo: int | None, escopo_ativo: str | None, id_ativo: int | None):
    if not id_grupo_ativo and not escopo_ativo:
        return  # compatibilidade: documento historico com apenas id_ativo
    if escopo_ativo not in {"GRUPO", "FASE"}:
        raise HTTPException(400, "Escopo do ativo deve ser GRUPO ou FASE")
    grupo = db.query(GrupoAtivo).filter(GrupoAtivo.id_grupo_ativo == id_grupo_ativo).first()
    if not grupo:
        raise HTTPException(400, "Grupo de ativo invalido")
    if id_subestacao and grupo.id_subestacao != id_subestacao:
        raise HTTPException(400, "O grupo nao pertence a subestacao selecionada")
    if id_funcao_operacao and grupo.id_funcao_operacao != id_funcao_operacao:
        raise HTTPException(400, "O grupo não pertence à função de transmissão selecionada")
    if escopo_ativo == "GRUPO" and id_ativo:
        raise HTTPException(400, "Selecao por grupo nao deve informar ativo individual")
    if escopo_ativo == "FASE":
        ativo = db.query(Ativo).filter(Ativo.id_ativo == id_ativo, Ativo.id_grupo_ativo == grupo.id_grupo_ativo).first()
        if not ativo:
            raise HTTPException(400, "A fase selecionada nao pertence ao grupo")
    return grupo
