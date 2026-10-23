from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v4 import scoped_promotions_r3 as scoped


def _a05_payload(trade_date: str) -> dict:
    return {
        "trade_date": trade_date,
        "scope": "CURRENT_SNAPSHOT_ONLY",
        "AS_RECORDED": False,
        "historical_PIT_equivalent": False,
        "amount_a_warm_branch_enabled": False,
        "accepted_candidate": "candidate",
        "artifact": "artifact",
        "acceptance_record": "acceptance",
        "full_541_sector_diff": "diff",
        "rotation_context_readback": "rotation",
        "algorithm_parameter_bindings": [],
        "normal_quote_universe": 3,
        "zero_member_sector_rows": 0,
    }


def test_a05_reader_uses_explicit_snapshot_date_without_a_code_default(monkeypatch, tmp_path):
    trade_date = "2032-04-15"
    payload = _a05_payload(trade_date)
    candidate = {
        "current_snapshot_replay": payload["artifact"],
        "A05_acceptance_record": payload["acceptance_record"],
        "full_accepted_artifact_diff": payload["full_541_sector_diff"],
        "rotation_context_readback": payload["rotation_context_readback"],
        "unchanged_algorithm_parameters": payload["algorithm_parameter_bindings"],
        "market_universe_count": payload["normal_quote_universe"],
        "zero_member_sector_rows": payload["zero_member_sector_rows"],
    }
    monkeypatch.setattr(scoped, "read_payload", lambda root, key: ({}, payload))
    monkeypatch.setattr(scoped, "bound", lambda root, ref: json.dumps(candidate).encode("utf-8"))
    monkeypatch.setattr(scoped, "rows", lambda root, ref: [{"trade_date": trade_date, "value": 1}])
    monkeypatch.setattr(scoped, "reference", lambda root, path: {"path": str(path)})

    result = scoped.read_a05(tmp_path, mode="CURRENT_SNAPSHOT_ONLY", trade_date=trade_date)

    assert result["trade_date"] == trade_date
    assert result["rows"][0]["trade_date"] == trade_date


def test_a05_reader_rejects_snapshot_rows_outside_requested_date(monkeypatch, tmp_path):
    payload = _a05_payload("2032-04-15")
    candidate = {
        "current_snapshot_replay": payload["artifact"],
        "A05_acceptance_record": payload["acceptance_record"],
        "full_accepted_artifact_diff": payload["full_541_sector_diff"],
        "rotation_context_readback": payload["rotation_context_readback"],
        "unchanged_algorithm_parameters": payload["algorithm_parameter_bindings"],
        "market_universe_count": payload["normal_quote_universe"],
        "zero_member_sector_rows": payload["zero_member_sector_rows"],
    }
    monkeypatch.setattr(scoped, "read_payload", lambda root, key: ({}, payload))
    monkeypatch.setattr(scoped, "bound", lambda root, ref: json.dumps(candidate).encode("utf-8"))
    monkeypatch.setattr(scoped, "rows", lambda root, ref: [{"trade_date": "2032-04-16", "value": 1}])

    import pytest
    with pytest.raises(ValueError, match="TRADE_DATE_MISMATCH"):
        scoped.read_a05(tmp_path, mode="CURRENT_SNAPSHOT_ONLY", trade_date="2032-04-15")
