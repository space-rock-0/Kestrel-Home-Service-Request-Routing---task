"""Extension contracts. Add a capability by subclassing one of these and registering it. No core file changes needed.

Kinds
  Tool      one typed operation: run(ctx, **params) -> JSON-serialisable result. Exposed at POST /api/tools/{name}/run.
  Command   CLI-style entry: run(ctx, args) -> result. Runs as `python -m kestrel run <name> [args]`.
  Skill     an instruction bundle for an AI agent (markdown). Loaded from skills/<name>/SKILL.md or registered in code.
  Workflow  an ordered list of tool/command/workflow steps. Runs in the background job runner.
  Agent     an autonomous worker that can call tools and workflows. Interface only: this repo ships no agent.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar


class Extension(ABC):
    kind: ClassVar[str] = "extension"
    name: str = ""
    description: str = ""
    version: str = "1.0.0"

    def describe(self) -> dict:
        return {"kind": self.kind, "name": self.name, "description": self.description, "version": self.version}


class Tool(Extension):
    kind = "tool"
    input_schema: dict = {"type": "object", "properties": {}}

    @abstractmethod
    def run(self, ctx, **params) -> Any: ...

    def describe(self) -> dict:
        return {**super().describe(), "input_schema": self.input_schema}


class Command(Extension):
    kind = "command"
    usage: str = ""

    @abstractmethod
    def run(self, ctx, args: list) -> Any: ...

    def describe(self) -> dict:
        return {**super().describe(), "usage": self.usage}


class Skill(Extension):
    """Instructions an agent loads on demand. `tools` lists tool names the skill expects to use."""
    kind = "skill"
    tools: tuple = ()

    @abstractmethod
    def instructions(self) -> str: ...

    def describe(self) -> dict:
        return {**super().describe(), "tools": list(self.tools)}


@dataclass
class Step:
    kind: str  # "tool" | "command" | "workflow"
    target: str
    params: dict = field(default_factory=dict)  # tool: keyword params; command: {"args": [...]}
    name: str = ""


class Workflow(Extension):
    kind = "workflow"
    steps: list = []

    def describe(self) -> dict:
        return {**super().describe(), "steps": [{"kind": s.kind, "target": s.target, "name": s.name or s.target} for s in self.steps]}


@dataclass
class AgentResult:
    ok: bool
    output: Any = None
    steps: list = field(default_factory=list)


class Agent(Extension):
    """Future integration point. An agent receives a task and the app context, and may call
    ctx.registry tools and workflows. Nothing in the core instantiates agents."""
    kind = "agent"

    @abstractmethod
    def run(self, ctx, task: str, **kwargs) -> AgentResult: ...
