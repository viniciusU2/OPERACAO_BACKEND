# routers/inspecoes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime
from database import get_db
from plano_manutencao.schemas import (

    PlanoManutencaoCreate,
    PlanoManutencaoRead,
    PlanoManutencaoReadFull,
    PlanoItemCreate,
    PlanoItemRead,
    PlanoExecucaoPlanilhaRead,
    PlanoExecucaoUpdate,
    PlanoExecucoesReagendarPlano,
    PlanoExecucoesReagendarPlanoResponse,
 
)


from models.plano_manutencao_models import (
    PlanoManutencao,
    PlanoItem,
    PlanoExecucao
)
from models.Ativo import Ativo


router = APIRouter(prefix="/planos-manutencao", tags=["planos-manutencao"])


# ====================== CRIAR PLANO ======================
@router.post("/", response_model=PlanoManutencaoRead, status_code=201)
def criar_plano(plano_in: PlanoManutencaoCreate, db: Session = Depends(get_db)):

    db_plano = PlanoManutencao(
        id_tipo_ativo=plano_in.id_tipo_ativo,
        descricao_geral=plano_in.descricao_geral,
        materiais_previstos=plano_in.materiais_previstos,
        procedimentos_instrucoes=plano_in.procedimentos_instrucoes,
        requisitos_de_seguranca=plano_in.requisitos_de_seguranca,
        observacao_geral=plano_in.observacao_geral,
    )

    db.add(db_plano)
    db.flush()

    for item in plano_in.itens:
        db.add(PlanoItem(
            id_plano_manutencao=db_plano.id_plano_manutencao,
            **item.model_dump()
        ))

    db.commit()
    db.refresh(db_plano)

    return db_plano


# ====================== LISTAR ======================
@router.get("/", response_model=List[PlanoManutencaoRead])
def listar(db: Session = Depends(get_db)):
    return db.query(PlanoManutencao).all()


def montar_execucao_planilha(execucao: PlanoExecucao):
    item = execucao.plano_item
    ativo = execucao.ativo
    plano = item.plano if item else None
    tipo_ativo = None

    if ativo and ativo.tipo_ativo:
        tipo_ativo = ativo.tipo_ativo.nome
    elif plano and plano.tipo_ativo:
        tipo_ativo = plano.tipo_ativo.nome

    return {
        "id_execucao": execucao.id_execucao,
        "id_plano_item": execucao.id_plano_item,
        "id_plano_manutencao": item.id_plano_manutencao if item else 0,
        "id_ativo": execucao.id_ativo,
        "nome_item": item.nome_item if item else "",
        "periodicidade": item.periodicidade if item else None,
        "intervalo": item.intervalo if item else 1,
        "antecedencia": item.antecedencia if item else 0,
        "plano_descricao": plano.descricao_geral if plano else "",
        "codigo_ativo": ativo.codigo_ativo if ativo else "",
        "instalacao": ativo.subestacao.nome if ativo and ativo.subestacao else None,
        "tipo_ativo": tipo_ativo,
        "bay": ativo.bay if ativo else None,
        "fase": ativo.fase if ativo else None,
        "ultima_execucao": execucao.ultima_execucao,
        "proxima_execucao": execucao.proxima_execucao,
    }


def data_inicial_execucao(item: PlanoItem):
    if item.data_inicio:
        return datetime.combine(item.data_inicio, datetime.min.time())

    return datetime.now()


def sincronizar_execucoes_pendentes(db: Session, plano_id: int | None = None) -> int:
    query_itens = (
        db.query(PlanoItem)
        .join(PlanoItem.plano)
        .options(joinedload(PlanoItem.plano))
    )

    if plano_id is not None:
        query_itens = query_itens.filter(PlanoItem.id_plano_manutencao == plano_id)

    itens = [item for item in query_itens.all() if item.plano]
    if not itens:
        return 0

    tipos_ativo = {item.plano.id_tipo_ativo for item in itens}
    ativos_por_tipo: dict[int, list[int]] = {}
    for id_ativo, id_tipo_ativo in (
        db.query(Ativo.id_ativo, Ativo.id_tipo_ativo)
        .filter(Ativo.id_tipo_ativo.in_(tipos_ativo))
        .all()
    ):
        ativos_por_tipo.setdefault(id_tipo_ativo, []).append(id_ativo)

    ids_itens = [item.id_plano_item for item in itens]
    existentes = set(
        db.query(PlanoExecucao.id_plano_item, PlanoExecucao.id_ativo)
        .filter(PlanoExecucao.id_plano_item.in_(ids_itens))
        .all()
    )

    novas_execucoes = []
    for item in itens:
        for id_ativo in ativos_por_tipo.get(item.plano.id_tipo_ativo, []):
            chave = (item.id_plano_item, id_ativo)
            if chave in existentes:
                continue

            novas_execucoes.append(
                PlanoExecucao(
                    id_plano_item=item.id_plano_item,
                    id_ativo=id_ativo,
                    ultima_execucao=None,
                    proxima_execucao=data_inicial_execucao(item),
                )
            )
            existentes.add(chave)

    if novas_execucoes:
        db.add_all(novas_execucoes)
        db.flush()

    return len(novas_execucoes)


@router.get("/execucoes", response_model=List[PlanoExecucaoPlanilhaRead])
def listar_execucoes(db: Session = Depends(get_db)):
    execucoes = (
        db.query(PlanoExecucao)
        .join(PlanoExecucao.plano_item)
        .join(PlanoExecucao.ativo)
        .options(
            joinedload(PlanoExecucao.plano_item)
            .joinedload(PlanoItem.plano)
            .joinedload(PlanoManutencao.tipo_ativo),
            joinedload(PlanoExecucao.ativo).joinedload(Ativo.tipo_ativo),
            joinedload(PlanoExecucao.ativo).joinedload(Ativo.subestacao),
        )
        .order_by(PlanoExecucao.proxima_execucao, Ativo.codigo_ativo, PlanoItem.ordem)
        .all()
    )

    return [montar_execucao_planilha(execucao) for execucao in execucoes]


@router.post("/execucoes/sincronizar")
def sincronizar_execucoes(db: Session = Depends(get_db)):
    criadas = sincronizar_execucoes_pendentes(db)
    db.commit()

    return {
        "mensagem": "Execucoes sincronizadas com sucesso",
        "total_criadas": criadas,
    }


@router.put("/execucoes/plano/{plano_id}/reagendar", response_model=PlanoExecucoesReagendarPlanoResponse)
def reagendar_execucoes_plano(
    plano_id: int,
    payload: PlanoExecucoesReagendarPlano,
    db: Session = Depends(get_db),
):
    plano = db.query(PlanoManutencao).filter(
        PlanoManutencao.id_plano_manutencao == plano_id
    ).first()

    if not plano:
        raise HTTPException(status_code=404, detail="Plano nao encontrado")

    sincronizar_execucoes_pendentes(db, plano_id=plano_id)

    query_execucoes = (
        db.query(PlanoExecucao)
        .join(PlanoExecucao.plano_item)
        .join(PlanoExecucao.ativo)
        .filter(PlanoItem.id_plano_manutencao == plano_id)
    )

    if payload.id_subestacao:
        query_execucoes = query_execucoes.filter(Ativo.id_subestacao == payload.id_subestacao)

    execucoes = (
        query_execucoes
        .order_by(Ativo.codigo_ativo, PlanoItem.ordem)
        .all()
    )

    for execucao in execucoes:
        execucao.proxima_execucao = payload.proxima_execucao
        if payload.atualizar_ultima_execucao:
            execucao.ultima_execucao = payload.ultima_execucao

    db.commit()

    for execucao in execucoes:
        db.refresh(execucao)

    return {
        "mensagem": "Execucoes do plano reagendadas com sucesso",
        "id_plano_manutencao": plano_id,
        "total_atualizadas": len(execucoes),
        "execucoes": [montar_execucao_planilha(execucao) for execucao in execucoes],
    }


@router.put("/execucoes/{execucao_id}", response_model=PlanoExecucaoPlanilhaRead)
def atualizar_execucao(
    execucao_id: int,
    execucao_in: PlanoExecucaoUpdate,
    db: Session = Depends(get_db)
):
    execucao = db.query(PlanoExecucao).filter(
        PlanoExecucao.id_execucao == execucao_id
    ).first()

    if not execucao:
        raise HTTPException(status_code=404, detail="Execucao nao encontrada")

    execucao.ultima_execucao = execucao_in.ultima_execucao
    execucao.proxima_execucao = execucao_in.proxima_execucao

    db.commit()
    db.refresh(execucao)

    return montar_execucao_planilha(execucao)


# ====================== BUSCAR ======================
@router.get("/{plano_id}", response_model=PlanoManutencaoReadFull)
def buscar(plano_id: int, db: Session = Depends(get_db)):
    plano = db.query(PlanoManutencao).filter(
        PlanoManutencao.id_plano_manutencao == plano_id
    ).first()

    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    return plano


# ====================== ITENS ======================
@router.get("/{plano_id}/itens", response_model=List[PlanoItemRead])
def itens(plano_id: int, db: Session = Depends(get_db)):
    return db.query(PlanoItem)\
        .filter(PlanoItem.id_plano_manutencao == plano_id)\
        .order_by(PlanoItem.ordem)\
        .all()


# ====================== CRIAR ITEM ======================
@router.post("/{plano_id}/itens", response_model=PlanoItemRead, status_code=201)
def criar_item(plano_id: int, item_in: PlanoItemCreate, db: Session = Depends(get_db)):

    plano = db.query(PlanoManutencao).filter(
        PlanoManutencao.id_plano_manutencao == plano_id
    ).first()

    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    db_item = PlanoItem(
        id_plano_manutencao=plano_id,
        **item_in.model_dump()
    )

    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    return db_item


# =========================================================
# ATUALIZAR PLANO (COM ITENS)
# =========================================================
@router.put("/{plano_id}", response_model=PlanoManutencaoRead)
def atualizar_plano(
    plano_id: int,
    plano_in: PlanoManutencaoCreate,
    db: Session = Depends(get_db)
):
    plano = db.query(PlanoManutencao).filter(
        PlanoManutencao.id_plano_manutencao == plano_id
    ).first()

    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    # Atualiza dados do plano
    plano.id_tipo_ativo = plano_in.id_tipo_ativo
    plano.descricao_geral = plano_in.descricao_geral
    plano.materiais_previstos = plano_in.materiais_previstos
    plano.procedimentos_instrucoes = plano_in.procedimentos_instrucoes
    plano.requisitos_de_seguranca = plano_in.requisitos_de_seguranca
    plano.observacao_geral = plano_in.observacao_geral

    # 🔥 Remove itens antigos
    db.query(PlanoItem).filter(
        PlanoItem.id_plano_manutencao == plano_id
    ).delete()

    # 🔥 Recria itens
    for item in plano_in.itens:
        db.add(PlanoItem(
            id_plano_manutencao=plano_id,
            **item.model_dump()
        ))

    db.commit()
    db.refresh(plano)

    return plano
