"""Checks on input data. Structure checks need only headers. Content checks need the full tables."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..errors import DataValidationError
from .cleaning import parse_ts
from .schemas import ID_COL, SchemaConfig


@dataclass
class Issue:
    level: str  # "error" | "warning"
    code: str
    message: str
    role: str | None = None

    def as_dict(self) -> dict:
        return {"level": self.level, "code": self.code, "message": self.message, "role": self.role}


@dataclass
class Report:
    action: str
    issues: list = field(default_factory=list)
    files_used: dict = field(default_factory=dict)
    rows: dict = field(default_factory=dict)

    @property
    def errors(self) -> list:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict:
        return {"action": self.action, "ok": self.ok, "files_used": self.files_used, "rows": self.rows,
                "errors": [i.as_dict() for i in self.errors], "warnings": [i.as_dict() for i in self.warnings]}

    def raise_if_errors(self) -> None:
        if self.errors:
            first = "; ".join(i.message for i in self.errors[:3])
            more = f" (+{len(self.errors) - 3} more)" if len(self.errors) > 3 else ""
            raise DataValidationError(f"Input data is not usable: {first}{more}", self.as_dict())


def check_structure(disc, schema: SchemaConfig, action: str) -> list:
    out = []
    for role in disc.missing.get(action, []):
        spec = schema.spec(role)
        out.append(Issue("error", "missing_file",
                         f"No file found for '{role}'. Add an Excel/CSV file named like '{spec.stems[0]}.xlsx' "
                         f"to {disc.input_dir}, or one whose headers include: {', '.join(spec.required)}.", role))
    needed = set(schema.roles_needed_for(action))
    for role, f in disc.by_role.items():
        miss = [c for c in schema.spec(role).required if c not in f.columns]
        if miss:
            level = "error" if role in needed else "warning"
            out.append(Issue(level, "missing_columns",
                             f"'{f.path.name}' (role '{role}') lacks columns: {', '.join(miss)}. Found: {', '.join(f.columns) or 'none'}.", role))
    for f in disc.files:
        if f.how == "unreadable":
            out.append(Issue("warning", "unreadable_file", f"'{f.path.name}' could not be read: {f.note}"))
        elif f.role is None:
            out.append(Issue("warning", "unmatched_file", f"'{f.path.name}' matches no known role and is ignored."))
    for w in disc.warnings:
        out.append(Issue("warning", "duplicate_role", w))
    return out


def _check_ids(df: pd.DataFrame, role: str, out: list) -> None:
    if df.empty:
        out.append(Issue("error", "empty_file", f"'{role}' file has no data rows.", role))
        return
    blank = int((df[ID_COL].str.strip() == "").sum())
    if blank:
        out.append(Issue("error", "blank_ids", f"'{role}' has {blank} rows with an empty {ID_COL}.", role))
    dup = int(df[ID_COL].duplicated().sum())
    if dup:
        out.append(Issue("warning", "duplicate_ids", f"'{role}' has {dup} repeated {ID_COL} values; the first row of each is kept.", role))


def check_content(frames: dict, action: str) -> list:
    out = []
    for role in ("train", "test"):
        df = frames.get(role)
        if df is None:
            continue
        _check_ids(df, role, out)
        if not df.empty and "created_at_ist" in df:
            bad = float(parse_ts(df["created_at_ist"]).isna().mean())
            if bad > 0.20:
                out.append(Issue("error", "bad_timestamps", f"{bad:.0%} of '{role}' created_at_ist values cannot be parsed as dates.", role))
            elif bad > 0.02:
                out.append(Issue("warning", "bad_timestamps", f"{bad:.1%} of '{role}' created_at_ist values cannot be parsed as dates.", role))
    tr, res, te = frames.get("train"), frames.get("resolution"), frames.get("test")
    if res is not None and not res.empty and "request_id" in res:
        _check_ids(res, "resolution", out)
        if tr is not None and not tr.empty:
            cov = float(tr[ID_COL].isin(set(res[ID_COL])).mean())
            if cov < 0.5:
                out.append(Issue("error", "resolution_coverage", f"Only {cov:.0%} of train request_ids appear in the resolution log.", "resolution"))
            elif cov < 1.0:
                out.append(Issue("warning", "resolution_coverage", f"{1 - cov:.1%} of train request_ids are missing from the resolution log; they are not used for training.", "resolution"))
    if tr is not None and te is not None and not tr.empty and not te.empty:
        overlap = int(te[ID_COL].isin(set(tr[ID_COL])).sum())
        if overlap:
            out.append(Issue("warning", "id_overlap", f"{overlap} test request_ids also appear in train.", "test"))
    ss = frames.get("sample_submission")
    if ss is not None and te is not None and set(ss[ID_COL]) != set(te[ID_COL]):
        out.append(Issue("warning", "sample_ids_differ", "sample_submission request_ids differ from the test file.", "sample_submission"))
    return out
