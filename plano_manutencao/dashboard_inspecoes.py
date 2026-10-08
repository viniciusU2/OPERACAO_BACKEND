from collections import Counter, defaultdict
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from auth.dependencies import get_current_user
from database import get_db
from models.Ativo import Ativo
from models.plano_manutencao_models import Inspecao, ResultadoItemInspecao


router = APIRouter(prefix="/inspecoes", tags=["Dashboard de inspeções"])


def valor_enum(valor):
    return getattr(valor, "value", valor) or "NA"


def status_inspecao(inspecao: Inspecao) -> str:
    return str(valor_enum(inspecao.status_geral)).upper()


def periodicidade_inspecao(inspecao: Inspecao) -> str:
    return str(valor_enum(inspecao.periodicidade))


def nome_instalacao(inspecao: Inspecao) -> str:
    if inspecao.ativo and inspecao.ativo.subestacao:
        return inspecao.ativo.subestacao.nome
    return "Não informada"


def nome_tipo_ativo(inspecao: Inspecao) -> str:
    if inspecao.ativo and inspecao.ativo.tipo_ativo:
        return inspecao.ativo.tipo_ativo.nome
    return "Não informado"


@router.get("/dashboard")
def dashboard_inspecoes(
    data_inicio: date | None = None,
    data_fim: date | None = None,
    instalacao: str | None = None,
    periodicidade: str | None = None,
    status: str | None = None,
    id_tipo_ativo: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(status_code=422, detail="A data inicial não pode ser posterior à data final")

    carregamentos = (
        joinedload(Inspecao.ativo).joinedload(Ativo.subestacao),
        joinedload(Inspecao.ativo).joinedload(Ativo.tipo_ativo),
        joinedload(Inspecao.ordem_servico),
        joinedload(Inspecao.resultados).joinedload(ResultadoItemInspecao.plano_item),
    )

    todas = db.query(Inspecao).options(*carregamentos).all()
    query = db.query(Inspecao).options(*carregamentos)
    if data_inicio:
        query = query.filter(Inspecao.data_inspecao >= datetime.combine(data_inicio, time.min))
    if data_fim:
        query = query.filter(Inspecao.data_inspecao <= datetime.combine(data_fim, time.max))
    if instalacao or id_tipo_ativo is not None:
        query = query.join(Ativo, Ativo.id_ativo == Inspecao.id_ativo)
    if instalacao:
        query = query.filter(Ativo.subestacao.has(nome=instalacao.strip()))
    if periodicidade:
        query = query.filter(Inspecao.periodicidade == periodicidade.strip())
    if status:
        query = query.filter(Inspecao.status_geral == status.strip())
    if id_tipo_ativo is not None:
        query = query.filter(Ativo.id_tipo_ativo == id_tipo_ativo)

    inspecoes = query.order_by(Inspecao.data_inspecao.desc()).all()
    status_contagem = Counter(status_inspecao(inspecao) for inspecao in inspecoes)
    periodicidades = Counter(periodicidade_inspecao(inspecao) for inspecao in inspecoes)

    serie = defaultdict(lambda: {"OK": 0, "NOK": 0, "NA": 0})
    instalacoes = defaultdict(lambda: {"total": 0, "OK": 0, "NOK": 0, "NA": 0})
    tipos_ativo = defaultdict(lambda: {"total": 0, "OK": 0, "NOK": 0, "NA": 0})
    responsaveis = Counter()
    itens_nok = Counter()
    total_itens = 0
    total_itens_nok = 0
    ativos_ids = set()
    vinculadas_os = 0

    for inspecao in inspecoes:
        resultado = status_inspecao(inspecao)
        mes = inspecao.data_inspecao.strftime("%Y-%m") if inspecao.data_inspecao else "Sem data"
        serie[mes][resultado if resultado in {"OK", "NOK", "NA"} else "NA"] += 1

        instalacao_nome = nome_instalacao(inspecao)
        instalacoes[instalacao_nome]["total"] += 1
        instalacoes[instalacao_nome][resultado if resultado in {"OK", "NOK", "NA"} else "NA"] += 1

        tipo_nome = nome_tipo_ativo(inspecao)
        tipos_ativo[tipo_nome]["total"] += 1
        tipos_ativo[tipo_nome][resultado if resultado in {"OK", "NOK", "NA"} else "NA"] += 1

        if inspecao.responsavel and inspecao.responsavel.strip():
            responsaveis[inspecao.responsavel.strip()] += 1
        ativos_ids.add(inspecao.id_ativo)
        if inspecao.id_os:
            vinculadas_os += 1

        for item in inspecao.resultados:
            total_itens += 1
            if str(valor_enum(item.status_item)).upper() == "NOK":
                total_itens_nok += 1
                itens_nok[item.nome_item or "Item não informado"] += 1

    total = len(inspecoes)
    avaliadas = status_contagem["OK"] + status_contagem["NOK"]
    atencao = []
    for inspecao in inspecoes:
        resultado = status_inspecao(inspecao)
        if resultado not in {"NOK", "NA"}:
            continue
        resultados_nok = [
            item.nome_item or "Item não informado"
            for item in inspecao.resultados
            if str(valor_enum(item.status_item)).upper() == "NOK"
        ]
        atencao.append({
            "id_inspecao": inspecao.id_inspecao,
            "id_os": inspecao.id_os,
            "numero_os": inspecao.numero_os,
            "data_inspecao": inspecao.data_inspecao,
            "instalacao": nome_instalacao(inspecao),
            "codigo_ativo": inspecao.codigo_ativo,
            "tipo_ativo": nome_tipo_ativo(inspecao),
            "periodicidade": periodicidade_inspecao(inspecao),
            "status": resultado,
            "responsavel": inspecao.responsavel,
            "observacao": inspecao.observacao_geral,
            "itens_nok": resultados_nok,
            "quantidade_itens_nok": len(resultados_nok),
        })

    tipos_opcoes = {
        inspecao.ativo.id_tipo_ativo: nome_tipo_ativo(inspecao)
        for inspecao in todas
        if inspecao.ativo and inspecao.ativo.id_tipo_ativo
    }

    return {
        "indicadores": {
            "total": total,
            "ok": status_contagem["OK"],
            "nok": status_contagem["NOK"],
            "na": status_contagem["NA"],
            "taxa_conformidade": round((status_contagem["OK"] / avaliadas) * 100, 1) if avaliadas else 0,
            "ativos_inspecionados": len(ativos_ids),
            "itens_avaliados": total_itens,
            "itens_nok": total_itens_nok,
            "taxa_vinculo_os": round((vinculadas_os / total) * 100, 1) if total else 0,
        },
        "serie_mensal": [
            {"mes": mes, **valores}
            for mes, valores in sorted(serie.items())
            if mes != "Sem data"
        ],
        "distribuicao_status": [
            {"status": item, "quantidade": status_contagem[item]}
            for item in ("OK", "NOK", "NA")
        ],
        "distribuicao_periodicidade": [
            {"periodicidade": item, "quantidade": quantidade}
            for item, quantidade in periodicidades.most_common()
        ],
        "ranking_instalacoes": [
            {"instalacao": nome, **valores}
            for nome, valores in sorted(
                instalacoes.items(),
                key=lambda item: (-item[1]["NOK"], -item[1]["total"], item[0]),
            )
        ],
        "ranking_tipos_ativo": [
            {"tipo_ativo": nome, **valores}
            for nome, valores in sorted(
                tipos_ativo.items(),
                key=lambda item: (-item[1]["NOK"], -item[1]["total"], item[0]),
            )[:10]
        ],
        "principais_itens_nok": [
            {"item": item, "quantidade": quantidade}
            for item, quantidade in itens_nok.most_common(10)
        ],
        "ranking_responsaveis": [
            {"responsavel": responsavel, "quantidade": quantidade}
            for responsavel, quantidade in responsaveis.most_common(10)
        ],
        "inspecoes_atencao": atencao[:30],
        "opcoes": {
            "instalacoes": sorted({nome_instalacao(inspecao) for inspecao in todas}),
            "periodicidades": sorted({periodicidade_inspecao(inspecao) for inspecao in todas}),
            "status": ["OK", "NOK", "NA"],
            "tipos_ativo": [
                {"id": tipo_id, "nome": nome}
                for tipo_id, nome in sorted(tipos_opcoes.items(), key=lambda item: item[1])
            ],
        },
        "atualizado_em": datetime.now(),
    }
