"""Aplicador idempotente das migrações de referência do módulo de Proteção.

As migrações versionadas ficam em ``migrations/*_engenharia_protecao_fase*.sql``
e são escritas de forma idempotente (``CREATE TABLE IF NOT EXISTS`` e inserções
com guarda). Este módulo garante que elas sejam efetivamente aplicadas na subida
da aplicação e registradas em ``engenharia_protecao_migracao`` — substituindo a
dependência exclusiva de ``Base.metadata.create_all``.

Uma falha em uma migração **não** derruba a aplicação: é registrada como aviso,
pois o ``create_all`` continua garantindo o esquema mínimo.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

LOGGER = logging.getLogger("engenharia_protecao.migracoes")

TABELA_CONTROLE = "engenharia_protecao_migracao"
PADRAO_ARQUIVOS = "*_engenharia_protecao_fase*.sql"
PASTA_PADRAO = Path(__file__).resolve().parent.parent / "migrations"


def _instrucoes(sql: str) -> list[str]:
    """Divide um script SQL em instruções, ignorando comentários de linha."""
    linhas = [linha for linha in sql.splitlines() if not linha.strip().startswith("--")]
    return [instrucao.strip() for instrucao in "\n".join(linhas).split(";") if instrucao.strip()]


def aplicar_migracoes(db: Session, pasta: Path | None = None) -> list[str]:
    """Aplica as migrações ainda não registradas e retorna os nomes aplicados."""
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
        except Exception as exc:  # noqa: BLE001 - best-effort, nunca derruba a subida
            db.rollback()
            LOGGER.warning("Falha ao aplicar a migração %s: %s", arquivo.name, exc)

    if registradas:
        LOGGER.info("Migrações de Proteção aplicadas: %s", ", ".join(registradas))
    return registradas
