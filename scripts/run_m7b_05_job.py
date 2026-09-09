"""Submit and wait for one local HISTORY_ANALYSIS task."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_service.history_jobs import HistoryJobService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--database", default=None)
    parser.add_argument("--publication-id", required=True)
    parser.add_argument("--basis", default="RECONSTRUCTED", choices=("OBSERVED", "RECONSTRUCTED"))
    parser.add_argument("--output-days", type=int, default=30)
    parser.add_argument("--domain", action="append", required=True)
    parser.add_argument("--slice-id", action="append", default=[])
    parser.add_argument("--contract-bundle-id", default="workbench-contract-bundle-v2.1-preview")
    parser.add_argument("--idempotency-key", required=True)
    parser.add_argument("--receipt", default=None)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    service = HistoryJobService(root, args.database)
    request = {
        "base_publication_id": args.publication_id,
        "basis": args.basis,
        "output_days": args.output_days,
        "domains": args.domain,
        "contract_bundle_id": args.contract_bundle_id,
        "idempotency_key": args.idempotency_key,
        "slice_ids": args.slice_id,
    }
    result = service.submit(request)
    deadline = time.monotonic() + 30
    while result["status"] in {"QUEUED", "RUNNING", "INTERRUPTED"} and time.monotonic() < deadline:
        time.sleep(0.05)
        result = service.status(result["job_id"])
    if args.receipt:
        receipt_path = (root / args.receipt).resolve()
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt = {"contract_version": "history-job-receipt-v1.0", "step": "M7B-05", **result}
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{receipt_path.name}.", suffix=".tmp", dir=receipt_path.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            temporary.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            os.replace(temporary, receipt_path)
        finally:
            temporary.unlink(missing_ok=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
