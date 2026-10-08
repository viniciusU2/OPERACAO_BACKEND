from collections import Counter, defaultdict
from datetime import date, datetime, time
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from auth.dependencies import get_current_user
from database import get_db
from models.Ativo import Ativo
from models.OS_models import OrdemServico


router = APIRouter(prefix="/os", tags=["Dashboard de manutenção corretiva"])

STATUS_ENCERRADOS = {
    "ENCERRADA",
    "ENCERRADO",
    "CONCLUIDA",
    "CONCLUIDO",
    "FINALIZADA",
    "FINALIZADO",
    "EXECUTADA",
    "EXECUTADO",
}
STATUS_CANCELADOS = {"CANCELADA", "CANCELADO"}


def normalizar(valor: str | None) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    sem_acentos = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    return " ".join(sem_acentos.upper().replace("_", " ").split())


def data_abertura(ordem: OrdemServico):
    return ordem.data_abertura_ss or ordem.criado_em or ordem.data_inicio_programado


def esta_encerrada(ordem: OrdemServico) -> bool:
    return normalizar(ordem.status) in STATUS_ENCERRADOS


def esta_cancelada(ordem: OrdemServico) -> bool:
    return normalizar(ordem.status) in STATUS_CANCELADOS


def rotulo_status(valor: str | None) -> str:
    texto = normalizar(valor)
    if texto in STATUS_ENCERRADOS:
        return "Encerrada"
    if texto in STATUS_CANCELADOS:
        return "Cancelada"
    if texto in {"EM EXECUCAO", "EM ANDAMENTO"}:
        return "Em execução"
    if texto in {"PROGRAMADA", "PROGRAMADO"}:
        return "Programada"
    return "Aberta"


def rotulo_prioridade(valor: str | None) -> str:
    texto = normalizar(valor)
    if not texto:
        return "Não informada"
    if texto.startswith("NIVEL "):
        return texto.title()
    return texto.title()


@router.get("/dashboard-corretivas")
def dashboard_manutencao_corretiva(
    data_inicio: date | None = None,
    data_fim: date | None = None,
    instalacao: str | None = None,
    prioridade: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(status_code=422, detail="A data inicial não pode ser posterior à data final")

    classificacao_corretiva = func.upper(func.coalesce(OrdemServico.esquema_servicos, "")).like("%CORRET%")
    referencia_abertura = func.coalesce(
        OrdemServico.data_abertura_ss,
        OrdemServico.criado_em,
        OrdemServico.data_inicio_programado,
    )

    opcoes_query = db.query(
        OrdemServico.instalacao,
        OrdemServico.prioridade,
        OrdemServico.status,
    ).filter(classificacao_corretiva)
    opcoes = opcoes_query.all()

    query = (
        db.query(OrdemServico)
        .options(
            joinedload(OrdemServico.ativo).joinedload(Ativo.tipo_ativo),
            joinedload(OrdemServico.grupo_ativo),
            joinedload(OrdemServico.subestacao),
        )
        .filter(classificacao_corretiva)
    )
    if data_inicio:
        query = query.filter(referencia_abertura >= datetime.combine(data_inicio, time.min))
    if data_fim:
        query = query.filter(referencia_abertura <= datetime.combine(data_fim, time.max))
    if instalacao:
        query = query.filter(OrdemServico.instalacao == instalacao.strip())
    if prioridade:
        query = query.filter(OrdemServico.prioridade == prioridade.strip())
    if status:
        status_normalizado = normalizar(status)
        if status_normalizado == "ABERTAS":
            query = query.filter(
                ~func.upper(func.coalesce(OrdemServico.status, "")).in_(STATUS_ENCERRADOS | STATUS_CANCELADOS)
            )
        elif status_normalizado == "ENCERRADAS":
            query = query.filter(func.upper(func.coalesce(OrdemServico.status, "")).in_(STATUS_ENCERRADOS))
        elif status_normalizado == "VENCIDAS":
            query = query.filter(
                ~func.upper(func.coalesce(OrdemServico.status, "")).in_(STATUS_ENCERRADOS | STATUS_CANCELADOS),
                OrdemServico.data_fim_programado.isnot(None),
                OrdemServico.data_fim_programado < datetime.now(),
            )
        else:
            query = query.filter(OrdemServico.status == status.strip())

    ordens = query.all()
    agora = datetime.now()
    abertas = [ordem for ordem in ordens if not esta_encerrada(ordem) and not esta_cancelada(ordem)]
    encerradas = [ordem for ordem in ordens if esta_encerrada(ordem)]
    vencidas = [
        ordem
        for ordem in abertas
        if ordem.data_fim_programado and ordem.data_fim_programado < agora
    ]

    tempos_atendimento = []
    for ordem in encerradas:
        inicio = data_abertura(ordem)
        fim = ordem.data_fim_execucao
        if inicio and fim and fim >= inicio:
            tempos_atendimento.append((fim - inicio).total_seconds() / 3600)

    serie = defaultdict(lambda: {"abertas": 0, "encerradas": 0})
    for ordem in ordens:
        abertura = data_abertura(ordem)
        if abertura:
            serie[abertura.strftime("%Y-%m")]["abertas"] += 1
        if ordem.data_fim_execucao:
            serie[ordem.data_fim_execucao.strftime("%Y-%m")]["encerradas"] += 1

    status_contagem = Counter(rotulo_status(ordem.status) for ordem in ordens)
    prioridade_contagem = Counter(rotulo_prioridade(ordem.prioridade) for ordem in ordens)

    instalacoes = defaultdict(lambda: {"total": 0, "encerradas": 0, "abertas": 0, "vencidas": 0})
    ids_vencidas = {ordem.id_os for ordem in vencidas}
    for ordem in ordens:
        nome = ordem.instalacao or "Não informada"
        instalacoes[nome]["total"] += 1
        if esta_encerrada(ordem):
            instalacoes[nome]["encerradas"] += 1
        elif not esta_cancelada(ordem):
            instalacoes[nome]["abertas"] += 1
        if ordem.id_os in ids_vencidas:
            instalacoes[nome]["vencidas"] += 1

    faixas_backlog = Counter()
    for ordem in abertas:
        abertura = data_abertura(ordem)
        idade = max(0, (agora - abertura).days) if abertura else 0
        if idade <= 7:
            faixas_backlog["Até 7 dias"] += 1
        elif idade <= 30:
            faixas_backlog["8 a 30 dias"] += 1
        elif idade <= 90:
            faixas_backlog["31 a 90 dias"] += 1
        else:
            faixas_backlog["Mais de 90 dias"] += 1

    causas = Counter()
    for ordem in ordens:
        causa = " ".join((ordem.causa_primaria or "").split())
        if causa and causa not in {"-", "N/A"}:
            causas[causa] += 1

    def criticidade(ordem: OrdemServico):
        atraso = max(0, (agora - ordem.data_fim_programado).days) if ordem.data_fim_programado else 0
        abertura = data_abertura(ordem)
        idade = max(0, (agora - abertura).days) if abertura else 0
        return (ordem.id_os not in ids_vencidas, -atraso, -idade, ordem.numero_os)

    backlog = []
    for ordem in sorted(abertas, key=criticidade)[:30]:
        abertura = data_abertura(ordem)
        atraso = max(0, (agora - ordem.data_fim_programado).days) if ordem.data_fim_programado else 0
        backlog.append({
            "id_os": ordem.id_os,
            "numero_os": ordem.numero_os,
            "instalacao": ordem.instalacao,
            "codigo_ativo": ordem.codigo_ativo,
            "tipo_ativo": ordem.tipo_ativo,
            "prioridade": ordem.prioridade,
            "status": ordem.status,
            "defeito": ordem.defeito,
            "causa_primaria": ordem.causa_primaria,
            "data_abertura": abertura,
            "data_limite": ordem.data_fim_programado,
            "idade_dias": max(0, (agora - abertura).days) if abertura else 0,
            "atraso_dias": atraso,
            "responsavel": ordem.responsavel_manutencao or ordem.responsavel,
        })

    total = len(ordens)
    return {
        "indicadores": {
            "total": total,
            "encerradas": len(encerradas),
            "abertas": len(abertas),
            "vencidas": len(vencidas),
            "taxa_encerramento": round((len(encerradas) / total) * 100, 1) if total else 0,
            "tempo_medio_atendimento_horas": round(sum(tempos_atendimento) / len(tempos_atendimento), 1) if tempos_atendimento else None,
            "idade_media_backlog_dias": round(
                sum(max(0, (agora - data_abertura(ordem)).days) for ordem in abertas if data_abertura(ordem))
                / len([ordem for ordem in abertas if data_abertura(ordem)]),
                1,
            ) if any(data_abertura(ordem) for ordem in abertas) else None,
        },
        "serie_mensal": [
            {"mes": mes, **valores}
            for mes, valores in sorted(serie.items())
        ],
        "distribuicao_status": [
            {"label": label, "quantidade": quantidade}
            for label, quantidade in status_contagem.most_common()
        ],
        "distribuicao_prioridade": [
            {"label": label, "quantidade": quantidade}
            for label, quantidade in prioridade_contagem.most_common()
        ],
        "ranking_instalacoes": [
            {"instalacao": nome, **valores}
            for nome, valores in sorted(
                instalacoes.items(),
                key=lambda item: (-item[1]["abertas"], -item[1]["total"], item[0]),
            )
        ],
        "faixas_backlog": [
            {"faixa": faixa, "quantidade": faixas_backlog[faixa]}
            for faixa in ("Até 7 dias", "8 a 30 dias", "31 a 90 dias", "Mais de 90 dias")
        ],
        "principais_causas": [
            {"causa": causa, "quantidade": quantidade}
            for causa, quantidade in causas.most_common(8)
        ],
        "backlog": backlog,
        "opcoes": {
            "instalacoes": sorted({valor[0] for valor in opcoes if valor[0]}),
            "prioridades": sorted({valor[1] for valor in opcoes if valor[1]}),
            "status": sorted({valor[2] for valor in opcoes if valor[2]}),
        },
        "atualizado_em": agora,
    }
