"""Policy rules loaded from rules.json. A rule fires only when `enabled` is true."""
from __future__ import annotations

import json
import re
from pathlib import Path


def load_rules(path: Path) -> list:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def match_rule(rec: dict, rules: list):
    for r in rules:
        if not r.get("enabled", False):
            continue
        w = r.get("when", {})
        ok = all(rec.get(k) in v for k, v in w.items() if k != "regex")
        if ok and "regex" in w and not re.search(w["regex"], rec.get("text", "")):
            ok = False
        if ok:
            return r
    return None
