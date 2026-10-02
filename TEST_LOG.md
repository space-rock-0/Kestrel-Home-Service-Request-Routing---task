# Test log — kestrel-router

Every test run, every change, and **the measured effect on accuracy or task
output**. The point of this file is the third thing: a change that does not
improve a measured number is still a change, but it has to say so.

Two kinds of row live here:

1. **Test runs** — `pytest -q` results, and the 14-step order of work in
   `docs/AGENT_TASK.md` with the exit status of each command.
2. **Change entries** — what changed, why, and what moved. "Moved" means a
   number from `artifacts/metrics.json` before vs after.

A change with no measured effect is recorded as **no effect**, not left blank.
That is the honest entry and it is a useful one.

---

## Rules this file follows

- **Numbers come from artifacts.** Every figure below cites its source file
  (`artifacts/metrics.json`, `artifacts/form_values.json`, `artifacts/audit.txt`).
  Nothing is estimated or retyped from memory.
- **The holdout is scored once.** Per `AGENTS.md` and `BUILD.md` D5. If training
  is re-run after a change, the whole test table is re-scored and the previous
  holdout number is marked `superseded`, never quietly replaced.
- **Interpreter is always explicit.** Commands are recorded exactly as run
  (see `errors.md` E1 — bare `python` does not work on this machine).
- **Accuracy changes are shown before → after**, with the delta. A regression is
  recorded as a regression.

---

## Format — test run

```markdown
### Run <n> — <what was tested> — <date>

**Interpreter:** `kestrel-router/.venv/Scripts/python.exe` (Python 3.12.10)

**Command:** `<exact command>`

**Result:** <pass/fail counts and exit code, or the command's exit status>

**Baseline established:** <what this run proves>
```

## Format — change entry

```markdown
### C<n> — <short title> — <date>
**Phase:** <AGENT_TASK.md step> · **Files:** `path/one.py`, `path/two.py`

**Change:** <what was altered, in one or two sentences>

**Why:** <the error, insight or gate that forced it>

**Measured effect:**

| Metric | Before | After | Delta | Source |
|---|---|---|---|---|
| holdout model accuracy | — | — | — | `artifacts/metrics.json` |
| holdout macro-F1 | — | — | — | `artifacts/metrics.json` |
| bot baseline (unchanged reference) | — | — | — | `artifacts/metrics.json` |
| flagged share / coverage | — | — | — | `artifacts/metrics.json` |
| tests passing | — | — | — | `pytest -q` |

**Verdict:** improved · no effect · regression · correctness-only (behaviour
unchanged, bug removed) · plumbing-only (no model change)
```

---

## Baseline — environment and test suite

*The first `pytest -q` baseline is recorded here once the environment is ready
(`errors.md` E1–E3). No model has been trained yet, so there are no accuracy
numbers to baseline — `artifacts/` is still empty.*

### Run 1 — environment + test suite baseline (PRE-CHANGE)
**Date:** 2026-10-02 · **Phase:** 0 · **Status:** pass

**Interpreter:** `kestrel-router/.venv/Scripts/python.exe` (Python 3.12.10)

**Commands and results:**

```
py -m venv .venv                                               -> created
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt -> 37 packages installed
.venv/Scripts/python.exe -m pytest -q                           -> 79 passed, 1 warning in 134.56s   EXIT 0
.venv/Scripts/python.exe -m kestrel doctor                      -> 18 pass, 1 warn, 0 fail              EXIT 0
```

Installed versions of note: pandas 3.0.6, numpy 2.5.3, scikit-learn 1.9.1,
fastapi 0.142.2, pytest 9.1.1, ftfy 6.3.1, pypdf 6.19.0.

**Baseline established:** the suite was green before any change, so Run 2 below is
a true before/after comparison. `doctor` confirmed all 5 roles detected
(`train`, `test`, `resolution`, `teams`, `sample_submission`) and
**validation: 0 warnings**.

---

### Run 2 — after the canonical-queue fix (POST-CHANGE)
**Date:** 2026-10-02 · **Phase:** 1 · **Status:** pass

**Interpreter:** `kestrel-router/.venv/Scripts/python.exe` (Python 3.12.10)

**Commands and results:**

```
.venv/Scripts/python.exe -m pytest -q       -> 86 passed, 1 warning in 182.29s   EXIT 0
.venv/Scripts/python.exe -m kestrel doctor  -> 18 pass, 1 warn, 0 fail             EXIT 0
```

**Result:** 79 → 86 tests. **+7 new tests, 0 failures, 0 regressions** — every
one of the 79 pre-existing tests still passes.

**Baseline established:** step 1 gate (`doctor`, no FAIL) passes. `artifacts/`
still holds only `.gitkeep` — no model trained, so **no accuracy numbers exist
yet**. Do not quote an accuracy figure before step 6.

---

## Order-of-work progress (`docs/AGENT_TASK.md`)

Gates must pass before the next step. Status is `pending` / `pass` / `FAIL` /
`blocked`, and a step is never marked done without its command actually run.

| # | Command | Gate | Status | Logged in |
|---|---|---|---|---|
| 1 | `kestrel doctor` | No FAIL | **pass** — 18 pass / 1 warn / 0 fail | Run 1, Run 2 |
| 2 | `kestrel status` | roles: train, resolution, teams | pending — roles confirmed by doctor | |
| 3 | `kestrel run policy_text` | transfer cost + page ref written down | pending | |
| 4 | `kestrel validate` | `ok: true`, every warning noted | **pass** — ok, 0 warnings | Run 3 |
| 5 | `kestrel audit` | `audit.txt` read in full | **pass** — 138 lines, all 10 Q answered | Run 3 |
| 6 | `kestrel run full_pipeline` | job succeeds, `check` passes | **pass** — 84.53% vs bot 75.00%, check ok | Run 3 |
| 7 | `kestrel run golden` | five cases read, wrong ones reported | **pass** — 3 clean, 2 correctly flagged | Run 3 |
| 8 | `kestrel run audit_rules` | enable only if `recommend_enable` | pending | |
| 9 | read `errors_holdout.csv` | ≥50 errors hand-labelled by cause | pending | |
| 10 | `kestrel run form_values` | `form_values.json` written | pending | |
| 11 | `kestrel run render_docs …` | N from policy PDF, M from user | blocked — needs steps 3, 6 | |
| 12 | fill `output/MEMO.md`, `output/EVIDENCE.md` | no `{{...}}` left | pending | |
| 13 | fill `docs/submission-form.md` | no `⟦...⟧` left | pending | |
| 14 | `kestrel doctor --strict` + `pytest -q` | all pass | pending | |

---

## Change entries

### C1 — Strip the rename date note; one queue = one canonical label
**Date:** 2026-10-02 · **Phase:** 1 · **Status:** correctness — large accuracy effect

**Files:** `kestrel/data/cleaning.py`, `kestrel/data/loader.py`, `tests/test_data.py`

**Change:** Added `RENAME_NOTE` + `bare_team_name()` in `cleaning.py` to strip
the trailing `(from 15 Jan 2026)` note from `teams.csv`'s `renamed_to` cell, and
rewrote the `build_team_map()` tie-break so the current name wins by default and
the old name only wins while it is still strictly more common in the last 60 days.
Both the old and the bare new spelling are now keys in the map. In `loader.py`,
stray labels are reported per column with their row counts.

**Why:** Found by probing the real data before training — `errors.md` E4. The
shipped tie-break compared two absent strings (`0 >= 0`) and adopted the suffixed
string as the canonical label.

**Measured effect** (real `data/input/`, pandas probe before/after):

| Metric | Before | After | Delta | Source |
|---|---|---|---|---|
| Distinct `final_team` values (class count) | 9 | **7** | −2 fragmented classes | probe, real data |
| Labels outside the official 7 | 2 | **0** | −2 | probe, real data |
| Canonical names carrying a date note | 2 | **0** | −2 | probe, real data |
| Rows split across two spellings of one queue | 1,674 (15.5%) | **0** | −1,674 | probe, real data |
| `Installs & Demo` (was split 1006 + 590) | 1,596 fragmented | 1,596 unified | consolidated | probe, real data |
| `Filters & Consumables` (was split 668 + 398) | 1,066 fragmented | 1,066 unified | consolidated | probe, real data |
| Mojibake in `text` after cleaning | 0.0000% | 0.0000% | unchanged | probe, real data |
| Tests passing | 79 | **86** | **+7** | `pytest -q` |

**Accuracy effect — NOT yet measured.** No model has been trained, so there is no
holdout accuracy to compare. What *is* measured is the class count and target
distribution, which accuracy depends on directly:

- the model would have trained on 9 classes, 2 of which are artefacts of a date
  string, with ~15.5% of rows fragmented across them
- `predictions.csv` would have named `Installs & Demo (from 15 Jan 2026)` — a queue
  that exists nowhere in the client's data — and the `check` gate at step 6
  rejects that outright
- macro-F1 and the confusion matrix would both have been computed against a
  fragmented target

The headline number (holdout accuracy vs `final_team`) gets measured at step 6 and
recorded as Run 3. **Do not quote an accuracy figure for this change until then.**

**Verdict:** correctness — a latent defect that would have invalidated the whole
submission. Accuracy effect expected large but unquantified.

---

### C2 — Report unmapped team labels with counts instead of a bare name list
**Date:** 2026-10-02 · **Phase:** 1 · **Status:** plumbing-only

**Files:** `kestrel/data/loader.py`, `tests/test_data.py`

**Change:** The `unknown_team_names` warning now loops over `final_team` and
`bot_team` separately and reports `<label> (<n> rows)` per stray value.

**Why:** A bare name list does not say how much data is affected, so a 2-row
stray and a 1,600-row one look identical in the job log.

**Measured effect:**

| Metric | Before | After | Delta | Source |
|---|---|---|---|---|
| Rows dropped silently | 0 | 0 | none — condition is vacuous on real data | probe |
| Stray labels reported with counts | no | yes | 2 columns covered | `loader.py` |
| Tests passing | 79 | 86 | +3 covering this | `pytest -q` |

**Verdict:** plumbing-only — no model change, no data change. Makes a future
recurrence of `errors.md` E4 impossible to miss.

---

### Run 3 — full pipeline: validate → audit → train → check
**Date:** 2026-10-02 · **Phase:** 2 (steps 4–6 + 7) · **Status:** pass

**Interpreter:** `kestrel-router/.venv/Scripts/python.exe` (Python 3.12.10)

**Commands and results:**

```
.venv/Scripts/python.exe -m kestrel run full_pipeline   -> EXIT 0, all 4 steps ok
    validate          ok: true, 0 warnings
    audit             wrote artifacts/audit.txt (138 lines)
    train             model_accuracy 0.8453, bot_accuracy 0.75, CI [0.8238, 0.8668]
    check_submission  ok: true, 2178 rows, 0 errors, 0 warnings
.venv/Scripts/python.exe -m kestrel run golden          -> 5 cases, 3 clean + 2 correctly flagged
```

**Baseline established:** the first trained model and the first
`artifacts/predictions.csv`. **The holdout has now been scored — once.**
Everything downstream (steps 7–14) reuses these numbers; they are not recomputed.

**Headline (holdout, 976 most recent closed CRM rows, scored once):**

| | Accuracy vs `final_team` | 95% interval | Macro-F1 |
|---|---|---|---|
| Bot (incumbent) | 75.00% | 72.33% – 77.46% | 76.44% |
| This model | **84.53%** | 82.38% – 86.68% | 84.38% |
| Agreement with the bot's own label | 78.59% | — | 79.64% |

**+9.53 points over the bot; the two intervals do not overlap (4.92-point gap),**
so the improvement is distinguishable from noise, which is what `docs/BUILD.md`
§7 requires before a win may be claimed.

**<90%. Both definitions.** Accuracy vs outcomes is 84.53% (interval tops out at
86.68%). Agreement with the bot's own labels — the easier, wrong bar — is 78.59%.
The target is not met on either reading. Reported as a finding, not engineered
around (`decisions.md` D11). Memo option B is a live outcome.

**Confidence gate:** τ=0.55, **16.80%** flagged for a person; accuracy **95.69%**
on unflagged rows vs **29.27%** on flagged rows. The flagged pile really is the
ambiguous pile.

---

### Run 4 — add a leak-free rolling-origin CV (reporting only)
**Date:** 2026-10-02 · **Phase:** 2 · **Status:** pass

**Commands and results:**

```
.venv/Scripts/python.exe -m kestrel train    -> EXIT 0
    rolling-origin CV (training rows only): mean acc 0.8385 over 4 folds
    holdout accuracy model=0.8453 bot=0.75
```

**Baseline established:** the "cross-validation accuracy" figure, measured the
only way it can be measured without leaking. Forward-chaining over time, on
training rows only — see `decisions.md` D10.

| fold | trained on | scored on | accuracy |
|---|---|---|---|
| 1 | 4,320 | 2025-10-01 → 2025-11-18 | 82.06% |
| 2 | 5,457 | 2025-11-18 → 2026-01-03 | 85.06% |
| 3 | 6,595 | 2026-01-03 → 2026-02-22 | 83.13% |
| 4 | 7,733 | 2026-02-22 → 2026-04-08 | 85.15% |
| **mean** | | | **83.85%** (macro-F1 83.63%) |

**Leak-freedom proof.** This re-run re-scored the holdout, which is exactly what
D5 forbids using it for. So the comparison was snapshotted beforehand and diffed
afterwards:

| Field | Run 3 vs Run 4 |
|---|---|
| `split`, `chosen_params`, `validation`, `gate_from_validation` | **identical** |
| `holdout`, `per_class_holdout`, `test` | **identical** |
| `predictions.csv` | **byte-for-byte identical** |
| only differences | `cv_rolling` (new key), `trained_at` (timestamp) |

The model is unchanged and the holdout number is unchanged, so nothing was tuned
on it. The second look confirmed the first; it did not inform anything.

**Post-change suite:**

```
.venv/Scripts/python.exe -m pytest -q           -> 86 passed, 1 warning in 50.95s   EXIT 0
.venv/Scripts/python.exe -m kestrel doctor      -> 20 pass, 0 warn, 0 fail           EXIT 0
```

`doctor` went from 18 pass / 1 warn to **20 pass / 0 warn** — the only outstanding
warning was "trained model: not trained yet", which training cleared.

---

### C3 — Add `rolling_cv`: forward-chaining validation on training rows only
**Date:** 2026-10-02 · **Phase:** 2 · **Status:** reporting-only

**Files:** `kestrel/ml/train.py`

**Change:** Added `rolling_cv()` and wired its result into `metrics.json` as
`cv_rolling`. It fits on every training row older than each fold's CRM test slice
and scores that slice, over 4 folds. Nothing else in `train()` changed.

**Why:** The Phase 2 acceptance criterion asks for "cross-validation accuracy".
Random K-fold is forbidden (`decisions.md` D10, `docs/BUILD.md` T5), so the
criterion is answered with a leak-free equivalent rather than obeyed literally or
dropped.

**Measured effect:**

| Metric | Before | After | Delta | Source |
|---|---|---|---|---|
| Rolling-origin CV mean accuracy | not measured | **83.85%** | new | `metrics.json` `cv_rolling` |
| Rolling-origin CV range | — | 82.06% – 85.15% | new | `cv_rolling` |
| Holdout accuracy | 84.53% | 84.53% | **0.00** | verified identical |
| Bot baseline | 75.00% | 75.00% | **0.00** | unchanged reference |
| Chosen params | `C=3, cw=None, zw=1.0` | identical | **0.00** | verified identical |
| `predictions.csv` | 2,178 rows | identical bytes | **0.00** | `cmp` |
| Tests passing | 86 | 86 | **0** | `pytest -q` |
| `doctor` | 18 pass / 1 warn | 20 pass / 0 warn | +2 checks clear | `doctor` |

**Accuracy effect: none, by design.** The CV confirms the holdout rather than
moving it — CV mean **83.85%** vs holdout **84.53%**, a 0.68-point gap. That
agreement is the useful result: the holdout slice is representative, and the
number is not a fluke of one slice.

**Verdict:** reporting-only. No model change, no prediction change, zero
regression. Added evidence, not an improvement.

---

### Run 5 — Phase 3: versioned endpoint, frontend, packaging
**Date:** 2026-10-02 · **Phase:** 3 · **Status:** pass

**Interpreter:** `kestrel-router/.venv/Scripts/python.exe` (Python 3.12.10)

**Commands and results:**

```
.venv/Scripts/python.exe -m pytest -q                                  -> 93 passed   EXIT 0   (86 -> 93, +7)
.venv/Scripts/python.exe -m kestrel doctor                             -> 20 pass, 0 warn, 0 fail   EXIT 0
.venv/Scripts/python.exe -m kestrel check                              -> ok: true, 2178 rows, 0 errors   EXIT 0
.venv/Scripts/python.exe -m uvicorn kestrel.api.app:app --port 8077    -> booted clean
```

**Live server, not the test client:**

```
GET  /api/health                      -> 200 {"status":"ok","model_ready":true,"watcher_running":true}
GET  /                                 -> 200   GET /static/app.js -> 200   GET /static/style.css -> 200
POST /api/v1/predict  (raw test row)  -> 200   Repairs, conf 0.976, flagged false
POST /api/v1/predict  (Meenal #1)      -> 200   Installs & Demo, conf 0.998, flagged false
GET  /openapi.json                    -> /api/v1/predict present, /api/route correctly absent
```

**Browser verification of the web UI** — driven, not assumed:

| Step | Result |
|---|---|
| Page load | badge reads **"model ready"**, all 5 tabs present |
| Dropdowns populated from `/api/meta` | 7 products, 3 warranties, 4 channels |
| Submit "I paid for the installation but nobody has come yet" | **Installs & Demo**, 100%, justification rendered |
| Submit "please call me about my purifier" | card flips to `card warn`, clarifying question shown, 44% flagged |
| Results tab | all 8 measured metrics rendered from `metrics.json` |
| Browser console | **zero errors** |

**Healthcheck command verified against a live server and a dead port:** exit 0 when
`/api/health` answers 200, exit 1 when nothing is listening.

**Baseline established:** the service surface is now externally reachable and
browser-verified. `predictions.csv` and `model.joblib` are byte-unchanged by this phase — no
retraining happened.

**Not verified:** `docker build` and `make run`. Neither `docker` nor `make` is installed on this
machine (`errors.md` E7). Both were checked by inspection and by running every command they wrap,
but neither was executed. Recorded in `README.md` §Limits.

---

### C4 — Add `POST /api/v1/predict` as the one documented endpoint
**Date:** 2026-10-02 · **Phase:** 3 · **Status:** feature

**Files:** `kestrel/api/app.py`, `static/app.js`, `static/style.css`, `tests/test_api.py`,
`README.md`

**Change:** Added `PredictRequest` (accepts a `test_unlabelled.csv` row verbatim, all fields
optional) and `PredictResponse` (Pydantic V2 response model, so `/docs` is accurate). Both
endpoints now call one internal `_predict()`. `/api/route` kept but `include_in_schema=False`.
The web page posts to `/api/v1/predict` and renders `predicted_team` + `justification` +
runner-up instead of a raw reasons list.

**Why:** Phase 3 brief; also removes the two-endpoints-doing-one-thing problem. `decisions.md` D12.

**Measured effect:**

| Metric | Before | After | Delta | Source |
|---|---|---|---|---|
| Documented predict endpoints | 1 (`/api/route`) | **1** (`/api/v1/predict`) | 0 — deliberately not 2 | `openapi.json` |
| Contract fields returned | `team`, `reasons` | **+`predicted_team`, `justification`** | +2 | live POST |
| Accepts a raw test row verbatim | no | **yes** | new | live POST |
| Tests passing | 86 | **93** | **+7** | `pytest -q` |
| `doctor` | 20 pass / 0 warn | 20 pass / 0 warn | unchanged | `doctor` |
| `predictions.csv` | 2,178 rows | identical | **0** | not regenerated |
| `model.joblib` | 428,746 B | unchanged | **0** | not retrained |
| Browser console errors | — | **0** | — | browser |

**Accuracy effect: none.** No model was retrained. Holdout remains **84.53%** vs bot **75.00%**.

**Verdict:** feature — new capability, zero regression, no effect on any measured model number.

---

### C5 — Ship the model in the Docker image; stop shadowing it with a volume
**Date:** 2026-10-02 · **Phase:** 3 · **Status:** correctness

**Files:** `.dockerignore`, `Dockerfile`, `Makefile`

**Change:** `.dockerignore` allows `artifacts/model.joblib` + `metrics.json` through and still
excludes all of `data/input/`. Removed `VOLUME /app/artifacts`. Added explicit `ENV`,
`PYTHONUNBUFFERED=1` and a `HEALTHCHECK`. Rewrote the `Makefile` so `PY` prefers the project
`.venv` and no command runs at parse time.

**Why:** As shipped, `docker run` started a service that answered **503 `model_not_ready`** to
everything — `.dockerignore` excluded the model and `VOLUME` would have hidden it anyway.
`decisions.md` D14, D15; `errors.md` E7.

**Measured effect:**

| Metric | Before | After | Delta |
|---|---|---|---|
| Model inside the image | **none** | `model.joblib` + `metrics.json` | fixed |
| Volume shadowing the model | **yes** | removed | fixed |
| `make run` interpreter | bare `python` (fails on Windows, E1) | `.venv` interpreter | fixed |
| Parse-time side effects in `make` | 1 shell call on every target | none | removed |
| Healthcheck | absent | `/api/health`, verified exit 0/1 | new |
| Tests passing | 86 | 93 | +7 |
| Image actually built | **no** | **no** — `docker` unavailable | unchanged |

**Verdict:** correctness — two real defects fixed. **Not verified end-to-end**: no `docker` on
this machine, so the image was never built. Stated in `README.md` §Limits rather than glossed.

---

These need the human. They stay listed here until the user closes them, and are
repeated in the final report.

| Item | Why | Owner |
|---|---|---|
| Screen recording (≤3 min) | Needs a person on screen | user |
| Google Drive upload + public link | Needs the user's account | user |
| GitHub repository creation and push | Needs the user's account | user |
| Honest hours spent | Only the user knows | user |
| What AI tools were used and their cost | Only the user knows | user |
| Hosting price | Depends on the user's infrastructure | user |
| Memo option A vs B | The rule suggests; the user owns the call | user |