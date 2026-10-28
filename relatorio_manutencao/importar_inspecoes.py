"""Monta um relatorio de manutencao a partir das inspecoes registradas no app.

Regras desta importacao:

- As fotos consideradas sao apenas as que estao no backend
  (``/inspecoes/fotos/<hash>.jpg``). Links externos (SharePoint, Drive...)
  sao ignorados de proposito: o servidor nao tem como baixa-los.
- As informacoes (item, valor medido, status e observacao) vem de
  ``resultado_item_inspecao``.
- O ZIP gerado segue o mesmo formato aceito pelo upload manual, entao o
  relatorio criado pode ser revisado e exportado em Word como qualquer outro.
"""

from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session, joinedload

from models.Ativo import Ativo
from models.plano_manutencao_models import Inspecao, ResultadoItemInspecao
from plano_manutencao.inspecoes import _caminho_foto_inspecao
from relatorio_manutencao.models import RelatorioManutencao
from relatorio_manutencao.photo_models import RelatorioManutencaoFoto

PREFIXO_FOTO_BACKEND = "/inspecoes/fotos/"

MESES = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


@dataclass
class FotoInspecao:
    nome_zip: str
    conteudo: bytes
    id_ativo: int
    id_plano_item: int | None
    valor: str | None
    status: str
    observacao: str | None


def formatar_valor(valor) -> str | None:
    """Converte o DECIMAL do banco em texto curto (12.0000 -> 12)."""
    if valor is None:
        return None
    if isinstance(valor, Decimal):
        texto = format(valor, "f")
    else:
        texto = str(valor)
    texto = texto.rstrip("0").rstrip(".") if "." in texto else texto
    return texto.strip() or None


def _slug(texto: str, limite: int = 80) -> str:
    normalizado = unicodedata.normalize("NFKD", texto or "")
    ascii_texto = normalizado.encode("ascii", "ignore").decode("ascii")
    ascii_texto = re.sub(r"[^A-Za-z0-9]+", "-", ascii_texto).strip("-").lower()
    return ascii_texto[:limite].strip("-") or "relatorio"


def _nome_foto(sequencia: int, codigo_ativo: str, nome_item: str) -> str:
    nome = re.sub(r'[\\/:*?"<>|]+', " ", nome_item or "Item")
    nome = re.sub(r"\s+", " ", nome).strip().rstrip(". ")[:70]
    return f"{codigo_ativo}/{sequencia:03d} - {nome}.jpg"


def _conteudo_foto_backend(url: str | None) -> bytes | None:
    """Le a foto do disco somente quando ela esta no backend."""
    if not url or not url.startswith(PREFIXO_FOTO_BACKEND):
        return None
    caminho = _caminho_foto_inspecao(url[len(PREFIXO_FOTO_BACKEND):])
    if not caminho or not caminho.is_file():
        return None
    try:
        return caminho.read_bytes()
    except OSError:
        return None


def contar_fotos(resultados) -> int:
    return sum(1 for resultado in resultados if _conteudo_foto_backend(resultado.foto))


def carregar_inspecoes(db: Session, ids_inspecao: list[int]) -> list[Inspecao]:
    if not ids_inspecao:
        return []
    return (
        db.query(Inspecao)
        .options(
            joinedload(Inspecao.ativo),
            joinedload(Inspecao.ordem_servico),
            joinedload(Inspecao.resultados).joinedload(ResultadoItemInspecao.plano_item),
        )
        .filter(Inspecao.id_inspecao.in_(ids_inspecao))
        .all()
    )


def listar_disponiveis(
    db: Session,
    id_subestacao: int | None = None,
    id_tipo_ativo: int | None = None,
    periodicidade: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> list[Inspecao]:
    query = (
        db.query(Inspecao)
        .join(Ativo, Ativo.id_ativo == Inspecao.id_ativo)
        .options(
            joinedload(Inspecao.ativo),
            joinedload(Inspecao.ordem_servico),
            joinedload(Inspecao.resultados),
        )
    )
    if id_subestacao is not None:
        query = query.filter(Ativo.id_subestacao == id_subestacao)
    if id_tipo_ativo is not None:
        query = query.filter(Ativo.id_tipo_ativo == id_tipo_ativo)
    if periodicidade:
        query = query.filter(Inspecao.periodicidade == periodicidade)
    if data_inicio is not None:
        query = query.filter(Inspecao.data_inspecao >= datetime.combine(data_inicio, time.min))
    if data_fim is not None:
        query = query.filter(Inspecao.data_inspecao <= datetime.combine(data_fim, time.max))
    return query.order_by(Inspecao.data_inspecao.desc()).all()


def resumo_inspecao(inspecao: Inspecao) -> dict:
    resultados = list(inspecao.resultados or [])
    fotos_backend = contar_fotos(resultados)
    fotos_link = sum(
        1
        for resultado in resultados
        if resultado.foto and not resultado.foto.startswith(PREFIXO_FOTO_BACKEND)
    )
    return {
        "id_inspecao": inspecao.id_inspecao,
        "id_ativo": inspecao.id_ativo,
        "codigo_ativo": inspecao.ativo.codigo_ativo if inspecao.ativo else None,
        "fase": inspecao.ativo.fase if inspecao.ativo else None,
        "data_inspecao": inspecao.data_inspecao,
        "periodicidade": inspecao.periodicidade.value
        if hasattr(inspecao.periodicidade, "value")
        else str(inspecao.periodicidade),
        "responsavel": inspecao.responsavel,
        "numero_os": inspecao.ordem_servico.numero_os if inspecao.ordem_servico else None,
        "numero_apr": inspecao.ordem_servico.numero_apr if inspecao.ordem_servico else None,
        "itens": len(resultados),
        "fotos_backend": fotos_backend,
        "fotos_link": fotos_link,
    }


def periodo_capa(data_referencia: date) -> str:
    return f"{MESES[data_referencia.month]}/ {data_referencia.year}"


def texto_introducao_padrao(
    data_referencia: date,
    subestacao: str,
    tipo_ativo: str,
) -> str:
    return (
        f"Este relatório reúne inspeções realizadas no dia "
        f"{data_referencia.strftime('%d/%m/%Y')} na Subestação {subestacao}, "
        f"nos equipamentos do tipo {tipo_ativo}, operados pela Rialma "
        "Transmissora de Energia V S.A., referentes ao projeto da RTV.\n"
        "As inspeções foram realizadas tendo como referência os itens do plano "
        "de manutenção cadastrados no Sistema ENGVI.\n"
        "São apresentadas imagens dos equipamentos inspecionados. Os "
        "equipamentos que apresentarem anormalidades deverão ser destacados e "
        "vinculados às respectivas Solicitações de Serviço (SS)."
    )


def montar_fotos(
    inspecoes: list[Inspecao],
) -> tuple[list[FotoInspecao], list[Inspecao]]:
    """Separa as fotos disponiveis no backend e as inspecoes sem foto."""
    fotos: list[FotoInspecao] = []
    sem_foto: list[Inspecao] = []
    sequencia = 0
    for inspecao in sorted(
        inspecoes,
        key=lambda item: (
            (item.ativo.codigo_ativo if item.ativo else ""),
            item.data_inspecao or datetime.min,
        ),
    ):
        codigo = inspecao.ativo.codigo_ativo if inspecao.ativo else "ATIVO"
        resultados = sorted(
            inspecao.resultados or [],
            key=lambda resultado: (
                resultado.plano_item.ordem if resultado.plano_item else 0,
                resultado.id_resultado,
            ),
        )
        incluidas = 0
        for resultado in resultados:
            conteudo = _conteudo_foto_backend(resultado.foto)
            if not conteudo:
                continue
            sequencia += 1
            incluidas += 1
            status = (
                resultado.status_item.value
                if hasattr(resultado.status_item, "value")
                else str(resultado.status_item or "OK")
            )
            fotos.append(
                FotoInspecao(
                    nome_zip=_nome_foto(sequencia, codigo, resultado.nome_item),
                    conteudo=conteudo,
                    id_ativo=inspecao.id_ativo,
                    id_plano_item=resultado.id_plano_item,
                    valor=formatar_valor(resultado.valor_medido),
                    status=status,
                    observacao=(resultado.observacao_item or "").strip() or None,
                )
            )
        if not incluidas:
            sem_foto.append(inspecao)
    return fotos, sem_foto


def montar_zip(fotos: list[FotoInspecao]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as pacote:
        for foto in fotos:
            pacote.writestr(foto.nome_zip, foto.conteudo)
    return buffer.getvalue()


def salvar_zip(conteudo: bytes, pasta: Path) -> tuple[str, Path]:
    pasta.mkdir(parents=True, exist_ok=True)
    nome_armazenado = f"{uuid4().hex}.zip"
    destino = pasta / nome_armazenado
    temporario = pasta / f".{nome_armazenado}.tmp"
    temporario.write_bytes(conteudo)
    temporario.replace(destino)
    return nome_armazenado, destino


def nome_arquivo_original(
    periodicidade: str,
    subestacao: str,
    tipo_ativo: str,
    data_referencia: date,
) -> str:
    origem = (
        f"Inspecoes {periodicidade.replace('_', ' ')} - {subestacao} - "
        f"{tipo_ativo} - {data_referencia.isoformat()}"
    )
    base = _slug(origem, 120)
    return f"{base}.zip"
