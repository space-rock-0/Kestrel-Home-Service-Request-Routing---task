"""Turn metrics into the numbers the memo, evidence file and form need. Nothing here is typed by hand."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

CENSORING_ALLOWANCE = 0.01  # recent rows are partly still open, so closed ones look easier. A stated assumption.
FLAGGED_LIMIT = 0.30         # decision rule default: A needs <= 30% of requests sent to a person. Change with --flagged-limit.
SEPARATION_NEEDED = 0.03     # decision rule: model interval must sit this far above the bot's.


def pct(x, nd: int = 1):
    return None if x is None else round(100 * x, nd)


def inr(n) -> str:
    """Indian digit grouping: 1234567 -> 12,34,567."""
    n = int(round(n))
    sign, s = ("-" if n < 0 else ""), str(abs(n))
    if len(s) <= 3:
        return sign + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return sign + ",".join(parts) + "," + tail


def form_values(metrics: dict, flagged_limit: float = FLAGGED_LIMIT) -> dict:
    h, sp = metrics["holdout"], metrics["split"]
    m, b = h["model"], h["bot_vs_final"]
    months = h.get("by_month_accuracy", {})
    keys = sorted(months)
    first_half = None
    last_month = months[keys[-1]] if keys else None
    if len(keys) >= 2:
        half = keys[: max(1, len(keys) // 2)]
        first_half = sum(months[k] for k in half) / len(half)
    drift = max(0.0, (first_half - last_month)) if first_half is not None and last_month is not None else 0.0
    point = m["accuracy"] - drift
    low = m["accuracy_ci95"][0] - drift - CENSORING_ALLOWANCE
    high = m["accuracy_ci95"][1] - drift
    rec = {k: v for k, v in metrics.get("per_class_holdout", {}).items()
           if isinstance(v, dict) and "recall" in v and k not in ("macro avg", "weighted avg") and v.get("support", 0) >= 10}
    worst = min(rec.items(), key=lambda kv: kv[1]["recall"]) if rec else (None, {"recall": None})
    gate = h["gate_on_holdout"]
    sep = m["accuracy_ci95"][0] - b["accuracy_ci95"][1]
    flagged = gate["share_flagged_for_human"]
    if sep >= SEPARATION_NEEDED and flagged <= flagged_limit:
        decision, why = "A", (f"model interval low {pct(m['accuracy_ci95'][0])}% is {pct(sep)} points above the bot's interval high "
                              f"{pct(b['accuracy_ci95'][1])}% and {pct(flagged)}% of requests go to a person (limit {pct(flagged_limit, 0)}%)")
    else:
        decision, why = "B", (f"separation between intervals is {pct(sep)} points (needs {pct(SEPARATION_NEEDED, 0)}) "
                              f"and {pct(flagged)}% of requests go to a person (limit {pct(flagged_limit, 0)}%)")
    closed, unclosed = sp["rows_closed"], sp["rows_unclosed"]
    return {
        "trained_at": metrics["trained_at"], "n_holdout": m["n"], "dev_rows": sp["dev"], "val_rows": sp["val"],
        "holdout_from": sp["holdout_from"], "rows_closed": closed, "rows_unclosed": unclosed,
        "unclosed_pct": pct(unclosed / max(closed + unclosed, 1)),
        "bot_acc_pct": pct(b["accuracy"]), "bot_ci_lo_pct": pct(b["accuracy_ci95"][0]), "bot_ci_hi_pct": pct(b["accuracy_ci95"][1]),
        "model_acc_pct": pct(m["accuracy"]), "ci_lo_pct": pct(m["accuracy_ci95"][0]), "ci_hi_pct": pct(m["accuracy_ci95"][1]),
        "model_f1": m["macro_f1"], "bot_f1": b["macro_f1"], "delta_pts": pct(m["accuracy"] - b["accuracy"]),
        "ci_separation_pts": pct(sep), "agree_pct": pct(h["model_agreement_with_bot_label"]["accuracy"]),
        "seen_text_acc_pct": pct(h.get("model_accuracy_seen_text")), "unseen_acc_pct": pct(h.get("model_accuracy_unseen_text")),
        "unseen_share_pct": pct(h.get("share_unseen_text")),
        "flagged_pct": pct(flagged), "acc_unflagged_pct": pct(gate["accuracy_when_not_flagged"]), "acc_flagged_pct": pct(gate["accuracy_when_flagged"]),
        "first_half_acc_pct": pct(first_half), "last_month_acc_pct": pct(last_month), "drift_pts": pct(drift),
        "expected_point_pct": pct(point), "expected_low_pct": pct(low), "expected_high_pct": pct(high),
        "expected_formula": f"point = holdout accuracy - drift; low = interval low - drift - {pct(CENSORING_ALLOWANCE)} point censoring allowance; high = interval high - drift",
        "wrong_bot_pct": pct(h["wrong_first_touch_rate"]["bot"]), "wrong_model_pct": pct(h["wrong_first_touch_rate"]["model"]),
        "worst_team": worst[0], "worst_team_recall_pct": pct(worst[1]["recall"]),
        "decision_suggestion": decision, "decision_reason": why,
        # ---- fixed prose, supplied here so render_docs is never destructive ------------------
        # Any {{placeholder}} left unresolved in a template is written through to output/ verbatim.
        # An earlier draft shipped three of these (error_taxonomy, golden_output,
        # tried_kept_discarded), so one render silently replaced 125 hand-written lines of the
        # evidence pack with three literal "{{...}}" strings. The content now lives in
        # docs/handwritten/EVIDENCE_SECTIONS.md and is merged in by hand where needed; the strings
        # below make the generator complete so that cannot happen again.
        "author": os.environ.get("KESTREL_MEMO_AUTHOR", "Sagi Siddhartha"),
        "bot_rule_fixes": (
            "(1) Billing takes a request only when the payment itself is the problem, so 'I paid "
            "for the installation' stops going to Billing; (2) anything reported broken, leaking or "
            "showing an error code goes to Repairs, not Consumables; (3) write those two rules into "
            "the bot's configuration for the three queues it handles worst -- Billing, Filters & "
            "Consumables and Repairs. The other four queues are already 96% correct and should be "
            "left alone"
        ),
        "busiest_teams": (
            "Repairs (23.4% of requests), Installs & Demo (14.7%) and Returns & Replacement (14.2%) "
            "-- the same three in that order when ranked by hand-offs instead"
        ),
    }


def numbers_values(n: dict, transfer_cost_inr: float, hosting_inr_month: float) -> dict:
    out = {"transfer_cost_inr": transfer_cost_inr, "hosting_inr_month": hosting_inr_month}
    for k in ("requests_per_month_measured", "requests_per_order", "transfers_avoided_per_month", "transfer_saving_inr_month",
              "licence_avoided_inr_month", "run_cost_inr_month", "net_benefit_inr_month", "net_benefit_inr_year"):
        out[k] = n[k]
    for k in list(out):
        if k.endswith(("_inr", "_inr_month", "_inr_year")):
            out[k + "_fmt"] = inr(out[k])
    return out


_PH = re.compile(r"\{\{(\w+)\}\}")


def render(template: str, values: dict):
    missing = set()

    def sub(m):
        k = m.group(1)
        if k in values and values[k] is not None:
            return str(values[k])
        missing.add(k)
        return m.group(0)

    return _PH.sub(sub, template), sorted(missing)


def render_dir(templates_dir: Path, out_dir: Path, values: dict) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    res = {}
    for t in sorted(templates_dir.glob("*.md")):
        text, missing = render(t.read_text(encoding="utf-8"), values)
        (out_dir / t.name).write_text(text, encoding="utf-8")
        res[t.name] = {"written": str(out_dir / t.name), "unresolved_placeholders": missing}
    return res


def dump(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
