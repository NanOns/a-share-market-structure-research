import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports" / "upgrade_v3" / "P11-V3-DAILY-ACTIVATION-20260913.json"


def test_p11_v3_daily_activation_receipt_is_full_pass_and_bounded():
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    assert payload["status"] == "FULL_PASS"
    assert payload["contract_version"] == "V3_P11_DAILY_ACTIVATION_POSTCONDITION_V1_0"
    assert all(payload["checks"].values())
    assert payload["build_result"]["entrypoint"] == "V3_DAILY_INCREMENTAL"
    assert payload["build_result"]["status"] == "BUILT"
    assert sorted(payload["build_result"]["target_domains"]) == ["high", "member_state", "strength", "structure", "summary", "technical"]
    assert payload["build_result"]["reused_result_objects"] >= 5
    assert payload["safety"]["tdx_inputs_modified"] is False
    assert payload["safety"]["old_tables_deleted"] is False
