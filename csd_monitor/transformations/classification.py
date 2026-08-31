"""Regras transparentes de classificação dos parâmetros e fatos."""

from __future__ import annotations

import re

import pandas as pd

from .normalization import base_parameter, channel_index


KNOWN_PARAM_GROUPS = {
    "information": "INFORMATION",
    "general": "GENERAL",
    "mechanical": "MECHANICAL",
    "transfo": "TRANSFO",
    "react": "REACTOR",
    "capa": "CAPACITOR",
    "line": "LINE",
    "internal": "INTERNAL",
}

MEASUREMENT_PREFIXES = (
    "calculated_", "measured_", "rms_", "current_", "voltage_", "travel_",
    "hydraulic_", "residual_", "differential_", "peak_", "transfo",
    "source_", "test_", "phase_", "mls_",
)


def classify_param(parameter: str) -> tuple[str, bool]:
    prefix = parameter.split("_", 1)[0].lower()
    if prefix in KNOWN_PARAM_GROUPS:
        return KNOWN_PARAM_GROUPS[prefix], False
    return "OUTROS", True


def param_dimensions(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame[["parametro", "valor_original", "valor_numerico", "unidade", "source_file"]].copy()
    classifications = result["parametro"].map(classify_param).tolist()
    result["categoria"] = [item[0] for item in classifications]
    result["nao_classificado"] = [item[1] for item in classifications]
    return result


def build_channels(param_frame: pd.DataFrame) -> pd.DataFrame:
    """Cria canais somente a partir dos nomes declarados no param.xml."""
    values = dict(zip(param_frame["parametro"], param_frame["valor_original"], strict=False))
    phases = {i: values.get(f"information_name_phase_{i}") for i in range(3)}
    rows = []
    for index in range(6):
        channel_name = values.get(f"information_name_uac_{index + 1}")
        if channel_name is None:
            channel_name = values.get(f"information_name_iac_{index + 1}")
        rows.append(
            {
                "indice_canal": index,
                "nome_canal": channel_name or f"canal_{index}",
                # Só vinculamos fase quando o XML fornece explicitamente esse índice.
                "fase": phases.get(index),
                "disjuntor": values.get("information_cb_model"),
                "descricao": "Canal declarado no param.xml",
            }
        )
    return pd.DataFrame(rows)


def equipment_dimension(param_frame: pd.DataFrame, measures_frame: pd.DataFrame) -> dict[str, object]:
    param_values = dict(zip(param_frame["parametro"], param_frame["valor_original"], strict=False))
    measure_values = dict(zip(measures_frame["parametro"], measures_frame["valor_original"], strict=False))
    values = {**param_values, **measure_values}

    def joined(prefix: str) -> str | None:
        pieces = [values.get(f"{prefix}_{i}") for i in (1, 2, 3)]
        pieces = [piece for piece in pieces if piece]
        return "/".join(pieces) if pieces else None

    return {
        "project_reference": values.get("information_project_reference"),
        "order_reference": values.get("information_order_reference"),
        "country": values.get("information_country"),
        "end_user": values.get("information_end_user"),
        "substation": values.get("information_substation"),
        "voltage_level_kv": _numeric(values.get("information_system_voltage_level")),
        "frequency_hz": _numeric(values.get("information_system_frequency")),
        "bay_number": values.get("information_bay_number"),
        "feeder_name": values.get("information_feeder_name"),
        "cb_model": values.get("information_cb_model"),
        "cb1_sn": joined("information_cb1_sn"),
        "cb2_sn": joined("information_cb2_sn"),
        "csd_serial_number": values.get("information_csd100_serial_number"),
        "csd_hostname": values.get("information_csd100_hostname"),
        "csd_ied_name": values.get("information_csd100_ied_name"),
        "csd_software_version": values.get("information_csd100_software_version"),
    }


def _numeric(value: object) -> float | None:
    try:
        return None if value is None else float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return None


def _is_alarm(parameter: str) -> bool:
    return parameter.startswith("alarm_") and not parameter.startswith("alarm_mask_")


def _is_timestamp(parameter: str) -> bool:
    return parameter.startswith("timestamp_")


def _is_counter(parameter: str) -> bool:
    return parameter.startswith("counter_")


def _is_state(row: pd.Series) -> bool:
    return row["valor_booleano"] is not None and not _is_alarm(row["parametro"])


def measurement_rows(frame: pd.DataFrame) -> pd.DataFrame:
    mask = frame["valor_numerico"].notna()
    mask &= ~frame["parametro"].map(_is_alarm)
    mask &= ~frame["parametro"].map(_is_timestamp)
    mask &= ~frame["parametro"].map(_is_counter)
    mask &= ~frame["parametro"].str.startswith(("information_", "archive_", "general_", "internal_"))
    mask &= ~frame["parametro"].map(lambda p: p.startswith("last_") or p.startswith("previous_"))
    mask &= ~frame.apply(_is_state, axis=1)
    result = frame.loc[mask].copy()
    result["codigo_grandeza"] = result["parametro"].map(base_parameter)
    result["indice_canal"] = result["parametro"].map(channel_index)
    result["categoria"] = result["codigo_grandeza"].map(_measurement_category)
    result["subcategoria"] = result["codigo_grandeza"].map(_measurement_subcategory)
    return result


def counter_rows(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.loc[frame["parametro"].map(_is_counter) & frame["valor_numerico"].notna()].copy()
    result["codigo_grandeza"] = result["parametro"].map(base_parameter)
    result["indice_canal"] = result["parametro"].map(channel_index)
    return result


def state_rows(frame: pd.DataFrame) -> pd.DataFrame:
    mask = frame.apply(_is_state, axis=1)
    result = frame.loc[mask].copy()
    result["indice_canal"] = result["parametro"].map(channel_index)
    return result


def timestamp_rows(frame: pd.DataFrame) -> pd.DataFrame:
    mask = frame["parametro"].map(_is_timestamp)
    mask &= ~frame["parametro"].str.startswith("timestamp_alarm_")
    mask &= frame["valor_datetime"].notna()
    result = frame.loc[mask].copy()
    result["tipo_timestamp"] = result["parametro"].map(base_parameter)
    result["indice_canal"] = result["parametro"].map(channel_index)
    return result


def alarm_rows(frame: pd.DataFrame) -> pd.DataFrame:
    mask = frame["parametro"].map(_is_alarm)
    mask &= frame["valor_booleano"].notna()
    result = frame.loc[mask].copy()
    result["codigo_alarme"] = result["parametro"].str.removeprefix("alarm_").map(base_parameter)
    result["indice_canal"] = result["parametro"].map(channel_index)
    on_map = dict(zip(frame["parametro"], frame["valor_datetime"], strict=False))
    result["timestamp_on"] = result["parametro"].map(lambda p: on_map.get(f"timestamp_{p}_on"))
    result["timestamp_off"] = result["parametro"].map(lambda p: on_map.get(f"timestamp_{p}_off"))
    result["duracao_segundos"] = (
        result["timestamp_off"] - result["timestamp_on"]
    ).dt.total_seconds()
    result["categoria"] = result["codigo_alarme"].map(_alarm_category)
    return result


def _measurement_category(code: str) -> str:
    if code.startswith(("calculated_", "measured_", "travel_", "hydraulic_")):
        return "MECHANICAL"
    if code.startswith(("rms_", "current_", "voltage_", "residual_", "differential_", "phase_")):
        return "ELECTRICAL"
    if code.startswith("transfo"):
        return "TRANSFO"
    return "OUTROS"


def _measurement_subcategory(code: str) -> str:
    if "meca" in code or "angle" in code or "arc" in code or "travel" in code:
        return "CHAVEAMENTO"
    if "current" in code:
        return "CORRENTE"
    if "voltage" in code:
        return "TENSÃO"
    if "pressure" in code:
        return "PRESSÃO"
    return "GERAL"


def _alarm_category(code: str) -> str:
    if any(token in code for token in ("mechanical", "meca", "position", "pressure")):
        return "MECHANICAL"
    if any(token in code for token in ("uac", "udc", "adc", "voltage", "current")):
        return "ELECTRICAL"
    if "sync" in code or "clock" in code:
        return "SYNCHRONIZATION"
    return "OUTROS"


