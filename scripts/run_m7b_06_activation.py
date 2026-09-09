"""Activate one prepared HISTORY_ANALYSIS job as a new publication revision."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_service.analysis_activation import AnalysisActivationService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--database", default=None)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--expected-head-id", required=True)
    parser.add_argument("--idempotency-key", required=True)
    parser.add_argument("--receipt", default=None)
    args = parser.parse_args()
    result = AnalysisActivationService(args.root, args.database).activate(args.job_id, expected_head_id=args.expected_head_id, idempotency_key=args.idempotency_key)
    if args.receipt:
        path = (Path(args.root).resolve() / args.receipt).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            temporary.write_text(json.dumps({"contract_version": "history-activation-receipt-v1.0", "step": "M7B-06", **result}, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
