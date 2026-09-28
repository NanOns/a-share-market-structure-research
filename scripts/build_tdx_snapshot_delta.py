from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.daily_data_head import write_json_atomic  # noqa: E402
from workbench_analysis.daily_increment_builder import build_raw_increment_staging  # noqa: E402
from workbench_analysis.tdx_snapshot_delta import build_tdx_package_delta  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the changed-file delta from two immutable official TDX snapshots.")
    parser.add_argument("--target-date", required=True)
    parser.add_argument("--current-snapshot-id", required=True)
    parser.add_argument("--parent-zip", type=Path, default=ROOT / "data/v4/raw_archive/b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f/hsjday.zip")
    parser.add_argument("--parent-snapshot-id", default="sha256-b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f")
    parser.add_argument("--snapshot-root", type=Path, default=ROOT / "data/v4/source_snapshots")
    parser.add_argument("--tdx-root", type=Path, default=Path("D:/new_tdx"))
    args = parser.parse_args()
    if not args.current_snapshot_id.startswith("sha256-"):
        raise SystemExit("CURRENT_SNAPSHOT_ID_MUST_BE_CONTENT_ADDRESSED")
    current_zip = args.snapshot_root / "tdx" / args.target_date.replace("-", "") / args.current_snapshot_id / "hsjday.zip"
    expected_current_sha = args.current_snapshot_id.removeprefix("sha256-")
    expected_parent_sha = args.parent_snapshot_id.removeprefix("sha256-")
    if not current_zip.is_file() or sha256(current_zip) != expected_current_sha:
        raise SystemExit("CURRENT_TDX_SNAPSHOT_HASH_MISMATCH")
    if not args.parent_zip.is_file() or sha256(args.parent_zip) != expected_parent_sha:
        raise SystemExit("PARENT_TDX_SNAPSHOT_HASH_MISMATCH")
    delta = build_tdx_package_delta(
        parent_zip=args.parent_zip,
        current_zip=current_zip,
        target_date=args.target_date,
        parent_snapshot_id=args.parent_snapshot_id,
        current_snapshot_id=args.current_snapshot_id,
    )
    delta_dir = current_zip.parent / "delta" / args.target_date.replace("-", "")
    delta_path = delta_dir / f"TDX_PACKAGE_DELTA_{args.target_date.replace('-', '')}.json"
    delta_sha = write_json_atomic(delta_path, delta, tdx_root=args.tdx_root)
    raw_path = delta_dir / f"RAW_DAILY_INCREMENT_{args.target_date.replace('-', '')}.jsonl"
    raw = build_raw_increment_staging(
        trade_date=args.target_date,
        source_snapshot_id=args.current_snapshot_id,
        delta=delta,
        output_path=raw_path,
        tdx_root=args.tdx_root,
    )
    summary = {
        "contract_id": "V4_DM01_TDX_DELTA_BUILD_RECEIPT_V1",
        "target_date": args.target_date,
        "status": delta["status"],
        "parent_snapshot_id": args.parent_snapshot_id,
        "current_snapshot_id": args.current_snapshot_id,
        "delta_path": str(delta_path.resolve()),
        "delta_sha256": delta_sha,
        "raw_increment": raw,
        "tdx_root_write_count": 0,
    }
    receipt_path = delta_dir / "tdx_delta_build_receipt.json"
    receipt_sha = write_json_atomic(receipt_path, summary, tdx_root=args.tdx_root)
    print(json.dumps({"status": summary["status"], "target_bar_count": delta["target_bar_count"],
                      "revision_events": len(delta["revision_events"]), "delta_path": str(delta_path),
                      "delta_sha256": delta_sha, "receipt": str(receipt_path), "receipt_sha256": receipt_sha},
                     ensure_ascii=False))
    return 0 if delta["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
