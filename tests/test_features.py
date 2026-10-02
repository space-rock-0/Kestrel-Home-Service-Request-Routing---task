import json
from dataclasses import replace

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from kestrel import reporting, services
from kestrel.api.app import create_app
from kestrel.cli import main
from kestrel.context import AppContext
from kestrel.data.cleaning import parse_ts
from kestrel.data.discovery import discover
from kestrel.data.loader import load_dataset
from kestrel.errors import DataNotFoundError
from tests.conftest import make_settings
from tests.synth import make_frames, write_dir

def _make_pdf(text: str) -> bytes:
    """Smallest valid one-page PDF with a correct cross-reference table."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [b"<</Type/Catalog/Pages 2 0 R>>", b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
            b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
            b"<</Length %d>>\nstream\n" % len(stream) + stream + b"\nendstream", b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"]
    out, offs = b"%PDF-1.4\n", []
    for n, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % n + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offs)
    return out + b"trailer\n<</Root 1 0 R/Size %d>>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)


PDF = _make_pdf("Each transfer costs Rs 150 per case.")


# ---- Excel quirks
def test_parse_ts_handles_excel_serials_and_strings():
    s = pd.Series(["45678", "45678.5", "2025-10-01 09:30:00", "01/11/2025", "", "junk"])
    out = parse_ts(s)
    assert out[0] == pd.Timestamp("2025-01-21") and out[1] == pd.Timestamp("2025-01-21 12:00")
    assert out[2] == pd.Timestamp("2025-10-01 09:30") and pd.notna(out[3])
    assert pd.isna(out[4]) and pd.isna(out[5])


def test_serial_dates_load_end_to_end(settings):
    f = make_frames(n=900, n_test=30, seed=2)
    for role in ("train", "test"):
        ts = pd.to_datetime(f[role]["created_at_ist"], format="mixed")
        f[role]["created_at_ist"] = ((ts - pd.Timestamp("1899-12-30")).dt.total_seconds() / 86400).round(5).astype(str)
    write_dir(settings.input_dir, f, "xlsx")
    ds = load_dataset(settings, "train")
    assert ds.train.ts.isna().mean() == 0


def test_alternative_headers_are_mapped(settings):
    f = make_frames(n=900, n_test=30, seed=2)
    f["train"] = f["train"].rename(columns={"request_id": "Ticket ID", "created_at_ist": "Created At", "channel": "Contact Channel",
                                            "product_family": "Product", "warranty_status": "Warranty", "request_text": "Message",
                                            "source": "System", "team_label": "Bot Queue"})
    write_dir(settings.input_dir, f, "xlsx")
    d = discover(settings)
    tr = d.by_role["train"]
    assert tr.renames["ticket_id"] == "request_id" and tr.renames["bot_queue"] == "team_label"
    ds = load_dataset(settings, "train")
    assert "request_id" in ds.train.columns and ds.train.team_label.notna().all()


def test_aliases_do_not_break_teams_file(settings):
    f = make_frames(n=300, n_test=10)
    write_dir(settings.input_dir, {"teams": f["teams"], "sample_submission": f["sample_submission"]}, "xlsx")
    d = discover(settings)
    assert d.by_role["teams"].renames == {} and d.by_role["sample_submission"].renames == {}


def test_missing_column_message_still_clear_when_no_alias_fits(settings):
    from kestrel.data.loader import validate
    f = make_frames(n=300, n_test=10)
    write_dir(settings.input_dir, f, "xlsx")
    f["train"].drop(columns=["request_text"]).to_excel(settings.input_dir / "train.xlsx", index=False)
    assert any("request_text" in e.message for e in validate(settings, "train").errors)


# ---- doctor
def test_doctor_empty_is_ok_but_strict_fails(settings):
    ctx = AppContext(settings)
    r = services.doctor(ctx)
    assert r["ok"] and r["counts"]["warn"] >= 2
    assert not services.doctor(ctx, strict=True)["ok"]


def test_doctor_on_trained_env_passes_strict(trained):
    r = services.doctor(AppContext(trained), strict=True)
    assert r["ok"], [c for c in r["checks"] if c["status"] == "fail"]
    names = {c["check"]: c["status"] for c in r["checks"]}
    assert names["trained model"] == "pass" and names["predictions.csv"] == "pass" and names["validation"] == "pass"


def test_doctor_reports_validation_errors(settings):
    f = make_frames(n=300, n_test=10)
    write_dir(settings.input_dir, f, "xlsx")
    f["train"].drop(columns=["warranty_status"]).to_excel(settings.input_dir / "train.xlsx", index=False)
    r = services.doctor(AppContext(settings))
    assert not r["ok"] and any("warranty_status" in c["detail"] for c in r["checks"] if c["status"] == "fail")


def test_doctor_api_and_cli(trained, settings, monkeypatch, capsys):
    c = TestClient(create_app(trained, watch=False))
    assert c.get("/api/doctor?strict=true").json()["ok"]
    monkeypatch.setenv("KESTREL_INPUT_DIR", str(settings.input_dir))
    monkeypatch.setenv("KESTREL_ARTIFACT_DIR", str(settings.artifact_dir))
    monkeypatch.setenv("KESTREL_PLUGINS_DIR", str(settings.plugins_dir))
    assert main(["doctor"]) == 0
    assert main(["doctor", "--strict"]) == 2
    assert "[FAIL]" in capsys.readouterr().out


# ---- policy text
def test_policy_text_extracts_cost_lines(settings):
    (settings.input_dir / "ops-policy.pdf").write_bytes(PDF)
    r = services.policy_text(AppContext(settings))
    assert r["pages"] == 1 and any("Rs 150" in ln for ln in r["cost_candidate_lines"])
    assert (settings.artifact_dir / "policy.txt").exists()


def test_policy_text_missing_pdf_is_clear(settings):
    with pytest.raises(DataNotFoundError) as e:
        services.policy_text(AppContext(settings))
    assert "ops-policy.pdf" in e.value.message


def test_pdf_is_not_mistaken_for_a_data_file(settings):
    (settings.input_dir / "ops-policy.pdf").write_bytes(PDF)
    assert discover(settings).files == []


# ---- rules audit
def test_audit_rules_measures_agreement(trained, tmp_path):
    rules = [{"id": "good", "enabled": False, "when": {"regex": "installation"}, "team": "Installation"},
             {"id": "bad", "enabled": False, "when": {"regex": "refund"}, "team": "Installation"},
             {"id": "none", "enabled": False, "when": {"regex": "zzzzqqq"}, "team": "Billing"}]
    f = tmp_path / "rules.json"
    f.write_text(json.dumps(rules))
    out = {r["id"]: r for r in services.audit_rules(AppContext(replace(trained, rules_file=f)))}
    assert out["good"]["recommend_enable"] and out["good"]["agreement"] >= 0.95
    assert not out["bad"]["recommend_enable"] and out["bad"]["matches_in_crm_closed"] > 0
    assert out["none"]["matches_in_crm_closed"] == 0 and out["none"]["agreement"] is None


def test_enabled_rule_overrides_model_and_is_reported(trained, tmp_path):
    f = tmp_path / "rules.json"
    f.write_text(json.dumps([{"id": "R9", "source": "test", "enabled": True, "when": {"regex": "installation"}, "team": "Billing"}]))
    ctx = AppContext(replace(trained, rules_file=f))
    r = ctx.router.route({"request_text": "need installation of my fan"})
    assert r["team"] == "Billing" and r["rule"]["id"] == "R9" and not r["needs_clarification"]


# ---- reporting
def test_inr_indian_grouping():
    assert reporting.inr(1234567) == "12,34,567" and reporting.inr(26667) == "26,667" and reporting.inr(999) == "999"
    assert reporting.inr(-320000) == "-3,20,000" and reporting.inr(100000) == "1,00,000"


def test_form_values_complete_and_consistent(trained):
    v = services.form_values(AppContext(trained))
    for k in ("bot_acc_pct", "model_acc_pct", "ci_lo_pct", "ci_hi_pct", "expected_point_pct", "expected_low_pct",
              "flagged_pct", "decision_suggestion", "worst_team", "drift_pts"):
        assert k in v, k
    assert v["ci_lo_pct"] <= v["model_acc_pct"] <= v["ci_hi_pct"]
    assert v["expected_low_pct"] <= v["expected_point_pct"] <= v["expected_high_pct"] + 0.001
    assert v["decision_suggestion"] in ("A", "B")
    assert (trained.artifact_dir / "form_values.json").exists()


def test_decision_rule_boundaries():
    base = {"trained_at": "t", "split": {"dev": 1, "val": 1, "holdout_from": "x", "rows_closed": 10, "rows_unclosed": 0},
            "holdout": {"model": {"n": 100, "accuracy": .9, "macro_f1": .9, "accuracy_ci95": [.86, .94]},
                        "bot_vs_final": {"accuracy": .7, "macro_f1": .7, "accuracy_ci95": [.65, .75]},
                        "model_agreement_with_bot_label": {"accuracy": .7},
                        "gate_on_holdout": {"share_flagged_for_human": .2, "accuracy_when_not_flagged": .95, "accuracy_when_flagged": .6},
                        "wrong_first_touch_rate": {"bot": .3, "model": .1}, "by_month_accuracy": {"2026-06": .9, "2026-07": .9}}}
    assert reporting.form_values(base)["decision_suggestion"] == "A"
    base["holdout"]["gate_on_holdout"]["share_flagged_for_human"] = .5
    assert reporting.form_values(base)["decision_suggestion"] == "B"
    base["holdout"]["gate_on_holdout"]["share_flagged_for_human"] = .2
    base["holdout"]["model"]["accuracy_ci95"] = [.76, .80]
    assert reporting.form_values(base)["decision_suggestion"] == "B"


def test_drift_haircut_applies_only_when_last_month_is_worse():
    m = {"trained_at": "t", "split": {"dev": 1, "val": 1, "holdout_from": "x", "rows_closed": 10, "rows_unclosed": 0},
         "holdout": {"model": {"n": 10, "accuracy": .9, "macro_f1": .9, "accuracy_ci95": [.8, .95]},
                     "bot_vs_final": {"accuracy": .7, "macro_f1": .7, "accuracy_ci95": [.6, .8]},
                     "model_agreement_with_bot_label": {"accuracy": .7},
                     "gate_on_holdout": {"share_flagged_for_human": .1, "accuracy_when_not_flagged": 1, "accuracy_when_flagged": .5},
                     "wrong_first_touch_rate": {"bot": .3, "model": .1}, "by_month_accuracy": {"a": .95, "b": .95, "c": .85, "d": .85}}}
    assert reporting.form_values(m)["drift_pts"] == 10.0
    m["holdout"]["by_month_accuracy"] = {"a": .8, "b": .8, "c": .95, "d": .95}
    assert reporting.form_values(m)["drift_pts"] == 0.0


def test_render_docs_fills_measured_and_flags_hand_written(trained, tmp_path):
    """Every template placeholder must be resolvable, or render_docs destroys content.

    This test previously asserted the opposite: that `author`, `bot_rule_fixes` and
    `busiest_teams` stayed unresolved. That was guarding a real bug. Unresolved placeholders are
    written through to output/ verbatim, and three were unresolved, so a single render replaced
    125 hand-written lines of the evidence pack with three literal "{{...}}" strings. The
    invariant now asserted is the safe one: only genuinely human-owned slots may remain.
    """
    s = replace(trained, output_dir=tmp_path / "out", templates_dir=ROOT_TEMPLATES)
    r = services.render_docs(AppContext(s), transfer_cost_inr=150, hosting_inr_month=500)
    memo = (tmp_path / "out" / "MEMO.md").read_text()
    assert "{{model_acc_pct}}" not in memo and "{{net_benefit_inr_month_fmt}}" not in memo and "Rs 500" in memo

    left = set(r["files"]["MEMO.md"]["unresolved_placeholders"])
    # measured values are filled
    assert "bot_acc_pct" not in left and "model_acc_pct" not in left
    # fixed prose is supplied by form_values, not left dangling
    for ph in ("author", "bot_rule_fixes", "busiest_teams"):
        assert ph not in left, f"{ph} must resolve; an unresolved placeholder overwrites content"
        assert "{{" + ph + "}}" not in memo
    # only the slots a human must decide are allowed to remain
    assert left == {"owner_it", "owner_service"}


def test_evidence_template_has_no_unresolvable_placeholders(trained, tmp_path):
    """EVIDENCE.md must regenerate complete. A regression here silently deletes the evidence pack."""
    s = replace(trained, output_dir=tmp_path / "out", templates_dir=ROOT_TEMPLATES)
    r = services.render_docs(AppContext(s), transfer_cost_inr=150, hosting_inr_month=500)
    evidence = (tmp_path / "out" / "EVIDENCE.md").read_text()
    assert r["files"]["EVIDENCE.md"]["unresolved_placeholders"] == []
    assert "{{" not in evidence
    # the hand-written sections that were lost must still be present after a render
    for marker in ("Error taxonomy", "Golden cases", "Tried, kept, discarded", "McNemar"):
        assert marker in evidence, f"{marker!r} was dropped by render_docs"


def test_render_docs_without_transfer_cost_leaves_rupee_placeholders(trained, tmp_path):
    s = replace(trained, output_dir=tmp_path / "out", templates_dir=ROOT_TEMPLATES)
    r = services.render_docs(AppContext(s))
    assert "transfer_saving_inr_month_fmt" in r["files"]["MEMO.md"]["unresolved_placeholders"]


from kestrel.settings import ROOT  # noqa: E402
ROOT_TEMPLATES = ROOT / "docs" / "templates"
