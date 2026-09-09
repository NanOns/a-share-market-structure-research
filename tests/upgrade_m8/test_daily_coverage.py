import json

import pandas as pd
import pytest

from workbench_analysis.coverage import CoverageAdapterError, build_historical_coverage, coverage_summary


def _inputs():
    technical = pd.DataFrame(
        [
            {"security_id": "SH.600001", "trade_date": "2026-09-07", "raw_close": 10, "adj_close": 10, "ret20": 0.1, "validity": "VALID"},
            {"security_id": "SH.600001", "trade_date": "2026-09-08", "raw_close": 11, "adj_close": 11, "ret20": 0.2, "validity": "VALID"},
            {"security_id": "SH.600002", "trade_date": "2026-09-08", "raw_close": None, "adj_close": None, "ret20": None, "validity": "INSUFFICIENT"},
        ]
    )
    memberships = pd.DataFrame(
        [
            {"security_id": "SH.600001", "trade_date": "2026-09-07", "sector_id": "INDUSTRY:A", "membership_snapshot_id": "m-1"},
            {"security_id": "SH.600001", "trade_date": "2026-09-08", "sector_id": "INDUSTRY:A", "membership_snapshot_id": "m-2"},
            {"security_id": "SH.600002", "trade_date": "2026-09-08", "sector_id": "INDUSTRY:A", "membership_snapshot_id": "m-2"},
        ]
    )
    structures = pd.DataFrame(
        [
            {"security_id": "SH.600001", "trade_date": "2026-09-08", "queue_name": "STEADY_QUEUE", "hit": True},
            {"security_id": "SH.600001", "trade_date": "2026-09-08", "queue_name": "PULLBACK_QUEUE", "hit": None},
        ]
    )
    return technical, memberships, structures


def test_coverage_is_date_local_and_separates_not_built_from_zero_hit():
    technical, memberships, structures = _inputs()
    result = build_historical_coverage(technical, memberships, structures, cutoff="2026-09-08", expected_security_ids=["SH.600001", "SH.600002"])
    first, latest = result.iloc[0], result.iloc[1]
    assert first.structure_capability == "NOT_BUILT"
    assert latest.structure_capability == "AVAILABLE"
    assert latest.quote_valid_count == 1 and latest.factor_valid_count == 1
    assert latest.structure_unknown_row_count == 1 and latest.structure_unique_hit_security_count == 1
    assert json.loads(latest.queue_hit_counts_json)["STEADY_QUEUE"] == 1
    assert latest.history_basis == "RECONSTRUCTED" and bool(latest.real_observation) is False


def test_coverage_is_order_invariant_and_marks_missing_expected_universe():
    technical, memberships, structures = _inputs()
    left = build_historical_coverage(technical, memberships, structures, cutoff="2026-09-08")
    right = build_historical_coverage(technical.sample(frac=1, random_state=1), memberships.sample(frac=1, random_state=2), structures, cutoff="2026-09-08")
    pd.testing.assert_frame_equal(left, right)
    assert "EXPECTED_UNIVERSE_NOT_SUPPLIED" in json.loads(left.iloc[0].quality_codes)
    assert coverage_summary(left)["date_count"] == 2


def test_coverage_rejects_future_duplicate_and_non_reconstructed_inputs():
    technical, memberships, structures = _inputs()
    with pytest.raises(CoverageAdapterError, match="COVERAGE_REQUIRES_RECONSTRUCTED"):
        build_historical_coverage(technical, memberships, structures, cutoff="2026-09-08", history_basis="OBSERVED")
    with pytest.raises(CoverageAdapterError, match="AFTER_CUTOFF"):
        build_historical_coverage(technical.assign(trade_date="2026-09-09"), memberships, structures, cutoff="2026-09-08")
    with pytest.raises(CoverageAdapterError, match="DUPLICATE"):
        build_historical_coverage(pd.concat([technical, technical.iloc[[0]]]), memberships, structures, cutoff="2026-09-08")


def test_coverage_never_falls_back_to_a_different_price_basis():
    technical, memberships, structures = _inputs()
    with pytest.raises(CoverageAdapterError, match="PRICE_BASIS_COLUMN_MISSING:RAW:raw_close"):
        build_historical_coverage(technical.drop(columns=["raw_close"]), memberships, structures, cutoff="2026-09-08", price_basis="RAW")
    with pytest.raises(CoverageAdapterError, match="PRICE_BASIS_COLUMN_MISSING:TDX_NATIVE_QFQ:adj_close"):
        build_historical_coverage(technical.drop(columns=["adj_close"]), memberships, structures, cutoff="2026-09-08", price_basis="TDX_NATIVE_QFQ")
