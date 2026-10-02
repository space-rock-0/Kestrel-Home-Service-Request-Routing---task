import os
import time

from kestrel.context import AppContext
from tests.conftest import make_settings
from tests.synth import make_frames, write_dir


def test_change_must_settle_and_marks_stale(settings, frames):
    ctx = AppContext(settings)
    s = ctx.watcher.check_now()
    assert s["fingerprint"] and s["settled"] is False
    assert ctx.watcher.check_now()["settled"] is True
    write_dir(settings.input_dir, {"teams": frames["teams"]}, "xlsx")
    a = ctx.watcher.check_now()
    assert a["settled"] is False and a["stale"] is True
    assert ctx.watcher.check_now()["settled"] is True
    p = settings.input_dir / "teams.xlsx"
    os.utime(p, (time.time() + 99, time.time() + 99))
    assert ctx.watcher.check_now()["settled"] is False


def test_events_emitted(settings, frames):
    ctx = AppContext(settings)
    seen = []
    ctx.bus.subscribe("*", lambda p: seen.append(p["event"]))
    ctx.watcher.check_now()
    write_dir(settings.input_dir, {"teams": frames["teams"]}, "xlsx")
    ctx.watcher.check_now()
    ctx.watcher.check_now()
    assert seen == ["data.changed", "data.settled"]


def test_auto_train_runs_after_files_settle(tmp_path):
    s = make_settings(tmp_path, auto_train=True)
    s.ensure_dirs()
    ctx = AppContext(s)
    ctx.watcher.check_now()
    write_dir(s.input_dir, make_frames(n=900, n_test=30, seed=7), "xlsx")
    ctx.watcher.check_now()           # change seen
    ctx.watcher.check_now()           # settled -> pipeline starts
    job = ctx.jobs.latest()
    assert job is not None and job.name == "full_pipeline"
    job = ctx.jobs.wait(job.id, 180)
    assert job.state == "succeeded", job.error
    assert ctx.watcher.check_now()["stale"] is False and s.model_path.exists()


def test_auto_train_reports_invalid_input_instead_of_crashing(tmp_path, frames):
    s = make_settings(tmp_path, auto_train=True)
    s.ensure_dirs()
    ctx = AppContext(s)
    ctx.watcher.check_now()
    write_dir(s.input_dir, {"train": frames["train"]}, "xlsx")
    ctx.watcher.check_now()
    st = ctx.watcher.check_now()
    assert ctx.jobs.latest() is None and st["auto_train_error"]


def test_thread_start_stop(tmp_path):
    s = make_settings(tmp_path, watch_interval=0.05)
    s.ensure_dirs()
    ctx = AppContext(s)
    ctx.watcher.start()
    time.sleep(0.3)
    assert ctx.watcher.status()["running"] and ctx.watcher.status()["fingerprint"] is not None
    ctx.watcher.stop()
    assert not ctx.watcher.status()["running"]
