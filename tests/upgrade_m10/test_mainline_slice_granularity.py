from datetime import date
import importlib.util
from pathlib import Path

import pandas as pd
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_m10_mainline_preview.py"
SPEC = importlib.util.spec_from_file_location("build_m10_mainline_preview", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_split_mainline_daily_frames_isolates_each_trade_date():
    frame = pd.DataFrame(
        {
            "sector_id": ["A", "B", "C"],
            "trade_date": ["2026-09-09 15:00:00", date(2026, 9, 8), "2026-09-09"],
        }
    )

    result = MODULE.split_mainline_daily_frames(frame)

    assert list(result) == [date(2026, 9, 8), date(2026, 9, 9)]
    assert set(result[date(2026, 9, 8)]["sector_id"]) == {"B"}
    assert set(result[date(2026, 9, 9)]["sector_id"]) == {"A", "C"}
    assert all(set(part["trade_date"]) == {trade_date} for trade_date, part in result.items())


def test_split_mainline_daily_frames_rejects_missing_trade_date():
    with pytest.raises(ValueError, match="MAINLINE_TRADE_DATE_REQUIRED_FOR_EVERY_ROW"):
        MODULE.split_mainline_daily_frames(pd.DataFrame({"sector_id": ["A"], "trade_date": [None]}))
