from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports/upgrade_v3/P11-03-OLD-TABLE-RETENTION-DECISION-20260913.json"


def test_old_tables_are_frozen_until_v3_and_ui_migration_complete():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["status"] == "FULL_PASS"
    assert report["user_decision"]["decision"] == "RETAIN_ALL_LEGACY_TABLES"
    assert report["retained_table_count"] == 17
    assert all(item["decision"] == "RETAIN_UNTIL_V3_AND_UI_MIGRATION_COMPLETE" for item in report["retained_tables"])
    assert all(item["actual_action"] == "NONE" for item in report["retained_tables"])
    assert report["database_read_boundary"]["unchanged"] is True
    assert report["safety"]["tables_deleted"] is False
    assert report["safety"]["vacuum_executed"] is False
