"""The committed model must not carry customer identifiers.

This exists because it already happened once. A TF-IDF pipeline persists its vocabulary_, the
scikit-learn default token pattern admits digits, and 119 customer numbers (order IDs
KO2xxxxxx and warranty serials SR#####) were learned into artifacts/model.joblib -- which shipped
in a public repository and made a .gitignore claim of "no identifiers" false.

The claim is checkable in a few lines, so it is checked in CI rather than asserted in a comment.
If this test fails, do not delete it: the fix is in kestrel/ml/model.py TOKEN_PATTERN.
"""
from __future__ import annotations

import re

import joblib

from kestrel.settings import Settings


def _vocabulary(model_path):
    """Every token string reachable from the persisted pipeline.

    Uses `named_transformers_` (fitted) and NOT `.transformers` (spec only). The spec returns
    unfitted clones that carry no vocabulary_, so a guard written against it collects nothing
    and passes silently -- worse than having no guard at all. That bug was in the first draft of
    this file, which is why the accessor is called out here.
    """
    bundle = joblib.load(model_path)
    pre = bundle["pipe"].named_steps["pre"]
    tokens = set()
    for _name, vec in pre.named_transformers_.items():
        if vec is None or isinstance(vec, str) or not hasattr(vec, "vocabulary_"):
            continue
        tokens.update(vec.vocabulary_.keys())
    return tokens


def test_word_vectoriser_has_no_numeric_tokens():
    """The WORD vectoriser must contain no digit-bearing token.

    Scoped to 'w' on purpose. The char_wb vectoriser legitimately produces digit fragments
    (' 1', '10', '26') -- 3,600-odd of them -- and a blanket "no digits anywhere" assertion
    fails on those while catching nothing. Whole identifiers only ever survived as word tokens.
    """
    s = Settings.from_env()
    if not s.model_path.exists():
        return  # nothing committed yet; the pipeline tests cover training

    bundle = joblib.load(s.model_path)
    w = bundle["pipe"].named_steps["pre"].named_transformers_["w"]
    with_digits = sorted(t for t in w.vocabulary_ if any(ch.isdigit() for ch in t))
    assert with_digits == [], (
        f"word vocabulary contains {len(with_digits)} token(s) with digits, e.g. {with_digits[:5]}. "
        "Order IDs and warranty serials must never reach the committed model. "
        "Fix the token_pattern in kestrel/ml/model.py, then retrain."
    )


def test_no_whole_customer_identifier_is_recoverable():
    """Cross-check the whole vocabulary against identifier shapes, char fragments included."""
    s = Settings.from_env()
    if not s.model_path.exists():
        return
    tokens = _vocabulary(s.model_path)
    whole = sorted(t for t in tokens if re.fullmatch(r"(?:ko\d{7}|sr\d{5})", t.strip(), re.I))
    assert whole == [], (
        f"{len(whole)} whole customer identifier(s) recoverable from the committed model: {whole[:5]}"
    )


def test_committed_model_matches_real_customer_identifiers():
    """Strongest form: cross-check against identifiers actually present in the source data."""
    s = Settings.from_env()
    csv = s.input_dir / "train.csv"
    if not s.model_path.exists() or not csv.exists():
        return  # no data in the public repo; the shape checks above still apply

    import pandas as pd

    text = " ".join(pd.read_csv(csv, usecols=["request_text"]).request_text.dropna().astype(str))
    real = {x.lower() for x in re.findall(r"KO\d{7}", text)} | {x.lower() for x in re.findall(r"SR\d{5}", text)}
    leaked = sorted(_vocabulary(s.model_path) & real)
    assert leaked == [], (
        f"{len(leaked)} real customer identifier(s) are recoverable from the committed model, "
        f"e.g. {leaked[:5]}. ops-policy section 10 forbids publishing this data."
    )