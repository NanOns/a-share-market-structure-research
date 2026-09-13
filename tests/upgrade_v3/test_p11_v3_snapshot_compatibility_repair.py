import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports" / "upgrade_v3" / "P11-V3-SNAPSHOT-COMPATIBILITY-REPAIR-20260913.json"


def test_p11_v3_snapshot_compatibility_repair_is_full_pass_without_deletion():
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    assert payload["status"] == "FULL_PASS"
    assert payload["contract_version"] == "V3_P11_SNAPSHOT_COMPATIBILITY_REPAIR_V1_0"
    assert all(payload["checks"].values())
    assert payload["before"]["missing_count"] == 8
    assert payload["after"]["inserted_count"] == 8
    assert payload["after"]["target_entry_count"] == payload["before"]["source_target_entry_count"]
    assert payload["safety"]["old_snapshot_deleted"] is False
    assert payload["safety"]["old_tables_deleted"] is False
