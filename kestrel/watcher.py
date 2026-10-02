"""Polls the input folder. A change must hold still for one poll before it counts as settled,
so a half-copied Excel file does not trigger a run."""
from __future__ import annotations

import json
import logging
import threading
import time

from .data.discovery import fingerprint
from .data.schemas import load_schema

log = logging.getLogger("kestrel.watcher")


class DataWatcher:
    def __init__(self, ctx):
        self.ctx = ctx
        self._last_fp = None
        self._stable = False
        self._changed_at = None
        self._auto_error = None
        self._thread = None
        self._stop = threading.Event()

    def _trained_fp(self):
        p = self.ctx.settings.state_path
        try:
            return json.loads(p.read_text(encoding="utf-8")).get("fingerprint") if p.exists() else None
        except ValueError:
            return None

    def check_now(self) -> dict:
        s = self.ctx.settings
        fp = fingerprint(s.input_dir, load_schema(s.schema_file))
        if fp != self._last_fp:
            first = self._last_fp is None
            self._last_fp, self._stable, self._changed_at = fp, False, time.time()
            if not first:
                self.ctx.bus.emit("data.changed", {"fingerprint": fp})
        elif not self._stable:
            self._stable = True
            self.ctx.bus.emit("data.settled", {"fingerprint": fp})
            self._maybe_auto_train()
        return self.status()

    def _maybe_auto_train(self) -> None:
        s = self.ctx.settings
        if not s.auto_train or self._last_fp == self._trained_fp():
            return
        from . import services
        try:
            if self.ctx.jobs.running():
                return
            report = services.validate_data(self.ctx, "train")
            if report["ok"]:
                services.start_workflow(self.ctx, "full_pipeline")
                self._auto_error = None
            else:
                self._auto_error = "; ".join(e["message"] for e in report["errors"][:2])
        except Exception as e:
            self._auto_error = str(e)
            log.warning("auto-train skipped: %s", e)

    def status(self) -> dict:
        trained = self._trained_fp()
        return {"fingerprint": self._last_fp, "settled": self._stable, "changed_at": self._changed_at,
                "stale": bool(self._last_fp) and self._last_fp != trained, "trained_fingerprint": trained,
                "auto_train": self.ctx.settings.auto_train, "auto_train_error": self._auto_error,
                "running": bool(self._thread and self._thread.is_alive())}

    def start(self) -> None:
        interval = self.ctx.settings.watch_interval
        if interval <= 0 or (self._thread and self._thread.is_alive()):
            return
        self._stop.clear()

        def loop():
            while not self._stop.is_set():
                try:
                    self.check_now()
                except Exception:
                    log.exception("watcher poll failed")
                self._stop.wait(interval)

        self._thread = threading.Thread(target=loop, daemon=True, name="data-watcher")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
