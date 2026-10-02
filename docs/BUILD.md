> **Note for this repository.** This plan was written before the project was built. The runnable code now lives in the `kestrel/` package, and the code blocks below are superseded by it. Command map:
>
> | BUILD.md | This project |
> |---|---|
> | `data/` | `data/input/` (Excel or CSV) |
> | `python -m scripts.audit` | `python -m kestrel audit` |
> | `python -m src.train` | `python -m kestrel train` |
> | `python -m scripts.validate_submission` | `python -m kestrel check` |
> | `python -m scripts.golden` | `python -m kestrel run golden` |
> | `python -m scripts.numbers --transfer-cost-inr N` | `python -m kestrel run numbers --transfer-cost-inr N` |
> | `uvicorn src.service:app` | `python -m kestrel serve` |
> | `/route`, `/meta` | `/api/route`, `/api/meta` |
> | `python -m scripts.make_synthetic` | test-only helper in `tests/synth.py` |
> | `artifacts/metrics.json` fields | unchanged |

# BUILD.md — Kestrel Home Service-Request Routing (Variant B)

**Version:** v2 (council-amended) · **Author voice:** senior FDE · **Window:** 1d 16h ≈ 40 h wall-clock, plan for ~30 h of work + 10 h buffer

> **Read this first — what this document is and is not**
> I was given the brief, email thread and README only. `train.csv`, `test_unlabelled.csv`, `resolution_log.csv`, `teams.csv` and `ops-policy.pdf` were **not** in the upload, so this file contains **no fabricated numbers**. Every number in the memo/form is produced by a script in Phase 9–10 and pasted in. Anything shown as `{{like_this}}` is intentionally blank until the script prints it. All code below was extracted from this file and smoke-tested end-to-end on synthetic data with the same columns (see Phase 14), (the test caught and fixed two real bugs: pandas silently turning mixed-format timestamps into NaT, and a confidence gate that flagged nothing). It has **not** seen your real data: every phase therefore has a **gate** that tells you what to do when reality differs.

---

## 0. The one-paragraph plan

Do **not** train a model to copy the bot's `team_label` and then claim 90% agreement. The bot is the thing being replaced, and the email thread (Meenal) proves it is wrong in systematic ways (installation/repair payments → Billing; purifier breakdowns → Consumables; "call me about my purifier" → unroutable). The scorer uses "outcomes you do not have" — for closed tickets that is where the request **actually ended up** (`final_team` in `resolution_log.csv`). So: target = `final_team` (mapped to current team names), validated **by time** on CRM-era rows, compared against the bot on the same rows, shipped as a small CPU-only scikit-learn model behind one FastAPI endpoint + one HTML page, **zero paid calls**, with a confidence flag that sends the genuinely ambiguous pile to a human instead of guessing. The memo answers "can we switch the bot off?" with a number from the data and a gated rollout, not with "yes, 90%".

---

## 1. Deliverables → files → phase

| # | Brief item | File / location | Built in | Done when |
|---|---|---|---|---|
| 1 | `predictions.csv` + expected score written in form | `predictions.csv`, form Q2 | Ph 7, 9 | validator passes; expectation written **before** submit |
| 2 | Working service (endpoint + screen), clean machine, no key | `src/service.py`, `static/index.html`, README | Ph 8, 14 | fresh venv → 3 commands → page works |
| 3 | Evidence + failure rate | `artifacts/metrics.json`, `EVIDENCE.md`, `artifacts/errors_holdout.csv` | Ph 9 | numbers + ≥50 hand-read errors in a taxonomy |
| 4 | One-page memo to Ritu | `MEMO.md` (+ PDF/Docx if you prefer) | Ph 11 | a non-technical person can act on it |
| 5 | ≤3-min screen recording | Drive link | Ph 12 | tried / changed / threw away, no slides |
| 6 | `submission-form.md` | `submission-form.md` | Ph 13 | no empty field |
| 7 | Public GitHub repo (with data files) + Drive link | repo URL | Ph 13 | cloned fresh, runs |

---

## 2. The traps in this pack (and what we do about each)

| # | Trap | Evidence in the pack | Decision |
|---|---|---|---|
| T1 | **Label ≠ truth.** `team_label` = what the vendor bot did at creation | Tanmay's email; Meenal's three complaints | Train and score on `final_team`; keep `team_label` only as the **baseline to beat** and for a bot-error report |
| T2 | **"90% match" bar is the wrong bar** | Ritu's email; brief says scoring is on hidden *outcomes* | Report both: agreement with bot labels, and correctness vs `final_team`. Memo explains why they differ |
| T3 | **Renamed teams** — two teams appear under old and new names | Tanmay; `teams.csv.renamed_to` | Map to one canonical name per team; canonical = name used in the **latest 60 days** of train (test is the most recent data); gate prints it for your confirmation; validator rejects old names |
| T4 | **Legacy Zoho rows**: mojibake text, unconverted resolution times, different era | README `source`; Tanmay | `ftfy` repair; never use `resolved_at`/durations as model inputs; **never use `source` as a feature** (era shortcut); optional down-weight chosen on validation; holdout is **CRM-only** |
| T5 | **Time drift / leakage** — test = most recent requests | README | Time-ordered split only. No random K-fold anywhere |
| T6 | **Right-censoring** — latest train rows have no resolution | Tanmay ("only for closed requests") | Train only on closed rows; report closed-rate by month; flag that the surviving recent rows are biased toward easy tickets → haircut on expected score |
| T7 | **Resolution-log fields are post-hoc** (`first_team`, `final_team`, `transfers`, `resolved_at`) | Not available at routing time | Used for target and evaluation only — never features |
| T8 | **Ambiguous pile** ("please call me about my purifier") | Meenal | No model can fix missing information. Confidence gate → `needs_clarification` + a suggested question. `predictions.csv` still gets a best-guess team (format requires one of seven) |
| T9 | **Cost**: Farhan wants a written monthly run cost, no per-request AI bill | Farhan | No paid API anywhere in the product. Cost = ₹0 per prediction; hosting is the only cost; show arithmetic |
| T10 | **"Busiest team" for headcount** | Ritu | Rank by **final_team** workload and by touches (1 + transfers), not by bot queue. Handling time isn't in the pack → give ranking + share, **do not invent FTE numbers** |
| T11 | **Policy PDF may override the data** (rules, costs, team changes, systems) | Pack listing | Phase 2 extracts rules into `rules.json`; a rule is switched on only if history agrees with it ≥95% on closed CRM rows; otherwise logged as "policy vs practice conflict" |
| T12 | **Public repo contains data files** | Brief | PII scan in Phase 1; if phones/emails/names exist, say so in the form (Q5) and mask them in the committed copy only if the brief permits; otherwise commit as supplied and flag the risk |
| T13 | **The "90%" might be unreachable honestly** | — | Never tune against the holdout to hit a number. State the achieved number and its interval |

---

## 3. Decision log (decide, write down, move on)

| ID | Decision | Why | Revisit if |
|---|---|---|---|
| D1 | Target = `final_team` (canonical names) | Scorer uses outcomes; bot labels encode the bot's errors | `resolution_log.csv` `final_team` is mostly blank or equals `first_team` always (then log is useless → fall back to bot labels + say so loudly) |
| D2 | Model = TF-IDF (word 1–2 + char 2–5) + product/warranty/channel tokens → multinomial Logistic Regression | Small, CPU-only, explainable per-word, trains in minutes, artifact < 50 MB, no downloads at runtime | A local embedding model beats it by **≥1.0 pt macro-F1 on validation** *and* installs offline (otherwise discard) |
| D3 | No LLM/API in the product | Cost determinism (Farhan), clean-machine start, reproducibility | Never for this submission; mention as discarded option |
| D4 | Split: dev (older) / val (middle 15% of CRM closed) / holdout (last 15% of CRM closed), by time | Mirrors "test = most recent" | CRM closed rows < 400 → use 10%/10% and say so |
| D5 | Holdout touched once, after all choices | Otherwise the expected-score claim is meaningless | — |
| D6 | Exclude unclosed train rows from training | No outcome label; bot label would re-import T1 | If > 25% of recent rows are unclosed, also report a bot-label-trained variant for comparison |
| D7 | Exact-duplicate texts are **kept** in training; accuracy also reported on the **unseen-text** subset | Templated texts will recur in test; no customer ID exists to group on; unseen-text accuracy is the conservative bound | A customer/phone column exists → group-split on it |
| D8 | Confidence gate threshold chosen on **validation**: smallest τ ≥ 0.50 giving ≥95% accuracy on kept rows with ≥50% coverage, else the 20th percentile (floor 0.50 because with 7 teams a top probability below 0.5 is a toss-up) | Gives ops a dial, not a guess | — |
| D9 | Rules layer is data (`rules.json`), default empty/disabled | Policy may be explicit; code shouldn't hide it | A rule fails the 95% agreement audit → leave disabled, report |
| D10 | Rollout recommendation = 2-week **shadow mode**, then confidence-gated auto-routing, low-confidence to a human triage desk; bot stays until the gate passes | Switching off a bot on a point estimate is how you get an incident | Gate numbers in §9 |
| D11 | `source` banned as a feature | Perfectly separates eras and label conventions; test is all-CRM | — |
| D12 | Predict the best-guess team for **every** test row | Format demands one of seven | — |
| D13 | Freeze rule: baseline submission exists by hour ~10; no new model experiments after hour 22 | A submission must always exist | — |
| D14 | Pin dependency versions at the end (`pip freeze` subset) | Clean-machine start | — |

---

## 4. Timeline (hours are budgets, not wishes)

| Phase | Name | Budget | Cumulative | Hard gate before moving on |
|---|---|---|---|---|
| 0 | Setup, freeze decisions | 1.0 | 1 | repo created, this file committed |
| 1 | Data forensics | 3.0 | 4 | `artifacts/audit.txt` read in full |
| 2 | Policy + teams extraction | 2.0 | 6 | canonical team list confirmed; rules drafted |
| 3 | Target + split | 1.5 | 7.5 | split sizes printed, CRM closed rows ≥ 400 |
| 4 | Baselines | 1.5 | 9 | bot-vs-final number known |
| 7a | **Checkpoint submission** | 1.0 | 10 | `predictions.csv` validates |
| 5 | Modelling | 3.5 | 13.5 | one chosen config, rest discarded & logged |
| 6 | Error analysis + rules | 3.0 | 16.5 | ≥50 errors hand-labelled |
| 8 | Service + UI | 3.5 | 20 | endpoint + screen run locally |
| 9 | Evidence pack | 2.5 | 22.5 | `EVIDENCE.md` done — **model frozen** |
| 10 | Cost + numbers | 1.0 | 23.5 | `scripts/numbers.py` output saved |
| 11 | Memo | 1.5 | 25 | read aloud by someone non-technical |
| 12 | Recording | 1.5 | 26.5 | ≤3:00 |
| 13 | Form + repo + Drive | 2.0 | 28.5 | no empty form field |
| 14 | Clean-machine test + final freeze | 1.5 | 30 | fresh venv passes |
| — | Buffer | 10 | 40 | — |

---

## 5. Phase-by-phase build

### Phase 0 — Setup (1 h)

- [ ] `git init kestrel-routing && cd kestrel-routing`
- [ ] Folders: `data/ src/ scripts/ static/ tests/ artifacts/`
- [ ] Copy the five data files + `sample_submission.csv` + `ops-policy.pdf` into `data/` (keep untouched — never edit raw files; Tanmay didn't either)
- [ ] Python ≥ 3.10; `python -m venv .venv && source .venv/bin/activate`
- [ ] Create `requirements.txt` (below), `pip install -r requirements.txt`
- [ ] Create `hours.log` — append a line each session (`date, hours, what`). Q "Honest hours" is read from here.
- [ ] Commit this file as `BUILD.md`.

`requirements.txt`
<!-- file: requirements.txt -->
```text
pandas>=2.0
numpy>=1.24
scikit-learn>=1.3
scipy>=1.10
joblib>=1.3
ftfy>=6.1
fastapi>=0.110
uvicorn>=0.27
httpx>=0.27
pytest>=8.0
```

`src/__init__.py`
<!-- file: src/__init__.py -->
```python
```

`src/config.py`
<!-- file: src/config.py -->
```python
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("KESTREL_DATA", ROOT / "data"))
ART = Path(os.environ.get("KESTREL_ART", ROOT / "artifacts"))
ART.mkdir(parents=True, exist_ok=True)
ZOHO_CUTOFF = "2025-10-01"
```

### Phase 1 — Data forensics (3 h)

Goal: know every way the data can lie before modelling.

- [ ] Add `src/clean.py` and `src/data.py` (below), then `scripts/audit.py` and run `python -m scripts.audit`
- [ ] Read `artifacts/audit.txt` top to bottom. Answer in `NOTES.md`:
  - [ ] Does `created_at_ist` parse? (`NaT` count). If > 2%, `data.py` auto-tries day-first; confirm which won.
  - [ ] How many rows are `legacy_zoho` vs `crm`? Date ranges? Is the test 100% `crm`?
  - [ ] Mojibake rate by source before/after cleaning (must be ~0 after).
  - [ ] Empty `request_text` rate by channel (IVR?). Non-English/Hinglish share (eyeball 30 rows).
  - [ ] Closed rate by month (censoring, T6).
  - [ ] Bot-vs-final agreement overall and by month (this is the **number that reframes the whole project**).
  - [ ] Bot team × final team crosstab — find the Billing and Consumables leaks Meenal described, with counts.
  - [ ] `resolved_at` for Zoho: negative durations? ×1000 units? 5.5 h offset? Write down what is wrong; do not "fix" unless cheap — we don't use it.
  - [ ] Exact-duplicate texts train↔test count.
  - [ ] Any final/first team names not in the canonical set.
- [ ] **PII scan** (T12): grep for `\b\d{10}\b`, `@`, `+91`. Record counts in `NOTES.md`.
- [ ] **Gate:** if `final_team` is blank for > 60% of train rows, D1 fails → read D1 "revisit" and tell Ritu in the memo.

<!-- file: src/clean.py -->
```python
import re
import unicodedata

import pandas as pd
from ftfy import fix_text


def clean_text(s) -> str:
    """Repair mojibake (legacy Zoho), normalise unicode/whitespace, lowercase."""
    if not isinstance(s, str):
        return ""
    s = fix_text(s)
    s = unicodedata.normalize("NFKC", s).lower()
    return re.sub(r"\s+", " ", s).strip()


def add_meta(df: pd.DataFrame) -> pd.DataFrame:
    """Token column carrying product/warranty/channel and their cross (no `source` — era shortcut)."""
    df = df.copy()
    p = df["product_family"].str.replace(r"\s+", "_", regex=True)
    w = df["warranty_status"].str.replace(r"\s+", "_", regex=True)
    c = df["channel"].str.replace(r"\s+", "_", regex=True)
    df["meta"] = "p_" + p + " w_" + w + " c_" + c + " pw_" + p + "_" + w
    return df


def build_team_map(teams: pd.DataFrame, train: pd.DataFrame):
    """old/new name -> canonical name. Canonical = the name used most in the latest 60 days of train.team_label."""
    ts = pd.to_datetime(train["created_at_ist"], errors="coerce")
    recent = train.loc[ts >= ts.max() - pd.Timedelta(days=60), "team_label"].str.strip().value_counts()
    m = {}
    for _, r in teams.iterrows():
        a = str(r["team"]).strip()
        b = r.get("renamed_to")
        b = str(b).strip() if pd.notna(b) and str(b).strip() else None
        if b and b != a:
            canon = b if recent.get(b, 0) >= recent.get(a, 0) else a
            m[a] = m[b] = canon
    for _, r in teams.iterrows():
        a = str(r["team"]).strip()
        m.setdefault(a, a)
    return m, sorted(set(m.values()))
```

<!-- file: src/data.py -->
```python
import numpy as np
import pandas as pd

from .clean import add_meta, build_team_map, clean_text


def _rd(d, name):
    return pd.read_csv(d / name, dtype=str, keep_default_na=False,
                       encoding="utf-8-sig", encoding_errors="replace")


def parse_ts(s: pd.Series) -> pd.Series:
    """format='mixed' parses each row on its own (pandas otherwise infers ONE format from row 1 and NaT-s the rest)."""
    a = pd.to_datetime(s, errors="coerce", format="mixed")
    if a.isna().mean() > 0.02:
        b = pd.to_datetime(s, errors="coerce", format="mixed", dayfirst=True)
        if b.isna().sum() < a.isna().sum():
            return b
    return a


def load(data_dir):
    tr, te, res, teams = (_rd(data_dir, n) for n in
                          ("train.csv", "test_unlabelled.csv", "resolution_log.csv", "teams.csv"))
    tmap, canon = build_team_map(teams, tr)
    canon_of = lambda s: tmap.get(str(s).strip(), str(s).strip())

    for df in (tr, te):
        df["text"] = df["request_text"].map(clean_text)
        df["ts"] = parse_ts(df["created_at_ist"])
        for c in ("product_family", "warranty_status", "channel"):
            df[c] = df[c].str.strip().str.lower().replace("", "unknown")
        df["source"] = df["source"].str.strip().str.lower()

    res = res.drop_duplicates("request_id", keep="last").copy()
    for c in ("first_team", "final_team"):
        res[c] = res[c].map(lambda s: canon_of(s) if str(s).strip() else np.nan)
    res["transfers"] = pd.to_numeric(res["transfers"], errors="coerce")
    res["resolved_ts"] = parse_ts(res["resolved_at"])

    tr = tr.merge(res[["request_id", "first_team", "final_team", "transfers", "resolved_ts"]],
                  on="request_id", how="left")
    tr["bot_team"] = tr["team_label"].map(canon_of)
    return add_meta(tr), add_meta(te), tmap, canon
```

<!-- file: scripts/__init__.py -->
```python
```

<!-- file: scripts/audit.py -->
```python
import re

import pandas as pd

from src.config import ART, DATA
from src.data import load

MOJI = re.compile(r"â€|Ã.|Â|\ufffd", re.I)


def main():
    tr, te, tmap, canon = load(DATA)
    L = []

    def P(*a):
        L.append(" ".join(str(x) for x in a))

    P("rows train/test:", len(tr), len(te))
    P("canonical teams:", canon)
    P("rename map:", tmap)
    P("unparsed created_at train/test:", int(tr.ts.isna().sum()), int(te.ts.isna().sum()))
    P("date range train:", tr.ts.min(), "->", tr.ts.max(), "| test:", te.ts.min(), "->", te.ts.max())
    P("\nsource train:\n" + tr.source.value_counts().to_string())
    P("\nsource test:\n" + te.source.value_counts().to_string())
    P("\nraw team_label values:\n" + tr.team_label.value_counts().to_string())
    P("\nfinal_team values:\n" + tr.final_team.value_counts(dropna=False).to_string())
    P("\nmojibake rate by source (raw):\n" +
      tr.groupby("source").request_text.apply(lambda s: s.map(lambda x: bool(MOJI.search(x))).mean()).to_string())
    P("mojibake after cleaning:", float(tr.text.map(lambda x: bool(MOJI.search(x))).mean()))
    P("\nempty text rate by channel:\n" + tr.assign(e=tr.text.eq("")).groupby("channel").e.mean().to_string())

    m = tr.ts.dt.to_period("M").astype(str)
    closed = tr.final_team.notna()
    P("\nclosed rate by month:\n" + closed.groupby(m).mean().round(3).to_string())
    c = tr[closed]
    P("\nbot_team == final_team overall:", round(float((c.bot_team == c.final_team).mean()), 4))
    P("by month:\n" + (c.bot_team == c.final_team).groupby(m[closed]).mean().round(3).to_string())
    P("\nbot_team (rows) x final_team (cols):\n" + pd.crosstab(c.bot_team, c.final_team).to_string())
    P("\ntransfers distribution:\n" + c.transfers.value_counts(dropna=False).sort_index().to_string())
    hrs = (c.resolved_ts - c.ts).dt.total_seconds() / 3600
    P("\nresolution hours by source (describe):\n" + hrs.groupby(c.source).describe().round(1).to_string())
    P("negative durations by source:\n" + (hrs < 0).groupby(c.source).sum().to_string())
    P("\nexact duplicate texts train<->test:", int(te.text.isin(set(tr.text)).sum()), "of", len(te))
    P("duplicate request_id in train:", int(tr.request_id.duplicated().sum()))
    recent = tr[tr.ts >= tr.ts.max() - pd.Timedelta(days=60)]
    for col in ("product_family", "channel", "warranty_status"):
        P(f"\n{col}: test vs last-60-days train (share)\n" +
          pd.concat([te[col].value_counts(normalize=True).rename("test"),
                     recent[col].value_counts(normalize=True).rename("train_recent")], axis=1).round(3).to_string())
    P("\nfinal/first team names outside canonical set:",
      sorted((set(c.final_team.dropna()) | set(c.first_team.dropna())) - set(canon)))
    (ART / "audit.txt").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
```

### Phase 2 — Policy + teams extraction (2 h)

- [ ] `pip install pypdf` (dev only) → `python -c "from pypdf import PdfReader; print('\n'.join(p.extract_text() for p in PdfReader('data/ops-policy.pdf').pages))" > artifacts/policy.txt`; if text is empty, it's scanned → read manually.
- [ ] In `NOTES.md` extract, **with page/section references**: (a) routing rules (by warranty status, product, channel), (b) **cost per transfer / per misroute / per call** (needed for ₹ model), (c) team changes (renames, merges, new teams and their dates), (d) systems (Zoho→CRM date, anything about the bot).
- [ ] Open `teams.csv`: confirm 7 canonical names printed by the audit match your reading of "renamed_to" and the names used in `sample_submission.csv`. **If `sample_submission.csv` team values use a different naming than the canonical set, use the sample's naming for output** and write the decision in the form.
- [ ] Did a team's scope change at the rename (read `handles`)? Crosstab team × month; a sudden category shift means old rows under that name mean something different → down-weight or drop those rows (decide on validation).
- [ ] Draft `rules.json` (below). Every rule needs `source` (policy section). Default `enabled:false`.
- [ ] **Gate:** if policy contradicts what actually happened in the CRM era (history disagrees > 5%), do **not** enable the rule; log it as a "policy vs practice conflict" — that's a finding for Ritu.
- [ ] Optional 30-min experiment E2: fit a depth-4 `DecisionTreeClassifier` to **bot labels**; if it reaches ≥97% the bot is a simple rule set — print the tree, and use it for the bot-error report (explains Billing/Consumables leaks exactly).

`rules.json` (example shape — replace with real policy rules, keep disabled until audited)
<!-- file: rules.json -->
```json
[
  {
    "id": "R-EXAMPLE",
    "source": "ops-policy.pdf §? (fill in)",
    "enabled": false,
    "when": {"warranty_status": ["shield"], "regex": "claim"},
    "team": "REPLACE_WITH_CANONICAL_TEAM"
  }
]
```

### Phase 3 — Target + split (1.5 h)

- [ ] Target = `final_team` (canonical). Training pool = closed rows only (D6).
- [ ] Time split on **CRM closed** rows: last 15% = holdout, previous 15% = validation, everything older (incl. Zoho) = dev (D4).
- [ ] Print split sizes and date ranges in `train.py` output; paste in `EVIDENCE.md`.
- [ ] **Gate:** CRM closed rows < 400 → use 10/10 and write the consequence (wider CI) in the form.
- [ ] Rule: the holdout is not looked at until Phase 9 (D5). Error analysis in Phase 6 uses **validation** errors.

### Phase 4 — Baselines (1.5 h)

Each baseline is a row in `EVIDENCE.md`, scored on validation, then holdout once at the end.

| Baseline | What it tells you |
|---|---|
| B0 majority class of `final_team` | floor |
| **B1 the bot's own label vs `final_team`** | **the incumbent's real accuracy** — the number to beat |
| B2 product_family + warranty only (tree) | how much metadata alone gives |
| B3 the chosen model (Phase 5) | the product |

- [ ] **Gate (decision about the whole project):** if B1 ≥ 90% vs `final_team`, the bot is fine and the project is "replace it cheaply" (cost story). If B1 is far lower, the project is "fix routing" (transfer story). Write which world you are in at the top of `NOTES.md`.

### Phase 5 — Modelling (3.5 h, hard time-box)

- [ ] Add `src/model.py` and `src/train.py` (below). Run `python -m src.train`.
- [ ] Grid is deliberately tiny (C × class_weight × zoho_weight = 12 fits), selected on **validation macro-F1**.
- [ ] Optional experiments (log each in `EVIDENCE.md` as tried/kept/discarded, 30–45 min each):
  - [ ] E1 local sentence-embedding + LR — keep only if ≥ +1.0 pt val macro-F1 **and** works offline from a committed artifact. Otherwise discard.
  - [ ] E2 decision tree on bot labels (Phase 2).
  - [ ] E3 LightGBM/HistGB on SVD(TF-IDF)+metadata — keep only if gain ≥ +1.0 pt and still explainable.
  - [ ] E4 train on bot labels for closed+unclosed rows (D6 comparison): shows how much of the apparent accuracy is "learning the bot".
- [ ] Do **not** add LLM calls. If tempted: price it (§8) and discard (D3).

<!-- file: src/model.py -->
```python
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def make_pipeline(C=10.0, class_weight=None):
    pre = ColumnTransformer([
        ("w", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True), "text"),
        ("c", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=3,
                              sublinear_tf=True, max_features=60000), "text"),
        ("m", CountVectorizer(token_pattern=r"\S+", lowercase=False, binary=True), "meta"),
    ])
    clf = LogisticRegression(C=C, class_weight=class_weight, max_iter=3000)
    return Pipeline([("pre", pre), ("clf", clf)])
```

<!-- file: src/train.py -->
```python
import json
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score

from .config import ART, DATA
from .data import load
from .model import make_pipeline


def boot_ci(y, p, n=1000, seed=0):
    rng = np.random.default_rng(seed)
    y, p = np.asarray(y), np.asarray(p)
    a = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        a.append((y[i] == p[i]).mean())
    return [round(float(np.percentile(a, 2.5)), 4), round(float(np.percentile(a, 97.5)), 4)]


def score(y, p):
    return {"n": int(len(y)), "accuracy": round(float(accuracy_score(y, p)), 4),
            "macro_f1": round(float(f1_score(y, p, average="macro")), 4)}


def fit(df, C, cw, zw):
    w = np.where(df.source == "legacy_zoho", zw, 1.0)
    pipe = make_pipeline(C, cw)
    pipe.fit(df, df.final_team, clf__sample_weight=w)
    return pipe


def pick_gate(y, proba, classes):
    y = np.asarray(y)
    top = proba.max(1)
    pred = np.asarray(classes)[proba.argmax(1)]
    best = None
    for tau in np.arange(0.50, 0.96, 0.05):  # floor 0.50: with 7 teams a top prob below 0.5 is a genuine toss-up
        keep = top >= tau
        if keep.mean() < 0.5:
            break
        acc = (pred[keep] == y[keep]).mean()
        if acc >= 0.95:
            best = (float(tau), float(keep.mean()), float(acc))
            break
    if best is None:
        tau = float(np.percentile(top, 20))
        keep = top >= tau
        best = (tau, float(keep.mean()), float((pred[keep] == y[keep]).mean()))
    return {"tau": round(best[0], 3), "coverage": round(best[1], 3), "accuracy_kept": round(best[2], 4)}


def main(holdout_frac=0.15, val_frac=0.15):
    tr, te, tmap, canon = load(DATA)
    closed = tr[tr.final_team.notna()].copy()
    crm = closed[closed.source == "crm"].sort_values("ts")
    assert len(crm) >= 200, f"Only {len(crm)} closed CRM rows - read Phase 3 gate."
    n = len(crm)
    t_hold = crm.ts.iloc[int(n * (1 - holdout_frac))]
    t_val = crm.ts.iloc[int(n * (1 - holdout_frac - val_frac))]
    hold = closed[closed.ts >= t_hold]
    val = closed[(closed.ts >= t_val) & (closed.ts < t_hold)]
    dev = closed[closed.ts < t_val]
    info = {"rows_train": len(tr), "rows_closed": len(closed), "rows_unclosed": int(len(tr) - len(closed)),
            "dev": len(dev), "val": len(val), "holdout": len(hold),
            "val_from": str(t_val), "holdout_from": str(t_hold), "canonical_teams": canon}
    print(info)

    best = None
    for C in (3, 10, 30):
        for cw in (None, "balanced"):
            for zw in (1.0, 0.5):
                pipe = fit(dev, C, cw, zw)
                s = score(val.final_team, pipe.predict(val))
                print(C, cw, zw, s)
                if best is None or s["macro_f1"] > best[0]["macro_f1"]:
                    best = (s, dict(C=C, cw=cw, zw=zw), pipe)
    val_score, params, pipe_dev = best
    gate = pick_gate(val.final_team, pipe_dev.predict_proba(val), pipe_dev.classes_)

    # holdout: evaluated ONCE, model fit on dev+val
    pipe_eval = fit(pd.concat([dev, val]), **params)
    ph = pipe_eval.predict(hold)
    seen = hold.text.isin(set(dev.text) | set(val.text)).values
    yh = hold.final_team.values
    mon = hold.ts.dt.to_period("M").astype(str).values
    holdout = {
        "model": {**score(yh, ph), "accuracy_ci95": boot_ci(yh, ph)},
        "bot_vs_final": {**score(yh, hold.bot_team.values), "accuracy_ci95": boot_ci(yh, hold.bot_team.values)},
        "model_agreement_with_bot_label": score(hold.bot_team.values, ph),
        "model_accuracy_seen_text": round(float((ph[seen] == yh[seen]).mean()), 4) if seen.any() else None,
        "model_accuracy_unseen_text": round(float((ph[~seen] == yh[~seen]).mean()), 4) if (~seen).any() else None,
        "share_unseen_text": round(float((~seen).mean()), 4),
        "by_month_accuracy": {k: round(float((ph[mon == k] == yh[mon == k]).mean()), 4) for k in sorted(set(mon))},
        "avg_transfers_logged": round(float(hold.transfers.mean()), 4),
        "wrong_first_touch_rate": {"bot": round(float((hold.bot_team.values != yh).mean()), 4),
                                   "model": round(float((ph != yh).mean()), 4)},
    }
    proba_h = pipe_eval.predict_proba(hold)
    flagged = proba_h.max(1) < gate["tau"]
    holdout["gate_on_holdout"] = {
        "share_flagged_for_human": round(float(flagged.mean()), 4),
        "accuracy_when_not_flagged": round(float((ph[~flagged] == yh[~flagged]).mean()), 4) if (~flagged).any() else None,
        "accuracy_when_flagged": round(float((ph[flagged] == yh[flagged]).mean()), 4) if flagged.any() else None,
    }

    pd.crosstab(pd.Series(yh, name="actual"), pd.Series(ph, name="predicted")).to_csv(ART / "confusion_holdout.csv")
    err = hold.assign(pred=ph, conf=proba_h.max(1))
    err = err[err.pred != err.final_team].sort_values("conf", ascending=False)
    err[["request_id", "created_at_ist", "channel", "product_family", "warranty_status", "text",
         "final_team", "pred", "conf", "bot_team"]].to_csv(ART / "errors_holdout.csv", index=False)
    rep = classification_report(yh, ph, output_dict=True, zero_division=0)

    # production model: fit on every closed row
    final = fit(closed, **params)
    if set(final.classes_) != set(canon):
        print("WARNING: classes never seen as final_team:", sorted(set(canon) - set(final.classes_)))
    bundle = {"pipe": final, "tau": gate["tau"], "teams": list(final.classes_),
              "products": sorted(tr.product_family.unique()), "warranties": sorted(tr.warranty_status.unique()),
              "channels": sorted(tr.channel.unique()), "trained_rows": int(len(closed)),
              "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "params": params}
    joblib.dump(bundle, ART / "model.joblib", compress=3)

    pred = final.predict(te)
    cols = list(pd.read_csv(DATA / "sample_submission.csv", nrows=0).columns)
    pd.DataFrame({cols[0]: te.request_id.values, cols[1]: pred}).to_csv("predictions.csv", index=False)
    proba_t = final.predict_proba(te)
    pd.DataFrame({"request_id": te.request_id.values, "team": pred, "confidence": proba_t.max(1).round(4),
                  "flagged_for_human": proba_t.max(1) < gate["tau"]}).to_csv(ART / "predictions_with_confidence.csv", index=False)

    metrics = {"split": info, "chosen_params": params, "validation": val_score, "gate_from_validation": gate,
               "holdout": holdout, "per_class_holdout": rep,
               "test_predicted_distribution": pd.Series(pred).value_counts().to_dict(),
               "test_flagged_share": round(float((proba_t.max(1) < gate["tau"]).mean()), 4)}
    (ART / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: metrics[k] for k in ("validation", "gate_from_validation")}, indent=2))
    print(json.dumps(holdout, indent=2))


if __name__ == "__main__":
    main()
```

### Phase 6 — Error analysis + rules (3 h)

- [ ] Work from **validation** errors only (re-run with holdout columns hidden, or temporarily dump `val` errors) until Phase 9.
- [ ] Hand-label ≥ 50 errors into a taxonomy. Suggested buckets (add your own): `ambiguous-no-info` · `payment-for-service (the Billing leak)` · `purifier breakdown vs consumables` · `IVR transcript noise` · `mixed intents` · `label looks wrong (final_team itself questionable)` · `scope change at rename` · `other`.
- [ ] For each bucket: count, one example, fix or "cannot fix, here's why".
- [ ] Cheap fixes allowed: add keyword-cross features, add `rules.json` rule (only after the 95% audit), tweak thresholds. Not allowed: tuning on the holdout.
- [ ] **Bot-error report** (bonus, high value to Meenal): from the Phase 1 crosstab, list "bot says X → ends in Y" top 5 pairs with counts and the **share of Billing that ends elsewhere**. This alone is worth money even if the model were never deployed.
- [ ] Re-run `python -m src.train` after each accepted change; keep a one-line changelog in `EVIDENCE.md`.

### Phase 7a — Checkpoint submission (1 h, do it early)

- [ ] After the first working `train.py` run (even before tuning), run `python -m scripts.validate_submission`. A valid `predictions.csv` now exists; later work can only improve it.
- [ ] Commit tag `checkpoint-1`.

<!-- file: scripts/validate_submission.py -->
```python
import sys

import pandas as pd

from src.config import DATA
from src.data import load


def main(path="predictions.csv"):
    sub = pd.read_csv(path, dtype=str, keep_default_na=False)
    test = pd.read_csv(DATA / "test_unlabelled.csv", dtype=str, keep_default_na=False)
    tmpl = pd.read_csv(DATA / "sample_submission.csv", dtype=str, keep_default_na=False)
    _, _, tmap, canon = load(DATA)
    errs = []
    if list(sub.columns) != list(tmpl.columns):
        errs.append(f"columns {list(sub.columns)} != template {list(tmpl.columns)}")
    idc, tc = tmpl.columns[0], tmpl.columns[1]
    if len(sub) != len(test):
        errs.append(f"row count {len(sub)} != test rows {len(test)}")
    if sub[idc].duplicated().any():
        errs.append("duplicate request_id rows")
    if set(sub[idc]) != set(test["request_id"]):
        errs.append("request_id set differs from test_unlabelled.csv")
    bad = sorted(set(sub[tc]) - set(canon))
    if bad:
        errs.append(f"team values not in canonical set {canon}: {bad}")
    old = sorted(set(sub[tc]) & {k for k, v in tmap.items() if k != v})
    if old:
        errs.append(f"OLD (pre-rename) team names present: {old}")
    sample_names = set(tmpl[tc])
    print("canonical teams:", canon, "| sample_submission team values:", sorted(sample_names))
    print("predicted distribution:\n", sub[tc].value_counts().to_string())
    if errs:
        print("FAIL:\n - " + "\n - ".join(errs))
        sys.exit(1)
    print("OK: submission is valid")


if __name__ == "__main__":
    main(*sys.argv[1:])
```

### Phase 8 — Service + screen (3.5 h)

Requirements from the brief: **one endpoint** taking one JSON record and returning the model output plus reasons a Kestrel employee would read; **one screen** calling it; starts on a clean machine **without a paid key**; if no model/API is available it must fail politely.

- [ ] `src/predict.py`, `src/rules.py`, `src/service.py`, `static/index.html` (below)
- [ ] Output reasons are **sentences**, not feature IDs: confidence, runner-up, the phrases that pushed toward the team, the product/warranty/channel context, any policy rule hit, and a clarifying question when flagged.
- [ ] Failure modes handled: model file missing → 503 with the exact command to fix; empty text → 200 with warning and metadata-only decision; unknown product/warranty/channel → treated as `unknown`; malformed JSON → FastAPI 422 with plain message.
- [ ] Run: `uvicorn src.service:app --port 8000` → open `http://localhost:8000`.
- [ ] Curl check:
  `curl -s localhost:8000/route -H 'content-type: application/json' -d '{"request_text":"I paid for installation but nobody came","product_family":"water purifier","warranty_status":"in_warranty","channel":"chat"}'`

<!-- file: src/rules.py -->
```python
import json
import re

from .config import ROOT


def load_rules():
    p = ROOT / "rules.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


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
```

<!-- file: src/predict.py -->
```python
import joblib
import numpy as np
import pandas as pd
import scipy.sparse as sp

from .clean import add_meta, clean_text
from .config import ART
from .rules import load_rules, match_rule

PRETTY = {"p_": "product", "w_": "warranty", "c_": "channel"}

CLARIFY = ("Ask the customer: which product, and is it (a) not working, (b) needs a filter/part, "
           "(c) installation, or (d) a payment/refund question?")


class ModelMissing(Exception):
    pass


def _norm(v):
    v = (v or "").strip().lower()
    return v or "unknown"


class Router:
    def __init__(self, path=None):
        path = path or ART / "model.joblib"
        if not path.exists():
            raise ModelMissing(f"Model file not found at {path}. Run: python -m src.train")
        b = joblib.load(path)
        self.b, self.pipe, self.tau = b, b["pipe"], b["tau"]
        self.rules = load_rules()

    def _explain(self, df, team, k=5):
        pre, clf = self.pipe.named_steps["pre"], self.pipe.named_steps["clf"]
        X = pre.transform(df)
        names = pre.get_feature_names_out()
        j = list(clf.classes_).index(team)
        row = sp.csr_matrix(X.multiply(clf.coef_[j]))
        order = np.argsort(-row.data)
        words, ctx = [], []
        for o in order:
            if row.data[o] <= 0:
                break
            n = names[row.indices[o]]
            if n.startswith("w__") and len(words) < k:
                words.append(n[3:])
            elif n.startswith("m__") and n[3:5] in PRETTY and len(ctx) < 2:
                ctx.append(f"{PRETTY[n[3:5]]} = {n[5:].replace('_', ' ')}")
        return words, ctx

    def route(self, rec: dict) -> dict:
        warnings = []
        text = clean_text(rec.get("request_text", ""))
        if not text:
            warnings.append("No request text: decision uses product, warranty and channel only.")
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
        team, conf = classes[order[0]], float(p[order[0]])
        alts = [{"team": classes[i], "probability": round(float(p[i]), 3)} for i in order[1:3]]
        reasons = [f"Routed to {team}: model confidence {conf:.0%}; next best {alts[0]['team']} {alts[0]['probability']:.0%}."]
        words, ctx = self._explain(df, team)
        if words:
            reasons.append("Phrases that pointed here: " + ", ".join(f"'{w}'" for w in words) + ".")
        reasons.append(f"Context read: product {row['product_family']}, warranty {row['warranty_status']}, channel {row['channel']}.")
        rule = match_rule({**row}, self.rules)
        rule_out = None
        if rule:
            team, rule_out = rule["team"], {"id": rule["id"], "source": rule.get("source")}
            reasons.append(f"Policy rule {rule['id']} applied ({rule.get('source')}).")
        flag = conf < self.tau and not rule
        if flag:
            reasons.append(f"Confidence {conf:.0%} is below the {self.tau:.0%} line: send to a human to confirm before routing.")
        return {"request_id": rec.get("request_id"), "team": team, "confidence": round(conf, 3),
                "alternatives": alts, "needs_clarification": flag,
                "clarifying_question": CLARIFY if flag else None, "reasons": reasons,
                "rule": rule_out, "warnings": warnings, "model_trained_at": self.b["trained_at"]}
```

<!-- file: src/service.py -->
```python
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .config import ROOT
from .predict import ModelMissing, Router

app = FastAPI(title="Kestrel service-request router")
_router = None


def get_router():
    global _router
    if _router is None:
        _router = Router()
    return _router


class Req(BaseModel):
    request_text: str = ""
    product_family: str = "unknown"
    warranty_status: str = "unknown"
    channel: str = "unknown"
    request_id: Optional[str] = None
    created_at_ist: Optional[str] = None


@app.get("/health")
def health():
    try:
        get_router()
        return {"status": "ok"}
    except ModelMissing as e:
        return JSONResponse(status_code=503, content={"status": "model_missing", "message": str(e)})


@app.get("/meta")
def meta():
    try:
        b = get_router().b
        return {"teams": b["teams"], "products": b["products"], "warranties": b["warranties"],
                "channels": b["channels"], "trained_at": b["trained_at"], "trained_rows": b["trained_rows"]}
    except ModelMissing as e:
        return JSONResponse(status_code=503, content={"message": str(e)})


@app.post("/route")
def route(req: Req):
    try:
        return get_router().route(req.model_dump())
    except ModelMissing as e:
        return JSONResponse(status_code=503, content={"message": str(e)})
    except Exception as e:  # never leak a stack trace to a service-desk user
        return JSONResponse(status_code=500, content={"message": "Could not route this request. "
                            "Please route it manually and tell the data team.", "detail": str(e)[:200]})


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")
```

<!-- file: static/index.html -->
```html
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Kestrel routing</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font-family:system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;color:#1a1a1a}
textarea,select,button{font:inherit;padding:.5rem;width:100%;box-sizing:border-box;margin:.25rem 0 .75rem}
button{background:#1f4e79;color:#fff;border:0;border-radius:6px;cursor:pointer}
.row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:.75rem}
.card{border:1px solid #ccc;border-radius:8px;padding:1rem;margin-top:1rem}
.team{font-size:1.6rem;font-weight:700}.warn{background:#fff4d6;border-color:#e0b000}
.bar{height:10px;background:#e5e5e5;border-radius:5px}.bar>div{height:10px;background:#1f4e79;border-radius:5px}
</style></head><body>
<h1>Where should this request go?</h1>
<label>Customer's message / IVR transcript</label>
<textarea id="t" rows="4" placeholder="e.g. I paid for installation but nobody has come"></textarea>
<div class="row">
 <div><label>Product</label><select id="p"></select></div>
 <div><label>Warranty</label><select id="w"></select></div>
 <div><label>Channel</label><select id="c"></select></div>
</div>
<button id="go">Route it</button>
<div id="out"></div>
<script>
const $=id=>document.getElementById(id);
function fill(id,vals){$(id).innerHTML="";["unknown",...vals.filter(v=>v!=="unknown")].forEach(v=>{const o=document.createElement("option");o.value=o.textContent=v;$(id).appendChild(o)})}
fetch("/meta").then(r=>r.json()).then(m=>{if(m.message){$("out").innerHTML="";const d=document.createElement("div");d.className="card warn";d.textContent=m.message;$("out").appendChild(d);return}
 fill("p",m.products);fill("w",m.warranties);fill("c",m.channels)}).catch(()=>{});
$("go").onclick=async()=>{
 const out=$("out");out.textContent="Working...";
 try{
  const r=await fetch("/route",{method:"POST",headers:{"content-type":"application/json"},
   body:JSON.stringify({request_text:$("t").value,product_family:$("p").value,warranty_status:$("w").value,channel:$("c").value})});
  const j=await r.json();out.innerHTML="";
  const card=document.createElement("div");card.className="card"+((!r.ok||j.needs_clarification)?" warn":"");
  const add=(tag,txt,cls)=>{const e=document.createElement(tag);e.textContent=txt;if(cls)e.className=cls;card.appendChild(e);return e};
  if(!r.ok){add("div",j.message||"Something went wrong.")}
  else{
   add("div",j.team,"team");
   add("div","Confidence "+Math.round(j.confidence*100)+"%");
   const b=document.createElement("div");b.className="bar";const f=document.createElement("div");f.style.width=Math.round(j.confidence*100)+"%";b.appendChild(f);card.appendChild(b);
   if(j.needs_clarification)add("p","Needs a human check. "+j.clarifying_question);
   add("h3","Why");const ul=document.createElement("ul");j.reasons.forEach(x=>{const li=document.createElement("li");li.textContent=x;ul.appendChild(li)});card.appendChild(ul);
   if(j.warnings.length)add("p","Notes: "+j.warnings.join(" "));
  }
  out.appendChild(card);
 }catch(e){out.textContent="Cannot reach the service. Is it running?"}
};
</script></body></html>
```

<!-- file: tests/test_smoke.py -->
```python
import pytest
from fastapi.testclient import TestClient

from src.config import ART
from src.service import app

pytestmark = pytest.mark.skipif(not (ART / "model.joblib").exists(), reason="train first")
client = TestClient(app)


def test_route_shape():
    r = client.post("/route", json={"request_text": "my purifier is not working", "product_family": "water purifier"})
    j = r.json()
    assert r.status_code == 200
    for k in ("team", "confidence", "reasons", "needs_clarification", "alternatives", "warnings"):
        assert k in j
    assert 0 <= j["confidence"] <= 1 and len(j["reasons"]) >= 2


def test_empty_text_is_polite():
    r = client.post("/route", json={})
    assert r.status_code == 200 and r.json()["warnings"]


def test_bad_json_is_422():
    assert client.post("/route", content="not json", headers={"content-type": "application/json"}).status_code == 422


def test_index_and_health():
    assert client.get("/").status_code == 200
    assert client.get("/health").json()["status"] == "ok"
```

<!-- file: scripts/golden.py -->
```python
"""Prints how the model handles the cases the client's own email describes. Read it; don't trust it blindly."""
from src.predict import Router

CASES = [
    ("Meenal #1: paid for installation", "I paid for the installation but nobody has come yet", "water purifier", "in_warranty", "chat"),
    ("Meenal #1b: paid for repair", "I already paid for the repair visit, please send the technician", "robot vacuum", "out_of_warranty", "email"),
    ("Meenal #2: purifier breakdown", "my water purifier stopped working and is leaking", "water purifier", "in_warranty", "whatsapp"),
    ("Meenal #3: call me", "please call me about my purifier", "water purifier", "unknown", "ivr"),
    ("Empty text", "", "fan", "in_warranty", "ivr"),
]

if __name__ == "__main__":
    r = Router()
    for name, t, p, w, c in CASES:
        o = r.route({"request_text": t, "product_family": p, "warranty_status": w, "channel": c})
        print(f"{name:34s} -> {o['team']:24s} conf {o['confidence']:.2f} flag={o['needs_clarification']}")
```

### Phase 9 — Evidence pack (2.5 h) — **model is frozen after this**

`EVIDENCE.md` must contain (copy from `artifacts/metrics.json`, don't retype):

- [ ] **Setup:** target definition, split by time with dates and sizes, what was excluded and why.
- [ ] **Headline table** (holdout, CRM-era, last 15% of closed rows):

| | Accuracy vs `final_team` | 95% CI | Macro-F1 |
|---|---|---|---|
| Bot (incumbent) | `{{bot_acc}}` | `{{bot_ci}}` | `{{bot_f1}}` |
| This model | `{{model_acc}}` | `{{model_ci}}` | `{{model_f1}}` |
| Model agreement with the bot's own label (Ritu's "90%" measure) | `{{agree}}` | — | — |

- [ ] **How often it is wrong:** `1 − accuracy`, per team (from `per_class_holdout`), by month (drift), seen-text vs unseen-text.
- [ ] **Confidence gate:** share flagged for human, accuracy on flagged vs unflagged.
- [ ] **Error taxonomy** from Phase 6 with counts and examples.
- [ ] **Confusion matrix** (`artifacts/confusion_holdout.csv`).
- [ ] **Tried / kept / discarded** list (feeds the recording).
- [ ] **Golden cases** (`python -m scripts.golden`) pasted verbatim, including the ones it gets wrong.
- [ ] **Busiest teams** table: by `final_team` count and by touches (`1 + transfers` lower bound), share of total. State "handling time not provided → no FTE figure".
- [ ] **Expected score statement** (written into the form *before* submission):
  1. Primary guess: scorer = accuracy against `final_team` on the hidden recent requests.
  2. Estimate = holdout accuracy (point), range = holdout CI lower bound minus drift haircut, where haircut = (accuracy of first half of holdout months − accuracy of last month) if negative, else 0, plus 1–2 pts for T6 censoring optimism.
  3. If the scorer uses macro-F1, expect `{{model_f1}}` minus the same haircut.
  4. If the scorer is instead matched to the bot's own labels, expect ≈ `{{agree}}` (and say that this is *not* the goal).
  5. State the one thing most likely to break it: a distribution shift in the last month (new product/team/policy).
- [ ] **Freeze:** tag `model-frozen`. No more `train.py` runs except for a bug.

### Phase 10 — Cost + numbers (1 h)

- [ ] `python -m scripts.numbers --transfer-cost-inr {{from policy}} --hosting-inr-month {{your hosting price or 0}}` → save output to `artifacts/numbers.txt`.
- [ ] See §8 for the arithmetic and the written monthly figure for Farhan.

<!-- file: scripts/numbers.py -->
```python
"""Single source of truth for every rupee/volume number used in the memo and the form."""
import argparse
import json

from src.config import ART, DATA
from src.data import load


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transfer-cost-inr", type=float, required=True, help="cost of one transfer, from ops-policy.pdf")
    ap.add_argument("--hosting-inr-month", type=float, default=0.0, help="0 if it runs on a machine Kestrel already pays for")
    ap.add_argument("--licence-inr-year", type=float, default=320000.0)
    ap.add_argument("--orders-per-month", type=float, default=700.0)
    ap.add_argument("--maintenance-hours-month", type=float, default=2.0)
    ap.add_argument("--hour-inr", type=float, default=0.0, help="internal cost of an hour of Tanmay's time, if you want it included")
    a = ap.parse_args()

    m = json.loads((ART / "metrics.json").read_text())
    tr, te, _, _ = load(DATA)
    months = max((tr.ts.max() - tr.ts.min()).days / 30.44, 1.0)
    req_month = len(tr) / months
    ratio = req_month / a.orders_per_month
    h = m["holdout"]
    bot_err, mod_err = h["wrong_first_touch_rate"]["bot"], h["wrong_first_touch_rate"]["model"]
    avoided = (bot_err - mod_err) * req_month
    lic_m = a.licence_inr_year / 12
    maint = a.maintenance_hours_month * a.hour_inr
    run = a.hosting_inr_month + maint
    out = [
        f"months of train data: {months:.1f}", f"measured requests/month: {req_month:.0f}  (vs {a.orders_per_month:.0f} orders/month => {ratio:.2f} requests per order)",
        f"bot wrong-first-touch rate (holdout): {bot_err:.1%}  model: {mod_err:.1%}",
        f"transfers avoided/month ~ ({bot_err:.3f} - {mod_err:.3f}) x {req_month:.0f} = {avoided:.0f}",
        f"transfer saving/month = {avoided:.0f} x Rs {a.transfer_cost_inr:,.0f} = Rs {avoided * a.transfer_cost_inr:,.0f}",
        f"licence avoided/month = Rs {a.licence_inr_year:,.0f} / 12 = Rs {lic_m:,.0f}",
        f"cost per prediction = Rs 0 (no paid API; CPU inference)",
        f"cost at {a.orders_per_month:.0f} orders/month = 0 x {a.orders_per_month:.0f} + hosting Rs {a.hosting_inr_month:,.0f} = Rs {a.hosting_inr_month:,.0f}",
        f"cost at measured {req_month:.0f} requests/month = Rs {a.hosting_inr_month:,.0f} hosting (+ maintenance Rs {maint:,.0f})",
        f"net monthly benefit = {lic_m:,.0f} + {avoided * a.transfer_cost_inr:,.0f} - {run:,.0f} = Rs {lic_m + avoided * a.transfer_cost_inr - run:,.0f}",
        f"net annual benefit = Rs {12 * (lic_m + avoided * a.transfer_cost_inr - run):,.0f}",
        "CAUTION: transfer saving uses the point estimate; recompute with the CI bounds before quoting a range.",
    ]
    print("\n".join(out))


if __name__ == "__main__":
    main()
```

### Phase 11 — Memo (1.5 h)

See §9 for the template. Rules: one page, no ML words, the one number stated once, rupees in lakh format, a decision in the first line, four next-week actions with owners.

### Phase 12 — Screen recording (1.5 h, ≤ 3:00)

See §10 for the script. Record twice; keep the better take. No slides, no code scrolling.

### Phase 13 — Form + repo + Drive (2 h)

- [ ] §11 holds draft answers for every field. Fill `{{}}` from `artifacts/*`.
- [ ] Repo: README (3-command start at the top), `BUILD.md`, `NOTES.md`, `EVIDENCE.md`, `MEMO.md`, `submission-form.md`, `predictions.csv`, `artifacts/model.joblib` (check size < 50 MB; if bigger, drop `max_features` to 30000 and retrain **before** freeze), `data/*` as supplied, `hours.log`.
- [ ] Drive folder (Anyone with link → Viewer): recording, memo PDF, `artifacts/`.
- [ ] Never commit API keys (there are none) or `.venv`.

README top block (copy verbatim, adjust nothing else):
```text
# Kestrel routing service
Python 3.10+. No API key needed.
1. python -m venv .venv && source .venv/bin/activate     (Windows: .venv\Scripts\activate)
2. pip install -r requirements.txt
3. uvicorn src.service:app --port 8000      then open http://localhost:8000
Retrain (optional): python -m src.train     Validate submission: python -m scripts.validate_submission
Tests: pytest -q     Golden cases: python -m scripts.golden
If the page says "model file not found", run the retrain command.
```

### Phase 14 — Clean-machine test + final freeze (1.5 h)

- [ ] `git clone` the **public** URL into a new folder; fresh venv; follow README literally; use a different terminal profile / another machine if you can. No env vars set.
- [ ] Page loads; the 5 golden cases return; `pytest -q` passes; `curl` returns JSON.
- [ ] Temporarily rename `artifacts/model.joblib` → page and `/route` show a polite message, no stack trace; rename back.
- [ ] `python -m scripts.validate_submission` → `OK`.
- [ ] Row count of `predictions.csv` equals test rows; open it in a text editor and eyeball 10 rows against the text.
- [ ] Final tag `submission`. Submit.

---

## 6. Dev-only synthetic data (for smoke-testing the code without the real files)

Use only to prove the plumbing runs; its numbers mean nothing. `python -m scripts.make_synthetic --out /tmp/kdata && KESTREL_DATA=/tmp/kdata KESTREL_ART=/tmp/kart python -m src.train`

<!-- file: scripts/make_synthetic.py -->
```python
import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd

TEAMS = ["Technical Support", "Installation", "Billing", "Returns & Refunds", "Escalations",
         "Consumables & Spares", "Warranty & Shield"]
OLD = {"Consumables & Spares": "Spares Desk", "Warranty & Shield": "Shield Desk"}
PRODS = ["air fryer", "mixer-grinder", "water purifier", "robot vacuum", "cooktop", "fan", "heater"]
T = {
    "Technical Support": ["{p} is not working, stopped suddenly", "{p} making loud noise and leaking", "{p} breakdown please send technician"],
    "Installation": ["need installation of my {p}", "installation not done yet nobody came", "demo and installation booking for {p}"],
    "Billing": ["refund for wrong charge on invoice", "invoice copy needed for {p}", "payment deducted twice for {p}"],
    "Returns & Refunds": ["want to return my {p} wrong item", "cancel order and refund {p}"],
    "Escalations": ["third time calling escalate to manager {p}", "consumer court notice about {p}"],
    "Consumables & Spares": ["need filter replacement for {p}", "order spare jar lid for {p}", "where to buy spare parts for {p}"],
    "Warranty & Shield": ["how to claim Shield plan for {p}", "is my {p} still under warranty", "extend warranty on {p}"],
}


def main(out, n=3000, seed=0):
    rng, nrng = random.Random(seed), np.random.default_rng(seed)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    start, end = pd.Timestamp("2025-03-01"), pd.Timestamp("2026-08-31")
    rows, res = [], []
    for i in range(n + 400):
        ts = start + (end - start) * (i / (n + 400))
        src = "legacy_zoho" if ts < pd.Timestamp("2025-10-01") else "crm"
        r = rng.random()
        if r < 0.10:
            final = rng.choice(["Installation", "Technical Support"]); bot = "Billing"
            txt = f"I paid for {'installation' if final == 'Installation' else 'repair'} of my {{p}} but nothing happened"
        elif r < 0.15:
            final = rng.choice(["Technical Support", "Consumables & Spares", "Warranty & Shield"]); bot = "Consumables & Spares"
            txt = "please call me about my {p}"
        else:
            final = rng.choice(TEAMS); txt = rng.choice(T[final]); bot = final if rng.random() < 0.85 else rng.choice(TEAMS)
        p = rng.choice(PRODS)
        txt = txt.format(p=p) + " — thanks"
        if src == "legacy_zoho":
            txt = txt.encode("utf-8").decode("latin-1")
        ren = ts >= pd.Timestamp("2025-12-01")
        nm = lambda t: t if ren or t not in OLD else OLD[t]
        ch = rng.choice(["ivr", "chat", "whatsapp", "email"])
        wr = rng.choice(["in_warranty", "shield", "out_of_warranty"])
        rid = f"SR{i:06d}"
        row = dict(request_id=rid, created_at_ist=str(ts), channel=ch, product_family=p, warranty_status=wr,
                   request_text=txt, source=src)
        if i < n:
            rows.append({**row, "team_label": nm(bot)})
            closed = i < n - int(0.03 * n)
            res.append(dict(request_id=rid, first_team=nm(bot), final_team=nm(final) if closed else "",
                            transfers=int(bot != final) if closed else "",
                            resolved_at=str(ts + pd.Timedelta(hours=float(nrng.integers(2, 90)))) if closed else ""))
        else:
            rows.append(row)
    df = pd.DataFrame(rows)
    df.iloc[:n].to_csv(out / "train.csv", index=False)
    df.iloc[n:].drop(columns=["team_label"], errors="ignore").to_csv(out / "test_unlabelled.csv", index=False)
    pd.DataFrame(res).to_csv(out / "resolution_log.csv", index=False)
    teams = [dict(team=t if t not in OLD else OLD[t], renamed_to=t if t in OLD else "", handles=t) for t in TEAMS]
    pd.DataFrame(teams).to_csv(out / "teams.csv", index=False)
    pd.DataFrame({"request_id": df.iloc[n:].request_id, "team": TEAMS[0]}).to_csv(out / "sample_submission.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    main(ap.parse_args().out)
```

---

## 7. Evidence standards (what "works" means here)

| Claim | Evidence required | Failure mode to disclose |
|---|---|---|
| "More accurate than the bot" | Holdout accuracy vs `final_team`, model vs bot, same rows, with CI; difference of CIs | CIs overlap → say "not distinguishable", don't claim a win |
| "Meets 90%" | Show **both** definitions (vs bot label / vs final team). Never tune toward 90 | Honest miss is fine and can raise the score |
| "Handles Meenal's cases" | Golden script output, incl. failures | Cases it still gets wrong |
| "Works on recent data" | By-month accuracy on holdout; CRM-only | Drift in the final month |
| "Transfers reduced" | `wrong_first_touch_rate` bot vs model × measured volume × policy transfer cost | Point estimate; log `transfers` is only for closed rows |
| "Reasons are usable" | 3 screenshots/recorded cases with a service-desk reading | Words that are artefacts, not reasons |

---

## 8. Cost model (Farhan's "in writing")

Write this as a short table in the memo and the form (Q: "What does one prediction cost…").

- **Per prediction:** ₹0 in paid calls (no API, no tokens). CPU inference ≈ `{{ms}}` ms measured with `python -c "import time;from src.predict import Router;r=Router();t=time.time();[r.route({'request_text':'x'}) for _ in range(200)];print((time.time()-t)/200*1000)"`.
- **Per month at 700 orders:** `₹0 × 700 + hosting`. If it runs on a machine Kestrel already has: hosting = ₹0. If a small cloud VM is needed: put **their quoted price** here — I do not invent cloud prices.
- **Per month at measured volume** (`numbers.py` prints requests per order — service requests are not necessarily equal to the 700 orders): same formula with the measured volume. The cost does **not grow** with volume until the box saturates (state the measured throughput).
- **Licence avoided:** ₹3,20,000 ÷ 12 = **₹26,667/month**.
- **Maintenance (stated assumption):** monthly retrain ≈ 2 hours of Tanmay's time; cost = hours × Kestrel's internal rate (leave at ₹0 if they don't charge internally, but say it).
- **If an LLM had been used** (not used): monthly cost = `requests × (input_tokens × price_in + output_tokens × price_out)` — it scales linearly with volume, which is exactly what Farhan said he doesn't want. That is the reason D3 exists.

---

## 9. Memo to Ritu — template (≤ 1 page, non-technical)

> **To:** Ritu Deshpande · **From:** {{you}} · **Re:** Can we switch the routing bot off?
>
> **The decision.** {{ONE of:}} 
> (A) *Yes, replace it — in two steps.* Run the new router alongside the bot for two weeks, then switch the bot off for everything the router is sure about; the unsure ones go to a person.
> (B) *Not yet.* The new router is not clearly better than the bot, and switching off now would cost you more than the licence saves. Here are three fixes to the bot's rules that you can make this month.
> *(Choose A only if the model's accuracy interval sits above the bot's by ≥ 3 points and the unsure share is ≤ {{x}}%. Otherwise B.)*
>
> **The number.** Measured against where requests actually ended up, the bot sends the right team first time **{{bot_acc}}%** of the time; the new router **{{model_acc}}%** (we are 95% sure the true figure is between {{lo}}% and {{hi}}%). Your 90% target measures how closely we copy the bot. We can copy it {{agree}}% — but copying the bot copies its mistakes: installation and repair payments go to Billing, purifier breakdowns go to Consumables. We measured against outcomes instead. {{x}}% of requests (e.g. "please call me about my purifier") do not contain enough to route; the router flags those for a person to ask one question.
>
> **The rupees.** The licence is ₹3,20,000 a year (₹26,667 a month). The router makes **no paid calls**: ₹0 per request, ₹{{hosting}} a month to run, so it does not grow with volume. Fewer wrong first touches ≈ {{avoided}} fewer transfers a month × ₹{{cost}} each = ₹{{saving}} a month. Net ≈ ₹{{net}} a month, ₹{{net_year}} a year *(the transfer saving is an estimate; the range is ₹{{lo_s}}–₹{{hi_s}})*. Farhan: this is the monthly run cost in writing.
>
> **Next week.** 1) **Tanmay** puts the router in shadow mode next to the bot (we will send the three commands). 2) **Meenal** names two people to review the flagged requests daily and tells us the first-week disagreements. 3) **You** decide the go/no-go date for switching the bot off; we recommend only when the shadow numbers match the table above. 4) **Meenal** adopts the three bot-rule fixes now (list attached) — they cut the Billing/Consumables transfers regardless of what you decide. **Headcount:** busiest by where requests end up is {{team1}}, {{team2}}, {{team3}} ({{share}}% of volume); we did not have handling times so we haven't converted this to people.

Memo checks: [ ] decision in line 1 · [ ] number appears once, with its meaning · [ ] no "F1/precision/TF-IDF" · [ ] every ₹ has arithmetic behind it in the form · [ ] read aloud to a non-technical person.

---

## 10. Screen-recording script (≤ 3:00, no slides)

| Time | Show | Say (plain words) |
|---|---|---|
| 0:00–0:20 | `audit.txt` crosstab (bot vs final) | "The bot's labels are not the truth. Against where requests ended, it's right {{bot_acc}}%. Meenal's complaints show up here: {{n}} Billing requests ended elsewhere." |
| 0:20–0:50 | NOTES.md decisions | "What I changed: I trained on where requests ended, not the bot's label; split by time not randomly; fixed the Zoho text; mapped renamed teams; banned the 'source' column." |
| 0:50–1:25 | EVIDENCE headline table | "Holdout, last months, CRM only: bot {{bot_acc}}%, mine {{model_acc}}% ({{ci}}). Wrong most often on {{bucket}}." |
| 1:25–2:10 | Browser: type 3 golden cases | "Installation payment goes to {{team}}, not Billing. Breakdown goes to {{team}}. 'Call me about my purifier' is flagged — a person should ask." |
| 2:10–2:35 | EVIDENCE tried/discarded list | "Tried an embedding model: {{delta}} points, needed a download — discarded. Considered an LLM: bill grows with every request — discarded." |
| 2:35–3:00 | Memo, cost line | "Decision: {{A/B}}. ₹0 per request, ₹{{hosting}} a month, saves ₹{{net}}. Where it fails: {{one}}." |

---

## 11. Submission form — draft answers (fill `{{}}` from artifacts)

1. **What did you build, and what business decision does it support? State the number and the rupees.**
   A routing service (CPU-only model + one JSON endpoint + one screen) that predicts the team where a request will actually end up, with reasons and a "needs a human" flag. It supports Ritu's decision on whether to retire the ₹3,20,000/yr bot. Number: bot right first time {{bot_acc}}% vs model {{model_acc}}% ({{ci}}) on the last {{n}} closed CRM requests; rupees: licence ₹26,667/month avoided, ₹0 per prediction, ₹{{hosting}}/month hosting, estimated net ₹{{net}}/month.
2. **Expected score on hidden outcomes, metric, why, how estimated.**
   {{model_acc}} accuracy vs `final_team` (range {{lo}}–{{hi}} after a drift/censoring haircut of {{h}}); macro-F1 {{model_f1}} if that's the metric. Accuracy because the client's own bar is a match rate and outcomes are what we're scored on. Estimated on a time-ordered CRM-only holdout touched once. Written before submission on {{date/time}}.
3. **How do you know it works?**
   Time split (dev older / val / holdout last 15% of closed CRM rows), tuned on validation only, holdout once. Error rate {{1-acc}}; by team {{...}}; by month {{...}}. Wrong mostly on {{buckets}}. Hand-read {{N}} errors. Golden cases from the client's email in `EVIDENCE.md`.
4. **Did you change, narrow, or push back on the client's ask?**
   Yes. Pushed back on "match the labels at 90%": the labels are the bot's output, not outcomes. Predicted where requests ended instead, reported agreement with the bot separately, and recommended shadow mode + a human check on low-confidence requests rather than switching off on day one. Narrowed headcount advice to a ranking (no handling times). When: Phase 1, after the bot-vs-final crosstab.
5. **What is wrong with what you are handing us / the data?**
   Be specific: {{closed-rate drop in recent months (censoring)}}; Zoho text mojibake ({{x}}% rows, repaired with ftfy; {{y}} unrecoverable); Zoho `resolved_at` unusable ({{what you found}}); `source` perfectly separates eras so excluded; teams renamed ({{names}}) and {{scope change?}}; {{PII found in request_text — n phones/emails — committed as supplied/masked}}; exact-duplicate texts {{n}}; no customer ID so repeat customers could leak across the split; `final_team` itself may reflect who happened to close it; my model cannot fix requests with no information; known bugs: {{list}}.
6. **What did you deliberately leave out?**
   LLM/API calls (cost grows per request; breaks clean start), embedding models (needed downloads, {{delta}} pts), per-team FTE numbers (no handling times), training on unclosed rows (no outcome), auto-retraining/monitoring (out of window), authentication on the service.
7. **Anything built or found that nobody asked for?**
   Bot-error report (Billing/Consumables leaks quantified), confidence gate for human triage, shadow-mode rollout plan, policy-vs-practice conflicts {{list}}, golden cases from the client's email.
8. **What did you use AI for?**
   {{tools/models}}; helped with {{boilerplate, FastAPI skeleton, drafting this plan}}; wasted time on {{…}}; discarded {{…}}. Cost: ₹/$ {{amount}}. Recording: {{link}}.
9. **Public Google Drive link:** {{link}} (Anyone with the link can view).
10. **Someone picks this up Monday and you are unreachable — three things.**
    (1) Run: README's 3 commands; retrain with `python -m src.train`; numbers live in `artifacts/metrics.json`. (2) Don't switch the bot off until shadow-mode numbers match `EVIDENCE.md`; low-confidence requests go to a human. (3) Known weak spots: ambiguous "call me" requests, drift after policy/team changes, renamed-team mapping in `teams.csv`; retrain monthly.
11. **Honest hours spent:** {{sum of hours.log}}
12. **GitHub Repo Link:** {{url}} (public; verified by fresh clone)
13. **Cost of one prediction; month at ~700 orders/month:** ₹0 per prediction (no paid calls). 700 × ₹0 = ₹0 + hosting ₹{{hosting}} = ₹{{hosting}}/month; at measured {{req_month}} requests/month the same (cost doesn't scale with volume). Licence avoided ₹3,20,000 ÷ 12 = ₹26,667.

---

## 12. Risk register & kill switches

| Risk | Signal | Response |
|---|---|---|
| `final_team` mostly blank | Phase 1 | D1 fallback: train on bot labels, **say so on page 1 of memo** |
| Too few CRM closed rows | < 400 | 10/10 split, widen CI in memo |
| Team naming ambiguity (old vs new in sample_submission) | Phase 2 | Follow `sample_submission.csv` naming; document |
| Model > 50 MB / slow load | file size | cut `max_features`, `compress=3` already on |
| Hour 22 and still tinkering | clock | freeze, move on (D13) |
| Holdout looked at early | you did | note it in the form; re-split with a new last-10% as a fresh holdout |
| Score below bot | headline table | Memo option B; that's still a valid, honest submission |
| Recording > 3:00 | timer | cut the tried/discarded section to one sentence |
| Repo missing artifact on fresh clone | Phase 14 | commit `artifacts/model.joblib` explicitly (check `.gitignore`) |

---

## 13. Master checklist (tick top to bottom before submitting)

**Data truth**
- [ ] Audit read; `NOTES.md` answers all Phase 1 questions
- [ ] Canonical team list confirmed against `sample_submission.csv`
- [ ] Policy cost-per-transfer found (page ref) — or stated as missing and the saving left unquantified
- [ ] PII scan done and disclosed

**Model**
- [ ] Target = `final_team`; unclosed rows excluded; `source` not a feature; no resolution-log feature
- [ ] Time split only; holdout touched once
- [ ] Bot baseline computed on the same rows
- [ ] ≥ 50 errors hand-read; taxonomy in `EVIDENCE.md`
- [ ] Expected score written **before** submission, with method

**Submission**
- [ ] `validate_submission` = OK; rows = test rows; only canonical names
- [ ] `predictions.csv` regenerated by the **frozen** model

**Service**
- [ ] Endpoint returns team, confidence, alternatives, reasons, flag, warnings
- [ ] Screen works; missing-model path is polite; empty text handled
- [ ] Fresh clone + fresh venv passes; no env vars, no key

**Communication**
- [ ] Memo: decision first, one number, rupees with arithmetic, four next-week actions, headcount ranking
- [ ] Recording ≤ 3:00: tried / changed / threw away
- [ ] Form: no blank field; AI usage and cost honest; hours from `hours.log`
- [ ] Drive link opens in a private window; GitHub repo public

---

## Appendix A — Council record (5 domain experts, anonymised peer review, chairman)

*Method note: this environment has no parallel sub-agent tool, so the five advisors were run as five independent passes from fixed lenses, then reviewed against each other, rather than as five separate processes. The lenses follow the llm-council skill, bound to this domain.*

**Advisors (mapped lens → domain expert)**
1. **Contrarian → ML evaluation / data-forensics lead.** v1 trained on the bot's label and scored against it — "you're building a bot clone and certifying it with the bot's own answer key." Also: random CV would leak by time; `source` leaks era; unclosed rows are censored; `transfers`/`resolved_at` can't be features; the public repo may leak PII; the Zoho quirks must not leak into a CRM-only test.
2. **First Principles → service-operations / queueing lead.** The business problem is transfers, not label agreement. Metric should be wrong-first-touch rate × volume × cost. Some requests are un-routable by information content — build an abstain path, don't chase accuracy. The 90% bar must be explicitly reframed.
3. **Expansionist → FDE / finance partner.** The bot-error report and shadow-mode rollout are worth more to Ritu than the classifier; headcount answer should use final-team workload; Farhan needs a literal sentence of monthly cost; use policy's transfer cost for rupees.
4. **Outsider → non-technical client reader.** Memo must lead with the decision; "macro-F1" and "CI" must be translated; "90%" will be read as a promise — say plainly what is and isn't being claimed; README must show three commands first; UI must speak in sentences.
5. **Executor → staff engineer.** Submission must exist by hour ~10; time-box modelling; pin versions; commit the model artifact so a clean machine needs no data and no download; extract-and-run test of every code block; kill switches for the hour-22 freeze.

**Peer review (anonymised) — strongest / biggest blind spot / missed by all**
- Strongest: the Contrarian's target-label objection (it invalidates everything downstream). Blind spot: the Contrarian alone would never ship — no abstain/rollout answer. Missed by all five initially: **what if `sample_submission.csv` uses old team names or a different set** (added T3 gate); **what if scope of a renamed team changed** (added crosstab-by-month check); **duplicate texts are legitimate in test** so removing them would make the estimate too pessimistic (added D7: keep, report unseen-text subset); **the 20% "call me" pile may be bigger than the model's abstain share** (added gate reporting on holdout: accuracy when flagged vs not).

**Chairman's verdict — what changed from v1**
| v1 | v2 |
|---|---|
| Train/score on `team_label` | Train/score on `final_team`; bot is the baseline |
| 5-fold CV | Time split: dev/val/CRM-only holdout touched once |
| `source` as a feature | Banned (D11) |
| Single accuracy number | Accuracy + CI + macro-F1 + by-month + seen/unseen text + gate stats |
| "Recommend replacing the bot" | Gated: A (shadow → confidence-gated) or B (not yet), decided by a numeric rule |
| Optional embeddings/LLM | Embeddings only with a ≥1 pt, offline-installable test; LLM discarded (D3) |
| No data-conflict handling | Policy-vs-practice audit (95% rule), PII scan, team-name ambiguity gate |
| Cost = "₹0" | Full arithmetic via `scripts/numbers.py`, volume measured not assumed, maintenance stated |
| Plan only | Plan + tested code (extracted from this file and run on synthetic data) + early checkpoint submission |

**Dissent kept on record:** the First Principles expert would drop the 90% framing from the memo entirely; the Outsider argued Ritu will still want a yes/no. Chairman's call: keep both numbers, explain once, lead with the decision.

**The one thing to do first:** run Phase 1's audit and read the bot-vs-final crosstab. Every other decision in this file branches on that table.
