from __future__ import annotations

from pathlib import Path
import gzip
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.v4.profile_core import closed_period_trend
from src.v4.replay_r4_identity import accepted_universe_snapshot_id, adjustment_basis_id, target_market_snapshot_id
from src.v4.replay_r4_lfs import parse_pointer, verify_restored
from src.v4.factors.core import Bar, Observation, compute_core
from src.v4.factors.native import historical_market_path
from scripts.build_v4_05_r4_periods import aggregate


def test_p01_closed_qfq_unavailable_keeps_temporal_view_and_blocks_data():
    bars = [{"trade_date": 20260924, "security_id": "S1", "source_security_key": "SH.600000",
             "board_scope": "SH_MAIN", "raw_ohlc": ["10", "11", "9", "10"], "qfq_ohlc": None,
             "volume": 1, "amount": 1, "formal_publication_at": "2026-09-29T06:53:52+00:00"}]
    row = aggregate(bars, ["2026-09-24"], "WEEKLY", "QFQ", "a" * 64)[0]
    assert row["period_view"] == "CLOSED_ONLY"
    assert row["period_status"] == "BLOCKED_BY_ADJUSTMENT"
    assert row["ohlc"] is None
    assert row["adjusted_quality"] == "UNKNOWN"


def test_p02_active_period_qfq_unavailable_keeps_partial_view():
    bars = [{"trade_date": 20260928, "security_id": "S1", "source_security_key": "SH.600000",
             "board_scope": "SH_MAIN", "raw_ohlc": ["10", "11", "9", "10"], "qfq_ohlc": None,
             "volume": 1, "amount": 1, "formal_publication_at": "2026-09-29T06:53:52+00:00"}]
    row = aggregate(bars, ["2026-09-28", "2026-09-29"], "WEEKLY", "QFQ", "a" * 64)[0]
    assert row["period_view"] == "AS_OF_PARTIAL"
    assert row["period_status"] == "BLOCKED_BY_ADJUSTMENT"
    assert row["ohlc"] is None
    assert row["adjusted_quality"] == "UNKNOWN"


def test_p03_closed_period_consumer_unknown_is_due_to_missing_qfq_inputs():
    state = closed_period_trend({"period_view": "CLOSED_ONLY", "close": None,
                                 "ma5": None, "previous_ma5": None}, "weekly")
    assert state.value == "UNKNOWN"
    assert state.unknown_reason == "CLOSED_PERIOD_OR_INPUT_UNAVAILABLE"


def test_snapshot_and_basis_ids_bind_all_identity_dimensions():
    members = [{"security_id": "S1", "membership_basis": "B1", "source_revision_id": "R1", "eligibility_status": "READY"}]
    assert accepted_universe_snapshot_id(members) != accepted_universe_snapshot_id([{**members[0], "source_revision_id": "R2"}])
    assert target_market_snapshot_id("2026-09-28", [{**members[0], "source_security_key": "SH.600000"}]) != target_market_snapshot_id("2026-09-29", [{**members[0], "source_security_key": "SH.600000"}])
    basis = [("S1", "T0_CURRENT_COORDINATE", "GBBQ1", "RAW1")]
    assert adjustment_basis_id(basis) != adjustment_basis_id([("S1", "T0_CURRENT_COORDINATE", "GBBQ2", "RAW1")])


def test_mixed_coordinate_factor_window_fails_closed():
    rows = [Observation("2026-09-25", "ACTUAL", Bar(10, 11, 9, 10, 100, 10, "basis-a", "source-a")),
            Observation("2026-09-28", "ACTUAL", Bar(10, 11, 9, 10.5, 100, 10, "basis-b", "source-b"))]
    ret = compute_core(rows, "S1")["ret1"]
    assert ret.value is None
    assert ret.unknown_reason == "MIXED_ADJUSTMENT_IDENTITY"


def test_market_path_unknown_suffix_does_not_resume_without_new_series_version():
    rows = historical_market_path([("2026-09-24", 0.01), ("2026-09-28", None), ("2026-09-29", 0.02)],
                                  start_sessions=["2026-09-23", "2026-09-24", "2026-09-28"],
                                  start_universe_snapshot_ids=["a"*64, "b"*64, "c"*64],
                                  market_calendar_id="calendar", input_source_digest="d"*64)
    assert rows[0]["quality_state"] == "OBSERVED"
    assert rows[1]["quality_state"] == rows[2]["quality_state"] == "UNKNOWN"
    assert rows[2]["unknown_reason"] == "DAILY_RETURN_UNKNOWN_BREAKS_SERIES_SUFFIX"


def test_market_path_fail_closed_and_revision_ledger_cases_are_observed():
    report = ROOT / "reports/v4_05"
    continuation = json.loads((report / "V4_05_R4_MARKET_PATH_CONTINUATION.json").read_text(encoding="utf-8"))
    regime = json.loads((report / "V4_05_R4_MARKET_REGIME.json").read_text(encoding="utf-8"))
    ledger = json.loads((report / "V4_05_R4_REVISION_LEDGER_IDEMPOTENCY.json").read_text(encoding="utf-8"))
    assert continuation["decision"] == "OPTION_C_FAIL_CLOSED"
    assert continuation["target_path_row_published"] is False
    assert regime["target_row"]["trend_axis"] == "UNKNOWN"
    assert ledger["cases"]["I01_identical_replay"]["no_count_drift"] is True
    assert ledger["cases"]["I03_same_revision_different_payload"]["hard_fail"] is True
    assert ledger["cases"]["I04_transaction_rollback"]["rollback_result"] is True


def test_remote_lfs_pointer_parser_requires_oid_size_and_restored_bytes():
    payload = b"immutable-replay-artifact"
    from hashlib import sha256
    oid = sha256(payload).hexdigest()
    pointer = f"version https://git-lfs.github.com/spec/v1\noid sha256:{oid}\nsize {len(payload)}\n"
    parsed = parse_pointer(pointer)
    assert verify_restored(parsed, payload, oid)["status"] == "PASS"
    try:
        parse_pointer("version https://git-lfs.github.com/spec/v1\noid sha256:bad\nsize 1\n")
    except ValueError as exc:
        assert str(exc) == "INVALID_LFS_POINTER_FIELDS"
    else:
        raise AssertionError("malformed pointer unexpectedly accepted")


def test_independent_numeric_postcheck_has_required_samples_and_recalculations():
    result = json.loads((ROOT / "reports/v4_05/V4_05_R4_INDEPENDENT_NUMERIC_POSTCHECK.json").read_text(encoding="utf-8"))
    assert result["unique_sample_count"] >= 20
    assert set(result["board_coverage"]) == {"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"}
    assert result["sample_category_matrix"]["code_change_confirmed_same_entity"]["count"] >= 1
    assert result["market_axis_recalculation"]["trend_axis"]["match"] is True


def test_r4_period_artifact_contains_only_accepted_temporal_enums():
    receipt = json.loads((ROOT / "reports/v4_05/V4_05_R4_PERIOD_ASOF.json").read_text(encoding="utf-8"))
    path = ROOT / receipt["artifact_path"]
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for index, line in enumerate(stream):
            row = json.loads(line)
            assert row["period_view"] in {"CLOSED_ONLY", "AS_OF_PARTIAL"}
            if row["period_status"] == "BLOCKED_BY_ADJUSTMENT":
                assert row["ohlc"] is None and row["adjusted_quality"] == "UNKNOWN"
            if index > 2500:
                break
