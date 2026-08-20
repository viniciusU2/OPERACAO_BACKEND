import base64
import io

from PIL import Image, ImageOps


def criar_miniatura_data_url(conteudo: bytes) -> str | None:
    """Cria uma imagem de revisão legível, preservando detalhes de placas e instrumentos."""
    try:
        with Image.open(io.BytesIO(conteudo)) as imagem:
            imagem = ImageOps.exif_transpose(imagem).convert("RGB")
            imagem.thumbnail((1600, 1200))
            saida = io.BytesIO()
            imagem.save(saida, format="JPEG", quality=86, optimize=True)
        encoded = base64.b64encode(saida.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        return None

