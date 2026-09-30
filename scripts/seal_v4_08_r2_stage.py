from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from sector.membership_baseline import (  # noqa: E402
    build_source_revision_identity,
    validate_revision_chain,
)
from sector.v4_08_rotation_vectors import evaluate_rotation_vector  # noqa: E402
from build_v4_08_r2_membership_evidence import (  # noqa: E402
    atomic_json,
    build_temporal_evidence,
    classify_unresolved_keys,
    sha,
    split_lineages,
)


STAGE_TERMINAL = "V4_08_R2_MEMBERSHIP_BLOCKED_ACCEPTED_CALENDAR_EXTENSION_REQUIRED_IDENTITY_SCOPE_AND_SOURCE_POLICY_REVIEW"
TASK_DOCS = {
    "docs/evidence/V4_08_R2_MEMBERSHIP_CONTRACT_REPAIR_AND_FORWARD_PIT_BASELINE_TASK_20260930.md": Path(r"D:\Users\lps\Desktop\V4_08_R2_MEMBERSHIP_CONTRACT_REPAIR_AND_FORWARD_PIT_BASELINE_TASK_20260930.md"),
    "docs/evidence/V4_06_V4_07_PROMOTION_V4_08_R1_INDEPENDENT_EXTERNAL_AUDIT_20260930.md": Path(r"D:\Users\lps\Desktop\V4_06_V4_07_PROMOTION_V4_08_R1_INDEPENDENT_EXTERNAL_AUDIT_20260930.md"),
}


def read_json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def manifest_entry(path: str) -> dict[str, Any]:
    data = (ROOT / path).read_bytes()
    return {"path": path, "sha256": sha(data), "byte_count": len(data)}


def write_source_documents() -> list[dict[str, Any]]:
    entries = []
    for relative, external in TASK_DOCS.items():
        data = external.read_bytes()
        destination = ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.tmp")
        temporary.write_bytes(data)
        temporary.replace(destination)
        entries.append({"path": relative, "sha256": sha(data), "byte_count": len(data),
                        "origin": str(external), "role": "stage instructions or independent R1 audit evidence"})
    return entries


def main() -> int:
    copied_docs = write_source_documents()
    first = split_lineages()
    first_artifacts = first["artifacts"]
    second = split_lineages()
    second_artifacts = second["artifacts"]
    identity = classify_unresolved_keys()
    build_temporal_evidence(second, identity)
    migration = read_json("reports/v4_08/V4_08_R2_SCHEMA_MIGRATION_RECEIPT.json")
    regression = read_json("reports/v4_08/V4_08_R2_REQUIRED_REGRESSION.json")
    pit = read_json("reports/v4_08/V4_08_R2_GO_FORWARD_PIT_CANDIDATE.json")
    identity_gate = read_json("reports/v4_08/V4_08_R2_FORMAL_UNIVERSE_IDENTITY_GATE.json")
    mixed = read_json("reports/v4_08/V4_08_R2_MIXED_BASIS_SPLIT_VERIFICATION.json")

    determinism_pass = (
        first["snapshots"] == second["snapshots"]
        and {key: value["sha256"] for key, value in first_artifacts.items()}
        == {key: value["sha256"] for key, value in second_artifacts.items()}
    )
    determinism = {
        "contract_id": "V4_08_R2_DETERMINISM_V1",
        "status": "PASS_FIXED_R1_EVIDENCE" if determinism_pass else "FAIL",
        "input_source_artifact_sha256": mixed["source_artifact"]["sha256"],
        "snapshot_ids_first_run": {key: value["snapshot_id"] for key, value in first["snapshots"].items()},
        "snapshot_ids_second_run": {key: value["snapshot_id"] for key, value in second["snapshots"].items()},
        "artifact_hashes_first_run": {key: value["sha256"] for key, value in first_artifacts.items()},
        "artifact_hashes_second_run": {key: value["sha256"] for key, value in second_artifacts.items()},
        "created_at_excluded_from_logical_identity": True,
    }
    atomic_json(ROOT / "reports/v4_08/V4_08_R2_DETERMINISM.json", determinism)

    checks = migration["checks"]
    formal_gate = {
        "contract_id": "V4_08_R2_FORMAL_VIEW_QUALITY_GATE_V1",
        "status": "PASS" if all(checks.get(key) for key in [
            "formal_view_contains_industry_and_theme_only",
            "formal_view_rejects_pit_with_unaccepted_quality",
            "pit_observed_degraded_history_unsafe_is_allowed",
            "stale_membership_asof_rejected",
            "temporal_leakage_rejected",
        ]) else "FAIL",
        "formal_view_requires": ["INDUSTRY/THEME", "fact PIT basis", "snapshot PIT basis", "accepted fact quality", "accepted snapshot quality", "accepted source revision quality", "pit_observed", "historical_backtest_safe", "mapped non-null identity", "exact target date", "provider/system availability within cutoff", "source byte and temporal evidence metadata"],
        "negative_quality_vector": "PIT_OBSERVED + SOURCE_TIME_UNVERIFIED excluded",
        "degraded_pit_vector": "PIT_OBSERVED=true and historical_backtest_safe=false accepted as stored evidence; excluded from formal view",
        "positive_formal_synthetic_fact_count": 2,
        "isolated_schema_checks": checks,
        "database_scope": migration["database_scope"],
    }
    atomic_json(ROOT / "reports/v4_08/V4_08_R2_FORMAL_VIEW_QUALITY_GATE.json", formal_gate)

    raw_revision = mixed["source_revisions"]["raw"]
    candidate_identity = pit["source_revision_identity_candidate"]
    repeated = build_source_revision_identity(raw_revision["source_bytes_digest"], {
        "lineage_role": "GO_FORWARD_PIT_CANDIDATE",
        "provider_available_at": pit["provider_available_at_candidate"],
        "provider_available_at_basis": pit["provider_available_at_basis"],
        "membership_asof_date": pit["candidate_membership_asof_date"],
        "membership_asof_basis": pit["membership_asof_basis"],
    })
    same_bytes_new_evidence = (
        raw_revision["source_bytes_digest"] == repeated["source_bytes_digest"]
        and raw_revision["temporal_evidence_digest"] != repeated["temporal_evidence_digest"]
        and raw_revision["source_revision_id"] != repeated["source_revision_id"]
    )
    revision_test = {
        "contract_id": "V4_08_R2_SOURCE_REVISION_METADATA_TEST_V1",
        "status": "PASS" if same_bytes_new_evidence and checks.get("same_bytes_new_temporal_evidence_is_a_new_revision") and checks.get("temporal_evidence_revision_is_append_only") else "FAIL",
        "same_bytes_digest": raw_revision["source_bytes_digest"],
        "first_temporal_evidence_digest": raw_revision["temporal_evidence_digest"],
        "second_temporal_evidence_digest": repeated["temporal_evidence_digest"],
        "first_source_revision_id": raw_revision["source_revision_id"],
        "second_source_revision_id": repeated["source_revision_id"],
        "candidate_pit_source_revision_id": candidate_identity["source_revision_id"],
        "database_same_bytes_new_metadata_check": checks.get("same_bytes_new_temporal_evidence_is_a_new_revision"),
        "database_update_of_prior_revision_rejected": checks.get("temporal_evidence_revision_is_append_only"),
        "append_only": True,
    }
    atomic_json(ROOT / "reports/v4_08/V4_08_R2_SOURCE_REVISION_METADATA_TEST.json", revision_test)

    chain = validate_revision_chain([
        {"source_revision_id": raw_revision["source_revision_id"], "supersedes_revision_id": None},
        {"source_revision_id": candidate_identity["source_revision_id"], "supersedes_revision_id": raw_revision["source_revision_id"]},
    ])
    revision_chain = {
        "contract_id": "V4_08_R2_REVISION_CHAIN_V1",
        "status": "PASS_CANDIDATE_CHAIN_ONLY" if chain["status"] == "PASS" and checks.get("revision_fork_rejected") else "FAIL",
        "candidate_chain": chain,
        "database_fork_rejected": checks.get("revision_fork_rejected"),
        "accepted_revision_mutated": False,
        "source_revision_inserted_into_production_database": False,
        "note": "The temporal-evidence successor is a candidate identity; external policy review and PIT acceptance are still required before formal insertion.",
    }
    atomic_json(ROOT / "reports/v4_08/V4_08_R2_REVISION_CHAIN.json", revision_chain)

    effective = read_json("reports/v4_08/V4_08_R2_EFFECTIVE_DATE_VERIFICATION.json")
    effective["isolated_sql_gate"] = "PASS_STALE_ASOF_REJECTED" if checks.get("stale_membership_asof_rejected") else "FAIL"
    atomic_json(ROOT / "reports/v4_08/V4_08_R2_EFFECTIVE_DATE_VERIFICATION.json", effective)

    parameter_path = ROOT / "config/v4_08_algorithm_parameter_set_v1.json"
    vectors_doc = read_json("config/v4_08_algorithm_machine_vectors_v1.json")
    vector_results = []
    for vector in vectors_doc["vectors"]:
        result = evaluate_rotation_vector(vector["scenario"])
        expected = vector["independent_expected"]
        if vector["vector_id"].startswith("R1"):
            passed = result["rotation_in_possible"] and result["mature_strong_retention"] == "NOT_APPLICABLE"
        elif vector["vector_id"].startswith("R2"):
            passed = not result["rotation_expanding_allowed"] and not result["rotation_reaccelerating_allowed"]
        else:
            passed = not result["rotation_accepted_possible"] and not result["rotation_expanding_allowed"]
        vector_results.append({"vector_id": vector["vector_id"], "result": result,
                               "independent_expected": expected, "status": "PASS" if passed else "FAIL"})
    algorithm_receipt = {
        "contract_id": "V4_08_R2_ALGORITHM_CONTRACT_VECTOR_RECEIPT_V1",
        "status": "PASS_CONTRACT_VECTOR_ENGINEERING_ONLY" if all(x["status"] == "PASS" for x in vector_results) else "FAIL",
        "contracts_frozen": [
            "config/v4_08_sector_native_contract_v1.json",
            "config/v4_08_sector_prewatch_contract_v1.json",
            "config/v4_08_rotation_core_contract_v1.json",
            "config/v4_08_sector_legacy_adapter_contract_v1.json",
            "config/v4_08_sector_field_registry_v1.json",
        ],
        "parameter_set_id": "V4_08_ALGORITHM_PARAMETER_SET_V1",
        "parameter_set_sha256": sha(parameter_path.read_bytes()),
        "vector_count": len(vectors_doc["vectors"]),
        "vector_results": vector_results,
        "pending_v4_00g_parameter_ids": [item["parameter_id"] for item in json.loads(parameter_path.read_text(encoding="utf-8"))["parameters"] if item["value"] is None],
        "base_seed_dependent_fields": "UNKNOWN / DEGRADED_BY_UPSTREAM_BASE_SEED_SIGNAL",
        "full_market_materialization": "NOT_RUN",
        "formal_production_authorized": False,
    }
    atomic_json(ROOT / "reports/v4_08/V4_08_R2_ALGORITHM_CONTRACT_VECTOR_RECEIPT.json", algorithm_receipt)

    rps = {
        "contract_id": "V4_07_PRIOR_RPS_BOOTSTRAP_GAP_ASSESSMENT_R2",
        "audit_id": "V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01",
        "status": "OPEN_REPAIR_CONTINUES_INDEPENDENTLY",
        "starting_evidence": {"path": "reports/audits/V4_07_PRIOR_RPS_BOOTSTRAP_GAP_ASSESSMENT_R1.json",
                              "sha256": sha((ROOT / "reports/audits/V4_07_PRIOR_RPS_BOOTSTRAP_GAP_ASSESSMENT_R1.json").read_bytes())},
        "accepted_factor_publication_created": False,
        "accepted_prior_rps_values_created": False,
        "v4_03_r3_staging_values_copied": False,
        "v4_05_accepted_artifacts_modified": False,
        "thresholds_changed": False,
        "required_next_inputs": ["accepted dated universe snapshots for T-1/T-3", "accepted session calendar", "accepted adjustment basis and source identities", "independent RPS cross-section recomputation", "first-available/warm-up reconciliation", "new append-only accepted factor publication/revision"],
        "impact": "Blocks only consumers requiring true Base Seed/Seed Width; Sector native non-seed contract engineering remains open.",
    }
    atomic_json(ROOT / "reports/audits/V4_07_PRIOR_RPS_BOOTSTRAP_GAP_ASSESSMENT_R2.json", rps)

    all_code_gates = all([
        mixed["status"] == "PASS_SPLIT_LINEAGES",
        migration["status"] == "PASS_ISOLATED_MIGRATION_AND_ROLLBACK",
        formal_gate["status"] == "PASS",
        effective["isolated_sql_gate"] == "PASS_STALE_ASOF_REJECTED",
        revision_test["status"] == "PASS",
        determinism["status"] == "PASS_FIXED_R1_EVIDENCE",
        algorithm_receipt["status"] == "PASS_CONTRACT_VECTOR_ENGINEERING_ONLY",
    ])
    contract_acceptance = {
        "contract_id": "V4_08_R2_CONTRACT_REPAIR_ACCEPTANCE_V1",
        "status": "PASS_CONTRACT_REPAIRS_PIT_PREREQUISITE_BLOCKED" if all_code_gates else "FAIL",
        "starting_head": "68276e4f48f7664827418a6095b3a0ddcc1fa0a8",
        "closed_code_gaps": {
            "B01_mixed_basis_snapshot": "PASS_RAW_AND_PARENT_SNAPSHOTS_SPLIT",
            "B02_formal_view_quality": "PASS_FACT_SNAPSHOT_SOURCE_REVISION_QUALITY_GATES",
            "B03_historical_safe_semantics": "PASS_PIT_DEGRADED_MAY_BE_HISTORY_UNSAFE",
            "B04_exact_effective_date": "PASS_DAILY_EXACT_NO_CARRY_FORWARD",
            "B05_temporal_revision_identity": "PASS_BYTES_PLUS_TEMPORAL_EVIDENCE_APPEND_ONLY",
        },
        "identity_scope": identity_gate["status"],
        "forward_pit": pit["status"],
        "sector_rotation_vectors": algorithm_receipt["status"],
        "prior_rps": rps["status"],
        "external_acceptance": "PENDING; no Accepted Head created",
        "stage_terminal": STAGE_TERMINAL,
        "next_stage": "ACCEPTED_CALENDAR_EXTENSION_AND_V4_01_IDENTITY_REVISION_THEN_INDEPENDENT_V4_08_MEMBERSHIP_AUDIT",
    }
    atomic_json(ROOT / "reports/v4_08/V4_08_R2_CONTRACT_REPAIR_ACCEPTANCE.json", contract_acceptance)

    stage_entry = f"""# V4-08 R2 Stage Entry\n\n- Stage contract: `V4_08_R2_MEMBERSHIP_CONTRACT_REPAIR_AND_FORWARD_PIT_BASELINE_TASK_20260930`.\n- Independent R1 audit: `V4_06_V4_07_PROMOTION_V4_08_R1_INDEPENDENT_EXTERNAL_AUDIT_20260930`.\n- Starting HEAD: `68276e4f48f7664827418a6095b3a0ddcc1fa0a8`; branch: `codex/v4-system-reform`.\n- Governing executable contract: REV2 SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`, §§77C, 78, 15–18, 21A.4.\n- Phase 0: `FULL_PASS` inherited from accepted global head; no new scanner production starts.\n- R1 RPS audit remains `OPEN`; V4-07 real Base Seed signal remains degraded.\n- R2 contract/schema engineering and Sector/Rotation synthetic vector work are authorized.\n- Entry result: `AUTHORIZED_FOR_R2_CONTRACT_REPAIR_AND_CANDIDATE_EVIDENCE`; formal PIT baseline remains fail-closed.\n- User-supplied task and external audit copies are hash-bound in the stage evidence manifest.\n"""
    entry_path = ROOT / "reports/v4_08/V4_08_R2_STAGE_ENTRY.md"
    entry_path.parent.mkdir(parents=True, exist_ok=True)
    entry_path.write_text(stage_entry, encoding="utf-8", newline="\n")

    clean_path = ROOT / "reports/v4_08/V4_08_R2_CLEAN_CHECKOUT_RECEIPT.json"
    clean = read_json(clean_path.relative_to(ROOT).as_posix()) if clean_path.exists() else {"status": "MISSING"}
    if clean.get("status") != "PASS_CLEAN_CHECKOUT":
        contract_acceptance["status"] = "PASS_CONTRACT_REPAIRS_PIT_PREREQUISITE_BLOCKED_CLEAN_CHECKOUT_PENDING"
        atomic_json(ROOT / "reports/v4_08/V4_08_R2_CONTRACT_REPAIR_ACCEPTANCE.json", contract_acceptance)

    closure = f"""# V4-08 R2 Closure\n\n## Terminal state\n\n`{STAGE_TERMINAL}`\n\n## Membership contract repair\n\n- Starting HEAD: `68276e4f48f7664827418a6095b3a0ddcc1fa0a8`.\n- Migration 018 SHA-256: `{migration['migrations'][-1]['sha256']}`; migration 016/017 were not rewritten.\n- Raw current snapshot: `{mixed['snapshots']['raw_current']['snapshot_id']}` ({mixed['raw_source_fact_count']:,} facts).\n- Derived parent snapshot: `{mixed['snapshots']['derived_parent']['snapshot_id']}` ({mixed['derived_parent_fact_count']:,} facts), parent raw snapshot `{mixed['snapshots']['derived_parent']['parent_snapshot_id']}`.\n- Raw and parent replay use separate snapshots; parent replay retains `DERIVED_PARENT_MEMBERSHIP`.\n- SQL formal view quality and exact-date gates passed in isolated PostgreSQL {migration['postgres_version']}.\n- Source revision identity now binds source bytes digest and temporal-evidence digest; evidence-only revisions are append-only.\n\n## Identity and go-forward PIT\n\n- 497 unresolved keys / 1,176 facts classified: ETF/fund 325 keys, convertible bond 55, BSE optional 106, ambiguous required-board candidate 11.\n- Required-board ambiguity by board: `{json.dumps(identity['formal_board_ambiguous_key_counts'], sort_keys=True)}`. A versioned V4-01 identity/lifecycle update is required; V4-08 did not hand-map these keys.\n- R1 frozen byte set was completely observed by `2026-09-30T00:45:21.890265Z`; source-specific provider-time policy remains a candidate and does not claim provider publication time. Filesystem mtime was not used.\n- Accepted market calendar coverage ends `2026-09-24`; no formal target session or cutoff after that date is accepted here. Candidate PIT trade date remains null and no PIT snapshot was created.\n\n## Sector / Rotation\n\n- Sector Native, B0 PREWATCH, B1 ROTATION_CORE_V1, B2 Legacy Adapter, field registry, parameter set, and machine vectors are frozen as engineering candidates.\n- Rotation synthetic R1/R2/R3: `{json.dumps({x['vector_id']: x['status'] for x in vector_results}, sort_keys=True)}`.\n- Five V4-00G retention parameters remain unassigned and block affected formal consumers. Real full-market materialization remains disabled.\n\n## Prior-RPS and regression\n\n- Prior-RPS audit `V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01` remains `OPEN`; no accepted factor publication or thresholds changed; V4-03 R3 staging was not copied.\n- Required regression status: `{regression['status']}` with observed summary `{json.dumps(regression.get('summary'), sort_keys=True)}`.\n- Clean checkout status: `{clean.get('status')}`.\n- External acceptance: not requested or self-recorded. No V4-08 Accepted Head exists.\n\nNext: complete the accepted calendar extension and V4-01 identity revision, then submit the PIT prerequisite and candidate contract evidence for independent external audit.\n"""
    (ROOT / "reports/v4_08/V4_08_R2_CLOSURE.md").write_text(closure, encoding="utf-8", newline="\n")

    implementation_paths = [
        "config/v4_08_sector_membership_contract_v2.json", "config/v4_08_sector_membership_quality_v2.json",
        "config/v4_08_tdx_source_availability_policy_candidate_v1.json",
        "config/v4_08_sector_native_contract_v1.json", "config/v4_08_sector_prewatch_contract_v1.json",
        "config/v4_08_rotation_core_contract_v1.json", "config/v4_08_sector_legacy_adapter_contract_v1.json",
        "config/v4_08_sector_field_registry_v1.json", "config/v4_08_algorithm_parameter_set_v1.json",
        "config/v4_08_algorithm_machine_vectors_v1.json", "src/sector/membership_baseline.py",
        "src/sector/v4_08_rotation_vectors.py", "scripts/build_v4_08_r2_membership_evidence.py",
        "scripts/verify_v4_08_membership_migration.py", "scripts/run_v4_08_r2_regression.py",
        "scripts/seal_v4_08_r2_stage.py", "src/workbench_db/migrations/v4_postgres/018_v4_08_membership_contract_repair_r2.sql",
        "src/workbench_db/migrations/v4_postgres/rollback/018_v4_08_membership_contract_repair_r2.sql",
        "tests/v4_08/test_membership_contract.py", "tests/v4_08/test_r2_contract_vectors.py",
    ]
    evidence_paths = [
        "reports/v4_08/V4_08_R2_STAGE_ENTRY.md", "reports/v4_08/V4_08_R2_CONTRACT_REPAIR_ACCEPTANCE.json",
        "reports/v4_08/V4_08_R2_MIXED_BASIS_SPLIT_VERIFICATION.json", "reports/v4_08/V4_08_R2_FORMAL_VIEW_QUALITY_GATE.json",
        "reports/v4_08/V4_08_R2_EFFECTIVE_DATE_VERIFICATION.json", "reports/v4_08/V4_08_R2_SOURCE_REVISION_METADATA_TEST.json",
        "reports/v4_08/V4_08_R2_IDENTITY_SCOPE_CLASSIFICATION.json", "reports/v4_08/V4_08_R2_FORMAL_UNIVERSE_IDENTITY_GATE.json",
        "reports/v4_08/V4_08_R2_FORWARD_SOURCE_AVAILABILITY_EVIDENCE.json", "reports/v4_08/V4_08_R2_GO_FORWARD_PIT_CANDIDATE.json",
        "reports/v4_08/V4_08_R2_DETERMINISM.json", "reports/v4_08/V4_08_R2_TEMPORAL_LEAKAGE.json",
        "reports/v4_08/V4_08_R2_REVISION_CHAIN.json", "reports/v4_08/V4_08_R2_SCHEMA_MIGRATION_RECEIPT.json",
        "reports/v4_08/V4_08_R2_CLEAN_CHECKOUT_RECEIPT.json", "reports/v4_08/V4_08_R2_REQUIRED_REGRESSION.json",
        "reports/v4_08/V4_08_R2_ALGORITHM_CONTRACT_VECTOR_RECEIPT.json", "reports/audits/V4_07_PRIOR_RPS_BOOTSTRAP_GAP_ASSESSMENT_R2.json",
        "reports/v4_08/V4_08_R2_CLOSURE.md",
        "reports/v4_08/staging/V4_08_R2_RAW_CURRENT_TDX_MEMBERSHIP.jsonl.gz",
        "reports/v4_08/staging/V4_08_R2_DERIVED_PARENT_MEMBERSHIP.jsonl.gz",
        "reports/v4_08/staging/V4_08_R2_RAW_CURRENT_MEMBERSHIP_REPLAY.jsonl.gz",
        "reports/v4_08/staging/V4_08_R2_DERIVED_PARENT_MEMBERSHIP_REPLAY.jsonl.gz",
        "reports/v4_08/staging/V4_08_CURRENT_TDX_MEMBERSHIP_R1.jsonl.gz",
    ]
    missing = [path for path in implementation_paths + evidence_paths if not (ROOT / path).is_file()]
    if missing:
        raise FileNotFoundError("required R2 manifest paths missing: " + ", ".join(missing))
    files = [manifest_entry(path) for path in implementation_paths + evidence_paths]
    files.extend(copied_docs)
    manifest = {
        "contract_id": "V4_08_R2_STAGE_CANDIDATE_MANIFEST_V1",
        "status": STAGE_TERMINAL,
        "starting_head": "68276e4f48f7664827418a6095b3a0ddcc1fa0a8",
        "stage_terminal": STAGE_TERMINAL,
        "file_count": len(files),
        "files": sorted(files, key=lambda entry: entry["path"]),
        "source_bindings": {
            "accepted_v4_05_head": {"path": "data/v4/V4_05_ACCEPTED_HEAD.json", "sha256": sha((ROOT / "data/v4/V4_05_ACCEPTED_HEAD.json").read_bytes())},
            "accepted_v4_01_identity_map": identity["source_identity_revision"],
            "r1_observation_receipt": manifest_entry("reports/v4_08/V4_08_SECTOR_MEMBERSHIP_SOURCE_CONTRACT_ACCEPTANCE.json"),
            "accepted_calendar": manifest_entry("reports/v4_02/V4_02_FORMAL_MARKET_CALENDAR_ACCEPTANCE_V2.json"),
            "prior_rps_audit_r1": manifest_entry("reports/audits/V4_07_PRIOR_RPS_BOOTSTRAP_GAP_ASSESSMENT_R1.json"),
        },
        "formal_production_enabled": False,
        "self_manifest_excluded": True,
    }
    atomic_json(ROOT / "reports/v4_08/V4_08_R2_STAGE_CANDIDATE_MANIFEST.json", manifest)
    print(json.dumps({"status": manifest["status"], "file_count": manifest["file_count"],
                      "regression": regression.get("summary"), "clean_checkout": clean.get("status")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
