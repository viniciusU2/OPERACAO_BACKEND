# routers/inspecoes.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, func, or_
from auth.dependencies import get_current_user
from models.familias_models import TipoAtivo
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import date, datetime, time
from database import get_db
from utils.agenda_planos import FUSO_HORARIO_PLANOS, horario_inicio_plano
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
from models.instalacao_models import Subestacao
from models.OS_models import OrdemServico


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
    return horario_inicio_plano(item.data_inicio or datetime.now(FUSO_HORARIO_PLANOS))


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


@router.get("/execucoes/resumo-dashboard")
def resumo_execucoes_dashboard(
    id_subestacao: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    # Uma linha por plano, periodicidade, intervalo e tipo de equipamento.
    # As datas resumem os registros dos ativos, sem presumir conclusao de todo o plano.
    campos = (
        PlanoManutencao.id_plano_manutencao,
        PlanoManutencao.descricao_geral,
        PlanoItem.periodicidade,
        PlanoItem.intervalo,
        TipoAtivo.id_tipo_ativo,
        TipoAtivo.nome,
    )
    query = (
        db.query(
            *campos,
            func.max(PlanoExecucao.ultima_execucao).label("ultima_execucao"),
            func.min(PlanoExecucao.proxima_execucao).label("proxima_execucao"),
            func.count(func.distinct(PlanoExecucao.id_ativo)).label("total_ativos"),
            func.count(func.distinct(case(
                (PlanoExecucao.ultima_execucao.isnot(None), PlanoExecucao.id_ativo),
                else_=None,
            ))).label("ativos_com_execucao"),
        )
        .select_from(PlanoExecucao)
        .join(PlanoItem, PlanoItem.id_plano_item == PlanoExecucao.id_plano_item)
        .join(PlanoManutencao, PlanoManutencao.id_plano_manutencao == PlanoItem.id_plano_manutencao)
        .join(Ativo, Ativo.id_ativo == PlanoExecucao.id_ativo)
        .join(TipoAtivo, TipoAtivo.id_tipo_ativo == Ativo.id_tipo_ativo)
    )
    if id_subestacao is not None:
        query = query.filter(Ativo.id_subestacao == id_subestacao)

    registros = query.group_by(*campos).order_by(
        func.min(PlanoExecucao.proxima_execucao),
        PlanoManutencao.id_plano_manutencao,
        PlanoItem.periodicidade,
        PlanoItem.intervalo,
        TipoAtivo.id_tipo_ativo,
    ).all()
    return [
        {
            "id_plano_manutencao": registro.id_plano_manutencao,
            "plano": registro.descricao_geral,
            "periodicidade": getattr(registro.periodicidade, "value", registro.periodicidade),
            "intervalo": registro.intervalo or 1,
            "id_tipo_ativo": registro.id_tipo_ativo,
            "tipo_ativo": registro.nome,
            "ultima_execucao": registro.ultima_execucao,
            "proxima_execucao": registro.proxima_execucao,
            "total_ativos": registro.total_ativos,
            "ativos_com_execucao": registro.ativos_com_execucao,
        }
        for registro in registros
    ]


STATUS_OS_REALIZADA = ("ENCERRADA", "CONCLUIDA", "CONCLUÍDA", "EXECUTADA", "FINALIZADA")
STATUS_OS_CANCELADA = ("CANCELADA", "CANCELADO")


def _condicao_os_realizada():
    status = func.upper(func.coalesce(OrdemServico.status, ""))
    return and_(
        ~status.in_(STATUS_OS_CANCELADA),
        or_(
            OrdemServico.data_fim_execucao.isnot(None),
            status.in_(STATUS_OS_REALIZADA),
        ),
    )


def _data_referencia_os():
    return func.coalesce(
        OrdemServico.data_fim_execucao,
        OrdemServico.data_inicio_execucao,
        OrdemServico.data_fim_programado,
        OrdemServico.data_inicio_programado,
        OrdemServico.criado_em,
    )


def _filtros_periodo_os(data_inicio: date | None, data_fim: date | None):
    filtros = []
    data_referencia = _data_referencia_os()
    if data_inicio is not None:
        filtros.append(data_referencia >= datetime.combine(data_inicio, time.min))
    if data_fim is not None:
        filtros.append(data_referencia <= datetime.combine(data_fim, time.max))
    return filtros


@router.get("/dashboard")
def dashboard_planos_manutencao(
    data_inicio: date | None = None,
    data_fim: date | None = None,
    id_subestacao: int | None = Query(default=None, gt=0),
    instalacao: str | None = None,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    realizada = _condicao_os_realizada()
    status = func.upper(func.coalesce(OrdemServico.status, ""))
    cancelada = status.in_(STATUS_OS_CANCELADA)
    aberta = and_(~realizada, ~cancelada)
    vencida = and_(
        aberta,
        OrdemServico.data_fim_programado.isnot(None),
        OrdemServico.data_fim_programado < datetime.now(),
    )

    condicoes_os = [
        OrdemServico.id_plano_manutencao == PlanoManutencao.id_plano_manutencao,
        *_filtros_periodo_os(data_inicio, data_fim),
    ]
    if id_subestacao is not None:
        condicoes_os.append(OrdemServico.id_subestacao == id_subestacao)
    if instalacao:
        condicoes_os.append(OrdemServico.instalacao == instalacao.strip())

    registros = (
        db.query(
            PlanoManutencao.id_plano_manutencao,
            PlanoManutencao.descricao_geral,
            TipoAtivo.nome.label("tipo_ativo"),
            func.count(func.distinct(PlanoItem.id_plano_item)).label("total_itens"),
            func.count(func.distinct(OrdemServico.id_os)).label("total_os"),
            func.count(func.distinct(case((realizada, OrdemServico.id_os), else_=None))).label("os_realizadas"),
            func.count(func.distinct(case((aberta, OrdemServico.id_os), else_=None))).label("os_abertas"),
            func.count(func.distinct(case((vencida, OrdemServico.id_os), else_=None))).label("os_vencidas"),
            func.max(case((realizada, _data_referencia_os()), else_=None)).label("ultima_execucao"),
        )
        .select_from(PlanoManutencao)
        .outerjoin(TipoAtivo, TipoAtivo.id_tipo_ativo == PlanoManutencao.id_tipo_ativo)
        .outerjoin(PlanoItem, PlanoItem.id_plano_manutencao == PlanoManutencao.id_plano_manutencao)
        .outerjoin(OrdemServico, and_(*condicoes_os))
        .group_by(
            PlanoManutencao.id_plano_manutencao,
            PlanoManutencao.descricao_geral,
            TipoAtivo.nome,
        )
        .order_by(PlanoManutencao.id_plano_manutencao)
        .all()
    )

    proximas_query = (
        db.query(
            PlanoItem.id_plano_manutencao,
            func.min(PlanoExecucao.proxima_execucao).label("proxima_execucao"),
        )
        .join(PlanoExecucao, PlanoExecucao.id_plano_item == PlanoItem.id_plano_item)
    )
    if id_subestacao is not None or instalacao:
        proximas_query = proximas_query.join(
            Ativo,
            Ativo.id_ativo == PlanoExecucao.id_ativo,
        )
    if id_subestacao is not None:
        proximas_query = proximas_query.filter(Ativo.id_subestacao == id_subestacao)
    if instalacao:
        proximas_query = proximas_query.join(
            Subestacao,
            Subestacao.id_subestacao == Ativo.id_subestacao,
        ).filter(Subestacao.nome == instalacao.strip())
    proximas = {
        item.id_plano_manutencao: item.proxima_execucao
        for item in proximas_query.group_by(PlanoItem.id_plano_manutencao).all()
    }

    instalacoes_query = db.query(
        OrdemServico.id_plano_manutencao,
        OrdemServico.instalacao,
    ).filter(
        OrdemServico.id_plano_manutencao.isnot(None),
        OrdemServico.instalacao.isnot(None),
        OrdemServico.instalacao != "",
        *_filtros_periodo_os(data_inicio, data_fim),
    )
    if id_subestacao is not None:
        instalacoes_query = instalacoes_query.filter(OrdemServico.id_subestacao == id_subestacao)
    instalacoes_por_plano: dict[int, set[str]] = {}
    for plano_id, nome_instalacao in instalacoes_query.distinct().all():
        instalacoes_por_plano.setdefault(plano_id, set()).add(nome_instalacao)

    planos = []
    instalacao_filtrada = instalacao.strip() if instalacao else None
    for registro in registros:
        if id_subestacao is not None and not registro.total_os and registro.id_plano_manutencao not in proximas:
            continue
        total_os = int(registro.total_os or 0)
        realizadas = int(registro.os_realizadas or 0)
        planos.append({
            "id_plano_manutencao": registro.id_plano_manutencao,
            "plano": registro.descricao_geral or f"Plano #{registro.id_plano_manutencao}",
            "tipo_ativo": registro.tipo_ativo or "Tipo não informado",
            "total_itens": int(registro.total_itens or 0),
            "total_os": total_os,
            "os_realizadas": realizadas,
            "os_abertas": int(registro.os_abertas or 0),
            "os_vencidas": int(registro.os_vencidas or 0),
            "taxa_conclusao": round((realizadas / total_os) * 100, 1) if total_os else 0,
            "ultima_execucao": registro.ultima_execucao,
            "proxima_execucao": proximas.get(registro.id_plano_manutencao),
            "instalacoes": (
                (
                    [instalacao_filtrada]
                    if instalacao_filtrada in instalacoes_por_plano.get(registro.id_plano_manutencao, set())
                    else []
                )
                if instalacao_filtrada
                else sorted(instalacoes_por_plano.get(registro.id_plano_manutencao, set()))
            ),
        })

    indicadores = {
        "total_planos": len(planos),
        "planos_com_execucao": sum(1 for plano in planos if plano["os_realizadas"] > 0),
        "os_total": sum(plano["total_os"] for plano in planos),
        "os_realizadas": sum(plano["os_realizadas"] for plano in planos),
        "os_abertas": sum(plano["os_abertas"] for plano in planos),
        "os_vencidas": sum(plano["os_vencidas"] for plano in planos),
    }
    indicadores["taxa_conclusao"] = round(
        (indicadores["os_realizadas"] / indicadores["os_total"]) * 100,
        1,
    ) if indicadores["os_total"] else 0

    return {
        "indicadores": indicadores,
        "planos": planos,
        "instalacoes": sorted({
            instalacao
            for valores in instalacoes_por_plano.values()
            for instalacao in valores
        }),
    }


@router.get("/{plano_id}/ordens-servico-realizadas")
def listar_os_realizadas_plano(
    plano_id: int,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    id_subestacao: int | None = Query(default=None, gt=0),
    instalacao: str | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    plano = db.get(PlanoManutencao, plano_id)
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    filtros_base = [
        OrdemServico.id_plano_manutencao == plano_id,
        *_filtros_periodo_os(data_inicio, data_fim),
    ]
    if id_subestacao is not None:
        filtros_base.append(OrdemServico.id_subestacao == id_subestacao)
    if instalacao:
        filtros_base.append(OrdemServico.instalacao == instalacao.strip())

    realizada = _condicao_os_realizada()
    status_os = func.upper(func.coalesce(OrdemServico.status, ""))
    cancelada = status_os.in_(STATUS_OS_CANCELADA)
    aberta = and_(~realizada, ~cancelada)
    vencida = and_(
        aberta,
        OrdemServico.data_fim_programado.isnot(None),
        OrdemServico.data_fim_programado < datetime.now(),
    )

    filtros_tabela = list(filtros_base)
    status_solicitado = (status or "").strip().upper().replace(" ", "_")
    if status_solicitado == "VENCIDAS":
        filtros_tabela.append(vencida)
    elif status_solicitado == "ABERTAS":
        filtros_tabela.append(aberta)
    elif status_solicitado == "REALIZADAS":
        filtros_tabela.append(realizada)
    elif status_solicitado:
        filtros_tabela.append(status_os == status_solicitado)

    query = db.query(OrdemServico).filter(*filtros_tabela)
    total = query.count()

    data_referencia = _data_referencia_os()
    distribuicao = (
        db.query(
            func.date_format(data_referencia, "%Y-%m").label("mes"),
            func.count(OrdemServico.id_os).label("quantidade"),
        )
        .filter(*filtros_base, realizada)
        .group_by(func.date_format(data_referencia, "%Y-%m"))
        .order_by(func.date_format(data_referencia, "%Y-%m"))
        .all()
    )

    ordens = (
        query.options(
            joinedload(OrdemServico.ativo).joinedload(Ativo.tipo_ativo),
            joinedload(OrdemServico.ativo).joinedload(Ativo.subestacao),
            joinedload(OrdemServico.grupo_ativo),
            joinedload(OrdemServico.subestacao),
        )
        .order_by(
            case((vencida, 1), else_=0).desc(),
            data_referencia.desc(),
            OrdemServico.id_os.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    ids_itens = {ordem.id_plano_item for ordem in ordens if ordem.id_plano_item}
    nomes_itens = {
        item.id_plano_item: item.nome_item
        for item in db.query(PlanoItem).filter(PlanoItem.id_plano_item.in_(ids_itens or [-1])).all()
    }

    itens = []
    for ordem in ordens:
        data_execucao = ordem.data_fim_execucao or ordem.data_inicio_execucao
        duracao_horas = None
        if ordem.data_inicio_execucao and ordem.data_fim_execucao:
            duracao_horas = round(
                max(0, (ordem.data_fim_execucao - ordem.data_inicio_execucao).total_seconds()) / 3600,
                2,
            )
        status_atual = (ordem.status or "").upper()
        ordem_realizada = bool(
            ordem.data_fim_execucao
            or status_atual in STATUS_OS_REALIZADA
        )
        ordem_cancelada = status_atual in STATUS_OS_CANCELADA
        ordem_vencida = bool(
            not ordem_realizada
            and not ordem_cancelada
            and ordem.data_fim_programado
            and ordem.data_fim_programado < datetime.now()
        )
        atraso_dias = 0
        if ordem_vencida and ordem.data_fim_programado:
            atraso_dias = (datetime.now().date() - ordem.data_fim_programado.date()).days
        elif data_execucao and ordem.data_fim_programado and data_execucao > ordem.data_fim_programado:
            atraso_dias = (data_execucao.date() - ordem.data_fim_programado.date()).days

        itens.append({
            "id_os": ordem.id_os,
            "numero_os": ordem.numero_os,
            "status": ordem.status,
            "instalacao": ordem.instalacao or (ordem.subestacao.nome if ordem.subestacao else None),
            "codigo_ativo": ordem.codigo_ativo,
            "tipo_ativo": ordem.tipo_ativo,
            "item_plano": nomes_itens.get(ordem.id_plano_item),
            "data_inicio_programado": ordem.data_inicio_programado,
            "data_fim_programado": ordem.data_fim_programado,
            "data_inicio_execucao": ordem.data_inicio_execucao,
            "data_fim_execucao": ordem.data_fim_execucao,
            "data_execucao": data_execucao,
            "responsavel": ordem.responsavel_manutencao or ordem.responsavel,
            "duracao_horas": duracao_horas,
            "atraso_dias": atraso_dias,
            "vencida": ordem_vencida,
            "origem": ordem.origem,
            "emissor": ordem.emissor,
        })

    return {
        "plano": {
            "id_plano_manutencao": plano.id_plano_manutencao,
            "descricao": plano.descricao_geral or f"Plano #{plano.id_plano_manutencao}",
            "tipo_ativo": plano.tipo_ativo.nome if plano.tipo_ativo else None,
        },
        "items": itens,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "distribuicao_mensal": [
            {"mes": item.mes, "quantidade": int(item.quantidade)}
            for item in distribuicao
            if item.mes
        ],
    }


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
        execucao.proxima_execucao = horario_inicio_plano(payload.proxima_execucao)
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
    execucao.proxima_execucao = horario_inicio_plano(execucao_in.proxima_execucao)

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
