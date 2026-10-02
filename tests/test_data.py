import os
import re
import time

import pandas as pd
import pytest

from kestrel.data.cleaning import add_meta, bare_team_name, build_team_map, clean_text
from kestrel.data.discovery import discover, fingerprint
from kestrel.data.loader import load_dataset, validate
from kestrel.data.readers import norm_header, read_table
from kestrel.data.schemas import load_schema
from kestrel.errors import DataValidationError
from tests.synth import make_frames, write_dir

MOJIBAKE = re.compile(r"â€|Ã.|Â|�", re.I)
DATE_NOTE = re.compile(r"\(\s*(?:from|since|renamed|effective|w\.e\.f\.?)[^)]*\)", re.I)


def test_header_normalisation():
    assert norm_header(" Request ID ") == "request_id"
    assert norm_header("Created At (IST)") == "created_at_ist"


def test_read_xlsx_and_csv_same_content(tmp_path, frames):
    write_dir(tmp_path / "x", {"train": frames["train"]}, "xlsx")
    write_dir(tmp_path / "c", {"train": frames["train"]}, "csv")
    a = read_table(tmp_path / "x" / "train.xlsx")
    b = read_table(tmp_path / "c" / "train.csv")
    assert list(a.columns) == list(b.columns)
    assert len(a) == len(b) == len(frames["train"])


def test_excel_headers_with_human_names_are_matched(tmp_path, frames):
    df = frames["teams"].rename(columns={"team": "Team", "renamed_to": "Renamed To", "handles": "Handles"})
    df.to_excel(tmp_path / "teams.xlsx", index=False)
    assert list(read_table(tmp_path / "teams.xlsx").columns) == ["team", "renamed_to", "handles"]


def test_sheet_selected_by_role_name(tmp_path, frames):
    with pd.ExcelWriter(tmp_path / "train.xlsx") as w:
        pd.DataFrame({"note": ["ignore me"]}).to_excel(w, sheet_name="Notes", index=False)
        frames["train"].to_excel(w, sheet_name="Train", index=False)
    assert "request_id" in read_table(tmp_path / "train.xlsx", role_hints=("train",)).columns


def test_discovery_by_filename(settings, frames):
    write_dir(settings.input_dir, frames, "xlsx")
    d = discover(settings)
    assert set(d.by_role) == {"train", "test", "resolution", "teams", "sample_submission"}
    assert d.missing == {}
    assert all(f.how == "filename" for f in d.files)


def test_discovery_by_columns_when_name_is_unhelpful(settings, frames):
    settings.input_dir.mkdir(parents=True, exist_ok=True)
    frames["train"].to_excel(settings.input_dir / "export_final_v2.xlsx", index=False)
    frames["test"].to_excel(settings.input_dir / "new batch.xlsx", index=False)
    d = discover(settings)
    roles = {f.path.name: f.role for f in d.files}
    assert roles["export_final_v2.xlsx"] == "train"
    assert roles["new batch.xlsx"] == "test"


def test_discovery_ignores_lock_hidden_and_unknown_types(settings, frames):
    write_dir(settings.input_dir, {"teams": frames["teams"]}, "xlsx")
    (settings.input_dir / "~$teams.xlsx").write_bytes(b"lock")
    (settings.input_dir / ".DS_Store").write_bytes(b"x")
    (settings.input_dir / "notes.txt").write_text("hi")
    assert [f.path.name for f in discover(settings).files] == ["teams.xlsx"]


def test_discovery_duplicate_role_uses_newest(settings, frames):
    write_dir(settings.input_dir, {"teams": frames["teams"]}, "csv")
    write_dir(settings.input_dir, {"teams": frames["teams"]}, "xlsx")
    old = settings.input_dir / "teams.csv"
    os.utime(old, (time.time() - 1000, time.time() - 1000))
    d = discover(settings)
    assert d.by_role["teams"].path.name == "teams.xlsx"
    assert any("Several files" in w for w in d.warnings)


def test_discovery_empty_and_missing_dir(settings):
    d = discover(settings)
    assert d.files == [] and set(d.missing["train"]) == {"train", "resolution", "teams"}
    settings.input_dir.rmdir()
    assert discover(settings).files == []


def test_corrupt_excel_is_reported_not_fatal(settings, frames):
    write_dir(settings.input_dir, {"teams": frames["teams"]}, "xlsx")
    (settings.input_dir / "broken.xlsx").write_bytes(b"not a zip")
    d = discover(settings)
    assert any(f.how == "unreadable" for f in d.files)
    assert "teams" in d.by_role


def test_fingerprint_changes_on_add_and_modify(settings, frames):
    schema = load_schema(settings.schema_file)
    f0 = fingerprint(settings.input_dir, schema)
    write_dir(settings.input_dir, {"teams": frames["teams"]}, "xlsx")
    f1 = fingerprint(settings.input_dir, schema)
    assert f0 != f1
    p = settings.input_dir / "teams.xlsx"
    os.utime(p, (time.time() + 50, time.time() + 50))
    assert fingerprint(settings.input_dir, schema) != f1


def test_validate_reports_missing_files_with_instructions(settings):
    r = validate(settings, "train")
    assert not r.ok
    assert any("train.xlsx" in e.message for e in r.errors)


def test_validate_missing_columns(settings, frames):
    write_dir(settings.input_dir, frames, "xlsx")
    frames["train"].drop(columns=["warranty_status"]).to_excel(settings.input_dir / "train.xlsx", index=False)
    r = validate(settings, "train")
    assert any(e.code == "missing_columns" and "warranty_status" in e.message for e in r.errors)


def test_validate_blank_and_duplicate_ids_and_dates(settings, frames):
    write_dir(settings.input_dir, frames, "xlsx")
    tr = frames["train"].copy()
    tr.loc[0, "request_id"] = ""
    tr.loc[2, "request_id"] = tr.loc[1, "request_id"]
    tr.loc[:400, "created_at_ist"] = "not a date"
    tr.to_excel(settings.input_dir / "train.xlsx", index=False)
    r = validate(settings, "train")
    codes = {i.code for i in r.issues}
    assert {"blank_ids", "duplicate_ids", "bad_timestamps"} <= codes
    with pytest.raises(DataValidationError):
        load_dataset(settings, "train")


def test_validate_ok_on_good_data(settings, frames):
    write_dir(settings.input_dir, frames, "xlsx")
    r = validate(settings, "train")
    assert r.ok, r.as_dict()
    assert r.rows["train"] == len(frames["train"])


def test_predict_action_needs_only_test_file(settings, frames):
    write_dir(settings.input_dir, {"test": frames["test"]}, "csv")
    assert validate(settings, "predict").ok
    assert load_dataset(settings, "predict").test is not None


def test_bad_test_file_does_not_block_training(settings, frames):
    write_dir(settings.input_dir, frames, "xlsx")
    t = frames["test"].copy()
    t.loc[0, "request_id"] = ""
    t.to_excel(settings.input_dir / "test_unlabelled.xlsx", index=False)
    ds = load_dataset(settings, "train")
    assert ds.test is None and any(w.role == "test" for w in ds.report.warnings)


def test_loader_maps_old_team_names_to_current(settings, frames):
    write_dir(settings.input_dir, frames, "xlsx")
    ds = load_dataset(settings, "train")
    assert "Spares Desk" not in set(ds.train.final_team.dropna()) | set(ds.train.bot_team)
    assert "Consumables & Spares" in ds.canon and len(ds.canon) == 7


def test_clean_text_repairs_mojibake_and_normalises():
    broken = "Refund \u2014 please".encode("utf-8").decode("latin-1")
    assert clean_text(broken) == "refund \u2014 please"
    assert clean_text(None) == "" and clean_text("  A\n\tB ") == "a b"


def test_add_meta_has_no_source_leak():
    df = pd.DataFrame({"product_family": ["water purifier"], "warranty_status": ["shield"], "channel": ["chat"], "source": ["crm"]})
    m = add_meta(df).meta[0]
    assert "crm" not in m and "p_water_purifier" in m and "pw_water_purifier_shield" in m


def test_team_map_prefers_recent_name(frames):
    m, canon = build_team_map(frames["teams"], frames["train"])
    assert m["Spares Desk"] == "Consumables & Spares" == m["Consumables & Spares"]
    assert len(canon) == 7


# --- Phase 1: text sanitation, canonical queues, and the rename-date regression -------------------

def test_bare_team_name_strips_the_change_date_from_the_teams_file():
    """The real teams.csv writes 'Installs & Demo (from 15 Jan 2026)'. The date describes the rename, not
    the queue, so it must not survive into a team name."""
    assert bare_team_name("Installs & Demo (from 15 Jan 2026)") == "Installs & Demo"
    assert bare_team_name("Filters & Consumables (from 15 Jan 2026)") == "Filters & Consumables"
    assert bare_team_name("Repairs") == "Repairs"
    assert bare_team_name("") is None and bare_team_name("   ") is None
    assert bare_team_name(None) is None
    assert bare_team_name(float("nan")) is None


def test_canonical_team_names_never_carry_a_date_note(frames):
    """Regression guard. When teams.csv carries the note and the training data uses the bare new name, the
    old logic compared two absent strings and adopted the suffixed label as canonical. That made one queue
    split into two classes and put a name no scorer recognises into predictions.csv."""
    teams = frames["teams"].copy()
    old_name = teams.loc[teams.renamed_to.astype(str).str.strip() != "", "team"].iloc[0]
    teams.loc[teams.team == old_name, "renamed_to"] = "Installs & Demo (from 15 Jan 2026)"

    m, canon = build_team_map(teams, frames["train"])

    assert "Installs & Demo" in canon
    assert len(canon) == 7
    assert not any(DATE_NOTE.search(c) for c in canon), f"canonical names carry a date note: {canon}"
    assert m[old_name] == "Installs & Demo" == m["Installs & Demo"]


def test_a_queue_renamed_with_a_date_note_stays_one_queue(settings, frames):
    """End-to-end on the real pack's shape: two spellings of one queue must not become two classes."""
    f = {k: v.copy() for k, v in frames.items()}
    old_name, new_name = "Spares Desk", "Consumables & Spares"
    f["teams"].loc[f["teams"].team == old_name, "renamed_to"] = f"{new_name} (from 15 Jan 2026)"
    for col in ("first_team", "final_team"):
        f["resolution"][col] = f["resolution"][col].str.replace(old_name, new_name, regex=False)
    f["train"]["team_label"] = f["train"]["team_label"].str.replace(old_name, new_name, regex=False)
    write_dir(settings.input_dir, f, "xlsx")

    ds = load_dataset(settings, "train")

    assert len(ds.canon) == 7
    assert new_name in ds.canon and old_name not in ds.canon
    assert set(ds.train.final_team.dropna()) <= set(ds.canon)
    assert not any(i.code == "unknown_team_names" for i in ds.report.issues)


def test_targets_strictly_match_the_seven_official_queues(settings, frames):
    """Acceptance: every target is one of the 7 official queues, so the model never trains a class the
    client cannot score against, and predictions.csv only ever names a real queue."""
    write_dir(settings.input_dir, frames, "xlsx")
    ds = load_dataset(settings, "train")

    official = set(ds.canon)
    assert len(official) == 7
    targets = set(ds.train.final_team.dropna())
    assert targets <= official, f"targets outside the official queues: {sorted(targets - official)}"
    assert set(ds.train.bot_team) <= official
    assert not any(i.code == "unknown_team_names" for i in ds.report.issues)


def test_a_stray_team_label_is_reported_with_its_row_count(settings, frames):
    """An unknown label is surfaced, not silently dropped: the row count has to appear so nobody can miss it."""
    f = {k: v.copy() for k, v in frames.items()}
    f["resolution"].loc[0, "final_team"] = "Ghost Queue"
    write_dir(settings.input_dir, f, "xlsx")

    ds = load_dataset(settings, "train")

    issue = next(i for i in ds.report.issues if i.code == "unknown_team_names")
    assert "Ghost Queue" in issue.message and "1 rows" in issue.message
    # the row is kept, so the report tells the truth about how many rows the dataset has
    assert (ds.train.final_team == "Ghost Queue").sum() == 1


def test_no_legacy_characters_survive_in_the_loaded_text(settings, frames):
    """Acceptance: the raw text is genuinely broken, and nothing broken reaches the model."""
    raw_hits = frames["train"].request_text.map(lambda t: bool(MOJIBAKE.search(t) if isinstance(t, str) else False)).sum()
    assert raw_hits > 0, "fixture no longer contains mojibake, so this test cannot fail"

    write_dir(settings.input_dir, frames, "xlsx")
    ds = load_dataset(settings, "train")

    assert ds.train.text.map(lambda t: bool(MOJIBAKE.search(t))).sum() == 0
    if ds.test is not None:
        assert ds.test.text.map(lambda t: bool(MOJIBAKE.search(t))).sum() == 0


def test_clean_text_handles_missing_and_non_string_values():
    """Missing values must not become the string 'nan' or crash the loader."""
    assert clean_text(None) == "" and clean_text(float("nan")) == ""
    assert clean_text(42) == ""
    assert clean_text("") == ""
    assert "nan" not in clean_text(None)
