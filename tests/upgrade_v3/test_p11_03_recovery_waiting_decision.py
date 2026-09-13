from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports/upgrade_v3/P11-03-RECOVERY-WAITING-DECISION.json"


def _report():
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_p11_03_register_is_waiting_decision_and_no_recovery_executed():
    report = _report()
    assert report["contract_version"] == "V3_P11_RECOVERY_WAITING_DECISION_V1_0"
    assert report["status"] == "DEGRADED_PASS"
    assert report["decision"]["status"] == "WAITING_DECISION"
    assert report["decision"]["deletion_authorized"] is False
    assert report["decision"]["physical_recovery_executed"] is False
    assert report["decision"]["reclaimed_bytes"] == 0
    assert report["database_read_boundary"]["read_only"] is True
    assert report["database_read_boundary"]["unchanged"] is True


def test_p11_03_register_has_exact_targets_and_carries_open_audits():
    report = _report()
    validation = report["register_validation"]
    assert validation["non_empty"] is True
    assert validation["exact_targets"] is True
    assert validation["unique_targets"] is True
    assert validation["no_action_recorded"] is True
    assert validation["counts_by_class"]["relation_old_copies"] == 4
    assert validation["counts_by_class"]["migrated_result_old_copies"] == 6
    assert validation["counts_by_class"]["extracted_directories"] == 4
    assert validation["counts_by_class"]["backup_objects"] == 16
    assert len(report["independent_audit_items"]) >= 2
    assert all(item["status"] == "OPEN" for item in report["independent_audit_items"])
