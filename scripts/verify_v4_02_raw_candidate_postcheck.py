from __future__ import annotations

"""Independent metadata, row and bounded source-sample postcheck for V4-02 RAW."""

import argparse
import hashlib
import json
import os
import struct
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
DAY_STRUCT = struct.Struct("<IIIII f II")
SAMPLE_INDICES = {0, 1, 2, 17, 101, 1001, 10001, 50001, 100001}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def row_source_root(family: str, package_root: Path, local_root: Path) -> Path:
    if family == "TDX_COMPLETE_PACKAGE":
        return package_root
    if family == "TDX_LOCAL_CURRENT_CHAIN":
        return local_root
    raise ValueError(f"UNKNOWN_SOURCE_FAMILY:{family}")


def verify_source_sample(row: dict, package_root: Path, local_root: Path, verified_files: dict[str, str]) -> dict:
    relative = row["source_relative_path"]
    source_root = row_source_root(row["selected_source_family"], package_root, local_root)
    path = source_root / relative
    actual_file_hash = verified_files.get(str(path))
    if actual_file_hash is None:
        actual_file_hash = sha256_file(path)
        verified_files[str(path)] = actual_file_hash
    if actual_file_hash != row["source_file_sha256"]:
        raise ValueError(f"SOURCE_SAMPLE_FILE_HASH_MISMATCH:{relative}")
    ordinal = int(row["source_record_ordinal"])
    with path.open("rb") as stream:
        stream.seek(ordinal * DAY_STRUCT.size)
        record = stream.read(DAY_STRUCT.size)
    if len(record) != DAY_STRUCT.size:
        raise ValueError(f"SOURCE_SAMPLE_ORDINAL_OUT_OF_RANGE:{relative}:{ordinal}")
    values = DAY_STRUCT.unpack(record)
    expected_values = (
        int(row["trade_date"]),
        int(row["open_price_raw"]),
        int(row["high_price_raw"]),
        int(row["low_price_raw"]),
        int(row["close_price_raw"]),
        float(row["amount_source_native"]),
        int(row["volume_source_native"]),
        int(row["reserved_raw"]),
    )
    if values != expected_values:
        raise ValueError(f"SOURCE_SAMPLE_VALUE_MISMATCH:{relative}:{ordinal}")
    alternative_hash = row.get("alternative_record_sha256")
    if alternative_hash:
        alternative_family = row["alternative_source_family"]
        alternative_root = row_source_root(alternative_family, package_root, local_root)
        alternative_path = alternative_root / relative
        data = alternative_path.read_bytes()
        if len(data) % DAY_STRUCT.size:
            raise ValueError(f"ALTERNATIVE_SOURCE_RECORD_SIZE_INVALID:{relative}")
        target_date = int(row["trade_date"])
        found = None
        for offset in range(0, len(data), DAY_STRUCT.size):
            if DAY_STRUCT.unpack_from(data, offset)[0] == target_date:
                found = data[offset : offset + DAY_STRUCT.size]
                break
        if found is None or hashlib.sha256(found).hexdigest() != alternative_hash:
            raise ValueError(f"ALTERNATIVE_SAMPLE_DIGEST_MISMATCH:{relative}:{target_date}")
    return {
        "source_security_key": row["source_security_key"],
        "trade_date": int(row["trade_date"]),
        "selected_source_family": row["selected_source_family"],
        "source_file_sha256": actual_file_hash,
        "source_record_ordinal": ordinal,
        "alternative_checked": bool(alternative_hash),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    run_id = args.run_id
    run_dir = ROOT / "data/v4/canonical" / run_id
    receipt_path = run_dir / "stage_receipt.json"
    manifest_path = run_dir / "source_manifest.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if receipt.get("run_id") != run_id or manifest.get("run_id") != run_id:
        raise ValueError("RUN_ID_BINDING_MISMATCH")
    descriptor = receipt["outputs"]["canonical_daily_raw_selected"]
    parquet_path = run_dir / descriptor["path"]
    parquet = pq.ParquetFile(parquet_path)
    expected_fields = descriptor["schema"]
    if parquet.schema_arrow.names != expected_fields:
        raise ValueError("PARQUET_SCHEMA_MISMATCH")
    if parquet.metadata.num_rows != descriptor["row_count"]:
        raise ValueError("PARQUET_METADATA_ROW_COUNT_MISMATCH")
    if parquet_path.stat().st_size != descriptor["byte_count"] or sha256_file(parquet_path) != descriptor["sha256"]:
        raise ValueError("PARQUET_SIZE_OR_HASH_MISMATCH")
    if sha256_file(manifest_path) != receipt["source_manifest"]["sha256"]:
        raise ValueError("SOURCE_MANIFEST_HASH_MISMATCH")

    contract = json.loads((ROOT / "config/v4_02_canonical_daily_pit_contract_v1.json").read_text(encoding="utf-8"))
    bundle = json.loads((ROOT / "data/source_bundles/6122afa9db83170f7b442d5ecc5c7c9287b9dd6b04c4d53729d55f71f7dd99d2/source_bundle.json").read_text(encoding="utf-8"))
    package_root = ROOT / bundle["extraction"]["root"]
    local_root = ROOT / "data/v4/local_tdx_snapshots/1644752b002fdeb4f3d3a2968b9c77729f27efcdae8923ad14d814abe5c78c70"

    row_count = 0
    max_trade_date = 0
    source_families: Counter[str] = Counter()
    board_counts: Counter[str] = Counter()
    identity_null_rows = 0
    identity_observed_rows = 0
    unknown_limit_rows = 0
    raw_rows = 0
    diagnostic_lineage_rows = 0
    bse_rows_emitted = 0
    quality_counts: Counter[str] = Counter()
    sample_rows: list[dict] = []
    alternative_sample_rows: list[dict] = []
    global_index = 0
    for batch in parquet.iter_batches(
        batch_size=250_000,
        columns=[
            "canonical_security_id", "source_security_key", "board_scope", "trade_date",
            "source_file_sha256", "source_record_ordinal", "selected_source_family",
            "alternative_source_family", "alternative_record_sha256", "open_price_raw",
            "high_price_raw", "low_price_raw", "close_price_raw", "amount_source_native",
            "volume_source_native", "reserved_raw", "identity_quality", "limit_status",
            "adjustment_view", "knowledge_lineage", "record_quality", "source_relative_path",
        ],
    ):
        row_count += batch.num_rows
        values = batch.to_pydict()
        if values["trade_date"]:
            max_trade_date = max(max_trade_date, max(values["trade_date"]))
        source_families.update(value for value in values["selected_source_family"] if value)
        board_counts.update(value for value in values["board_scope"] if value)
        bse_rows_emitted += sum(key.startswith("BJ.") for key in values["source_security_key"])
        identity_null_rows += sum(value is None for value in values["canonical_security_id"])
        identity_observed_rows += sum(value == "R6_2_DATED_ROSTER_OBSERVED" for value in values["identity_quality"])
        unknown_limit_rows += sum(value == "UNKNOWN" for value in values["limit_status"])
        raw_rows += sum(value == "RAW" for value in values["adjustment_view"])
        diagnostic_lineage_rows += sum(value == "DIAGNOSTIC_NON_PIT" for value in values["knowledge_lineage"])
        quality_counts.update(value for value in values["record_quality"] if value)
        for index in range(batch.num_rows):
            if global_index in SAMPLE_INDICES:
                sample_rows.append({name: values[name][index] for name in values})
            if values["alternative_record_sha256"][index] and len(alternative_sample_rows) < 3:
                alternative_sample_rows.append({name: values[name][index] for name in values})
            global_index += 1

    if row_count != int(manifest["required_scope_emitted_rows"]) or row_count != int(receipt["row_counts"]["raw_daily_rows_at_asof"]):
        raise ValueError("SOURCE_SELECTION_TO_PARQUET_ROW_COUNT_MISMATCH")
    if max_trade_date > int(manifest["asof_trade_date"]):
        raise ValueError("FUTURE_ROW_AFTER_ASOF")
    if identity_null_rows + identity_observed_rows != row_count:
        raise ValueError("IDENTITY_QUALITY_COUNT_MISMATCH")
    if unknown_limit_rows != row_count or raw_rows != row_count or diagnostic_lineage_rows != row_count:
        raise ValueError("FAIL_CLOSED_QUALITY_MARKER_MISMATCH")

    verified_files: dict[str, str] = {}
    checked_samples = [verify_source_sample(row, package_root, local_root, verified_files) for row in sample_rows + alternative_sample_rows]
    checks = {
        "receipt_manifest_run_identity": True,
        "parquet_schema_hash_size_and_rows": True,
        "source_selection_required_scope_row_count_matches": row_count == manifest["required_scope_emitted_rows"],
        "optional_bse_excluded_from_required_output": bse_rows_emitted == 0 and int(manifest["optional_bse_degraded_rows_excluded"]) > 0,
        "asof_future_row_exclusion": max_trade_date <= int(manifest["asof_trade_date"]),
        "identity_and_quality_markers_consistent": identity_null_rows + identity_observed_rows == row_count,
        "raw_non_pit_and_unknown_limit_fail_closed": unknown_limit_rows == row_count and raw_rows == row_count and diagnostic_lineage_rows == row_count,
        "bounded_source_record_samples_match": len(checked_samples) == len(sample_rows) + len(alternative_sample_rows) and bool(checked_samples),
    }
    # Compare the digest value directly to the source manifest on disk.
    selection_manifest = ROOT / manifest["source_selection_manifest_path"] if manifest.get("source_selection_manifest_path") else ROOT / contract["inputs"]["canonical_source_selection"]
    checks["source_selection_manifest_digest_bound"] = sha256_file(selection_manifest) == manifest["source_selection_manifest_sha256"]
    status = "CANDIDATE_POSTCHECK_PASS" if all(checks.values()) else "CANDIDATE_POSTCHECK_BLOCKED"
    result = {
        "contract_id": "V4_02_RAW_CANDIDATE_INDEPENDENT_POSTCHECK_V1",
        "version": "1.0.0",
        "run_id": run_id,
        "stage": "V4-02",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "independent_postcheck_status": status,
        "stage_acceptance_status": receipt.get("status"),
        "stage_completion_authorized": receipt.get("stage_completion_authorized"),
        "input_receipt_sha256": sha256_file(receipt_path),
        "input_source_manifest_sha256": sha256_file(manifest_path),
        "checks": checks,
        "summary": {
            "row_count": row_count,
            "max_trade_date": max_trade_date,
            "source_family_counts": dict(source_families),
            "board_scope_counts": dict(board_counts),
            "bse_rows_emitted": bse_rows_emitted,
            "optional_bse_degraded_rows_excluded": int(manifest["optional_bse_degraded_rows_excluded"]),
            "identity_null_rows": identity_null_rows,
            "identity_roster_observed_rows": identity_observed_rows,
            "unknown_limit_rows": unknown_limit_rows,
            "raw_rows": raw_rows,
            "diagnostic_non_pit_rows": diagnostic_lineage_rows,
            "record_quality_counts": dict(quality_counts),
        },
        "bounded_source_samples": checked_samples,
        "note": "Postcheck accepts only the source-selected RAW candidate artifact integrity. It does not accept V4-02 capabilities or change the stage BLOCKED status.",
    }
    report_path = ROOT / f"reports/v4_02/{run_id}_independent_postcheck.json"
    atomic_json(report_path, result)
    print(json.dumps({"report": report_path.relative_to(ROOT).as_posix(), "status": status, "checks_passed": sum(checks.values()), "checks_total": len(checks), "rows": row_count}, ensure_ascii=False))
    return 0 if status == "CANDIDATE_POSTCHECK_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
