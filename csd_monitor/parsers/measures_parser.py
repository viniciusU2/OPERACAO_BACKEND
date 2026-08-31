"""Parser específico do arquivo measures.xml."""

from pathlib import Path

import pandas as pd

from .xml_parser import parse_xml, sha256_file


def parse_measures(path: str | Path) -> pd.DataFrame:
    return parse_xml(path)


def measures_metadata(path: str | Path, frame: pd.DataFrame) -> dict[str, object]:
    values = dict(zip(frame["parametro"], frame["valor_original"], strict=False))
    return {
        "nome_arquivo": Path(path).name,
        "hash_arquivo": sha256_file(path),
        "archive_type": values.get("archive_type"),
        "archive_creation_date_utc": frame.loc[
            frame["parametro"].eq("archive_creation_date_utc"), "valor_datetime"
        ].dropna().iloc[0]
        if frame["parametro"].eq("archive_creation_date_utc").any()
        and frame.loc[frame["parametro"].eq("archive_creation_date_utc"), "valor_datetime"].notna().any()
        else None,
        "archive_creation_date_local": frame.loc[
            frame["parametro"].eq("archive_creation_date_local"), "valor_datetime"
        ].dropna().iloc[0]
        if frame["parametro"].eq("archive_creation_date_local").any()
        and frame.loc[frame["parametro"].eq("archive_creation_date_local"), "valor_datetime"].notna().any()
        else None,
        "switching_program": values.get("calculated_switching_program_open")
        or values.get("general_switching_program"),
        "phase_ref_open": values.get("phase_reference_open"),
        "phase_ref_close": values.get("phase_reference_close"),
    }

