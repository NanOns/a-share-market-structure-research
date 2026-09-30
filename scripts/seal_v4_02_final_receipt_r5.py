from __future__ import annotations

"""Build R5 manifest, independently compare R4/R5 outputs, then atomically seal."""

import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.dated_security_alias import DatedSecurityAliasResolver
from workbench_analysis.special_price_phases import SpecialPhaseEventStore, SpecialPricePhase

REPORTS = ROOT / "reports/v4_02"
MANIFEST = REPORTS / "V4_02_FINAL_STAGING_MANIFEST_R5.json"
POSTCHECK = REPORTS / "V4_02_FINAL_INDEPENDENT_POSTCHECK_R5.json"
RECEIPT = REPORTS / "V4_02_FINAL_RECEIPT_R5.json"
ACCEPTED_HEAD = ROOT / "data/v4/V4_02_ACCEPTED_HEAD.json"
R4_HEAD_SNAPSHOT = REPORTS / "V4_02_R4_ACCEPTED_HEAD_SNAPSHOT_R5.json"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def component(path: Path, *, row_count: int | None = None) -> dict:
    item = {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha(path)}
    if row_count is not None:
        item["row_count"] = row_count
    return item


def code_scan() -> dict:
    files = list((ROOT / "src/workbench_analysis").rglob("*.py"))
    files += list((ROOT / "scripts").glob("build_v4_02*.py"))
    files.append(ROOT / "scripts/capture_special_phase_sources.py")
    forbidden = re.compile(r"(?:SZ|SH)\.\d{6}|SEC-[A-F0-9]{16,}")
    hits = []
    for path in sorted(set(files)):
        source = path.read_text(encoding="utf-8")
        if forbidden.search(source):
            hits.append(rel(path))
    return {"scanned_files": len(set(files)), "forbidden_identifier_hits": hits, "status": "PASS" if not hits else "FAIL"}


def input_paths() -> dict[str, Path]:
    return {
        "alias_contract": ROOT / "config/dated_security_alias_v1.json",
        "phase_event_contract": ROOT / "config/special_price_phase_event_v1.json",
        "phase_policy": ROOT / "config/special_price_phase_policy_v1.json",
        "source_capture_policy": ROOT / "config/special_phase_source_capture_v1.json",
        "alias_facts": ROOT / "data/v4/bootstrap/dated_security_alias_r7.jsonl",
        "phase_events": ROOT / "data/v4/bootstrap/special_price_phase_events_r4.jsonl",
        "source_requests": ROOT / "data/v4/bootstrap/special_phase_source_requests_r4.jsonl",
        "source_capture_receipt": ROOT / "reports/v4_02/V4_02_R5_SOURCE_CAPTURE_VERIFY.json",
        "replay_receipt": ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_REPLAY_R5.json",
        "test_receipt": ROOT / "reports/v4_02/V4_02_FINAL_R5_TEST_RECEIPT.json",
        "r4_final_receipt": ROOT / "reports/v4_02/V4_02_FINAL_RECEIPT_R4.json",
        "r4_postcheck": ROOT / "reports/v4_02/V4_02_FINAL_INDEPENDENT_POSTCHECK_R4.json",
        "r4_price": ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R4_20260927.jsonl.gz",
        "r5_price": ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R5_20260927.jsonl.gz",
        "r4_audit": ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R4.json",
        "r4_acceptance": ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_ACCEPTANCE_R4_20260927.json",
    }


def build_manifest(paths: dict[str, Path], code_commit: str, r4_head: dict, r4_head_sha: str) -> tuple[dict, dict]:
    alias_rows = [json.loads(line) for line in paths["alias_facts"].read_text(encoding="utf-8").splitlines() if line.strip()]
    event_store = SpecialPhaseEventStore.from_jsonl(paths["phase_events"])
    requests = [json.loads(line) for line in paths["source_requests"].read_text(encoding="utf-8").splitlines() if line.strip()]
    capture = json.loads(paths["source_capture_receipt"].read_text(encoding="utf-8"))
    replay = json.loads(paths["replay_receipt"].read_text(encoding="utf-8"))
    tests = json.loads(paths["test_receipt"].read_text(encoding="utf-8"))
    r4_post = json.loads(paths["r4_postcheck"].read_text(encoding="utf-8"))
    policies = json.loads(paths["phase_policy"].read_text(encoding="utf-8"))
    enum_values = {phase.value for phase in SpecialPricePhase}
    policy_values = {str(row.get("phase")) for row in policies.get("policies", [])}
    resolver = DatedSecurityAliasResolver(alias_rows)
    alias_rows_valid = len(alias_rows) == 2 and all(resolver.resolve_alias(alias_rows[0]["security_id"], day)
                            for day in (alias_rows[0]["effective_from"], alias_rows[1]["effective_from"]))
    scan = code_scan()
    checks = {
        "r4_history_preserved": r4_head.get("final_receipt_path", "").endswith("R4.json") and r4_head.get("status") == "PASS_WITH_BSE_SCOPE_DEGRADED",
        "alias_fact_contract_valid": alias_rows_valid,
        "phase_events_migrated": len(event_store.events) == 22 and len({x.event_id for x in event_store.events}) == 22,
        "all_phase_values_have_policy": enum_values.issubset(policy_values),
        "source_capture_manifest_verified_offline": capture.get("status") == "PASS" and capture.get("mode") == "verify-existing" and capture.get("verified_count") == 22,
        "source_requests_match_events": len(requests) == len(event_store.events) == 22,
        "replay_equivalent": replay.get("status") == "PASS" and replay.get("equivalence", {}).get("outcome_equivalent") is True,
        "special_phase_counts_preserved": replay.get("event_derived_phase_counts") == {"DELISTING_FIRST_DAY": 22, "DELISTING_PERIOD": 308}
            and replay.get("all_phase_counts") == r4_post.get("counts", {}).get("special_price_phases"),
        "unknown_inventory_preserved": replay.get("unknown_reason_inventory") == r4_post.get("counts", {}).get("unknown_reasons") and replay.get("r4_fail_closed_dispositions") == 31,
        "synthetic_and_r4_tests_pass": tests.get("result") == "PASS" and tests.get("failed") == 0 and tests.get("skipped") == 0,
        "genericity_scan_pass": scan["status"] == "PASS",
    }
    components = {name.upper(): component(path, row_count=22 if name in {"alias_facts", "phase_events", "source_requests"} else None)
                  for name, path in paths.items()}
    components["GENERICITY_CODE_SCAN"] = {"scanned_files": scan["scanned_files"], "forbidden_identifier_hits": scan["forbidden_identifier_hits"], "status": scan["status"]}
    task_doc = Path(r"D:\Users\lps\Desktop\V4_02_R4_GENERALIZATION_AUDIT_AND_R5_GENERIC_RUNTIME_CLOSURE_20260927.md")
    governing = Path(r"D:\Users\lps\Desktop\A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925_codex修改版.md")
    manifest = {
        "contract_id": "V4_02_WHOLE_STAGE_STAGING_MANIFEST_R5", "version": "5.0.0", "stage": "V4-02",
        "status": "STAGING_CANDIDATE_READY" if all(checks.values()) else "BLOCKED",
        "stage_contract": "SPECIAL_PRICE_PHASE_EVENT_V1 + SPECIAL_PRICE_PHASE_POLICY_V1 + DATED_SECURITY_ALIAS_V1; accepted R4 data frozen",
        "governing_upgrade_contract": {"contract_id": "DA-MSR-V4.2.2-CODEX-REV2",
            "path": "D:/Users/lps/Desktop/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925_codex修改版.md",
            "sha256": sha(governing)},
        "r5_task_document": {"path": "D:/Users/lps/Desktop/V4_02_R4_GENERALIZATION_AUDIT_AND_R5_GENERIC_RUNTIME_CLOSURE_20260927.md",
            "sha256": sha(task_doc)},
        "evidence": {"checks": checks, "r4_status": "DATA_CORRECTNESS_ACCEPTED; GENERIC_RUNTIME_NOT_EXTERNALLY_ACCEPTED",
            "r4_external_status": "BLOCKED_PENDING_R5_GENERALIZATION", "genericity_scan": scan,
            "source_capture_mode": "VERIFY_EXISTING_OFFLINE_ONLY", "new_notice_searches": 0, "new_source_recaptures": 0},
        "components": components, "required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"],
        "optional_degraded_boards": ["BSE"], "scope": {"source_cutoff": "2026-09-24", "bse": "OPTIONAL_DEGRADED_EXCLUDED"},
        "historical_R4_head": {"path": "data/v4/V4_02_ACCEPTED_HEAD.json", "sha256": r4_head_sha,
                                "status": r4_head.get("status"), "receipt_path": r4_head.get("final_receipt_path")},
        "implementation_commit": code_commit, "scanner_factor_trading_runs": 0, "tdx_root_write_count": 0,
        "next_stage": "INDEPENDENT_R5_POSTCHECK_AND_INTERNAL_FINAL_RECEIPT; V4-03_BLOCKED_PENDING_EXTERNAL_ACCEPTANCE",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    return manifest, checks


def independent_compare(paths: dict[str, Path], replay: dict, r4_post: dict) -> dict:
    r4_digest = hashlib.sha256()
    r5_digest = hashlib.sha256()
    r4_phases: Counter[str] = Counter()
    r5_phases: Counter[str] = Counter()
    r4_unknown: Counter[str] = Counter()
    r5_unknown: Counter[str] = Counter()
    mismatch = None
    count = 0
    with gzip.open(paths["r4_price"], "rt", encoding="utf-8") as old, gzip.open(paths["r5_price"], "rt", encoding="utf-8") as new:
        for left, right in zip(old, new, strict=True):
            old_row, new_row = json.loads(left), json.loads(right)
            if old_row != new_row and mismatch is None:
                mismatch = {"row": count, "security_id": old_row.get("security_id"), "trade_date": old_row.get("trade_date")}
            for row, digest, phases, unknown in ((old_row, r4_digest, r4_phases, r4_unknown), (new_row, r5_digest, r5_phases, r5_unknown)):
                encoded = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                digest.update(encoded.encode("utf-8"))
                phases[str(row.get("special_price_phase") or "REGULAR")] += 1
                if row.get("limit_status") == "UNKNOWN":
                    unknown[str(row.get("reason") or "<blank>")] += 1
            count += 1
    expected_phases = r4_post.get("counts", {}).get("special_price_phases", {})
    expected_unknown = r4_post.get("counts", {}).get("unknown_reasons", {})
    checks = {
        "row_count_unchanged": count == int(replay.get("row_count", -1)) == int(json.loads(paths["r4_acceptance"].read_text(encoding="utf-8"))["row_count"]),
        "row_payloads_identical": mismatch is None,
        "normalized_digest_matches_r4": r4_digest.hexdigest() == r5_digest.hexdigest() == replay.get("output", {}).get("normalized_output_sha256"),
        "phase_inventory_matches_r4": dict(r4_phases) == dict(r5_phases) == expected_phases,
        "unknown_reason_inventory_matches_r4": dict(r4_unknown) == dict(r5_unknown) == expected_unknown,
        "22_resolved_and_31_fail_closed_retained": replay.get("resolved_special_events") == 22 and replay.get("r4_fail_closed_dispositions") == 31,
    }
    return {"contract_id": "V4_02_FINAL_INDEPENDENT_POSTCHECK_R5", "version": "5.0.0",
            "status": "PASS" if all(checks.values()) else "BLOCKED", "checks": checks,
            "counts": {"price_rows": count, "resolved_special_events": replay.get("resolved_special_events"),
                       "fail_closed_dispositions": replay.get("r4_fail_closed_dispositions"),
                       "special_price_phases": dict(r5_phases), "unknown_reasons": dict(r5_unknown)},
            "r4_r5_first_mismatch": mismatch,
            "digests": {"r4_normalized": r4_digest.hexdigest(), "r5_normalized": r5_digest.hexdigest()},
            "inputs": {"r4_price_sha256": sha(paths["r4_price"]), "r5_price_sha256": sha(paths["r5_price"]),
                       "r5_replay_receipt_sha256": sha(paths["replay_receipt"])},
            "tdx_root_write_count": 0,
            "next_stage": "SEAL_R5_INTERNAL_RECEIPT; KEEP_V4-03_BLOCKED_PENDING_EXTERNAL_ACCEPTANCE",
            "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}


def main() -> int:
    paths = input_paths()
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise SystemExit("R5_SEAL_INPUT_MISSING:" + ",".join(missing))
    head_before = json.loads(ACCEPTED_HEAD.read_text(encoding="utf-8"))
    if head_before.get("status") != "PASS_WITH_BSE_SCOPE_DEGRADED" or not head_before.get("final_receipt_path", "").endswith("R4.json"):
        raise SystemExit("R5_PRIOR_R4_ACCEPTED_HEAD_NOT_PRESERVED")
    head_sha = sha(ACCEPTED_HEAD)
    atomic_json(R4_HEAD_SNAPSHOT, {"contract_id": "V4_02_R4_ACCEPTED_HEAD_SNAPSHOT_R5", "head": head_before,
                                  "sha256": head_sha, "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()})
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    test_receipt = json.loads(paths["test_receipt"].read_text(encoding="utf-8"))
    if test_receipt.get("execution_commit") != git:
        raise SystemExit("R5_TEST_EXECUTION_COMMIT_MISMATCH")
    manifest, checks = build_manifest(paths, git, head_before, head_sha)
    atomic_json(MANIFEST, manifest)
    replay = json.loads(paths["replay_receipt"].read_text(encoding="utf-8"))
    r4_post = json.loads(paths["r4_postcheck"].read_text(encoding="utf-8"))
    post = independent_compare(paths, replay, r4_post)
    atomic_json(POSTCHECK, post)
    all_pass = all(checks.values()) and post["status"] == "PASS"
    receipt = {
        "contract_id": "V4_02_FINAL_ACCEPTANCE_RECEIPT_R5", "version": "5.0.0",
        "stage": "V4-02 FINAL GENERIC RUNTIME CLOSURE / R5",
        "status": "PASS_WITH_BSE_SCOPE_DEGRADED" if all_pass else "BLOCKED",
        "external_acceptance": "PENDING_R5_GENERALIZATION_REVIEW" if all_pass else "NOT_READY",
        "v4_03_entry": "BLOCKED_PENDING_EXTERNAL_ACCEPTANCE",
        "blockers": [] if all_pass else ["R5_MANIFEST_OR_INDEPENDENT_POSTCHECK_GATE_FAILED"],
        "checks": {**checks, "independent_r5_postcheck_pass": post["status"] == "PASS",
                   "r4_preserved_as_data_correctness_accepted": True,
                   "generic_runtime_external_acceptance_not_claimed": True,
                   "v4_03_remains_blocked": True},
        "evidence": {"manifest": {"path": rel(MANIFEST), "sha256": sha(MANIFEST)},
                     "independent_postcheck": {"path": rel(POSTCHECK), "sha256": sha(POSTCHECK), "status": post["status"]},
                     "r5_tests": {"path": rel(paths["test_receipt"]), "sha256": sha(paths["test_receipt"]),
                                  "result": test_receipt.get("result"), "passed": test_receipt.get("passed")},
                     "r5_replay": {"path": rel(paths["replay_receipt"]), "sha256": sha(paths["replay_receipt"]),
                                   "status": replay.get("status")},
                     "preserved_r4_receipt": {"path": rel(paths["r4_final_receipt"]), "sha256": sha(paths["r4_final_receipt"]),
                                              "historical_status": "DATA_CORRECTNESS_ACCEPTED; GENERIC_RUNTIME_NOT_EXTERNALLY_ACCEPTED"}},
        "scope": {"required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"], "optional_degraded": ["BSE"],
                  "source_cutoff": "2026-09-24"},
        "tdx_root_write_count": 0, "scanner_factor_trading_runs": 0,
        "next_stage": "WAIT_FOR_EXTERNAL_R5_ACCEPTANCE; DO_NOT_START_V4-03",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    atomic_json(RECEIPT, receipt)
    if all_pass:
        accepted = {"contract_id": "V4_02_ACCEPTED_HEAD_V1", "stage": "V4-02", "status": "PASS_WITH_BSE_SCOPE_DEGRADED",
                    "accepted_at_utc": receipt["observed_at_utc"], "source_cutoff": "2026-09-24",
                    "final_receipt_path": rel(RECEIPT), "final_receipt_sha256": sha(RECEIPT),
                    "manifest_path": rel(MANIFEST), "manifest_sha256": sha(MANIFEST),
                    "supersedes_final_receipt_path": head_before.get("final_receipt_path"),
                    "supersedes_final_receipt_sha256": head_before.get("final_receipt_sha256"),
                    "history": {"r1_revoked": True, "r3_blocked_receipt_retained": True, "r4_data_correctness_accepted": True,
                                "r4_generic_runtime_not_externally_accepted": True, "r4_head_snapshot_path": rel(R4_HEAD_SNAPSHOT)},
                    "v4_03_entry": "BLOCKED_PENDING_EXTERNAL_ACCEPTANCE"}
        atomic_json(ACCEPTED_HEAD, accepted)
    print(json.dumps({"manifest": manifest["status"], "postcheck": post["status"], "receipt": receipt["status"],
                      "accepted_head_updated": all_pass, "v4_03": receipt["v4_03_entry"]}, ensure_ascii=False))
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
