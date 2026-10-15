from workbench_analysis.forward_r7 import compute_nominal_settlement
from workbench_analysis.forward_r7_pipeline import (
    accepted_prices_with_status, build_schedules, classify_after_close_capture)
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
        frozen_at="2026-10-14T15:30:00+08:00")
    assert valid["lane"] == "LIVE_OOS"
    assert valid["observed_signal_T0"] == "2026-10-14"
    assert valid["valid_from_session"] == "2026-10-15"
    assert valid["executable_from"] == "2026-10-15T09:30:00+08:00"
    assert valid["execution_semantics"] == "RESEARCH_REFERENCE_ONLY_NOT_EXECUTED"
    late = classify_after_close_capture(trade_date="2026-10-14", sessions=sessions,
        first_available_at="2026-10-14T15:05:00+08:00",
        head_accepted_at="2026-10-14T15:12:00+08:00",
        first_processed_at="2026-10-15T09:30:00+08:00",
        frozen_at="2026-10-15T09:31:00+08:00")
    assert late["lane"] == "LATE_OBSERVED_NOT_PIT"
    assert "FREEZE_AFTER_NEXT_SESSION_OPEN" in late["timing_reasons"]


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
