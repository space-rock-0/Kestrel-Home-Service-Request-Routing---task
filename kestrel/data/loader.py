"""Turn the input folder into model-ready tables. One entry point: load_dataset()."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..errors import DataValidationError
from ..settings import Settings
from .cleaning import add_meta, build_team_map, clean_text, parse_ts
from .discovery import Discovery, discover, read_detected
from .schemas import CATEGORICAL, load_schema
from .validation import Report, check_content, check_structure


@dataclass
class Dataset:
    train: pd.DataFrame | None
    test: pd.DataFrame | None
    team_map: dict
    canon: list
    sample_cols: list
    discovery: Discovery
    report: Report


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["text"] = df["request_text"].map(clean_text)
    df["ts"] = parse_ts(df["created_at_ist"])
    for c in CATEGORICAL:
        df[c] = df[c].str.strip().str.lower().replace("", "unknown")
    df["source"] = df["source"].str.strip().str.lower()
    df = df.drop_duplicates("request_id", keep="first").reset_index(drop=True)
    return add_meta(df)


def _read_roles(settings: Settings, disc: Discovery, roles: list) -> dict:
    return {r: read_detected(settings, disc.by_role[r], r) for r in roles if r in disc.by_role}


def _plan(settings: Settings, action: str):
    schema = load_schema(settings.schema_file)
    disc = discover(settings)
    report = Report(action)
    report.issues += check_structure(disc, schema, action)
    report.files_used = {r: f.path.name for r, f in disc.by_role.items()}
    return schema, disc, report


def _roles_to_read(schema, action: str) -> list:
    return list(dict.fromkeys(schema.roles_needed_for(action) + ["test", "sample_submission"]))


def _soften(issues: list, action: str) -> list:
    """The test file is optional while training, so its content errors become warnings there."""
    if action != "predict":
        for i in issues:
            if i.role in ("test", "sample_submission") and i.level == "error":
                i.level = "warning"
    return issues


def validate(settings: Settings, action: str = "train") -> Report:
    """Full check without raising. Reads the tables only when the structure is sound."""
    schema, disc, report = _plan(settings, action)
    if report.ok:
        frames = _read_roles(settings, disc, _roles_to_read(schema, action))
        report.rows = {r: int(len(f)) for r, f in frames.items()}
        report.issues += _soften(check_content(frames, action), action)
    return report


def load_dataset(settings: Settings, action: str = "train") -> Dataset:
    schema, disc, report = _plan(settings, action)
    report.raise_if_errors()
    frames = _read_roles(settings, disc, _roles_to_read(schema, action))
    report.rows = {r: int(len(f)) for r, f in frames.items()}
    report.issues += _soften(check_content(frames, action), action)
    report.raise_if_errors()

    tr = te = None
    tmap, canon = {}, []
    if action == "train":
        raw_tr, res, teams = frames["train"], frames["resolution"], frames["teams"]
        tmap, canon = build_team_map(teams, raw_tr)
        canon_of = lambda s: tmap.get(str(s).strip(), str(s).strip())
        tr = _prep(raw_tr)
        res = res.drop_duplicates("request_id", keep="last").copy()
        for c in ("first_team", "final_team"):
            res[c] = res[c].map(lambda s: canon_of(s) if str(s).strip() else np.nan)
        res["transfers"] = pd.to_numeric(res["transfers"], errors="coerce")
        res["resolved_ts"] = parse_ts(res["resolved_at"])
        tr = tr.merge(res[["request_id", "first_team", "final_team", "transfers", "resolved_ts"]], on="request_id", how="left")
        tr["bot_team"] = tr["team_label"].map(canon_of)
        known = set(canon)
        # A label outside the official list would train a class the client never scores against.
        # These rows are kept, not dropped: dropping them silently would hide the problem and shrink the
        # dataset without anyone noticing. Instead every stray label is counted and named, so the job log,
        # the audit and the doctor report all show it.
        for col in ("final_team", "bot_team"):
            counts = tr[col].value_counts()
            stray = counts[~counts.index.isin(known)]
            if len(stray):
                from .validation import Issue
                detail = ", ".join(f"{k} ({v} rows)" for k, v in stray.items())
                report.issues.append(Issue(
                    "warning", "unknown_team_names",
                    f"{col} has labels outside the official queues in the teams file: {detail}", "teams"))
        if "test" in frames and not frames["test"].empty and not frames["test"]["request_id"].str.strip().eq("").any():
            te = _prep(frames["test"])
    else:
        te = _prep(frames["test"])
    ss = frames.get("sample_submission")
    cols = list(ss.columns[:2]) if ss is not None and len(ss.columns) >= 2 else ["request_id", "team"]
    return Dataset(tr, te, tmap, canon, cols, disc, report)
