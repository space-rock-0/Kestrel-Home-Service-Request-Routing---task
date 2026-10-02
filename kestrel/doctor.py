"""One command that tells a person or an agent what is ready and what is not."""
from __future__ import annotations

import importlib
import sys
import tempfile

from .data.discovery import discover
from .data.loader import validate
from .data.schemas import load_schema

REQUIRED_MODULES = ("pandas", "numpy", "sklearn", "scipy", "joblib", "ftfy", "openpyxl", "fastapi", "uvicorn")
OPTIONAL_MODULES = {"xlrd": "needed only for old .xls files", "pypdf": "needed only to read the policy PDF"}


def run_doctor(ctx, strict: bool = False) -> dict:
    s = ctx.settings
    checks: list = []

    def add(name: str, status: str, detail: str = "") -> None:
        checks.append({"check": name, "status": status, "detail": detail})

    soft = "fail" if strict else "warn"  # "nothing here yet" is a failure only in strict mode
    v = sys.version_info
    add("python 3.10+", "pass" if v >= (3, 10) else "fail", f"{v.major}.{v.minor}.{v.micro}")
    for m in REQUIRED_MODULES:
        try:
            importlib.import_module(m)
            add(f"module {m}", "pass")
        except Exception as e:
            add(f"module {m}", "fail", f"{e}. Run: pip install -r requirements.txt")
    for m, why in OPTIONAL_MODULES.items():
        try:
            importlib.import_module(m)
            add(f"module {m}", "pass")
        except Exception:
            add(f"module {m}", "warn", why)
    for label, d in (("input folder writable", s.input_dir), ("artifact folder writable", s.artifact_dir)):
        try:
            d.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryFile(dir=d):
                pass
            add(label, "pass", str(d))
        except Exception as e:
            add(label, "fail", f"{d}: {e}")
    try:
        schema = load_schema(s.schema_file)
        add("schema file", "pass", f"{len(schema.specs)} roles")
    except Exception as e:
        add("schema file", "fail", str(e))
        return _summary(checks)

    disc = discover(s)
    if not disc.files:
        add("input files", soft, f"none in {s.input_dir}. Copy the Excel files there.")
    else:
        add("input files", "pass", ", ".join(f"{f.path.name}->{f.role or 'unmatched'}" for f in disc.files))
        for action in ("train", "predict"):
            if disc.missing.get(action):
                add(f"files for {action}", soft if action == "train" else "warn", f"missing roles: {', '.join(disc.missing[action])}")
        if "train" not in disc.missing:
            rep = validate(s, "train")
            for e in rep.errors:
                add("validation", "fail", e.message)
            if rep.ok:
                add("validation", "pass", f"{len(rep.warnings)} warning(s)" + ("".join(f"; {w.message}" for w in rep.warnings[:3])))
    if ctx.router.ready:
        add("trained model", "pass", f"trained {ctx.router.b['trained_at']}")
        if "test" in disc.by_role:
            from . import services
            r = services.check_submission(ctx)
            add("predictions.csv", "pass" if r.get("ok") else "fail", "; ".join(r.get("errors", [])) or f"{r.get('rows')} rows")
    else:
        add("trained model", soft, "not trained yet. Run: python -m kestrel run full_pipeline")
    if ctx.registry.load_errors:
        add("plugins", "warn", "; ".join(f"{e.get('plugin') or e.get('skill')}: {e['error']}" for e in ctx.registry.load_errors))
    else:
        add("plugins", "pass", f"{len(ctx.registry.names('tool'))} tools, {len(ctx.registry.names('command'))} commands")
    return _summary(checks)


def _summary(checks: list) -> dict:
    n = {k: sum(c["status"] == k for c in checks) for k in ("pass", "warn", "fail")}
    return {"ok": n["fail"] == 0, "counts": n, "checks": checks}
