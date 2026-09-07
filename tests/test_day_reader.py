from __future__ import annotations

from pathlib import Path
import struct

from tdx.day_reader import decode_record, validate_day_file


def test_decode_record_units() -> None:
    raw = struct.pack("<IIIIIfII", 20260904, 1234, 1300, 1200, 1288, 456.5, 789, 0)
    record = decode_record(raw)
    assert record.trade_date == 20260904
    assert record.open == 12.34
    assert record.close == 12.88
    assert record.amount == 456.5
    assert record.volume == 789


def test_validate_rejects_incomplete_tail(tmp_path: Path) -> None:
    path = tmp_path / "sh600000.day"
    path.write_bytes(b"x" * 33)
    result = validate_day_file(path, "sh")
    assert not result["valid"]
    assert result["errors"] == ["INCOMPLETE_TAIL_RECORD"]


def test_validate_complete_file(tmp_path: Path) -> None:
    path = tmp_path / "sz000001.day"
    path.write_bytes(
        struct.pack("<IIIIIfII", 20260903, 1000, 1100, 900, 1050, 100.0, 10, 0)
        + struct.pack("<IIIIIfII", 20260904, 1050, 1150, 1000, 1100, 110.0, 11, 0)
    )
    result = validate_day_file(path, "sz")
    assert result["valid"]
    assert result["record_count"] == 2
    assert result["last_date"] == 20260904

