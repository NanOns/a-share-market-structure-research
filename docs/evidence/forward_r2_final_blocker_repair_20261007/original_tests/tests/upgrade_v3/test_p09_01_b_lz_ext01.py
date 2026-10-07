import json
from pathlib import Path

from workbench_online.base import FetchResult
from scripts.probe_p09_01_b_lz_ext01 import CONTRACT, build_receipt


def test_new_longzijue_ext01_contract_supersedes_old_static_runtime_path_without_enabling_it():
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "v3-longzijue-source-contract-v1"
    assert payload["contract_id"] == "V3_LZ_EXT01_LIMIT_UP_1"
    assert payload["stage"] == "P09-01-B-LZ-EXT01"
    assert payload["source_id"] == "EXT01"
    assert payload["origin"] == "LONGZIJUE_PARSED"
    assert payload["enabled"] is False
    assert payload["request"]["field_codes"] is None
    assert payload["request"]["field_codes_status"] == "UNRESOLVED"
    assert "data.10jqka.com.cn/dataapi/limit_up/limit_up_pool" in payload["request"]["endpoint_template"]


def test_valid_current_json_is_degraded_until_field_scale_and_pagination_are_fixed():
    body = json.dumps({"status_code": 0, "data": {"info": [{"code": "600000", "name": "浦发银行", "latest": 9.26, "change_rate": -0.96, "amount": 604625882, "order_amount": 1200000, "currency_value": 30000000000, "first_limit_up_time": 1700000000, "last_limit_up_time": 1700000100}], "limit_up_count": {"today": {"num": 40, "open_num": 18}}}}).encode("utf-8")
    result = FetchResult("2026-09-13T00:00:00+08:00", "2026-09-13T00:00:01+08:00", 200, "application/json", body, "https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?page=1")
    receipt = build_receipt(result)
    assert receipt["status"] == "DEGRADED_PASS"
    assert receipt["probe"]["status"] == "CURRENT_PROBE"
    assert receipt["probe"]["row_path"] == "$.data.info"
    assert receipt["probe"]["row_count"] == 1
    assert receipt["probe"]["complete_pagination"] is False
    assert receipt["normalized_fields"]["field_scale_status"] == "UNRESOLVED_UNTIL_REPEATED_SAMPLE"
    assert receipt["capability"]["enabled"] is False
    assert receipt["persistence"]["raw_payload_persisted"] is False
    assert "浦发银行" not in json.dumps(receipt, ensure_ascii=False)


def test_invalid_ext01_response_is_unavailable_and_fail_closed():
    result = FetchResult("2026-09-13T00:00:00+08:00", "2026-09-13T00:00:01+08:00", 403, "text/html", b"denied", "https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool")
    receipt = build_receipt(result)
    assert receipt["status"] == "UNAVAILABLE"
    assert receipt["probe"]["status"] == "UNAVAILABLE"
    assert receipt["capability"]["enabled"] is False
    assert receipt["persistence"]["raw_payload_persisted"] is False
    assert receipt["next_stage"] == "P09-01-B-LZ-EXT03"


def test_checked_in_ext01_receipt_is_bound_to_the_new_contract():
    root = Path(__file__).resolve().parents[2]
    receipt = json.loads((root / "reports/upgrade_v3/P09-01-B-LZ-EXT01_CURRENT_PROBE.json").read_text(encoding="utf-8"))
    assert receipt["stage"] == "P09-01-B-LZ-EXT01"
    assert receipt["source_id"] == "EXT01"
    assert receipt["contract_version"] == "v3-lz-ext01-limit-up-v1.0"
    assert receipt["persistence"]["raw_payload_persisted"] is False
