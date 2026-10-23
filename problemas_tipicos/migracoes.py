"""Aplicador idempotente das migrações da base de conhecimento de problemas típicos.

As migrações ficam em ``migrations/*_problemas_tipicos*.sql`` e são escritas de
forma idempotente (``ADD COLUMN IF NOT EXISTS``, ``ADD KEY IF NOT EXISTS`` e
``CREATE TABLE IF NOT EXISTS``). O aplicador mantém o controle em
``problemas_tipicos_migracao`` e é chamado na subida da aplicação, logo após o
``Base.metadata.create_all``.

A ordem importa: o ``create_all`` cria as tabelas para bancos novos; as
migrações ajustam bancos que já existiam antes da base de conhecimento.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

LOGGER = logging.getLogger("problemas_tipicos.migracoes")

TABELA_CONTROLE = "problemas_tipicos_migracao"
PADRAO_ARQUIVOS = "*_problemas_tipicos*.sql"
PASTA_PADRAO = Path(__file__).resolve().parent.parent / "migrations"


def _instrucoes(sql: str) -> list[str]:
    """Divide um script SQL em instruções, ignorando comentários de linha."""
    linhas = [linha for linha in sql.splitlines() if not linha.strip().startswith("--")]
    return [instrucao.strip() for instrucao in "\n".join(linhas).split(";") if instrucao.strip()]


def aplicar_migracoes(db: Session, pasta: Path | None = None) -> list[str]:
    """Aplica as migrações ainda não registradas e devolve os nomes aplicados."""
    pasta = pasta or PASTA_PADRAO
    if not pasta.is_dir():
        LOGGER.warning("Pasta de migrações não encontrada: %s", pasta)
        return []

    db.execute(
        text(
            f"CREATE TABLE IF NOT EXISTS {TABELA_CONTROLE} ("
            "nome VARCHAR(160) NOT NULL PRIMARY KEY, "
            "aplicado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
    )
    db.commit()

    aplicadas = {linha[0] for linha in db.execute(text(f"SELECT nome FROM {TABELA_CONTROLE}"))}
    arquivos = sorted(
        arquivo for arquivo in pasta.glob(PADRAO_ARQUIVOS) if not arquivo.name.endswith("_down.sql")
    )

    registradas: list[str] = []
    for arquivo in arquivos:
        if arquivo.name in aplicadas:
            continue
        try:
            for instrucao in _instrucoes(arquivo.read_text(encoding="utf-8")):
                db.execute(text(instrucao))
            db.execute(
                text(f"INSERT INTO {TABELA_CONTROLE} (nome) VALUES (:nome)"),
                {"nome": arquivo.name},
            )
            db.commit()
            registradas.append(arquivo.name)
        except Exception as exc:  # noqa: BLE001 - registra contexto e falha rápido
            db.rollback()
            LOGGER.exception("Falha ao aplicar a migração %s", arquivo.name)
            raise RuntimeError(f"Falha ao aplicar a migração {arquivo.name}") from exc

    if registradas:
        LOGGER.info("Migrações de problemas típicos aplicadas: %s", ", ".join(registradas))
    return registradas
