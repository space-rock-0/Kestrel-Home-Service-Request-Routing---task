"""Check predictions.csv against the test file and the model's team names before anyone sends it."""
from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from ..data.loader import load_dataset
from ..errors import ModelNotReadyError
from ..settings import Settings


def validate_predictions(settings: Settings, path: Path | None = None) -> dict:
    path = path or settings.predictions_path
    if not path.exists():
        return {"ok": False, "errors": [f"{path} does not exist. Run the pipeline first."], "warnings": []}
    if not settings.model_path.exists():
        raise ModelNotReadyError("No trained model: cannot know the valid team names.")
    b = joblib.load(settings.model_path)
    ds = load_dataset(settings, "predict")
    sub = pd.read_csv(path, dtype=str, keep_default_na=False)
    idc, tc = ds.sample_cols
    errs, warns = [], []
    if list(sub.columns) != [idc, tc]:
        errs.append(f"columns {list(sub.columns)} != expected {[idc, tc]}")
    else:
        if len(sub) != len(ds.test):
            errs.append(f"row count {len(sub)} != test rows {len(ds.test)}")
        if sub[idc].duplicated().any():
            errs.append("duplicate request_id rows")
        if set(sub[idc]) != set(ds.test.request_id):
            errs.append("request_id set differs from the test file")
        bad = sorted(set(sub[tc]) - set(b["canon"]))
        if bad:
            errs.append(f"team values outside the canonical set {b['canon']}: {bad}")
        old = sorted(set(sub[tc]) & {k for k, v in b["team_map"].items() if k != v})
        if old:
            errs.append(f"pre-rename team names present: {old}")
    return {"ok": not errs, "errors": errs, "warnings": warns, "rows": int(len(sub)),
            "distribution": sub[tc].value_counts().to_dict() if tc in sub else {}}
