from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import pytest
from workbench_analysis.forward_pit_ledger_r2 import (append_observation, atomic, canonical, digest, publications, reference)
from workbench_analysis.amount_a_authority_r2 import calculate_candidate, convert_amount
from workbench_analysis.adjusted_price_lineage_r2 import capture_source, classify_lineage, independent_ex_right_reference


def envelope(tmp_path):
    for name, body in [("calendar", {"session_dates": ["2026-09-28", "2026-09-29", "2026-09-30"]}), ("identity", {"identity": "verified"}), ("raw", {"source": "actual"})]:
        atomic(tmp_path/(name+".json"), canonical(body))
    return {"capture_id": "SYNTHETIC_ENGINEERING_ONLY_1", "target_trade_date": "2026-09-28",
            "observed_at": "2026-10-01T00:00:00+00:00", "received_at": "2026-10-01T00:01:00+00:00",
            "expected_available_by": "2026-09-28T16:00:00+00:00", "expected_source_families": ["RAW"],
            "expected_schema_ids": {"RAW": "RAW_V1"}, "identity_complete": True,
            "calendar_binding": reference(tmp_path, tmp_path/"calendar.json"), "identity_binding": reference(tmp_path, tmp_path/"identity.json"),
            "sources": {"RAW": {"bytes_binding": reference(tmp_path, tmp_path/"raw.json"), "schema_id": "RAW_V1",
                                "target_trade_date": "2026-09-28", "received_at": "2026-10-01T00:00:30+00:00", "source_revision": "r1"}}}


def test_pit_no_backdate_duplicate_and_crash_recovery(tmp_path):
    e = envelope(tmp_path)
    with pytest.raises(RuntimeError):
        append_observation(tmp_path, "ledger", e, failure_after_publication=True)
    assert not (tmp_path/"ledger/projections/latest.json").exists()
    retry = append_observation(tmp_path, "ledger", e)
    assert retry["detectors"] == ["DUPLICATE_CAPTURE"]
    assert len(publications(tmp_path, "ledger")) == 1
    p = retry["publication"]
    assert p["first_available_at"] == e["received_at"]
    assert p["knowledge_lineage"] == "RECONSTRUCTED_CORRECTED" and p["AS_RECORDED"] is False
    assert p["sources"]["RAW"]["first_available_at"] == e["sources"]["RAW"]["received_at"]
    assert "LATE_SOURCE" in p["detectors"]


def test_same_day_revision_immutable(tmp_path):
    e = envelope(tmp_path)
    first = append_observation(tmp_path, "ledger", e)["publication"]
    original = (tmp_path/"ledger/publications"/(first["publication_id"]+".json")).read_bytes()
    revision = deepcopy(e)
    revision["capture_id"] = "SYNTHETIC_ENGINEERING_ONLY_2"
    atomic(tmp_path/"revision.json", canonical({"source": "revised"}))
    revision["sources"]["RAW"]["bytes_binding"] = reference(tmp_path, tmp_path/"revision.json")
    revision["sources"]["RAW"]["source_revision"] = "r2"
    revision["received_at"] = "2026-10-01T00:02:00+00:00"
    second = append_observation(tmp_path, "ledger", revision)["publication"]
    assert "SOURCE_REVISION" in second["detectors"]
    assert first["publication_id"] != second["publication_id"]
    assert (tmp_path/"ledger/publications"/(first["publication_id"]+".json")).read_bytes() == original


def test_same_source_repeat_retains_original_first_availability(tmp_path):
    e=envelope(tmp_path)
    first=append_observation(tmp_path,"ledger",e)["publication"]
    e["capture_id"]="SYNTHETIC_ENGINEERING_ONLY_REPEAT"
    e["sources"]["RAW"]["received_at"]="2026-10-01T00:02:00+00:00"
    e["received_at"]="2026-10-01T00:03:00+00:00"
    second=append_observation(tmp_path,"ledger",e)["publication"]
    assert second["sources"]["RAW"]["first_available_at"]==first["sources"]["RAW"]["first_available_at"]


@pytest.mark.parametrize("change,detector", [("missing", "MISSING_EXPECTED_SOURCE"), ("schema", "SCHEMA_DRIFT"), ("target", "TARGET_DATE_MISMATCH"), ("calendar", "CALENDAR_GAP"), ("identity", "IDENTITY_GAP")])
def test_partial_source_detectors(tmp_path, change, detector):
    e = envelope(tmp_path)
    if change == "missing": e["sources"] = {}
    if change == "schema": e["sources"]["RAW"]["schema_id"] = "DRIFT"
    if change == "target": e["sources"]["RAW"]["target_trade_date"] = "2026-09-29"
    if change == "calendar": e["target_trade_date"] = "2026-10-01"
    if change == "identity": e["identity_complete"] = False
    result = append_observation(tmp_path, "ledger", e)["publication"]
    assert detector in result["detectors"] and result["completeness"] == "PARTIAL"


def test_calendar_gap_between_observations(tmp_path):
    e = envelope(tmp_path)
    append_observation(tmp_path, "ledger", e)
    e["capture_id"] = "SYNTHETIC_ENGINEERING_ONLY_3"
    e["target_trade_date"] = e["sources"]["RAW"]["target_trade_date"] = "2026-09-30"
    assert "CALENDAR_GAP" in append_observation(tmp_path, "ledger", e)["detectors"]


def test_binding_and_capture_id_fail_closed(tmp_path):
    e = envelope(tmp_path)
    append_observation(tmp_path, "ledger", e)
    e["received_at"] = "2026-10-01T00:03:00+00:00"
    with pytest.raises(ValueError, match="CAPTURE_ID_CONFLICT"): append_observation(tmp_path, "ledger", e)
    (tmp_path/"raw.json").write_text("tamper", encoding="utf8")
    with pytest.raises(ValueError, match="SOURCE_BINDING_MISMATCH"): publications(tmp_path, "ledger")


def amount_inputs():
    sessions = [(datetime(2026, 1, 1)+timedelta(days=i)).date().isoformat() for i in range(23)]
    members = {s: ["OLD", "OTHER"] for s in sessions}
    rows = {(m,s): {"amount": 100 if m == "OLD" else 300, "state": "ACTUAL_TRADED"} for s in sessions for m in members[s]}
    return dict(target=sessions[-1], sessions=sessions, members_by_session=members, amount_rows=rows,
                source_unit="CNY_YUAN", membership_timestamp="SYNTHETIC_ENGINEERING_ONLY", source_revision="fixture")


def test_currency_is_explicit():
    assert convert_amount("2.5", "CNY_WAN") == Decimal("25000")
    assert convert_amount("2", "CNY_YI") == Decimal("200000000")
    for unit in ["SHARES", "TDX_SOURCE_NATIVE", ""]:
        with pytest.raises(ValueError): convert_amount(10, unit)
    for value in [None, -1, "NaN", "Infinity"]:
        with pytest.raises(ValueError): convert_amount(value, "CNY_YUAN")


def test_exact_twenty_and_concentration_no_threshold_grant():
    args = amount_inputs()
    result = calculate_candidate(**args)
    assert result["prior20_sessions"] == args["sessions"][-21:-1]
    assert result["diagnostic_amount_a"] == "1" and result["formal_amount_a"] is None
    assert result["concentration"]["weights"] == {"OLD": "0.25", "OTHER": "0.75"}
    assert result["coverage_threshold"] is None and not result["v4_11_amount_a_branch_enabled"]


def test_listing_suspension_gap_and_zero_unknown():
    args = amount_inputs()
    for s in args["sessions"][-3:]:
        args["members_by_session"][s].append("IPO")
        args["amount_rows"][("IPO",s)] = {"amount": 10, "state": "ACTUAL_TRADED"}
    args["amount_rows"][("OLD", args["sessions"][-1])] = {"amount": 0, "state": "SUSPENDED_CONFIRMED"}
    del args["amount_rows"][("OTHER", args["sessions"][-2])]
    result = calculate_candidate(**args)
    assert result["comparable_members"] == ["OLD"]
    assert result["coverage_numerator"] == 1 and result["coverage_denominator"] == 3
    assert result["excluded_member_reasons"]["IPO"] == ["LISTING_WARMUP_OR_MEMBERSHIP_CHANGE"]
    assert "DATA_GAP_UNKNOWN" in result["excluded_member_reasons"]["OTHER"][0]
    assert result["diagnostic_amount_a"] == "0"  # actual confirmed suspension, never a missing fallback
    args["amount_rows"][("OLD", args["sessions"][-1])]["state"] = "ACTUAL_TRADED"
    assert calculate_candidate(**args)["diagnostic_amount_a"] is None


def test_amount_calendar_warmup_and_duplicate_calendar():
    args = amount_inputs(); args["target"] = args["sessions"][3]
    assert calculate_candidate(**args)["diagnostic_amount_a"] is None
    args["sessions"].append(args["sessions"][-1])
    with pytest.raises(ValueError, match="INVALID_MARKET_CALENDAR"): calculate_candidate(**args)


def test_capture_knowledge_cannot_rewrite_past(tmp_path):
    path = tmp_path/"actual.bin"; path.write_bytes(b"actual locally read source")
    record = capture_source(tmp_path, path, source_kind="GBBQ", source_identity="TEST_ENGINEERING_ONLY")
    assert classify_lineage(tmp_path, record, knowledge_time=record["received_at"])["lineage"] == "AS_RECORDED"
    assert classify_lineage(tmp_path, record, knowledge_time="2020-01-01T00:00:00Z")["lineage"] == "RECONSTRUCTED_CORRECTED"
    altered = dict(record, first_available_at="2010-01-01T00:00:00Z")
    assert classify_lineage(tmp_path, altered, knowledge_time=record["received_at"])["lineage"] != "AS_RECORDED"
    assert classify_lineage(tmp_path, dict(record, recomputed_now=True), knowledge_time=record["received_at"])["lineage"] == "CURRENT_RECOMPUTED"


@pytest.mark.parametrize("missing", ["first_available_at", "source_revision", "knowledge_time", "source_bytes"])
def test_as_recorded_each_requirement(tmp_path, missing):
    path=tmp_path/"source.bin"; path.write_bytes(b"a")
    record=capture_source(tmp_path,path,source_kind="PROVIDER_FACTOR",source_identity="fixture")
    record.pop(missing)
    assert classify_lineage(tmp_path,record,knowledge_time="2099-01-01T00:00:00Z")["lineage"] != "AS_RECORDED"


def test_price_event_independent_arithmetic():
    assert independent_ex_right_reference(10, cash_per10=10) == Decimal(9)
    assert independent_ex_right_reference(10, bonus_per10=10) == Decimal(5)
    assert independent_ex_right_reference(10, rights_per10=10, rights_price=6) == Decimal(8)


def test_same_day_adjustment_revision_appends_immutable_sources(tmp_path):
    path=tmp_path/"live_source.bin";path.write_bytes(b"revision one")
    first=capture_source(tmp_path,path,source_kind="GBBQ",source_identity="SYNTHETIC_ENGINEERING_ONLY")
    first_bytes=(tmp_path/first["source_bytes"]["path"]).read_bytes()
    path.write_bytes(b"revision two")
    second=capture_source(tmp_path,path,source_kind="GBBQ",source_identity="SYNTHETIC_ENGINEERING_ONLY")
    assert first["source_revision"]!=second["source_revision"]
    assert first["capture_id"]!=second["capture_id"]
    assert (tmp_path/first["source_bytes"]["path"]).read_bytes()==first_bytes
    assert len(list((tmp_path/"data/v4/source_evidence/a07_r2/captures").glob("*.json")))==2
