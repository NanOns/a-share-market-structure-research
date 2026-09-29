"""Executable target-date replay and temporal negatives for V4-05 R3."""
from dataclasses import dataclass
import gzip
import json
from pathlib import Path

import pytest

from scripts.build_v4_05_r3_history import visible_bars
from scripts.build_v4_05_r3_periods import aggregate
from src.v4.go_forward_r3 import target_identity
from src.v4.replay_r3_guards import require_factor_visibility, require_market_dates, require_source_identity

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/v4_05"


def receipt(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


@dataclass
class Bar:
    trade_date: int


def fixture_bar(day):
    return {"security_id": "SEC-TEST", "source_security_key": "SH.600000", "board_scope": "SH_MAIN", "trade_date": day,
            "raw_ohlc": ["10", "11", "9", "10"], "qfq_ohlc": ["10", "11", "9", "10"],
            "volume": 100, "amount": 1000.0, "formal_publication_at": "2026-09-29T06:53:52+00:00"}


def test_future_raw_price_does_not_enter_t0_history():
    baseline = visible_bars([Bar(20260924), Bar(20260928)])
    assert visible_bars([*baseline, Bar(20260929)]) == baseline


@pytest.mark.parametrize("kind", ["WEEKLY", "MONTHLY"])
def test_future_sessions_cannot_change_monday_or_month_asof(kind):
    calendar = ["2026-09-24", "2026-09-28", "2026-09-29", "2026-09-30"]
    baseline = aggregate([fixture_bar(20260924), fixture_bar(20260928)], calendar, kind, "QFQ", "x")
    injected = aggregate([fixture_bar(20260924), fixture_bar(20260928), fixture_bar(20260929), fixture_bar(20260930)], calendar, kind, "QFQ", "x")
    assert injected == baseline
    target = [row for row in baseline if row["period_last_session"] == "2026-09-30"]
    assert target and target[0]["period_view"] == "AS_OF_PARTIAL"


def test_future_identity_metadata_cannot_change_target_membership():
    base = {"source_security_key": "SH.600000", "security_id": "SEC-ONE", "security_type": "A_STOCK",
            "list_date": "2000-01-01", "symbol_effective_from": "2000-01-01"}
    a, _ = target_identity({"SH.600000"}, {"SH.600000"}, [base], "2026-09-28")
    b, _ = target_identity({"SH.600000"}, {"SH.600000"}, [{**base, "delist_date": "2026-09-30"}], "2026-09-28")
    assert set(a) == set(b) == {"SH.600000"}
    future, unresolved = target_identity(set(), {"SH.605999"}, [{**base, "source_security_key": "SH.605999", "list_date": "2026-09-29"}], "2026-09-28")
    assert not future and unresolved == ["SH.605999"]


def test_later_gbbq_revision_cannot_replace_accepted_snapshot():
    with pytest.raises(ValueError, match="ACCEPTED_SOURCE_IDENTITY_MISMATCH"):
        require_source_identity("later-revision", receipt("V4_05_R3_DAILY_HISTORY_RECEIPT.json")["gbbq_snapshot_id"])


def test_late_provider_is_excluded():
    with pytest.raises(ValueError, match="PROVIDER_AFTER_FORMAL_PUBLICATION"):
        require_factor_visibility({"late": {"available_at": "2026-09-30T00:00:00Z"}}, "2026-09-29T06:53:52Z")


def test_future_factor_source_is_hard_blocked():
    with pytest.raises(ValueError, match="FUTURE_FACTOR_SOURCE"):
        require_factor_visibility({"future": {"max_source_trade_date": 20260929}}, "2026-09-29T06:53:52Z")


def test_future_market_regime_input_is_hard_blocked():
    with pytest.raises(ValueError, match="FUTURE_MARKET_REGIME_INPUT"):
        require_market_dates([{"trade_date": "2026-09-28"}, {"trade_date": "2026-09-29"}])


def test_target_profile_preserves_row_set_and_unknowns():
    profile = receipt("V4_05_R3_CORE_PROFILE_REPLAY.json")
    assert profile["row_count"] == 5222
    assert profile["upstream_adjusted_unavailable_entities"] == 27
    assert profile["max_source_trade_date"] <= 20260928
    assert profile["quality_counts"]["PARTIAL_UNKNOWN"] == 5222


def test_factor_rows_expose_source_time_and_bootstrap_unknown():
    factors = receipt("V4_05_R3_FACTOR_SOURCE_TIME.json")
    seen = 0
    with gzip.open(ROOT / factors["artifact_path"], "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            assert row["trade_date"] == "2026-09-28"
            for item in row["fields"].values():
                assert item["max_source_trade_date"] <= 20260928
                assert item["available_at"] <= row["formal_publication_at"]
            assert row["fields"]["rps5_delta1"]["unknown_reason"] == "BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY"
            seen += 1
    assert seen == 5222
