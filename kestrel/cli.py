"""Command line. `python -m kestrel --help`."""
from __future__ import annotations

import argparse
import json
import sys
import time

from .context import AppContext
from .errors import KestrelError
from .extensions.workflow import run_workflow
from .logging_setup import setup_logging
from .settings import Settings


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _pass_run_flags_through(argv: list) -> list:
    """Let `run <name> --flag value` reach the command instead of argparse.

    argparse reads a `--flag` that follows a subcommand as one of its own options, so the
    documented `python -m kestrel run numbers --transfer-cost-inr 565` died with
    "unrecognized arguments". The flags belong to the command being run, not to `run` itself, so an
    explicit `--` is inserted after the command name. Users should not have to know that.
    """
    if "run" not in argv or "--" in argv:
        return argv
    i = argv.index("run")
    rest = argv[i + 1:]
    for j, token in enumerate(rest):
        if not token.startswith("-"):
            tail = rest[j + 1:]
            return argv[:i + 1] + rest[:j + 1] + (["--"] + tail if tail else [])
    return argv


def main(argv: list | None = None) -> int:
    argv = _pass_run_flags_through(list(sys.argv[1:] if argv is None else argv))
    ap = argparse.ArgumentParser(prog="kestrel", description="Kestrel service-request router")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, help_ in (("status", "show input files and model state"), ("validate", "validate input files"),
                        ("audit", "write the data audit"), ("train", "train, evaluate, write predictions"),
                        ("predict", "route the test file with the current model"), ("extensions", "list tools, commands, skills, workflows")):
        p = sub.add_parser(name, help=help_)
        if name == "validate":
            p.add_argument("--action", default="train", choices=["train", "predict"])
        if name == "predict":
            p.add_argument("--out", default=None)
    sub.add_parser("check", help="validate predictions.csv")
    p = sub.add_parser("doctor", help="check environment, input files and model state")
    p.add_argument("--strict", action="store_true", help="treat missing data and model as failures")
    p = sub.add_parser("run", help="run any registered command or workflow by name")
    p.add_argument("name")
    p.add_argument("args", nargs="*")
    p = sub.add_parser("serve", help="start the API and web UI")
    p.add_argument("--host")
    p.add_argument("--port", type=int)
    sub.add_parser("watch", help="watch the input folder and retrain when files change (auto-train on)")
    a = ap.parse_args(argv)

    settings = Settings.from_env()
    setup_logging(settings.log_level)
    if a.cmd == "serve":
        import uvicorn
        from .api.app import create_app
        uvicorn.run(create_app(settings), host=a.host or settings.host, port=a.port or settings.port)
        return 0
    from dataclasses import replace
    if a.cmd == "watch":
        settings = replace(settings, auto_train=True, watch_interval=settings.watch_interval or 5)
    ctx = AppContext(settings)
    try:
        if a.cmd == "extensions":
            _print(ctx.registry.describe())
        elif a.cmd == "status":
            _print(ctx.registry.get("command", "status").run(ctx, []))
        elif a.cmd == "validate":
            r = ctx.registry.get("command", "validate").run(ctx, ["--action", a.action])
            _print(r)
            return 0 if r["ok"] else 2
        elif a.cmd == "doctor":
            r = ctx.registry.get("command", "doctor").run(ctx, ["--strict"] if a.strict else [])
            for c in r["checks"]:
                print(f"[{c['status'].upper():4}] {c['check']}" + (f": {c['detail']}" if c["detail"] else ""))
            print(f"\n{r['counts']['pass']} pass, {r['counts']['warn']} warn, {r['counts']['fail']} fail")
            return 0 if r["ok"] else 2
        elif a.cmd == "check":
            r = ctx.registry.get("command", "check_submission").run(ctx, [])
            _print(r)
            return 0 if r.get("ok", r.get("skipped", False)) else 2
        elif a.cmd == "predict":
            _print(ctx.registry.get("command", "predict").run(ctx, ["--out", a.out] if a.out else []))
        elif a.cmd in ("audit", "train"):
            _print(ctx.registry.get("command", a.cmd).run(ctx, []))
        elif a.cmd == "run":
            if a.name in ctx.registry.names("workflow"):
                _print(run_workflow(ctx, ctx.registry.get("workflow", a.name)))
            else:
                _print(ctx.registry.get("command", a.name).run(ctx, a.args))
        elif a.cmd == "watch":
            print(f"Watching {settings.input_dir} every {settings.watch_interval}s. Ctrl+C to stop.")
            ctx.watcher.start()
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                ctx.watcher.stop()
    except KestrelError as e:
        print(f"ERROR [{e.code}]: {e.message}", file=sys.stderr)
        if e.details:
            print(json.dumps(e.details, indent=2, default=str)[:3000], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
