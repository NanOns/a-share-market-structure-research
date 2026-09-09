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
    assert m6["status"] in {"IN_PROGRESS", "AWAITING_EXTERNAL_AUDIT"}


def test_developer_cannot_self_issue_external_audit_pass():
    m6 = load("reports/upgrade_m6/M6_START_RECEIPT.json")
    assert m6["external_audit_claimed"] is False
    assert m6["production_entry_switch_allowed"] is False
    contract = (ROOT / "docs/M6_INDEPENDENT_ACCEPTANCE_CONTRACT_V1.md").read_text(encoding="utf-8")
    assert "不得自行签发 `EXTERNAL_AUDIT_PASS`" in contract
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

