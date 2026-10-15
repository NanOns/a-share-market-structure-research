from workbench_analysis.forward_r7 import compute_nominal_settlement
from workbench_analysis.forward_r7_pipeline import (
    accepted_prices_with_status, build_schedules, classify_after_close_capture,
    classify_membership_provenance, build_daily_universe, next_capture_plan)
from workbench_analysis.r43_owner_replay import complete_target_universe, unknown_active_core_row
from workbench_db.forward_r7_store import summarize_settlement_schedule
from scripts import run_v4_04_full_market_candidate_r4 as profile_builder
from v4.market_regime_ui import RegimeUI


def _observation():
    return {"entity_type": "STOCK", "status": "MATCH", "T0": "2026-10-12",
            "entity_id": "SEC-1", "rule_id": "R", "rule_version": "1",
            "source_hashes": {"raw": "a" * 64}}


def test_active_lifecycle_identity_is_added_and_low_history_stays_unknown():
    assert complete_target_universe({"SEC-OLD"}, {"SEC-NEW"}) == {"SEC-OLD", "SEC-NEW"}
    row = unknown_active_core_row(
        {"security_id": "SEC-NEW", "source_security_key": "SZ.301660",
         "board_scope": "CHINEXT", "list_date": "2026-10-13"},
        "2026-10-14", ["2026-10-13", "2026-10-14"], "NATIVE")
    assert row["quality_codes"] == ["UNKNOWN", "INSUFFICIENT_HISTORY"]
    assert row["profile_quality"] == "INSUFFICIENT_HISTORY"
    assert row["fields"]
    assert all(value["value"] is None for value in row["fields"].values())
    prior_cutoff = getattr(profile_builder, "CUTOFF", None)
    profile_builder.CUTOFF = "2026-10-14"
    try:
        profile = profile_builder.build_row(row, [], [], [], [("2026-10-14", "UNKNOWN")],
            {"source_security_key": "SZ.301660"}, "a" * 64, "b" * 64, ["2026-10-14"],
            RegimeUI("UNKNOWN", "UNKNOWN", None, 0, {"reason": "ISOLATED_TEST"}, "ISOLATED_TEST"))
    finally:
        if prior_cutoff is None: delattr(profile_builder, "CUTOFF")
        else: profile_builder.CUTOFF = prior_cutoff
    assert profile["profile_quality"] == "PARTIAL_UNKNOWN"
    assert profile["states"]["trend_state"]["value"] == "UNKNOWN"


def test_due_schedule_distinguishes_future_not_accepted_gap_and_security_facts():
    sessions = ["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-19"]
    pending = build_schedules([_observation()], "2026-10-12", sessions,
        {"2026-10-12": {"SEC-1": {"close": 10}}}, "2026-10-12T16:00:00+08:00")
    assert pending[0]["schedule_status"] == "PENDING_FUTURE_SESSION"
    not_accepted = build_schedules([_observation()], "2026-10-12", sessions,
        {"2026-10-12": {"SEC-1": {"close": 10}}}, "2026-10-15T16:00:00+08:00")
    assert not_accepted[0]["schedule_status"] == "DUE_SOURCE_NOT_ACCEPTED"
    gap = compute_nominal_settlement(observation=_observation(), due_date="2026-10-13",
        prices_by_date={"2026-10-12": {"SEC-1": {"close": 10}}, "2026-10-13": {}},
        settlement_at="2026-10-14T15:00:00+00:00")
    assert gap["status"] == "SOURCE_GAP"
    suspended = compute_nominal_settlement(observation=_observation(), due_date="2026-10-13",
        prices_by_date={"2026-10-12": {"SEC-1": {"close": 10}},
                        "2026-10-13": {"SEC-1": {"source_status": "SUSPENDED", "source_hash": "b" * 64}}},
        settlement_at="2026-10-14T15:00:00+00:00")
    assert suspended["status"] == "SUSPENDED"
    assert suspended["source_hash"] == "b" * 64


def test_after_close_first_freeze_window_uses_distinct_timestamp_roles():
    sessions = ["2026-10-14", "2026-10-15", "2026-10-16"]
    valid = classify_after_close_capture(trade_date="2026-10-14", sessions=sessions,
        first_available_at="2026-10-14T15:05:00+08:00",
        head_accepted_at="2026-10-14T15:12:00+08:00",
        first_processed_at="2026-10-14T15:13:00+08:00",
        frozen_at="2026-10-14T15:30:00+08:00",source_ready_at="2026-10-14T15:08:00+08:00")
    assert valid["lane"] == "LIVE_OOS"
    assert valid["observed_signal_T0"] == "2026-10-14"
    assert valid["valid_from_session"] == "2026-10-15"
    assert valid["executable_from"] == "2026-10-15T09:30:00+08:00"
    assert valid["execution_semantics"] == "RESEARCH_REFERENCE_ONLY_NOT_EXECUTED"
    assert valid["market_close_at"] == "2026-10-14T15:00:00+08:00"
    assert valid["source_ready_at"] == "2026-10-14T15:08:00+08:00"
    late = classify_after_close_capture(trade_date="2026-10-14", sessions=sessions,
        first_available_at="2026-10-14T15:05:00+08:00",
        head_accepted_at="2026-10-14T15:12:00+08:00",
        first_processed_at="2026-10-15T09:30:00+08:00",
        frozen_at="2026-10-15T09:31:00+08:00")
    assert late["lane"] == "LATE_OBSERVED_NOT_PIT"
    assert "FREEZE_AFTER_NEXT_SESSION_OPEN" in late["timing_reasons"]
    edge = classify_after_close_capture(trade_date="2026-10-14", sessions=sessions,
        first_available_at="2026-10-14T15:01:00+08:00",
        head_accepted_at="2026-10-14T15:02:00+08:00",
        first_processed_at="2026-10-15T09:29:00+08:00",
        frozen_at="2026-10-15T09:29:59+08:00")
    assert edge["lane"] == "LIVE_OOS"
    at_open = classify_after_close_capture(trade_date="2026-10-14", sessions=sessions,
        first_available_at="2026-10-14T15:01:00+08:00",
        head_accepted_at="2026-10-14T15:02:00+08:00",
        first_processed_at="2026-10-15T09:29:59+08:00",
        frozen_at="2026-10-15T09:30:00+08:00")
    assert at_open["lane"] == "LATE_OBSERVED_NOT_PIT"
    assert "FREEZE_AFTER_NEXT_SESSION_OPEN" in at_open["timing_reasons"]


def test_membership_provenance_requires_same_day_timestamps_and_bound_source():
    binding = {"path": "sector/accepted.json", "sha256": "a" * 64}
    same_day = {"sector_id": "SAME", "membership_provenance": {
        "observed_at": "2026-10-14T15:03:00+08:00",
        "first_available_at": "2026-10-14T15:04:00+08:00",
        "membership_effective_T0": "2026-10-14",
        "source_sha256": "b" * 64, "source_path": "membership/2026-10-14.json"}}
    derived_only = {"sector_id": "DERIVED_ONLY", "membership_provenance": {
        "observed_at": "2026-10-14T15:03:00+08:00",
        "first_available_at": "2026-10-14T15:04:00+08:00",
        "membership_effective_T0": "2026-10-14"}}
    next_day = {"sector_id": "RETRO", "membership_provenance": {
        "observed_at": "2026-10-15T08:00:00+08:00",
        "first_available_at": "2026-10-15T08:01:00+08:00",
        "membership_effective_T0": "2026-10-14", "source_sha256": "b" * 64,
        "source_path": "membership/2026-10-14.json"}}
    unknown = {"sector_id": "UNKNOWN", "membership_snapshot_id": "latest"}
    result = classify_membership_provenance(trade_date="2026-10-14",
        sector_rows=[same_day, next_day, derived_only, unknown], binding=binding,
        membership_binding={"path": "membership/2026-10-14.json", "sha256": "b" * 64},
        frozen_at="2026-10-14T15:10:00+08:00")
    assert result["by_sector"]["SAME"]["membership_basis"] == "AS_RECORDED"
    assert result["by_sector"]["RETRO"]["membership_basis"] == "MEMBERSHIP_RETRO"
    assert result["by_sector"]["DERIVED_ONLY"]["membership_basis"] == "UNKNOWN_MEMBERSHIP_BASIS"
    assert result["by_sector"]["UNKNOWN"]["membership_basis"] == "UNKNOWN_MEMBERSHIP_BASIS"


def test_stock_price_observation_survives_unknown_sector_membership():
    rows = build_daily_universe(trade_date="2026-10-14",
        stock_rows=[{"security_id": "SEC-1"}],
        raw_rows=[{"security_id": "SEC-1", "close": 10}],
        sector_rows=[{"sector_id": "IND-1", "membership_snapshot_id": "latest"}],
        prior_stock_rows=None, prior_raw_rows=None, prior_sector_rows=None,
        bindings={name: {"sha256": name[0] * 64} for name in ("raw", "core", "sector")},
        captured_at="2026-10-15T16:00:00+08:00", lane="LIVE_OOS",
        membership_basis="UNKNOWN_MEMBERSHIP_BASIS",
        membership_provenance={"IND-1": {"membership_basis": "UNKNOWN_MEMBERSHIP_BASIS"}})
    by_type = {row["entity_type"]: row for row in rows}
    assert by_type["STOCK"]["entity_id"] == "SEC-1"
    assert by_type["STOCK"]["membership_basis"] == "NOT_APPLICABLE"
    assert by_type["SECTOR"]["membership_basis"] == "UNKNOWN_MEMBERSHIP_BASIS"
    assert by_type["SECTOR"]["membership_pit_eligible"] is False
    assert by_type["SECTOR"]["evidence_lane"] == "LATE_OBSERVED_NOT_PIT"


def test_capture_plan_uses_session_gaps_source_readiness_and_next_open(monkeypatch, tmp_path):
    import workbench_analysis.forward_r7_pipeline as pipeline
    head = {"accepted_trade_date": "2026-10-13", "published_sessions": ["2026-10-13"],
            "source_registry": {"2026-10-14": {"freeze": {"path": "freeze-14.json"}}}}
    monkeypatch.setattr(pipeline, "official_sessions", lambda root: [
        "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-19"])
    monkeypatch.setattr(pipeline, "_head", lambda root: head)
    monkeypatch.setattr(pipeline, "_daily_job_snapshot", lambda root: {
        "available": True, "auto_enabled": False, "last_job": None})
    monkeypatch.setattr(pipeline, "_document", lambda root, binding: {
        "source_ready_at": "2026-10-14T18:00:00+08:00"})
    plan = next_capture_plan(tmp_path, now=__import__("datetime").datetime.fromisoformat(
        "2026-10-15T15:01:00+08:00"))
    assert plan["missing_sessions"] == ["2026-10-14", "2026-10-15"]
    assert plan["collection_batch_dates"] == []
    assert plan["signal_T0"] == "2026-10-15"
    assert plan["market_close_at"] == "2026-10-15T15:00:00+08:00"
    assert plan["capture_window_end"] == "2026-10-16T09:30:00+08:00"
    assert "capture_deadline" not in plan
    assert "late_capture_dates" not in plan
    assert plan["status"] == "WAIT_SOURCE_READY"
    assert plan["next_attempt_at"] is None
    head["source_registry"]["2026-10-15"] = {"freeze": {"path": "freeze-15.json"}}
    complete = next_capture_plan(tmp_path, now=__import__("datetime").datetime.fromisoformat(
        "2026-10-15T18:01:00+08:00"))
    assert complete["status"] == "SOURCE_READY"
    assert complete["collection_batch_dates"] == ["2026-10-14", "2026-10-15"]


def test_unverified_schedule_states_never_enter_return_denominator():
    summary = summarize_settlement_schedule("2026-10-14", "RETROSPECTIVE_RESEARCH", 1, [
        {"observation_id": "a", "schedule_status": "DUE_SOURCE_NOT_ACCEPTED"},
        {"observation_id": "b", "schedule_status": "SOURCE_GAP"},
        {"observation_id": "c", "schedule_status": "NO_QUOTE",
         "settlement": {"status": "NO_QUOTE"}},
        {"observation_id": "d", "schedule_status": "SETTLED",
         "settlement": {"status": "SETTLED", "nominal_return": 0.1}},
    ])
    assert summary["outcomes"]["DUE_SOURCE_NOT_ACCEPTED"] == 1
    assert summary["outcomes"]["SOURCE_GAP"] == 1
    assert summary["outcomes"]["NO_QUOTE"] == 1
    assert summary["return_denominator"] == summary["settled_count"] == 1
    assert summary["mean_return"] == 0.1


def test_accepted_lifecycle_is_the_only_source_for_no_quote_or_suspended():
    prices = accepted_prices_with_status(
        [{"security_id": "SEC-TRADED", "close": 10}],
        {"rows": [
            {"security_id": "SEC-SUSPENDED", "status": "SUSPENDED"},
            {"security_id": "SEC-GAP", "status": "DATA_GAP"},
        ]}, source_hash="c" * 64)
    assert prices["SEC-SUSPENDED"]["source_status"] == "SUSPENDED"
    assert prices["SEC-SUSPENDED"]["source_hash"] == "c" * 64
    assert "SEC-GAP" not in prices
    assert prices["SEC-TRADED"]["close"] == 10
