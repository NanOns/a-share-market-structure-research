"""Guard capability claims against the independently reproduced daily evidence."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/v4_05"


def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_forward_daily_digest_matches_accepted_head():
    replay = load("V4_05_R2_DAILY_DETERMINISM.json")
    accepted = json.loads((ROOT / "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))
    assert replay["status"] == "PASS"
    assert replay["first_digest"] == replay["second_digest"] == accepted["logical_digest"]
    assert replay["max_source_trade_date"] <= 20260928


def test_incomplete_capabilities_cannot_claim_factor_replay_pass():
    gate = load("V4_05_R2_CAPABILITY_GATE.json")
    scopes = {row["capability_scope"]: row["status"] for row in gate["capabilities"]}
    assert scopes["CURRENT_FORWARD_ADJUSTED_PRICE"] == "FULL_PASS"
    assert scopes["CURRENT_FORWARD_STOCK_CORE"] == "BLOCKED"
    assert scopes["HISTORICAL_AS_RECORDED_ADJUSTED_PRICE"] == "BLOCKED"
    assert gate["data_factor_replay_pass"] == []
