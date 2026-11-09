"""Aplicador idempotente das migracoes do modulo Unifilar.

Mesma mecanica do modulo de Protecao: os scripts ficam em
``migrations/*unifilar*.sql`` (ignora ``*_down.sql``), sao aplicados na
subida da aplicacao e registrados na tabela de controle
``unifilar_migracao``. Uma falha interrompe a subida - seguir com o
esquema parcial deixaria a API incompativel com os modelos.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

LOGGER = logging.getLogger("unifilar.migracoes")

TABELA_CONTROLE = "unifilar_migracao"
PADRAO_ARQUIVOS = "*unifilar*.sql"
PASTA_PADRAO = Path(__file__).resolve().parent.parent / "migrations"


def _instrucoes(sql: str) -> list[str]:
    """Divide um script SQL em instrucoes, ignorando comentarios de linha."""
    linhas = [linha for linha in sql.splitlines() if not linha.strip().startswith("--")]
    return [instrucao.strip() for instrucao in "\n".join(linhas).split(";") if instrucao.strip()]


def aplicar_migracoes(db: Session, pasta: Path | None = None) -> list[str]:
    """Aplica as migracoes ainda nao registradas e retorna os nomes aplicados."""
    pasta = pasta or PASTA_PADRAO
    if not pasta.is_dir():
        LOGGER.warning("Pasta de migracoes nao encontrada: %s", pasta)
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
        arquivo
        for arquivo in pasta.glob(PADRAO_ARQUIVOS)
        if not arquivo.name.endswith("_down.sql")
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
        except Exception as exc:  # noqa: BLE001 - registra contexto e falha rapido
            db.rollback()
            LOGGER.exception("Falha ao aplicar a migracao %s", arquivo.name)
            raise RuntimeError(f"Falha ao aplicar a migracao {arquivo.name}") from exc

    if registradas:
        LOGGER.info("Migracoes Unifilar aplicadas: %s", ", ".join(registradas))
    return registradas
