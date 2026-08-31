"""Leitura genérica dos XMLs SAM_V3_SETTINGS."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

import pandas as pd


NULL_LITERALS = {"", "nan", "NaN", "NA", "N/A", "null", "NULL"}
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?$")


def clean_original(value: Any) -> str | None:
    """Preserva o texto original, normalizando somente marcadores de ausência."""
    if value is None:
        return None
    text = str(value).strip()
    return None if text in NULL_LITERALS else text


def parse_numeric(value: str | None) -> float | None:
    value = clean_original(value)
    if value is None:
        return None
    try:
        return float(value.replace(",", "."))
    except (TypeError, ValueError):
        return None


def parse_boolean(value: str | None) -> bool | None:
    value = clean_original(value)
    if value is None:
        return None
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return None


def parse_datetime(value: str | None) -> datetime | None:
    value = clean_original(value)
    if value is None or not DATETIME_RE.match(value):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_xml(path: str | Path) -> pd.DataFrame:
    """Converte todos os elementos ``value`` em um DataFrame normalizado."""
    path = Path(path)
    root = ET.parse(path).getroot()
    if root.tag != "SAM_V3_SETTINGS":
        raise ValueError(f"Raiz XML inesperada em {path.name}: {root.tag}")

    rows: list[dict[str, Any]] = []
    for value_node in root.findall(".//value"):
        parameter = (value_node.attrib.get("lbl") or "").strip()
        if not parameter:
            raise ValueError(f"Elemento <value> sem atributo lbl em {path.name}")
        original = clean_original("".join(value_node.itertext()))
        rows.append(
            {
                "parametro": parameter,
                "valor_original": original,
                "unidade": clean_original(value_node.attrib.get("unit")),
                "source_file": path.name,
            }
        )

    if not rows:
        raise ValueError(f"Nenhum elemento <value> encontrado em {path}")

    frame = pd.DataFrame(rows)
    frame["valor_numerico"] = frame["valor_original"].map(parse_numeric)
    frame["valor_booleano"] = frame["valor_original"].map(parse_boolean)
    frame["valor_datetime"] = frame["valor_original"].map(parse_datetime)
    return frame


def value_map(frame: pd.DataFrame) -> dict[str, str | None]:
    """Retorna o último valor por parâmetro, útil para metadados escalares."""
    return dict(zip(frame["parametro"], frame["valor_original"], strict=False))

