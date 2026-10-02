from __future__ import annotations

import re
import threading

from ..errors import ExtensionError, NotFoundError
from .base import Agent, Command, Extension, Skill, Tool, Workflow

KINDS = {"tool": Tool, "command": Command, "skill": Skill, "workflow": Workflow, "agent": Agent}
NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class Registry:
    def __init__(self):
        self._items: dict = {k: {} for k in KINDS}
        self.load_errors: list = []
        self._lock = threading.Lock()

    def register(self, ext: Extension) -> Extension:
        kind = next((k for k, base in KINDS.items() if isinstance(ext, base)), None)
        if kind is None:
            raise ExtensionError(f"{type(ext).__name__} is not a Tool, Command, Skill, Workflow or Agent.")
        if not NAME_RE.match(ext.name or ""):
            raise ExtensionError(f"Invalid {kind} name '{ext.name}'. Use lowercase letters, digits and underscores, starting with a letter.")
        with self._lock:
            if ext.name in self._items[kind]:
                raise ExtensionError(f"A {kind} named '{ext.name}' is already registered.")
            self._items[kind][ext.name] = ext
        return ext

    def get(self, kind: str, name: str) -> Extension:
        try:
            return self._items[kind][name]
        except KeyError:
            raise NotFoundError(f"No {kind} named '{name}'.", {"available": sorted(self._items.get(kind, {}))}) from None

    def names(self, kind: str) -> list:
        return sorted(self._items[kind])

    def describe(self) -> dict:
        out = {f"{k}s": [e.describe() for _, e in sorted(v.items())] for k, v in self._items.items()}
        out["load_errors"] = list(self.load_errors)
        return out
