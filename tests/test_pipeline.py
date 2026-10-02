import json

import pandas as pd
import pytest

from kestrel import services
from kestrel.context import AppContext
from kestrel.errors import DataValidationError
from tests.conftest import make_settings
from tests.synth import make_frames, write_dir


def test_artifacts_written(trained):
    for name in ("model.joblib", "metrics.json", "predictions.csv", "predictions_with_confidence.csv",
                 "confusion_holdout.csv", "errors_holdout.csv", "state.json"):
        assert (trained.artifact_dir / name).exists(), name


def test_metrics_contract(trained):
    m = json.loads(trained.metrics_path.read_text())
    h = m["holdout"]
    assert {"model", "bot_vs_final", "model_agreement_with_bot_label", "gate_on_holdout", "wrong_first_touch_rate"} <= set(h)
    lo, hi = h["model"]["accuracy_ci95"]
    assert 0 <= lo <= h["model"]["accuracy"] <= hi <= 1
    assert m["split"]["holdout"] > 20 and m["input_files"]["train"] == "train.xlsx"
    assert h["model"]["accuracy"] > 0.5  # sanity on trivial synthetic text, not a quality claim


def test_predictions_match_test_file_and_use_current_names(trained, frames):
    sub = pd.read_csv(trained.predictions_path, dtype=str)
    assert list(sub.columns) == ["request_id", "team"]
    assert set(sub.request_id) == set(frames["test"].request_id) and len(sub) == len(frames["test"])
    assert not ({"Spares Desk", "Shield Desk"} & set(sub.team))


def test_check_submission_ok_and_catches_bad_file(trained, tmp_path):
    ctx = AppContext(trained)
    assert services.check_submission(ctx)["ok"]
    bad = pd.read_csv(trained.predictions_path, dtype=str)
    bad.loc[0, "team"] = "Spares Desk"
    bad = bad.iloc[:-1]
    p = tmp_path / "bad.csv"
    bad.to_csv(p, index=False)
    r = services.check_submission(ctx, str(p))
    assert not r["ok"] and len(r["errors"]) >= 2


def test_predict_file_uses_existing_model(trained, tmp_path):
    ctx = AppContext(trained)
    out = tmp_path / "again.csv"
    r = services.predict_file(ctx, str(out))
    assert r["rows"] == len(pd.read_csv(out)) and out.with_name("again_with_confidence.csv").exists()


def test_train_refuses_when_too_few_closed_crm_rows(tmp_path):
    s = make_settings(tmp_path)
    s.ensure_dirs()
    write_dir(s.input_dir, make_frames(n=300, n_test=20), "csv")
    with pytest.raises(DataValidationError) as e:
        services.run_train(AppContext(s))
    assert "closed" in e.value.message


def test_csv_and_xlsx_inputs_both_train(tmp_path):
    s = make_settings(tmp_path)
    s.ensure_dirs()
    write_dir(s.input_dir, make_frames(n=900, n_test=40, seed=3), "csv")
    out = services.run_train(AppContext(s))
    assert out["test_rows"] == 40


def test_training_without_test_file_skips_predictions(tmp_path):
    s = make_settings(tmp_path)
    s.ensure_dirs()
    f = make_frames(n=900, seed=4)
    f.pop("test"); f.pop("sample_submission")
    write_dir(s.input_dir, f, "xlsx")
    out = services.run_train(AppContext(s))
    assert out["test_rows"] is None and not s.predictions_path.exists()
    assert services.check_submission(AppContext(s))["skipped"]


def test_golden_cases_run(trained):
    out = services.golden(AppContext(trained))
    assert len(out) == 5 and all({"case", "team", "confidence"} <= set(r) for r in out)


def test_numbers_arithmetic_is_consistent(trained):
    from kestrel.extensions.builtin import NumbersCommand
    ctx = AppContext(trained)
    r = NumbersCommand().run(ctx, ["--transfer-cost-inr", "150", "--hosting-inr-month", "500"])
    assert r["licence_avoided_inr_month"] == 26667 and r["cost_per_prediction_inr"] == 0
    assert r["run_cost_inr_month"] == 500
    assert abs(r["net_benefit_inr_month"] - (r["licence_avoided_inr_month"] + r["transfer_saving_inr_month"] - r["run_cost_inr_month"])) <= 2
    assert r["net_benefit_inr_year"] == pytest.approx(12 * r["net_benefit_inr_month"], abs=12)
    from kestrel.errors import ExtensionError
    with pytest.raises(ExtensionError):
        NumbersCommand().run(ctx, [])
