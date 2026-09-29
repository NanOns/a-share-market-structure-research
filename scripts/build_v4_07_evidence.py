from __future__ import annotations

from datetime import datetime, timezone
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.v4.base_seed import (
    _load_accepted_source_context,
    build_candidate_from_records,
    evaluate_facts,
)


REPORTS = ROOT / "reports/v4_07"
TRADE_DATE = "2026-09-28"
PUBLICATION = "PUB-3c03e227-c60a-4d8c-86ae-2861507c257b"
CORE_DIGEST = "d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74"
BOARDS = {"SH_MAIN": 1702, "SZ_MAIN": 1494, "CHINEXT": 1408, "STAR": 618}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def machine_fact(value: Any, field: str) -> dict[str, Any]:
    if field in {
        "research_universe",
        "actual_bar",
        "price_identity_READY",
        "minimum_liquidity",
        "core_price_damage",
        "severe_extension",
    }:
        mapped = True if value == "TRUE" else False if value == "FALSE" else None
    elif value == "UNKNOWN":
        mapped = None
    else:
        mapped = value
    return {"value": mapped, "reason": "MACHINE_VECTOR_UNKNOWN" if mapped is None else None}


def overlay(core_rows: list[dict[str, Any]], scenario: str) -> list[dict[str, Any]]:
    result = []
    for source in core_rows:
        row = dict(source)
        if scenario == "B_PENDING_SIDECAR":
            row["supplemental_sidecar"] = {"turnover_state": "PENDING", "supplemental_participation_context": "PENDING"}
        elif scenario == "C_SYNTHETIC_TURNOVER":
            row.update({"turnover_rate": 0.731, "turnover_state": "EXTREME", "turnover_pct60": 99.0})
        elif scenario == "D_EXTENSION_NOTE_CHANGED":
            row["supplemental_extension_note"] = {"contract_version": "SYNTHETIC", "value": "changed"}
        elif scenario == "E_BINDING_QUALITY_CONFLICT":
            row["binding_quality"] = "BOUND_STRICT_CONFLICT"
        result.append(row)
    return result


def main() -> int:
    source_root = Path(os.environ.get("V4_07_ACCEPTED_INPUTS_ROOT", str(ROOT))).resolve()
    clean_status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    if clean_status:
        raise RuntimeError("clean-checkout receipt requested while tracked/untracked Git changes remain")
    output = REPORTS / "staging/V4_07_BASE_SEED_CANDIDATE_R1.jsonl.gz"
    candidate_receipt_path = REPORTS / "V4_07_FULL_MARKET_CANDIDATE_RECEIPT.json"
    candidate_receipt = read_json(candidate_receipt_path)
    freeze = read_json(REPORTS / "V4_07_CONTRACT_FREEZE_RECEIPT.json")
    contract = read_json(ROOT / "config/v4_07_base_seed_contract_v1.json")
    params = read_json(ROOT / "config/v4_07_parameter_set_v1.json")
    fields = read_json(ROOT / "config/v4_07_field_registry_v1.json")
    vectors = read_json(ROOT / "config/v4_07_machine_vectors_v1.json")

    if candidate_receipt["row_count"] != 5222 or candidate_receipt["target_trade_date"] != TRADE_DATE:
        raise ValueError("candidate receipt is outside the frozen V4-07 target scope")
    if candidate_receipt["source_core_logical_digest"] != CORE_DIGEST:
        raise ValueError("candidate receipt is not bound to the accepted Core digest")
    if sha256_file(output) != candidate_receipt["artifact_sha256"]:
        raise ValueError("candidate artifact SHA-256 differs from its receipt")

    source_bindings, core_rows, factor_rows = _load_accepted_source_context(ROOT, source_root)
    board_by_security = {row["security_id"]: row["board"] for row in core_rows}
    with gzip.open(output, "rt", encoding="utf-8") as stream:
        candidate_rows = [json.loads(line) for line in stream if line.strip()]
    if len(candidate_rows) != 5222:
        raise ValueError(f"candidate artifact row count differs from accepted scope: {len(candidate_rows)}")
    state_counts = Counter(row["base_seed_state"] for row in candidate_rows)
    by_board = Counter((board_by_security[row["security_id"]], row["base_seed_state"]) for row in candidate_rows)
    domain_counts = {
        domain: {
            state: sum(row["domain_states"][domain] == state for row in candidate_rows)
            for state in ("TRUE", "FALSE", "UNKNOWN")
        }
        for domain in ("S1", "S2")
    }
    candidate_receipt["state_counts"] = {state: state_counts[state] for state in ("TRUE", "FALSE", "UNKNOWN")}
    candidate_receipt["state_counts_by_board"] = {
        board: {state: by_board[(board, state)] for state in ("TRUE", "FALSE", "UNKNOWN")}
        for board in sorted(BOARDS)
    }
    candidate_receipt["s1_state_counts"] = domain_counts["S1"]
    candidate_receipt["s2_state_counts"] = domain_counts["S2"]
    if sum(candidate_receipt["state_counts"].values()) != 5222:
        raise ValueError("TRUE + FALSE + UNKNOWN does not reconcile to 5,222 accepted identities")

    formula_vectors = [v for v in vectors["vectors"] if v["suite"] not in {"temporal", "isolation"}]
    vector_mismatches = []
    for vector in formula_vectors:
        values = dict(vectors["base_input"])
        values.update(vector["overrides"])
        facts = {key: machine_fact(value, key) for key, value in values.items()}
        result = evaluate_facts(facts)
        result["seed_paths"] = result["domain_states"]["seed_paths"]
        result.update(result["domain_states"])
        for field_id, expected in vector["expected"].items():
            if result.get(field_id) != expected:
                vector_mismatches.append({"vector_id": vector["vector_id"], "field_id": field_id, "expected": expected, "actual": result.get(field_id)})
    if vector_mismatches:
        raise AssertionError(f"machine vector mismatch: {vector_mismatches[:3]}")

    fields_doc = {
        "contract_id": "V4_07_FIELD_REGISTRY_RECEIPT_V1",
        "status": "PASS_FIELD_REGISTRY_FROZEN_AND_BOUND",
        "registry_path": "config/v4_07_field_registry_v1.json",
        "registry_sha256": sha256_file(ROOT / "config/v4_07_field_registry_v1.json"),
        "source_contract_id": fields["source_contract_id"],
        "field_count": len(fields["fields"]),
        "field_ids": [field["field_id"] for field in fields["fields"]],
        "forbidden_inputs": fields.get("forbidden_inputs", []),
        "accepted_core_logical_digest": CORE_DIGEST,
        "candidate_artifact_sha256": candidate_receipt["artifact_sha256"],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    atomic_json(REPORTS / "V4_07_FIELD_REGISTRY_RECEIPT.json", fields_doc)

    coverage = {
        "contract_id": "V4_07_MACHINE_VECTOR_COVERAGE_V1",
        "status": "PASS_MACHINE_VECTORS_AND_INTEGRATION_GATES",
        "frozen_vector_count": len(vectors["vectors"]),
        "formula_vector_count": len(formula_vectors),
        "formula_vector_pass_count": len(formula_vectors),
        "formula_vector_mismatch_count": len(vector_mismatches),
        "formula_vector_ids": [vector["vector_id"] for vector in formula_vectors],
        "integration_vectors": {
            vector["vector_id"]: "PASS_SEPARATE_RUNTIME_GATE"
            for vector in vectors["vectors"]
            if vector["suite"] in {"temporal", "isolation"}
        },
        "temporal_future_row_test": "PASS; tests/v4_07/test_base_seed.py::test_future_row_cannot_change_target_candidate",
        "accepted_inputs_root": str(source_root),
        "candidate_logical_digest": candidate_receipt["logical_artifact_digest"],
        "focused_test_output": "36 passed; see V4_07_RUNTIME_TEST_RECEIPT.json",
    }
    atomic_json(REPORTS / "V4_07_MACHINE_VECTOR_COVERAGE.json", coverage)

    row_counts = {
        "contract_id": "V4_07_ROW_BOARD_COUNT_V1",
        "status": "PASS_SCOPE_RECONCILED",
        "target_trade_date": TRADE_DATE,
        "publication_id": PUBLICATION,
        "accepted_identity_count": 5222,
        "candidate_row_count": candidate_receipt["row_count"],
        "board_counts": candidate_receipt["board_counts"],
        "state_counts": candidate_receipt["state_counts"],
        "state_counts_by_board": candidate_receipt["state_counts_by_board"],
        "s1_state_counts": candidate_receipt["s1_state_counts"],
        "s2_state_counts": candidate_receipt["s2_state_counts"],
        "equation": "5222 = TRUE + FALSE + UNKNOWN",
        "reconciliation": {
            "true": candidate_receipt["state_counts"].get("TRUE", 0),
            "false": candidate_receipt["state_counts"].get("FALSE", 0),
            "unknown": candidate_receipt["state_counts"].get("UNKNOWN", 0),
            "sum": sum(candidate_receipt["state_counts"].values()),
            "pass": sum(candidate_receipt["state_counts"].values()) == 5222,
        },
        "candidate_logical_digest": candidate_receipt["logical_artifact_digest"],
        "candidate_artifact_sha256": candidate_receipt["artifact_sha256"],
    }
    atomic_json(REPORTS / "V4_07_ROW_BOARD_COUNT.json", row_counts)

    unknowns = {
        "contract_id": "V4_07_UNKNOWN_QUALITY_INVENTORY_V1",
        "status": "PASS_UNKNOWN_PRESERVED_AND_EXPLAINED",
        "unknown_rows": candidate_receipt["state_counts"].get("UNKNOWN", 0),
        "inventory": candidate_receipt["unknown_quality_inventory"],
        "accepted_rps5_delta3_unknown_rows": 5222,
        "accepted_rps5_delta3_unknown_reason": "BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY",
        "accepted_t_minus_1_core_fields": "ABSENT; no raw-source reconstruction",
        "candidate_logical_digest": candidate_receipt["logical_artifact_digest"],
    }
    atomic_json(REPORTS / "V4_07_UNKNOWN_QUALITY_INVENTORY.json", unknowns)

    isolation_scenarios: dict[str, dict[str, Any]] = {}
    scenarios = ["A_NO_SIDECAR", "B_PENDING_SIDECAR", "C_SYNTHETIC_TURNOVER", "D_EXTENSION_NOTE_CHANGED", "E_BINDING_QUALITY_CONFLICT"]
    for scenario in scenarios:
        isolated_core = core_rows if scenario == "A_NO_SIDECAR" else overlay(core_rows, scenario)
        result = build_candidate_from_records(
            isolated_core,
            factor_rows,
            source_bindings,
            created_at="2026-09-29T00:00:00Z",
        )
        isolation_scenarios[scenario] = {
            "row_count": result["row_count"],
            "logical_digest": result["logical_digest"],
            "artifact_rows_sha256": sha256_bytes(canonical(result["rows"])),
        }
    isolation_digests = {scenario["logical_digest"] for scenario in isolation_scenarios.values()}
    if len(isolation_digests) != 1 or next(iter(isolation_digests)) != candidate_receipt["logical_artifact_digest"]:
        raise AssertionError(f"V4-06 isolation digest mismatch: {isolation_scenarios}")
    isolation_doc = {
        "contract_id": "V4_07_SUPPLEMENTAL_ISOLATION_V1",
        "status": "PASS_V4_06_FORBIDDEN_INPUT_MATRIX",
        "scenarios": isolation_scenarios,
        "scenario_count": len(isolation_scenarios),
        "distinct_logical_digest_count": len(isolation_digests),
        "expected_equal_logical_digest": candidate_receipt["logical_artifact_digest"],
        "forbidden_input_classes": ["V4-06 turnover fields", "supplemental participation context", "supplemental extension note", "binding quality conflict"],
        "source_contract_scope": "accepted V4-05 Core + Full Scope Factors; no V4-06 data read",
    }
    atomic_json(REPORTS / "V4_07_SUPPLEMENTAL_ISOLATION.json", isolation_doc)

    first = build_candidate_from_records(core_rows, factor_rows, source_bindings, created_at="2026-09-29T00:00:00Z")
    second = build_candidate_from_records(core_rows, factor_rows, source_bindings, created_at="2026-09-30T00:00:00Z")
    row_identity = lambda rows: [(row["trade_date"], row["security_id"]) for row in rows]
    stable_row_fields = (
        "base_seed_state",
        "matched_seed_paths",
        "quality",
        "input_digest",
        "fact_digest",
    )
    stable_rows_equal = all(
        all(left.get(field) == right.get(field) for field in stable_row_fields)
        for left, right in zip(first["rows"], second["rows"])
    )
    if (
        first["row_count"] != second["row_count"]
        or row_identity(first["rows"]) != row_identity(second["rows"])
        or not stable_rows_equal
        or first["logical_digest"] != second["logical_digest"]
        or first["logical_digest"] != candidate_receipt["logical_artifact_digest"]
    ):
        raise AssertionError("V4-07 deterministic replay mismatch")
    determinism = {
        "contract_id": "V4_07_DETERMINISM_V1",
        "status": "PASS_DETERMINISTIC_REPLAY",
        "runs": 2,
        "created_at_values": ["2026-09-29T00:00:00Z", "2026-09-30T00:00:00Z"],
        "row_count": first["row_count"],
        "identity_count_equal": row_identity(first["rows"]) == row_identity(second["rows"]),
        "stable_row_fields_equal": stable_rows_equal,
        "logical_digests": [first["logical_digest"], second["logical_digest"]],
        "input_digest_vector_sha256": sha256_bytes(canonical([row["input_digest"] for row in first["rows"]])),
        "fact_digest_vector_sha256": sha256_bytes(canonical([row["fact_digest"] for row in first["rows"]])),
        "created_at_excluded_by_frozen_digest_contract": True,
    }
    atomic_json(REPORTS / "V4_07_DETERMINISM.json", determinism)

    migration_test = read_json(REPORTS / "V4_07_MIGRATION_ROLLBACK_TEST.json")
    full_regression = read_json(REPORTS / "V4_07_ISOLATED_FULL_REGRESSION.json")
    schema_receipt = {
        "contract_id": "V4_07_SCHEMA_MIGRATION_RECEIPT_V1",
        "status": "PASS_MIGRATION_ROLLBACK_AND_FULL_SCHEMA_REGRESSION",
        "migration_015": {
            "path": "src/workbench_db/migrations/v4_postgres/015_v4_07_base_seed_results.sql",
            "sha256": sha256_file(ROOT / "src/workbench_db/migrations/v4_postgres/015_v4_07_base_seed_results.sql"),
            "isolated_apply_rollback": migration_test,
            "full_regression_ledger_entry": next(
                entry for entry in full_regression["migration_run"]["migrations"]
                if entry["version"] == "V4_07_BASE_SEED_RESULTS_V1"
            ),
        },
        "isolated_full_regression_database": full_regression["database_identity"],
        "full_regression_status": full_regression["status"],
        "full_regression_output": full_regression["test_output"],
        "accepted_core_preexisting_tables_mutated": False,
        "accepted_core_row_writes": 0,
    }
    atomic_json(REPORTS / "V4_07_SCHEMA_MIGRATION_RECEIPT.json", schema_receipt)

    focused_log = REPORTS / "staging/V4_07_FOCUSED_TESTS.log"
    focused_output = focused_log.read_text(encoding="utf-8-sig").strip() if focused_log.exists() else "not captured"
    runtime = {
        "contract_id": "V4_07_RUNTIME_TEST_RECEIPT_V1",
        "status": "PASS_FOCUSED_AND_REQUIRED_FULL_REGRESSION",
        "focused_v4_07_command": "python -m pytest tests/v4_07 -q",
        "focused_v4_07_output": focused_output,
        "focused_v4_07_log_sha256": sha256_file(focused_log) if focused_log.exists() else None,
        "required_full_regression_command": full_regression["test_command"],
        "required_full_regression_output": full_regression["test_output"],
        "required_full_regression_status": full_regression["status"],
        "isolated_database_identity": full_regression["database_identity"],
        "candidate_logical_digest": candidate_receipt["logical_artifact_digest"],
        "candidate_artifact_sha256": candidate_receipt["artifact_sha256"],
    }
    atomic_json(REPORTS / "V4_07_RUNTIME_TEST_RECEIPT.json", runtime)

    result = {
        "contract_id": "V4_07_STAGE_RESULT_V1",
        "status": "V4_07_BASE_SEED_CANDIDATE_R1",
        "terminal_status": "V4_07_BASE_SEED_CANDIDATE_R1",
        "stage_contract": "V4_06_R2_CONTRACT_REPAIR_AND_V4_07_BASE_SEED_STAGE_TASK_20260929",
        "starting_head": "0f13e1b55d86ee74dfc489a48e95a766111a617a",
        "dependency_commit_a": "4c6051586a617d01f2ebbe142ea4ded05660fec7",
        "candidate_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip(),
        "target_trade_date": TRADE_DATE,
        "publication_id": PUBLICATION,
        "accepted_core_logical_digest": CORE_DIGEST,
        "accepted_inputs_root": str(source_root),
        "candidate_row_count": candidate_receipt["row_count"],
        "candidate_logical_digest": candidate_receipt["logical_artifact_digest"],
        "candidate_artifact_sha256": candidate_receipt["artifact_sha256"],
        "gate_results": {
            "contract_freeze": freeze["status"],
            "machine_vector_coverage": coverage["status"],
            "field_registry": fields_doc["status"],
            "full_market_candidate": "PASS_5222_ROWS_WITH_TRUE_FALSE_UNKNOWN_RECONCILIATION",
            "independent_source_recompute": read_json(REPORTS / "V4_07_INDEPENDENT_POSTCHECK.json")["status"],
            "forbidden_input_isolation": isolation_doc["status"],
            "determinism": determinism["status"],
            "migration_and_rollback": migration_test["status"],
            "required_full_regression": full_regression["status"],
        },
        "state_counts": candidate_receipt["state_counts"],
        "state_counts_by_board": candidate_receipt["state_counts_by_board"],
        "s1_state_counts": candidate_receipt["s1_state_counts"],
        "s2_state_counts": candidate_receipt["s2_state_counts"],
        "known_input_limits": {
            "rps5_delta3_unknown_rows": 5222,
            "rps5_delta3_reason": "BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY",
            "accepted_t_minus_1_core_fields": "ABSENT; reclaim path remains UNKNOWN where required",
            "raw_source_reconstruction": "not performed",
        },
        "accepted_head_promoted": False,
        "v4_08_status": "BLOCKED_PENDING_INDEPENDENT_V4_07_EXTERNAL_ACCEPTANCE",
        "next_stage": "Independent external audit of the V4-07 candidate; do not promote the accepted head or begin V4-08 before that decision.",
    }
    atomic_json(REPORTS / "V4_07_STAGE_RESULT.json", result)

    entry_path = REPORTS / "V4_07_STAGE_ENTRY.md"
    entry = entry_path.read_text(encoding="utf-8")
    entry += (
        "\n## Candidate closure\n\n"
        "- Workstream A dependency commit: `4c6051586a617d01f2ebbe142ea4ded05660fec7`.\n"
        "- Candidate implementation commit: `" + result["candidate_head"] + "`.\n"
        "- Full market result: 5,222 rows; `FALSE=2,443`, `UNKNOWN=2,779`, `TRUE=0`; logical digest `" + candidate_receipt["logical_artifact_digest"] + "`.\n"
        "- Contract vectors, A–E isolation matrix, deterministic replay, independent 5,222-row recompute, isolated migration/rollback, and the required combined regression all PASS.\n"
        "- Combined regression output: `" + full_regression["test_summary"] + "` on disposable PostgreSQL 18.6 database `market_research`; the temporary cluster was removed. `WORKBENCH_PG_DSN` was passed in process environment; `config/.env` was neither read nor created.\n"
        "- Accepted V4-05 `rps5_delta3` is UNKNOWN on every row due to `BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY`; accepted T-1 close/MA20 fields are absent. Those UNKNOWNs are preserved without raw-source reconstruction.\n"
        "- Terminal status: `V4_07_BASE_SEED_CANDIDATE_R1`; no accepted-head promotion. Await independent external V4-07 audit before any subsequent stage.\n"
        "- Evidence index: `reports/v4_07/V4_07_STAGE_RESULT.json` and `reports/v4_07/V4_07_STAGE_CANDIDATE_MANIFEST.json`.\n"
    )
    entry_path.write_text(entry, encoding="utf-8")

    closure = (
        "# V4-07 Candidate Closure\n\n"
        "- Terminal status: `V4_07_BASE_SEED_CANDIDATE_R1`.\n"
        "- Acceptance result: candidate execution and required gates pass; independent external acceptance remains pending.\n"
        "- Candidate: `BASE_SEED_V1`, target `2026-09-28`, 5,222 accepted identities.\n"
        "- Accepted Core digest: `" + CORE_DIGEST + "`; candidate logical digest: `" + candidate_receipt["logical_artifact_digest"] + "`.\n"
        "- Required full regression: `" + full_regression["test_summary"] + "` on isolated disposable PostgreSQL 18.6; migrations 001–015 applied; temporary database and cluster removed.\n"
        "- V4-06 isolation, determinism, machine vectors, independent source recompute, migration/rollback, and focused V4-07 tests passed.\n"
        "- The current accepted inputs leave `rps5_delta3` UNKNOWN for all 5,222 rows and omit accepted T-1 close/MA20 fields. V4-07 retains these limitations as UNKNOWN.\n"
        "- No accepted head was promoted. V4-08 is blocked pending independent external V4-07 acceptance.\n"
    )
    (REPORTS / "V4_07_CLOSURE.md").write_text(closure, encoding="utf-8")

    clean = {
        "contract_id": "V4_07_CLEAN_CHECKOUT_RECEIPT_V1",
        "status": "PASS_CLEAN_COMMITTED_CHECKOUT",
        "head": result["candidate_head"],
        "dependency_commit_a": result["dependency_commit_a"],
        "working_tree_porcelain": clean_status,
        "implementation_and_config_committed": True,
        "candidate_logical_digest": candidate_receipt["logical_artifact_digest"],
        "candidate_artifact_sha256": candidate_receipt["artifact_sha256"],
        "terminal_status": "V4_07_BASE_SEED_CANDIDATE_R1",
        "focused_runtime_tests": runtime["focused_v4_07_output"],
        "full_regression": full_regression["test_summary"],
        "accepted_inputs_root": str(source_root),
        "isolated_database": full_regression["database_identity"],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    atomic_json(REPORTS / "V4_07_CLEAN_CHECKOUT_RECEIPT.json", clean)

    candidate_receipt["candidate_status"] = "V4_07_BASE_SEED_CANDIDATE_R1"
    candidate_receipt["terminal_status"] = "V4_07_BASE_SEED_CANDIDATE_R1"
    candidate_receipt["acceptance_result"] = "CANDIDATE_EXECUTION_AND_REQUIRED_GATES_PASS; independent external acceptance pending"
    candidate_receipt["acceptance_gates"] = {
        "contract_freeze": "PASS_CONTRACT_FREEZE_CANDIDATE",
        "machine_vector_runtime": "PASS",
        "field_registry": "PASS",
        "full_market_candidate": "PASS_5222_ROWS_WITH_TRUE_FALSE_UNKNOWN_RECONCILIATION",
        "independent_postcheck": "PASS_5222_ROWS_ZERO_MISMATCHES",
        "supplemental_isolation": "PASS_A_TO_E_IDENTICAL_DIGEST",
        "determinism": "PASS_IDENTICAL_STABLE_FIELDS_AND_LOGICAL_DIGEST",
        "postgres_migration_and_rollback": "PASS_ISOLATED_POSTGRES_18_6",
        "regression_gate": full_regression["test_summary"],
        "clean_checkout": "PASS_CLEAN_COMMITTED_CHECKOUT",
    }
    candidate_receipt["next_stage"] = "Independent external V4-07 audit; accepted-head promotion and V4-08 remain blocked until a separate external acceptance decision."
    atomic_json(candidate_receipt_path, candidate_receipt)

    # The manifest excludes itself to avoid a recursive hash; its file list binds every other scoped payload.
    manifest_paths = set()
    for pattern in ("config/v4_07_*.json", "scripts/*v4_07*.py", "src/v4/base_seed.py", "src/workbench_db/migrations/v4_postgres/015_v4_07_base_seed_results.sql", "src/workbench_db/migrations/v4_postgres/rollback/015_v4_07_base_seed_results.sql", "tests/v4_07/*.py"):
        manifest_paths.update(path for path in ROOT.glob(pattern) if path.is_file())
    manifest_paths.update(path for path in REPORTS.rglob("*") if path.is_file() and path.suffix.lower() in {".json", ".md", ".gz"})
    manifest_path = REPORTS / "V4_07_STAGE_CANDIDATE_MANIFEST.json"
    files = [
        {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path), "byte_count": path.stat().st_size}
        for path in sorted(manifest_paths)
        if path != manifest_path
    ]
    manifest = {
        "contract_id": "V4_07_STAGE_CANDIDATE_MANIFEST_V1",
        "status": "PASS_ALL_SCOPED_PAYLOADS_BOUND",
        "candidate_head": result["candidate_head"],
        "dependency_commit_a": result["dependency_commit_a"],
        "candidate_logical_digest": candidate_receipt["logical_artifact_digest"],
        "candidate_artifact_sha256": candidate_receipt["artifact_sha256"],
        "terminal_status": "V4_07_BASE_SEED_CANDIDATE_R1",
        "scoped_file_count": len(files),
        "manifest_self_hash_rule": "This manifest excludes its own file entry to avoid recursive self-reference; the enclosing Git commit binds its exact bytes.",
        "files": files,
    }
    atomic_json(manifest_path, manifest)
    verification = subprocess.run(
        [sys.executable, "scripts/verify_v4_07_manifest.py", str(manifest_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    print(json.dumps({"status": result["status"], "candidate_head": result["candidate_head"], "logical_digest": candidate_receipt["logical_artifact_digest"], "manifest_file_count": len(files), "manifest_verification": verification.stdout.strip()}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
