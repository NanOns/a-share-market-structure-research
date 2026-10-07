import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports" / "upgrade_v3" / "P11-DAILY-OPERATION-20260913.json"


def test_p11_daily_operation_receipt_is_full_pass_and_effect_gate_is_honest():
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    assert payload["status"] == "FULL_PASS"
    assert payload["contract_version"] == "V3_P11_DAILY_OPERATION_V1_0"
    assert all(payload["checks"].values())
    assert payload["daily_run"]["live_event"] == "NEW_DAILY_FORWARD_CAPTURE"
    assert payload["forward_observation"]["outcome_status_counts"] == {"OBSERVED": payload["forward_observation"]["outcome_row_count"]}
    assert payload["forward_evaluation"]["status"] == "DATA_INSUFFICIENT"
    assert payload["forward_evaluation"]["probability_claim"] is False
    assert payload["forward_evaluation"]["synthetic_dates_used"] is False
    assert payload["safety"]["tdx_inputs_modified"] is False
