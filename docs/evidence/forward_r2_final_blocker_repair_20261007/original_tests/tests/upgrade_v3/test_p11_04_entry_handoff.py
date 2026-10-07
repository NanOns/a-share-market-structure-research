from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports/upgrade_v3/P11-04-ENTRY-HANDOFF-20260913.json"


def test_p11_04_switches_primary_entry_and_preserves_fallback():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["contract_version"] == "V3_P11_ENTRY_HANDOFF_V1_0"
    assert report["status"] == "FULL_PASS"
    assert all(report["checks"].values())
    assert report["handoff"]["previous_route"] == "/v2"
    assert report["handoff"]["active_route"] == "/v3"
    assert report["handoff"]["fallback_route"] == "/view"
    assert report["handoff"]["switch_executed"] is True
    assert report["safety"]["production_database_mutated"] is False
    assert report["safety"]["old_tables_deleted"] is False
