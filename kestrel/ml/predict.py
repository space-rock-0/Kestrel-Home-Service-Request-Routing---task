from __future__ import annotations

import threading

import joblib
import numpy as np
import pandas as pd
import scipy.sparse as sp

from ..data.cleaning import add_meta, clean_text
from ..errors import ModelNotReadyError
from ..settings import Settings
from .rules import load_rules, match_rule

PRETTY = {"p_": "product", "w_": "warranty", "c_": "channel"}
CLARIFY = ("Ask the customer: which product, and is it (a) not working, (b) needs a filter or part, "
           "(c) installation, or (d) a payment or refund question?")


def _norm(v) -> str:
    v = (v or "").strip().lower()
    return v or "unknown"


class Router:
    """Loads the trained bundle and reloads it when model.joblib changes on disk."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._lock = threading.Lock()
        self._mtime = None
        self.b = None
        self.pipe = None
        self.tau = 0.5
        self.rules = []

    def ensure_fresh(self) -> None:
        path = self.settings.model_path
        if not path.exists():
            self.b = self.pipe = self._mtime = None
            raise ModelNotReadyError(
                "No trained model yet. Add your Excel files to data/input/ and run the pipeline "
                "(Pipeline tab, or `python -m kestrel train`).")
        m = path.stat().st_mtime_ns
        if m != self._mtime:
            with self._lock:
                self.b = joblib.load(path)
                self.pipe, self.tau = self.b["pipe"], self.b["tau"]
                self.rules = load_rules(self.settings.rules_file)
                self._mtime = m

    @property
    def ready(self) -> bool:
        try:
            self.ensure_fresh()
            return True
        except ModelNotReadyError:
            return False

    def _explain(self, df: pd.DataFrame, team: str, k: int = 5):
        pre, clf = self.pipe.named_steps["pre"], self.pipe.named_steps["clf"]
        X = pre.transform(df)
        names = pre.get_feature_names_out()
        j = list(clf.classes_).index(team)
        row = sp.csr_matrix(X.multiply(clf.coef_[j]))
        words, ctx = [], []
        for o in np.argsort(-row.data):
            if row.data[o] <= 0:
                break
            n = names[row.indices[o]]
            if n.startswith("w__") and len(words) < k:
                words.append(n[3:])
            elif n.startswith("m__") and n[3:5] in PRETTY and len(ctx) < 2:
                ctx.append(f"{PRETTY[n[3:5]]} = {n[5:].replace('_', ' ')}")
        return words, ctx

    def route(self, rec: dict) -> dict:
        self.ensure_fresh()
        warnings = []
        text = clean_text(rec.get("request_text", ""))
        if not text:
            warnings.append("No request text: the decision uses product, warranty and channel only.")
        row = {"text": text, "product_family": _norm(rec.get("product_family")),
               "warranty_status": _norm(rec.get("warranty_status")), "channel": _norm(rec.get("channel"))}
        for k, allowed in (("product_family", "products"), ("warranty_status", "warranties"), ("channel", "channels")):
            if row[k] not in self.b[allowed]:
                if row[k] != "unknown":
                    warnings.append(f"Unrecognised {k} '{row[k]}': treated as unknown.")
                row[k] = "unknown"
        df = add_meta(pd.DataFrame([row]))
        p = self.pipe.predict_proba(df)[0]
        order = p.argsort()[::-1]
        classes = self.pipe.classes_
        team, conf = str(classes[order[0]]), float(p[order[0]])
        alts = [{"team": str(classes[i]), "probability": round(float(p[i]), 3)} for i in order[1:3]]
        reasons = [f"Routed to {team}: model confidence {conf:.0%}; next best {alts[0]['team']} {alts[0]['probability']:.0%}."]
        words, _ = self._explain(df, team)
        if words:
            reasons.append("Phrases that pointed here: " + ", ".join(f"'{w}'" for w in words) + ".")
        reasons.append(f"Context read: product {row['product_family']}, warranty {row['warranty_status']}, channel {row['channel']}.")
        rule = match_rule(dict(row), self.rules)
        rule_out = None
        if rule:
            team, rule_out = rule["team"], {"id": rule["id"], "source": rule.get("source")}
            reasons.append(f"Policy rule {rule['id']} applied ({rule.get('source')}).")
        flag = conf < self.tau and not rule
        if flag:
            reasons.append(f"Confidence {conf:.0%} is below the {self.tau:.0%} line: a person should confirm before routing.")
        return {"request_id": rec.get("request_id"), "team": team, "confidence": round(conf, 3), "alternatives": alts,
                "needs_clarification": flag, "clarifying_question": CLARIFY if flag else None, "reasons": reasons,
                "rule": rule_out, "warnings": warnings, "model_trained_at": self.b["trained_at"]}

    def route_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        """Batch routing for a prepared frame (text, meta columns present)."""
        self.ensure_fresh()
        proba = self.pipe.predict_proba(df)
        return pd.DataFrame({"request_id": df.request_id.values, "team": self.pipe.classes_[proba.argmax(1)],
                             "confidence": proba.max(1).round(4), "flagged_for_human": proba.max(1) < self.tau})
