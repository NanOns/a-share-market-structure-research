import json

from workbench_online.base import FetchResult
from scripts.probe_p09_01_b_ext11 import build_receipt


def test_ext11_current_probe_receipt_separates_observed_quote_from_timestamped_rank():
    body = b'{"data":{"diff":[{"f2":9.26,"f3":-0.96,"f6":604625882,"f12":"600000","f13":1,"f47":255474000,"f168":null},{"f2":11.74,"f3":-0.93,"f6":979990554.2,"f12":"000001","f13":0,"f47":287857000,"f168":1.2}]}}'
    result = FetchResult("2026-09-13T00:30:00+08:00", "2026-09-13T00:30:01+08:00", 200, "application/json", body, "https://push2.eastmoney.com/api/qt/ulist.np/get")
    rows = [
        {"security_id": "SH.600000", "price": 9.26, "ret1": -0.0096, "amount": 604625882, "volume": 255474000, "turnover_rate": None, "quote_time": None},
        {"security_id": "SZ.000001", "price": 11.74, "ret1": -0.0093, "amount": 979990554.2, "volume": 287857000, "turnover_rate": 0.012, "quote_time": None},
    ]
    receipt = build_receipt(result, rows)
    assert receipt["status"] == "DEGRADED_PASS"
    assert receipt["probe"]["status"] == "CURRENT_PROBE_PARSED"
    assert receipt["probe"]["coverage_ratio"] == 1.0
    assert receipt["probe"]["market_coverage"] == {"SH": 1, "SZ": 1, "BJ": 0}
    assert receipt["capability_decision"]["observed_quote"] == "DEGRADED_AVAILABLE_FOR_DISPLAY_ONLY"
    assert receipt["capability_decision"]["timestamped_rank"] == "NOT_VERIFIED"
    assert receipt["guardrails"]["raw_payload_persisted"] is False
    assert "604625882" not in json.dumps(receipt, ensure_ascii=False)


def test_ext11_probe_fail_closed_on_source_failure_without_persisting_partial_data():
    receipt = build_receipt(None, [], error="TimeoutError:timed out")
    assert receipt["status"] == "BLOCKED"
    assert receipt["probe"]["status"] == "SOURCE_UNAVAILABLE_OR_SCHEMA_INVALID"
    assert receipt["capability_decision"]["timestamped_rank"] == "NOT_VERIFIED"
    assert receipt["probe"]["response"]["raw_sha256"] is None
    assert receipt["request_policy"]["network_calls"] == 1
    assert receipt["guardrails"]["raw_payload_persisted"] is False


def test_ext11_receipt_keeps_current_probe_bound_to_v3_contract():
    receipt = build_receipt(None, [], error="SOURCE_UNAVAILABLE")
    assert receipt["source_id"] == "EXT11"
    assert receipt["contract_id"] == "V3_ONLINE_SOURCE_REGISTRY_1"
    assert receipt["request_policy"]["timeout_seconds"] == 8
    assert receipt["request_policy"]["max_response_bytes"] == 2000000
    assert receipt["next_stage"] == "P09-01-B-EXT11-RETRY"
