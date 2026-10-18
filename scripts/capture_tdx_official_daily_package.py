from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.tdx_official_daily_source import capture_tdx_official_daily_package  # noqa: E402


def _ingest_capture_evidence(result: dict, *, root: Path = ROOT) -> dict:
    """Ingress bounded TDX page metadata and receipt before returning to orchestration."""
    from workbench_db.v4_historical_source_ingress_pg_r1 import ingest_captured_bytes, read_bound

    receipt_path = Path(str(result.get("receipt_path") or "")).resolve()
    capture_id = receipt_path.parent.name
    target_date = str(result.get("target_date") or "")
    if not capture_id.startswith("capture-") or not target_date:
        raise ValueError("TDX_CAPTURE_RECEIPT_IDENTITY_REQUIRED")
    bindings = {}
    for name, path_key, digest_key, origin in (
        ("page.html", "page_html_path", "page_sha256", "TDX_OFFICIAL_DAILY_PAGE_CAPTURE"),
        ("update_info.js", "update_info_path", "update_info_sha256", "TDX_OFFICIAL_DAILY_UPDATE_INFO_CAPTURE"),
        ("capture_receipt.json", None, None, "TDX_OFFICIAL_DAILY_CAPTURE_RECEIPT"),
    ):
        source_path = receipt_path if name == "capture_receipt.json" else Path(str(result.get(path_key) or "")).resolve()
        raw = source_path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        expected = result.get(digest_key) if digest_key else sha
        if sha != expected:
            raise ValueError("TDX_CAPTURE_EVIDENCE_DIGEST_MISMATCH:" + name)
        logical_path = f"external/tdx_daily_capture/{target_date}/{capture_id}/{name}"
        ingest_captured_bytes(root, logical_path, raw, source_revision=sha, source_origin=origin)
        exact = read_bound(root, logical_path, sha)
        if (exact["raw"] != raw or exact["record"].get("source_bytes") != len(raw)):
            raise ValueError("TDX_CAPTURE_EVIDENCE_PG_READBACK_MISMATCH:" + name)
        bindings[name] = dict(path=logical_path, sha256=sha, bytes=len(raw))
    return bindings


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture the official TDX daily page and validated package if published.")
    parser.add_argument("--target-date", default=datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat())
    parser.add_argument("--snapshot-root", type=Path, default=None,
                        help="Override TDX_SNAPSHOT_ROOT/config/paths.yaml")
    parser.add_argument("--daily-download-root", type=Path, default=None,
                        help="Override TDX_DAILY_DOWNLOAD_ROOT/config/paths.yaml")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    try:
        result = capture_tdx_official_daily_package(
            target_date=args.target_date,
            snapshot_root=args.snapshot_root,
            daily_download_root=args.daily_download_root,
            timeout=args.timeout,
        )
        result["pg_source_bindings"] = _ingest_capture_evidence(result)
        print(json.dumps({
            "status": result["status"],
            "target_date": result["target_date"],
            "update_date": result["update_date"],
            "page_sha256": result["page_sha256"],
            "update_info_sha256": result["update_info_sha256"],
            "snapshot_id": result["snapshot_id"],
            "receipt_path": result["receipt_path"],
            "pg_source_bindings": result["pg_source_bindings"],
        }, ensure_ascii=False))
        return 0 if result["status"] in {"WAIT_TDX_PUBLICATION", "TDX_PACKAGE_READY", "NOOP_SOURCE_ALREADY_FROZEN"} else 2
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED_TDX_SOURCE_CAPTURE", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
