from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from analytics.schemas import (
    EquipeCapacidadeCreate,
    EquipeCapacidadeRead,
    PlanoPlanejamentoUpdate,
    RecursoCreate,
    RecursoRead,
    RecursoUpdate,
)
from auth.dependencies import require_roles
from database import get_db
from models.Ativo import Ativo
from models.OS_models import OrdemServico
from models.auth_models import Usuario
from models.familias_models import TipoAtivo
from models.instalacao_models import Subestacao
from models.plano_manutencao_models import (
    Inspecao,
    PlanoExecucao,
    PlanoItem,
    PlanoManutencao,
    ResultadoItemInspecao,
)
from models.planning_resource_models import (
    EquipeCapacidade,
    PlanoEquipe,
    PlanoEstimativa,
    PlanoRecurso,
    Recurso,
)
from models.sobreaviso_models import SobreavisoEquipe


router = APIRouter(prefix="/analytics", tags=["Analytics"])
recursos_router = APIRouter(prefix="/recursos", tags=["Recursos de manutencao"])

STATUS_ENCERRADOS = {"ENCERRADA", "ENCERRADO", "CONCLUIDA", "CONCLUIDO", "FINALIZADA", "FINALIZADO"}
STATUS_ABERTOS = {"ABERTA", "ABERTO", "PROGRAMADA", "PROGRAMADO", "EM_EXECUCAO", "EM ANDAMENTO"}


def normalizar(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).upper().replace("_", " ").split())


def enum_valor(valor):
    return getattr(valor, "value", valor)


def dt_inicio(valor: date | None):
    return datetime.combine(valor, time.min) if valor else None


def dt_fim(valor: date | None):
    return datetime.combine(valor, time.max) if valor else None


def os_filtradas(db, data_inicio=None, data_fim=None, id_subestacao=None, id_tipo_ativo=None):
    query = db.query(OrdemServico).options(joinedload(OrdemServico.ativo), joinedload(OrdemServico.grupo_ativo))
    if data_inicio:
        query = query.filter(OrdemServico.criado_em >= dt_inicio(data_inicio))
    if data_fim:
        query = query.filter(OrdemServico.criado_em <= dt_fim(data_fim))
    if id_subestacao:
        query = query.filter(OrdemServico.id_subestacao == id_subestacao)
    if id_tipo_ativo:
        query = query.outerjoin(Ativo, OrdemServico.id_ativo == Ativo.id_ativo).filter(
            or_(Ativo.id_tipo_ativo == id_tipo_ativo, OrdemServico.id_ativo.is_(None))
        )
        query = query.filter(or_(Ativo.id_tipo_ativo == id_tipo_ativo, OrdemServico.grupo_ativo.has(id_tipo_ativo=id_tipo_ativo)))
    return query.all()


def os_encerrada(os):
    return normalizar(os.status) in STATUS_ENCERRADOS


def classe_os(os):
    texto = normalizar(os.esquema_servicos)
    if "CORRET" in texto:
        return "CORRETIVA"
    if "PREDIT" in texto:
        return "PREDITIVA"
    if "PREVENT" in texto:
        return "PREVENTIVA"
    if "MONITOR" in texto:
        return "MONITORAMENTO"
    if "RECOMENDA" in texto:
        return "ATENDIMENTO_RECOMENDACAO"
    return "NAO_CLASSIFICADA"


def evento_chave(execucao):
    item = execucao.plano_item
    return (
        item.id_plano_manutencao,
        execucao.id_ativo,
        execucao.proxima_execucao.date(),
        str(enum_valor(item.periodicidade)),
    )


def carregar_eventos(db, data_inicio, data_fim, id_subestacao=None, id_plano=None, periodicidade=None, id_tipo_ativo=None):
    query = (
        db.query(PlanoExecucao)
        .join(PlanoExecucao.plano_item)
        .join(PlanoExecucao.ativo)
        .options(
            joinedload(PlanoExecucao.plano_item).joinedload(PlanoItem.plano),
            joinedload(PlanoExecucao.ativo).joinedload(Ativo.subestacao),
            joinedload(PlanoExecucao.ativo).joinedload(Ativo.tipo_ativo),
        )
        .filter(PlanoExecucao.proxima_execucao >= dt_inicio(data_inicio), PlanoExecucao.proxima_execucao <= dt_fim(data_fim))
    )
    if id_subestacao:
        query = query.filter(Ativo.id_subestacao == id_subestacao)
    if id_plano:
        query = query.filter(PlanoItem.id_plano_manutencao == id_plano)
    if periodicidade:
        query = query.filter(PlanoItem.periodicidade == periodicidade)
    if id_tipo_ativo:
        query = query.filter(Ativo.id_tipo_ativo == id_tipo_ativo)

    grupos = defaultdict(list)
    for execucao in query.order_by(PlanoExecucao.proxima_execucao).all():
        grupos[evento_chave(execucao)].append(execucao)

    planos_ids = {chave[0] for chave in grupos}
    estimativas = {x.id_plano_manutencao: x for x in db.query(PlanoEstimativa).filter(PlanoEstimativa.id_plano_manutencao.in_(planos_ids or [-1])).all()}
    equipes = defaultdict(list)
    for item in db.query(PlanoEquipe).filter(PlanoEquipe.id_plano_manutencao.in_(planos_ids or [-1])).all():
        equipes[item.id_plano_manutencao].append(item)
    recursos = defaultdict(list)
    for item in db.query(PlanoRecurso).filter(PlanoRecurso.id_plano_manutencao.in_(planos_ids or [-1])).all():
        recursos[item.id_plano_manutencao].append(item)

    eventos = []
    for chave, execucoes in grupos.items():
        id_plano_evt, id_ativo, data_evt, periodicidade_evt = chave
        primeira = execucoes[0]
        ativo = primeira.ativo
        estimativa = estimativas.get(id_plano_evt)
        duracao = float(estimativa.duracao_estimada_horas) if estimativa and estimativa.duracao_estimada_horas is not None else None
        hh = 0.0
        recursos_mao_de_obra = []
        for plano_recurso in recursos[id_plano_evt]:
            recurso = db.get(Recurso, plano_recurso.id_recurso)
            if recurso and recurso.categoria == "MAO_DE_OBRA":
                recursos_mao_de_obra.append(plano_recurso)
        hh_calculavel = bool(recursos_mao_de_obra)
        for plano_recurso in recursos_mao_de_obra:
            horas = plano_recurso.horas_por_recurso or (estimativa.duracao_estimada_horas if estimativa else None)
            if horas is None:
                hh_calculavel = False
            else:
                hh += float(plano_recurso.quantidade) * float(horas)
        eventos.append({
            "event_id": f"{id_plano_evt}:{id_ativo}:{data_evt.isoformat()}:{periodicidade_evt}",
            "id_plano_manutencao": id_plano_evt,
            "id_ativo": id_ativo,
            "codigo_ativo": ativo.codigo_ativo,
            "id_subestacao": ativo.id_subestacao,
            "subestacao": ativo.subestacao.nome if ativo.subestacao else None,
            "id_tipo_ativo": ativo.id_tipo_ativo,
            "tipo_ativo": ativo.tipo_ativo.nome if ativo.tipo_ativo else None,
            "data_programada": data_evt,
            "periodicidade": periodicidade_evt,
            "quantidade_itens": len(execucoes),
            "ids_execucao": [x.id_execucao for x in execucoes],
            "duracao_estimada_horas": duracao,
            "hh_previsto": round(hh, 2) if hh_calculavel else None,
            "ids_equipe": [x.id_equipe for x in sorted(equipes[id_plano_evt], key=lambda y: y.prioridade)],
            "recursos_cadastrados": len(recursos[id_plano_evt]),
        })
    return eventos


@router.get("/filters")
def filtros(db: Session = Depends(get_db)):
    return {
        "subestacoes": [{"id": x.id_subestacao, "nome": x.nome} for x in db.query(Subestacao).order_by(Subestacao.nome).all()],
        "tipos_ativo": [{"id": x.id_tipo_ativo, "nome": x.nome} for x in db.query(TipoAtivo).order_by(TipoAtivo.nome).all()],
        "planos": [{"id": x.id_plano_manutencao, "descricao": x.descricao_geral} for x in db.query(PlanoManutencao).order_by(PlanoManutencao.id_plano_manutencao).all()],
        "periodicidades": ["SEMANAL", "MENSAL", "BIMESTRAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL", "3_ANOS", "5_ANOS", "6_ANOS"],
        "status_os": sorted({str(x[0]) for x in db.query(OrdemServico.status).distinct().all() if x[0]}),
    }


@router.get("/executive-summary")
def resumo_executivo(data_inicio: date | None = None, data_fim: date | None = None, id_subestacao: int | None = None, id_tipo_ativo: int | None = None, db: Session = Depends(get_db)):
    ordens = os_filtradas(db, data_inicio, data_fim, id_subestacao, id_tipo_ativo)
    encerradas = [x for x in ordens if os_encerrada(x)]
    backlog = [x for x in ordens if not os_encerrada(x)]
    avaliaveis = [x for x in encerradas if x.data_fim_programado and x.data_fim_execucao]
    no_prazo = [x for x in avaliaveis if x.data_fim_execucao <= x.data_fim_programado]
    return {
        "total_os": len(ordens),
        "encerradas": len(encerradas),
        "backlog": len(backlog),
        "atrasadas": sum(1 for x in backlog if x.data_fim_programado and x.data_fim_programado < datetime.now()),
        "cumprimento_prazo_percentual": round(len(no_prazo) / len(avaliaveis) * 100, 1) if avaliaveis else None,
        "cobertura_prazo_percentual": round(len(avaliaveis) / len(encerradas) * 100, 1) if encerradas else None,
        "classes": dict(Counter(classe_os(x) for x in ordens)),
    }


@router.get("/os/timeline")
def timeline_os(data_inicio: date | None = None, data_fim: date | None = None, id_subestacao: int | None = None, id_tipo_ativo: int | None = None, granularidade: str = Query("mes", pattern="^(dia|mes|ano)$"), db: Session = Depends(get_db)):
    ordens = os_filtradas(db, data_inicio, data_fim, id_subestacao, id_tipo_ativo)
    valores = Counter()
    for ordem in ordens:
        data = ordem.criado_em
        if not data:
            continue
        chave = data.date().isoformat() if granularidade == "dia" else (data.strftime("%Y") if granularidade == "ano" else data.strftime("%Y-%m"))
        valores[chave] += 1
    return [{"periodo": chave, "quantidade": valores[chave]} for chave in sorted(valores)]


@router.get("/os/status")
def status_os(data_inicio: date | None = None, data_fim: date | None = None, id_subestacao: int | None = None, id_tipo_ativo: int | None = None, db: Session = Depends(get_db)):
    valores = Counter(normalizar(x.status) or "NAO_INFORMADO" for x in os_filtradas(db, data_inicio, data_fim, id_subestacao, id_tipo_ativo))
    return [{"status": chave, "quantidade": quantidade} for chave, quantidade in valores.most_common()]


@router.get("/os/backlog-aging")
def backlog_aging(id_subestacao: int | None = None, id_tipo_ativo: int | None = None, db: Session = Depends(get_db)):
    hoje = datetime.now()
    faixas = Counter({"0-7": 0, "8-30": 0, "31-60": 0, "61-90": 0, ">90": 0})
    for ordem in os_filtradas(db, None, None, id_subestacao, id_tipo_ativo):
        if os_encerrada(ordem):
            continue
        dias = max(0, (hoje - (ordem.criado_em or hoje)).days)
        faixa = "0-7" if dias <= 7 else "8-30" if dias <= 30 else "31-60" if dias <= 60 else "61-90" if dias <= 90 else ">90"
        faixas[faixa] += 1
    return [{"faixa": faixa, "quantidade": faixas[faixa]} for faixa in ("0-7", "8-30", "31-60", "61-90", ">90")]


@router.get("/os/distribution")
def distribuicao_os(campo: str = Query("subestacao", pattern="^(subestacao|tipo_ativo|classe|emissor|editor)$"), data_inicio: date | None = None, data_fim: date | None = None, id_subestacao: int | None = None, id_tipo_ativo: int | None = None, db: Session = Depends(get_db)):
    valores = Counter()
    for ordem in os_filtradas(db, data_inicio, data_fim, id_subestacao, id_tipo_ativo):
        if campo == "subestacao":
            valor = ordem.subestacao.nome if ordem.subestacao else ordem.instalacao
        elif campo == "tipo_ativo":
            valor = ordem.tipo_ativo
        elif campo == "classe":
            valor = classe_os(ordem)
        elif campo == "emissor":
            valor = ordem.emissor
        else:
            valor = ordem.editado_por
        valores[str(valor or "Nao informado")] += 1
    return [{"categoria": chave, "quantidade": quantidade} for chave, quantidade in valores.most_common()]


@router.get("/inspections/summary")
def resumo_inspecoes(data_inicio: date | None = None, data_fim: date | None = None, id_subestacao: int | None = None, id_tipo_ativo: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Inspecao).join(Inspecao.ativo)
    if data_inicio:
        query = query.filter(Inspecao.data_inspecao >= dt_inicio(data_inicio))
    if data_fim:
        query = query.filter(Inspecao.data_inspecao <= dt_fim(data_fim))
    if id_subestacao:
        query = query.filter(Ativo.id_subestacao == id_subestacao)
    if id_tipo_ativo:
        query = query.filter(Ativo.id_tipo_ativo == id_tipo_ativo)
    inspecoes = query.all()
    ids = [x.id_inspecao for x in inspecoes]
    resultados = db.query(ResultadoItemInspecao).filter(ResultadoItemInspecao.id_inspecao.in_(ids or [-1])).all()
    status = Counter(normalizar(enum_valor(x.status_item)) for x in resultados)
    nok = status.get("NOK", 0)
    avaliados = status.get("OK", 0) + nok
    return {"inspecoes": len(inspecoes), "itens": len(resultados), "status_itens": dict(status), "nok_percentual": round(nok / avaliados * 100, 1) if avaliados else None, "cobertura_avaliada_percentual": round(avaliados / len(resultados) * 100, 1) if resultados else None}


@router.get("/planning/events")
def eventos_planejados(data_inicio: date = Query(default_factory=date.today), data_fim: date = Query(default_factory=lambda: date.today() + timedelta(days=90)), id_subestacao: int | None = None, id_plano: int | None = None, periodicidade: str | None = None, id_tipo_ativo: int | None = None, limite: int = Query(500, ge=1, le=5000), db: Session = Depends(get_db)):
    if data_fim < data_inicio:
        raise HTTPException(422, "data_fim deve ser maior ou igual a data_inicio")
    return carregar_eventos(db, data_inicio, data_fim, id_subestacao, id_plano, periodicidade, id_tipo_ativo)[:limite]


@router.get("/planning/upcoming")
def proximas_execucoes(data_inicio: date = Query(default_factory=date.today), data_fim: date = Query(default_factory=lambda: date.today() + timedelta(days=90)), id_subestacao: int | None = None, id_plano: int | None = None, periodicidade: str | None = None, id_tipo_ativo: int | None = None, db: Session = Depends(get_db)):
    eventos = carregar_eventos(db, data_inicio, data_fim, id_subestacao, id_plano, periodicidade, id_tipo_ativo)
    por_data = Counter(x["data_programada"].isoformat() for x in eventos)
    return {"total_eventos": len(eventos), "total_itens": sum(x["quantidade_itens"] for x in eventos), "serie": [{"data": k, "eventos": por_data[k]} for k in sorted(por_data)]}


@router.get("/planning/workload")
def carga_planejada(data_inicio: date = Query(default_factory=date.today), data_fim: date = Query(default_factory=lambda: date.today() + timedelta(days=90)), id_subestacao: int | None = None, id_plano: int | None = None, periodicidade: str | None = None, id_tipo_ativo: int | None = None, db: Session = Depends(get_db)):
    eventos = carregar_eventos(db, data_inicio, data_fim, id_subestacao, id_plano, periodicidade, id_tipo_ativo)
    grupos = defaultdict(lambda: {"eventos": 0, "hh_previsto": 0.0, "eventos_sem_hh": 0})
    for evento in eventos:
        chave = evento["data_programada"].isoformat()
        grupos[chave]["eventos"] += 1
        if evento["hh_previsto"] is None:
            grupos[chave]["eventos_sem_hh"] += 1
        else:
            grupos[chave]["hh_previsto"] += evento["hh_previsto"]
    return [{"periodo": k, **grupos[k], "hh_previsto": round(grupos[k]["hh_previsto"], 2)} for k in sorted(grupos)]


def demandas_recursos(db, eventos):
    por_plano = defaultdict(int)
    for evento in eventos:
        por_plano[evento["id_plano_manutencao"]] += 1
    linhas = []
    for item, recurso in db.query(PlanoRecurso, Recurso).join(Recurso, PlanoRecurso.id_recurso == Recurso.id_recurso).filter(PlanoRecurso.id_plano_manutencao.in_(por_plano or [-1])).all():
        multiplicador = por_plano[item.id_plano_manutencao]
        demanda = float(item.quantidade) * multiplicador
        linhas.append({"id_recurso": recurso.id_recurso, "recurso": recurso.nome, "categoria": recurso.categoria, "unidade": recurso.unidade, "eventos": multiplicador, "demanda_periodo": round(demanda, 3), "quantidade_disponivel": float(recurso.quantidade_disponivel) if recurso.quantidade_disponivel is not None else None, "controla_disponibilidade": recurso.controla_disponibilidade, "consumivel": item.consumivel})
    return linhas


@router.get("/planning/resources-demand")
def demanda_recursos(data_inicio: date = Query(default_factory=date.today), data_fim: date = Query(default_factory=lambda: date.today() + timedelta(days=90)), id_subestacao: int | None = None, id_plano: int | None = None, periodicidade: str | None = None, id_tipo_ativo: int | None = None, db: Session = Depends(get_db)):
    return demandas_recursos(db, carregar_eventos(db, data_inicio, data_fim, id_subestacao, id_plano, periodicidade, id_tipo_ativo))


@router.get("/planning/conflicts")
def conflitos_planejamento(data_inicio: date = Query(default_factory=date.today), data_fim: date = Query(default_factory=lambda: date.today() + timedelta(days=90)), id_subestacao: int | None = None, id_plano: int | None = None, periodicidade: str | None = None, id_tipo_ativo: int | None = None, db: Session = Depends(get_db)):
    eventos = carregar_eventos(db, data_inicio, data_fim, id_subestacao, id_plano, periodicidade, id_tipo_ativo)
    alertas = []
    for evento in eventos:
        pendencias = []
        if evento["duracao_estimada_horas"] is None:
            pendencias.append("DURACAO")
        if not evento["ids_equipe"]:
            pendencias.append("EQUIPE")
        if not evento["recursos_cadastrados"]:
            pendencias.append("RECURSOS")
        if pendencias:
            alertas.append({"tipo": "DADOS_INSUFICIENTES", "severidade": "ALERTA", "event_id": evento["event_id"], "data": evento["data_programada"], "pendencias": pendencias})
    # Sem horário confiável, disponibilidade reutilizável é comparada no pico diário.
    por_dia_plano = Counter((e["data_programada"], e["id_plano_manutencao"]) for e in eventos)
    demandas = defaultdict(float)
    for (data_evt, plano_id), quantidade_eventos in por_dia_plano.items():
        for item in db.query(PlanoRecurso).filter(PlanoRecurso.id_plano_manutencao == plano_id, PlanoRecurso.consumivel.is_(False)).all():
            demandas[(data_evt, item.id_recurso)] += float(item.quantidade) * quantidade_eventos
    for (data_evt, recurso_id), demanda in demandas.items():
        recurso = db.get(Recurso, recurso_id)
        if recurso and recurso.controla_disponibilidade and recurso.quantidade_disponivel is not None and demanda > float(recurso.quantidade_disponivel):
            alertas.append({"tipo": "RECURSO", "severidade": "CONFLITO", "data": data_evt, "id_recurso": recurso_id, "recurso": recurso.nome, "demanda": round(demanda, 3), "disponivel": float(recurso.quantidade_disponivel), "excesso": round(demanda - float(recurso.quantidade_disponivel), 3)})
    return {"conflitos": sum(1 for x in alertas if x["severidade"] == "CONFLITO"), "alertas": sum(1 for x in alertas if x["severidade"] == "ALERTA"), "itens": alertas}


@router.get("/planning/data-coverage")
def cobertura_planejamento(data_inicio: date = Query(default_factory=date.today), data_fim: date = Query(default_factory=lambda: date.today() + timedelta(days=90)), db: Session = Depends(get_db)):
    eventos = carregar_eventos(db, data_inicio, data_fim)
    total = len(eventos)
    def percentual(qtd): return round(qtd / total * 100, 1) if total else None
    return {"eventos": total, "duracao_percentual": percentual(sum(x["duracao_estimada_horas"] is not None for x in eventos)), "hh_percentual": percentual(sum(x["hh_previsto"] is not None for x in eventos)), "equipe_percentual": percentual(sum(bool(x["ids_equipe"]) for x in eventos)), "recursos_percentual": percentual(sum(x["recursos_cadastrados"] > 0 for x in eventos))}


@router.get("/data-quality")
def qualidade_dados(db: Session = Depends(get_db)):
    return {
        "os_sem_ativo_ou_grupo": db.query(OrdemServico).filter(OrdemServico.id_ativo.is_(None), OrdemServico.id_grupo_ativo.is_(None)).count(),
        "os_sem_subestacao": db.query(OrdemServico).filter(OrdemServico.id_subestacao.is_(None)).count(),
        "os_encerradas_sem_fim": sum(1 for x in db.query(OrdemServico.status, OrdemServico.data_fim_execucao).all() if normalizar(x.status) in STATUS_ENCERRADOS and not x.data_fim_execucao),
        "os_fim_antes_inicio": db.query(OrdemServico).filter(OrdemServico.data_inicio_execucao.isnot(None), OrdemServico.data_fim_execucao.isnot(None), OrdemServico.data_fim_execucao < OrdemServico.data_inicio_execucao).count(),
        "ativos_sem_funcao_operacao": db.query(Ativo).filter(Ativo.id_funcao_operacao.is_(None)).count(),
        "planos_sem_duracao": db.query(PlanoManutencao).outerjoin(PlanoEstimativa, PlanoManutencao.id_plano_manutencao == PlanoEstimativa.id_plano_manutencao).filter(or_(PlanoEstimativa.id_plano_manutencao.is_(None), PlanoEstimativa.duracao_estimada_horas.is_(None))).count(),
        "planos_sem_recursos": db.query(PlanoManutencao).outerjoin(PlanoRecurso, PlanoManutencao.id_plano_manutencao == PlanoRecurso.id_plano_manutencao).filter(PlanoRecurso.id_plano_recurso.is_(None)).count(),
    }


@router.get("/details/{key}")
def detalhes(key: str, limite: int = Query(200, ge=1, le=2000), db: Session = Depends(get_db)):
    query = db.query(OrdemServico)
    if key == "backlog":
        itens = [x for x in query.order_by(OrdemServico.criado_em.desc()).all() if not os_encerrada(x)]
    elif key.startswith("status:"):
        status = normalizar(key.split(":", 1)[1])
        itens = [x for x in query.order_by(OrdemServico.criado_em.desc()).all() if normalizar(x.status) == status]
    else:
        raise HTTPException(404, "Detalhamento nao suportado")
    return [{"id_os": x.id_os, "numero_os": x.numero_os, "status": x.status, "id_subestacao": x.id_subestacao, "id_ativo": x.id_ativo, "criado_em": x.criado_em, "data_fim_programado": x.data_fim_programado} for x in itens[:limite]]


@recursos_router.get("", response_model=list[RecursoRead])
def listar_recursos(categoria: str | None = None, somente_ativos: bool = True, db: Session = Depends(get_db)):
    query = db.query(Recurso)
    if categoria:
        query = query.filter(Recurso.categoria == categoria)
    if somente_ativos:
        query = query.filter(Recurso.ativo.is_(True))
    return query.order_by(Recurso.categoria, Recurso.nome).all()


@recursos_router.post("", response_model=RecursoRead, status_code=201)
def criar_recurso(payload: RecursoCreate, db: Session = Depends(get_db), _usuario: Usuario = Depends(require_roles("admin", "mantenedor"))):
    recurso = Recurso(**payload.model_dump())
    db.add(recurso)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ja existe recurso com esse nome e categoria")
    db.refresh(recurso)
    return recurso


@recursos_router.put("/{id_recurso}", response_model=RecursoRead)
def atualizar_recurso(id_recurso: int, payload: RecursoUpdate, db: Session = Depends(get_db), _usuario: Usuario = Depends(require_roles("admin", "mantenedor"))):
    recurso = db.get(Recurso, id_recurso)
    if not recurso:
        raise HTTPException(404, "Recurso nao encontrado")
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(recurso, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ja existe recurso com esse nome e categoria")
    db.refresh(recurso)
    return recurso


@router.get("/planning/plans/{id_plano}/configuration")
def obter_configuracao_plano(id_plano: int, db: Session = Depends(get_db)):
    if not db.get(PlanoManutencao, id_plano):
        raise HTTPException(404, "Plano nao encontrado")
    estimativa = db.get(PlanoEstimativa, id_plano)
    recursos = db.query(PlanoRecurso, Recurso).join(Recurso).filter(PlanoRecurso.id_plano_manutencao == id_plano).all()
    equipes = db.query(PlanoEquipe, SobreavisoEquipe).join(SobreavisoEquipe, PlanoEquipe.id_equipe == SobreavisoEquipe.id_equipe).filter(PlanoEquipe.id_plano_manutencao == id_plano).all()
    return {"id_plano_manutencao": id_plano, "duracao_estimada_horas": float(estimativa.duracao_estimada_horas) if estimativa and estimativa.duracao_estimada_horas is not None else None, "observacao": estimativa.observacao if estimativa else None, "recursos": [{"id_recurso": r.id_recurso, "nome": recurso.nome, "categoria": recurso.categoria, "quantidade": float(r.quantidade), "horas_por_recurso": float(r.horas_por_recurso) if r.horas_por_recurso is not None else None, "consumivel": r.consumivel, "obrigatorio": r.obrigatorio, "observacao": r.observacao} for r, recurso in recursos], "equipes": [{"id_equipe": e.id_equipe, "nome": equipe.nome, "prioridade": e.prioridade, "observacao": e.observacao} for e, equipe in equipes]}


@router.put("/planning/plans/{id_plano}/configuration")
def salvar_configuracao_plano(id_plano: int, payload: PlanoPlanejamentoUpdate, db: Session = Depends(get_db), _usuario: Usuario = Depends(require_roles("admin", "mantenedor"))):
    if not db.get(PlanoManutencao, id_plano):
        raise HTTPException(404, "Plano nao encontrado")
    if len({x.id_recurso for x in payload.recursos}) != len(payload.recursos):
        raise HTTPException(422, "Recursos duplicados")
    if len({x.id_equipe for x in payload.equipes}) != len(payload.equipes):
        raise HTTPException(422, "Equipes duplicadas")
    ids_recursos = {x.id_recurso for x in payload.recursos}
    ids_equipes = {x.id_equipe for x in payload.equipes}
    if ids_recursos and db.query(Recurso).filter(Recurso.id_recurso.in_(ids_recursos)).count() != len(ids_recursos):
        raise HTTPException(422, "Um ou mais recursos nao existem")
    if ids_equipes and db.query(SobreavisoEquipe).filter(SobreavisoEquipe.id_equipe.in_(ids_equipes)).count() != len(ids_equipes):
        raise HTTPException(422, "Uma ou mais equipes nao existem")
    estimativa = db.get(PlanoEstimativa, id_plano) or PlanoEstimativa(id_plano_manutencao=id_plano)
    estimativa.duracao_estimada_horas = payload.duracao_estimada_horas
    estimativa.observacao = payload.observacao
    db.add(estimativa)
    db.query(PlanoRecurso).filter(PlanoRecurso.id_plano_manutencao == id_plano).delete(synchronize_session=False)
    db.query(PlanoEquipe).filter(PlanoEquipe.id_plano_manutencao == id_plano).delete(synchronize_session=False)
    db.add_all([PlanoRecurso(id_plano_manutencao=id_plano, **x.model_dump()) for x in payload.recursos])
    db.add_all([PlanoEquipe(id_plano_manutencao=id_plano, **x.model_dump()) for x in payload.equipes])
    db.commit()
    return obter_configuracao_plano(id_plano, db)


@router.get("/planning/teams/{id_equipe}/capacities", response_model=list[EquipeCapacidadeRead])
def listar_capacidades(id_equipe: int, db: Session = Depends(get_db)):
    return db.query(EquipeCapacidade).filter(EquipeCapacidade.id_equipe == id_equipe).order_by(EquipeCapacidade.data_inicio.desc()).all()


@router.post("/planning/teams/{id_equipe}/capacities", response_model=EquipeCapacidadeRead, status_code=201)
def criar_capacidade(id_equipe: int, payload: EquipeCapacidadeCreate, db: Session = Depends(get_db), _usuario: Usuario = Depends(require_roles("admin", "mantenedor"))):
    if not db.get(SobreavisoEquipe, id_equipe):
        raise HTTPException(404, "Equipe nao encontrada")
    sobreposicao = db.query(EquipeCapacidade).filter(EquipeCapacidade.id_equipe == id_equipe, EquipeCapacidade.data_inicio <= payload.data_fim, EquipeCapacidade.data_fim >= payload.data_inicio).first()
    if sobreposicao:
        raise HTTPException(409, "Ja existe capacidade sobreposta para a equipe")
    item = EquipeCapacidade(id_equipe=id_equipe, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


