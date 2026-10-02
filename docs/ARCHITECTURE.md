# Architecture

```
data/input/*.xlsx|csv
        |
   discovery  --- fingerprint ---> watcher --- events ---> bus
        |                                          |
   readers (normalise headers)                     v
        |                                    auto-train (optional)
   validation (structure, content)
        |
   loader -> Dataset (train, test, team map)
        |
   ml.train -> artifacts/ (model, metrics, predictions)
        |
   ml.predict.Router  (reloads when model.joblib changes)
        |
   services  <-- commands, tools, workflows (extensions)
      ^    ^
      |    +---- cli
      +--------- api (FastAPI) --- static web page
```

## Layers

| Layer | Package | Job |
|---|---|---|
| Input | `kestrel/data` | Find files, match roles, read Excel and CSV, validate |
| Model | `kestrel/ml` | Train on `final_team`, time-based evaluation, route one or many requests |
| Services | `kestrel/services.py` | One function per operation. Everything else calls these |
| Extensions | `kestrel/extensions` | Contracts, registry, plugin and skill loaders, workflow runner |
| Runtime | `jobs.py`, `watcher.py`, `events.py`, `context.py` | Background job, folder polling, event bus, wiring |
| Interfaces | `kestrel/api`, `kestrel/cli.py`, `static/` | HTTP, command line, web page |

## Decisions

- **Target is `final_team`.** `team_label` is the old bot's choice. It serves as the baseline.
- **Time split.** Dev older than validation older than holdout. The holdout contains only the CRM-era rows and is scored once.
- **No `source` feature.** It separates two data eras perfectly and would not generalise to the test period.
- **Logistic regression on TF-IDF.** Small, CPU-only, per-word reasons from coefficients, no download at runtime.
- **Confidence line.** Chosen on validation data. Requests below it go to a person.
- **Schema in JSON.** File roles and required columns live in `config/datasets.json`.
- **Plugins fail soft.** A broken plugin is recorded, the app starts.
- **Single job slot.** A second pipeline run while one is active returns 409.

## Failure behaviour

| Situation | Behaviour |
|---|---|
| No input files | App starts. Status page says where to put files. `/api/route` returns 503 `model_not_ready` |
| Missing file or column | Validation error naming the file and column. Pipeline job fails with that message |
| Corrupt or locked Excel file | Listed as unreadable, ignored, other files still used |
| Two files for one role | Newest used, warning shown |
| Model file replaced | Router reloads on the next request |
| Plugin import error | Listed in `load_errors`, app continues |
| Unexpected exception in a route | JSON 500 with a plain message, details logged |
