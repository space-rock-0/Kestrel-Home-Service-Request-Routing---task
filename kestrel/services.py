"""Application service layer. API routes, CLI commands, tools and workflows all call these."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .data.discovery import discover
from .data.loader import load_dataset, validate
from .errors import DataNotFoundError, NotFoundError
from .extensions.workflow import run_workflow
from .ml.audit import audit
from .ml.submission import validate_predictions
from .ml.train import train


def _read_state(ctx) -> dict:
    p = ctx.settings.state_path
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except ValueError:
        return {}


def data_status(ctx) -> dict:
    disc = discover(ctx.settings)
    state = _read_state(ctx)
    job = ctx.jobs.latest()
    msg = None
    if not disc.files:
        msg = f"No input files yet. Copy your Excel files into {ctx.settings.input_dir} and they are picked up automatically."
    return {**disc.as_dict(), "message": msg, "model_ready": ctx.router.ready, "trained_at": state.get("trained_at"),
            "stale": bool(disc.files) and disc.fingerprint != state.get("fingerprint"),
            "ready_to_train": bool(disc.files) and "train" not in disc.missing,
            "ready_to_predict": bool(disc.files) and "predict" not in disc.missing,
            "watcher": ctx.watcher.status(), "job": job.as_dict() if job else None}


def validate_data(ctx, action: str = "train") -> dict:
    if action not in ("train", "predict"):
        raise NotFoundError(f"Unknown action '{action}'. Use 'train' or 'predict'.")
    return validate(ctx.settings, action).as_dict()


def run_audit(ctx) -> dict:
    ds = load_dataset(ctx.settings, "train")
    text = audit(ctx.settings, ds)
    ctx.log(f"audit written to {ctx.settings.artifact_dir / 'audit.txt'}")
    return {"path": str(ctx.settings.artifact_dir / "audit.txt"), "preview": text.splitlines()[:25]}


def run_train(ctx) -> dict:
    ds = load_dataset(ctx.settings, "train")
    for w in ds.report.warnings:
        ctx.log(f"warning: {w.message}")
    ctx.bus.emit("pipeline.training", {})
    m = train(ctx.settings, ds, log=ctx.log)
    ctx.router.ensure_fresh()
    ctx.bus.emit("pipeline.trained", {"trained_at": m["trained_at"]})
    h = m["holdout"]
    return {"trained_at": m["trained_at"], "model_accuracy": h["model"]["accuracy"], "bot_accuracy": h["bot_vs_final"]["accuracy"],
            "accuracy_ci95": h["model"]["accuracy_ci95"], "test_rows": (m["test"] or {}).get("rows")}


def check_submission(ctx, path: str | None = None) -> dict:
    disc = discover(ctx.settings)
    if "test" not in disc.by_role:
        return {"skipped": True, "reason": "No test file in the input folder."}
    return validate_predictions(ctx.settings, Path(path) if path else None)


def predict_file(ctx, out: str | None = None) -> dict:
    """Route every row of the test file with the current model. Does not retrain."""
    ds = load_dataset(ctx.settings, "predict")
    res = ctx.router.route_frame(ds.test)
    out_path = Path(out) if out else ctx.settings.predictions_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    res.rename(columns={"request_id": ds.sample_cols[0], "team": ds.sample_cols[1]})[list(ds.sample_cols)].to_csv(out_path, index=False)
    res.to_csv(out_path.with_name(out_path.stem + "_with_confidence.csv"), index=False)
    return {"path": str(out_path), "rows": int(len(res)), "flagged_for_human": int(res.flagged_for_human.sum())}


def read_metrics(ctx) -> dict:
    p = ctx.settings.metrics_path
    if not p.exists():
        raise DataNotFoundError("No metrics yet. Run the pipeline first.")
    return json.loads(p.read_text(encoding="utf-8"))


def start_workflow(ctx, name: str):
    wf = ctx.registry.get("workflow", name)

    def work():
        ctx.bus.emit("pipeline.started", {"workflow": name})
        try:
            out = run_workflow(ctx, wf)
        except Exception as e:
            ctx.bus.emit("pipeline.failed", {"workflow": name, "error": str(e)})
            raise
        ctx.bus.emit("pipeline.succeeded", {"workflow": name})
        return [{"step": r["step"], "result": r["result"]} for r in out]

    return ctx.jobs.submit(name, work)


def golden(ctx, path: str | None = None) -> list:
    """Run the fixed cases taken from the client's email. Read the output, do not trust it blindly."""
    p = Path(path) if path else ctx.settings.root / "config" / "golden_cases.json"
    if not p.exists():
        raise DataNotFoundError(f"Golden case file not found: {p}")
    out = []
    for case in json.loads(p.read_text(encoding="utf-8")):
        r = ctx.router.route({k: v for k, v in case.items() if k != "name"})
        out.append({"case": case["name"], "team": r["team"], "confidence": r["confidence"], "flagged_for_human": r["needs_clarification"]})
    return out


def numbers(ctx, transfer_cost_inr: float, hosting_inr_month: float = 0.0, licence_inr_year: float = 320000.0,
            orders_per_month: float = 700.0, maintenance_hours_month: float = 2.0, hour_inr: float = 0.0) -> dict:
    """Rupee and volume arithmetic from measured values. Every input is an argument, nothing is assumed silently."""
    m = read_metrics(ctx)
    ds = load_dataset(ctx.settings, "train")
    tr = ds.train
    months = max((tr.ts.max() - tr.ts.min()).days / 30.44, 1.0)
    req_month = len(tr) / months
    h = m["holdout"]["wrong_first_touch_rate"]
    # Round the transfer count BEFORE costing it. The memo prints "N transfers x Rs C = Rs S", so
    # N has to be the number that was actually multiplied, or a reader auditing the arithmetic gets
    # a different answer than the document claims.
    avoided = round((h["bot"] - h["model"]) * req_month)
    lic_m = licence_inr_year / 12
    maint = maintenance_hours_month * hour_inr
    run = hosting_inr_month + maint
    saving = round(avoided * transfer_cost_inr)
    net = round(lic_m + saving - run)
    return {
        "months_of_data": round(months, 1), "requests_per_month_measured": round(req_month),
        "requests_per_order": round(req_month / orders_per_month, 2),
        "wrong_first_touch_rate": h, "transfers_avoided_per_month": avoided,
        "transfer_saving_inr_month": saving, "licence_avoided_inr_month": round(lic_m),
        "cost_per_prediction_inr": 0, "run_cost_inr_month": round(run),
        "net_benefit_inr_month": net, "net_benefit_inr_year": round(12 * net),
        "arithmetic": [
            f"licence avoided = {licence_inr_year:,.0f} / 12 = {lic_m:,.0f}",
            f"transfers avoided = ({h['bot']:.3f} - {h['model']:.3f}) x {req_month:.0f} requests = {avoided:.0f}",
            f"transfer saving = {avoided:.0f} x {transfer_cost_inr:,.0f} = {saving:,.0f}",
            f"run cost = hosting {hosting_inr_month:,.0f} + maintenance {maint:,.0f} = {run:,.0f}",
            f"net per month = {lic_m:,.0f} + {saving:,.0f} - {run:,.0f} = {net:,.0f}",
        ],
        "caution": "The transfer saving uses the point estimate. Recompute with the interval bounds before quoting a range.",
    }


def doctor(ctx, strict: bool = False) -> dict:
    from .doctor import run_doctor
    return run_doctor(ctx, strict)


def policy_text(ctx) -> dict:
    """Extract text from the policy PDF in the input folder. Returns lines that look like costs, as candidates only."""
    import re
    pdfs = sorted(ctx.settings.input_dir.glob("*.pdf"))
    if not pdfs:
        raise DataNotFoundError(f"No PDF found in {ctx.settings.input_dir}. Copy ops-policy.pdf there.")
    pdf = next((p for p in pdfs if "policy" in p.name.lower()), pdfs[0])
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise DataNotFoundError("pypdf is not installed. Run: pip install pypdf") from e
    try:
        reader = PdfReader(str(pdf))
        pages = [(pg.extract_text() or "") for pg in reader.pages]
    except Exception as e:
        raise DataNotFoundError(f"Could not read '{pdf.name}': {e}") from e
    text = "\n".join(f"--- page {i} ---\n{t}" for i, t in enumerate(pages, 1))
    out = ctx.settings.artifact_dir / "policy.txt"
    out.write_text(text, encoding="utf-8")
    cost_re = re.compile(r"(rs\.?\s?\d|₹|\binr\b|\bcost\b|\bfee\b|\bcharge)", re.I)
    cands = [ln.strip() for ln in text.splitlines() if cost_re.search(ln)][:25]
    res = {"file": pdf.name, "pages": len(pages), "chars": len(text), "path": str(out), "cost_candidate_lines": cands,
           "note": "Candidates only. Read the page and confirm the cost of one transfer before using it."}
    if len(text) < 200:
        res["warning"] = "Almost no text extracted. The PDF may be scanned; read it by eye."
    return res


def audit_rules(ctx) -> list:
    """For each rule in rules.json: how often did history agree with it? Enable a rule only if this says so."""
    from .ml.rules import load_rules, match_rule
    ds = load_dataset(ctx.settings, "train")
    closed = ds.train[ds.train.final_team.notna() & (ds.train.source == "crm")]
    out = []
    for r in load_rules(ctx.settings.rules_file):
        trial = {**r, "enabled": True}
        hits = agree = 0
        for row in closed[["text", "product_family", "warranty_status", "channel", "final_team"]].itertuples(index=False):
            rec = {"text": row.text, "product_family": row.product_family, "warranty_status": row.warranty_status, "channel": row.channel}
            if match_rule(rec, [trial]):
                hits += 1
                agree += int(row.final_team == r["team"])
        rate = agree / hits if hits else None
        out.append({"id": r.get("id"), "team": r.get("team"), "enabled_now": bool(r.get("enabled")), "matches_in_crm_closed": hits,
                    "agreement": None if rate is None else round(rate, 4),
                    "recommend_enable": bool(hits >= 30 and rate is not None and rate >= 0.95),
                    "reason": "needs >= 30 matches and >= 95% agreement with the team that closed the request"})
    return out


def form_values(ctx, flagged_limit: float | None = None) -> dict:
    from . import reporting
    vals = reporting.form_values(read_metrics(ctx), flagged_limit if flagged_limit is not None else reporting.FLAGGED_LIMIT)
    reporting.dump(ctx.settings.artifact_dir / "form_values.json", vals)
    return vals


def render_docs(ctx, transfer_cost_inr: float | None = None, hosting_inr_month: float = 0.0, flagged_limit: float | None = None, **num_kw) -> dict:
    """Fill docs/templates/*.md with measured values and write them to output/. Hand-written placeholders stay visible."""
    from . import reporting
    vals = form_values(ctx, flagged_limit)
    if transfer_cost_inr is not None:
        n = numbers(ctx, transfer_cost_inr, hosting_inr_month, **num_kw)
        vals.update(reporting.numbers_values(n, transfer_cost_inr, hosting_inr_month))
    res = reporting.render_dir(ctx.settings.templates_dir, ctx.settings.output_dir, vals)
    return {"files": res, "note": "Placeholders left in the output need your own judgement or a missing input (for example --transfer-cost-inr)."}
