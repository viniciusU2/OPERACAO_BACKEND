import io
import re
import unicodedata
import zipfile
from difflib import SequenceMatcher
from pathlib import Path, PurePosixPath

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models.Ativo import Ativo
from models.familias_models import TipoAtivo
from models.plano_manutencao_models import PlanoItem, PlanoManutencao
from relatorio_manutencao.routes import MAX_ZIP_BYTES, _normalizar_periodicidade, _validar_contexto, _validar_zip
from relatorio_manutencao.review_enrichment import criar_miniatura_data_url

try:
    import pytesseract
    caminho_windows = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if caminho_windows.is_file():
        pytesseract.pytesseract.tesseract_cmd = str(caminho_windows)
    try:
        idiomas_ocr = set(pytesseract.get_languages(config=""))
        IDIOMA_OCR = "por+eng" if "por" in idiomas_ocr and "eng" in idiomas_ocr else "por" if "por" in idiomas_ocr else "eng"
    except Exception:
        IDIOMA_OCR = "eng"
except ImportError:  # OCR opcional: a análise continua usando o nome do arquivo.
    pytesseract = None
    IDIOMA_OCR = "eng"

router = APIRouter(prefix="/relatorios-manutencao", tags=["Relatorios de manutencao"])


def _normalizar(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def _hash_medio(conteudo: bytes, tamanho: int = 8) -> str:
    with Image.open(io.BytesIO(conteudo)) as imagem:
        imagem = ImageOps.exif_transpose(imagem).convert("L").resize((tamanho, tamanho))
        pixels = list(imagem.getdata())
    media = sum(pixels) / len(pixels)
    return "".join("1" if pixel >= media else "0" for pixel in pixels)


def _distancia_hash(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b))


def _compactar_codigo(valor: str) -> str:
    compacto = re.sub(r"[^A-Z0-9]", "", unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode().upper())
    return compacto.translate(str.maketrans({"I": "1", "L": "1", "O": "0"}))


def _detectar_ponteiro_contador(conteudo: bytes) -> bool:
    """Detecta a seta larga do contador sem confundi-la com a escala do manômetro."""
    try:
        import math
        import numpy as np

        with Image.open(io.BytesIO(conteudo)) as imagem:
            cinza = ImageOps.grayscale(ImageOps.exif_transpose(imagem)).resize((256, 256))
            pixels = np.asarray(cinza, dtype=float)
        raios = np.arange(22, 102)
        proporcoes = []
        for graus in range(360):
            angulo = math.radians(graus)
            xs = np.clip((128 + raios * math.cos(angulo)).astype(int), 0, 255)
            ys = np.clip((128 + raios * math.sin(angulo)).astype(int), 0, 255)
            proporcoes.append(float((pixels[ys, xs] > 185).mean()))
        direcoes_fortes = sum(valor > 0.30 for valor in proporcoes)
        # A seta gera poucos raios muito claros. Um manômetro possui muitas
        # marcas claras distribuídas pelo círculo e é rejeitado pelo limite 24.
        return max(proporcoes, default=0.0) >= 0.38 and 3 <= direcoes_fortes <= 24
    except Exception:
        return False

def _detectar_placa_refletiva_ativo(conteudo: bytes) -> bool:
    """Detecta a placa amarela horizontal de identificação fixada no painel."""
    try:
        import numpy as np

        with Image.open(io.BytesIO(conteudo)) as imagem:
            rgb = np.asarray(ImageOps.exif_transpose(imagem).convert("RGB").resize((256, 256)))
        vermelho, verde, azul = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        amarelo = (
            (vermelho > 180) & (verde > 120) & (verde < 235) &
            (azul < 100) & (vermelho > verde * 1.05)
        )
        area = float(amarelo.mean())
        largura_maxima = int(amarelo.sum(axis=1).max(initial=0))
        # A etiqueta ocupa uma faixa horizontal contínua; pontos amarelos de
        # escadas e sinalização ao fundo não alcançam essa largura/área juntas.
        return area >= 0.006 and largura_maxima >= 25
    except Exception:
        return False

def _detectar_vista_geral_disjuntor(conteudo: bytes) -> bool:
    """Reconhece vista externa do conjunto por céu e contornos da estrutura."""
    try:
        import numpy as np

        with Image.open(io.BytesIO(conteudo)) as imagem:
            imagem = ImageOps.exif_transpose(imagem).convert("RGB").resize((256, 256))
            rgb = np.asarray(imagem, dtype=float)
        vermelho, verde, azul = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        proporcao_ceu = float(((azul > 110) & (azul > vermelho * 1.15) & (azul > verde * 1.04)).mean())
        cinza = vermelho * 0.299 + verde * 0.587 + azul * 0.114
        bordas_x = float((np.abs(np.diff(cinza, axis=1)) > 25).mean())
        bordas_y = float((np.abs(np.diff(cinza, axis=0)) > 25).mean())
        # Fotos gerais têm céu e muitos contornos de cabos, isoladores e colunas.
        # Enquadramentos fechados de instrumentos possuem bem menos contornos.
        return proporcao_ceu >= 0.35 and max(bordas_x, bordas_y) >= 0.095
    except Exception:
        return False

def _extrair_texto_seccionadora(conteudo: bytes) -> str:
    """OCR do código SC-35... usando somente os pixels da fotografia."""
    if pytesseract is None:
        return ""
    try:
        with Image.open(io.BytesIO(conteudo)) as imagem:
            imagem = ImageOps.grayscale(ImageOps.exif_transpose(imagem))
            escala = max(1, int(1800 / max(imagem.size)))
            imagem = imagem.resize((imagem.width * escala, imagem.height * escala))
            textos = []
            for limite, psm in ((200, 11), (220, 6)):
                binaria = imagem.point(lambda pixel: 255 if pixel >= limite else 0)
                try:
                    texto = pytesseract.image_to_string(binaria, lang=IDIOMA_OCR, config=f"--psm {psm}", timeout=6)
                except Exception:
                    texto = pytesseract.image_to_string(binaria, config=f"--psm {psm}", timeout=6)
                textos.append(texto)
            return "\n".join(textos).strip()
    except Exception:
        return ""


def _classificar_imagem_seccionadora(conteudo: bytes) -> str:
    """Distingue painel/resistência da vista externa usando somente pixels."""
    try:
        import numpy as np
        with Image.open(io.BytesIO(conteudo)) as imagem:
            rgb = np.asarray(ImageOps.exif_transpose(imagem).convert("RGB").resize((256, 256)), dtype=float)
        vermelho, verde, azul = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        maior, menor = rgb.max(2), rgb.min(2)
        cinza = vermelho * 0.299 + verde * 0.587 + azul * 0.114
        blue = float(((azul > 105) & (azul > vermelho * 1.12) & (azul > verde * 1.03)).mean())
        bright = float((cinza > 190).mean())
        sat = float(np.mean((maior - menor) / np.maximum(maior, 1)))
        edge = float(max((np.abs(np.diff(cinza, axis=1)) > 25).mean(), (np.abs(np.diff(cinza, axis=0)) > 25).mean()))
        std_gray = float(cinza.std() / 255)
        dark = float((cinza < 65).mean())
        valores = np.asarray([blue, bright, sat, edge, std_gray, dark, blue * edge, bright * edge])
        medias = np.asarray([0.2998645, 0.1890866, 0.2294794, 0.1927990, 0.1953508, 0.0808057, 0.0643282, 0.0367472])
        desvios = np.asarray([0.2013862, 0.1137578, 0.0951214, 0.0617463, 0.0255395, 0.0289124, 0.0489957, 0.0228427])
        pesos = np.asarray([-0.8691837, 0.9619074, 0.3565486, -1.1620084, -1.2019811, 1.1016933, -0.4119867, -0.2135174])
        pontuacao = 0.0693936 + float(np.sum(((valores - medias) / desvios) * pesos))
        return "resistencia" if pontuacao >= 0 else "conservacao"
    except Exception:
        return ""

def _extrair_texto_imagem(conteudo: bytes) -> str:
    if pytesseract is None:
        return ""
    try:
        with Image.open(io.BytesIO(conteudo)) as imagem:
            imagem = ImageOps.exif_transpose(imagem).convert("L")
            imagem_original = imagem.copy()
            imagem = ImageOps.autocontrast(imagem)
            if max(imagem.size) < 1600:
                escala = 1600 / max(imagem.size)
                imagem = imagem.resize((int(imagem.width * escala), int(imagem.height * escala)))
            imagem = ImageEnhance.Contrast(imagem).enhance(1.6).filter(ImageFilter.SHARPEN)

            def executar_ocr(imagem_ocr, psm: int) -> str:
                try:
                    return pytesseract.image_to_string(
                        imagem_ocr, lang=IDIOMA_OCR, config=f"--psm {psm}", timeout=4
                    )
                except Exception:
                    return pytesseract.image_to_string(imagem_ocr, config=f"--psm {psm}", timeout=4)

            texto_geral = executar_ocr(imagem, 11)
            recorte_marca = imagem.crop((
                int(imagem.width * 0.35), int(imagem.height * 0.48), imagem.width, imagem.height
            ))
            recorte_marca = recorte_marca.resize((recorte_marca.width * 2, recorte_marca.height * 2))
            recorte_marca = ImageEnhance.Contrast(recorte_marca).enhance(2.2).filter(ImageFilter.SHARPEN)
            texto_marca = executar_ocr(recorte_marca, 6)
            # A fase é lida da imagem original: o contraste aplicado ao restante
            # pode apagar as letras brancas da marca d'agua.
            recorte_fase = imagem_original.crop((
                int(imagem_original.width * 0.42), int(imagem_original.height * 0.55),
                imagem_original.width, imagem_original.height
            ))
            recorte_fase = recorte_fase.resize((recorte_fase.width * 4, recorte_fase.height * 4))
            recorte_fase = recorte_fase.point(lambda pixel: 255 if pixel >= 220 else 0)
            texto_fase = executar_ocr(recorte_fase, 6)

            # O centro superior contém a placa de manômetros, onde normalmente
            # aparecem SF6, MPa/psi e a etiqueta PR1.
            recorte_instrumento = imagem.crop((
                int(imagem.width * 0.15), int(imagem.height * 0.05),
                int(imagem.width * 0.85), int(imagem.height * 0.70)
            ))
            recorte_instrumento = recorte_instrumento.resize((
                recorte_instrumento.width * 2, recorte_instrumento.height * 2
            ))
            recorte_instrumento = ImageEnhance.Contrast(recorte_instrumento).enhance(2.0).filter(ImageFilter.SHARPEN)
            texto_instrumento = executar_ocr(recorte_instrumento, 11)
            return f"{texto_geral}\n{texto_marca}\n{texto_fase}\n{texto_instrumento}".strip()
    except Exception:
        return ""

def _normalizar_fase(valor: str | None) -> str | None:
    fase = _normalizar(valor or "").replace(" ", "").upper()
    mapas = {
        "VM": "VM", "VN": "VM", "VERMELHA": "VM", "VERMELHO": "VM",
        "BR": "BR", "8R": "BR", "BRANCA": "BR", "BRANCO": "BR",
        "AZ": "AZ", "A2": "AZ", "AZUL": "AZ",
    }
    return mapas.get(fase)


def _extrair_fase(texto_fonte: str) -> str | None:
    texto = unicodedata.normalize("NFKD", str(texto_fonte)).encode("ascii", "ignore").decode().upper()
    # Exige o rótulo FASE para não interpretar letras soltas do equipamento.
    ocorrencias = re.findall(r"FA[S5]E\s*[:=\-]?\s*([A-Z0-9]{1,8})", texto)
    for valor in reversed(ocorrencias):
        fase = _normalizar_fase(valor)
        if fase:
            return fase
    return None

def _sugerir_ativo(texto_fonte: str, ativos: list[Ativo]):
    fase_detectada = _extrair_fase(texto_fonte)
    ativos_da_fase = [ativo for ativo in ativos if _normalizar_fase(ativo.fase) == fase_detectada]
    ativos_considerados = ativos_da_fase if fase_detectada and ativos_da_fase else ativos
    texto_compacto = _compactar_codigo(texto_fonte)
    tokens = [_compactar_codigo(token) for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9 _-]{2,10}", texto_fonte)]
    melhor = None
    melhor_pontuacao = 0.0
    # Se o OCR perder o prefixo (15C4 -> C4), aceite o sufixo apenas quando
    # ele pertencer a um único ativo cadastrado.
    ativos_por_sufixo = {}
    for ativo in ativos_considerados:
        codigo_sufixo = _compactar_codigo(ativo.codigo_ativo or "")
        if len(codigo_sufixo) >= 2:
            ativos_por_sufixo.setdefault(codigo_sufixo[-2:], []).append(ativo)
    for sufixo, correspondencias in ativos_por_sufixo.items():
        if len(correspondencias) == 1 and any(caractere.isalpha() for caractere in sufixo) and sufixo in texto_compacto:
            return correspondencias[0], 0.88
    for ativo in ativos_considerados:
        codigo = _compactar_codigo(ativo.codigo_ativo or "")
        if not codigo:
            continue
        if codigo in texto_compacto:
            return ativo, 1.0
        candidatos = [token for token in tokens if abs(len(token) - len(codigo)) <= 2]
        pontuacao = max((SequenceMatcher(None, codigo, token).ratio() for token in candidatos), default=0.0)
        if pontuacao > melhor_pontuacao:
            melhor, melhor_pontuacao = ativo, pontuacao
    return (melhor, melhor_pontuacao) if melhor_pontuacao >= 0.78 else (None, 0.0)

def _sugerir_item(texto_fonte: str, itens: list[PlanoItem], disjuntor: bool = False):
    texto = _normalizar(texto_fonte)
    palavras_foto = set(texto.split())
    aliases = {
        "oleo": {"lubrificante"}, "arrefecimento": {"refrigerante", "agua"},
        "bat": {"bateria"}, "tensao": {"voltagem"}, "geral": {"conservacao"},
        "armario": {"painel", "cubiculo", "cabinet"}, "horas": {"horimetro"},
    }
    if disjuntor:
        grupos = {
            "contador": {"contador", "operacao", "operacoes", "counter", "operation", "operations", "number"},
            "sf6": {"sf6", "pressao", "pressure", "densidade", "density", "bar", "mpa", "psi", "pr1", "manometro", "gauge", "temperatura", "temperature"},
            "painel": {"painel", "paineis", "armario", "comando", "acionamento", "mecanismo", "control", "cabinet", "relay"},
            "conservacao": {"conservacao", "limpeza", "ferrugem", "corrosao", "estrutura", "objetos", "estranhos"},
            "fechadura": {"fechadura", "fechaduras", "porta", "lock", "door"},
        }
        for chave, termos in grupos.items():
            if palavras_foto & termos:
                palavras_foto.add(chave)
                palavras_foto.update(termos)
    expandidas = set(palavras_foto)
    for palavra in palavras_foto:
        expandidas.update(aliases.get(palavra, set()))
    melhor, pontuacao = None, 0.0
    for item in itens:
        palavras_item = {p for p in _normalizar(item.nome_item).split() if len(p) > 2}
        comuns = expandidas & palavras_item
        atual = sum(2 if palavra in {"contador", "sf6", "pressao", "painel", "armario", "fechadura"} else 1 for palavra in comuns)
        if atual > pontuacao:
            melhor, pontuacao = item, atual
    return melhor, pontuacao

@router.post("/analisar")
async def analisar_zip(
    id_subestacao: int = Form(...),
    id_tipo_ativo: int = Form(...),
    periodicidade: str = Form(...),
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _usuario=Depends(get_current_user),
):
    _validar_contexto(db, id_subestacao, id_tipo_ativo)
    periodicidade = _normalizar_periodicidade(periodicidade)
    if not (arquivo.filename or "").lower().endswith(".zip"):
        raise HTTPException(400, "Envie um arquivo .zip com as fotos.")
    conteudo = await arquivo.read(MAX_ZIP_BYTES + 1)
    if len(conteudo) > MAX_ZIP_BYTES:
        raise HTTPException(413, "O ZIP excede o limite permitido.")
    _validar_zip(conteudo)

    planos = db.query(PlanoManutencao).filter(PlanoManutencao.id_tipo_ativo == id_tipo_ativo).all()
    ids_planos = [plano.id_plano_manutencao for plano in planos]
    itens = (
        db.query(PlanoItem)
        .filter(PlanoItem.id_plano_manutencao.in_(ids_planos), PlanoItem.periodicidade == periodicidade)
        .order_by(PlanoItem.ordem, PlanoItem.id_plano_item)
        .all()
        if ids_planos else []
    )
    if not itens:
        raise HTTPException(400, "Nao existe item de plano para o tipo de ativo e periodicidade selecionados.")
    ativos = db.query(Ativo).filter(Ativo.id_subestacao == id_subestacao, Ativo.id_tipo_ativo == id_tipo_ativo).all()
    tipo_ativo = db.get(TipoAtivo, id_tipo_ativo)
    nome_tipo_ativo = _normalizar(tipo_ativo.nome if tipo_ativo else "")
    eh_disjuntor = "disjuntor" in nome_tipo_ativo
    eh_seccionadora = "seccionadora" in nome_tipo_ativo

    hashes: list[tuple[str, str]] = []
    fotos = []
    ultimo_ativo = None
    with zipfile.ZipFile(io.BytesIO(conteudo)) as pacote:
        for entrada in pacote.infolist():
            if entrada.is_dir():
                continue
            nome = str(PurePosixPath(entrada.filename.replace("\\", "/")))
            dados = pacote.read(entrada)
            if eh_disjuntor:
                texto_ocr = _extrair_texto_imagem(dados)
                texto_fonte = f"{nome} {texto_ocr}"
            elif eh_seccionadora:
                texto_ocr = _extrair_texto_seccionadora(dados)
                # O nome do arquivo não participa da sugestão da seccionadora.
                texto_fonte = texto_ocr
                classe_visual = _classificar_imagem_seccionadora(dados)
                if classe_visual == "resistencia":
                    texto_fonte += " resistencia aquecimento funcionamento painel armario"
                elif classe_visual == "conservacao":
                    texto_fonte += " conservacao estruturas metalicas conexoes vista geral"
            else:
                texto_ocr = ""
                texto_fonte = nome
            texto_ocr_normalizado = _normalizar(texto_ocr)
            sinais_sf6 = {"sf6", "mpa", "psi", "pr1", "pressao", "pressure", "densidade", "density"}
            tem_sinal_sf6 = bool(set(texto_ocr_normalizado.split()) & sinais_sf6)
            tem_placa_refletiva = eh_disjuntor and _detectar_placa_refletiva_ativo(dados)
            if tem_sinal_sf6:
                texto_fonte += " sf6 pressao densidade manometro"
            elif tem_placa_refletiva:
                texto_fonte += " painel paineis armario comando acionamento placa identificacao ativo"
            elif eh_disjuntor and _detectar_ponteiro_contador(dados):
                texto_fonte += " contador operacoes ponteiro"
            elif eh_disjuntor and _detectar_vista_geral_disjuntor(dados):
                texto_fonte += " vista geral disjuntor conservacao objetos estranhos estado geral"
            ativo, confianca_ativo = _sugerir_ativo(texto_fonte, ativos)
            if ativo:
                ultimo_ativo = ativo
            elif eh_disjuntor and ultimo_ativo:
                ativo, confianca_ativo = ultimo_ativo, 0.55
            item, pontos = _sugerir_item(texto_fonte, itens, eh_disjuntor)
            largura = altura = 0
            duplicata_de = None
            try:
                with Image.open(io.BytesIO(dados)) as imagem:
                    imagem = ImageOps.exif_transpose(imagem)
                    largura, altura = imagem.size
                hash_atual = _hash_medio(dados)
                duplicata_de = next((anterior for anterior, hash_anterior in hashes if _distancia_hash(hash_atual, hash_anterior) <= 3), None)
                hashes.append((nome, hash_atual))
            except Exception:
                pass
            confianca = min(0.98, 0.30 + pontos * 0.12 + confianca_ativo * 0.45)
            fotos.append({
                "arquivo": nome,
                "miniatura": criar_miniatura_data_url(dados),
                "id_ativo_sugerido": ativo.id_ativo if ativo else None,
                "codigo_ativo_sugerido": ativo.codigo_ativo if ativo else None,
                "fase_sugerida": ativo.fase if ativo else _extrair_fase(texto_fonte),
                "id_plano_item_sugerido": item.id_plano_item if item else None,
                "item_sugerido": item.nome_item if item else None,
                "confianca": confianca,
                "possivel_duplicata": duplicata_de is not None,
                "duplicata_de": duplicata_de,
                "largura": largura,
                "altura": altura,
                "requer_confirmacao": confianca < 0.6 or duplicata_de is not None,
            })
    return {
        "periodicidade": periodicidade,
        "quantidade_fotos": len(fotos),
        "quantidade_requer_confirmacao": sum(foto["requer_confirmacao"] for foto in fotos),
        "ativos": [{"id_ativo": ativo.id_ativo, "codigo_ativo": ativo.codigo_ativo, "fase": ativo.fase, "bay": ativo.bay} for ativo in ativos],
        "itens": [{"id_plano_item": item.id_plano_item, "nome_item": item.nome_item, "unidade": item.unidade} for item in itens],
        "fotos": fotos,
    }




