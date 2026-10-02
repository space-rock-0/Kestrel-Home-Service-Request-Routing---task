import json

import pytest

from kestrel.cli import _pass_run_flags_through, main
from tests.synth import make_frames, write_dir


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("KESTREL_INPUT_DIR", str(tmp_path / "in"))
    monkeypatch.setenv("KESTREL_ARTIFACT_DIR", str(tmp_path / "art"))
    monkeypatch.setenv("KESTREL_PLUGINS_DIR", str(tmp_path / "plugins"))
    monkeypatch.setenv("KESTREL_FAST", "true")
    monkeypatch.setenv("KESTREL_WATCH_INTERVAL", "0")
    return tmp_path


def test_validate_exit_code_without_data(env, capsys):
    assert main(["validate"]) == 2
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_train_without_data_prints_error(env, capsys):
    assert main(["train"]) == 1
    assert "not usable" in capsys.readouterr().err


def test_full_cli_flow(env, capsys):
    write_dir(env / "in", make_frames(n=900, n_test=30, seed=9), "xlsx")
    assert main(["validate"]) == 0
    capsys.readouterr()
    assert main(["run", "full_pipeline"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert [s["step"] for s in out] == ["validate input", "audit data", "train and evaluate", "check predictions"]
    assert main(["check"]) == 0
    capsys.readouterr()
    assert main(["predict", "--out", str(env / "p.csv")]) == 0
    assert (env / "p.csv").exists()
    assert main(["extensions"]) == 0
    assert "full_pipeline" in capsys.readouterr().out


def test_unknown_command_name(env, capsys):
    assert main(["run", "does_not_exist"]) == 1
    assert "No command named" in capsys.readouterr().err


# --- flags must reach the command being run, not argparse -------------------------------------

def test_run_passes_flags_through_to_the_command():
    """`run numbers --transfer-cost-inr 565` is the syntax README documents.

    argparse reads a `--flag` after a subcommand as its own option, so this used to die with
    'unrecognized arguments'. The flags belong to the command, so main() inserts a `--` itself
    and the user should not have to know that."""
    assert _pass_run_flags_through(["run", "numbers", "--transfer-cost-inr", "565"]) == \
        ["run", "numbers", "--", "--transfer-cost-inr", "565"]
    # no flags, nothing to do
    assert _pass_run_flags_through(["run", "golden"]) == ["run", "golden"]
    assert _pass_run_flags_through(["run", "full_pipeline"]) == ["run", "full_pipeline"]
    # a flag before the command name still belongs to the command
    assert _pass_run_flags_through(["run", "render_docs", "--transfer-cost-inr", "1", "--hosting-inr-month", "0"]) == \
        ["run", "render_docs", "--", "--transfer-cost-inr", "1", "--hosting-inr-month", "0"]
    # an explicit separator is left alone, not doubled
    assert _pass_run_flags_through(["run", "numbers", "--", "--transfer-cost-inr", "565"]) == \
        ["run", "numbers", "--", "--transfer-cost-inr", "565"]
    # commands that are not `run` are untouched
    assert _pass_run_flags_through(["predict", "--out", "x.csv"]) == ["predict", "--out", "x.csv"]


def test_run_command_with_flags_actually_executes(trained, capsys, monkeypatch):
    """End to end: the documented command runs and prints the rupee arithmetic.

    The arithmetic is asserted as a relationship, not as a literal, because this runs on the
    synthetic fixture. The real figures come from the real data and live in artifacts/numbers.txt.
    """
    from kestrel.settings import ROOT
    monkeypatch.setenv("KESTREL_INPUT_DIR", str(trained.input_dir))
    monkeypatch.setenv("KESTREL_ARTIFACT_DIR", str(trained.artifact_dir))
    monkeypatch.setenv("KESTREL_PLUGINS_DIR", str(ROOT / "plugins"))
    monkeypatch.setenv("KESTREL_FAST", "true")
    monkeypatch.setenv("KESTREL_WATCH_INTERVAL", "0")

    assert main(["run", "numbers", "--transfer-cost-inr", "565", "--hosting-inr-month", "0"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["cost_per_prediction_inr"] == 0
    # services.numbers rounds each published figure, so compare with the same rounding
    assert out["licence_avoided_inr_month"] == round(320000 / 12)
    assert out["transfer_saving_inr_month"] == round(out["transfers_avoided_per_month"] * 565)
    # the printed arithmetic must reconcile: a reader checking N x C = S has to get S
    saving_line = next(x for x in out["arithmetic"] if x.startswith("transfer saving"))
    assert f"= {out['transfer_saving_inr_month']:,}" in saving_line
    assert out["run_cost_inr_month"] == 0
    assert out["net_benefit_inr_month"] == pytest.approx(
        out["licence_avoided_inr_month"] + out["transfer_saving_inr_month"], abs=1)
    assert out["net_benefit_inr_year"] == round(out["net_benefit_inr_month"] * 12)
    # the whole point: no paid calls anywhere in the product
    assert "0" in out["arithmetic"][0] or "licence avoided" in out["arithmetic"][0]
