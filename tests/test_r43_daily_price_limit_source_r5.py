import hashlib
import json

import pytest

from workbench_analysis.r43_daily_price_limits import _current_candidate_daily_source


def _fixture(root, rows=None):
    day = "2026-10-14"
    owner_id = "a" * 64
    candidate_dir = root / "data/v4/dynamic_daily_owners" / day / owner_id
    raw_path = candidate_dir / "owner_v3/owners" / day / "raw.jsonl.gz"
    raw_path.parent.mkdir(parents=True)
    raw_bytes = b"frozen raw candidate"
    raw_path.write_bytes(raw_bytes)
    raw = {
        "path": raw_path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "bytes": len(raw_bytes),
    }
    (candidate_dir / "SUCCESSOR_CANDIDATE.json").write_text(
        json.dumps({
            "accepted_trade_date": day,
            "owners": {day: {"raw": raw}},
        }),
        encoding="utf-8",
    )
    daily_path = candidate_dir / "sources/daily.json"
    daily_path.parent.mkdir(parents=True)
    daily_path.write_text(
        json.dumps({"observed_at": "2026-10-20T17:52:01+08:00", "rows": rows or [
            {"code": "sh.600000", "date": day, "preclose": "10.00"},
        ]}),
        encoding="utf-8",
    )
    return day, raw


def test_daily_limit_source_follows_exact_candidate_raw_binding(tmp_path):
    day, raw = _fixture(tmp_path)

    binding, daily = _current_candidate_daily_source(tmp_path, {"raw": raw}, day)

    assert binding["trade_date"] == day
    assert binding["candidate_owner_id"] == "a" * 64
    assert binding["source_contract"] == "CANDIDATE_BAOSTOCK_DAILY_SOURCE_V1"
    assert daily["rows"][0]["date"] == day


def test_daily_limit_source_rejects_wrong_trade_date(tmp_path):
    day, raw = _fixture(tmp_path, [{"code": "sh.600000", "date": "2026-10-15"}])

    with pytest.raises(ValueError, match="DAILY_LIMIT_BAOSTOCK_CAPTURE_DATE_MISMATCH"):
        _current_candidate_daily_source(tmp_path, {"raw": raw}, day)


def test_daily_limit_source_rejects_raw_binding_mismatch(tmp_path):
    day, raw = _fixture(tmp_path)
    forged = dict(raw, source_variant="unbound")

    with pytest.raises(ValueError, match="DAILY_LIMIT_CANDIDATE_RAW_BINDING_MISMATCH"):
        _current_candidate_daily_source(tmp_path, {"raw": forged}, day)
