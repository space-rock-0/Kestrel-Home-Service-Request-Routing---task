"""One background worker at a time. Long work (the pipeline) runs here so the API stays responsive."""
from __future__ import annotations

import threading
import time
import traceback
import uuid
from collections import OrderedDict
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import KestrelError, PipelineBusyError

log_var: ContextVar = ContextVar("kestrel_log", default=None)


@dataclass
class Job:
    id: str
    name: str
    state: str = "running"  # running | succeeded | failed
    started: float = field(default_factory=time.time)
    finished: float | None = None
    error: dict | None = None
    result: Any = None
    log: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "state": self.state, "started": self.started,
                "finished": self.finished, "error": self.error, "result": self.result, "log": self.log[-200:]}


class JobManager:
    def __init__(self, bus, keep: int = 20):
        self.bus = bus
        self.keep = keep
        self._jobs: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._threads: dict = {}

    def running(self) -> Job | None:
        return next((j for j in self._jobs.values() if j.state == "running"), None)

    def submit(self, name: str, fn: Callable[[], Any]) -> Job:
        with self._lock:
            cur = self.running()
            if cur:
                raise PipelineBusyError(f"Job '{cur.name}' is already running.", {"job_id": cur.id})
            job = Job(id=uuid.uuid4().hex[:10], name=name)
            self._jobs[job.id] = job
            while len(self._jobs) > self.keep:
                self._jobs.popitem(last=False)
        t = threading.Thread(target=self._run, args=(job, fn), daemon=True, name=f"job-{job.id}")
        self._threads[job.id] = t
        t.start()
        return job

    def _run(self, job: Job, fn: Callable[[], Any]) -> None:
        log_var.set(lambda m: job.log.append(str(m)))
        self.bus.emit("job.started", {"job": job.id, "name": job.name})
        try:
            job.result = fn()
            job.state = "succeeded"
        except KestrelError as e:
            job.state, job.error = "failed", e.as_dict()["error"]
            job.log.append(f"FAILED: {e.message}")
        except Exception as e:
            job.state, job.error = "failed", {"code": "internal_error", "message": str(e), "details": traceback.format_exc(limit=3)}
            job.log.append(f"FAILED: {e}")
        job.finished = time.time()
        self.bus.emit("job.finished", {"job": job.id, "name": job.name, "state": job.state})

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def latest(self) -> Job | None:
        return next(reversed(self._jobs.values()), None) if self._jobs else None

    def list(self) -> list:
        return [j.as_dict() for j in reversed(self._jobs.values())]

    def wait(self, job_id: str, timeout: float = 120) -> Job:
        t = self._threads.get(job_id)
        if t:
            t.join(timeout)
        return self._jobs[job_id]
