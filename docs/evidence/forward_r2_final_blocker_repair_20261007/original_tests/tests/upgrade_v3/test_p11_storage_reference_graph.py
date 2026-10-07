from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports/upgrade_v3/P11-02-AUD-STORAGE-REFERENCE-GRAPH-20260913.json"


def test_storage_reference_graph_is_fully_reconciled_without_mutation():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["contract_version"] == "V3_P11_STORAGE_REFERENCE_GRAPH_AUDIT_V1_0"
    assert report["status"] == "FULL_PASS"
    assert report["audit_disposition"] == "RESOLVED_AS_CURRENT_OR_HISTORICAL_REFERENCE_NO_AUTO_ACTION"
    assert all(report["checks"].values())
    assert report["catalog_summary"]["storage_object_count"] == 52
    assert report["catalog_summary"]["prior_stale_flags_classified_historically"] == 17
    assert report["issues"]["flagged_objects_without_known_row_graph"] == []
    assert report["issues"]["unexpected_missing_physical_artifact"] == []
    assert report["storage_decision"]["automatic_action"] == "NONE"
    assert report["storage_decision"]["clear_referenced_flags"] is False
    assert report["storage_decision"]["delete_storage_objects"] is False
    assert report["safety"]["production_mutation_executed"] is False
    assert report["database_read_boundary"]["read_only"] is True
