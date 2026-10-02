"""AppContext wires settings, registry, job runner, router and watcher. Extensions receive it as `ctx`."""
from __future__ import annotations

import logging

from .events import EventBus
from .extensions.loader import load_plugins, load_skills
from .extensions.registry import Registry
from .jobs import JobManager, log_var
from .ml.predict import Router
from .settings import Settings
from .watcher import DataWatcher

logger = logging.getLogger("kestrel")


class AppContext:
    def __init__(self, settings: Settings, load_extensions: bool = True):
        settings.ensure_dirs()
        self.settings = settings
        self.bus = EventBus()
        self.registry = Registry()
        self.jobs = JobManager(self.bus)
        self.router = Router(settings)
        self.watcher = DataWatcher(self)
        if load_extensions:
            from .extensions.builtin import register_builtins
            register_builtins(self.registry)
            load_plugins(self.registry, settings.plugins_dir)
            load_skills(self.registry, settings.skills_dir)

    def log(self, msg) -> None:
        logger.info(msg)
        fn = log_var.get()
        if fn:
            fn(msg)
