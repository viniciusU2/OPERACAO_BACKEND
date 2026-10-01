import html
import math
import os
import re
import shutil
import tempfile
import unicodedata
from collections import Counter
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from starlette.background import BackgroundTask

from database import get_db
from models.Ativo import Ativo, GrupoAtivo
from models.OS_models import OrdemServico
from models.SS_models import SolicitacaoServico
from models.instalacao_models import Subestacao
from models.plano_manutencao_models import PlanoManutencao


router = APIRouter(prefix="/downloads", tags=["Downloads"])

STATUS_FINALIZADOS = {
    "ENCERRADA",
    "ENCERRADO",
    "CONCLUIDA",
    "CONCLUIDO",
    "FINALIZADA",
    "FINALIZADO",
}

AZUL = colors.HexColor("#1D4ED8")
AZUL_ESCURO = colors.HexColor("#0F2A5F")
AZUL_CLARO = colors.HexColor("#EAF2FF")
VERDE = colors.HexColor("#15803D")
VERDE_CLARO = colors.HexColor("#DCFCE7")
AMBAR = colors.HexColor("#B45309")
AMBAR_CLARO = colors.HexColor("#FEF3C7")
VERMELHO = colors.HexColor("#B91C1C")
VERMELHO_CLARO = colors.HexColor("#FEE2E2")
CINZA = colors.HexColor("#475569")
CINZA_CLARO = colors.HexColor("#F8FAFC")
BORDA = colors.HexColor("#CBD5E1")


def normalizar(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    sem_acentos = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(sem_acentos.upper().replace("_", " ").split())


def esta_finalizada(status) -> bool:
    return normalizar(status) in STATUS_FINALIZADOS


def inicio_semana(valor: date) -> date:
    return valor - timedelta(days=valor.weekday())


def intervalo_relatorio(data_inicio: date | None, data_fim: date | None) -> tuple[date, date]:
    hoje = date.today()
    if not data_inicio and not data_fim:
        inicio = inicio_semana(hoje)
        return inicio, inicio + timedelta(days=6)
    if data_inicio and not data_fim:
        return data_inicio, data_inicio + timedelta(days=6)
    if data_fim and not data_inicio:
        return data_fim - timedelta(days=6), data_fim
    if data_fim < data_inicio:
        raise HTTPException(400, "A data final deve ser igual ou posterior a data inicial.")
    if (data_fim - data_inicio).days > 366:
        raise HTTPException(400, "O período do relatório não pode exceder 366 dias.")
    return data_inicio, data_fim


def fmt_data(valor) -> str:
    if not valor:
        return "-"
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    return valor.strftime("%d/%m/%Y")


def texto_seguro(valor) -> str:
    return html.escape(str(valor if valor not in (None, "") else "-"))


def nome_subestacao(id_subestacao, subestacoes: dict[int, str], fallback=None) -> str:
    return subestacoes.get(id_subestacao) or fallback or "Nao informada"


def codigo_ativo(ordem) -> str:
    return ordem.codigo_ativo or "-"


def id_subestacao_ss(ss) -> int | None:
    if ss.ativo:
        return ss.ativo.id_subestacao
    if ss.grupo_ativo:
        return ss.grupo_ativo.id_subestacao
    return None


def codigo_ativo_ss(ss) -> str:
    if ss.ativo:
        return ss.ativo.codigo_ativo
    if ss.grupo_ativo:
        return ss.grupo_ativo.codigo_ativo
    return "-"


def estilos_pdf():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "TituloAuditoria",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=AZUL_ESCURO,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "subtitulo": ParagraphStyle(
            "SubtituloAuditoria",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=CINZA,
            spaceAfter=14,
        ),
        "secao": ParagraphStyle(
            "SecaoAuditoria",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=AZUL_ESCURO,
            spaceBefore=8,
            spaceAfter=8,
        ),
        "normal": ParagraphStyle(
            "NormalAuditoria",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1E293B"),
        ),
        "celula": ParagraphStyle(
            "CelulaAuditoria",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#1E293B"),
        ),
        "cabecalho": ParagraphStyle(
            "CabecalhoTabelaAuditoria",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "card_valor": ParagraphStyle(
            "CardValorAuditoria",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=21,
            alignment=TA_CENTER,
            textColor=AZUL_ESCURO,
        ),
        "card_rotulo": ParagraphStyle(
            "CardRotuloAuditoria",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            alignment=TA_CENTER,
            textColor=CINZA,
        ),
        "nota": ParagraphStyle(
            "NotaAuditoria",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7,
            leading=10,
            textColor=CINZA,
        ),
    }


def tabela_pdf(cabecalhos, linhas, larguras, estilos, alinhamentos=None):
    dados = [[Paragraph(texto_seguro(item), estilos["cabecalho"]) for item in cabecalhos]]
    if linhas:
        dados.extend([
            [Paragraph(texto_seguro(item), estilos["celula"]) for item in linha]
            for linha in linhas
        ])
    else:
        dados.append([
            Paragraph("Nenhum registro encontrado.", estilos["celula"]),
            *[Paragraph("", estilos["celula"]) for _ in cabecalhos[1:]],
        ])

    tabela = Table(dados, colWidths=larguras, repeatRows=1, hAlign="LEFT")
    comandos = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_ESCURO),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDA),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for indice in range(1, len(dados)):
        if indice % 2 == 0:
            comandos.append(("BACKGROUND", (0, indice), (-1, indice), CINZA_CLARO))
    for coluna, alinhamento in (alinhamentos or {}).items():
        comandos.append(("ALIGN", (coluna, 1), (coluna, -1), alinhamento))
    if not linhas:
        comandos.append(("SPAN", (0, 1), (-1, 1)))
        comandos.append(("ALIGN", (0, 1), (-1, 1), "CENTER"))
    tabela.setStyle(TableStyle(comandos))
    return tabela


def cards_resumo(valores, estilos):
    colunas = []
    cores = [AZUL_CLARO, VERDE_CLARO, VERMELHO_CLARO, AMBAR_CLARO]
    for indice, (rotulo, valor) in enumerate(valores):
        card = Table(
            [[Paragraph(str(valor), estilos["card_valor"])], [Paragraph(rotulo, estilos["card_rotulo"])]],
            colWidths=[46 * mm],
            rowHeights=[10 * mm, 9 * mm],
        )
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), cores[indice]),
            ("BOX", (0, 0), (-1, -1), 0.6, BORDA),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        colunas.append(card)
    externa = Table([colunas], colWidths=[48 * mm] * len(colunas), hAlign="LEFT")
    externa.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return externa


def grafico_vencidas_por_subestacao(contagem: Counter, subestacoes: dict[int, str]):
    itens = sorted(contagem.items(), key=lambda item: (-item[1], nome_subestacao(item[0], subestacoes)))[:10]
    if not itens:
        return None

    altura = max(120, min(250, 24 * len(itens)))
    desenho = Drawing(750, altura + 24)
    grafico = HorizontalBarChart()
    grafico.x = 155
    grafico.y = 18
    grafico.width = 540
    grafico.height = altura
    grafico.data = [[quantidade for _, quantidade in itens]]
    grafico.categoryAxis.categoryNames = [
        nome_subestacao(id_subestacao, subestacoes)[:26] for id_subestacao, _ in itens
    ]
    grafico.categoryAxis.labels.fontName = "Helvetica"
    grafico.categoryAxis.labels.fontSize = 7
    grafico.valueAxis.valueMin = 0
    maior = max(quantidade for _, quantidade in itens)
    grafico.valueAxis.valueMax = max(1, maior)
    grafico.valueAxis.valueStep = max(1, math.ceil(maior / 5))
    grafico.valueAxis.labels.fontSize = 7
    grafico.bars[0].fillColor = VERMELHO
    grafico.bars[0].strokeColor = VERMELHO
    desenho.add(grafico)
    return desenho


def gerar_pdf_auditoria(
    caminho: str,
    data_inicio: date,
    data_fim: date,
    referencia: datetime,
    subestacao_filtro: str | None,
    subestacoes: dict[int, str],
    previstas,
    executadas,
    vencidas_os,
    vencidas_ss,
    planos: dict[int, PlanoManutencao],
):
    estilos = estilos_pdf()
    documento = SimpleDocTemplate(
        caminho,
        pagesize=landscape(A4),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=18 * mm,
        bottomMargin=15 * mm,
        title="Auditoria semanal de manutenção",
        author="Sistema de Operação e Manutenção",
    )

    previstas_plano = Counter(os.id_plano_manutencao for os in previstas if os.id_plano_manutencao)
    executadas_plano = Counter(os.id_plano_manutencao for os in executadas if os.id_plano_manutencao)
    previstas_subestacao = Counter(os.id_subestacao for os in previstas)
    executadas_subestacao = Counter(os.id_subestacao for os in executadas)
    vencidas_os_subestacao = Counter(os.id_subestacao for os in vencidas_os)
    vencidas_ss_subestacao = Counter(id_subestacao_ss(ss) for ss in vencidas_ss)

    elementos = []
    logo = os.path.join(os.path.dirname(__file__), "modelos", "logo_rdo.png")
    titulo = [
        Paragraph("AUDITORIA SEMANAL DE MANUTENÇÃO", estilos["titulo"]),
        Paragraph(
            f"Período auditado: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')} | "
            f"Referência de vencimento: {referencia.strftime('%d/%m/%Y %H:%M')} | "
            f"Instalação: {texto_seguro(subestacao_filtro or 'Todas')}",
            estilos["subtitulo"],
        ),
    ]
    if os.path.exists(logo):
        cabecalho = Table([[titulo, Image(logo, width=42 * mm, height=14 * mm)]], colWidths=[150 * mm, 42 * mm])
        cabecalho.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        elementos.append(cabecalho)
    else:
        elementos.extend(titulo)

    elementos.append(cards_resumo([
        ("OS PREVISTAS NO PERÍODO", len(previstas)),
        ("OS EXECUTADAS NO PERÍODO", len(executadas)),
        ("OS VENCIDAS EM ABERTO", len(vencidas_os)),
        ("SS VENCIDAS EM ABERTO", len(vencidas_ss)),
    ], estilos))
    elementos.append(Spacer(1, 5 * mm))

    elementos.append(Paragraph("OS vencidas em aberto por instalação", estilos["secao"]))
    grafico = grafico_vencidas_por_subestacao(vencidas_os_subestacao, subestacoes)
    if grafico:
        elementos.append(grafico)
    else:
        elementos.append(Paragraph("Nenhuma OS vencida e ainda aberta na data de referencia.", estilos["normal"]))

    elementos.append(PageBreak())
    elementos.append(Paragraph("OS previstas por plano", estilos["secao"]))
    ids_planos = sorted(set(previstas_plano) | set(executadas_plano))
    linhas_planos = []
    for id_plano in ids_planos:
        plano = planos.get(id_plano)
        previstas_qtd = previstas_plano[id_plano]
        executadas_qtd = executadas_plano[id_plano]
        cobertura = f"{(executadas_qtd / previstas_qtd * 100):.1f}%" if previstas_qtd else "-"
        linhas_planos.append([
            f"#{id_plano}",
            plano.descricao_geral if plano and plano.descricao_geral else "Sem descricao",
            previstas_qtd,
            executadas_qtd,
            cobertura,
        ])
    elementos.append(tabela_pdf(
        ["Plano", "Descrição", "Previstas", "Executadas", "Execução / previsão"],
        linhas_planos,
        [22 * mm, 112 * mm, 26 * mm, 26 * mm, 34 * mm],
        estilos,
        {2: "CENTER", 3: "CENTER", 4: "CENTER"},
    ))
    sem_plano_previstas = sum(1 for os_item in previstas if not os_item.id_plano_manutencao)
    sem_plano_executadas = sum(1 for os_item in executadas if not os_item.id_plano_manutencao)
    elementos.append(Spacer(1, 3 * mm))
    elementos.append(Paragraph(
        f"OS sem plano vinculado: {sem_plano_previstas} previstas no período e {sem_plano_executadas} executadas.",
        estilos["nota"],
    ))

    elementos.append(Spacer(1, 5 * mm))
    elementos.append(Paragraph("Quantidade de OS por instalação", estilos["secao"]))
    ids_subestacoes = sorted(
        set(previstas_subestacao)
        | set(executadas_subestacao)
        | set(vencidas_os_subestacao)
        | set(vencidas_ss_subestacao),
        key=lambda item: nome_subestacao(item, subestacoes),
    )
    linhas_subestacoes = [[
        nome_subestacao(id_subestacao, subestacoes),
        previstas_subestacao[id_subestacao],
        executadas_subestacao[id_subestacao],
        vencidas_os_subestacao[id_subestacao],
        vencidas_ss_subestacao[id_subestacao],
    ] for id_subestacao in ids_subestacoes]
    elementos.append(tabela_pdf(
        ["Instalação", "OS previstas", "OS executadas", "OS vencidas", "SS vencidas"],
        linhas_subestacoes,
        [75 * mm, 30 * mm, 32 * mm, 30 * mm, 30 * mm],
        estilos,
        {1: "CENTER", 2: "CENTER", 3: "CENTER", 4: "CENTER"},
    ))
    elementos.append(Spacer(1, 4 * mm))
    elementos.append(Paragraph(
        "Critérios: OS executada = status finalizado e data de fim da execução dentro do período; "
        "OS prevista = início programado dentro do período; OS vencida = status não finalizado e fim programado anterior à referência; "
        "SS vencida = status não finalizado e data limite anterior à referência.",
        estilos["nota"],
    ))

    elementos.append(PageBreak())
    elementos.append(Paragraph("OS executadas no período", estilos["secao"]))
    linhas_executadas = [[
        os_item.numero_os,
        nome_subestacao(os_item.id_subestacao, subestacoes, os_item.instalacao),
        codigo_ativo(os_item),
        fmt_data(os_item.data_fim_execucao),
        os_item.status,
        os_item.descricao_servicos,
    ] for os_item in sorted(executadas, key=lambda item: item.data_fim_execucao or datetime.min)]
    elementos.append(tabela_pdf(
        ["OS", "Instalação", "Ativo", "Fim da execução", "Status", "Serviço executado"],
        linhas_executadas,
        [25 * mm, 35 * mm, 38 * mm, 31 * mm, 25 * mm, 103 * mm],
        estilos,
    ))

    elementos.append(PageBreak())
    elementos.append(Paragraph("OS vencidas com data programada e ainda abertas", estilos["secao"]))
    linhas_vencidas_os = [[
        os_item.numero_os,
        nome_subestacao(os_item.id_subestacao, subestacoes, os_item.instalacao),
        codigo_ativo(os_item),
        fmt_data(os_item.data_fim_programado),
        max(0, (referencia.date() - os_item.data_fim_programado.date()).days),
        os_item.status,
        os_item.emissor or (
            f"Plano #{os_item.id_plano_manutencao}"
            if os_item.id_plano_manutencao
            else "Não informado"
        ),
    ] for os_item in sorted(vencidas_os, key=lambda item: item.data_fim_programado or datetime.max)]
    cabecalhos_vencidas_os = [
        "OS", "Instalação", "Ativo", "Fim programado", "Dias vencida", "Status", "Emissor / plano"
    ]
    larguras_vencidas_os = [25 * mm, 34 * mm, 38 * mm, 30 * mm, 23 * mm, 24 * mm, 83 * mm]
    blocos_vencidas_os = [
        linhas_vencidas_os[indice:indice + 14]
        for indice in range(0, len(linhas_vencidas_os), 14)
    ] or [[]]
    for indice, bloco in enumerate(blocos_vencidas_os):
        if indice:
            elementos.append(PageBreak())
        elementos.append(tabela_pdf(
            cabecalhos_vencidas_os,
            bloco,
            larguras_vencidas_os,
            estilos,
            {4: "CENTER"},
        ))

    elementos.append(PageBreak())
    elementos.append(Paragraph("SS vencidas e ainda abertas", estilos["secao"]))
    linhas_vencidas_ss = [[
        ss.numero_ss,
        nome_subestacao(id_subestacao_ss(ss), subestacoes, ss.instalacao),
        codigo_ativo_ss(ss),
        fmt_data(ss.data_hora_limite),
        max(0, (referencia.date() - ss.data_hora_limite.date()).days),
        ss.prioridade,
        ss.status,
        ss.descricao_problema,
    ] for ss in sorted(vencidas_ss, key=lambda item: item.data_hora_limite or datetime.max)]
    elementos.append(tabela_pdf(
        ["SS", "Instalação", "Ativo", "Data limite", "Dias vencida", "Prioridade", "Status", "Problema"],
        linhas_vencidas_ss,
        [26 * mm, 34 * mm, 38 * mm, 28 * mm, 22 * mm, 24 * mm, 22 * mm, 63 * mm],
        estilos,
        {4: "CENTER"},
    ))
    periodo_rodape = f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"

    def cabecalho_rodape(canvas, doc):
        canvas.saveState()
        largura, altura = landscape(A4)
        canvas.setStrokeColor(BORDA)
        canvas.setLineWidth(0.4)
        canvas.line(14 * mm, altura - 12 * mm, largura - 14 * mm, altura - 12 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(CINZA)
        canvas.drawString(14 * mm, altura - 9 * mm, "Auditoria semanal de manutenção")
        canvas.drawRightString(largura - 14 * mm, altura - 9 * mm, f"Período: {periodo_rodape}")
        canvas.line(14 * mm, 10 * mm, largura - 14 * mm, 10 * mm)
        canvas.drawString(14 * mm, 6.5 * mm, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        canvas.drawRightString(largura - 14 * mm, 6.5 * mm, f"Pagina {doc.page}")
        canvas.restoreState()

    documento.build(elementos, onFirstPage=cabecalho_rodape, onLaterPages=cabecalho_rodape)


@router.get("/auditoria-semanal")
def baixar_auditoria_semanal(
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    id_subestacao: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    inicio, fim = intervalo_relatorio(data_inicio, data_fim)
    inicio_dt = datetime.combine(inicio, time.min)
    fim_dt = datetime.combine(fim, time.max)
    agora = datetime.now()
    referencia = min(fim_dt, agora)

    subestacoes_lista = db.query(Subestacao).order_by(Subestacao.nome).all()
    subestacoes = {item.id_subestacao: item.nome for item in subestacoes_lista}
    subestacao_filtro = subestacoes.get(id_subestacao) if id_subestacao else None
    if id_subestacao and not subestacao_filtro:
        raise HTTPException(404, "Instalacao nao encontrada.")

    opcoes_os = (
        joinedload(OrdemServico.ativo),
        joinedload(OrdemServico.grupo_ativo),
    )
    previstas_query = db.query(OrdemServico).options(*opcoes_os).filter(
        OrdemServico.data_inicio_programado >= inicio_dt,
        OrdemServico.data_inicio_programado <= fim_dt,
    )
    executadas_query = db.query(OrdemServico).options(*opcoes_os).filter(
        OrdemServico.data_fim_execucao >= inicio_dt,
        OrdemServico.data_fim_execucao <= fim_dt,
    )
    vencidas_os_query = db.query(OrdemServico).options(*opcoes_os).filter(
        OrdemServico.data_fim_programado.isnot(None),
        OrdemServico.data_fim_programado < referencia,
    )
    if id_subestacao:
        previstas_query = previstas_query.filter(OrdemServico.id_subestacao == id_subestacao)
        executadas_query = executadas_query.filter(OrdemServico.id_subestacao == id_subestacao)
        vencidas_os_query = vencidas_os_query.filter(OrdemServico.id_subestacao == id_subestacao)

    previstas = previstas_query.order_by(OrdemServico.data_inicio_programado).all()
    executadas = [item for item in executadas_query.order_by(OrdemServico.data_fim_execucao).all() if esta_finalizada(item.status)]
    vencidas_os = [item for item in vencidas_os_query.order_by(OrdemServico.data_fim_programado).all() if not esta_finalizada(item.status)]

    vencidas_ss_query = db.query(SolicitacaoServico).options(
        joinedload(SolicitacaoServico.ativo),
        joinedload(SolicitacaoServico.grupo_ativo),
    ).filter(
        SolicitacaoServico.data_hora_limite.isnot(None),
        SolicitacaoServico.data_hora_limite < referencia,
    )
    if id_subestacao:
        ids_ativos = db.query(Ativo.id_ativo).filter(Ativo.id_subestacao == id_subestacao)
        ids_grupos = db.query(GrupoAtivo.id_grupo_ativo).filter(GrupoAtivo.id_subestacao == id_subestacao)
        vencidas_ss_query = vencidas_ss_query.filter(or_(
            SolicitacaoServico.id_ativo.in_(ids_ativos),
            SolicitacaoServico.id_grupo_ativo.in_(ids_grupos),
            SolicitacaoServico.instalacao == subestacao_filtro,
        ))
    vencidas_ss = [
        item for item in vencidas_ss_query.order_by(SolicitacaoServico.data_hora_limite).all()
        if not esta_finalizada(item.status)
    ]

    ids_planos = {
        item.id_plano_manutencao
        for item in [*previstas, *executadas]
        if item.id_plano_manutencao
    }
    planos = {
        item.id_plano_manutencao: item
        for item in db.query(PlanoManutencao).filter(
            PlanoManutencao.id_plano_manutencao.in_(ids_planos or [-1])
        ).all()
    }

    pasta = tempfile.mkdtemp(prefix="auditoria_semanal_")
    nome = f"auditoria_semanal_{inicio.isoformat()}_{fim.isoformat()}.pdf"
    caminho = os.path.join(pasta, re.sub(r"[^A-Za-z0-9_.-]", "_", nome))
    try:
        gerar_pdf_auditoria(
            caminho,
            inicio,
            fim,
            referencia,
            subestacao_filtro,
            subestacoes,
            previstas,
            executadas,
            vencidas_os,
            vencidas_ss,
            planos,
        )
    except Exception:
        shutil.rmtree(pasta, ignore_errors=True)
        raise

    return FileResponse(
        path=caminho,
        filename=os.path.basename(caminho),
        media_type="application/pdf",
        background=BackgroundTask(shutil.rmtree, pasta, ignore_errors=True),
    )
