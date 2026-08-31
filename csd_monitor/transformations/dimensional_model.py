"""Constrói os DataFrames intermediários do modelo dimensional."""

from __future__ import annotations

import pandas as pd

from .classification import alarm_rows, build_channels, counter_rows, measurement_rows, param_dimensions, state_rows, timestamp_rows
from .normalization import normalize_frame


def build_dimensional_model(param_frame: pd.DataFrame, measures_frame: pd.DataFrame) -> dict[str, pd.DataFrame | dict]:
    param = normalize_frame(param_frame)
    measures = normalize_frame(measures_frame)
    return {
        "param": param,
        "measures": measures,
        "configuracao": param_dimensions(param),
        "canais": build_channels(param),
        "medicoes": measurement_rows(measures),
        "alarmes": alarm_rows(measures),
        "estados": state_rows(measures),
        "contadores": counter_rows(measures),
        "timestamps": timestamp_rows(measures),
    }

