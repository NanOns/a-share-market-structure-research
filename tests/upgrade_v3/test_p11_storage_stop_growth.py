from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports/upgrade_v3/P11-01-STORAGE-STOP-GROWTH-GATE-20260913.json"


def test_p11_storage_stop_growth_gate_is_ready_for_separate_handoff():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["contract_version"] == "V3_P11_STORAGE_STOP_GROWTH_GATE_V1_0"
    assert report["status"] == "FULL_PASS"
    assert all(report["checks"].values())
    assert report["storage_stop_growth"]["status"] == "FULL_PASS"
    assert report["runtime_entry"]["current_primary_entry"]["route"] == "/v2"
    assert report["runtime_entry"]["target_p11_04_entry"]["route"] == "/v3"
    assert report["runtime_entry"]["target_p11_04_entry"]["switch_executed"] is False
    assert report["safety"]["runtime_entry_mutated"] is False
    assert report["safety"]["production_database_mutated"] is False
