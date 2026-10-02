"""Scan the input folder, work out which file plays which role, fingerprint the folder."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..settings import Settings
from .readers import read_table
from .schemas import SchemaConfig, load_schema, map_columns


@dataclass
class DetectedFile:
    path: Path
    role: str | None
    how: str  # "filename" | "columns" | "unmatched" | "unreadable"
    columns: list = field(default_factory=list)
    renames: dict = field(default_factory=dict)
    size: int = 0
    modified: float = 0.0
    note: str = ""

    def as_dict(self) -> dict:
        return {"file": self.path.name, "role": self.role, "matched_by": self.how, "columns": self.columns,
                "header_renames": self.renames, "size_bytes": self.size, "modified": self.modified, "note": self.note}


@dataclass
class Discovery:
    input_dir: Path
    files: list
    by_role: dict
    missing: dict  # action -> [roles]
    warnings: list
    fingerprint: str

    def as_dict(self) -> dict:
        return {"input_dir": str(self.input_dir), "fingerprint": self.fingerprint,
                "files": [f.as_dict() for f in self.files],
                "roles_found": {r: f.path.name for r, f in self.by_role.items()},
                "missing_roles": self.missing, "warnings": self.warnings}


def _stem_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", Path(name).stem.lower()).strip("_")


def _candidate_files(input_dir: Path, schema: SchemaConfig) -> list:
    if not input_dir.exists():
        return []
    out = []
    for p in sorted(input_dir.iterdir()):
        if not p.is_file() or p.name.startswith(("~$", ".")) or p.suffix.lower() not in schema.extensions:
            continue
        out.append(p)
    return out


def fingerprint(input_dir: Path, schema: SchemaConfig) -> str:
    h = hashlib.sha1()
    for p in _candidate_files(input_dir, schema):
        st = p.stat()
        h.update(f"{p.name}|{st.st_size}|{st.st_mtime_ns}".encode())
    return h.hexdigest()


def _match_by_name(key: str, schema: SchemaConfig) -> str | None:
    best, best_len = None, 0
    for role, spec in schema.specs.items():
        for stem in spec.stems:
            if (key == stem or key.startswith(stem + "_") or key.endswith("_" + stem)) and len(stem) > best_len:
                best, best_len = role, len(stem)
    return best


def _match_by_columns(cols: list, schema: SchemaConfig):
    """Best role whose required columns (after alias mapping) are all present. Returns (role, renames) or (None, {})."""
    cands = []
    for role, spec in schema.specs.items():
        mapped, ren = map_columns(cols, spec)
        if set(spec.required) <= set(mapped):
            cands.append((len(spec.required), -len(ren), role, ren))
    if not cands:
        return None, {}
    best = max(cands)
    return best[2], best[3]


def read_detected(settings: Settings, f: "DetectedFile", role: str):
    """Read a detected file and apply its header renames."""
    df = read_table(f.path, settings.excel_sheet, (role,))
    return df.rename(columns=f.renames) if f.renames else df


def discover(settings: Settings) -> Discovery:
    schema = load_schema(settings.schema_file)
    files, warnings = [], []
    for p in _candidate_files(settings.input_dir, schema):
        st = p.stat()
        df = DetectedFile(p, None, "unmatched", size=st.st_size, modified=st.st_mtime)
        try:
            hdr = read_table(p, settings.excel_sheet, nrows=0)
            df.columns = list(hdr.columns)
        except Exception as e:  # unreadable or locked file: report, keep scanning
            df.how, df.note = "unreadable", str(getattr(e, "message", e))
            files.append(df)
            continue
        raw = list(df.columns)
        role = _match_by_name(_stem_key(p.name), schema)
        renames = {}
        if role:
            mapped, renames = map_columns(raw, schema.spec(role))
            if set(schema.spec(role).required) <= set(mapped):
                df.how = "filename"
            else:
                # filename says one thing, headers disagree: trust headers if they match another role
                alt, alt_ren = _match_by_columns(raw, schema)
                if alt and alt != role:
                    df.note = f"filename suggested '{role}' but headers match '{alt}'"
                    role, renames, df.how = alt, alt_ren, "columns"
                else:
                    df.how = "filename"
        else:
            role, renames = _match_by_columns(raw, schema)
            df.how = "columns" if role else "unmatched"
        if role and renames:
            df.renames = renames
            df.columns = [renames.get(c, c) for c in raw]
            extra = "headers mapped: " + ", ".join(f"{a} -> {b}" for a, b in renames.items())
            df.note = f"{df.note}; {extra}" if df.note else extra
        df.role = role
        if not role:
            df.note = df.note or "no role matched by name or headers"
        files.append(df)

    by_role = {}
    for f in sorted((f for f in files if f.role), key=lambda f: f.modified):
        if f.role in by_role:
            warnings.append(f"Several files match role '{f.role}'. Using the newest: '{f.path.name}' "
                            f"(ignoring '{by_role[f.role].path.name}').")
        by_role[f.role] = f
    missing = {}
    for action in ("train", "predict"):
        miss = [r for r in schema.roles_needed_for(action) if r not in by_role]
        if miss:
            missing[action] = miss
    return Discovery(settings.input_dir, files, by_role, missing, warnings, fingerprint(settings.input_dir, schema))
