# Kestrel service-request router

Routes customer service requests to the team that will solve them. It replaces a rules-based routing bot with a small local model, a JSON API and a web page. No paid API, no API key.

The model learns from where past requests ended up (`final_team` in the resolution log), not from the old bot's own labels. The bot is the baseline it gets compared against.

## Quick start

Python 3.12 or newer. The pinned dependencies (`numpy==2.5.3`, `scipy==1.18.1`) publish wheels
for 3.12+ only, so on 3.10 or 3.11 `pip install -r requirements.txt` fails outright rather than
degrading. `python -m kestrel doctor` checks this too.

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m kestrel serve                                 # open http://127.0.0.1:8000
```

The app starts with no data and says so on every page. Then:

1. Copy your Excel files into `data/input/` (see `data/input/README.md` for names and columns).
2. Open the **Input data** tab. The files appear within a few seconds.
3. Open **Pipeline** and press **Run pipeline**. Or run `python -m kestrel run full_pipeline`.
4. Use **Route a request**, **Results**, and download `predictions.csv`.

`make setup`, `make run`, `make test`, `make pipeline` do the same steps. `make` is optional —
the commands above work on their own. On Windows, `make` prefers the project's own
`.venv/Scripts/python.exe`, because bare `python` is often only a Microsoft Store alias.

The server can also be started directly as an ASGI app:

```bash
uvicorn kestrel.api.app:app --port 8000
```

## What the pipeline does

1. **Validate.** Missing files, missing columns, blank or duplicate IDs, unparseable dates. Errors name the file and the column.
2. **Audit.** Writes `artifacts/audit.txt`: bot accuracy against real outcomes, text repair stats, closed-request rate by month, resolution-time sanity, duplicate IDs.
3. **Train and evaluate.** Time-ordered split: older rows train, the next slice tunes, the latest 15% of closed CRM rows is scored once. Writes the model, metrics, a confusion matrix and the holdout errors.
4. **Check predictions.** Row count, ID set, team names against the canonical list, no pre-rename names.

Outputs land in `artifacts/`. Open `metrics.json` for every number. The web page shows the headline ones.

## For an AI coding agent

Give it this folder and the line: "Read AGENTS.md and docs/AGENT_TASK.md, then do the task." The task file lists the command order, the gates, the forbidden shortcuts and the items only a human can finish. `python -m kestrel doctor --strict` is the one-command readiness check.

## Automatic detection

The server scans `data/input/` every `KESTREL_WATCH_INTERVAL` seconds. A change must stay unchanged for one scan before it counts, so a file still being copied does not trigger anything. The page shows "input changed since last training". Set `KESTREL_AUTO_TRAIN=true`, or run `python -m kestrel watch`, to retrain by itself when valid files settle. Invalid input is reported, not trained on.

## API

| Method and path | Purpose |
|---|---|
| `GET /api/health` | Status, model ready, input folder |
| `GET /api/doctor?strict=false` | Readiness checks |
| `GET /api/data/status` | Detected files, roles, missing roles, stale flag, last job |
| `POST /api/data/validate?action=train\|predict` | Full validation report |
| `POST /api/pipeline/run` | Start the pipeline in the background (202) |
| `GET /api/pipeline/status` | Latest job with log lines |
| `GET /api/metrics` | Latest `metrics.json` |
| `GET /api/meta` | Teams, products, confidence line |
| **`POST /api/v1/predict`** | **One request in, `predicted_team` + `justification` out** |
| `GET /api/predictions/download` | `predictions.csv` |
| `GET /api/extensions` | Registered tools, commands, skills, workflows, agents |
| `POST /api/tools/{name}/run` | Run a tool, body `{"params": {...}}` |
| `POST /api/workflows/{name}/run` | Run a workflow in the background |

Errors share one shape: `{"error": {"code": "...", "message": "...", "details": ...}}`. Interactive docs at `/docs`.

`/api/route` still works and is the same implementation; it is kept out of the OpenAPI schema so there is one documented endpoint, not two ways to do the same thing.

```bash
curl -s localhost:8000/api/v1/predict -H 'content-type: application/json' \
  -d '{"request_text":"I paid for installation but nobody came","product_family":"water purifier","warranty_status":"in_warranty","channel":"chat"}'
```

A payload shaped like a row of `test_unlabelled.csv` can be posted verbatim — `request_id`,
`created_at_ist` and `source` are accepted and ignored. `source` is deliberately not a model
input: it separates the legacy era from the current one perfectly and is constant for the test
set. Every field is optional, so a partial payload is answered rather than rejected.

The response carries `predicted_team`, `justification` (plain sentences a service-desk person can
read), `confidence`, `alternatives`, `reasons`, `needs_clarification`, `clarifying_question` and
`warnings`. Requests below the confidence line are flagged for a person.

## Command line

```
python -m kestrel doctor [--strict] | status | validate [--action predict] | audit | train | predict [--out f.csv] | check
python -m kestrel run <command-or-workflow> [args]     # e.g. run golden, run numbers --transfer-cost-inr 150
python -m kestrel extensions | serve | watch
```

More commands through `run`:

| Command | What it does |
|---|---|
| `run policy_text` | Extract the policy PDF to `artifacts/policy.txt` and list lines that mention costs (candidates, not facts) |
| `run audit_rules` | Measure each rule in `rules.json` against closed CRM history. Enable a rule only when it says so |
| `run golden` | Run the fixed cases from the client's email |
| `run numbers --transfer-cost-inr N` | Rupee arithmetic from measured volume and holdout error rates. Take N from your ops policy |
| `run form_values` | Every measured value the form needs, in `artifacts/form_values.json` |
| `run render_docs [--transfer-cost-inr N] [--hosting-inr-month M]` | Fill `docs/templates/` and write `output/MEMO.md` and `output/EVIDENCE.md`. Placeholders that need judgement stay visible |

## Configuration

Environment variables or a `.env` file (copy `.env.example`). Every value is optional.

| Variable | Default | Meaning |
|---|---|---|
| `KESTREL_INPUT_DIR` | `data/input` | Where Excel/CSV files go |
| `KESTREL_ARTIFACT_DIR` | `artifacts` | Model, metrics, predictions |
| `KESTREL_EXCEL_SHEET` | empty | Force a sheet name |
| `KESTREL_WATCH_INTERVAL` | `5` | Scan seconds, `0` disables |
| `KESTREL_AUTO_TRAIN` | `false` | Retrain when files settle |
| `KESTREL_PLUGINS_DIR`, `KESTREL_SKILLS_DIR` | `plugins`, `skills` | Extension folders |
| `KESTREL_OUTPUT_DIR` | `output` | Where `render_docs` writes |
| `KESTREL_SCHEMA_FILE` | `config/datasets.json` | File roles and required columns |
| `KESTREL_RULES_FILE` | `rules.json` | Policy rules, disabled unless `"enabled": true` |

## Extending

Add a tool, command, skill, workflow or agent without touching core code. See `AGENTS.md` (written for AI coding agents) and `plugins/README.md`. `docs/ARCHITECTURE.md` shows the layers.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The tests generate synthetic spreadsheets in temporary folders. They never touch `data/input/`. They prove the plumbing: discovery, validation, training, API, watcher, plugins, CLI. They say nothing about model quality on your data.

## Docs

- `docs/BUILD.md`: the build plan and decision log. Commands inside it map to this project, see the note at its top.
- `docs/submission-form.md`: draft answers for the Kestrel assignment form. Fill the blanks from `artifacts/`.
- `docs/explain.md`: the problem in plain words.

## Data handling

This repository was built from a client's service-request export. It is safe to publish, and it is
worth being precise about why.

**Not in this repository.** `data/input/` — the raw customer files — is excluded by `.gitignore` and
has never been committed (verified across every commit). The client's operations policy §10 states
that customer and operational data *"must not be published, uploaded to public repositories or shared
beyond the engagement team."* The assignment brief agrees and names the delivery route: a private
repository shared with the invitation address, or a zip. Build that zip with
`tools/package_data_for_handover.py`, which refuses to write inside the repo and prints a SHA-256.

**In this repository, and why it is safe:**

| File | Contents |
|---|---|
| `artifacts/model.joblib` | Fitted coefficients and TF-IDF vocabularies. The word vectoriser's token pattern excludes digits, so **no** order number, warranty serial or other customer identifier can appear in it. Enforced by `tests/test_model_privacy.py`, which fails the build if one ever does. No names, phone numbers, emails, verbatim complaints, timestamps or outcomes are present. |
| `artifacts/predictions.csv` | The deliverable: `request_id` and predicted team only. No customer text. |
| `artifacts/metrics.json` | Aggregate accuracy figures. No customer text. |
| `docs/`, `output/`, logs | Prose and measured figures. The five rows of instruction-like text found in the source data are quoted in `errors.md` and `NOTES.md` **pseudonymised as row A–row E**, without their ticket ids. |

**PII scan of the source data:** 0 names, 0 phone numbers, 0 email addresses. 1,396 customer
registration numbers (`reg no SR#####`, a 5-digit namespace distinct from the 6-digit `request_id`)
appear inside request text. Under the DPDP Act 2023 these are pseudonymous personal data — the rows
still carry product, warranty status, channel, timestamp and outcome — so the exclusion above is a
substantive control, not a formality. Only two registration numbers appear in both train and test.

**Operational data.** `metrics.json` publishes per-queue closed-request volumes and accuracy. These
are non-identifying aggregates and are necessary to evidence the numbers, but they are Kestrel's
operational data under §10 and the client should confirm that scope in writing.

## Limits

- Model quality on your real data is unknown until you run the pipeline. Read `artifacts/audit.txt` first.
- The service has **no authentication**. `POST /api/pipeline/run` retrains in place and rewrites
  `artifacts/model.joblib`; anyone who can reach the port can do that. Bind to localhost, or put a
  token in front, before exposing it to a network. The container sets `KESTREL_HOST=0.0.0.0`, so
  `-p 8000:8000` publishes those endpoints to whatever network Docker is on.
- `request_text` is capped at 4,000 characters. Uncapped, a single multi-megabyte request cost 86
  seconds of CPU and concurrent calls saturated the threadpool until `/api/health` stopped
  answering. Over HTTP, a longer `request_text` is **rejected with 422** rather than truncated —
  measured from a clean clone, a 5 MB body comes back 422 and a 9,000-character body comes back 422.
  Callers that bypass HTTP (CLI, plugins, batch) get truncation instead, with a warning in the
  response. Real complaints run to a few hundred characters, so nothing legitimate is rejected.
- One background job at a time. One server process.
- `.xls` reading uses `xlrd` and has no test here (the tests write `.xlsx` and `.csv`).
- The `Dockerfile` and `Makefile` have **not** been executed: neither `docker` nor `make` is
  installed in the environment that produced this project. They are verified by inspection and
  by running every command they wrap. Build and run them yourself before promising the client a
  container. The dependency pins (`numpy==2.5.3`, `scipy==1.18.1`) have no wheels below Python
  3.12, which the image uses — but check that your platform is covered before you rely on it.
- **Five rows of the training data contain text written to look like instructions to an AI agent**,
  asking for the bot's labels to be treated as verified ground truth. They were treated as customer
  text and nothing else; the training target was never `team_label`. They are inert here, but they
  mean Kestrel's intake channel accepts text engineered to manipulate downstream AI systems, which
  is worth raising with them as a security matter. See `errors.md` E10.
- Skills, agents and any LLM integration are interfaces only. Nothing in the app calls an LLM.
