from dataclasses import replace
from pathlib import Path

import pytest

from kestrel.context import AppContext
from kestrel.settings import ROOT, Settings
from tests.synth import make_frames, write_dir


def make_settings(tmp: Path, **kw) -> Settings:
    base = Settings(root=ROOT, input_dir=tmp / "input", artifact_dir=tmp / "artifacts", plugins_dir=tmp / "plugins",
                    skills_dir=ROOT / "skills", schema_file=ROOT / "config" / "datasets.json",
                    rules_file=ROOT / "rules.json", fast=True, watch_interval=0)
    return replace(base, **kw)


@pytest.fixture
def settings(tmp_path):
    s = make_settings(tmp_path)
    s.ensure_dirs()
    return s


@pytest.fixture(scope="session")
def frames():
    return make_frames()


@pytest.fixture(scope="session")
def trained(tmp_path_factory, frames):
    """A settings object whose input folder holds xlsx files and whose model is already trained."""
    from kestrel import services
    tmp = tmp_path_factory.mktemp("trained")
    s = make_settings(tmp)
    s.ensure_dirs()
    write_dir(s.input_dir, frames, "xlsx")
    ctx = AppContext(s)
    services.run_train(ctx)
    return s
