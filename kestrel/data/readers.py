"""Read CSV/TSV/Excel into string DataFrames with normalised headers."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from ..errors import DataValidationError


def norm_header(h) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(h).strip().lower()).strip("_")


def _pick_sheet(path: Path, sheet: str, role_hints: tuple) -> str | int:
    if sheet:
        return sheet
    try:
        names = pd.ExcelFile(path).sheet_names
    except Exception as e:
        raise DataValidationError(f"Cannot open Excel file '{path.name}': {e}") from e
    low = {n.lower().strip(): n for n in names}
    for hint in role_hints:
        if hint in low:
            return low[hint]
    return names[0]


def read_table(path: Path, sheet: str = "", role_hints: tuple = (), nrows: int | None = None) -> pd.DataFrame:
    ext = path.suffix.lower()
    try:
        if ext in (".csv", ".tsv"):
            df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig",
                             encoding_errors="replace", sep="\t" if ext == ".tsv" else ",", nrows=nrows)
        elif ext in (".xlsx", ".xlsm", ".xls"):
            sh = _pick_sheet(path, sheet, role_hints)
            df = pd.read_excel(path, sheet_name=sh, dtype=str, keep_default_na=False, nrows=nrows)
        else:
            raise DataValidationError(f"Unsupported file type '{ext}' for '{path.name}'.")
    except DataValidationError:
        raise
    except Exception as e:
        raise DataValidationError(f"Could not read '{path.name}': {e}") from e
    df.columns = [norm_header(c) for c in df.columns]
    df = df.loc[:, [c for c in df.columns if c and not c.startswith("unnamed")]]
    return df
