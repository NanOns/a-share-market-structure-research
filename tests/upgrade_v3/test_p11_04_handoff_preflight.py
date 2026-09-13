from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports/upgrade_v3/P11-04-HANDOFF-PREFLIGHT-20260913.json"


def test_p11_04_handoff_preflight_is_ready_without_switching_entry():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["contract_version"] == "V3_P11_HANDOFF_PREFLIGHT_V1_0"
    assert report["status"] == "FULL_PASS"
    assert all(report["checks"].values())
    assert report["handoff"]["preflight_status"] == "READY_FOR_EXPLICIT_P11_04_SWITCH"
    assert report["handoff"]["current_primary_entry"]["route"] == "/v2"
    assert report["handoff"]["target_primary_entry"]["route"] == "/v3"
    assert report["handoff"]["switch_executed"] is False
    assert report["safety"]["runtime_entry_mutated"] is False
    assert report["safety"]["launcher_mutated"] is False
