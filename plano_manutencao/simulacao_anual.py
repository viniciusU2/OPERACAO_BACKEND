from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from auth.dependencies import get_current_user
from database import get_db
from models.Ativo import Ativo
from models.OS_models import OrdemServico
from models.plano_manutencao_models import PlanoExecucao, PlanoItem, PlanoManutencao
from OS.ordem_de_servico import delta_periodicidade


router = APIRouter(
    prefix="/planos-manutencao",
    tags=["Simulação anual dos planos de manutenção"],
)

STATUS_CONCLUIDOS = {"CONCLUIDA", "CONCLUÍDA", "ENCERRADA", "FINALIZADA"}
STATUS_PROJECAO = {"CONCLUIDA", "CRIADA", "A_GERAR", "VENCIDA_NAO_CRIADA"}
MESES = (
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
)


def valor_enum(valor) -> str:
    return str(getattr(valor, "value", valor) or "").strip()


def sem_fuso(valor: datetime | date | None) -> datetime | None:
    if valor is None:
        return None
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return datetime.combine(valor, time(hour=8))
    return valor.replace(tzinfo=None) if valor.tzinfo else valor


def data_referencia_os(ordem: OrdemServico) -> datetime | None:
    return next(
        (
            sem_fuso(valor)
            for valor in (
                ordem.data_inicio_programado,
                ordem.data_fim_programado,
                ordem.data_inicio_execucao,
                ordem.data_fim_execucao,
                ordem.criado_em,
            )
            if valor is not None
        ),
        None,
    )


def descricao_plano(item: PlanoItem | None, id_plano: int) -> str:
    plano = item.plano if item else None
    descricao = (plano.descricao_geral if plano else "") or ""
    return descricao.strip() or f"Plano #{id_plano}"


def nova_ordem_simulada(
    execucao: PlanoExecucao,
    item: PlanoItem,
    data_execucao: datetime,
) -> dict:
    ativo = execucao.ativo
    subestacao = ativo.subestacao if ativo else None
    plano = item.plano
    return {
        "id_plano_manutencao": item.id_plano_manutencao,
        "plano": descricao_plano(item, item.id_plano_manutencao),
        "id_ativo": execucao.id_ativo,
        "ativo": (ativo.codigo_ativo if ativo else "") or f"Ativo #{execucao.id_ativo}",
        "id_subestacao": ativo.id_subestacao if ativo else None,
        "subestacao": (subestacao.nome if subestacao else "") or "Não informada",
        "tipo_ativo": (
            (ativo.tipo_ativo.nome if ativo and ativo.tipo_ativo else None)
            or (plano.tipo_ativo.nome if plano and plano.tipo_ativo else None)
            or "Não informado"
        ),
        "data_prevista": data_execucao,
        "antecedencia": max(item.antecedencia or 0, 0),
        "itens": {},
        "periodicidades": set(),
        "os_existentes": {},
        "ids_execucao": set(),
    }


def adicionar_item(ordem: dict, execucao: PlanoExecucao, item: PlanoItem) -> None:
    ordem["itens"][item.id_plano_item] = {
        "id_plano_item": item.id_plano_item,
        "nome_item": item.nome_item or f"Item #{item.id_plano_item}",
        "periodicidade": valor_enum(item.periodicidade),
        "intervalo": max(item.intervalo or 1, 1),
    }
    ordem["periodicidades"].add(valor_enum(item.periodicidade))
    ordem["antecedencia"] = max(ordem["antecedencia"], max(item.antecedencia or 0, 0))
    ordem["ids_execucao"].add(execucao.id_execucao)
    if execucao.id_os:
        ordem["os_existentes"].setdefault(execucao.id_os, None)


def adicionar_os_existente(ordem: dict, os: OrdemServico) -> None:
    ordem["os_existentes"][os.id_os] = {
        "id_os": os.id_os,
        "numero_os": os.numero_os,
        "status": (os.status or "ABERTA").upper(),
    }


def serializar_ordem(ordem: dict, hoje: date) -> dict:
    data_prevista = ordem["data_prevista"]
    data_liberacao = data_prevista - timedelta(days=ordem["antecedencia"])
    os_existentes = [valor for valor in ordem["os_existentes"].values() if valor]
    statuses = {os["status"] for os in os_existentes}

    if os_existentes and statuses and statuses.issubset(STATUS_CONCLUIDOS):
        status_projecao = "CONCLUIDA"
    elif os_existentes:
        status_projecao = "CRIADA"
    elif data_liberacao.date() <= hoje:
        status_projecao = "VENCIDA_NAO_CRIADA"
    else:
        status_projecao = "A_GERAR"

    return {
        "id_plano_manutencao": ordem["id_plano_manutencao"],
        "plano": ordem["plano"],
        "id_ativo": ordem["id_ativo"],
        "ativo": ordem["ativo"],
        "id_subestacao": ordem["id_subestacao"],
        "subestacao": ordem["subestacao"],
        "tipo_ativo": ordem["tipo_ativo"],
        "data_prevista": data_prevista.isoformat(),
        "data_liberacao": data_liberacao.isoformat(),
        "mes": data_prevista.month,
        "antecedencia": ordem["antecedencia"],
        "quantidade_itens": len(ordem["itens"]),
        "itens": sorted(ordem["itens"].values(), key=lambda item: item["nome_item"]),
        "periodicidades": sorted(ordem["periodicidades"]),
        "status_projecao": status_projecao,
        "os_existentes": sorted(os_existentes, key=lambda os: os["numero_os"] or ""),
    }


@router.get("/simulacao-anual")
def simular_plano_anual(
    ano: int = Query(default_factory=lambda: datetime.now().year, ge=2000, le=2100),
    id_plano_manutencao: int | None = Query(default=None, gt=0),
    id_subestacao: int | None = Query(default=None, gt=0),
    periodicidade: str | None = None,
    status: str | None = None,
    busca: str | None = None,
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=50, ge=10, le=200),
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    """Projeta as OS do ano sem inserir ou alterar registros no banco."""
    periodicidade_normalizada = (periodicidade or "").strip().upper() or None
    status_normalizado = (status or "").strip().upper() or None
    busca_normalizada = (busca or "").strip().casefold()
    if status_normalizado and status_normalizado not in STATUS_PROJECAO:
        raise HTTPException(status_code=422, detail="Status de projeção inválido")

    inicio_ano = datetime(ano, 1, 1)
    fim_ano = datetime(ano, 12, 31, 23, 59, 59)
    hoje = datetime.now().date()

    execucoes = (
        db.query(PlanoExecucao)
        .join(PlanoItem, PlanoItem.id_plano_item == PlanoExecucao.id_plano_item)
        .join(Ativo, Ativo.id_ativo == PlanoExecucao.id_ativo)
        .options(
            joinedload(PlanoExecucao.plano_item)
            .joinedload(PlanoItem.plano)
            .joinedload(PlanoManutencao.tipo_ativo),
            joinedload(PlanoExecucao.ativo).joinedload(Ativo.subestacao),
            joinedload(PlanoExecucao.ativo).joinedload(Ativo.tipo_ativo),
        )
        .all()
    )

    opcoes_planos: dict[int, str] = {}
    opcoes_subestacoes: dict[int, str] = {}
    opcoes_periodicidades: set[str] = set()
    ordens: dict[tuple[int, int, date], dict] = {}
    ordens_por_id_os: defaultdict[int, list[dict]] = defaultdict(list)

    for execucao in execucoes:
        item = execucao.plano_item
        ativo = execucao.ativo
        if not item or not item.plano or not ativo:
            continue

        id_plano = item.id_plano_manutencao
        opcoes_planos[id_plano] = descricao_plano(item, id_plano)
        if ativo.subestacao:
            opcoes_subestacoes[ativo.id_subestacao] = ativo.subestacao.nome
        periodicidade_item = valor_enum(item.periodicidade).upper()
        opcoes_periodicidades.add(periodicidade_item)

        if id_plano_manutencao and id_plano != id_plano_manutencao:
            continue
        if id_subestacao and ativo.id_subestacao != id_subestacao:
            continue
        if periodicidade_normalizada and periodicidade_item != periodicidade_normalizada:
            continue

        ocorrencia = sem_fuso(execucao.proxima_execucao)
        if ocorrencia is None:
            ocorrencia = sem_fuso(item.data_inicio)
        if ocorrencia is None:
            continue

        delta = delta_periodicidade(item.periodicidade, item.intervalo)
        limite_seguranca = 0
        while ocorrencia < inicio_ano and limite_seguranca < 1000:
            ocorrencia += delta
            limite_seguranca += 1

        while ocorrencia <= fim_ano and limite_seguranca < 1400:
            chave = (id_plano, execucao.id_ativo, ocorrencia.date())
            ordem = ordens.get(chave)
            if ordem is None:
                ordem = nova_ordem_simulada(execucao, item, ocorrencia)
                ordens[chave] = ordem
            adicionar_item(ordem, execucao, item)
            if execucao.id_os:
                ordens_por_id_os[execucao.id_os].append(ordem)
            ocorrencia += delta
            limite_seguranca += 1

    consulta_os = db.query(OrdemServico).filter(OrdemServico.id_plano_manutencao.isnot(None))
    if id_plano_manutencao:
        consulta_os = consulta_os.filter(OrdemServico.id_plano_manutencao == id_plano_manutencao)
    if id_subestacao:
        consulta_os = consulta_os.filter(OrdemServico.id_subestacao == id_subestacao)
    consulta_os = consulta_os.filter(
        or_(
            OrdemServico.id_os.in_(list(ordens_por_id_os)) if ordens_por_id_os else False,
            OrdemServico.data_inicio_programado.between(inicio_ano, fim_ano),
            OrdemServico.data_fim_programado.between(inicio_ano, fim_ano),
            OrdemServico.data_inicio_execucao.between(inicio_ano, fim_ano),
            OrdemServico.data_fim_execucao.between(inicio_ano, fim_ano),
            OrdemServico.criado_em.between(inicio_ano, fim_ano),
        )
    )
    existentes = consulta_os.all()

    for ordem_existente in existentes:
        data_os = data_referencia_os(ordem_existente)
        if not data_os or data_os.year != ano:
            continue

        destinos = ordens_por_id_os.get(ordem_existente.id_os, [])
        if not destinos and ordem_existente.id_ativo:
            chave = (
                ordem_existente.id_plano_manutencao,
                ordem_existente.id_ativo,
                data_os.date(),
            )
            destino = ordens.get(chave)
            if destino:
                destinos = [destino]

        if not destinos:
            ativo = ordem_existente.ativo
            subestacao = ordem_existente.subestacao or (ativo.subestacao if ativo else None)
            id_ativo = ordem_existente.id_ativo or 0
            chave = (ordem_existente.id_plano_manutencao, id_ativo, data_os.date())
            destinos = [
                {
                    "id_plano_manutencao": ordem_existente.id_plano_manutencao,
                    "plano": opcoes_planos.get(
                        ordem_existente.id_plano_manutencao,
                        f"Plano #{ordem_existente.id_plano_manutencao}",
                    ),
                    "id_ativo": id_ativo,
                    "ativo": (ativo.codigo_ativo if ativo else "") or "Ativo não informado",
                    "id_subestacao": ordem_existente.id_subestacao,
                    "subestacao": (subestacao.nome if subestacao else "") or "Não informada",
                    "tipo_ativo": ordem_existente.tipo_ativo or "Não informado",
                    "data_prevista": data_os,
                    "antecedencia": 0,
                    "itens": {},
                    "periodicidades": set(),
                    "os_existentes": {},
                    "ids_execucao": set(),
                }
            ]
            ordens[chave] = destinos[0]

        for destino in destinos:
            adicionar_os_existente(destino, ordem_existente)

    linhas = [serializar_ordem(ordem, hoje) for ordem in ordens.values()]
    if status_normalizado:
        linhas = [linha for linha in linhas if linha["status_projecao"] == status_normalizado]
    if busca_normalizada:
        linhas = [
            linha for linha in linhas
            if busca_normalizada in " ".join(
                (
                    linha["plano"], linha["ativo"], linha["subestacao"],
                    linha["tipo_ativo"],
                    " ".join(item["nome_item"] for item in linha["itens"]),
                    " ".join(os["numero_os"] or "" for os in linha["os_existentes"]),
                )
            ).casefold()
        ]

    linhas.sort(key=lambda linha: (linha["data_prevista"], linha["plano"], linha["ativo"]))
    total = len(linhas)
    total_paginas = max(1, ceil(total / por_pagina))
    pagina = min(pagina, total_paginas)
    inicio = (pagina - 1) * por_pagina
    linhas_pagina = linhas[inicio: inicio + por_pagina]

    contagem_status = Counter(linha["status_projecao"] for linha in linhas)
    planos = defaultdict(lambda: Counter(total=0))
    subestacoes = defaultdict(lambda: Counter(total=0))
    meses = {mes: Counter(total=0) for mes in range(1, 13)}
    ativos = set()
    for linha in linhas:
        status_linha = linha["status_projecao"]
        meses[linha["mes"]]["total"] += 1
        meses[linha["mes"]][status_linha] += 1
        planos[(linha["id_plano_manutencao"], linha["plano"])]["total"] += 1
        planos[(linha["id_plano_manutencao"], linha["plano"])][status_linha] += 1
        subestacoes[(linha["id_subestacao"], linha["subestacao"])]["total"] += 1
        subestacoes[(linha["id_subestacao"], linha["subestacao"])][status_linha] += 1
        ativos.add(linha["id_ativo"])

    def serie_contador(chave, contador: Counter) -> dict:
        return {
            **chave,
            "total": contador["total"],
            "concluidas": contador["CONCLUIDA"],
            "criadas": contador["CRIADA"],
            "a_gerar": contador["A_GERAR"],
            "vencidas_nao_criadas": contador["VENCIDA_NAO_CRIADA"],
        }

    ranking_planos = [
        serie_contador({"id": id_plano, "nome": nome}, contador)
        for (id_plano, nome), contador in planos.items()
    ]
    ranking_planos.sort(key=lambda item: (-item["total"], item["nome"]))
    ranking_subestacoes = [
        serie_contador({"id": id_subestacao_item, "nome": nome}, contador)
        for (id_subestacao_item, nome), contador in subestacoes.items()
    ]
    ranking_subestacoes.sort(key=lambda item: (-item["total"], item["nome"]))

    return {
        "ano": ano,
        "somente_leitura": True,
        "gerado_em": datetime.now().isoformat(),
        "resumo": {
            "total": total,
            "concluidas": contagem_status["CONCLUIDA"],
            "criadas": contagem_status["CRIADA"],
            "a_gerar": contagem_status["A_GERAR"],
            "vencidas_nao_criadas": contagem_status["VENCIDA_NAO_CRIADA"],
            "planos": len(planos),
            "ativos": len(ativos),
        },
        "meses": [
            serie_contador({"mes": mes, "nome": MESES[mes - 1]}, meses[mes])
            for mes in range(1, 13)
        ],
        "ranking_planos": ranking_planos[:12],
        "ranking_subestacoes": ranking_subestacoes,
        "opcoes": {
            "planos": [
                {"id": id_plano, "nome": nome}
                for id_plano, nome in sorted(opcoes_planos.items(), key=lambda item: item[1])
            ],
            "subestacoes": [
                {"id": id_subestacao_item, "nome": nome}
                for id_subestacao_item, nome in sorted(opcoes_subestacoes.items(), key=lambda item: item[1])
            ],
            "periodicidades": sorted(opcoes_periodicidades),
        },
        "paginacao": {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total,
            "total_paginas": total_paginas,
        },
        "ordens": linhas_pagina,
    }
