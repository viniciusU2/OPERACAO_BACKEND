from __future__ import annotations

import os
import re
import textwrap
from collections import defaultdict
from datetime import date, datetime, time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PAGE_W = 1240
PAGE_H = 1754
MARGIN_X = 145
TOP_Y = 58
BOTTOM_Y = 70
BLUE = (0, 78, 133)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
LIGHT = (245, 247, 250)


def _font(size: int, bold: bool = False):
    custom_font_dir = os.getenv("RDO_FONT_DIR")
    names = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf",
        "Arial_Bold.ttf" if bold else "Arial.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    ]
    dirs = [Path(custom_font_dir)] if custom_font_dir else []
    dirs += [
        Path(__file__).resolve().parent.parent / "modelos" / "fonts",
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/truetype/liberation"),
        Path("/usr/share/fonts/truetype/liberation2"),
        Path("/usr/share/fonts/dejavu"),
        Path("C:/Windows/Fonts"),
    ]

    for directory in dirs:
        for name in names:
            path = directory / name
            if path.exists():
                try:
                    return ImageFont.truetype(str(path), size=size)
                except OSError:
                    continue

    return ImageFont.load_default()


FONT_18 = _font(18)
FONT_18_B = _font(18, True)
FONT_20_B = _font(20, True)
FONT_22_B = _font(22, True)
FONT_24_B = _font(24, True)
FONT_28_B = _font(28, True)


def _texto(valor):
    if valor is None:
        return ""
    return str(valor)


def _data_br(valor):
    if not valor:
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return str(valor)


def _hora_br(valor):
    if not valor:
        return ""
    if isinstance(valor, time):
        return valor.strftime("%Hh%Mmin")
    texto = str(valor)
    if len(texto) >= 5 and texto[2] == ":":
        return f"{texto[:2]}h{texto[3:5]}min"
    return texto


def _periodo(inicio, fim):
    return f"{_hora_br(inicio)} às {_hora_br(fim)}"


def _nome_arquivo_seguro(texto: str):
    texto = re.sub(r"[^A-Za-z0-9_-]+", "_", texto.strip())
    return texto.strip("_") or "rdo"


class RdoPdfRenderer:
    def __init__(self, rdo, total_pages: int = 1):
        self.rdo = rdo
        self.total_pages = total_pages
        self.pages: list[Image.Image] = []
        self.draw: ImageDraw.ImageDraw | None = None
        self.y = TOP_Y
        self.page_number = 0
        self.logo_path = Path("modelos/logo_rdo.png")
        self.logo_fallback_path = Path("modelos/logo.jpg")

    def render(self):
        self.new_page()
        self.draw_configuracoes()
        self.draw_eventos()
        return self.pages

    def new_page(self):
        page = Image.new("RGB", (PAGE_W, PAGE_H), WHITE)
        self.pages.append(page)
        self.draw = ImageDraw.Draw(page)
        self.page_number = len(self.pages)
        self.y = TOP_Y
        self.draw_header()
        self.y = 265

    def ensure_space(self, height: int):
        if self.y + height > PAGE_H - BOTTOM_Y:
            self.new_page()

    def text_size(self, text: str, font):
        bbox = self.draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def draw_centered(self, box, text: str, font, fill=BLACK):
        x1, y1, x2, y2 = box
        w, h = self.text_size(text, font)
        self.draw.text((x1 + (x2 - x1 - w) / 2, y1 + (y2 - y1 - h) / 2 - 1), text, font=font, fill=fill)

    def draw_wrapped(self, box, text: str, font, line_height=28, fill=BLACK, bold_prefix=False):
        x1, y1, x2, _ = box
        max_w = x2 - x1
        lines = wrap_text(self.draw, text, font, max_w)
        yy = y1
        for line in lines:
            if bold_prefix and ":" in line:
                prefix, rest = line.split(":", 1)
                prefix = f"{prefix}:"
                self.draw.text((x1, yy), prefix, font=FONT_18_B, fill=fill)
                pw = self.text_size(prefix + " ", FONT_18_B)[0]
                self.draw.text((x1 + pw, yy), rest.strip(), font=font, fill=fill)
            else:
                self.draw.text((x1, yy), line, font=font, fill=fill)
            yy += line_height
        return yy

    def draw_header(self):
        d = self.draw
        x = MARGIN_X
        y = 55
        header_w = PAGE_W - 2 * MARGIN_X

        logo_path = self.logo_path if self.logo_path.exists() else self.logo_fallback_path
        if logo_path.exists():
            try:
                logo = Image.open(logo_path).convert("RGB")
                logo.thumbnail((270, 100))
                d._image.paste(logo, (x + 8, y + 8))
            except Exception:
                self.draw_logo_fallback(x + 8, y + 8)
        else:
            self.draw_logo_fallback(x + 8, y + 8)

        table_x = x + 335
        table_y = y
        table_w = header_w - 335
        d.rectangle([table_x, table_y, table_x + table_w, table_y + 172], outline=BLACK, width=2)
        d.line([table_x, table_y + 78, table_x + table_w, table_y + 78], fill=BLACK, width=2)
        d.line([table_x + 300, table_y, table_x + 300, table_y + 78], fill=BLACK, width=2)
        d.line([table_x + table_w - 86, table_y, table_x + table_w - 86, table_y + 172], fill=BLACK, width=2)

        d.text((table_x + 8, table_y + 8), "Tipo do Documento:", font=FONT_18, fill=BLACK)
        self.draw_centered((table_x, table_y + 34, table_x + 300, table_y + 76), "FORMULÁRIO", FONT_22_B)
        d.text((table_x + 310, table_y + 8), "Código do Procedimento", font=FONT_18, fill=BLACK)
        self.draw_centered((table_x + 300, table_y + 34, table_x + table_w - 86, table_y + 76), self.rdo.codigo_procedimento or "PR-OP.COS.002", FONT_22_B)
        d.text((table_x + table_w - 80, table_y + 8), "Rev.", font=FONT_18, fill=BLACK)
        self.draw_centered((table_x + table_w - 86, table_y + 34, table_x + table_w, table_y + 76), self.rdo.revisao or "00", FONT_22_B)

        d.text((table_x + 8, table_y + 88), "Título:", font=FONT_18, fill=BLACK)
        self.draw_centered((table_x, table_y + 120, table_x + table_w - 86, table_y + 150), self.rdo.titulo or "RDO - RELATÓRIO DIÁRIO DA OPERAÇÃO", FONT_20_B)
        self.draw_centered((table_x, table_y + 148, table_x + table_w - 86, table_y + 170), f"Data: {_data_br(self.rdo.data_rdo)}", FONT_20_B)
        d.text((table_x + table_w - 80, table_y + 88), "Folha", font=FONT_18, fill=BLACK)
        self.draw_centered((table_x + table_w - 86, table_y + 116, table_x + table_w, table_y + 160), f"{self.page_number}/{self.total_pages}", FONT_22_B)

        d.line([x, 232, x + header_w, 232], fill=BLACK, width=5)

    def draw_logo_fallback(self, x, y):
        self.draw.rectangle([x, y, x + 270, y + 95], fill=BLUE)
        self.draw.text((x + 28, y + 28), "Rialma S.A", font=FONT_28_B, fill=WHITE)

    def draw_configuracoes(self):
        configuracoes = sorted(self.rdo.configuracoes, key=lambda item: (item.ordem or 0, item.periodo_inicio, item.id_configuracao or 0))
        if not configuracoes:
            configuracoes = []

        por_periodo = defaultdict(list)
        for item in configuracoes:
            por_periodo[_periodo(item.periodo_inicio, item.periodo_fim)].append(item)

        periodos = list(por_periodo.keys())
        if not periodos:
            periodos = ["00h00min às 23h59min"]
            por_periodo[periodos[0]] = []

        for inicio in range(0, len(periodos), 3):
            chunk = periodos[inicio:inicio + 3]
            self.draw_config_table(chunk, por_periodo)

    def draw_config_table(self, periodos, por_periodo):
        table_x = MARGIN_X
        table_w = PAGE_W - 2 * MARGIN_X
        col_w = table_w // len(periodos)
        max_rows = max([len(por_periodo[p]) for p in periodos] + [1])
        height = 62 + max_rows * 38
        self.ensure_space(height + 30)

        y = self.y
        d = self.draw
        d.rectangle([table_x, y, table_x + table_w, y + height], outline=BLACK, width=4)
        for idx, periodo in enumerate(periodos):
            x1 = table_x + idx * col_w
            x2 = table_x + table_w if idx == len(periodos) - 1 else x1 + col_w
            d.rectangle([x1, y, x2, y + 62], fill=BLUE, outline=BLACK, width=2)
            self.draw_centered((x1, y + 5, x2, y + 30), "Configuração do Sistema", FONT_20_B, WHITE)
            self.draw_centered((x1, y + 30, x2, y + 58), periodo, FONT_20_B, WHITE)
            if idx:
                d.line([x1, y, x1, y + height], fill=BLACK, width=2)

        for row in range(max_rows):
            y1 = y + 62 + row * 38
            d.line([table_x, y1, table_x + table_w, y1], fill=BLACK, width=1)
            for idx, periodo in enumerate(periodos):
                x1 = table_x + idx * col_w + 8
                itens = por_periodo[periodo]
                if row < len(itens):
                    item = itens[row]
                    texto = f"{item.equipamento} {item.estado}".strip()
                    self.draw_wrapped((x1, y1 + 8, x1 + col_w - 16, y1 + 34), texto, FONT_18, line_height=22, bold_prefix=True)

        self.y += height + 30

    def draw_eventos(self):
        ordem = [
            "Desligamento Automático",
            "Alarmes",
            "Intervenções",
            "Manobras para Conveniência Operativa",
            "Eventos em Sistemas de Comunicação de Voz e Dados",
            "Eventos no Centro de Operação",
            "Eventos para Atendimento a Terceiros",
            "Outros Temas",
            "Documentos Operativos Recebidos ou Alterados",
            "Ocorrências",
        ]
        eventos_por_categoria = defaultdict(list)
        for evento in self.rdo.eventos:
            eventos_por_categoria[evento.categoria or "Ocorrências"].append(evento)

        categorias = list(ordem)
        categorias += sorted(c for c in eventos_por_categoria if c not in categorias)

        for categoria in categorias:
            eventos = sorted(eventos_por_categoria.get(categoria, []), key=lambda item: (item.ordem or 0, item.hora_inicio or time.min, item.id_evento or 0))
            self.draw_event_section(categoria, eventos)

    def draw_event_section(self, categoria: str, eventos):
        self.ensure_space(135)
        table_x = MARGIN_X
        table_w = PAGE_W - 2 * MARGIN_X
        d = self.draw
        y = self.y
        d.rectangle([table_x, y, table_x + table_w, y + 56], fill=BLUE, outline=BLACK, width=3)
        self.draw_centered((table_x, y, table_x + table_w, y + 56), categoria, FONT_22_B, WHITE)
        y += 56
        widths = [128, 128, 110, table_w - 366]
        headers = ["Sistema", "Subestação", "Hora", "Descrição"]
        x = table_x
        for width, header in zip(widths, headers):
            d.rectangle([x, y, x + width, y + 36], outline=BLACK, width=1)
            self.draw_centered((x, y, x + width, y + 36), header, FONT_18_B)
            x += width
        self.y = y + 36

        if not eventos:
            self.draw_event_row("", "", "", "")
        else:
            for evento in eventos:
                hora = _hora_br(evento.hora_inicio)
                if evento.hora_fim:
                    hora = f"{hora}\nàs\n{_hora_br(evento.hora_fim)}"
                descricao = "\n".join(filter(None, [evento.titulo, evento.descricao, evento.status_evento]))
                self.draw_event_row(evento.sistema or self.rdo.sistema or "", evento.subestacao or "", hora, descricao)

        self.y += 30

    def draw_event_row(self, sistema: str, subestacao: str, hora: str, descricao: str):
        table_x = MARGIN_X
        table_w = PAGE_W - 2 * MARGIN_X
        widths = [128, 128, 110, table_w - 366]
        desc_lines = wrap_text(self.draw, descricao, FONT_18, widths[3] - 16)
        if not desc_lines:
            desc_lines = [""]
        hora_lines = hora.splitlines() if hora else [""]
        first = True
        while desc_lines:
            available = PAGE_H - BOTTOM_Y - self.y
            max_lines = max(1, min(len(desc_lines), (available - 22) // 29))
            if available < 90:
                self.new_page()
                continue
            chunk = desc_lines[:max_lines]
            desc_lines = desc_lines[max_lines:]
            row_h = max(70, 20 + max(len(chunk), len(hora_lines)) * 29)
            self.ensure_space(row_h)
            y = self.y
            x = table_x
            values = [sistema if first else "", subestacao if first else "", "\n".join(hora_lines) if first else "", "\n".join(chunk)]
            for idx, width in enumerate(widths):
                self.draw.rectangle([x, y, x + width, y + row_h], outline=BLACK, width=1)
                if idx < 3:
                    lines = values[idx].splitlines() if values[idx] else [""]
                    yy = y + max(8, (row_h - len(lines) * 26) // 2)
                    for line in lines:
                        self.draw_centered((x + 4, yy, x + width - 4, yy + 24), line, FONT_18)
                        yy += 26
                else:
                    self.draw_wrapped((x + 8, y + 10, x + width - 8, y + row_h - 8), values[idx], FONT_18, line_height=29)
                x += width
            self.y += row_h
            first = False


def wrap_text(draw, text: str, font, max_width: int):
    paragraphs = _texto(text).splitlines() or [""]
    lines = []
    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
                line = candidate
            else:
                if line:
                    lines.append(line)
                if draw.textbbox((0, 0), word, font=font)[2] <= max_width:
                    line = word
                else:
                    wrapped = textwrap.wrap(word, width=max(8, max_width // 12))
                    lines.extend(wrapped[:-1])
                    line = wrapped[-1]
        if line:
            lines.append(line)
    return lines


def gerar_pdf_rdo(rdo, pasta_saida: str | os.PathLike = "exports/rdo"):
    pasta = Path(pasta_saida)
    pasta.mkdir(parents=True, exist_ok=True)

    first = RdoPdfRenderer(rdo, total_pages=1).render()
    pages = RdoPdfRenderer(rdo, total_pages=len(first)).render()

    data_nome = _data_br(rdo.data_rdo).replace("/", "-") or datetime.now().strftime("%d-%m-%Y")
    sistema = _nome_arquivo_seguro(rdo.sistema or "RIALMA")
    arquivo = pasta / f"RDO_COS_{sistema}_{data_nome}.pdf"
    pages[0].save(arquivo, save_all=True, append_images=pages[1:], resolution=150.0)
    return arquivo
