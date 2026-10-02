# Error log — kestrel-router

Every error hit while working this project: what it looked like, why it
happened, what fixed it, and whether it can come back.

Written at the moment the error is understood, not at the end of the session.
If a fix is a workaround rather than a repair, say so — workarounds expire.

Status values: `fixed` · `worked-around` · `open` · `recurring`

---

## Format

```markdown
## E<n> — <short title>
**Date:** YYYY-MM-DD · **Phase:** <step> · **Status:** fixed

**Symptom:** <the exact command and output the user or tool saw>

**Root cause:** <why it happened>

**Fix:** <what changed, and where — file:line where possible>

**Guard added:** <the check, test or rule that stops it returning>

**Can it recur?** <yes/no + the condition>
```

---

## E1 — `python` is not on `PATH`; only the `py` launcher works
**Date:** 2026-10-02 · **Phase:** 0 (environment) · **Status:** worked-around

**Symptom:**

```
$ python --version
Python was not found; run without arguments to install from the Microsoft Store,
or disable this shortcut in Settings > Apps > Advanced app settings > App
execution aliases.
Exited with code 49
```

Every documented command in `README.md`, `AGENTS.md`, `docs/AGENT_TASK.md` and
the `Makefile` starts with `python -m kestrel …`, so all of them fail as written.

**Root cause:** The Microsoft Store `python` alias stub shadows the real
interpreter. The actual interpreter is reachable only through the launcher:
`py` → `C:\Users\Varma\AppData\Local\Python\pythoncore-3.12-64\python.exe`
(3.12.10, 64-bit, the only install on the machine).

**Fix:** Use the project-local interpreter for every command:

```
kestrel-router/.venv/Scripts/python.exe -m kestrel …
kestrel-router/.venv/Scripts/python.exe -m pytest -q
```

**Guard added:** The `.venv` path is recorded in `decisions.md` D1. Every entry
in `TEST_LOG.md` and `errors.md` cites the interpreter used, so a command can
always be replayed exactly. Do not "fix" a future error by switching back to
bare `python`.

**Can it recur?** Yes, if anyone runs the documented commands verbatim. This is
a machine quirk, not a project bug — the repo's instructions are correct for a
normal Python install and must stay that way for the client's clean-machine test.

---

## E2 — Six required Python packages are missing
**Date:** 2026-10-02 · **Phase:** 0 (environment) · **Status:** fixed

**Symptom:** Import probe against the global interpreter:

```
  OK   pandas
  OK   numpy
  MISS sklearn: ModuleNotFoundError     <- scikit-learn, required by kestrel/ml
  OK   scipy
  OK   joblib
  MISS ftfy: ModuleNotFoundError        <- mojibake repair, required by kestrel/data
  OK   openpyxl
  MISS fastapi: ModuleNotFoundError     <- required by kestrel/api
  MISS uvicorn: ModuleNotFoundError     <- required to serve
  OK   pypdf
  MISS pytest: ModuleNotFoundError      <- required by AGENTS.md before every change
  MISS httpx: ModuleNotFoundError       <- required by tests/test_api.py
```

**Root cause:** Nothing was installed for this project. `.venv` did not exist.

**Fix:** `py -m venv .venv` then
`.venv/Scripts/python.exe -m pip install -r requirements-dev.txt`.

**Guard added:** `python -m kestrel doctor` already checks all nine required
modules by name and prints `pip install -r requirements.txt` on failure — this
error is self-diagnosing in future. Run doctor first in any new environment.

**Can it recur?** Only in a fresh clone, which is exactly what
`docs/AGENT_TASK.md` step 14 (clean-machine test) is designed to catch.

---

## E3 — `pytest -q` could not run, blocking the "before and after every change" rule
**Date:** 2026-10-02 · **Phase:** 0 (environment) · **Status:** fixed

**Symptom:** `pytest` was not importable by any interpreter on the machine, so
the `AGENTS.md` rule *"Run `pytest -q` before and after every change"* was
unsatisfiable.

**Root cause:** Same as E2 — no project environment existed.

**Fix:** `pytest>=8.0` and `httpx>=0.27` come from `requirements-dev.txt`, which
now installs into `.venv`. The baseline run is the first entry in `TEST_LOG.md`.

**Guard added:** `TEST_LOG.md` requires a recorded baseline before any change.
If a later entry has no "before" row, the change was not measured properly and
should be treated as unverified.

**Can it recur?** Only on a fresh clone.

---

---

## E4 — Rename date note became part of the canonical team name, splitting one queue into two classes
**Date:** 2026-10-02 · **Phase:** 1 · **Status:** fixed

**Symptom:** Found by probing the real data before training, not by a test. With
the shipped code, `build_team_map()` on the real `data/input/` produced:

```
'Installations'  -> 'Installs & Demo (from 15 Jan 2026)'
'Consumables'    -> 'Filters & Consumables (from 15 Jan 2026)'

canon (7): ['Billing', 'Filters & Consumables (from 15 Jan 2026)',
            'Installs & Demo (from 15 Jan 2026)', 'Product Advice',
            'Repairs', 'Returns & Replacement', 'Warranty Claims']
```

and `final_team` ended up with **nine** distinct values, two of them outside
`canon`:

```
Installs & Demo (from 15 Jan 2026)  1006   <- old spelling "Installations"
Filters & Consumables (from ... )     668   <- old spelling "Consumables"
Installs & Demo                      590   <- UNMAPPED, should be the same queue
Filters & Consumables                398   <- UNMAPPED
values NOT in canon: ['Filters & Consumables', 'Installs & Demo']
```

**Root cause:** Two compounding faults in `build_team_map()`
(`kestrel/data/cleaning.py`):

1. **The note was never stripped.** `renamed_to` in `teams.csv` is the team name
   plus a human note — `"Installs & Demo (from 15 Jan 2026)"`. The code used the
   whole string as a name.
2. **The tie-break fell through to it.** The line was
   `canon = b if recent.get(b, 0) >= recent.get(a, 0) else a`. `recent` counts
   `team_label` over the last 60 days of training data, which uses the **bare
   new** name. So `recent.get(b)` — the suffixed string — was `0`, and
   `recent.get(a)` — the old name, also long gone — was *also* `0`. `0 >= 0` is
   true, so the suffixed label won by accident.

Because the bare new name was not a key in the map either, it was never remapped
at all: `tmap.get(s, s)` passed it straight through.

**Impact if it had shipped:** the model would have trained on **9 classes instead
of 7**, with `Installs & Demo (from 15 Jan 2026)` and `Installs & Demo` as two
separate classes for the same queue. Roughly **1,674 rows (15.5% of the dataset)**
would have been split across classes that are one queue. Two consequences:
`predictions.csv` would name a queue string that exists nowhere in the client's
data, so the `check` gate rejects the submission outright; and per-class accuracy,
the confusion matrix and macro-F1 would all be wrong, because ~15% of the target
column was fragmented by a date string.

**Fix:** `kestrel/data/cleaning.py` — added `RENAME_NOTE` regex and
`bare_team_name()` to strip a trailing `(from …)` / `(since …)` note, and rewrote
the tie-break so the **current** name wins by default and the old name only wins
while it is still strictly more common in recent data. `kestrel/data/loader.py` —
stray labels are now counted per column and named in the message.

**Guard added:** four new tests in `tests/test_data.py` —
`test_bare_team_name_strips_the_change_date_from_the_teams_file`,
`test_canonical_team_names_never_carry_a_date_note`,
`test_a_queue_renamed_with_a_date_note_stays_one_queue`,
`test_targets_strictly_match_the_seven_official_queues`.

**Can it recur?** Not in the same form — the note is now stripped and both
spellings are keys. It would recur only if `teams.csv` adopted a **new** kind of
note that `RENAME_NOTE` does not match, e.g. `"Installs & Demo (was: Installation)"`.
The guard `test_canonical_team_names_never_carry_a_date_note` only checks for a
parenthesis opening with *from/since/renamed/effective*, so that shape would pass
it. **Mitigation: read `canon` from the audit output at step 5 and confirm all
seven names are clean.** That check is now in `NOTES.md`.

---

## E5 — `sample_submission.csv` carries no naming signal
**Date:** 2026-10-02 · **Phase:** 1 · **Status:** worked-around

**Symptom:** `docs/BUILD.md` T3 and `docs/AGENT_TASK.md` both say to settle the
canonical team naming against `sample_submission.csv` — "if the team values use a
different naming than the canonical set, use the sample's naming for output".

All **2,178** rows of `data/input/sample_submission.csv` contain the single value
`Repairs`. It is a placeholder, not a sample, so it says nothing about whether the
expected naming is old-style or new-style.

**Root cause:** The file provided is a template with one example value filled in,
not a representative extract. Not a bug in our code.

**Fix:** Resolved from date evidence instead. `Installations` and `Consumables`
stop appearing after 2026-01 and are absent from the last 60 days of training
data; `Installs & Demo` and `Filters & Consumables` appear from 2026-01 onward.
The test set begins 2026-07-01, entirely after the 15 Jan 2026 rename, so the
new names are correct. Recorded in `NOTES.md` and `decisions.md` D5.

**Guard added:** None possible in code — the input carries no signal. The audit at
step 5 prints the canonical set, and `check` at step 6 will still catch an
out-of-set name in `predictions.csv` before submission.

**Can it recur?** Only with another placeholder-only template. Do not treat this
file as evidence of naming in any future phase.

---

---

## E6 — `rolling_cv` crashed on the last split edge
**Date:** 2026-10-02 · **Phase:** 2 · **Status:** fixed

**Symptom:** `python -m kestrel train` failed before writing anything:

```
File "kestrel/ml/train.py", line 86, in rolling_cv
  edges = [crm.ts.iloc[int(n * k / n_splits)] for k in range(n_splits + 1)]
IndexError: single positional indexer is out-of-bounds
```

**Root cause:** my own off-by-one, in the function I added minutes earlier.
`range(n_splits + 1)` runs `k` from `0` to `n_splits` **inclusive**. At
`k = n_splits` the expression `int(n * n_splits / n_splits)` evaluates to `n`,
and `.iloc[n]` is one past the last valid position on a frame of length `n`.

**Fix:** clamp the index to `n - 1`:

```python
edges = [crm.ts.iloc[min(int(n * k / n_splits), n - 1)] for k in range(n_splits + 1)]
```

**Guard added:** the function already guards the *size* conditions (`n < min_train`,
no fold scoring at least `min_test` rows, `len(tr_part) < min_train`). This crash
was an unguarded **index**, not a data condition. A one-line comment at the clamp
states why, so the next reader does not "simplify" it away.

**Nothing was overwritten.** The crash happened inside `rolling_cv`, which runs
*before* the holdout is scored and before `metrics.json` / `model.joblib` are
written — so `artifacts/` still held the previous run's output, and the failed
invocation never touched the holdout.

**Can it recur?** No — `min(…, n - 1)` is correct for every `k` in range.

---

---

## E7 — The Docker image could never answer a request
**Date:** 2026-10-02 · **Phase:** 3 · **Status:** fixed (unverified end-to-end)

**Symptom:** Found by reading the packaging files, not by running them. The container's stated
job is to start the service; it could not have.

**Root cause:** two defects that hide each other.

1. `.dockerignore` contained `artifacts/*`, so `COPY . .` never copied
   `artifacts/model.joblib` into the image. There was no model.
2. `Dockerfile` declared `VOLUME ["/app/data/input", "/app/artifacts"]`. A Docker volume mounted
   over a path **shadows** whatever the image contains there, so even with the model baked in,
   `/app/artifacts` would have been an empty volume at run time.

The service would have started, reported `"status": "ok"` on `/api/health` — and answered
**503 `model_not_ready`** to every prediction. A healthcheck that only checks the process would
have called that healthy.

**Fix:** `.dockerignore` now excludes every artifact *except* `model.joblib`, `metrics.json` and
`.gitkeep`, and still excludes all of `data/input/` so customer data is never baked in. The
`/app/artifacts` volume is removed; only `/app/data/input` remains a mount point.

**Guard added:** a `HEALTHCHECK` against `/api/health`, plus README wording that makes the mount
behaviour explicit.

**Verification — partial, and the gap is real.** The healthcheck *command* was executed against
a live server (exit 0) and against a closed port (exit 1), so that part works. **`docker` is not
installed on this machine, so `docker build` was never run.** The image is unverified. It is
recorded as a known limit in `README.md` §Limits and must be built before the client is promised a
container.

**Can it recur?** Yes, quietly — any future `.dockerignore` edit that re-adds `artifacts/*` brings
it straight back, and nothing fails until someone runs the container. The honest fix is to build
the image in CI; that is out of scope here.

---

## E8 — `uvicorn kestrel.api.app:app` did not exist
**Date:** 2026-10-02 · **Phase:** 3 · **Status:** fixed

**Symptom:** `kestrel.api.app` defined only `create_app()`. There was no module-level `app`, so
the documented ASGI command failed with an import error.

**Root cause:** The CLI serves via `uvicorn.run(create_app(settings), ...)`, which never needed a
module-level object, so the gap was invisible until an external ASGI server was required.

**Fix:** PEP 562 module `__getattr__` that builds the app on first access. Verified by actually
starting `uvicorn kestrel.api.app:app --port 8077` and driving it.

**Rejected the obvious fix:** `app = create_app()` at module scope. `AppContext.__init__` calls
`settings.ensure_dirs()` and loads every plugin and skill, so that would construct a real context
against the real `data/input/` on every import — including all 93 tests, which import
`create_app` from this module. Lazy resolution gives the server a real app and keeps the import
inert. See `decisions.md` D13.

**Can it recur?** No.

---

## E9 — Test asserted a warning that the code correctly does not raise
**Date:** 2026-10-02 · **Phase:** 3 · **Status:** fixed

**Symptom:** My own new test failed:

```
assert ('Technical Support' and [])
AssertionError
```

**Root cause:** I asserted that posting `{"request_text": "hi"}` returns warnings. It does not,
and should not — the "no request text" warning fires only when the text is **empty**. `"hi"` is
text. The empty payload `{}` is the case that warns.

**Fix:** Split the assertions — `{}` must warn (empty text, metadata-only decision), `"hi"` must
not warn (a normal request).

**Note:** this was a wrong test, not a wrong endpoint. Recorded because the rule still holds — a
failing test is evidence about the test until proven otherwise.

**Can it recur?** Only by writing assertions from memory instead of from the behaviour.

---

## Template for new entries

Keep it short. The useful parts are: the **exact** command and output, the
**file that had to change**, and the **check that now prevents it**. Anything a
future session could trip over belongs here; routine typing mistakes do not.