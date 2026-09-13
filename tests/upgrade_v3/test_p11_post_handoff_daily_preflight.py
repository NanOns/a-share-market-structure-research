import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports" / "upgrade_v3" / "P11-POST-HANDOFF-DAILY-PREFLIGHT-20260913.json"


def test_p11_post_handoff_daily_preflight_receipt_is_full_pass_and_read_only():
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    assert payload["status"] == "FULL_PASS"
    assert payload["contract_version"] == "V3_P11_POST_HANDOFF_DAILY_PREFLIGHT_V1_0"
    assert all(payload["checks"].values())
    assert payload["daily_dry_run"]["status"] == "DRY_RUN_READY"
    assert payload["daily_dry_run"]["resolved_cutoff_date"] == payload["daily_dry_run"]["local_tdx_latest_session"]
    assert payload["database_boundary"]["before"] == payload["database_boundary"]["after"]
    assert payload["safety"]["production_database_written"] is False
    assert payload["safety"]["tdx_inputs_modified"] is False
