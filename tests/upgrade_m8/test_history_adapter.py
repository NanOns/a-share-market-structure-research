import pandas as pd
import pytest

from workbench_analysis.history_adapter import (
    CURRENT_MEMBERSHIP_BASIS,
    HISTORY_BASIS,
    HistoryAdapterError,
    add_cross_sectional_rs,
    build_sector_base,
    guard_history_inputs,
    run_historical_sector_pipeline,
)


def _inputs():
    date = "2026-09-08"
    technical = pd.DataFrame(
        [
            {
                "security_id": f"SH.{index:06d}",
                "date": date,
                "ret5": index / 100,
                "ret10": index / 200,
                "ret20": index / 100,
                "ret60": index / 300,
                "amount_ratio_5_20": 1.0,
                "raw_close": 10.0 + index,
                "universe_status": "IN_NORMAL_UNIVERSE",
            }
            for index in range(1, 11)
        ]
    )
    memberships = pd.DataFrame(
        [
            {
                "trade_date": date,
                "sector_id": f"INDUSTRY:{'A' if index <= 5 else 'B'}",
                "sector_name": f"行业{'A' if index <= 5 else 'B'}",
                "sector_type": "industry",
                "security_id": f"SH.{index:06d}",
            }
            for index in range(1, 11)
        ]
    )
    return pd.DataFrame(technical), memberships


def test_cross_sectional_rs_is_date_local_and_small_rps_is_null():
    technical, _ = _inputs()
    result = add_cross_sectional_rs(technical.assign(trade_date=pd.to_datetime(technical.date).dt.date))
    assert result.loc[result.security_id == "SH.000001", "rs20"].iloc[0] < 0
    assert result["rps20"].isna().all()
    assert set(result["rps20_valid_n"].astype(int)) == {10}


def test_history_guard_rejects_current_snapshot_backfill_and_missing_membership_date():
    technical, memberships = _inputs()
    prior_technical = technical.assign(date="2026-09-07")
    prior_memberships = memberships.assign(trade_date="2026-09-07")
    with pytest.raises(HistoryAdapterError, match="CURRENT_SNAPSHOT_ONLY"):
        guard_history_inputs(pd.concat([technical, prior_technical]), pd.concat([memberships, prior_memberships]), "2026-09-08", membership_basis=CURRENT_MEMBERSHIP_BASIS)
    missing = memberships[memberships.trade_date != "2026-09-08"]
    with pytest.raises(HistoryAdapterError, match="MEMBERSHIP_DATE_MISSING"):
        guard_history_inputs(technical, missing, "2026-09-08", membership_basis=HISTORY_BASIS)


def test_sector_base_and_scanner_pipeline_are_deterministic_and_explicitly_reconstructed():
    technical, memberships = _inputs()
    result = run_historical_sector_pipeline(technical, memberships, cutoff="2026-09-08")
    assert result["history_basis"] == HISTORY_BASIS
    assert result["audit"]["formal_snapshot_guard_preserved"] is True
    assert set(result["sector_base"]["sector_id"]) == {"INDUSTRY:A", "INDUSTRY:B"}
    assert result["sector_base"]["membership_basis"].eq(HISTORY_BASIS).all()
    assert result["sector_scanner"]["membership_basis"].eq(HISTORY_BASIS).all()
    assert result["sector_scanner"]["historical_backtest_safe"].eq(False).all()
    shuffled = run_historical_sector_pipeline(technical.sample(frac=1, random_state=7), memberships.sample(frac=1, random_state=11), cutoff="2026-09-08")
    left = result["sector_base"].sort_values(["trade_date", "sector_id"]).reset_index(drop=True)
    right = shuffled["sector_base"].sort_values(["trade_date", "sector_id"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(left, right)
    assert len(result["sector_scanner"]) <= len(result["sector_base"])


def test_sector_base_requires_aligned_trade_dates():
    technical, memberships = _inputs()
    technical["trade_date"] = pd.to_datetime(technical.date).dt.date
    with pytest.raises(HistoryAdapterError, match="MEMBERSHIP_DATE_MISSING"):
        guard_history_inputs(technical, memberships.iloc[:0], "2026-09-08")


def test_conflicting_duplicate_membership_is_rejected_instead_of_last_wins():
    technical = pd.DataFrame([{"security_id": "SH.600001", "date": "2026-09-08", "ret20": 0.1}])
    memberships = pd.DataFrame([
        {"security_id": "SH.600001", "trade_date": "2026-09-08", "sector_id": "INDUSTRY:A", "sector_name": "A"},
        {"security_id": "SH.600001", "trade_date": "2026-09-08", "sector_id": "INDUSTRY:A", "sector_name": "B"},
    ])
    with pytest.raises(HistoryAdapterError, match="MEMBERSHIP_DUPLICATE_CONFLICT"):
        guard_history_inputs(technical, memberships, "2026-09-08")
