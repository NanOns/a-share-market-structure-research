import json
from pathlib import Path

from scripts.verify_m14_01_source_registry import GUARDRAILS, REGISTRY, validate_registry


def test_m14_registry_is_fail_closed_and_has_four_datasets():
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    checks = validate_registry(payload, GUARDRAILS.read_text(encoding="utf-8"))
    assert all(item["status"] == "PASS" for item in checks)
    assert payload["enabled"] is False
    assert payload["network_calls_allowed"] is True
    assert payload["network_policy"] == "M14-01_PROBE_ONLY"
    assert payload["personal_collection_policy"] == "M14-02_BOUNDED_PERSONAL_ONLY"
    assert payload["production_network_enabled"] is False
    assert {item["dataset"] for item in payload["datasets"]} == {
        "HOT_RANKINGS",
        "EXTERNAL_EVIDENCE",
        "QUOTES_LATEST",
        "LH_LIST",
    }


def test_no_source_or_dataset_can_claim_verified_or_enabled():
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert all(item["enabled"] is False for item in payload["source_candidates"])
    assert all(item["terms_state"] in {"NOT_VERIFIED", "REJECTED"} for item in payload["source_candidates"])
    assert all(item["status"] in {"NOT_VERIFIED", "UNAVAILABLE", "REJECTED"} for item in payload["source_candidates"])
    assert all(item["status"] in {"NOT_VERIFIED", "UNAVAILABLE", "REJECTED"} for item in payload["datasets"])


def test_review_closes_unlicensed_candidates_without_enabling_them():
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    candidates = {item["source_id"]: item for item in payload["source_candidates"]}
    assert all(item["enabled"] is False for item in candidates.values())
    assert all(item["status"] == "REJECTED" for item in candidates.values())
    assert all(item["terms_state"] == "REJECTED" for item in candidates.values())
    datasets = {item["dataset"]: item for item in payload["datasets"]}
    assert datasets["HOT_RANKINGS"]["status"] == "REJECTED"
    assert datasets["QUOTES_LATEST"]["status"] == "NOT_VERIFIED"
    assert datasets["EXTERNAL_EVIDENCE"]["status"] == "UNAVAILABLE"
    assert datasets["LH_LIST"]["status"] == "UNAVAILABLE"


def test_contract_and_plan_are_present():
    root = Path(__file__).resolve().parents[2]
    assert (root / "docs/M14_SOURCE_VALIDATION_CONTRACT_V1.md").exists()
    assert "## 14. M14：免费在线增强" in (root / "docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md").read_text(encoding="utf-8")


def test_probe_report_is_metadata_only_and_keeps_capabilities_unverified():
    root = Path(__file__).resolve().parents[2]
    report = json.loads((root / "reports/upgrade_m14/m14_01_source_probe_report_20260911.json").read_text(encoding="utf-8"))
    assert report["probe_policy"]["credentials_used"] is False
    assert report["probe_policy"]["raw_payloads_persisted"] is False
    assert report["probe_policy"]["production_tables_written"] is False
    assert len(report["sources"]) == 2
    assert all(source["capability_status"] == "NOT_VERIFIED" for source in report["sources"])
    ths = next(source for source in report["sources"] if source["source_id"] == "TONGHUASHUN_HOT_RANK")
    assert ths["api"]["required_rank_fields_present"] is True
    assert ths["api"]["source_as_of_present"] is False
