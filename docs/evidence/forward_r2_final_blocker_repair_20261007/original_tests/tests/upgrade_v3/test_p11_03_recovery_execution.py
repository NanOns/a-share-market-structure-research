from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports/upgrade_v3/P11-03-RECOVERY-EXECUTION-20260913.json"


def test_p11_03_authorized_recovery_postconditions():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["contract_version"] == "V3_P11_AUTHORIZED_RECOVERY_POSTCONDITION_V1_0"
    assert report["status"] == "FULL_PASS"
    assert report["deleted_object_count"] == 19
    assert report["deleted_file_bytes_accounted"] == 25295015262
    assert all(report["postconditions"].values())
    assert report["production_database"]["unchanged"] is True
    assert report["safety"]["tdx_mutated"] is False
    assert report["safety"]["tables_deleted"] is False
    assert report["safety"]["vacuum_executed"] is False
