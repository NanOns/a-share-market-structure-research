from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/verify_p11_02_old_write_and_recovery_preview.py"
REPORT = ROOT / "reports/upgrade_v3/P11-02-OLD-WRITE-RECOVERY-PREVIEW.json"


def _module():
    spec = importlib.util.spec_from_file_location("p11_02_verifier", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_p11_02_report_records_read_only_acceptance():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["contract_version"] == "V3_P11_OLD_WRITE_RECOVERY_PREVIEW_V1_0"
    assert report["status"] in {"FULL_PASS", "DEGRADED_PASS"}
    assert all(report["checks"].values()) is False or report["status"] == "DEGRADED_PASS"
    assert report["database_read_boundary"]["read_only"] is True
    assert report["database_read_boundary"]["unchanged"] is True
    assert report["recovery_preview"]["deletion_authorized"] is False
    assert report["recovery_preview"]["reclaimable_bytes_now"] == 0
    assert report["next_stage"] == "P11-03"


def test_p11_02_core_migrated_domains_have_no_legacy_writer_call_sites():
    audit = _module()._writer_audit()
    assert not audit["syntax_errors"]
    matrix = audit["migrated_domain_matrix"]
    assert {item["domain"] for item in matrix} == {
        "technical",
        "strength",
        "high",
        "member_state",
        "structure",
        "summary",
    }
    assert all(
        item["status"] == "OLD_WRITE_STOP_PROVEN"
        and not item["legacy_non_definition_call_sites"]
        for item in matrix
    )
    assert not audit["current_v3_daily_entry"]["legacy_membership_insert_sites"]
