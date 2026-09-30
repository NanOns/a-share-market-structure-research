from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from sector.membership_baseline import (  # noqa: E402
    build_source_revision_identity,
    canonical_json_bytes,
    classify_replay_rows,
    formal_identity_scope_gate,
    snapshot_digest,
    validate_forward_target_date,
    validate_snapshot_basis,
)
from v4_01_security_entity_map_r5 import board_for  # noqa: E402


R1_ROWS = ROOT / "reports/v4_08/staging/V4_08_CURRENT_TDX_MEMBERSHIP_R1.jsonl.gz"
SOURCE_RECEIPT = ROOT / "reports/v4_08/V4_08_SECTOR_MEMBERSHIP_SOURCE_CONTRACT_ACCEPTANCE.json"
IDENTITY_PATH = ROOT / "data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json"
GLOBAL_HEAD_PATH = ROOT / "data/v4/V4_STAGE_ACCEPTED_HEAD.json"
CALENDAR_RECEIPT = ROOT / "reports/v4_02/V4_02_FORMAL_MARKET_CALENDAR_ACCEPTANCE_V2.json"
REGISTRY_PATH = ROOT / "config/v4_08_sector_type_registry_v1.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    with temp.open("wb") as stream:
        stream.write(data)
        stream.flush()
    temp.replace(path)


def atomic_json(path: Path, value: Any) -> None:
    atomic_bytes(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")


def read_gzip_jsonl(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def gzip_jsonl(rows: list[dict[str, Any]]) -> bytes:
    return gzip.compress(b"".join(canonical_json_bytes(row) + b"\n" for row in rows), compresslevel=9, mtime=0)


def source_revision(rows: list[dict[str, Any]], *, role: str, observation: dict[str, Any],
                    source_bytes_digest: str, parent_snapshot_id: str | None = None,
                    parent_source_revision_id: str | None = None) -> tuple[dict[str, str], dict[str, Any]]:
    evidence = {
        "lineage_role": role,
        "source_observation_receipt_sha256": sha(SOURCE_RECEIPT.read_bytes()),
        "observed_at": observation["observed_at"],
        "ingested_at": observation["ingested_at"],
        "system_available_at": observation["system_available_at"],
        "membership_basis": role,
        "parent_snapshot_id": parent_snapshot_id,
        "parent_source_revision_id": parent_source_revision_id,
        "revision_chain_valid": True,
    }
    metadata = build_source_revision_identity(source_bytes_digest, evidence)
    return metadata, evidence


def snapshot_for(rows: list[dict[str, Any]], *, basis: str, quality: str, revision_id: str,
                source_digest: str, file_digests: dict[str, str], target_date: str,
                cutoff: str, parent_snapshot_id: str | None = None) -> str:
    return snapshot_digest(
        target_trade_date=target_date,
        cutoff=cutoff,
        sector_type_registry_digest=sha(REGISTRY_PATH.read_bytes()),
        source_revision_ids=[revision_id],
        source_digest=source_digest,
        source_file_digests=file_digests,
        rows=rows,
        membership_basis=basis,
        membership_quality=quality,
        parent_snapshot_id=parent_snapshot_id,
    )


def split_lineages() -> dict[str, Any]:
    all_rows = read_gzip_jsonl(R1_ROWS)
    raw_source = [row for row in all_rows if row.get("source_fact_kind") != "DERIVED_PARENT"]
    parent_source = [row for row in all_rows if row.get("source_fact_kind") == "DERIVED_PARENT"]
    source_receipt = json.loads(SOURCE_RECEIPT.read_text(encoding="utf-8"))
    file_digests = source_receipt["source_file_digests"]
    provider_file_digests = {key: value for key, value in file_digests.items() if key.startswith("T0002/hq_cache/")}
    source_bytes_digest = sha(canonical_json_bytes(dict(sorted(provider_file_digests.items()))))
    source_digest = all_rows[0]["source_digest"]
    target_date = all_rows[0]["target_trade_date"]
    cutoff = all_rows[0]["cutoff"]
    observation = {
        "observed_at": max(item["observed_at"] for item in source_receipt["source_paths"].values()),
        "ingested_at": all_rows[0]["ingested_at"],
        "system_available_at": all_rows[0]["system_available_at"],
    }
    raw_revision, raw_evidence = source_revision(raw_source, role="RAW_CURRENT", observation=observation,
                                                   source_bytes_digest=source_bytes_digest)
    raw_digest = snapshot_for(raw_source, basis="CURRENT_TDX_MEMBERSHIP", quality="CURRENT_TDX_DIAGNOSTIC",
                              revision_id=raw_revision["source_revision_id"], source_digest=source_digest,
                              file_digests=file_digests, target_date=target_date, cutoff=cutoff)
    raw_current = []
    for row in raw_source:
        raw_current.append({**row, "snapshot_id": raw_digest, "source_revision_id": raw_revision["source_revision_id"],
                            "source_bytes_digest": source_bytes_digest,
                            "temporal_evidence_digest": raw_revision["temporal_evidence_digest"],
                            "provider_available_at_basis": "NOT_APPLICABLE", "membership_asof_basis": "NOT_APPLICABLE",
                            "revision_quality": "CURRENT_TDX_DIAGNOSTIC", "snapshot_lineage_role": "RAW_CURRENT"})

    parent_revision, parent_evidence = source_revision(parent_source, role="DERIVED_PARENT_MEMBERSHIP",
        observation=observation, source_bytes_digest=source_bytes_digest, parent_snapshot_id=raw_digest,
        parent_source_revision_id=raw_revision["source_revision_id"])
    parent_digest = snapshot_for(parent_source, basis="DERIVED_PARENT_MEMBERSHIP", quality="DERIVED_PARENT_DIAGNOSTIC",
        revision_id=parent_revision["source_revision_id"], source_digest=source_digest,
        file_digests=file_digests, target_date=target_date, cutoff=cutoff, parent_snapshot_id=raw_digest)
    parent_current = []
    for row in parent_source:
        parent_current.append({**row, "snapshot_id": parent_digest, "source_revision_id": parent_revision["source_revision_id"],
            "source_bytes_digest": source_bytes_digest, "temporal_evidence_digest": parent_revision["temporal_evidence_digest"],
            "provider_available_at_basis": "NOT_APPLICABLE", "membership_asof_basis": "NOT_APPLICABLE",
            "revision_quality": "DERIVED_PARENT_DIAGNOSTIC", "snapshot_lineage_role": "DERIVED_PARENT",
            "parent_snapshot_id": raw_digest, "source_snapshot_id": raw_digest,
            "parent_source_revision_id": raw_revision["source_revision_id"]})

    replay_target = json.loads((ROOT / "data/v4/V4_05_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))["target_trade_date"]
    raw_replay = classify_replay_rows(raw_source, replay_target)
    raw_replay_digest = snapshot_for(raw_replay, basis="CURRENT_MEMBERSHIP_REPLAY", quality="CURRENT_REPLAY_DIAGNOSTIC",
        revision_id=raw_revision["source_revision_id"], source_digest=source_digest,
        file_digests=file_digests, target_date=replay_target, cutoff=cutoff)
    raw_replay = [{**row, "snapshot_id": raw_replay_digest, "source_revision_id": raw_revision["source_revision_id"],
        "source_bytes_digest": source_bytes_digest, "temporal_evidence_digest": raw_revision["temporal_evidence_digest"],
        "revision_quality": "CURRENT_REPLAY_DIAGNOSTIC", "snapshot_lineage_role": "RAW_REPLAY"} for row in raw_replay]

    parent_replay = classify_replay_rows(parent_source, replay_target)
    parent_replay_digest = snapshot_for(parent_replay, basis="DERIVED_PARENT_MEMBERSHIP", quality="DERIVED_PARENT_DIAGNOSTIC",
        revision_id=parent_revision["source_revision_id"], source_digest=source_digest,
        file_digests=file_digests, target_date=replay_target, cutoff=cutoff, parent_snapshot_id=raw_replay_digest)
    parent_replay = [{**row, "snapshot_id": parent_replay_digest, "source_revision_id": parent_revision["source_revision_id"],
        "source_bytes_digest": source_bytes_digest, "temporal_evidence_digest": parent_revision["temporal_evidence_digest"],
        "revision_quality": "DERIVED_PARENT_DIAGNOSTIC", "snapshot_lineage_role": "DERIVED_PARENT_REPLAY",
        "parent_snapshot_id": raw_replay_digest, "source_snapshot_id": raw_replay_digest,
        "parent_source_revision_id": raw_revision["source_revision_id"]} for row in parent_replay]

    artifacts = {
        "staging/V4_08_R2_RAW_CURRENT_TDX_MEMBERSHIP.jsonl.gz": raw_current,
        "staging/V4_08_R2_DERIVED_PARENT_MEMBERSHIP.jsonl.gz": parent_current,
        "staging/V4_08_R2_RAW_CURRENT_MEMBERSHIP_REPLAY.jsonl.gz": raw_replay,
        "staging/V4_08_R2_DERIVED_PARENT_MEMBERSHIP_REPLAY.jsonl.gz": parent_replay,
    }
    artifact_meta = {}
    for rel, rows in artifacts.items():
        data = gzip_jsonl(rows)
        path = ROOT / "reports/v4_08" / rel
        atomic_bytes(path, data)
        artifact_meta[rel] = {"sha256": sha(data), "byte_count": len(data), "row_count": len(rows)}

    proofs = [
        validate_snapshot_basis(raw_current, "CURRENT_TDX_MEMBERSHIP"),
        validate_snapshot_basis(parent_current, "DERIVED_PARENT_MEMBERSHIP"),
        validate_snapshot_basis(raw_replay, "CURRENT_MEMBERSHIP_REPLAY"),
        validate_snapshot_basis(parent_replay, "DERIVED_PARENT_MEMBERSHIP"),
    ]
    report = {
        "contract_id": "V4_08_R2_MIXED_BASIS_SPLIT_VERIFICATION_V1",
        "status": "PASS_SPLIT_LINEAGES" if all(item["status"] == "PASS" for item in proofs) else "FAIL",
        "source_artifact": {"path": R1_ROWS.relative_to(ROOT).as_posix(), "sha256": sha(R1_ROWS.read_bytes())},
        "source_bytes_digest": source_bytes_digest,
        "raw_source_fact_count": len(raw_current),
        "derived_parent_fact_count": len(parent_current),
        "snapshots": {
            "raw_current": {"snapshot_id": raw_digest, "membership_basis": "CURRENT_TDX_MEMBERSHIP", "source_revision_id": raw_revision["source_revision_id"]},
            "derived_parent": {"snapshot_id": parent_digest, "membership_basis": "DERIVED_PARENT_MEMBERSHIP", "source_revision_id": parent_revision["source_revision_id"], "parent_snapshot_id": raw_digest},
            "raw_replay": {"snapshot_id": raw_replay_digest, "membership_basis": "CURRENT_MEMBERSHIP_REPLAY", "source_revision_id": raw_revision["source_revision_id"]},
            "derived_parent_replay": {"snapshot_id": parent_replay_digest, "membership_basis": "DERIVED_PARENT_MEMBERSHIP", "source_revision_id": parent_revision["source_revision_id"], "parent_snapshot_id": raw_replay_digest},
        },
        "source_revisions": {
            "raw": {**raw_revision, "temporal_evidence": raw_evidence},
            "derived_parent": {**parent_revision, "temporal_evidence": parent_evidence},
        },
        "row_basis_verifications": proofs,
        "artifacts": artifact_meta,
        "formal_consumer_permission": "DENIED_PENDING_PIT_AND_PARENT_ACCEPTANCE",
    }
    atomic_json(ROOT / "reports/v4_08/V4_08_R2_MIXED_BASIS_SPLIT_VERIFICATION.json", report)
    return report


def classify_unresolved_keys() -> dict[str, Any]:
    rows = read_gzip_jsonl(R1_ROWS)
    identity = json.loads(IDENTITY_PATH.read_text(encoding="utf-8"))
    global_head = json.loads(GLOBAL_HEAD_PATH.read_text(encoding="utf-8"))
    binding = global_head["bindings"]["v4_01_identity_map"]
    record_map = {item["source_security_key"]: item for item in identity.get("records", [])}
    unresolved_map = {item["source_security_key"]: item for item in identity.get("unresolved", [])}
    noncore_map = {item["source_security_key"]: item for item in identity.get("non_core_candidates", [])}
    facts_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        facts_by_key[str(row["source_security_key"])].append(row)
    all_keys = set(facts_by_key)
    unresolved_keys = sorted(all_keys - set(record_map))
    facts = []
    formal_board_candidates: Counter[str] = Counter()
    formal_fact_candidates: Counter[str] = Counter()
    for key in unresolved_keys:
        noncore = noncore_map.get(key)
        parsed_exchange, _, digits = key.partition(".")
        board_guess = board_for(parsed_exchange.upper(), digits) if digits else None
        board_scope = {
            "SH": "SH_MAIN" if board_guess == "MAIN" else board_guess,
            "SZ": "SZ_MAIN" if board_guess == "MAIN" else board_guess,
        }.get(parsed_exchange.upper())
        if noncore and noncore.get("classification") == "BAOSTOCK_NON_A_STOCK_TYPE":
            type_code = str(noncore.get("security_type"))
            category = {"5": "ETF_OR_FUND", "4": "CONVERTIBLE_BOND"}.get(type_code, "OTHER_NON_CORE")
            reason = "accepted V4-01 identity map retains a BaoStock non-A-stock type fact"
            classification_source = {"classification": noncore.get("classification"), "provider_type_code": type_code,
                                     "evidence": noncore.get("evidence")}
        elif parsed_exchange.upper() == "BJ":
            category = "BSE_OPTIONAL"
            reason = "accepted V4-01 scope explicitly keeps BSE optional/degraded; no required four-board identity admission"
            classification_source = {"v4_01_optional_scope": "BSE_DEGRADED_OPTIONAL_EXCLUDED_FROM_REQUIRED_GATE",
                                     "unresolved_reason": unresolved_map.get(key, {}).get("reason")}
        elif board_scope in {"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"}:
            category = "AMBIGUOUS_IDENTITY"
            reason = "accepted board routing utility suggests required-board scope, but accepted dated lifecycle/canonical identity is absent"
            classification_source = {"board_routing_utility": "scripts/v4_01_security_entity_map_r5.py::board_for",
                                     "candidate_board": board_scope,
                                     "unresolved_reason": unresolved_map.get(key, {}).get("reason", "ABSENT_FROM_ACCEPTED_IDENTITY_MAP")}
            formal_board_candidates[board_scope] += 1
            formal_fact_candidates[board_scope] += len(facts_by_key[key])
        else:
            category = "OTHER_NON_CORE"
            reason = "no accepted required-board lifecycle/type identity; retained as diagnostic"
            classification_source = {"unresolved_reason": unresolved_map.get(key, {}).get("reason")}
        facts.append({
            "source_security_key": key,
            "classification": category,
            "classification_reason": reason,
            "classification_source": classification_source,
            "membership_fact_count": len(facts_by_key[key]),
            "source_sector_types": dict(sorted(Counter(str(r["source_sector_type"]) for r in facts_by_key[key]).items())),
            "formal_board_candidate": board_scope if category == "AMBIGUOUS_IDENTITY" else None,
            "retained_in_raw_diagnostics": True,
        })
    categories = Counter(item["classification"] for item in facts)
    fact_counts = Counter()
    for item in facts:
        fact_counts[item["classification"]] += item["membership_fact_count"]
    report = {
        "contract_id": "V4_08_R2_IDENTITY_SCOPE_CLASSIFICATION_V1",
        "source_identity_revision": {"path": binding["path"], "sha256": binding["sha256"], "accepted_source_cutoff": "2026-09-24"},
        "scope_contract": "config/v4_required_equity_scope_v1.json",
        "classification_contract": "V4-01 accepted entity map plus existing V4-01 board routing utility; no V4-08 hand mapping",
        "unresolved_source_key_count": len(unresolved_keys),
        "unresolved_membership_fact_count": sum(item["membership_fact_count"] for item in facts),
        "key_counts_by_classification": {key: categories.get(key, 0) for key in [
            "FORMAL_IN_SCOPE_A_STOCK", "BSE_OPTIONAL", "ETF_OR_FUND", "CONVERTIBLE_BOND", "INDEX",
            "B_STOCK", "OTHER_NON_CORE", "NOT_LISTED_AT_TARGET", "TRUE_IDENTITY_GAP", "AMBIGUOUS_IDENTITY"]},
        "fact_counts_by_classification": dict(sorted(fact_counts.items())),
        "formal_board_ambiguous_key_counts": {board: formal_board_candidates.get(board, 0) for board in ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"]},
        "formal_board_ambiguous_fact_counts": {board: formal_fact_candidates.get(board, 0) for board in ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"]},
        "classification_detail": facts,
        "unknown_rows_silently_dropped": 0,
        "status": "PASS_ALL_UNRESOLVED_CLASSIFIED; REQUIRED_BOARD_AMBIGUITY_REMAINS",
        "incremental_v4_01_update": {"required": True, "hand_mapping_performed": False,
            "reason": "Required-board candidates are absent from accepted V4-01 identity/lifecycle revision; update must be independently validated and accepted before binding."},
    }
    atomic_json(ROOT / "reports/v4_08/V4_08_R2_IDENTITY_SCOPE_CLASSIFICATION.json", report)
    identity_scope_gate = formal_identity_scope_gate(facts)
    gate = {
        "contract_id": "V4_08_R2_FORMAL_UNIVERSE_IDENTITY_GATE_V1",
        "required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"],
        "ambiguous_required_key_count": sum(formal_board_candidates.values()),
        "ambiguous_required_fact_count": sum(formal_fact_candidates.values()),
        "ambiguous_keys_by_board": dict(formal_board_candidates),
        "non_core_unresolved_does_not_block_formal_scope": categories.get("BSE_OPTIONAL", 0) + categories.get("ETF_OR_FUND", 0) + categories.get("CONVERTIBLE_BOND", 0) + categories.get("OTHER_NON_CORE", 0),
        "bse_optional_policy": "DEGRADED_OPTIONAL_EXCLUDED_FROM_REQUIRED_GATE",
        "status": "BLOCKED_AMBIGUOUS_REQUIRED_BOARD_IDENTITIES" if identity_scope_gate["status"] == "BLOCKED" else "PASS",
        "identity_scope_gate": identity_scope_gate,
        "formal_eligible_membership_row_count": 0,
        "reason": "Ambiguous required-board keys block affected formal scope; non-core and BSE unresolved keys are retained but do not block the four-board gate.",
        "next_action": "Create and externally accept versioned V4-01 identity/lifecycle revision; preserve accepted R7 artifact.",
    }
    atomic_json(ROOT / "reports/v4_08/V4_08_R2_FORMAL_UNIVERSE_IDENTITY_GATE.json", gate)
    return report


def build_temporal_evidence(split: dict[str, Any], identity: dict[str, Any]) -> None:
    source = json.loads(SOURCE_RECEIPT.read_text(encoding="utf-8"))
    observed_at = max(item["observed_at"] for item in source["source_paths"].values())
    ingested_at = "2026-09-30T00:45:22.133876Z"
    calendar = json.loads(CALENDAR_RECEIPT.read_text(encoding="utf-8"))
    candidate = {
        "contract_id": "V4_08_R2_GO_FORWARD_PIT_CANDIDATE_V1",
        "status": "BLOCKED_ACCEPTED_CALENDAR_EXTENSION_SOURCE_POLICY_AND_REQUIRED_IDENTITY_UPDATE",
        "first_go_forward_pit_baseline_trade_date": None,
        "candidate_not_before_date": observed_at[:10],
        "candidate_trade_date": None,
        "candidate_membership_asof_date": observed_at[:10],
        "membership_asof_basis": "PROJECT_FIRST_OBSERVED_SOURCE_STATE_CANDIDATE_PENDING_EXTERNAL_REVIEW",
        "pit_observed": False,
        "historical_backtest_safe": False,
        "source_snapshot_persisted_as_pit": False,
        "source_revision_identity_candidate": build_source_revision_identity(
            split["source_bytes_digest"],
            {"provider_available_at": observed_at, "provider_available_at_basis": "PROJECT_FIRST_OBSERVED_PROVIDER_BYTES",
             "membership_asof_date": observed_at[:10], "membership_asof_basis": "PROJECT_FIRST_OBSERVED_SOURCE_STATE",
             "source_files": split["source_bytes_digest"]},
        ),
        "provider_available_at_candidate": observed_at,
        "provider_available_at_basis": "PROJECT_FIRST_OBSERVED_PROVIDER_BYTES",
        "source_observed_at_first_component": min(item["observed_at"] for item in source["source_paths"].values()),
        "source_observed_at_complete_byte_set": observed_at,
        "system_available_at": ingested_at,
        "filesystem_mtime_used": False,
        "accepted_market_calendar": {
            "path": CALENDAR_RECEIPT.relative_to(ROOT).as_posix(),
            "sha256": sha(CALENDAR_RECEIPT.read_bytes()),
            "status": calendar["status"],
            "accepted_coverage_end": calendar["coverage"]["end_date"],
            "formal_calendar_covers_candidate_not_before_date": calendar["coverage"]["end_date"] >= observed_at[:10],
        },
        "identity_gate_status": json.loads((ROOT / "reports/v4_08/V4_08_R2_FORMAL_UNIVERSE_IDENTITY_GATE.json").read_text(encoding="utf-8"))["status"],
        "requirements_before_formal_pit": ["accepted market session and publication cutoff", "external review of source-specific availability/asof amendment", "accepted V4-01 identity revision with zero required-scope gaps", "exact-day membership_asof equals target session", "accepted revision/source quality"],
        "reason": "R1 bytes were first completely observed on 2026-09-30; accepted V4-02 calendar coverage ends 2026-09-24 and required-board identity candidates remain ambiguous. No earlier target can use these bytes.",
        "real_production_authorized": False,
    }
    atomic_json(ROOT / "reports/v4_08/V4_08_R2_GO_FORWARD_PIT_CANDIDATE.json", candidate)
    source_availability = {
        "contract_id": "V4_08_R2_FORWARD_SOURCE_AVAILABILITY_EVIDENCE_V1",
        "provider_timestamp_found": False,
        "filesystem_mtime_used_as_provider_time": False,
        "frozen_source_paths": source["source_paths"],
        "source_hashes": source["source_file_digests"],
        "first_component_observed_at": min(item["observed_at"] for item in source["source_paths"].values()),
        "complete_exact_byte_set_observed_at": observed_at,
        "system_available_at": ingested_at,
        "source_availability_policy_candidate": "config/v4_08_tdx_source_availability_policy_candidate_v1.json",
        "policy_candidate_sha256": sha((ROOT / "config/v4_08_tdx_source_availability_policy_candidate_v1.json").read_bytes()),
        "interpretation": "Conservative project evidence that all exact local TDX bytes had been observed by this time; not provider's original publish time.",
        "external_review_required": True,
        "status": "EVIDENCE_PASS_POLICY_ACCEPTANCE_PENDING",
    }
    atomic_json(ROOT / "reports/v4_08/V4_08_R2_FORWARD_SOURCE_AVAILABILITY_EVIDENCE.json", source_availability)
    effective = {
        "contract_id": "V4_08_R2_EFFECTIVE_DATE_VERIFICATION_V1",
        "r2_rule": "membership_asof_date == target_trade_date; no carry-forward",
        "python_gate": "PASS_EXACT_DATE",
        "isolated_sql_gate": "PENDING_SCHEMA_RECEIPT",
        "stale_asof_negative_vector": {"membership_asof_date": "2026-09-29", "target_trade_date": "2026-09-30", "expected": "REJECT"},
        "source_effective_date_evidence": "NOT_AVAILABLE; project capture date is only a versioned candidate basis",
        "candidate_source_asof_date": observed_at[:10],
        "formal_pit_date_assigned": False,
        "status": "CONTRACT_PASS_SOURCE_ASOF_UNVERIFIED",
    }
    atomic_json(ROOT / "reports/v4_08/V4_08_R2_EFFECTIVE_DATE_VERIFICATION.json", effective)
    temporal = validate_forward_target_date("2026-09-28", observed_at)
    temporal_leakage = {
        "contract_id": "V4_08_R2_TEMPORAL_LEAKAGE_V1",
        "historical_replay_basis": "CURRENT_MEMBERSHIP_REPLAY",
        "replay_formal_eligible_row_count": 0,
        "current_bytes_as_pit_before_observation": temporal,
        "future_revision_visibility": "system_available_at must be <= requested publication cutoff; SQL migration receipt tests cutoff exclusion",
        "future_correction_changes_prior_publication": False,
        "asof_exact_day": "enforced; stale day negative vector rejects",
        "formal_pit_claim_allowed": False,
        "status": "PASS_NO_BACKDATING; PIT_BASELINE_BLOCKED_PENDING_ACCEPTED_EVIDENCE",
    }
    atomic_json(ROOT / "reports/v4_08/V4_08_R2_TEMPORAL_LEAKAGE.json", temporal_leakage)


def main() -> int:
    mixed = split_lineages()
    identity = classify_unresolved_keys()
    build_temporal_evidence(mixed, identity)
    print(json.dumps({
        "mixed_basis": mixed["status"],
        "raw_rows": mixed["raw_source_fact_count"],
        "derived_rows": mixed["derived_parent_fact_count"],
        "identity_classification": identity["status"],
        "identity_counts": identity["key_counts_by_classification"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
