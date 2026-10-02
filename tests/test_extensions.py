import pytest

from kestrel.errors import ExtensionError, NotFoundError
from kestrel.events import EventBus
from kestrel.extensions import Agent, Command, Registry, Step, Tool, Workflow
from kestrel.extensions.loader import load_plugins, load_skills
from kestrel.extensions.workflow import run_workflow


class Echo(Tool):
    name, description = "echo", "returns its params"

    def run(self, ctx, **p):
        return p


class Boom(Command):
    name = "boom"

    def run(self, ctx, args):
        raise ExtensionError("kaboom")


class Count(Command):
    name = "count"

    def run(self, ctx, args):
        return len(args)


class Ctx:
    def __init__(self, reg):
        self.registry, self.logs = reg, []

    def log(self, m):
        self.logs.append(m)


def test_register_and_lookup():
    r = Registry()
    r.register(Echo())
    assert r.get("tool", "echo").run(None, a=1) == {"a": 1}
    with pytest.raises(ExtensionError):
        r.register(Echo())
    with pytest.raises(NotFoundError) as e:
        r.get("tool", "missing")
    assert e.value.details["available"] == ["echo"]


def test_invalid_names_rejected():
    class Bad(Tool):
        name = "Bad-Name"

        def run(self, ctx, **p): ...

    with pytest.raises(ExtensionError):
        Registry().register(Bad())
    with pytest.raises(ExtensionError):
        Registry().register(object())


def test_agent_is_abstract():
    with pytest.raises(TypeError):
        Agent()


def test_plugin_loading_and_isolation(tmp_path):
    (tmp_path / "good.py").write_text(
        "from kestrel.extensions import Tool\n"
        "class T(Tool):\n    name='good_tool'\n    def run(self, ctx, **p): return 7\n"
        "def register(r): r.register(T())\n")
    (tmp_path / "broken.py").write_text("raise RuntimeError('bad import')\n")
    (tmp_path / "noregister.py").write_text("x = 1\n")
    (tmp_path / "_private.py").write_text("raise RuntimeError('must not load')\n")
    pkg = tmp_path / "pkgplugin"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        "from kestrel.extensions import Command\n"
        "class C(Command):\n    name='pkg_cmd'\n    def run(self, ctx, args): return 'ok'\n"
        "def register(r): r.register(C())\n")
    r = Registry()
    load_plugins(r, tmp_path)
    assert r.names("tool") == ["good_tool"] and r.names("command") == ["pkg_cmd"]
    failed = {e["plugin"] for e in r.load_errors}
    assert failed == {"broken.py", "noregister.py"}


def test_skill_loading(tmp_path):
    d = tmp_path / "my-skill"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: my-skill\ndescription: does a thing\ntools: a, b\n---\n# Body\n")
    (tmp_path / "empty-dir").mkdir()
    r = Registry()
    load_skills(r, tmp_path)
    s = r.get("skill", "my_skill")
    assert s.description == "does a thing" and s.tools == ("a", "b") and "# Body" in s.instructions()


def test_workflow_runs_steps_in_order_and_nests():
    r = Registry()
    for e in (Echo(), Count()):
        r.register(e)

    class Inner(Workflow):
        name, steps = "inner", [Step("command", "count", {"args": ["a", "b"]})]

    class Outer(Workflow):
        name = "outer"
        steps = [Step("tool", "echo", {"x": 1}), Step("workflow", "inner")]

    r.register(Inner())
    r.register(Outer())
    ctx = Ctx(r)
    out = run_workflow(ctx, r.get("workflow", "outer"))
    assert out[0]["result"] == {"x": 1} and out[1]["result"][0]["result"] == 2
    assert len(ctx.logs) >= 3


def test_workflow_failure_names_the_step_and_stops():
    r = Registry()
    r.register(Boom())
    r.register(Count())

    class W(Workflow):
        name, steps = "w", [Step("command", "boom"), Step("command", "count")]

    ctx = Ctx(r)
    with pytest.raises(ExtensionError) as e:
        run_workflow(ctx, W())
    assert "w:1:boom" in e.value.message and "kaboom" in e.value.message


def test_event_bus_isolates_bad_subscribers():
    bus, seen = EventBus(), []
    bus.subscribe("x", lambda p: 1 / 0)
    bus.subscribe("x", lambda p: seen.append(p))
    bus.subscribe("*", lambda p: seen.append("any"))
    bus.emit("x", {"k": 1})
    assert seen == [{"event": "x", "k": 1}, "any"]
