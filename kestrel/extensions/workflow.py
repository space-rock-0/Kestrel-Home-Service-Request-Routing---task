from __future__ import annotations

from ..errors import ExtensionError, KestrelError
from .base import Workflow


def run_workflow(ctx, wf: Workflow, depth: int = 0) -> list:
    if depth > 5:
        raise ExtensionError("Workflow nesting deeper than 5 levels.")
    results = []
    for i, step in enumerate(wf.steps, 1):
        label = f"{wf.name}:{i}:{step.name or step.target}"
        ctx.log(f"step {i}/{len(wf.steps)} {step.kind} {step.target}")
        try:
            if step.kind == "tool":
                out = ctx.registry.get("tool", step.target).run(ctx, **step.params)
            elif step.kind == "command":
                out = ctx.registry.get("command", step.target).run(ctx, list(step.params.get("args", [])))
            elif step.kind == "workflow":
                out = run_workflow(ctx, ctx.registry.get("workflow", step.target), depth + 1)
            else:
                raise ExtensionError(f"Unknown step kind '{step.kind}'.")
        except KestrelError as e:
            raise type(e)(f"Workflow step {label} failed: {e.message}", e.details) from e
        results.append({"step": step.name or step.target, "result": out})
    return results
