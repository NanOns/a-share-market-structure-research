from datetime import date
import importlib.util
from pathlib import Path

import pandas as pd
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_m8_m9_preview.py"
SPEC = importlib.util.spec_from_file_location("build_m8_m9_preview", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_split_daily_frames_normalizes_and_isolates_trade_dates():
    frame = pd.DataFrame(
        {
            "security_id": ["A", "B", "C"],
            "trade_date": ["2026-09-09 15:00:00", date(2026, 9, 8), "2026-09-09"],
        }
    )

    result = MODULE.split_daily_frames(frame)

    assert list(result) == [date(2026, 9, 8), date(2026, 9, 9)]
    assert set(result[date(2026, 9, 8)]["security_id"]) == {"B"}
    assert set(result[date(2026, 9, 9)]["security_id"]) == {"A", "C"}
    assert all(set(part["trade_date"]) == {trade_date} for trade_date, part in result.items())


def test_split_daily_frames_rejects_missing_trade_date():
    frame = pd.DataFrame({"security_id": ["A"], "trade_date": [None]})

    with pytest.raises(ValueError, match="TRADE_DATE_REQUIRED_FOR_EVERY_ROW"):
        MODULE.split_daily_frames(frame)


def test_quote_quality_gate_rejects_missing_adjustment_metadata():
    frame = pd.DataFrame(
        {
            "security_id": ["SH.1", "SH.1", "SH.1"],
            "date": [date(2026, 9, 7), date(2026, 9, 8), date(2026, 9, 9)],
            "raw_close": [10.0, 11.0, 12.0],
            "qfq_mul": ["1.0", "1.0", None],
            "qfq_add": ["0.0", "0.0", "0.0"],
            "adjustment_status": ["VERIFIED"] * 3,
            "adjustment_version": ["v1"] * 3,
            "tradable": [True] * 3,
            "has_actual_bar": [True] * 3,
            "data_observed": [True] * 3,
            "is_synthetic_fill": [False] * 3,
            "missing_state": ["BAR"] * 3,
            "is_master_session": [True] * 3,
        }
    )

    result = MODULE.apply_quote_quality_gate(frame)

    assert result.loc[1, "quote_prev_close"] == 10.0
    assert result.loc[1, "quote_ret1_basis"] == "RAW_CLOSE_PREVIOUS_TRADING_DAY"
    assert pd.isna(result.loc[2, "quote_prev_close"])
    assert result.loc[2, "quote_ret1_basis"] == "ADJUSTMENT_METADATA_UNAVAILABLE"
    assert result.loc[2, "quote_state"] == "UNKNOWN_CORPORATE_ACTION"
