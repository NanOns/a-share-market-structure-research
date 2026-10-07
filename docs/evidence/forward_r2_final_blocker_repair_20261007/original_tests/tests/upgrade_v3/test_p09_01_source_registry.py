import json
from pathlib import Path

from scripts.verify_p09_01_source_registry import EXPECTED_ENDPOINTS, EXPECTED_POOL_TYPES, GUARDRAILS, REGISTRY, SPEC, build_report, load_registry, validate_registry


def test_static_registry_matches_v3_known_endpoints_and_is_fail_closed():
    payload = load_registry()
    checks = validate_registry(payload, spec_text=SPEC.read_text(encoding="utf-8"), guardrail_text=GUARDRAILS.read_text(encoding="utf-8"))
    assert checks and all(item["status"] == "PASS" for item in checks)
    assert [item["source_id"] for item in payload["sources"]] == list(EXPECTED_ENDPOINTS)
    assert {item["source_id"]: item["endpoint_template"] for item in payload["sources"]} == EXPECTED_ENDPOINTS
    assert payload["enabled"] is False
    assert payload["network_calls_allowed"] is False
    assert all(item["capability_status"] == "NOT_VERIFIED" and item["enabled"] is False for item in payload["sources"])


def test_seven_event_pools_have_distinct_semantics_and_no_invented_field_codes():
    payload = load_registry()
    assert {item["pool_name"]: item["pool_type"] for item in payload["event_pools"]} == EXPECTED_POOL_TYPES
    for source in payload["sources"][:2]:
        assert source["request_contract"]["field_codes"] is None
        assert source["request_contract"]["field_codes_status"] == "UNRESOLVED"
    ext04 = next(item for item in payload["sources"] if item["source_id"] == "EXT04")
    assert "map arrays by returned field names" in ext04["field_contract"]["conversion_rules"]
    ext05 = next(item for item in payload["sources"] if item["source_id"] == "EXT05")
    assert "do not rename source_limit_days as consecutive_limit_days before semantic confirmation" in ext05["field_contract"]["conversion_rules"]


def test_hot_rank_and_quote_sources_are_request_time_only():
    payload = load_registry()
    direct = {"EXT07", "EXT08", "EXT09", "EXT10", "EXT11"}
    for source in payload["sources"]:
        if source["source_id"] in direct:
            assert "REQUEST_TIME_ONLY" in source["storage_policy"]
            assert "FORBIDDEN" in source["storage_policy"]
    ext11 = next(item for item in payload["sources"] if item["source_id"] == "EXT11")
    assert ext11["request_contract"]["batch_size"] == 50
    assert ext11["request_contract"]["supported_markets"] == ["SH", "SZ"]
    assert ext11["request_contract"]["unsupported_markets"] == ["BJ"]


def test_report_is_scoped_full_pass_and_requires_manual_current_probe():
    report = build_report("PASS")
    assert report["status"] == "FULL_PASS"
    assert report["release_ready"] is False
    assert report["evidence"]["network_calls"] == 0
    assert report["verification"]["network_probe"]["status"] == "NOT_RUN_BY_SCOPE"
    assert report["next_stage"] == "P09-01-B"
    assert report["next_stage_requires_manual_start"] is True


def test_checked_in_receipt_has_the_same_static_scope():
    root = Path(__file__).resolve().parents[2]
    receipt_path = root / "reports/upgrade_v3/P09-01-A_SOURCE_REGISTRY.json"
    assert receipt_path.exists()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["stage"] == "P09-01-A"
    assert receipt["status"] == "FULL_PASS"
    assert receipt["next_stage"] == "P09-01-B"
