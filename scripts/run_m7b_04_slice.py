"""Run a small M7B-04 historical slice coordination sample."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_service.slice_coordinator import SliceCoordinator, iter_security_batches  # noqa: E402
from workbench_service.source_freezer import verify_source_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--database", default=None)
    parser.add_argument("--source-manifest", required=True)
    parser.add_argument("--input", default="data/normalized/adjusted_daily.parquet")
    parser.add_argument("--trade-date", required=True)
    parser.add_argument("--security-id", action="append", required=True)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--receipt", default=None)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    manifest_path = (root / args.source_manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verification = verify_source_manifest(root, manifest)
    if verification["status"] != "PASS":
        raise RuntimeError("SOURCE_MANIFEST_VERIFICATION_FAILED")
    manifest_hash = manifest["manifest_sha256"]
    coordinator = SliceCoordinator(root, args.database)
    results = []
    for batch in iter_security_batches(root / args.input, trade_date=args.trade_date, security_ids=args.security_id, batch_size=args.batch_size):
        basis = {
            "source_manifest_sha256": manifest_hash,
            "source_bundle_id": manifest["source_bundle_id"],
            "source_identity_sha256": manifest["source_identity_sha256"],
            "universe_basis": "CURRENT_SNAPSHOT_ONLY",
            "pit_safe": False,
            "daily_basis": {
                "universe_basis": "CURRENT_SNAPSHOT_ONLY",
                "membership_snapshot_id": None,
                "price_basis": "FORWARD_ADJUSTED",
                "adjustment_as_of": manifest["cutoff_date"],
                "source_observed_at": manifest["observed_at"],
                "coverage": 1.0,
                "capabilities_json": {"quote_input": "OBSERVED", "membership": "CURRENT_SNAPSHOT_ONLY"},
            },
        }
        results.append(coordinator.coordinate(domain="quote_input", trade_date=args.trade_date, contract_id="history-quote-input-v1.0", rows=batch["rows"], basis=basis))
    if not results:
        raise RuntimeError("SECURITY_BATCH_EMPTY")
    receipt = {"contract_version": "history-slice-coordination-receipt-v1.0", "step": "M7B-04", "source_manifest_sha256": manifest_hash, "trade_date": args.trade_date, "items": results}
    if args.receipt:
        receipt_path = (root / args.receipt).resolve()
        receipt["receipt_path"] = receipt_path.relative_to(root).as_posix()
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{receipt_path.name}.", suffix=".tmp", dir=receipt_path.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            temporary.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            os.replace(temporary, receipt_path)
        finally:
            temporary.unlink(missing_ok=True)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
