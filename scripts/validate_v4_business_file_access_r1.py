"""Fail closed if the business-code file-access inventory is incomplete or misclassified."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def validate(path: Path, root: Path) -> dict:
    inventory = json.loads(path.read_text(encoding="utf-8"))
    expected_head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"]).decode().strip()
    if inventory.get("contract_id") != "V4_BUSINESS_CODE_FILE_ACCESS_AUDIT_R1":
        raise ValueError("BUSINESS_FILE_ACCESS_CONTRACT_MISMATCH")
    if inventory.get("git_head") != expected_head:
        raise ValueError("BUSINESS_FILE_ACCESS_HEAD_MISMATCH")
    rows = inventory.get("rows")
    if not isinstance(rows, list):
        raise ValueError("BUSINESS_FILE_ACCESS_ROWS_MISSING")
    scanned_files = inventory.get("scanned_files")
    if not isinstance(scanned_files, list) or len(scanned_files) != inventory.get("tracked_code_file_count"):
        raise ValueError("BUSINESS_FILE_ACCESS_FILE_COVERAGE_MISMATCH")
    for item in scanned_files:
        rel = item.get("path")
        if not isinstance(rel, str) or Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise ValueError("BUSINESS_FILE_ACCESS_SOURCE_PATH_INVALID")
        source = (root / rel).resolve()
        if not source.is_relative_to(root.resolve()) or not source.is_file():
            raise ValueError("BUSINESS_FILE_ACCESS_SOURCE_MISSING")
        if hashlib.sha256(source.read_bytes()).hexdigest() != item.get("sha256"):
            raise ValueError("BUSINESS_FILE_ACCESS_SOURCE_HASH_MISMATCH")
    accesses = [row for row in rows if row.get("kind") == "FILE_ACCESS"]
    if len(accesses) != inventory.get("file_access_call_count"):
        raise ValueError("BUSINESS_FILE_ACCESS_COUNT_MISMATCH")
    for row in accesses:
        if row.get("category") == "OWNER_GOVERNED_READ":
            raise ValueError("OWNER_FILE_READ_MUST_NOT_BE_EXEMPT")
        if row.get("category") in {"BUSINESS_OWNER_FILE_READ_REQUIRES_DB", "BUSINESS_FILE_READ_REQUIRES_DB", "BUSINESS_FILE_WRITE_REQUIRES_DB", "EXTERNAL_BUSINESS_DATA_FILE_READ_REQUIRES_DB"} and row.get("priority") != "P1":
            raise ValueError("BUSINESS_FILE_ACCESS_MIGRATION_PRIORITY_MISMATCH")
        if len(row.get("source_sha256", "")) != 64:
            raise ValueError("BUSINESS_FILE_ACCESS_SOURCE_HASH_MISSING")
    return {"status": "PASS", "git_head": expected_head, "file_access_call_count": len(accesses),
            "p1_finding_count": sum(row.get("priority") == "P1" for row in rows),
            "owner_file_read_requires_db_count": sum(row.get("category") == "BUSINESS_OWNER_FILE_READ_REQUIRES_DB" for row in accesses),
            "source_file_count": len(scanned_files), "source_hashes_verified": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--inventory", required=True)
    args = parser.parse_args()
    result = validate(Path(args.inventory), Path(args.root).resolve())
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
