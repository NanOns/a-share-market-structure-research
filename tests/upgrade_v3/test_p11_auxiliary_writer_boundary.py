from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports/upgrade_v3/P11-02-AUD-AUXILIARY-WRITES-BOUNDARY-20260913.json"


def test_auxiliary_writer_audit_is_bounded_without_table_cleanup():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["contract_version"] == "V3_P11_AUXILIARY_LEGACY_WRITER_BOUNDARY_V1_0"
    assert report["status"] == "FULL_PASS"
    assert report["audit_disposition"] == "RESOLVED_WITH_BOUNDED_LEGACY_WRITER_BOUNDARY"
    assert all(report["checks"].values())
    assert report["database_read_boundary"]["read_only"] is True
    assert report["safety"]["production_mutation_executed"] is False
    assert report["safety"]["legacy_tables_deleted"] is False
    assert report["retention_boundary"]["table_cleanup"] == "NOT_IN_SCOPE"
