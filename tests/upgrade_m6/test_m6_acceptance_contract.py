import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_m6_starts_only_after_m5_full_pass():
    m5 = load("reports/upgrade_m5/M5_OPERATIONS_RECEIPT.json")
    m6 = load("reports/upgrade_m6/M6_START_RECEIPT.json")
    assert m5["final_status"] == "FULL_PASS"
    assert m5["next_stage"] == "M6_INDEPENDENT_ACCEPTANCE"
    assert m6["started_after"]["status"] == "FULL_PASS"
    assert m6["status"] == "INTERNAL_USER_ACCEPTED"


def test_user_internal_acceptance_replaces_external_audit_gate():
    m6 = load("reports/upgrade_m6/M6_START_RECEIPT.json")
    assert m6["external_audit_claimed"] is False
    assert m6["external_audit_required"] is False
    assert m6["production_entry_switch_allowed"] is True
    contract = (ROOT / "docs/M6_INTERNAL_ACCEPTANCE_OVERRIDE_V1.md").read_text(encoding="utf-8")
    assert "本项目不存在第三方验收方" in contract
    assert "INTERNAL_USER_ACCEPTED" in contract
    assert "两个真实交易日" in contract


def test_m6_acceptance_dates_are_real_published_days():
    import duckdb

    m6 = load("reports/upgrade_m6/M6_START_RECEIPT.json")
    with duckdb.connect(str(ROOT / "data/database/market_research.duckdb")) as con:
        published = {
            str(row[0])
            for row in con.execute(
                "select trade_date from publication_heads where publication_id is not null"
            ).fetchall()
        }
    assert len(m6["acceptance_dates"]) == 2
    assert set(m6["acceptance_dates"]) <= published
