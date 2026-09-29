from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.v4.base_seed import run_accepted_candidate, unknown_reason_inventory  # noqa: E402


def atomic_json(path: Path, payload: object) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the frozen V4-07 BASE_SEED_V1 candidate over accepted V4-05 Core inputs.")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/v4_07/staging/V4_07_BASE_SEED_CANDIDATE_R1.jsonl.gz")
    parser.add_argument("--created-at", help="Explicit UTC timestamp for deterministic replay evidence only.")
    parser.add_argument("--receipt", type=Path, default=ROOT / "reports/v4_07/V4_07_FULL_MARKET_CANDIDATE_RECEIPT.json")
    parser.add_argument(
        "--accepted-inputs-root",
        type=Path,
        default=Path(os.environ["V4_07_ACCEPTED_INPUTS_ROOT"]) if os.environ.get("V4_07_ACCEPTED_INPUTS_ROOT") else None,
        help="Optional read-only repository root holding the accepted V4-05 head and evidence inputs.",
    )
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    receipt_path = args.receipt if args.receipt.is_absolute() else ROOT / args.receipt

    stamp = args.created_at or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    result = run_accepted_candidate(ROOT, output, created_at=stamp, accepted_inputs_root=args.accepted_inputs_root)
    receipt = {
        "contract_id": "V4_07_FULL_MARKET_CANDIDATE_RECEIPT_V1",
        "stage_contract": "V4_06_R2_CONTRACT_REPAIR_AND_V4_07_BASE_SEED_STAGE_TASK_20260929",
        "candidate_status": "V4_07_ENGINEERING_CANDIDATE_PENDING_GATES",
        "target_trade_date": "2026-09-28",
        "publication_id": "PUB-3c03e227-c60a-4d8c-86ae-2861507c257b",
        "source_core_logical_digest": "d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74",
        "accepted_identity_count": 5222,
        "accepted_inputs_root": str(args.accepted_inputs_root.resolve()) if args.accepted_inputs_root else "stage_repository_root",
        "row_count": result["row_count"],
        "artifact_path": output.relative_to(ROOT).as_posix() if output.is_relative_to(ROOT) else str(output),
        "artifact_sha256": result["artifact_sha256"],
        "logical_artifact_digest": result["logical_digest"],
        "source_bindings": result["source_bindings"],
        "board_counts": result["board_counts"],
        "state_counts": result["state_counts"],
        "state_counts_by_board": result["state_counts_by_board"],
        "participation_annotation_counts": result["participation_annotation_counts"],
        "unknown_quality_inventory": result["unknown_reason_inventory"],
        "created_at": stamp,
        "created_at_excluded_from_logical_digest": True,
        "acceptance_gates": {
            "contract_freeze": "PASS_CONTRACT_FREEZE_CANDIDATE",
            "machine_vector_runtime": "PENDING",
            "independent_postcheck": "PENDING",
            "supplemental_isolation": "PENDING",
            "determinism": "PENDING",
            "postgres_migration_and_rollback": "PENDING",
            "regression_gate": "PENDING"
        },
        "next_stage": "V4_07_INDEPENDENT_POSTCHECK_ISOLATION_DETERMINISM_AND_PERSISTENCE_GATES"
    }
    atomic_json(receipt_path, receipt)
    print(json.dumps({
        "status": "OUTPUT_GENERATED_GATES_PENDING",
        "row_count": result["row_count"],
        "state_counts": result["state_counts"],
        "state_counts_by_board": result["state_counts_by_board"],
        "logical_artifact_digest": result["logical_digest"],
        "artifact_sha256": result["artifact_sha256"],
        "receipt": str(receipt_path)
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
