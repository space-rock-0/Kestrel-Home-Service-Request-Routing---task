import time
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from kestrel.api.app import create_app
from kestrel.settings import ROOT
from tests.conftest import make_settings
from tests.synth import make_frames, write_dir


@pytest.fixture
def empty_client(settings):
    return TestClient(create_app(settings, watch=False))


@pytest.fixture(scope="module")
def client(trained):
    return TestClient(create_app(replace(trained, plugins_dir=ROOT / "plugins"), watch=False))


def test_index_and_static(empty_client):
    assert empty_client.get("/").status_code == 200
    assert empty_client.get("/static/app.js").status_code == 200


def test_empty_state_is_polite(empty_client, settings):
    h = empty_client.get("/api/health").json()
    assert h["status"] == "ok" and h["model_ready"] is False
    d = empty_client.get("/api/data/status").json()
    assert "No input files yet" in d["message"] and d["files"] == [] and d["ready_to_train"] is False
    r = empty_client.post("/api/route", json={"request_text": "x"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "model_not_ready"
    assert empty_client.get("/api/meta").status_code == 503
    assert empty_client.get("/api/metrics").json()["error"]["code"] == "data_not_found"
    assert empty_client.get("/api/predictions/download").status_code == 409


def test_pipeline_on_empty_input_fails_with_clear_message(empty_client):
    assert empty_client.post("/api/pipeline/run").status_code == 202
    ctx = empty_client.app.state.ctx
    job = ctx.jobs.wait(ctx.jobs.latest().id)
    assert job.state == "failed" and "not usable" in job.error["message"]
    st = empty_client.get("/api/pipeline/status").json()["job"]
    assert st["state"] == "failed" and st["error"]["code"] == "data_invalid"


def test_route_response_shape(client):
    r = client.post("/api/route", json={"request_text": "my purifier is not working", "product_family": "water purifier",
                                        "warranty_status": "in_warranty", "channel": "chat"})
    j = r.json()
    assert r.status_code == 200
    for k in ("team", "confidence", "reasons", "needs_clarification", "alternatives", "warnings"):
        assert k in j
    assert 0 <= j["confidence"] <= 1 and len(j["reasons"]) >= 2


def test_route_edge_inputs(client):
    j = client.post("/api/route", json={}).json()
    assert j["warnings"]
    j = client.post("/api/route", json={"request_text": "hello", "product_family": "spaceship"}).json()
    assert any("spaceship" in w for w in j["warnings"])
    assert client.post("/api/route", content="not json", headers={"content-type": "application/json"}).status_code == 422


def test_meta_metrics_download(client):
    m = client.get("/api/meta").json()
    assert len(m["teams"]) == 7 and "water purifier" in m["products"]
    assert client.get("/api/metrics").json()["holdout"]["model"]["n"] > 0
    d = client.get("/api/predictions/download")
    assert d.status_code == 200 and d.text.startswith("request_id,team")


def test_data_status_after_training(client):
    d = client.get("/api/data/status").json()
    assert d["model_ready"] and d["ready_to_train"] and d["stale"] is False and d["trained_at"]
    assert {f["role"] for f in d["files"]} == {"train", "test", "resolution", "teams", "sample_submission"}


def test_validate_endpoint(client):
    r = client.post("/api/data/validate?action=train").json()
    assert r["ok"] and r["rows"]["train"] > 0
    assert client.post("/api/data/validate?action=nonsense").status_code == 404


def test_extensions_listing_and_tools(client):
    x = client.get("/api/extensions").json()
    assert {"data_status", "route_request", "data_summary"} <= {t["name"] for t in x["tools"]}
    assert "full_pipeline" in {w["name"] for w in x["workflows"]}
    assert "triage_review" in {s["name"] for s in x["skills"]}
    assert x["agents"] == []
    r = client.post("/api/tools/data_summary/run", json={"params": {}}).json()["result"]
    assert r["train"]["rows"] == 1200
    r = client.post("/api/tools/route_request/run", json={"params": {"request_text": "refund please"}}).json()["result"]
    assert "team" in r
    assert client.post("/api/tools/nope/run", json={"params": {}}).status_code == 404
    assert "Triage review" in client.get("/api/extensions/skills/triage_review").json()["instructions"]


def test_pipeline_run_hot_reloads_model(tmp_path):
    s = make_settings(tmp_path)
    s.ensure_dirs()
    c = TestClient(create_app(s, watch=False))
    assert c.post("/api/route", json={"request_text": "x"}).status_code == 503
    write_dir(s.input_dir, make_frames(n=900, n_test=30, seed=5), "xlsx")
    assert c.post("/api/pipeline/run").status_code == 202
    ctx = c.app.state.ctx
    job = ctx.jobs.wait(ctx.jobs.latest().id, 180)
    assert job.state == "succeeded", job.error
    assert c.post("/api/route", json={"request_text": "need filter replacement"}).status_code == 200
    assert c.get("/api/data/status").json()["stale"] is False


def test_second_run_while_busy_is_rejected(empty_client):
    ctx = empty_client.app.state.ctx
    ctx.jobs.submit("slow", lambda: time.sleep(1.0))
    r = empty_client.post("/api/pipeline/run")
    assert r.status_code == 409 and r.json()["error"]["code"] == "pipeline_busy"
    ctx.jobs.wait(ctx.jobs.latest().id)


# --- POST /api/v1/predict: versioned endpoint, justification, missing-field handling -------------

def test_predict_v1_returns_team_and_justification(client):
    payload = {"request_text": "my purifier is not working and is leaking", "product_family": "water purifier",
               "warranty_status": "in_warranty", "channel": "chat"}
    r = client.post("/api/v1/predict", json=payload)
    j = r.json()
    assert r.status_code == 200
    assert j["predicted_team"] in client.get("/api/meta").json()["teams"]
    # justification is prose a service-desk person can read, not feature identifiers
    assert isinstance(j["justification"], str) and len(j["justification"]) > 20
    assert j["predicted_team"] in j["justification"]
    # both endpoints are one implementation, so they cannot disagree
    assert j["confidence"] == pytest.approx(client.post("/api/route", json=payload).json()["confidence"])


def test_predict_v1_accepts_a_raw_test_row_verbatim(client):
    """A line straight out of test_unlabelled.csv must work, including the two columns that are
    deliberately not model inputs: `source` separates the Zoho era from the CRM era and is constant
    across the test set, and `created_at_ist` would leak the time split. Both are accepted, ignored."""
    row = {"request_id": "SR000001", "created_at_ist": "2026-07-01 00:31", "channel": "chat",
           "product_family": "air fryer", "warranty_status": "in_warranty",
           # Synthetic, not a real complaint. An earlier draft used a line copied verbatim from
           # test_unlabelled.csv; the request_id had been made synthetic but the text had not.
           # A public repository should not carry customer wording, even with no identifier beside it.
           "request_text": "screen of my air fryer has gone blank pls call back", "source": "crm"}
    j = client.post("/api/v1/predict", json=row).json()
    assert j["request_id"] == "SR000001"
    assert j["predicted_team"] in client.get("/api/meta").json()["teams"]

    with_zoho = {**row, "request_id": "SR000002", "source": "legacy_zoho"}
    without = {k: v for k, v in row.items() if k != "source"}
    assert (client.post("/api/v1/predict", json=with_zoho).json()["predicted_team"]
            == client.post("/api/v1/predict", json=without).json()["predicted_team"])


def test_predict_v1_handles_missing_and_unknown_fields_without_crashing(client):
    # nothing at all: the decision falls back to metadata only, and says so
    j = client.post("/api/v1/predict", json={}).json()
    assert j["predicted_team"] and j["warnings"]
    # text present, metadata absent: a normal request, no spurious warning
    j = client.post("/api/v1/predict", json={"request_text": "hi"}).json()
    assert j["predicted_team"] and j["warnings"] == []
    # an unrecognised enum value degrades to a warning rather than failing
    j = client.post("/api/v1/predict", json={"request_text": "hello", "product_family": "spaceship"}).json()
    assert any("spaceship" in w for w in j["warnings"])
    # unknown keys are ignored, not rejected
    assert client.post("/api/v1/predict", json={"request_text": "x", "nonsense_column": 1}).status_code == 200
    # an explicitly null required field is still a 422
    assert client.post("/api/v1/predict", json={"request_text": None}).status_code == 422


def test_predict_v1_malformed_body_and_missing_model(empty_client):
    assert empty_client.post("/api/v1/predict", content="not json",
                             headers={"content-type": "application/json"}).status_code == 422
    r = empty_client.post("/api/v1/predict", json={"request_text": "x"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "model_not_ready"


def test_predict_v1_flags_low_confidence_for_a_human(client):
    j = client.post("/api/v1/predict", json={"request_text": "please call me about my purifier",
                                             "product_family": "water purifier", "channel": "ivr"}).json()
    assert j["needs_clarification"] is True
    assert j["clarifying_question"]


def test_predict_v1_is_the_documented_endpoint(client):
    """One documented surface. /api/route stays a working alias but is out of the schema, so /docs
    cannot drift into advertising two ways to do the same thing."""
    schema = client.get("/openapi.json").json()
    assert "/api/v1/predict" in schema["paths"]
    assert "/api/route" not in schema["paths"]
    assert client.post("/api/route", json={"request_text": "x"}).status_code == 200


def test_static_page_calls_the_versioned_endpoint(client):
    js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    assert "/api/v1/predict" in js
    assert "predicted_team" in js and "justification" in js
