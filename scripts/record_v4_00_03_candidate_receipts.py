from __future__ import annotations

"""Record scoped V4-00 authority and V4-03 ownership amendment candidates."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PHASE0_RECEIPT = Path("reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json")
GLOBAL_HEAD = Path("data/v4/V4_STAGE_ACCEPTED_HEAD.json")
PHASE0_EXTERNAL_R4 = Path("docs/audits/V4_PHASE0_EXTERNAL_ACCEPTANCE_R4_RESEAL_20260925.md")
PRE03_EXTERNAL_REAUDIT = Path("docs/evidence/V4_PRE03_JOINT_R1_EXTERNAL_REAUDIT_20260928.md")
V401_IDENTITY = Path("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
V401_UNIVERSE = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz")
V402_HEAD = Path("data/v4/V4_02_ACCEPTED_HEAD.json")
V402_MANIFEST = Path("reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R6.json")
V403_HEAD = Path("data/v4/V4_03_ACCEPTED_HEAD.json")
V403_DISPOSITION = Path("reports/v4_03/V4_03_STAGE_DISPOSITION_R3.json")
V403_FINAL_RECEIPT = Path("reports/v4_03/V4_03_FINAL_STAGE_RECEIPT_R1_20260928.json")
V403_SECTOR_BOUNDARY = Path("reports/v4_03/V4_03_SECTOR_NATIVE_BOUNDARY_ACCEPTANCE_R1.json")
V403_NATIVE_ACCEPTANCE = Path("reports/v4_03/V4_03_NATIVE_CONTRACT_ACCEPTANCE_R3.json")
V403_PRODUCER_CHECK = Path("reports/v4_03/V4_03_CONTRACT_PRODUCER_CONSISTENCY_R3.json")
V403_VECTOR_ACCEPTANCE = Path("reports/v4_03/V4_03_AST_GOLDEN_VECTOR_ACCEPTANCE_R3.json")
AMENDMENT_DOC = Path("docs/audits/V4_03_SECTOR_OWNERSHIP_AMENDMENT_V1_20260929.md")
AMENDMENT_RECEIPT = Path("reports/v4_03/V4_03_SECTOR_OWNERSHIP_AMENDMENT_R1.json")
RESEAL_CANDIDATE = Path("reports/v4_03/V4_03_FOUNDATION_RESEAL_CANDIDATE_R1.json")
V400_RECEIPT = Path("reports/v4_phase0/V4_00_CURRENT_AUTHORITY_NORMALIZATION_R1.json")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def evidence(path: Path) -> dict[str, Any]:
    return {"path": path.as_posix(), "sha256": sha(path), "byte_count": (ROOT / path).stat().st_size}


def atomic_json(path: Path, value: dict[str, Any]) -> bytes:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd, temp = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    finally:
        Path(temp).unlink(missing_ok=True)
    return payload


def atomic_text(path: Path, text: str) -> bytes:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = text.encode("utf-8")
    fd, temp = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    finally:
        Path(temp).unlink(missing_ok=True)
    return payload


def main() -> int:
    phase0 = load(PHASE0_RECEIPT)
    global_head = load(GLOBAL_HEAD)
    v403_head = load(V403_HEAD)
    v403_disposition = load(V403_DISPOSITION)
    v403_final = load(V403_FINAL_RECEIPT)
    sector_boundary = load(V403_SECTOR_BOUNDARY)
    native = load(V403_NATIVE_ACCEPTANCE)
    producer = load(V403_PRODUCER_CHECK)
    vectors = load(V403_VECTOR_ACCEPTANCE)

    phase0_binding = global_head.get("bindings", {}).get("phase0", {})
    phase0_external_r4 = phase0.get("external_acceptance_r4", {})
    phase0_scope_external = "V4-00 = FULL_PASS / 外部无新增异议" in (ROOT / PRE03_EXTERNAL_REAUDIT).read_text(encoding="utf-8")
    v400_checks = {
        "current_phase0_receipt_is_full_pass": phase0.get("phase0_status") == "FULL_PASS",
        "current_phase0_receipt_hash_bound_by_global_head": phase0_binding.get("path") == PHASE0_RECEIPT.as_posix() and phase0_binding.get("sha256") == sha(PHASE0_RECEIPT),
        "phase0_r4_entry_authority_preserved": phase0_external_r4.get("authority") == "DA-MSR-V4-PHASE0-FINAL-EXTERNAL-ACCEPTANCE-R4" and phase0.get("v4_01_entry_permission") == "R8_STAGE_COMPLETE; EXTERNAL_REVIEW_REQUIRED",
        "independent_joint_review_accepts_v4_00_scope": phase0_scope_external,
        "phase0_core_blockers_empty": phase0.get("core_blockers") == [] and phase0.get("remaining_phase0_blockers") == [],
    }
    v400_status = "FULL_PASS" if all(v400_checks.values()) else "BLOCKED"
    v400 = {
        "contract_id": "V4_00_CURRENT_AUTHORITY_NORMALIZATION_R1",
        "version": "1.0.0-candidate",
        "stage": "V4-00 CURRENT AUTHORITY NORMALIZATION",
        "status": v400_status,
        "v4_00_external_acceptance": "ACCEPTED_SCOPE_SPECIFIC" if v400_status == "FULL_PASS" else "PENDING",
        "joint_00_01_02_03_external_acceptance": "PENDING_EXTERNAL_REVIEW",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "authority_scope": {
            "phase0_current_receipt_status": phase0.get("phase0_status"),
            "current_receipt_external_acceptance_field": phase0.get("external_acceptance"),
            "phase0_r4_entry_authority": phase0_external_r4.get("authority"),
            "phase0_r4_authority_acceptance_at_time": phase0_external_r4.get("phase0_status"),
            "v4_00_specific_external_review_result": "FULL_PASS; NO_NEW_OBJECTION" if phase0_scope_external else "NOT_CONFIRMED",
            "interpretation": "The V4-00-specific review is accepted for Phase0 obligations. The current R5 receipt's PENDING_JOINT_EXTERNAL_REVIEW remains true for the combined 00-03 seal and is not overwritten.",
        },
        "bindings": {
            "current_phase0_receipt": evidence(PHASE0_RECEIPT),
            "global_accepted_head": evidence(GLOBAL_HEAD),
            "phase0_r4_reseal_evidence": evidence(PHASE0_EXTERNAL_R4),
            "v4_00_specific_external_review": evidence(PRE03_EXTERNAL_REAUDIT),
        },
        "checks": v400_checks,
        "mutations": {"phase0_receipt_modified": False, "global_accepted_head_modified": False, "00a_to_00h_reexecuted": False},
        "stage_record": {
            "stage_contract": "V4_PHASE0_FINAL_ACCEPTANCE_R5_STAGE_OBLIGATION plus Phase0 R4 receipt-only external seal and V4-00-specific R1 external disposition",
            "evidence": "Current R5 FULL_PASS receipt, R4 scope authority, and external R1 finding V4-00 FULL_PASS/no new objection",
            "acceptance_result": v400_status,
            "next_stage": "BIND_IN_FOUNDATION_CANDIDATE; KEEP_JOINT_EXTERNAL_REVIEW_PENDING",
        },
        "execution_identity": {
            "input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "script_sha256": sha(Path(__file__).resolve().relative_to(ROOT)),
            "python_version": sys.version.split()[0],
        },
    }
    v400_bytes = atomic_json(V400_RECEIPT, v400)

    existing_upstream = v403_head.get("upstream_identities", {})
    upstream_matches = (
        existing_upstream.get("v4_01_identity_map", {}).get("sha256") == sha(V401_IDENTITY)
        and existing_upstream.get("v4_01_universe", {}).get("sha256") == sha(V401_UNIVERSE)
        and existing_upstream.get("v4_02_accepted_head", {}).get("sha256") == sha(V402_HEAD)
        and existing_upstream.get("v4_02_manifest", {}).get("sha256") == sha(V402_MANIFEST)
    )
    required_capabilities = v403_disposition.get("capabilities", {})
    stock_market_candidate_pass = all(
        required_capabilities.get(key, {}).get("status") == "PASS_CANDIDATE"
        and not required_capabilities.get(key, {}).get("residual_blockers")
        for key in ("STOCK_CORE", "RELATIVE_RPS", "MARKET_REFERENCE", "MARKET_REGIME")
    )
    sector_contract_pass = native.get("status") == "PASS" and producer.get("status") == "PASS" and vectors.get("status") == "PASS"
    sector_materialization_blocked = sector_boundary.get("status") == "BLOCKED_ACCEPTED_SECTOR_MEMBERSHIP_INPUT_MISSING" and sector_boundary.get("full_market_artifact") == "NOT_PRODUCED"

    amendment_text = """# V4-03 Sector Ownership Amendment V1 — Candidate\n\n- 日期：2026-09-29\n- 合同：`V4_03_SECTOR_OWNERSHIP_AMENDMENT_V1 v1.0.0-candidate`\n- 状态：`AMENDMENT_CANDIDATE_PENDING_EXTERNAL_ACCEPTANCE`\n- 适用阶段：V4-03 / V4-08\n\n## 决策\n\n本 amendment 调整依赖 accepted point-in-time (PIT) sector membership 的 materialization 所属阶段。它不删除 V4-03 的算法验收，也不降低质量门。V4-03 保留 membership-independent 的 Sector Native schema、machine contracts、field-local quality semantics、common-member semantics、native primitive formulas 与 synthetic/library vectors；这些内容的既有 machine-contract / producer-consistency / golden-vector receipts 继续绑定为 V4-03 evidence。\n\n由于当前无 accepted historical PIT sector membership，V4-03 不生成 full-market sector rows。以下能力统一迁移至 V4-08 Sector / Rotation owner stage：\n\n- PIT sector member snapshots 与 historical membership reconstruction；\n- full-market Sector Native materialization；\n- sector-native full-market rows；\n- 任何消费历史 Sector/Rotation inputs 的生产路径。\n\n`CURRENT_TDX_MEMBERSHIP` 仍为 diagnostic input，`pit_membership=false`，`historical_backtest_safe=false`。V4-08 必须先建立正式、可追溯的 membership source contract 与 baseline/PIT reconstruction，再产出、读取上述 materialization。此边界不授权将当前成员表回填到历史。\n\n## Stage status and downstream permissions\n\nAmendment 外部验收前，V4-03 为 `PASS_WITH_SECTOR_SCOPE_DEGRADED` candidate：Stock Core、Relative RPS、Market Reference、Market Regime 按各自现有 candidate receipts；Sector Native contract 保持 PASS，sector materialization 保持 `BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP`。当前 V4-03 accepted head 不变。\n\n外部接受本 amendment 与 00-03 joint candidate 后，V4-03 可按修订范围申请 `FULL_PASS_AMENDED_SCOPE`。V4-04 Stock Core 仍须等待 joint external acceptance；V4-08 Sector/Rotation 仍 blocked，直到接受的 PIT membership baseline 和 full historical reconstruction 完成。Sector-dependent stock paths 继续 BLOCKED 或 SHADOW_ONLY。\n\n## 不变项\n\n- 没有伪造 historical PIT membership，也没有使用 `CURRENT_TDX_MEMBERSHIP` 回填历史。\n- 没有修改 V4-01/V4-02 accepted input identities。\n- 没有重建 V4-03 的 47 fields、market path 或 Market Regime。\n- 没有生成 sector full-market rows、qualification、rotation 或 V4-08 production。\n- 本 amendment 是 review candidate；未创建 V4-03 accepted head，也未授权 V4-04。\n\n## 阶段记录\n\n- Stage contract：V4-03 current capability contracts + V4-03 Sector Native boundary receipt + this versioned ownership amendment.\n- Evidence：V4-03 R3 capability disposition、native machine-contract/producer/golden-vector PASS receipts、sector boundary `BLOCKED_ACCEPTED_SECTOR_MEMBERSHIP_INPUT_MISSING`。\n- Acceptance：`AMENDMENT_CANDIDATE_PENDING_EXTERNAL_ACCEPTANCE`。\n- Next stage：独立外部验收；之后才能按 accepted upstream/head policy 更新 sealed scope。\n"""
    amendment_bytes = atomic_text(AMENDMENT_DOC, amendment_text)
    amendment_sha = hashlib.sha256(amendment_bytes).hexdigest()
    amend_status = "AMENDMENT_CANDIDATE_PENDING_EXTERNAL_ACCEPTANCE" if upstream_matches and stock_market_candidate_pass and sector_contract_pass and sector_materialization_blocked else "BLOCKED"
    amendment = {
        "contract_id": "V4_03_SECTOR_OWNERSHIP_AMENDMENT_V1",
        "version": "1.0.0-candidate",
        "stage": "V4-03 SECTOR OWNERSHIP AMENDMENT",
        "status": amend_status,
        "external_acceptance": "PENDING_EXTERNAL_REVIEW",
        "candidate_only": True,
        "document": {"path": AMENDMENT_DOC.as_posix(), "sha256": amendment_sha, "byte_count": len(amendment_bytes)},
        "retained_v4_03_capabilities": ["SECTOR_NATIVE_SCHEMA", "MACHINE_CONTRACTS", "FIELD_LOCAL_QUALITY_SEMANTICS", "COMMON_MEMBER_SEMANTICS", "NATIVE_PRIMITIVE_FORMULAS", "SYNTHETIC_AND_LIBRARY_VECTORS"],
        "retained_sector_contract_status": "PASS" if sector_contract_pass else "BLOCKED",
        "moved_to_v4_08": ["PIT_SECTOR_MEMBERSHIP_RECONSTRUCTION", "FULL_MARKET_SECTOR_MATERIALIZATION", "SECTOR_NATIVE_FULL_MARKET_ROWS", "SECTOR_ROTATION_PRODUCTION_INPUTS"],
        "sector_materialization_status": "BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP" if sector_materialization_blocked else "NOT_CONFIRMED",
        "current_tdx_membership_policy": {"pit_membership": False, "historical_backtest_safe": False, "diagnostic_only": True},
        "upstream_identity_hashes_unchanged": upstream_matches,
        "v4_04_entry": "BLOCKED_PENDING_JOINT_EXTERNAL_ACCEPTANCE",
        "v4_08_entry": "BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION",
        "checks": {
            "upstream_v4_01_v4_02_hashes_match_existing_v4_03_head": upstream_matches,
            "stock_and_market_capabilities_pass_candidate": stock_market_candidate_pass,
            "membership_independent_sector_native_contract_pass": sector_contract_pass,
            "full_market_materialization_remains_blocked_without_pit_membership": sector_materialization_blocked,
            "accepted_head_modified": False,
            "pit_membership_fabricated": False,
        },
        "evidence": {
            path.as_posix(): evidence(path)
            for path in (V403_DISPOSITION, V403_FINAL_RECEIPT, V403_SECTOR_BOUNDARY, V403_NATIVE_ACCEPTANCE, V403_PRODUCER_CHECK, V403_VECTOR_ACCEPTANCE, V403_HEAD, V401_IDENTITY, V401_UNIVERSE, V402_HEAD, V402_MANIFEST)
        },
        "stage_record": {
            "stage_contract": "V4-03 capability-scoped disposition and V4_03_SECTOR_OWNERSHIP_AMENDMENT_V1",
            "evidence": "Existing V4-03 R3 receipts plus accepted V4-01/V4-02 canonical hash equality; no materialization rebuild",
            "acceptance_result": amend_status,
            "next_stage": "INDEPENDENT_EXTERNAL_AMENDMENT_ACCEPTANCE",
        },
    }
    amendment_bytes = atomic_json(AMENDMENT_RECEIPT, amendment)

    reseal = {
        "contract_id": "V4_03_FOUNDATION_RESEAL_CANDIDATE_R1",
        "version": "1.0.0-candidate",
        "stage": "V4-03 CONDITIONAL RESEAL CANDIDATE",
        "status": "PASS_WITH_SECTOR_SCOPE_DEGRADED_CANDIDATE" if amend_status != "BLOCKED" else "BLOCKED",
        "external_acceptance": "PENDING_EXTERNAL_REVIEW",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "decision": "NO_CANONICAL_REBUILD_OR_ACCEPTED_HEAD_PROMOTION; existing upstream hashes are unchanged; amendment and V4-01 R9 remain candidates until external review.",
        "upstream": {
            "v4_01_identity_map": evidence(V401_IDENTITY),
            "v4_01_required_universe": evidence(V401_UNIVERSE),
            "v4_02_accepted_head": evidence(V402_HEAD),
            "v4_02_manifest": evidence(V402_MANIFEST),
            "existing_v4_03_head_upstream_identities_match": upstream_matches,
        },
        "capabilities": {
            "STOCK_CORE": "PASS_CANDIDATE" if stock_market_candidate_pass else "BLOCKED",
            "RELATIVE_RPS": required_capabilities.get("RELATIVE_RPS", {}).get("status"),
            "MARKET_REFERENCE": required_capabilities.get("MARKET_REFERENCE", {}).get("status"),
            "MARKET_REGIME": required_capabilities.get("MARKET_REGIME", {}).get("status"),
            "SECTOR_NATIVE_CONTRACT": "PASS" if sector_contract_pass else "BLOCKED",
            "SECTOR_NATIVE_FULL_MARKET": "BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP",
        },
        "amendment_candidate": {"path": AMENDMENT_RECEIPT.as_posix(), "sha256": hashlib.sha256(amendment_bytes).hexdigest()},
        "existing_v4_03_accepted_head": evidence(V403_HEAD),
        "existing_accepted_head_modified": False,
        "v4_03_rebuilt": False,
        "membership_dependent_materialization_rebuilt": False,
        "v4_04_entry": "BLOCKED_PENDING_FINAL_EXTERNAL_ACCEPTANCE",
        "v4_08_sector_rotation": "BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP",
        "stage_record": {
            "stage_contract": "V4-03 final receipt and accepted head; R2 amendment scope",
            "evidence": "Current accepted V4-03 head hash bindings and R3 capability receipts",
            "acceptance_result": "CANDIDATE_ONLY_PENDING_EXTERNAL_ACCEPTANCE" if amend_status != "BLOCKED" else "BLOCKED",
            "next_stage": "JOINT_00_03_EXTERNAL_REVIEW",
        },
    }
    reseal_bytes = atomic_json(RESEAL_CANDIDATE, reseal)
    print(json.dumps({
        "v4_00_status": v400_status,
        "v4_00_authority_sha256": hashlib.sha256(v400_bytes).hexdigest(),
        "v4_03_amendment_status": amend_status,
        "v4_03_amendment_sha256": hashlib.sha256(amendment_bytes).hexdigest(),
        "v4_03_reseal_candidate_status": reseal["status"],
        "v4_03_reseal_candidate_sha256": hashlib.sha256(reseal_bytes).hexdigest(),
        "upstream_hashes_match": upstream_matches,
        "v4_04_authorized": False,
    }, ensure_ascii=False, indent=2))
    return 0 if v400_status == "FULL_PASS" and amend_status != "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
