"""Normalização e derivação de chaves naturais dos parâmetros."""

from __future__ import annotations

import re

import pandas as pd


CHANNEL_SUFFIX_RE = re.compile(r"_(\d+)$")


def channel_index(parameter: str) -> int | None:
    match = CHANNEL_SUFFIX_RE.search(parameter)
    if not match:
        return None
    index = int(match.group(1))
    return index if 0 <= index <= 5 else None


def base_parameter(parameter: str) -> str:
    match = CHANNEL_SUFFIX_RE.search(parameter)
    if match and 0 <= int(match.group(1)) <= 5:
        return parameter[: match.start()]
    return parameter


def normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"parametro", "valor_original", "unidade", "source_file"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Colunas ausentes no DataFrame XML: {sorted(missing)}")
    normalized = frame.copy()
    normalized["indice_canal"] = normalized["parametro"].map(channel_index)
    normalized["codigo_base"] = normalized["parametro"].map(base_parameter)
    normalized["valor_numerico"] = pd.to_numeric(
        normalized["valor_numerico"], errors="coerce"
    )
    normalized["valor_original"] = normalized["valor_original"].where(
        normalized["valor_original"].notna(), None
    )
    return normalized

