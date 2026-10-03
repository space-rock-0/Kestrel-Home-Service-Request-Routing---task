# Decision log — kestrel-router

Every key decision made while working this project, in order. Written as it is
made, not reconstructed at the end.

Each entry answers: what was decided, why, what was rejected instead, and what
would make us revisit it. Project-level rules that were fixed before this work
started (target = `final_team`, no `source` feature, no paid API, holdout
touched once) are **not** repeated here — they live in `AGENTS.md`,
`docs/ARCHITECTURE.md` and `docs/BUILD.md` §3.

Status values: `active` · `superseded` · `revisited` · `rejected`

---

## Format

```markdown
## D<n> — <short title>
**Date:** YYYY-MM-DD · **Phase:** <AGENT_TASK.md step> · **Status:** active

**Decision:** <what was chosen>

**Why:** <the reason, ideally with the number or file that forced it>

**Rejected:** <the alternative, and why it lost>

**Revisit if:** <the condition that would change this>
```

---

## D1 — Use a project-local `.venv`; run everything through its interpreter
**Date:** 2026-10-02 · **Phase:** 0 (environment) · **Status:** active

**Decision:** Create `kestrel-router/.venv` from the Python 3.12.10 install and
use `.venv/Scripts/python.exe` for every project command, including `pytest`.

**Why:** On this machine `python` is not on `PATH` (it resolves to the Microsoft
Store stub and exits 49). Only the launcher `py` works. `pytest` was not
installed globally, and `sklearn`, `ftfy`, `fastapi`, `uvicorn`, `httpx` were all
missing — so `python -m kestrel doctor` would have failed its own module checks
and step 1 of the order of work could not start. Installing into the project
folder rather than the global interpreter also matches the clean-machine test in
`docs/AGENT_TASK.md` step 14 and keeps the global environment untouched.

**Rejected:**
- Global `pip install` — pollutes the machine, makes the clean-machine test
  impossible to trust, and `AGENTS.md` scopes work to this folder.
- Installing into the base Python and aliasing `python` — not reproducible for
  whoever clones the repo.

**Revisit if:** The project needs to run on a machine where `.venv` cannot be
created (no write access). Fall back to a documented one-line install in the
README.

---

## D2 — Audit findings go in `NOTES.md`, decisions stay in `decisions.md`
**Date:** 2026-10-02 · **Phase:** 0 (setup) · **Status:** active

**Decision:** Two separate files. `NOTES.md` records only **what the data says**
(what the audit found, with numbers). `decisions.md` records only **what we chose
to do about it**.

**Why:** `docs/AGENT_TASK.md` steps 4 and 5 explicitly require `NOTES.md` to hold
the audit answers, and `docs/BUILD.md` §13 checks it. Merging the two would make
`NOTES.md` unreadable as an evidence document, and would mix "the data is like
this" with "we decided this", which are different kinds of claim and get
verified differently.

**Rejected:** One combined file — fewer files, but a reviewer cannot tell a
measurement from a choice.

**Revisit if:** The submission form starts requiring decisions inline with
findings. Until then, keep them separate.

---

## D3 — Track the run in `TEST_LOG.md` and `PROMPTS.md` at the project root
**Date:** 2026-10-02 · **Phase:** 0 (setup) · **Status:** active

**Decision:** Root-level `TEST_LOG.md` (every test run, what changed, and the
measured effect on accuracy or task output) and `PROMPTS.md` (the prompts that
drove each phase, verbatim enough to replay).

**Why:** The project already records machine numbers in `artifacts/`, but not
the **reasoning trail**: which option was chosen, what it cost, what failed on
the way. Without it the work cannot be reproduced or defended to the client, and
`docs/submission-form.md` Q8 asks what AI was used for — which needs a real
record, not a reconstruction.

**Rejected:** `docs/` subfolder — the root is what gets opened first, and these
are working logs rather than deliverables. Only `NOTES.md`, `EVIDENCE.md`,
`MEMO.md` and `submission-form.md` are deliverables, and those live in `docs/`.

**Revisit if:** The client-facing repo gets a cleanliness pass. Then these move
to a clearly-marked working-docs folder; they are process records, not evidence.

---

## D4 — Do not trust `docs/BUILD.md`'s team names for anything the client sees
**Date:** 2026-10-02 · **Phase:** 0 (setup) · **Status:** active

**Decision:** Treat `data/input/teams.csv` as the only source of canonical team
names. The team list inside `docs/BUILD.md` is synthetic data-generator output
and is wrong for this dataset.

**Why:** `BUILD.md` names `Technical Support, Installation, Billing, Returns &
Refunds, Escalations, Consumables & Spares, Warranty & Shield`. The real
`teams.csv` names `Installations, Repairs, Consumables, Billing, Returns &
Replacement, Warranty Claims, Product Advice`. Only `Billing` and `Consumables`
even partially overlap. `BUILD.md` says its own code blocks are superseded by
`kestrel/`, and `AGENT_TASK.md` forbids extracting code from it — the same
applies to its synthetic constants.

**Rejected:** Using `BUILD.md`'s list because the memo templates were written
against it. The templates use `{{placeholders}}`, not literal names, so there is
nothing to reuse.

**Revisit if:** `artifacts/audit.txt` prints a canonical set that disagrees with
`teams.csv`. Then the audit's logic is the defect and gets fixed.

---

## D5 — `teams.csv` rename values carry a date suffix and must be stripped
**Date:** 2026-10-02 · **Phase:** 1 · **Status:** active — *confirmed on real data, fix in place*

**Decision:** Parse `renamed_to` by stripping the trailing note, so
`Installs & Demo (from 15 Jan 2026)` becomes `Installs & Demo`. A renamed team
is **one queue with two spellings**; both spellings map to the single bare new
name. The new name wins by default; the old name only wins while it is genuinely
still the more common one in the last 60 days of training data.

**Why:** Confirmed against the real files. `data/input/teams.csv` writes the note
inline. The previous tie-break was
`canon = b if recent.get(b, 0) >= recent.get(a, 0) else a`, and both counters
were **zero** — the newest 60 days of training data use the *bare* new name
`Installs & Demo`, so neither the suffixed nor the old spelling appears. `0 >= 0`
is true, so the suffixed string was adopted as the canonical label. See `errors.md`
E4 for the full failure and `TEST_LOG.md` C1 for the measured effect.

The data confirms the rename is real and complete:

| team | old name rows | new name rows |
|---|---|---|
| Installations → Installs & Demo | 745 | 440 |
| Consumables → Filters & Consumables | 927 | 531 |

`Installations` and `Consumables` stop entirely after 2026-01; `Installs & Demo`
and `Filters & Consumables` begin in 2026-01 and hold for every later month. The
test set starts 2026-07-01, so it is entirely post-rename and must be answered
with the **new** names.

**Rejected:**
- Keeping the old name as canonical — it is correct as a *fallback* when the old
  spelling is still the one in recent use, but wrong here, because the newest data
  has already moved to the new name.
- Dropping the suffix without also mapping the bare new name — the bare name was
  not a key in the map, so it would have fallen through unchanged and become a
  stray class.
- Taking the canonical name from `sample_submission.csv` — it cannot be used.
  All 2,178 rows of that file contain the single placeholder value `Repairs`, so
  it carries **zero** naming signal (see `NOTES.md`).

**Revisit if:** A future pack ships a rename where the old spelling genuinely
dominates the most recent training data. The tie-break handles that case on its
own; no code change needed.

---

## D6 — `.gitignore` contradicts the submission requirements; fix at repo-init time, not now
> **SUPERSEDED by D17 (2026-10-03).** This entry instructed that `data/input/` be committed
> because the brief appeared to require it. It does not: the brief says *"Do not publish it.
> Use a private repository (share access with the address in your invitation) or send a zip.
> A public repository containing the data files is recorded against the submission."*
> Left as `active`, this contradicted D17 and an auditor reading the trail in order hit two
> opposite instructions. Status corrected below.
**Date:** 2026-10-02 · **Phase:** 0 (setup) · **Status:** superseded by D17 — *closed*

**Decision:** Leave `.gitignore` alone for now. When the public repository is
created (step 13), amend it so `artifacts/model.joblib` and `data/input/*` are
committed, because the brief requires the repo to contain the data files and a
working model.

**Why:** The current `.gitignore` excludes exactly what the client must be able
to see:

```
artifacts/*
!artifacts/.gitkeep
data/input/*
!data/input/.gitkeep
!data/input/README.md
```

`docs/BUILD.md` Phase 13 requires committing `artifacts/model.joblib` (checked
< 50 MB), `predictions.csv` and `data/*` as supplied, and Phase 14 requires that
a fresh clone runs without the data present. Meanwhile `BUILD.md` T12 flags that
the public repo would then contain whatever PII is in the real request text —
the audit has not run, so that count is unknown.

**Rejected:** Amending `.gitignore` immediately — the PII scan has not run
(`NOTES.md`), and whether the committed copy must be masked depends on what the
brief actually permits. Changing it now would commit to an answer we do not have.

**Revisit if:** The PII scan finds anything, or the user says the brief requires
the raw files. Both outcomes change what the committed copy looks like.

---

## D7 — `team_label` is kept; it is the incumbent baseline, not a leak
**Date:** 2026-10-02 · **Phase:** 1 · **Status:** active

**Decision:** Do **not** drop `team_label`. It stays in the dataset, mapped to
canonical names as `bot_team`, and is used for one thing only: scoring the old
routing bot against `final_team` on the holdout.

**Why:** The Phase 1 brief said "Drop `team_label`. Set the target variable to
`final_team`." The second half is correct and is what the code does. The first
half would have destroyed the central piece of evidence in the whole project.

`train.py` computes `holdout.bot_vs_final` from `bot_team`, which is derived
from `team_label`. That number is:

- the "bot is right first time X% of the time" figure in `output/MEMO.md`
- the baseline the model is measured against in `EVIDENCE.md`
- the counterfactual that decides memo **option A vs option B**
- the `wrong_first_touch_rate.bot` input to the entire rupee model in
  `kestrel/services.py::numbers()`
- the input to `docs/submission-form.md` Q4 ("did you push back on the client's
  ask?" — the answer is "yes, here is how wrong the bot was")

Removing it would leave the memo unable to state its own premise, and would
leave the transfer saving with no bot term. `AGENTS.md` forbids `team_label` as
the **training target** — which is a different and narrower rule, and is honoured:
`train.py` fits `pipe.fit(df, df.final_team, ...)`.

**Rejected:**
- Dropping it, per the literal instruction — as above, unrecoverable loss of the
  evidence base, and `numbers()` would silently compute a zero bot error rate.
- Keeping it as a **feature** — that would be the real leak, re-importing the
  bot's mistakes. It is not a feature, and `add_meta()` deliberately excludes it.

**Revisit if:** Never. If the model ever scores *against* the bot's own labels as
its target, this is the moment to revisit — and that is explicitly forbidden by
`AGENTS.md` and `docs/BUILD.md` D1.

---

## D8 — An unmapped team label is counted and reported, never silently dropped
**Date:** 2026-10-02 · **Phase:** 1 · **Status:** active

**Decision:** Rows whose label falls outside the official queues are **kept** and
reported with their exact name and row count, once per column
(`final_team` and `bot_team`). The loader does not drop them.

**Why:** The Phase 1 brief said "Drop records where the final team does not map to
the current 7 operational teams." The *goal* of that instruction — the dataset
must contain only the 7 official queues — is right and is now guaranteed by D5
plus a test. The *means* of silently dropping rows is wrong here:

- a silent drop shrinks the dataset with no trace, so every later number in the
  memo is quietly computed on less data than the reader assumes
- `AGENTS.md` requires raising `KestrelError` subclasses for anything a user can
  fix; an unknown queue name is exactly that, and it is only fixable by the user
  editing `teams.csv`
- on the real data the condition is now **vacuous** — after the D5 fix, zero
  labels fall outside the 7, so no row is dropped and nothing is lost

**Rejected:** Raising a hard error instead of warning — that would break the
pipeline on a dataset that is otherwise fine, and the audit still needs to run so
the problem can be reported rather than crashed into.

**Guard added:** `test_targets_strictly_match_the_seven_official_queues` asserts
zero strays, and `test_a_stray_team_label_is_reported_with_its_row_count` asserts
the message names the label *and* the count.

**Revisit if:** The count of strays is ever non-zero. Then the decision is
escalated to the user with the names and counts, because that means the rename
map or `teams.csv` is wrong and the dataset must be fixed before training.

---

## D9 — `source` stays OUT of the feature set, against an explicit instruction to include it
**Date:** 2026-10-02 · **Phase:** 2 · **Status:** active

**Decision:** The Phase 2 brief asked for One-Hot encoding of
`channel`, `product_family`, `warranty_status` **and `source`**. Three of the four
are encoded. `source` is not, and will not be.

**Why:** `AGENTS.md` states it flatly: *"Do not add `source`, `resolved_at`,
`transfers` or `first_team` as model features. They leak era or outcome."*
`docs/BUILD.md` D11 and trap T4 say the same, and
`docs/ARCHITECTURE.md` lists it as a fixed decision.

The technical reason is specific to this dataset. `source` takes exactly two
values, `crm` and `legacy_zoho`, and it perfectly separates two eras that also
label things differently:

- the **test** file is 100% `crm` (probe: test range starts 2026-07-01, well after
  the Zoho→CRM cutover)
- so at inference time the feature is **constant** and carries no information to
  exploit — it cannot help
- during training it *does* let the model fit a separate decision surface per era.
  The dev split contains both eras; validation and holdout are CRM-only. The
  model would spend capacity on Zoho-era conventions that have no bearing on the
  rows it is actually scored on, while the Zoho rows it down-weights become
  separable by era instead of by content

That is a leak, not a feature. It would make the development number look better
while changing nothing about real performance.

**Rejected:**
- Including it because the instruction named it — the instruction predates this
  project's own written rule, and `AGENTS.md` takes precedence over a task brief.
- Dropping `legacy_zoho` rows instead — a separate question, settled by the
  `zoho_weight` hyper-parameter in the grid (`C3`), which the code already tunes
  on validation. That is the honest way to weigh the era; a perfect era flag is not.

**Guard added:** `test_add_meta_has_no_source_leak` asserts the token column
carries no `crm` value. `build_team_map` and `fit()` both read `source` for
*reporting and weighting only* — never as a matrix column.

**Revisit if:** Never. This is one of the two or three decisions the whole
submission rests on.

---

## D10 — "Cross-validation" means time-ordered folds, never random K-fold
**Date:** 2026-10-02 · **Phase:** 2 · **Status:** active

**Decision:** The Phase 2 acceptance criterion reads *"Cross-validation accuracy
on `final_team` exceeds 90%."* Random K-fold is **not** used. Accuracy is measured
by the existing time-ordered protocol — dev (older) / validation (middle 15%) /
holdout (latest 15% of closed CRM rows, scored once) — plus a **rolling-origin**
time-series CV computed on dev rows only, added as a reporting diagnostic.

**Why:** `docs/BUILD.md` T5: *"Time drift / leakage — test = most recent requests
→ Time-ordered split only. **No random K-fold anywhere**."* D4 fixes the split;
D5 fixes the holdout protocol.

Random K-fold on this dataset is not merely a different choice, it is a wrong
one. It would place recent requests in the training set and older requests in the
validation fold, so the model would be graded partly on data it was trained on.
The test set is the *most recent* requests, so a random-split number is
systematically optimistic — and the entire point of the exercise is an honest
number the client can rely on for a go/no-go decision.

Rolling-origin CV answers the request the same way a practitioner means it —
repeated train-on-the-past, score-on-the-future — without the leak. It runs only
on dev rows, so it cannot touch validation or the holdout.

**Rejected:**
- `cross_val_score` with `KFold(shuffle=True)` — forbidden by T5, and the reason
  this project's headline number exists.
- `StratifiedKFold` — same leak, plus stratification actively fights the class
  imbalance the time split is designed to respect.
- Dropping the criterion and reporting nothing — the user asked for a
  cross-validated figure; a leak-free version of it is the right answer, not a
  refusal.

**Revisit if:** Never for this submission. The criterion is only satisfiable with
a leak, so the criterion is answered, not obeyed.

---

## D11 — 90% is reported, never targeted
**Date:** 2026-10-02 · **Phase:** 2 · **Status:** active

**Decision:** The Phase 2 objective reads *"hits the >90% accuracy benchmark."*
The number is measured and reported. It is **not** an optimisation target, and no
change will be made to move it.

**Why:** This is the central trap of the project, and it is the reason
`docs/explain.md` exists as a standalone document.

Ritu's 90% is defined as **agreement with the old bot's own labels**. Those labels
are the bot's output, not outcomes — the student-copying-a-wrong-classmate
analogy in `explain.md` §5. Accuracy against `final_team`, which is what the
scorer uses, is a *different and harder* question. Chasing 90% would push toward
whatever maximises similarity to the bot, which is the thing being replaced.

`docs/BUILD.md` T13 is unambiguous: *"Never tune against the holdout to hit a
number. State the achieved number and its interval."* And `AGENT_TASK.md`: *"If
the model is not better than the bot, say so. Decision B in the memo is a valid,
honest outcome."*

The acceptance criterion is therefore satisfied by **reporting the measured
accuracy with its bootstrap interval and stating plainly whether it clears 90%** —
not by engineering the figure upward. If it lands below 90%, that is a finding,
and the memo becomes option B.

**Rejected:** Adjusting thresholds, features or the grid until the number clears
90 — tuning to a target number is the exact failure mode T13 exists to prevent,
and it would invalidate the expected-score claim the client compares against a
hidden key.

**Revisit if:** Never within this submission. If the achieved number is below
90%, the correct response is to report it and recommend the gated rollout, not to
re-tune.

---

---

## D12 — `/api/v1/predict` is the one documented endpoint; `/api/route` stays as a hidden alias
**Date:** 2026-10-02 · **Phase:** 3 · **Status:** active

**Decision:** Added `POST /api/v1/predict`, which accepts a payload shaped like a row of
`test_unlabelled.csv` and returns `predicted_team` plus `justification` alongside the
existing fields. Both endpoints call **one** internal function, so they cannot disagree.
`/api/route` keeps working but is excluded from the OpenAPI schema.

**Why:** The Phase 3 brief asked for a versioned `/api/v1/predict`. The existing surface was
`/api/route`, used by `static/app.js`, the README, eight assertions in `tests/test_api.py`, and
the bundled `route_request` plugin tool.

Two ways to do one thing is the failure mode this project keeps guarding against — the same
reason `cities`, `datasources.json` and `rules.json` are single sources of truth. Publishing two
documented endpoints for the same operation invites drift and leaves the client guessing which is
canonical. So the versioned path is canonical and documented; the old path keeps working and is
marked `include_in_schema=False`.

**Rejected:**
- Renaming `/api/route` outright — breaks the web page, the README, the tests and the
  `triage-review` skill's `route_request` tool for no benefit.
- Keeping both in `/docs` — two advertised ways to route a request.
- Two independent handler bodies — they would silently diverge, and the divergence would only
  show up as a support ticket.

**The payload accepts two columns it deliberately ignores.** `created_at_ist` would leak the time
split; `source` separates the Zoho era from the CRM era and is constant across the test set
(D9). Accepting them means a caller can POST a CSV line verbatim instead of hand-picking fields,
and `test_predict_v1_accepts_a_raw_test_row_verbatim` asserts that flipping `source` from `crm`
to `legacy_zoho` changes nothing — which is D9 enforced at the API boundary rather than only in
the feature code.

**Revisit if:** A second major version arrives. Then `/api/v1/*` becomes the frozen legacy
prefix, `/api/v2/predict` becomes canonical, and the same one-implementation rule applies.

---

## D13 — Lazy module-level `app` so `uvicorn kestrel.api.app:app` works without import side effects
**Date:** 2026-10-02 · **Phase:** 3 · **Status:** active

**Decision:** Added a module-level `__getattr__` (PEP 562) in `kestrel/api/app.py` that builds
the app on first attribute access. `uvicorn kestrel.api.app:app` works; importing the module
does not construct an `AppContext`.

**Why:** The acceptance criterion names `uvicorn kestrel.api.app:app`, but the module only
exposed `create_app(settings)`. The obvious fix — `app = create_app()` at module scope — was
wrong here: `AppContext.__init__` calls `settings.ensure_dirs()`, loads every plugin and every
skill. The test suite imports `create_app` from this module, so module scope would have built a
real context against the real `data/input/` on every test run.

Lazy resolution satisfies both: the ASGI server gets a real app, and `import kestrel.api.app`
stays inert.

**Rejected:**
- `app = create_app()` at module level — side effects on every import, including 93 tests.
- Requiring `uvicorn --factory kestrel.api.app:create_app` — changes the documented command the
  client was given, so it fails the acceptance criterion as written.

**Revisit if:** Never. If the project ever needs a second app instance in one process, the
factory stays available and this is a non-issue.

---

## D14 — The Docker image must ship the model, and must not mount over `artifacts/`
**Date:** 2026-10-02 · **Phase:** 3 · **Status:** active

**Decision:** `.dockerignore` now lets `artifacts/model.joblib` and `artifacts/metrics.json` into
the image while still excluding every other artifact and all of `data/input/`. The `VOLUME`
declaration for `/app/artifacts` is removed; only `/app/data/input` stays a mount point.

**Why:** Two compounding defects made the container unable to answer a single request:

1. `.dockerignore` excluded `artifacts/*`, so `COPY . .` shipped **no model at all**
2. even with a model baked in, `VOLUME ["/app/artifacts"]` **shadows** the image's contents — a
   Docker volume mounted over a path hides whatever the image put there

Together they meant `docker run` always started a service that answered
`503 model_not_ready` until something retrained inside the container. For a deliverable whose
stated requirement is that it "boots flawlessly on a clean machine", that is the whole ballgame.

Mounting `/app/data/input` is still correct and necessary — real customer data must not be baked
into an image. Writing artifacts into the container is fine; the service recreates them on the
first pipeline run.

**Also added:** an explicit `ENV` block for the three directories, `PYTHONUNBUFFERED=1` so logs
are not buffered, and a `HEALTHCHECK` against `/api/health`.

**Verified as far as this environment allows:** the healthcheck command was run against a live
server and against a dead port — exit 0 when up, exit 1 when down. **The image itself was never
built**, because `docker` is not installed here. See `README.md` §Limits and E7.

**Revisit if:** The project adopts a real registry or multi-stage build.

---

## D15 — `make` prefers the project's own interpreter
**Date:** 2026-10-02 · **Phase:** 3 · **Status:** active

**Decision:** `PY` resolves to `.venv/Scripts/python.exe`, then `.venv/bin/python`, then
`python3`. Every target wraps it in quotes.

**Why:** `errors.md` E1 — on this machine bare `python` is a Microsoft Store alias that exits 49.
`make run` would have failed at the first command for anyone who followed the README on Windows,
which is precisely the audience the client-side walkthrough targets.

The first draft of this Makefile ran `$(PY) -c "import sys; ..."` at **parse time** to check the
Python version. That executes on every invocation including `make help`, and errors out when
`.venv` does not exist yet. Removed; version checking is left to `doctor`, which reports it
properly.

**Rejected:** Hardcoding `python3` — wrong on Windows, and wrong after `make setup` when the venv
interpreter is the correct one.

**Revisit if:** The project drops `make` in favour of a Python-based task runner.

---

---

## D16 — Dependencies pinned to exact versions
**Date:** 2026-10-02 · **Phase:** 4 (close-out) · **Status:** active

**Decision:** `requirements.txt` and `requirements-dev.txt` now pin every package with `==` to the
versions the project was built and tested against (pandas 3.0.6, numpy 2.5.3, scikit-learn 1.9.1,
fastapi 0.142.2, pytest 9.1.1, and the rest).

**Why:** `docs/BUILD.md` D14 requires it, and the deliverable's core promise is that it starts on a
clean machine with `pip install -r requirements.txt` and nothing else. Every entry was previously
`>=`, so an unpinned install resolves to whatever is newest on the day. This machine resolved to
**pandas 3.0.6** — a very new major version — and it happens to work, but that is luck, not design.
`docs/AGENT_TASK.md` step 14 (fresh clone, fresh venv) is precisely the test that would catch a
breakage, and it cannot be trusted while the inputs float.

**Rejected:** Leaving `>=` and relying on CI to catch it — CI runs on `push`, not at install time on
someone else's machine, and the failure would surface as a broken demo rather than a red build.

**Revisit if:** Upgrading deliberately. Re-run `pytest -q` and the full pipeline before trusting it.

---

## D17 — The policy beats the brief on publishing data: no `data/input/` in the repo
**Date:** 2026-10-02 · **Phase:** 4 · **Status:** active — *user's call, revisitable in writing*

**Decision:** `data/input/` is excluded from the repository. The trained model, `predictions.csv`,
`metrics.json`, all code and all documents are committed.

**Why:** Two instructions collide and cannot both be satisfied:

- `docs/BUILD.md` Phase 13 and the brief: *"Public GitHub repo (**with data files**)"*
- `ops-policy.pdf` p1 **§10**: *"Customer and operational data ... must not be published, uploaded
  to public repositories or shared beyond the engagement team."*

§10 is the client's own rulebook, it addresses this exact question, and it is more specific than the
brief. The PII scan strengthens the case rather than weakening it: **0** names, phone numbers or
email addresses, but **1,396** customer registration numbers (`reg no SR#####` — a 5-digit namespace
distinct from the 6-digit `request_id`) embedded in request text. That is pseudonymous, not
anonymous: it maps 1:1 to a customer.

The user was asked directly and chose the policy. Recorded here so the reasoning survives.

**Rejected:**
- Commit the data as supplied — would breach §10.
- Mask the registration numbers and commit the rest — partially satisfies both, but it produces a
  repository that no longer reproduces the reported numbers, and a half-masked customer file is a
  worse artefact than none.

**Proof this costs nothing.** Verified by fresh clone: the repository contains **0** CSV data files,
and the service still boots and answers `/api/v1/predict` with 99.8% confidence, because the model
carries the learned routing and needs the data only to retrain. The client supplies `data/input/` at
run time exactly as the project always did.

**Revisit if:** The client confirms **in writing** that publishing is permitted. Then the `.gitignore`
block is deleted and the data is committed as supplied.

---

## D18 — A misroute costs ₹565, and the ₹305 floor is published beside it
**Date:** 2026-10-02 · **Phase:** 4 · **Status:** active

**Decision:** The headline misroute cost is **₹565** = the policy's ₹305 transfer handling **plus**
the ₹260 for the one extra customer contact a misroute generates. The transfer-only **₹305** figure
is published alongside as a conservative floor.

**Why:** `ops-policy.pdf` p1 §4 gives two numbers and `wrong_first_touch_rate` measures first-touch
errors — which is precisely what the policy calls a *misrouted request*, and what it says generates
both the transfer and the extra contact. So 565 is the all-in cost of the event being counted.

Only the transfer cost would understate it; only the contact cost would overstate it. Publishing both
means a reader can reject the aggressive number and still have an honest one.

**The resulting arithmetic**, from `python -m kestrel run numbers --transfer-cost-inr 565`:

```
transfers avoided = (0.250 - 0.155) x 724 requests = 69
transfer saving   = 69 x 565 = 38,985
licence avoided   = 320,000 / 12 = 26,667
net per month     = 26,667 + 38,985 - 0 = 65,652        -> 65,652 x 12 = 787,824 a year
```

Floor with ₹305: 69 × 305 = 21,045; net **₹47,712/month**.

**Rejected:** ₹305 alone, because it ignores a cost the policy explicitly attaches to the same event.

**Revisit if:** Kestrel's finance team says a transfer and an extra contact are not both caused by a
misroute, or supplies a different rate.

---

## D19 — One policy rule enabled; the other six stay disabled and are reported
**Date:** 2026-10-02 · **Phase:** 4 · **Status:** active

**Decision:** Seven rules drafted from `ops-policy.pdf` §3 and the `handles` column of `teams.csv`,
each measured against all 6,502 closed CRM rows. **Only `R-PAID-NOT-BILLING` is enabled.**

| Rule | Matches | Agreement | Enabled |
|---|---|---|---|
| `R-PAID-NOT-BILLING` | 58 | **98.28%** | **yes** |
| `R-RETURN-DAMAGED` | 839 | 91.90% | no |
| `R-BILLING-PAYMENT` | 739 | 91.61% | no |
| `R-WARRANTY-COVERAGE` | 714 | 90.90% | no |
| `R-USAGE-ADVICE` | 688 | 89.68% | no |
| `R-FAULT-NOT-CONSUMABLE` | 1,467 | 88.34% | no |
| `R-CONSUMABLE-PART` | 596 | 88.26% | no |

**Why:** `docs/BUILD.md` T11 sets the bar — a rule is switched on only if history agrees with it at
≥95% on closed CRM rows, otherwise it is logged as a **policy-versus-practice conflict**. Six rules
fail it by 3–7 points. That is a finding for Ritu, not a defect to hide: the written rules are too
broad to run as automation, and Meenal should tighten them rather than ship them.

**The enabled rule is redundant, and that is the honest finding.** Measured on the **validation**
slice — never the holdout — it fires on 10 rows and changes **0** decisions, because the model
already learned what the policy says. `artifacts/predictions.csv` is byte-identical before and
after enabling it, confirmed with `cmp`.

It is kept enabled anyway as a guard rather than an improvement, and the submission form says so
rather than implying it raised the score.

**A design inconsistency found while checking this:** rules are applied by `Router.route()` for
single requests but **not** by `Router.route_frame()` or by the training-time prediction write. So a
rule cannot affect `predictions.csv` at all. Harmless here (the rule changes nothing), but it means
an enabled rule is not a way to influence the submission. Noted, not changed — changing it would
alter predictions.csv this late.

**Revisit if:** Meenal rewrites the policy rules more narrowly, or a future rule clears 95% *and*
measurably improves validation.

---

## D20 — Memo decision A, with 16.8% escalation accepted
**Date:** 2026-10-02 · **Phase:** 4 · **Status:** active — *user's call*

**Decision:** Memo option **A** — a two-week shadow run alongside the bot, then switch the bot off
for requests the router is confident about, with 16.8% of requests going to a person.

**Why:** `docs/BUILD.md` §9 sets a numeric rule: choose A only if the model's accuracy interval sits
at least 3 points above the bot's **and** the unsure share is within a limit the client sets.
Measured: interval separation **4.92 points** (model low 82.4% vs bot high 77.5%) — clears the first
condition. The second needs a human tolerance, which only the user can give. **16.8%** was accepted.

`form_values.json` reached the same conclusion independently, against its default 30% limit:
`decision_suggestion: "A"`.

**Note:** option B stays *available*. 16.8% is a business tolerance, not a data finding — if support
capacity is smaller than that, B is the honest answer and only the limit changes.

---

## Note — `docs/BUILD.md` code blocks are not to be used

`docs/AGENT_TASK.md` forbids extracting code from `BUILD.md`; its blocks are
superseded by `kestrel/`. D4 extends that to its **synthetic constants** — the
team list, product list and channel list in that file belong to its dev-only
data generator, not to this dataset. Anything real comes from `data/input/` or
`config/`.