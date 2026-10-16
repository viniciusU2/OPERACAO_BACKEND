# -*- coding: utf-8 -*-
"""Limpa residuos dos cenarios de E2E (TMP-HP-*, e2e.hardening.*)."""
from __future__ import annotations

from sqlalchemy import text

from database import engine

with engine.begin() as c:
    ieds = [linha[0] for linha in c.execute(text("SELECT id_ied, tag_operacional FROM ied WHERE tag_operacional LIKE 'TMP-HP-%'"))]
    print("IEDs TMP-HP:", ieds)
    for id_ied in ieds:
        c.execute(text("DELETE FROM ied WHERE id_ied = :id"), {"id": id_ied})
    ativos = c.execute(text("DELETE FROM ativo WHERE codigo_ativo LIKE 'TMP-HP-%'")).rowcount
    usuarios = c.execute(text("DELETE FROM usuarios WHERE email LIKE 'e2e.hardening.%'")).rowcount
    arquivos = c.execute(
        text("SELECT id_arquivo, caminho FROM arquivo WHERE nome_original LIKE 'e2e%'")
    ).all()
    print("ativos removidos:", ativos, "| usuarios removidos:", usuarios, "| arquivos e2e:", arquivos)
    for id_arquivo, _caminho in arquivos:
        c.execute(text("DELETE FROM arquivo WHERE id_arquivo = :id"), {"id": id_arquivo})
    print("saldo ied:", c.execute(text("SELECT COUNT(*) FROM ied")).scalar())
    print("saldo ativo TMP:", c.execute(text("SELECT COUNT(*) FROM ativo WHERE codigo_ativo LIKE 'TMP-%'")).scalar())
    print("saldo usuarios e2e:", c.execute(text("SELECT COUNT(*) FROM usuarios WHERE email LIKE 'e2e.%'")).scalar())
