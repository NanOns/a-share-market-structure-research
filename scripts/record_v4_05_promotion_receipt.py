"""Write the final promotion receipt and stage record after independent validation."""
from __future__ import annotations

import json
import os
from pathlib import Path

from v4_05_promotion_contract import (
    ACCEPTED_HEAD, CANDIDATE, DECISION, EXTERNAL_ACCEPTANCE, GLOBAL_HEAD,
    HISTORICAL_BLOCK, PROMOTION_PREFLIGHT, PROMOTION_RECEIPT, PROMOTION_TASK, PROMOTION_VALIDATION,
    ROOT, atomic_json, file_identity, load_json, validate,
)

STAGE_RECORD = "docs/evidence/V4_05_ACCEPTED_HEAD_PROMOTION_AND_V4_06_ENTRY_20260929.md"


def atomic_text(relative: str, value: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(value.encode("utf-8"))
    os.replace(temp, path)


def record() -> dict:
    validation_path = ROOT / PROMOTION_VALIDATION
    if not validation_path.is_file():
        raise ValueError("final independent promotion validation is missing")
    validation = load_json(PROMOTION_VALIDATION)
    current = validate("final")
    if (validation.get("status") != "PASS" or validation.get("phase") != "final" or
            not all(validation.get("checks", {}).values()) or current["status"] != "PASS" or
            validation.get("accepted_head") != current.get("accepted_head") or
            validation.get("global_head") != current.get("global_head")):
        raise ValueError("final independent promotion validation is stale or failed")
    preflight = load_json(PROMOTION_PREFLIGHT)
    if preflight.get("status") != "PASS" or preflight.get("phase") != "pre-entry":
        raise ValueError("promotion pre-entry validation is missing or failed")

    receipt = {
        "contract_id": "V4_05_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1",
        "status": "PASS",
        "external_acceptance_decision": DECISION,
        "accepted_candidate": CANDIDATE,
        "accepted_head": file_identity(ACCEPTED_HEAD),
        "global_head": file_identity(GLOBAL_HEAD),
        "promotion_preflight_validation": file_identity(PROMOTION_PREFLIGHT),
        "final_independent_validation": file_identity(PROMOTION_VALIDATION),
        "promotion_task": file_identity(PROMOTION_TASK),
        "external_acceptance_evidence": file_identity(EXTERNAL_ACCEPTANCE),
        "accepted_artifacts": validation["accepted_artifacts"],
        "exact_candidate_ledger_binding": validation["exact_candidate_ledger_binding"],
        "checks": validation["checks"],
        "terminal_state": {
            "v4_05": "EXTERNALLY_ACCEPTED",
            "data_factor_replay_pass": "DEGRADED_PASS_CURRENT_FORWARD_SCOPE",
            "v4_06_entry": "AUTHORIZED_SUPPLEMENTAL_ENRICHMENT",
            "v4_06_implementation": "NOT_STARTED",
            "v4_07": "NOT_STARTED",
            "v4_08": "BLOCKED",
        },
        "stage_record": {
            "stage_contract": "V4_05_ACCEPTED_HEAD_PROMOTION_V4_06_ENTRY_TASK_20260929",
            "acceptance_result": "V4_05_ACCEPTED_HEAD_PROMOTION_PASS_R1",
            "evidence": "Externally accepted R4.2 candidate promoted; independent validator passed all 12 requested checks; V4-06 entry authorization recorded without implementation.",
            "next_stage": "WAIT_FOR_NEXT_EXTERNAL_AUDIT",
        },
    }
    atomic_json(PROMOTION_RECEIPT, receipt)

    head = file_identity(ACCEPTED_HEAD)
    global_head = file_identity(GLOBAL_HEAD)
    validation_id = file_identity(PROMOTION_VALIDATION)
    stage_text = f"""# V4-05 Accepted Head Promotion and V4-06 Entry

Stage contract: `V4_05_ACCEPTED_HEAD_PROMOTION_V4_06_ENTRY_TASK_20260929`

Starting HEAD: `{validation['reviewed_starting_head']}`

External decision: `{DECISION}`

Terminal state: `V4_05_ACCEPTED_HEAD_PROMOTION_PASS_R1`

## Promotion

- Accepted candidate: `{CANDIDATE}`.
- V4-05 status: `DATA_FACTOR_REPLAY_DEGRADED_PASS` with the externally accepted current-forward capability scope.
- Historical as-recorded adjusted price remains `{HISTORICAL_BLOCK}`.
- V4-05 Accepted Head SHA-256: `{head['sha256']}` ({head['byte_count']} bytes).
- Global Accepted Head SHA-256: `{global_head['sha256']}` ({global_head['byte_count']} bytes); accepted range is `V4_00_TO_V4_05_ACCEPTED`.
- Exact R4.1 binding: `all_exact_bindings_match=true`; `old_r4_binding_count=0`; PostgreSQL state logical digest `{validation['exact_candidate_ledger_binding']['state_logical_digest']}`.

## Accepted capability scope

- `CURRENT_FORWARD_ADJUSTED_PRICE = FULL_PASS`
- `WEEKLY_PERIOD = DEGRADED_PASS`
- `MONTHLY_PERIOD = DEGRADED_PASS`
- `PURE_CORE_FACTORS = DEGRADED_PASS`
- `MARKET_REFERENCE = FULL_PASS`
- `MARKET_REGIME = DEGRADED_PASS`
- `CURRENT_FORWARD_STOCK_CORE = DEGRADED_PASS`
- `HISTORICAL_AS_RECORDED_ADJUSTED_PRICE = {HISTORICAL_BLOCK}`
- `DATA_FACTOR_REPLAY_PASS = DEGRADED_PASS` for the accepted current-forward scope.

## Independent validation and next-stage boundary

- Pre-entry promotion validation passed before V4-06 authorization.
- Final independent promotion validation: `{validation_id['sha256']}`; all requested promotion, capability, hash, LFS, Global Head, and successor-gate checks passed.
- V4-06 entry: `AUTHORIZED_SUPPLEMENTAL_ENRICHMENT`; V4-06 implementation: `NOT_STARTED`.
- V4-07: `NOT_STARTED`.
- V4-08: `BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION`.
- No V4-06 business artifacts were created. The next stage awaits the next external audit.

See [`V4_05_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json`](../../reports/v4_joint/V4_05_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json) and [`V4_05_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json`](../../reports/v4_joint/V4_05_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json).
"""
    atomic_text(STAGE_RECORD, stage_text)
    return {"status": receipt["status"], "accepted_head": head, "global_head": global_head,
            "validation": validation_id, "receipt": file_identity(PROMOTION_RECEIPT),
            "stage_record": file_identity(STAGE_RECORD)}


if __name__ == "__main__":
    print(json.dumps(record(), ensure_ascii=False, sort_keys=True))
