"""Tiny in-process event bus. Plugins and future agents subscribe to events such as pipeline.succeeded."""
from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Callable

log = logging.getLogger("kestrel.events")


class EventBus:
    def __init__(self):
        self._subs: dict = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event: str, fn: Callable[[dict], None]) -> None:
        with self._lock:
            self._subs[event].append(fn)

    def emit(self, event: str, payload: dict | None = None) -> None:
        with self._lock:
            fns = list(self._subs.get(event, [])) + list(self._subs.get("*", []))
        for fn in fns:
            try:
                fn({"event": event, **(payload or {})})
            except Exception:  # a broken subscriber must not break the pipeline
                log.exception("event subscriber failed for %s", event)
