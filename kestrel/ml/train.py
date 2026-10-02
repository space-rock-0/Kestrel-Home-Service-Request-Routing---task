"""Train on closed requests (target = team that finally closed the request), evaluate by time, write artifacts."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Callable

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score

from ..data.loader import Dataset
from ..data.schemas import CURRENT_SOURCE, LEGACY_SOURCE
from ..errors import DataValidationError
from ..settings import Settings
from .model import make_pipeline

MIN_CLOSED_CRM = 200


def boot_ci(y, p, n: int = 1000, seed: int = 0) -> list:
    rng = np.random.default_rng(seed)
    y, p = np.asarray(y), np.asarray(p)
    acc = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        acc.append((y[i] == p[i]).mean())
    return [round(float(np.percentile(acc, 2.5)), 4), round(float(np.percentile(acc, 97.5)), 4)]


def score(y, p) -> dict:
    return {"n": int(len(y)), "accuracy": round(float(accuracy_score(y, p)), 4),
            "macro_f1": round(float(f1_score(y, p, average="macro")), 4)}


def fit(df: pd.DataFrame, C: float, cw, zw: float):
    w = np.where(df.source == LEGACY_SOURCE, zw, 1.0)
    pipe = make_pipeline(C, cw)
    pipe.fit(df, df.final_team, clf__sample_weight=w)
    return pipe


def pick_gate(y, proba, classes) -> dict:
    """Smallest confidence line (>= 0.50) that gives >= 95% accuracy on kept rows with >= 50% coverage; else the 20th percentile."""
    y = np.asarray(y)
    top = proba.max(1)
    pred = np.asarray(classes)[proba.argmax(1)]
    for tau in np.arange(0.50, 0.96, 0.05):
        keep = top >= tau
        if keep.mean() < 0.5:
            break
        acc = (pred[keep] == y[keep]).mean()
        if acc >= 0.95:
            return {"tau": round(float(tau), 3), "coverage": round(float(keep.mean()), 3), "accuracy_kept": round(float(acc), 4)}
    tau = float(np.percentile(top, 20))
    keep = top >= tau
    return {"tau": round(tau, 3), "coverage": round(float(keep.mean()), 3),
            "accuracy_kept": round(float((pred[keep] == y[keep]).mean()), 4)}


def _grid(fast: bool):
    if fast:
        return [(10, None, 1.0), (10, "balanced", 0.5)]
    return [(C, cw, zw) for C in (3, 10, 30) for cw in (None, "balanced") for zw in (1.0, 0.5)]


def rolling_cv(dev: pd.DataFrame, C: float, cw, zw: float, n_splits: int = 4, min_train: int = 1500,
               min_test: int = 50) -> dict:
    """Forward-chaining validation over time, on the training rows only.

    Fold i fits on every row older than its test slice and scores the next CRM slice. Every scored row
    therefore comes from a period the model has never seen, which is the same shape as deployment.

    Random K-fold is deliberately not used anywhere in this project (docs/BUILD.md T5). The test set is
    the most recent requests, so a random split trains on recent rows and grades on old ones and reads
    high. This walks forward instead.

    Nothing here reads the validation or holdout slices: it reports stability of the training era only.
    """
    dev = dev.sort_values("ts")
    crm = dev[dev.source == CURRENT_SOURCE]
    n = len(crm)
    if n < min_train or n < n_splits * min_test:
        return {"n_splits": 0, "note": f"only {n} CRM training rows; need at least {max(min_train, n_splits * min_test)}"}
    # iloc is 0-based and n is out of bounds, so the last edge clamps to the final row.
    edges = [crm.ts.iloc[min(int(n * k / n_splits), n - 1)] for k in range(n_splits + 1)]
    folds = []
    for i in range(n_splits):
        te = crm[crm.ts >= edges[i]] if i == n_splits - 1 else crm[(crm.ts >= edges[i]) & (crm.ts < edges[i + 1])]
        tr_part = dev[dev.ts < edges[i]]
        if len(te) < min_test or len(tr_part) < min_train:
            continue
        pipe = fit(tr_part, C, cw, zw)
        s = score(te.final_team, pipe.predict(te))
        s.update({"train_rows": int(len(tr_part)), "test_rows": int(len(te)),
                  "from": str(te.ts.min())[:10], "to": str(te.ts.max())[:10]})
        folds.append(s)
    if not folds:
        return {"n_splits": 0, "note": "no fold had enough rows to score"}
    accs = [f["accuracy"] for f in folds]
    return {"n_splits": len(folds), "mean_accuracy": round(float(np.mean(accs)), 4),
            "min_accuracy": round(float(np.min(accs)), 4), "max_accuracy": round(float(np.max(accs)), 4),
            "mean_macro_f1": round(float(np.mean([f["macro_f1"] for f in folds])), 4), "folds": folds}


def train(settings: Settings, ds: Dataset, log: Callable[[str], None] = print, holdout_frac: float = 0.15, val_frac: float = 0.15) -> dict:
    tr = ds.train
    closed = tr[tr.final_team.notna()].copy()
    crm = closed[closed.source == CURRENT_SOURCE].sort_values("ts")
    if len(crm) < MIN_CLOSED_CRM:
        raise DataValidationError(
            f"Only {len(crm)} closed '{CURRENT_SOURCE}' requests with a known final team; need at least {MIN_CLOSED_CRM} for a time-based evaluation.",
            {"closed_total": int(len(closed)), "closed_crm": int(len(crm))})
    n = len(crm)
    t_hold = crm.ts.iloc[int(n * (1 - holdout_frac))]
    t_val = crm.ts.iloc[int(n * (1 - holdout_frac - val_frac))]
    hold = closed[closed.ts >= t_hold]
    val = closed[(closed.ts >= t_val) & (closed.ts < t_hold)]
    dev = closed[closed.ts < t_val]
    if min(len(hold), len(val), len(dev)) < 20:
        raise DataValidationError("Time split left fewer than 20 rows in dev, validation or holdout.",
                                  {"dev": len(dev), "val": len(val), "holdout": len(hold)})
    info = {"rows_train": int(len(tr)), "rows_closed": int(len(closed)), "rows_unclosed": int(len(tr) - len(closed)),
            "dev": int(len(dev)), "val": int(len(val)), "holdout": int(len(hold)),
            "val_from": str(t_val), "holdout_from": str(t_hold), "canonical_teams": ds.canon}
    log(f"split: {info}")

    best = None
    for C, cw, zw in _grid(settings.fast):
        pipe = fit(dev, C, cw, zw)
        s = score(val.final_team, pipe.predict(val))
        log(f"grid C={C} class_weight={cw} zoho_weight={zw}: {s}")
        if best is None or s["macro_f1"] > best[0]["macro_f1"]:
            best = (s, dict(C=C, cw=cw, zw=zw), pipe)
    val_score, params, pipe_dev = best
    gate = pick_gate(val.final_team, pipe_dev.predict_proba(val), pipe_dev.classes_)
    # Reporting only. Uses training rows exclusively; it cannot change the model, the gate or the holdout.
    cv = rolling_cv(dev, params["C"], params["cw"], params["zw"])
    log(f"rolling-origin CV (training rows only): mean acc {cv.get('mean_accuracy')} over {cv.get('n_splits')} folds")

    # Holdout is scored once, with the model fit on dev + val.
    pipe_eval = fit(pd.concat([dev, val]), **params)
    ph = pipe_eval.predict(hold)
    yh = hold.final_team.values
    seen = hold.text.isin(set(dev.text) | set(val.text)).values
    mon = hold.ts.dt.to_period("M").astype(str).values
    proba_h = pipe_eval.predict_proba(hold)
    flagged = proba_h.max(1) < gate["tau"]
    holdout = {
        "model": {**score(yh, ph), "accuracy_ci95": boot_ci(yh, ph)},
        "bot_vs_final": {**score(yh, hold.bot_team.values), "accuracy_ci95": boot_ci(yh, hold.bot_team.values)},
        "model_agreement_with_bot_label": score(hold.bot_team.values, ph),
        "model_accuracy_seen_text": round(float((ph[seen] == yh[seen]).mean()), 4) if seen.any() else None,
        "model_accuracy_unseen_text": round(float((ph[~seen] == yh[~seen]).mean()), 4) if (~seen).any() else None,
        "share_unseen_text": round(float((~seen).mean()), 4),
        "by_month_accuracy": {k: round(float((ph[mon == k] == yh[mon == k]).mean()), 4) for k in sorted(set(mon))},
        "avg_transfers_logged": round(float(hold.transfers.mean()), 4) if hold.transfers.notna().any() else None,
        "wrong_first_touch_rate": {"bot": round(float((hold.bot_team.values != yh).mean()), 4),
                                   "model": round(float((ph != yh).mean()), 4)},
        "gate_on_holdout": {
            "share_flagged_for_human": round(float(flagged.mean()), 4),
            "accuracy_when_not_flagged": round(float((ph[~flagged] == yh[~flagged]).mean()), 4) if (~flagged).any() else None,
            "accuracy_when_flagged": round(float((ph[flagged] == yh[flagged]).mean()), 4) if flagged.any() else None,
        },
    }
    art = settings.artifact_dir
    art.mkdir(parents=True, exist_ok=True)
    pd.crosstab(pd.Series(yh, name="actual"), pd.Series(ph, name="predicted")).to_csv(art / "confusion_holdout.csv")
    err = hold.assign(pred=ph, conf=proba_h.max(1))
    err = err[err.pred != err.final_team].sort_values("conf", ascending=False)
    err[["request_id", "created_at_ist", "channel", "product_family", "warranty_status", "text",
         "final_team", "pred", "conf", "bot_team"]].to_csv(art / "errors_holdout.csv", index=False)
    report = classification_report(yh, ph, output_dict=True, zero_division=0)

    # Production model: every closed row.
    final = fit(closed, **params)
    missing = sorted(set(ds.canon) - set(final.classes_))
    if missing:
        log(f"WARNING: teams never seen as a final team, the model cannot predict them: {missing}")
    bundle = {"pipe": final, "tau": gate["tau"], "teams": list(final.classes_), "canon": ds.canon, "team_map": ds.team_map,
              "products": sorted(tr.product_family.unique()), "warranties": sorted(tr.warranty_status.unique()),
              "channels": sorted(tr.channel.unique()), "trained_rows": int(len(closed)),
              "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "params": params}
    joblib.dump(bundle, settings.model_path, compress=3)

    test_info = None
    if ds.test is not None:
        te = ds.test
        pred = final.predict(te)
        proba_t = final.predict_proba(te)
        id_col, team_col = ds.sample_cols[0], ds.sample_cols[1]
        pd.DataFrame({id_col: te.request_id.values, team_col: pred}).to_csv(settings.predictions_path, index=False)
        pd.DataFrame({"request_id": te.request_id.values, "team": pred, "confidence": proba_t.max(1).round(4),
                      "flagged_for_human": proba_t.max(1) < gate["tau"]}).to_csv(art / "predictions_with_confidence.csv", index=False)
        test_info = {"rows": int(len(te)), "predicted_distribution": pd.Series(pred).value_counts().to_dict(),
                     "flagged_share": round(float((proba_t.max(1) < gate["tau"]).mean()), 4)}
        log(f"wrote {settings.predictions_path} ({len(te)} rows)")
    else:
        log("No test file found: model trained, predictions.csv not written.")

    metrics = {"trained_at": bundle["trained_at"], "input_files": ds.report.files_used, "split": info,
               "chosen_params": params, "validation": val_score, "gate_from_validation": gate,
               "cv_rolling": cv, "holdout": holdout, "per_class_holdout": report, "test": test_info}
    settings.metrics_path.write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")
    settings.state_path.write_text(json.dumps({"fingerprint": ds.discovery.fingerprint, "trained_at": bundle["trained_at"]}), encoding="utf-8")
    log(f"holdout accuracy model={holdout['model']['accuracy']} bot={holdout['bot_vs_final']['accuracy']}")
    return metrics
