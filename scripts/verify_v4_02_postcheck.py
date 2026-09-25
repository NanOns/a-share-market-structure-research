from __future__ import annotations

"""Independent, fail-closed postcheck for a V4-02 run and its input snapshot."""

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.tdx_snapshot import verify_zip_snapshot  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_inventory(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return {row["relative_path"]: row for row in csv.DictReader(stream)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="V4_02_CANONICAL_DAILY_PIT_20260924_085207Z")
    args = parser.parse_args()
    if not re.fullmatch(r"V4_02_CANONICAL_DAILY_PIT_[A-Za-z0-9_]+", args.run_id):
        raise ValueError("INVALID_RUN_ID")
    receipt_path = ROOT / "reports/v4_02" / f"{args.run_id}_stage_receipt.json"
    manifest_path = ROOT / "reports/v4_02" / f"{args.run_id}_source_manifest.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archive = ROOT / "data/v4/raw_archive/b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f/hsjday.zip"
    stage01_receipt_path = ROOT / "reports/v4_01/v4_01_stage_receipt_R2_20260925.json"
    stage01_manifest_path = ROOT / "reports/v4_01/v4_01_source_manifest_R2_20260925.json"
    stage01_inventory_path = ROOT / "reports/v4_01/v4_01_security_inventory_R2_20260925.csv"
    stage01_receipt = json.loads(stage01_receipt_path.read_text(encoding="utf-8"))
    stage01_manifest = json.loads(stage01_manifest_path.read_text(encoding="utf-8"))
    bundle = json.loads((ROOT / "data/source_bundles/6122afa9db83170f7b442d5ecc5c7c9287b9dd6b04c4d53729d55f71f7dd99d2/source_bundle.json").read_text(encoding="utf-8"))
    snapshot = verify_zip_snapshot(
        archive,
        ROOT / bundle["extraction"]["root"],
        load_inventory(stage01_inventory_path),
        int(bundle["extraction"]["entry_count"]),
        stage01_manifest["source"]["extracted_content_digest"],
    )
    checks: dict[str, bool] = {
        "archive_identity_matches_v4_01": snapshot["archive_sha256"] == receipt.get("entry_gate", {}).get("raw_archive_sha256"),
        "zip_to_extraction_snapshot_verified": snapshot["status"] == "PASS",
        "v4_01_receipt_manifest_hash_bound": stage01_receipt.get("evidence", {}).get("source_manifest_sha256") == sha256_file(stage01_manifest_path),
        "v4_02_manifest_binds_its_receipt": manifest.get("receipt_sha256") == sha256_file(receipt_path),
        "v4_02_receipt_full_pass": receipt.get("status") == "FULL_PASS",
        "v4_01_entry_gate_full_pass": receipt.get("entry_gate", {}).get("v4_01") == "FULL_PASS",
        "source_manifest_uses_r2_snapshot": manifest.get("extracted_snapshot_verification", {}).get("content_digest") == snapshot["content_digest"],
    }
    output_checks: dict[str, dict] = {}
    required_daily_fields = {"canonical_security_id", "source_security_key", "trade_date_raw", "record_quality"}
    for name, descriptor in receipt.get("outputs", {}).items():
        path = (ROOT / descriptor["path"]).resolve()
        if ROOT.resolve() not in path.parents:
            raise ValueError("OUTPUT_PATH_ESCAPES_PROJECT_ROOT")
        parquet = pq.ParquetFile(path)
        output_checks[name] = {
            "exists": path.is_file(),
            "byte_count_matches": path.stat().st_size == descriptor["byte_count"],
            "sha256_matches": sha256_file(path) == descriptor["sha256"],
            "row_count_matches": parquet.metadata.num_rows == descriptor["row_count"],
            "row_count": parquet.metadata.num_rows,
            "schema_fields": parquet.schema_arrow.names,
        }
        if name == "canonical_daily_raw":
            output_checks[name]["source_and_canonical_identity_separate"] = required_daily_fields.issubset(parquet.schema_arrow.names)
    checks["all_output_metadata_and_hashes_match"] = bool(output_checks) and all(
        all(value for key, value in row.items() if key in {"exists", "byte_count_matches", "sha256_matches", "row_count_matches"})
        for row in output_checks.values()
    )
    checks["canonical_identity_columns_present"] = output_checks.get("canonical_daily_raw", {}).get("source_and_canonical_identity_separate", False)
    status = "FULL_PASS" if all(checks.values()) else "SUPERSEDED_CANDIDATE"
    report = {
        "audit_id": "V4_01_02_R2_POSTCHECK_V1",
        "run_id": args.run_id,
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "prior_stage_receipt_preserved": True,
        "prior_run_disposition": "SUPERSEDED_CANDIDATE" if status != "FULL_PASS" else "R2_POSTCHECKED",
        "snapshot_verification": snapshot,
        "checks": checks,
        "output_checks": output_checks,
        "stage01_receipt_sha256": sha256_file(stage01_receipt_path),
        "stage01_source_manifest_sha256": sha256_file(stage01_manifest_path),
        "v4_02_receipt_sha256": sha256_file(receipt_path),
        "v4_02_source_manifest_sha256": sha256_file(manifest_path),
        "current_code_commit": __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "current_postcheck_script_sha256": sha256_file(Path(__file__).resolve()),
        "acceptance": "Old artifacts are retained as historical candidate evidence. R2 completion remains blocked unless every listed check passes and the independent online acceptance accepts the submitted code/artifacts.",
        "tdx_root_read_count": 0,
        "tdx_root_write_count": 0,
    }
    target = ROOT / "reports/v4_02" / f"{args.run_id}_r2_postcheck.json"
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)
    print(json.dumps({"status": status, "checks": checks, "report": str(target.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if status == "FULL_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
