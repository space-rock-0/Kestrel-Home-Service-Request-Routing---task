"""Find plugins in plugins/ and skills in skills/. A broken plugin is recorded, never fatal."""
from __future__ import annotations

import importlib.util
import logging
import re
from pathlib import Path

from .base import Skill
from .registry import Registry

log = logging.getLogger("kestrel.plugins")


class FileSkill(Skill):
    def __init__(self, name: str, description: str, path: Path, tools: tuple = ()):
        self.name, self.description, self.path, self.tools = name, description, path, tools

    def instructions(self) -> str:
        return self.path.read_text(encoding="utf-8")


def _frontmatter(text: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    out = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def load_plugins(registry: Registry, plugins_dir: Path) -> None:
    if not plugins_dir.exists():
        return
    entries = sorted(p for p in plugins_dir.iterdir()
                     if not p.name.startswith(("_", ".")) and (p.suffix == ".py" or (p.is_dir() and (p / "__init__.py").exists())))
    for p in entries:
        mod_name = f"kestrel_plugin_{p.stem}"
        try:
            target = p / "__init__.py" if p.is_dir() else p
            spec = importlib.util.spec_from_file_location(mod_name, target)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if not hasattr(mod, "register"):
                raise AttributeError("plugin has no register(registry) function")
            mod.register(registry)
        except Exception as e:
            log.warning("plugin %s failed: %s", p.name, e)
            registry.load_errors.append({"plugin": p.name, "error": f"{type(e).__name__}: {e}"})


def load_skills(registry: Registry, skills_dir: Path) -> None:
    if not skills_dir.exists():
        return
    for d in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        f = d / "SKILL.md"
        if not f.exists():
            continue
        try:
            fm = _frontmatter(f.read_text(encoding="utf-8"))
            tools = tuple(t.strip() for t in fm.get("tools", "").split(",") if t.strip())
            registry.register(FileSkill(fm.get("name", d.name).replace("-", "_"), fm.get("description", ""), f, tools))
        except Exception as e:
            registry.load_errors.append({"skill": d.name, "error": f"{type(e).__name__}: {e}"})
