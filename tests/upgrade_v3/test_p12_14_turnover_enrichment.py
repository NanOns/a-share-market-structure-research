import json
from pathlib import Path

from workbench_analysis.turnover_enrichment_v3_3 import (
    CONTRACT_ID,
    LocalDailyFingerprint,
    apply_turnover_enhancement,
    bind_turnover_row,
    select_enrichment_ids,
)


ROOT = Path(__file__).resolve().parents[2]


def test_source_contract_is_bounded_optional_and_fail_closed():
    contract = json.loads((ROOT / "config/p12_14_turnover_source_contract_v1.json").read_text(encoding="utf-8"))
    assert contract["contract_id"] == CONTRACT_ID
    assert contract["enabled_by_default"] is False
    assert contract["request_policy"]["candidate_scope"] == "ALL_SUPPORTED_ROWS_IN_ACTIVE_V3_3_BUNDLE"
    assert contract["request_policy"]["max_candidates"] == "ACTIVE_BUNDLE_RESULT_COUNT"
    assert contract["request_policy"]["max_batches"] == "CEIL(SUPPORTED_CANDIDATE_COUNT/50)"
    assert contract["request_policy"]["max_batch_size"] == 50
    assert contract["request_policy"]["retries"] == 0
    assert contract["request_policy"]["raw_payload_persisted"] is False
    assert "CORE_V3_3_SCORE_OR_CATEGORY_RANK" in contract["forbidden_uses"]
    assert "SECONDARY_ORDER_FOR_QUALIFIED_UNRANKED" in contract["allowed_uses"]
    assert contract["failure_policy"] == "FAIL_CLOSED_WITHOUT_BLOCKING_LOCAL_PIPELINE"


def test_candidate_selection_is_stable_deduplicated_and_market_bounded():
    values = ["BJ.920028", "SH.600000", "SH.600000"] + [f"SZ.{n:06d}" for n in range(30)]
    selected = select_enrichment_ids(values)
    assert selected[0] == "SH.600000"
    assert len(selected) == 31
    assert len(set(selected)) == 31
    assert all(value.startswith(("SH.", "SZ.")) for value in selected)


def test_turnover_binds_only_when_local_session_fingerprint_matches():
    local = LocalDailyFingerprint("SZ.002491", "2026-09-15", 22.23, 5_840_461_313.31, 267_049_400)
    row = {
        "security_id": "SZ.002491",
        "price": 22.23,
        "amount": 5_840_461_313.31,
        "volume": 267_049_400,
        "turnover_rate": 0.227,
        "observed_at_utc": "2026-09-16T01:00:00Z",
        "source_id": "EASTMONEY_QUOTES_LATEST",
    }
    bound = bind_turnover_row(row, local)
    assert bound["capability_status"] == "BOUND"
    assert bound["turnover_rate"] == 0.227
    assert bound["trade_date"] == "2026-09-15"

    stale = bind_turnover_row({**row, "amount": row["amount"] / 2}, local)
    assert stale["capability_status"] == "UNAVAILABLE"
    assert stale["turnover_rate"] is None
    assert stale["reason"] == "LOCAL_SESSION_FINGERPRINT_MISMATCH"


def test_source_failure_and_unsupported_market_do_not_fabricate_zero():
    sh = LocalDailyFingerprint("SH.600000", "2026-09-15", 10, 1000, 100)
    assert bind_turnover_row(None, sh)["capability_status"] == "SOURCE_FAILED"
    bj = LocalDailyFingerprint("BJ.920028", "2026-09-15", 10, 1000, 100)
    result = bind_turnover_row(None, bj)
    assert result["capability_status"] == "UNSUPPORTED_MARKET"
    assert result["turnover_rate"] is None


def test_source_timestamp_must_match_target_session_when_present():
    local = LocalDailyFingerprint("SZ.002491", "2026-09-15", 22.23, 1000, 100)
    row = {"security_id": "SZ.002491", "price": 22.23, "amount": 1000, "volume": 100,
           "turnover_rate": .03, "quote_time": "20260916150001", "source_id": "TENCENT_QUOTES_LATEST"}
    result = bind_turnover_row(row, local)
    assert result["capability_status"] == "UNAVAILABLE"
    assert result["reason"] == "SOURCE_SESSION_DATE_MISMATCH"


def test_matching_post_close_source_timestamp_is_session_verified():
    local = LocalDailyFingerprint("SZ.002491", "2026-09-15", 22.23, 1000, 100)
    row = {"security_id": "SZ.002491", "price": 22.23, "amount": 1000, "volume": 100,
           "turnover_rate": .03, "quote_time": "20260915161415", "source_id": "TENCENT_QUOTES_LATEST"}
    assert bind_turnover_row(row, local)["session_binding_status"] == "SESSION_VERIFIED"


def test_turnover_enhancement_orders_only_qualified_unranked_and_preserves_core_fields():
    candidates = [
        {"security_id": "SZ.000001", "primary_category": "A", "selection_mode": "X", "rank_status": "QUALIFIED_UNRANKED", "category_rank": None, "score": None},
        {"security_id": "SZ.000002", "primary_category": "A", "selection_mode": "X", "rank_status": "QUALIFIED_UNRANKED", "category_rank": None, "score": None},
        {"security_id": "SZ.000003", "primary_category": "A", "selection_mode": "X", "rank_status": "QUALIFIED_UNRANKED", "category_rank": None, "score": None},
        {"security_id": "SH.600000", "primary_category": "A", "selection_mode": "X", "rank_status": "SCORED", "category_rank": 7, "score": .63},
    ]
    evidence = [
        {"security_id": "SZ.000001", "capability_status": "BOUND", "turnover_rate": .01},
        {"security_id": "SZ.000002", "capability_status": "BOUND", "turnover_rate": .05},
        {"security_id": "SZ.000003", "capability_status": "BOUND", "turnover_rate": .03},
        {"security_id": "SH.600000", "capability_status": "BOUND", "turnover_rate": .02},
    ]
    enhanced = {row["security_id"]: row for row in apply_turnover_enhancement(candidates, evidence)}
    assert all(row["turnover_enhanced_rank"] is None for row in enhanced.values())
    assert all(row["turnover_activity_percentile"] is None for row in enhanced.values())
    assert all("TURNOVER_BASIS_NOT_VERIFIED" in row["turnover_reason_codes"] for row in enhanced.values())
    assert enhanced["SH.600000"]["category_rank"] == 7
    assert enhanced["SH.600000"]["score"] == .63
