from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import __version__, services
from ..context import AppContext
from ..errors import DataNotFoundError, KestrelError
from ..logging_setup import setup_logging
from ..settings import Settings

log = logging.getLogger("kestrel.api")


class RouteRequest(BaseModel):
    # max_length is a DoS guard, not a validation nicety. Uncapped, one unauthenticated POST with a
    # multi-megabyte request_text burned 86 seconds of CPU (measured) and concurrent calls
    # saturated the threadpool until /api/health stopped responding. Real complaints run to a few
    # hundred characters, so nothing legitimate is rejected. route() truncates again as defence in
    # depth for callers that bypass HTTP.
    request_text: str = Field(default="", max_length=4000)
    product_family: str = "unknown"
    warranty_status: str = "unknown"
    channel: str = "unknown"
    request_id: Optional[str] = None


class PredictRequest(RouteRequest):
    """A payload shaped exactly like one row of ``test_unlabelled.csv``.

    A raw CSV row can be POSTed verbatim, including the two columns that are deliberately
    **not** model inputs:

    - ``created_at_ist`` is accepted and ignored. A time feature would leak the time split.
    - ``source`` is accepted and ignored. It separates the legacy Zoho era from the CRM era
      perfectly, and the test set is 100% CRM, so at inference it is a constant
      (``decisions.md`` D9, ``docs/BUILD.md`` D11).

    Every field is optional and defaults to a safe value, so a partial payload is a valid
    request rather than a 422. No external service is contacted anywhere in this path, so
    there is no API key to be missing (``AGENTS.md``: no paid call in the request path).
    """

    created_at_ist: Optional[str] = None
    source: Optional[str] = None


class PredictResponse(BaseModel):
    """Routing result. ``predicted_team`` and ``justification`` are the contract fields."""

    predicted_team: str
    justification: str
    confidence: float
    team: str
    request_id: Optional[str] = None
    alternatives: list[dict] = Field(default_factory=list)
    needs_clarification: bool = False
    clarifying_question: Optional[str] = None
    reasons: list[str] = Field(default_factory=list)
    rule: Optional[dict] = None
    warnings: list[str] = Field(default_factory=list)
    model_trained_at: str


class ToolRun(BaseModel):
    params: dict = Field(default_factory=dict)


def create_app(settings: Settings | None = None, watch: bool | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    setup_logging(settings.log_level)
    ctx = AppContext(settings)
    do_watch = settings.watch_interval > 0 if watch is None else watch

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if do_watch:
            ctx.watcher.start()
        yield
        ctx.watcher.stop()

    app = FastAPI(title="Kestrel service-request router", version=__version__, lifespan=lifespan)
    app.state.ctx = ctx
    static_dir = settings.root / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.exception_handler(KestrelError)
    async def kestrel_error(_: Request, e: KestrelError):
        return JSONResponse(status_code=e.status, content=jsonable_encoder(e.as_dict()))

    @app.exception_handler(Exception)
    async def unexpected(_: Request, e: Exception):
        log.exception("unhandled error")
        return JSONResponse(status_code=500, content={"error": {"code": "internal_error",
                            "message": "Something went wrong. Route this request by hand and tell the data team.", "details": str(e)[:200]}})

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(static_dir / "index.html")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": __version__, "model_ready": ctx.router.ready,
                "input_dir": str(settings.input_dir), "watcher_running": ctx.watcher.status()["running"]}

    @app.get("/api/doctor")
    def doctor(strict: bool = False):
        return services.doctor(ctx, strict)

    @app.get("/api/data/status")
    def data_status():
        return services.data_status(ctx)

    @app.post("/api/data/validate")
    def data_validate(action: str = "train"):
        return services.validate_data(ctx, action)

    @app.post("/api/pipeline/run", status_code=202)
    def pipeline_run():
        return services.start_workflow(ctx, "full_pipeline").as_dict()

    @app.get("/api/pipeline/status")
    def pipeline_status():
        job = ctx.jobs.latest()
        return {"job": job.as_dict() if job else None, "watcher": ctx.watcher.status()}

    @app.get("/api/jobs")
    def jobs():
        return {"jobs": ctx.jobs.list()}

    @app.get("/api/metrics")
    def metrics():
        return services.read_metrics(ctx)

    @app.get("/api/meta")
    def meta():
        ctx.router.ensure_fresh()
        b = ctx.router.b
        return {"teams": b["teams"], "products": b["products"], "warranties": b["warranties"], "channels": b["channels"],
                "trained_at": b["trained_at"], "trained_rows": b["trained_rows"], "confidence_line": b["tau"]}

    def _predict(req: PredictRequest | RouteRequest) -> dict:
        """The single routing implementation. Both endpoints call this, so there is one
        code path and the two can never disagree about how a request is routed."""
        return ctx.router.route(req.model_dump())

    @app.post("/api/v1/predict", response_model=PredictResponse, tags=["predict"],
              summary="Route one request and explain the decision")
    def predict_v1(req: PredictRequest):
        """Versioned endpoint. Accepts a row shaped like `test_unlabelled.csv`."""
        out = _predict(req)
        return {**out,
                "predicted_team": out["team"],
                "justification": " ".join(out["reasons"]) or
                                 f"Routed to {out['team']} at {out['confidence']:.0%} confidence."}

    @app.post("/api/route", tags=["predict"], include_in_schema=False)
    def route(req: RouteRequest):
        """Unversioned alias, kept because the bundled web page, the plugin tools and the
        README all use it. Same implementation as /api/v1/predict."""
        return _predict(req)

    @app.get("/api/predictions/download")
    def download():
        if not settings.predictions_path.exists():
            raise DataNotFoundError("predictions.csv does not exist yet. Run the pipeline with a test file in the input folder.")
        return FileResponse(settings.predictions_path, filename="predictions.csv", media_type="text/csv")

    @app.get("/api/extensions")
    def extensions():
        return ctx.registry.describe()

    @app.get("/api/extensions/skills/{name}")
    def skill_text(name: str):
        return {"name": name, "instructions": ctx.registry.get("skill", name).instructions()}

    @app.post("/api/tools/{name}/run")
    def run_tool(name: str, body: ToolRun):
        tool = ctx.registry.get("tool", name)
        return jsonable_encoder({"tool": name, "result": tool.run(ctx, **body.params)})

    @app.post("/api/workflows/{name}/run", status_code=202)
    def run_wf(name: str):
        return services.start_workflow(ctx, name).as_dict()

    return app


def __getattr__(name: str):
    """Support `uvicorn kestrel.api.app:app` (README, Docker, ASGI servers).

    Built on first access (PEP 562) rather than at import time, so importing this module — the test
    suite imports `create_app` from here — does not construct an AppContext against the real input
    folder and load every plugin as a side effect.
    """
    if name == "app":
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
