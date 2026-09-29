"""Promote the externally accepted V4-05 R4.2 candidate without starting V4-06."""
from __future__ import annotations

import json
from hashlib import sha256
import os
from pathlib import Path
import subprocess

from v4_05_promotion_contract import (
    ACCEPTED_HEAD, ARTIFACTS, CANDIDATE, CANDIDATE_MANIFEST, CAPABILITIES,
    CORE_LOGICAL_DIGEST, DECISION, EVIDENCE_PATHS, EXTERNAL_ACCEPTANCE,
    GLOBAL_HEAD, HISTORICAL_BLOCK, PROMOTION_TASK, ROOT, SNAPSHOT_ID, START_HEAD,
    authority_checks, atomic_json, file_identity, git_bytes, load_json,
)


def promote() -> dict:
    checks, detail = authority_checks()
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise RuntimeError("V4-05 promotion preflight failed: " + ", ".join(failed))

    accepted_path = ROOT / ACCEPTED_HEAD
    global_path = ROOT / GLOBAL_HEAD
    if accepted_path.exists():
        raise ValueError("V4-05 Accepted Head already exists")
    baseline_bytes = git_bytes("show", f"{START_HEAD}:{GLOBAL_HEAD}")
    baseline_global = json.loads(baseline_bytes.decode("utf-8"))
    if json.loads(global_path.read_text(encoding="utf-8")) != baseline_global:
        raise ValueError("Global Accepted Head semantics differ from the externally reviewed starting HEAD")
    if subprocess.run(["git", "diff", "--quiet", START_HEAD, "--", GLOBAL_HEAD], cwd=ROOT).returncode != 0:
        raise ValueError("Global Accepted Head has a tracked change before promotion")
    if "v4_06_entry" in detail["baseline_global_head"]:
        raise ValueError("V4-06 already has an entry state before this promotion")

    candidate_manifest = load_json(CANDIDATE_MANIFEST)
    exact = load_json("reports/v4_05/V4_05_R4_2_EXACT_CANDIDATE_LEDGER_BINDING.json")
    reference = load_json("reports/v4_05/V4_05_R4_1_MARKET_REFERENCE.json")
    market_regime = load_json("reports/v4_05/V4_05_R4_1_MARKET_REGIME.json")
    snapshot = load_json("reports/v4_05/V4_05_R4_1_MARKET_SNAPSHOT_IDENTITY.json")

    accepted_artifacts = {}
    for name, identity in detail["artifact_identities"].items():
        accepted_artifacts[name] = dict(identity)
        if "logical_digest" in ARTIFACTS[name]:
            accepted_artifacts[name]["logical_digest"] = ARTIFACTS[name]["logical_digest"]

    evidence_bindings = {name: file_identity(path) for name, path in EVIDENCE_PATHS.items()}
    market_reference_values = {
        str(horizon): reference["horizons"][str(horizon)]["reference_return"]
        for horizon in (1, 3, 5)
    }
    accepted = {
        "contract_id": "V4_05_ACCEPTED_HEAD_V1",
        "stage": "V4-05",
        "status": "DATA_FACTOR_REPLAY_DEGRADED_PASS",
        "external_acceptance": "EXTERNALLY_ACCEPTED",
        "external_acceptance_decision": DECISION,
        "accepted_at_date": "2026-09-29",
        "source_cutoff": "2026-09-24",
        "target_trade_date": "2026-09-28",
        "accepted_candidate": CANDIDATE,
        "accepted_manifest": file_identity(CANDIDATE_MANIFEST),
        "accepted_artifact": accepted_artifacts["core_profile"],
        "accepted_artifacts": accepted_artifacts,
        "implementation_commit": candidate_manifest["implementation_commit"],
        "evidence_seal_commit": START_HEAD,
        "external_acceptance_evidence": file_identity(EXTERNAL_ACCEPTANCE),
        "promotion_task": file_identity(PROMOTION_TASK),
        "capabilities": CAPABILITIES,
        "historical_as_recorded_adjusted_price": HISTORICAL_BLOCK,
        "ledger_state_logical_digest": CORE_LOGICAL_DIGEST,
        "target_market_snapshot_id": SNAPSHOT_ID,
        "market_snapshot_id": snapshot["target_market_snapshot_id"],
        "market_reference_values": market_reference_values,
        "market_reference_one_session_output_digest": reference["horizons"]["1"]["output_digest"],
        "market_reference_canonical_identity": exact["r4_1_candidate_receipt_identities"]["MARKET_REFERENCE"]["canonical_json_sha256"],
        "market_regime_trend_axis": market_regime["target_row"]["trend_axis"],
        "target_identity_count": candidate_manifest["business_state"]["target_identities"],
        "evidence_bindings": evidence_bindings,
        "stage_record": {
            "stage_contract": "V4_05_ACCEPTED_HEAD_PROMOTION_V4_06_ENTRY_TASK_20260929",
            "acceptance_result": "DATA_FACTOR_REPLAY_DEGRADED_PASS / EXTERNALLY_ACCEPTED",
            "evidence": "External R4.2 acceptance; exact R4.1 PostgreSQL ledger identity; hash, determinism, LFS restore and clean-checkout evidence.",
            "next_stage": "V4-06 Supplemental Enrichment entry authorized after independent promotion validation",
        },
        "next_stage": "V4-06_SUPPLEMENTAL_ENRICHMENT_ENTRY_AFTER_PROMOTION_VALIDATION",
    }

    accepted_bytes = (json.dumps(accepted, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    accepted_binding = {"path": ACCEPTED_HEAD, "sha256": sha256(accepted_bytes).hexdigest(),
                        "byte_count": len(accepted_bytes)}
    updated_global = dict(detail["baseline_global_head"])
    updated_global.update({
        "accepted_stage_range": "V4_00_TO_V4_05_ACCEPTED",
        "v4_05_entry": "COMPLETED_EXTERNALLY_ACCEPTED",
        "v4_05_status": "DATA_FACTOR_REPLAY_DEGRADED_PASS",
        "v4_05_external_acceptance": "EXTERNALLY_ACCEPTED",
        "v4_05_binding": accepted_binding,
        "version": "2.3.0",
    })

    # Prepare both files first; each replacement is atomic and contains no business rebuild.
    accepted_temp = accepted_path.with_suffix(".json.tmp")
    global_temp = global_path.with_suffix(".json.tmp")
    accepted_path.parent.mkdir(parents=True, exist_ok=True)
    accepted_temp.write_bytes(accepted_bytes)
    global_temp.write_bytes((json.dumps(updated_global, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    os.replace(accepted_temp, accepted_path)
    os.replace(global_temp, global_path)
    return {"status": "PROMOTED_PENDING_V4_06_ENTRY_VALIDATION", "accepted_head": file_identity(ACCEPTED_HEAD),
            "global_head": file_identity(GLOBAL_HEAD), "v4_06_entry": "NOT_YET_AUTHORIZED"}


if __name__ == "__main__":
    print(json.dumps(promote(), ensure_ascii=False, sort_keys=True))
