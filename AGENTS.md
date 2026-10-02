# AGENTS.md

Instructions for AI coding agents working in this repository.

## Read order

1. This file (code rules).
2. `docs/AGENT_TASK.md` (the job, the order of commands, when to stop, what only a human can do).
3. `README.md` (commands and API).

Start with `python -m kestrel doctor`. It tells you what is ready.

## Rules

- Do not invent data. `data/input/` holds the user's real files. Tests build synthetic data in temp folders through `tests/synth.py`.
- Do not add a paid API call to the request path. Cost per prediction is zero by design.
- Run `pytest -q` before and after every change. Keep it green.
- Put logic in `kestrel/services.py` or `kestrel/ml/`. Routes, commands and tools stay thin and call services.
- Raise `KestrelError` subclasses (`kestrel/errors.py`) for anything a user can fix. The API maps them to JSON.
- Never use `team_label` as the training target. It is the old bot's output. The target is `final_team`.
- Do not add `source`, `resolved_at`, `transfers` or `first_team` as model features. They leak era or outcome.

## Add a tool

Create `plugins/my_tool.py`:

```python
from kestrel.extensions import Tool

class MyTool(Tool):
    name = "my_tool"                      # lowercase, digits, underscores
    description = "What it does."
    input_schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
    def run(self, ctx, x: int = 0, **params):
        return {"double": x * 2}          # JSON-serialisable

def register(registry):
    registry.register(MyTool())
```

Restart the server. It appears at `GET /api/extensions` and runs at `POST /api/tools/my_tool/run`.

## Add a command

Subclass `Command` with `run(self, ctx, args: list)`. Run it with `python -m kestrel run <name> [args]`.

## Add a workflow

```python
from kestrel.extensions import Workflow, Step

class Nightly(Workflow):
    name = "nightly"
    description = "Validate then train."
    steps = [Step("command", "validate", {"args": []}), Step("command", "train", {"args": []})]
```

Register it. Run with `POST /api/workflows/nightly/run` or `python -m kestrel run nightly`. A failing step stops the workflow and names the step.

## Add a skill

Create `skills/<name>/SKILL.md` with frontmatter (`name`, `description`, `tools`). See `skills/README.md`.

## Add an agent

Subclass `Agent` (`kestrel/extensions/base.py`), implement `run(ctx, task, **kwargs) -> AgentResult`, register it. The core never instantiates agents. Wire yours to an endpoint or command in a plugin. Use `ctx.registry.get("tool", name).run(ctx, ...)` to call tools and `kestrel.services.start_workflow(ctx, name)` to start workflows.

## Context object (`ctx`)

`ctx.settings`, `ctx.registry`, `ctx.bus` (events), `ctx.jobs` (background runner), `ctx.router` (loaded model), `ctx.watcher`, `ctx.log(msg)`.

Events on `ctx.bus`: `data.changed`, `data.settled`, `job.started`, `job.finished`, `pipeline.started`, `pipeline.trained`, `pipeline.succeeded`, `pipeline.failed`. Subscribe with `ctx.bus.subscribe("pipeline.succeeded", fn)`.

## Change input columns or file names

Edit `config/datasets.json`. Feature code reads these fixed columns (`kestrel/data/schemas.py`): request_id, request_text, created_at_ist, product_family, warranty_status, channel, source. Changing those names means changing `kestrel/data/loader.py`.

## Layout

`kestrel/data` read and validate. `kestrel/ml` model, train, predict. `kestrel/extensions` contracts and loaders. `kestrel/api` HTTP. `kestrel/services.py` shared operations. `static/` web page. `tests/` pytest.
