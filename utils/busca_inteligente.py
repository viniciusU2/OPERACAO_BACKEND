import re
import unicodedata

from sqlalchemy import String, cast


def termos_busca_inteligente(valor: str | None) -> list[str]:
    """Normaliza acentos e separadores para pesquisar códigos e textos livremente."""
    if not valor or not valor.strip():
        return []
    normalizado = unicodedata.normalize("NFKD", valor)
    sem_acentos = "".join(char for char in normalizado if not unicodedata.combining(char))
    return [termo for termo in re.split(r"[^A-Za-z0-9]+", sem_acentos) if termo]


def condicoes_textuais(modelo, termo: str):
    padrao = f"%{termo}%"
    return [cast(coluna, String).ilike(padrao) for coluna in modelo.__table__.columns]
