"""File-role specs, loaded from config/datasets.json (single source of truth)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..errors import KestrelError
from .readers import norm_header

# Model-level column names. These are fixed by the feature code, not by the file specs.
ID_COL = "request_id"
TEXT_COL = "request_text"
TS_COL = "created_at_ist"
CATEGORICAL = ("product_family", "warranty_status", "channel")
LEGACY_SOURCE = "legacy_zoho"
CURRENT_SOURCE = "crm"


class ConfigError(KestrelError):
    status = 500
    code = "config_error"


@dataclass(frozen=True)
class FileSpec:
    role: str
    stems: tuple
    required: tuple
    needed_for: tuple
    aliases: dict = None  # canonical column -> accepted alternative header names


@dataclass(frozen=True)
class SchemaConfig:
    extensions: tuple
    specs: dict

    def spec(self, role: str) -> FileSpec:
        return self.specs[role]

    def roles_needed_for(self, action: str) -> list:
        return [r for r, s in self.specs.items() if action in s.needed_for]


def map_columns(cols: list, spec: FileSpec):
    """Rename alternative headers to the canonical ones the spec requires. Returns (mapped_columns, renames)."""
    present, renames, taken = set(cols), {}, set()
    for canon in spec.required:
        if canon in present:
            continue
        for alt in (spec.aliases or {}).get(canon, ()):
            if alt in present and alt not in spec.required and alt not in taken:
                renames[alt] = canon
                taken.add(alt)
                break
    return [renames.get(c, c) for c in cols], renames


def load_schema(path: Path) -> SchemaConfig:
    if not path.exists():
        raise ConfigError(f"Schema file not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        common = raw.get("common_aliases", {})
        specs = {}
        for role, d in raw["files"].items():
            merged = {**common, **d.get("aliases", {})}
            aliases = {norm_header(k): tuple(norm_header(a) for a in v) for k, v in merged.items()}
            specs[role] = FileSpec(role, tuple(s.lower() for s in d["stems"]), tuple(d["required"]),
                                   tuple(d.get("needed_for", [])), aliases)
        return SchemaConfig(tuple(e.lower() for e in raw.get("extensions", [".xlsx", ".csv"])), specs)
    except (KeyError, ValueError, TypeError) as e:
        raise ConfigError(f"Schema file {path} is malformed: {e}") from e
