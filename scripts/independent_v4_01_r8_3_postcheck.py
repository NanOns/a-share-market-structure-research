from __future__ import annotations

"""Independent R8.3 policy, linkage, and coverage postcheck."""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.official_code_change_event_index import validate_index_coverage  # noqa: E402

DISCOVERY = Path("reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_3.json")
LINKAGE = Path("reports/v4_01/V4_01_IDENTITY_RELATION_LINKAGE_R8_3.json")
INDEX = Path("data/v4/source_evidence/official_code_change_event_index/official_security_code_change_events_v1.jsonl")
COVERAGE = Path("data/v4/source_evidence/official_code_change_event_index/coverage_receipt_v1.json")
INDEX_AUDIT_ITEM = Path("reports/v4_01/V4_01_OFFICIAL_INDEX_COVERAGE_AUDIT_ITEM_R1_20260928.json")
TEST_RECEIPT = Path("reports/v4_joint/V4_R8_3_DM01_TEST_RECEIPT_R1_20260928.json")
OUTPUT = Path("reports/v4_01/V4_01_R8_3_INDEPENDENT_POSTCHECK.json")
OLD_ADJACENCY_SIGNALS = {"ROSTER_EXIT_ENTRY_ADJACENCY", "LIFECYCLE_BOUNDARY_ADJACENCY"}
REQUIRED_BOUNDARIES = {"SECURITY_EXIT", "SECURITY_ENTRY", "LISTING_START", "LISTING_END", "SYMBOL_REASSIGNMENT"}


def sha(path: Path) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def read(path: Path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> int:
    discovery, linkage, coverage_doc = read(DISCOVERY), read(LINKAGE), read(COVERAGE)
    linkage_contract = read(Path("config/security_identity_event_linkage_v1.json"))
    test_receipt = read(TEST_RECEIPT)
    audit_item = read(INDEX_AUDIT_ITEM)
    required_test_names = {
        "test_single_exit_three_unrelated_ipos_does_not_create_three_pairs",
        "test_multiple_exit_entry_same_day_has_no_cartesian_product",
        "test_roster_boundary_without_link_signal_remains_atomic_event",
        "test_lifecycle_boundary_without_link_signal_remains_atomic_event",
        "test_official_code_change_links_nonoverlap_symbols",
        "test_same_issuer_id_creates_candidate_but_does_not_confirm_same",
        "test_same_normalized_name_creates_candidate_but_does_not_confirm_same",
        "test_different_listing_dates_never_confirm_distinct_alone",
        "test_official_distinct_issuer_evidence_confirms_distinct",
        "test_symbol_reuse_disjoint_lifecycle_is_candidate",
        "test_official_event_index_coverage_is_required",
        "test_missing_exchange_event_index_blocks_completeness",
        "test_known_300114_302132_fixture_passes",
        "test_no_specific_security_literals_in_generic_linkage_runtime",
    }
    test_source = (ROOT / "tests/v4_01/test_r8_3_identity_event_linkage.py").read_text("utf-8")
    delta_source = (ROOT / "src/workbench_analysis/continuous_data_maintenance.py").read_text("utf-8")
    identity_runtime = (ROOT / "src/workbench_analysis/security_identity_event_discovery.py").read_text("utf-8")
    index_rows = [json.loads(line) for line in (ROOT / INDEX).read_text(encoding="utf-8").splitlines() if line]
    coverage_rows = coverage_doc.get("coverage_receipts", [])
    coverage = validate_index_coverage(coverage_records=coverage_rows, events=index_rows)
    search_capture = coverage_doc.get("supplemental_search_capture") or {}
    search_manifest_path = Path(str(search_capture.get("path") or ""))
    search_manifest = read(search_manifest_path) if search_manifest_path.is_file() else {}
    raw_search_hashes_valid = bool(search_manifest)
    if search_manifest:
        for query in search_manifest.get("queries", []):
            for page in query.get("pages", []):
                captured = ROOT / str(page.get("capture_path") or "")
                if (not captured.is_file()
                        or hashlib.sha256(captured.read_bytes()).hexdigest() != page.get("response_sha256")):
                    raw_search_hashes_valid = False
    event_signals = [set(row.get("candidate_signals", [])) for row in discovery.get("events", [])]
    all_signals = set().union(*event_signals) if event_signals else set()
    boundary_types = {str(row.get("event_type")) for row in discovery.get("boundary_events", [])}
    pair = next((row for row in discovery.get("events", [])
                 if row.get("source_keys") == ["SZ.300114", "SZ.302132"]), None)
    index_hashes_valid = all(
        hashlib.sha256((ROOT / row["source_capture_path"]).read_bytes()).hexdigest()
        == str(row["source_capture_sha256"]).lower()
        for row in index_rows
    )
    checks = {
        "atomic_boundary_event_contract_present": discovery.get("linkage_contract", {}).get("contract_id")
        == "SECURITY_IDENTITY_EVENT_LINKAGE_V1",
        "required_r8_3_dm01_test_gate_passed": test_receipt.get("status") == "PASS"
        and test_receipt.get("counts", {}).get("failed") == 0
        and all(name in test_source for name in required_test_names),
        "all_boundary_types_contracted": REQUIRED_BOUNDARIES <= set(linkage_contract.get("boundary_event_types", [])),
        "historical_boundary_events_are_atomic": not bool(OLD_ADJACENCY_SIGNALS & all_signals),
        "discovery_candidate_count_is_supported_only": all(
            bool(row.get("candidate_signals")) and not (OLD_ADJACENCY_SIGNALS & set(row.get("candidate_signals", [])))
            for row in discovery.get("events", [])
        ),
        "known_code_change_fixture_confirms_same": bool(pair)
        and pair.get("resolution_status") == "CONFIRMED_SAME_ENTITY_CODE_CHANGE",
        "unresolved_required_scope_candidate_count_zero": discovery.get("unresolved_required_scope_candidate_count") == 0,
        "unlinked_boundary_anomaly_count_zero": discovery.get("unlinked_boundary_anomaly_count") == 0,
        "r7_identity_and_universe_hashes_unchanged": discovery.get("canonical_repair", {}).get("r7_canonical_artifacts_unchanged") is True,
        "no_r7_same_entity_counterexample": discovery.get("canonical_repair", {}).get("confirmed_same_entity_counterexamples") == [],
        "official_event_capture_hashes_valid": index_hashes_valid,
        "official_index_has_all_exchange_receipts": {row.get("exchange") for row in coverage_rows}
        == {"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"},
        "official_index_coverage_fails_closed": coverage.get("coverage_status") == "BLOCKED"
        and coverage.get("event_index_completeness_pass") is False,
        "supplemental_cninfo_capture_is_hash_bound_and_successful": (
            search_capture.get("sha256") == sha(search_manifest_path)
            and search_manifest.get("acceptance") == "PASS_CAPTURE_ONLY"
            and search_manifest.get("coverage_effect") == "DOES_NOT_CLOSE_OFFICIAL_EVENT_INDEX_COVERAGE"
            and len(search_manifest.get("queries", [])) == 12
            and search_manifest.get("failed_query_count") == 0
            and all(row.get("status") == "PASS" and row.get("truncated_at_page_limit") is False
                    for row in search_manifest.get("queries", []))
            and raw_search_hashes_valid
        ),
        "supplemental_cninfo_capture_does_not_claim_full_coverage": (
            coverage_doc.get("query_count") == 12
            and coverage_doc.get("coverage_status") == "BLOCKED"
            and all(row.get("coverage_complete") is False
                    and bool(row.get("unresolved_source_windows")) for row in coverage_rows)
        ),
        "official_index_coverage_audit_item_open_and_independent": (
            audit_item.get("status") == "OPEN"
            and audit_item.get("acceptance_result") == "NOT_ACCEPTED_INCOMPLETE_EXHAUSTIVE_COVERAGE_EVIDENCE"
            and audit_item.get("relationship_to_gate_a", "").startswith("Tracked independently")
            and audit_item.get("evidence", {}).get("event_index_coverage", {}).get("sha256") == sha(COVERAGE)
        ),
        "gate_a_blocked_by_incomplete_official_coverage": discovery.get("gate_a_status") == "BLOCKED"
        and coverage.get("coverage_status") == "BLOCKED",
        "daily_identity_delta_no_cartesian_pairing": "for old in exited:\n        for new in entered:" not in delta_source,
        "generic_identity_runtime_has_no_specific_security_literals": "300114" not in identity_runtime
        and "302132" not in identity_runtime,
    }
    status = "PASS" if all(checks.values()) else "BLOCKED"
    payload = {
        "contract_id": "V4_01_R8_3_INDEPENDENT_POSTCHECK",
        "version": "1.0.0",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "gate_a_status": "BLOCKED" if coverage.get("coverage_status") != "PASS" else discovery.get("gate_a_status"),
        "checks": {key: "PASS" if value else "BLOCKED" for key, value in checks.items()},
        "evidence": {
            "discovery": {"path": DISCOVERY.as_posix(), "sha256": sha(DISCOVERY)},
            "linkage": {"path": LINKAGE.as_posix(), "sha256": sha(LINKAGE)},
            "official_event_index": {"path": INDEX.as_posix(), "sha256": sha(INDEX)},
            "official_index_coverage": {"path": COVERAGE.as_posix(), "sha256": sha(COVERAGE)},
            "official_index_coverage_audit_item": {"path": INDEX_AUDIT_ITEM.as_posix(),
                                                   "sha256": sha(INDEX_AUDIT_ITEM)},
            "supplemental_search_capture": {"path": search_manifest_path.as_posix(),
                                            "sha256": sha(search_manifest_path) if search_manifest_path.is_file() else None},
            "test_receipt": {"path": TEST_RECEIPT.as_posix(), "sha256": sha(TEST_RECEIPT)},
        },
        "candidate_count": discovery.get("candidate_count"),
        "candidate_status_counts": discovery.get("candidate_status_counts"),
        "unresolved_required_scope_candidate_count": discovery.get("unresolved_required_scope_candidate_count"),
        "boundary_event_count": discovery.get("boundary_event_count"),
        "unlinked_boundary_event_count": discovery.get("unlinked_boundary_event_count"),
        "official_event_count": len(index_rows),
        "official_index_coverage_status": coverage.get("coverage_status"),
        "next_stage": "COMPLETE_GATE_A_AFTER_FULL_OFFICIAL_INDEX_COVERAGE" if status == "PASS" else "BLOCKED_OFFICIAL_EVENT_INDEX_COVERAGE",
    }
    temp = (ROOT / OUTPUT).with_name(OUTPUT.name + ".tmp")
    temp.parent.mkdir(parents=True, exist_ok=True)
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(ROOT / OUTPUT)
    print(json.dumps({"status": status, "gate_a_status": payload["gate_a_status"],
                      "checks": payload["checks"], "receipt": OUTPUT.as_posix()}, ensure_ascii=False))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
