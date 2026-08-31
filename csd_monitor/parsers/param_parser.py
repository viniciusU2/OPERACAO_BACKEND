"""Parser específico do arquivo param.xml."""

from pathlib import Path

import pandas as pd

from .xml_parser import parse_xml


def parse_param(path: str | Path) -> pd.DataFrame:
    return parse_xml(path)

