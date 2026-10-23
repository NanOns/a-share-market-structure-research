from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from phase0_2b_runner import latest_local_trade_date
from tdx.day_reader import DAY_STRUCT


def _write_day(path: Path, dates: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(DAY_STRUCT.pack(day, 1000, 1100, 900, 1000, 1000.0, 100, 0) for day in dates))


def test_phase0_2b_anchor_comes_from_latest_actual_source_bar(tmp_path):
    tdx = tmp_path / "source"
    _write_day(tdx / "vipdoc/sh/lday/sh000001.day", [20261020, 20261021])
    _write_day(tdx / "vipdoc/sz/lday/sz000002.day", [20261019, 20261022])

    assert latest_local_trade_date(tdx, ["SH.000001", "SZ.000002"]) == 20261022


def test_phase0_2b_anchor_skips_missing_source_files_and_fails_closed(tmp_path):
    tdx = tmp_path / "source"
    _write_day(tdx / "vipdoc/bj/lday/bj000003.day", [20261021])

    assert latest_local_trade_date(tdx, ["SZ.999999", "BJ.000003"]) == 20261021

    try:
        latest_local_trade_date(tdx, ["SZ.999999"])
    except RuntimeError as exc:
        assert str(exc) == "SOURCE_TRADE_DATE_UNAVAILABLE"
    else:
        raise AssertionError("missing date authority must fail closed")
