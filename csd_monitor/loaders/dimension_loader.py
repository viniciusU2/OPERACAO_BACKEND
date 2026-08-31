"""Carregamento/upsert das dimensões."""

from __future__ import annotations

import pandas as pd

from ..database.repository import get_or_create_canal, get_or_create_grandeza, get_or_create_tipo_alarme


def load_channels(connection, frame: pd.DataFrame) -> dict[int, int]:
    return {int(row["indice_canal"]): get_or_create_canal(connection, row) for row in frame.to_dict("records")}


def load_grandezas(connection, frames: list[pd.DataFrame]) -> dict[tuple[str, str], int]:
    result = {}
    for frame in frames:
        for row in frame.itertuples(index=False):
            code = row.codigo_grandeza
            unit = getattr(row, "unidade", None) or ""
            values = {
                "codigo": code,
                "nome": code.replace("_", " ").title(),
                "categoria": getattr(row, "categoria", None),
                "subcategoria": getattr(row, "subcategoria", None),
                "unidade": unit,
            }
            result[(code, unit)] = get_or_create_grandeza(connection, values)
    return result


def load_alarm_types(connection, frame: pd.DataFrame) -> dict[str, int]:
    result = {}
    for row in frame.itertuples(index=False):
        code = row.codigo_alarme
        result[code] = get_or_create_tipo_alarme(
            connection,
            {"codigo": code, "nome": code.replace("_", " ").title(), "categoria": getattr(row, "categoria", None), "severidade": None},
        )
    return result


