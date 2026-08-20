import io
import re
import unicodedata
import zipfile
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models.Ativo import Ativo
from models.plano_manutencao_models import PlanoItem, PlanoManutencao
from relatorio_manutencao.routes import MAX_ZIP_BYTES, _normalizar_periodicidade, _validar_contexto, _validar_zip
from relatorio_manutencao.review_enrichment import criar_miniatura_data_url

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


def _sugerir_ativo(nome: str, ativos: list[Ativo]):
    texto = _normalizar(nome)
    candidatos = sorted(ativos, key=lambda ativo: len(ativo.codigo_ativo or ""), reverse=True)
    return next((ativo for ativo in candidatos if _normalizar(ativo.codigo_ativo or "") in texto), None)


def _sugerir_item(nome: str, itens: list[PlanoItem]):
    palavras_foto = set(_normalizar(nome).split())
    aliases = {
        "oleo": {"lubrificante"}, "arrefecimento": {"refrigerante", "agua"},
        "bat": {"bateria"}, "tensao": {"voltagem"}, "geral": {"conservacao"},
        "armario": {"painel", "cubiculo"}, "horas": {"horimetro"},
    }
    expandidas = set(palavras_foto)
    for palavra in palavras_foto:
        expandidas.update(aliases.get(palavra, set()))
    melhor, pontuacao = None, 0
    for item in itens:
        palavras_item = {p for p in _normalizar(item.nome_item).split() if len(p) > 3}
        atual = len(expandidas & palavras_item)
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

    hashes: list[tuple[str, str]] = []
    fotos = []
    with zipfile.ZipFile(io.BytesIO(conteudo)) as pacote:
        for entrada in pacote.infolist():
            if entrada.is_dir():
                continue
            nome = str(PurePosixPath(entrada.filename.replace("\\", "/")))
            dados = pacote.read(entrada)
            ativo = _sugerir_ativo(nome, ativos)
            item, pontos = _sugerir_item(nome, itens)
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
            confianca = min(0.95, 0.35 + pontos * 0.15 + (0.25 if ativo else 0))
            fotos.append({
                "arquivo": nome,
                "miniatura": criar_miniatura_data_url(dados),
                "id_ativo_sugerido": ativo.id_ativo if ativo else None,
                "codigo_ativo_sugerido": ativo.codigo_ativo if ativo else None,
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
