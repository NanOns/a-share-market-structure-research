from __future__ import annotations

"""Build V4-02 RAW canonical bars and diagnostic weekly/monthly periods.

Inputs are the hash-bound V4-01 TDX package extraction. The script never reads
or writes under a configured live TDX root. Every output is staged beside its
destination and atomically renamed on completion.
"""

import argparse
import csv
import hashlib
import json
import math
import os
import re
import struct
import sys
import subprocess
import tempfile
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.tdx_snapshot import verify_zip_snapshot  # noqa: E402

PACKAGE_SHA = "b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f"
SOURCE_BUNDLE_ID = "6122afa9db83170f7b442d5ecc5c7c9287b9dd6b04c4d53729d55f71f7dd99d2"
DAY_DTYPE = np.dtype(
    [
        ("trade_date", "<u4"),
        ("open_raw", "<u4"),
        ("high_raw", "<u4"),
        ("low_raw", "<u4"),
        ("close_raw", "<u4"),
        ("amount_source", "<f4"),
        ("volume_source", "<u4"),
        ("reserved", "<u4"),
    ]
)
DAY_BYTES = 32
DATE_STRUCT = struct.Struct("<I")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def staging_path(final_path: Path) -> Path:
    final_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=final_path.name + ".", suffix=".tmp", dir=final_path.parent)
    os.close(fd)
    return Path(temp_name)


def int_date(value: int) -> date | None:
    try:
        year, rem = divmod(int(value), 10000)
        month, day = divmod(rem, 100)
        return date(year, month, day)
    except (ValueError, OverflowError):
        return None


def security_identity(path: Path, extracted_root: Path) -> tuple[str | None, str, str]:
    rel = path.relative_to(extracted_root)
    market = rel.parts[0].upper() if rel.parts and rel.parts[0].lower() in {"sh", "sz", "bj"} else "UNKNOWN"
    match = re.fullmatch(r"(sh|sz|bj)(\d{6})", path.stem.lower())
    if not match:
        return None, market, path.stem[2:] if len(path.stem) > 2 else ""
    return f"{match.group(1).upper()}.{match.group(2)}", match.group(1).upper(), match.group(2)


def read_calendar(path: Path) -> list[int]:
    if not path.is_file() or path.stat().st_size % DAY_BYTES:
        return []
    raw = path.read_bytes()
    dates = []
    seen = set()
    for offset in range(0, len(raw), DAY_BYTES):
        value = DATE_STRUCT.unpack_from(raw, offset)[0]
        if int_date(value) is not None and value not in seen:
            dates.append(value)
            seen.add(value)
    return dates


def calendar_period_map(dates: list[int]) -> tuple[dict[int, dict], dict[str, dict]]:
    by_date: dict[int, dict] = {}
    periods: dict[str, dict] = {"WEEK": {}, "MONTH": {}}
    parsed = [(encoded, int_date(encoded)) for encoded in dates]
    for encoded, day_value in parsed:
        if day_value is None:
            continue
        iso = day_value.isocalendar()
        week_key = f"{iso.year}-W{iso.week:02d}"
        month_key = f"{day_value.year}-{day_value.month:02d}"
        by_date[encoded] = {"WEEK": week_key, "MONTH": month_key}
        for kind, key in (("WEEK", week_key), ("MONTH", month_key)):
            item = periods[kind].setdefault(key, {"session_count": 0, "last_session": encoded})
            item["session_count"] += 1
            item["last_session"] = max(item["last_session"], encoded)
    return by_date, periods


def load_inventory(path: Path) -> dict[str, dict]:
    rows = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rows[row["relative_path"]] = row
    return rows


def daily_table(records: np.ndarray, identity: str | None, market: str, code: str, rel: str, type_hint: str, file_valid: bool) -> pa.Table:
    count = len(records)
    dates = records["trade_date"]
    op, hi, lo, cl = (records[name] for name in ("open_raw", "high_raw", "low_raw", "close_raw"))
    amount = records["amount_source"]
    zeros = (op == 0) & (hi == 0) & (lo == 0) & (cl == 0)
    valid_ohlc = zeros | ((hi >= op) & (hi >= lo) & (hi >= cl) & (lo <= op) & (lo <= hi) & (lo <= cl))
    valid_amount = np.isfinite(amount) & (amount >= 0)
    valid_date = np.fromiter((int_date(int(v)) is not None for v in dates), dtype=np.bool_, count=count)
    quality = np.where(~valid_date, "INVALID_DATE", np.where(~valid_ohlc, "INVALID_OHLC", np.where(~valid_amount, "INVALID_AMOUNT", np.where(zeros, "NO_ACTUAL_OHLC", "SOURCE_RECORD_RETAINED"))))
    return pa.table(
        {
            "canonical_security_id": pa.array([None] * count, type=pa.string()),
            "source_security_key": pa.array([identity] * count, type=pa.string()),
            "market": pa.array([market] * count, type=pa.string()),
            "code": pa.array([code] * count, type=pa.string()),
            "trade_date_raw": pa.array(dates, type=pa.uint32()),
            "open_price_raw": pa.array(op, type=pa.uint32()),
            "high_price_raw": pa.array(hi, type=pa.uint32()),
            "low_price_raw": pa.array(lo, type=pa.uint32()),
            "close_price_raw": pa.array(cl, type=pa.uint32()),
            "price_scale": pa.array([100] * count, type=pa.uint16()),
            "amount_source_native": pa.array(amount, type=pa.float32()),
            "volume_source_native": pa.array(records["volume_source"], type=pa.uint32()),
            "reserved_raw": pa.array(records["reserved"], type=pa.uint32()),
            "source_relative_path": pa.array([rel] * count, type=pa.string()),
            "source_record_ordinal": pa.array(np.arange(count, dtype=np.uint32), type=pa.uint32()),
            "security_type_asof_hint": pa.array([type_hint] * count, type=pa.string()),
            "source_file_valid": pa.array([file_valid] * count, type=pa.bool_()),
            "record_quality": pa.array(quality.tolist(), type=pa.string()),
            "membership_basis": pa.array(["DIAGNOSTIC_NON_PIT"] * count, type=pa.string()),
            "limit_status": pa.array(["UNKNOWN"] * count, type=pa.string()),
            "missing_bar_semantics": pa.array(["DATA_MISSING_UNKNOWN_NOT_SUSPENSION_OR_DELISTING"] * count, type=pa.string()),
        }
    )


def aggregate_periods(records: np.ndarray, period_map: dict[int, dict], period_defs: dict[str, dict], asof: int, kind: str, security_id: str | None, market: str, code: str, rel: str) -> list[dict]:
    if security_id is None:
        return []
    groups: dict[str, dict] = {}
    for ordinal, record in enumerate(records):
        trade_date = int(record["trade_date"])
        if trade_date > asof or trade_date not in period_map:
            continue
        op = int(record["open_raw"])
        hi = int(record["high_raw"])
        lo = int(record["low_raw"])
        cl = int(record["close_raw"])
        amount = float(record["amount_source"])
        volume = int(record["volume_source"])
        is_zero = op == hi == lo == cl == 0
        valid_ohlc = is_zero or (hi >= max(op, lo, cl) and lo <= min(op, hi, cl))
        if is_zero or not valid_ohlc or not math.isfinite(amount) or amount < 0:
            continue
        key = period_map[trade_date][kind]
        item = groups.get(key)
        if item is None:
            groups[key] = {"first_date": trade_date, "first_open": op, "first_ordinal": ordinal, "last_date": trade_date, "last_close": cl, "high": hi, "low": lo, "amount": amount, "volume": volume, "actual_dates": {trade_date}, "valid_record_count": 1, "last_ordinal": ordinal}
        else:
            item["actual_dates"].add(trade_date)
            item["high"] = max(item["high"], hi)
            item["low"] = min(item["low"], lo)
            item["amount"] += amount
            item["volume"] += volume
            item["valid_record_count"] += 1
            if (trade_date, ordinal) < (item["first_date"], item["first_ordinal"]):
                item["first_date"] = trade_date
                item["first_open"] = op
                item["first_ordinal"] = ordinal
            if (trade_date, ordinal) >= (item["last_date"], item["last_ordinal"]):
                item["last_date"] = trade_date
                item["last_close"] = cl
                item["last_ordinal"] = ordinal
    output = []
    for key, item in groups.items():
        definition = period_defs.get(key)
        if definition is None:
            continue
        closed = int(definition["last_session"]) <= asof
        period_view = "DIAGNOSTIC_CLOSED_PERIOD" if closed else "DIAGNOSTIC_AS_OF_PARTIAL"
        first_date = item["first_date"]
        output.append({
            "canonical_security_id": None,
            "source_security_key": security_id,
            "market": market,
            "code": code,
            "period_type": "WEEKLY" if kind == "WEEK" else "MONTHLY",
            "period_key": key,
            "period_view": period_view,
            "period_last_session": int(definition["last_session"]),
            "asof_trade_date": asof,
            "max_source_trade_date": item["last_date"],
            "open_price_raw": item["first_open"],
            "high_price_raw": item["high"],
            "low_price_raw": item["low"],
            "close_price_raw": item["last_close"],
            "price_scale": 100,
            "amount_source_native_sum": item["amount"],
            "volume_source_native_sum": item["volume"],
            "calendar_count": int(definition["session_count"]),
            "actual_count": len(item["actual_dates"]),
            "suspended_count": None,
            "coverage_status": "UNKNOWN_GAP_OR_LISTING_OR_SUSPENSION",
            "limit_status": "UNKNOWN",
            "valid_record_count": item["valid_record_count"],
            "source_relative_path": rel,
            "membership_basis": "DIAGNOSTIC_NON_PIT",
            "knowledge_status": "DIAGNOSTIC_NON_PIT",
            "adjustment_view": "RAW",
        })
    return output


PERIOD_SCHEMA = pa.schema([
    ("canonical_security_id", pa.string()), ("source_security_key", pa.string()), ("market", pa.string()), ("code", pa.string()),
    ("period_type", pa.string()), ("period_key", pa.string()), ("period_view", pa.string()),
    ("period_last_session", pa.uint32()), ("asof_trade_date", pa.uint32()), ("max_source_trade_date", pa.uint32()),
    ("open_price_raw", pa.uint32()), ("high_price_raw", pa.uint32()), ("low_price_raw", pa.uint32()), ("close_price_raw", pa.uint32()),
    ("price_scale", pa.uint16()), ("amount_source_native_sum", pa.float64()), ("volume_source_native_sum", pa.uint64()),
    ("calendar_count", pa.uint16()), ("actual_count", pa.uint16()), ("suspended_count", pa.uint16()),
    ("coverage_status", pa.string()), ("limit_status", pa.string()), ("valid_record_count", pa.uint16()), ("source_relative_path", pa.string()),
    ("membership_basis", pa.string()), ("knowledge_status", pa.string()), ("adjustment_view", pa.string())
])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asof", default="20260924", help="cutoff in YYYYMMDD; cannot exceed the frozen source package cutoff")
    args = parser.parse_args()
    if not re.fullmatch(r"\d{8}", args.asof) or int_date(int(args.asof)) is None:
        raise ValueError("INVALID_ASOF_DATE")
    asof = int(args.asof)
    run_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    run_id = f"V4_02_CANONICAL_DAILY_PIT_{asof}_{datetime.now(timezone.utc):%H%M%S}Z"

    contract_path = ROOT / "config/v4_02_canonical_daily_pit_contract_v1.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "V4_CANONICAL_DAILY_PIT_PERIODS_V1":
        raise ValueError("V4_02_CONTRACT_ID_MISMATCH")
    execution_identity = {
        "input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "contract_sha256": sha256_file(contract_path),
    }
    if asof > int(contract["inputs"]["source_cutoff"].replace("-", "")):
        raise ValueError("ASOF_AFTER_SOURCE_CUTOFF")
    bundle_path = ROOT / "data/source_bundles" / SOURCE_BUNDLE_ID / "source_bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    if bundle.get("source_bundle_id") != SOURCE_BUNDLE_ID or bundle.get("package", {}).get("sha256") != PACKAGE_SHA:
        raise ValueError("SOURCE_BUNDLE_IDENTITY_MISMATCH")
    archive = ROOT / "data/v4/raw_archive" / PACKAGE_SHA / "hsjday.zip"
    if not archive.is_file() or sha256_file(archive) != PACKAGE_SHA:
        raise ValueError("RAW_ARCHIVE_HASH_MISMATCH")
    stage01_path = ROOT / "reports/v4_01/v4_01_stage_receipt_R2_20260925.json"
    stage01 = json.loads(stage01_path.read_text(encoding="utf-8"))
    if stage01.get("status") != "FULL_PASS" or stage01.get("evidence", {}).get("raw_archive_sha256") != PACKAGE_SHA:
        blocked_receipt_path = ROOT / contract["outputs"]["blocked_entry_receipt"]
        blocked_receipt = {
            "stage": "V4-02",
            "run_id": run_id,
            "stage_contract": "V4.2.2 REV2 §§3B.6/3C.1-3C.4/5.2-5.3/6A/10N/78; V4_CANONICAL_DAILY_PIT_PERIODS_V1",
            "consulted_upgrade": contract["consulted_upgrade"],
            "execution_identity": execution_identity,
            "input_evidence": {
                "v4_01_receipt": stage01_path.relative_to(ROOT).as_posix(),
                "v4_01_receipt_sha256": sha256_file(stage01_path),
                "v4_01_status": stage01.get("status"),
                "required_v4_01_status": "FULL_PASS",
                "source_package_sha256": PACKAGE_SHA,
            },
            "status": "BLOCKED",
            "blocked_scopes": ["V4_01_ENTRY_GATE_NOT_SATISFIED"],
            "stage_completion_authorized": False,
            "outputs_emitted": False,
            "acceptance": "V4-02 was stopped at its contracted entry gate because the hash-bound V4-01 receipt is not FULL_PASS. No canonical, period, or scanner/factor output was produced.",
            "next_stage": "RESOLVE_V4_01_BLOCKERS_THEN_RERUN_V4_02",
            "tdx_root_write_count": 0,
        }
        atomic_json(blocked_receipt_path, blocked_receipt)
        print(json.dumps({"stage": "V4-02", "status": "BLOCKED", "receipt": blocked_receipt_path.relative_to(ROOT).as_posix()}, ensure_ascii=False))
        return 2
    source_manifest_path = ROOT / "reports/v4_01/v4_01_source_manifest_R2_20260925.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    inventory_path = ROOT / "reports/v4_01/v4_01_security_inventory_R2_20260925.csv"
    if stage01.get("evidence", {}).get("source_manifest_sha256") != sha256_file(source_manifest_path):
        raise ValueError("V4_01_SOURCE_MANIFEST_RECEIPT_HASH_MISMATCH")
    extracted_root = ROOT / bundle["extraction"]["root"]
    if source_manifest.get("source", {}).get("extracted_content_digest_algorithm") != "SHA256(sorted relative_path NUL byte_count NUL file_sha256 LF)":
        raise ValueError("V4_01_SNAPSHOT_DIGEST_CONTRACT_MISSING")
    inventory = load_inventory(inventory_path)
    snapshot_verification = verify_zip_snapshot(
        archive,
        extracted_root,
        inventory,
        int(bundle["extraction"]["entry_count"]),
        str(source_manifest["source"]["extracted_content_digest"]),
    )
    files = sorted((p for p in extracted_root.rglob("*.day") if p.relative_to(extracted_root).parts[0].lower() in {"sh", "sz", "bj"}), key=lambda p: p.as_posix().casefold())
    expected_files = int(source_manifest["inventory"]["day_file_count"])
    expected_records = int(source_manifest["inventory"]["day_record_count"])
    if len(files) != expected_files:
        raise ValueError(f"DAY_FILE_COUNT_CHANGED:{len(files)}:{expected_files}")
    if len(inventory) != expected_files:
        raise ValueError("V4_01_INVENTORY_COUNT_MISMATCH")

    calendar_inputs = {"SH": "sh/lday/sh000001.day", "SZ": "sz/lday/sz399001.day", "BJ": "bj/lday/bj899050.day"}
    calendars = {}
    calendar_evidence = {}
    for market, relative in calendar_inputs.items():
        dates = read_calendar(extracted_root / relative)
        date_map, period_defs = calendar_period_map(dates)
        calendars[market] = {"dates": date_map, "periods": period_defs}
        calendar_evidence[market] = {"source_relative_path": relative, "calendar_session_count": len(dates), "first_session": min(dates) if dates else None, "last_session": max(dates) if dates else None, "basis": "LOCAL_INDEX_BAR_DATES_DIAGNOSTIC_NOT_EXCHANGE_OFFICIAL_CALENDAR"}

    data_final = ROOT / "data/v4/canonical" / run_id
    daily_final = data_final / "canonical_daily_raw.parquet"
    weekly_final = data_final / "weekly_raw_diagnostic.parquet"
    monthly_final = data_final / "monthly_raw_diagnostic.parquet"
    daily_tmp, weekly_tmp, monthly_tmp = (staging_path(p) for p in (daily_final, weekly_final, monthly_final))
    daily_writer = weekly_writer = monthly_writer = None
    file_count = row_count = invalid_record_count = 0
    week_count = month_count = 0
    try:
        week_writer = pq.ParquetWriter(weekly_tmp, PERIOD_SCHEMA, compression="zstd", version="2.6")
        month_writer = pq.ParquetWriter(monthly_tmp, PERIOD_SCHEMA, compression="zstd", version="2.6")
        for path in files:
            rel = path.relative_to(extracted_root).as_posix()
            item = inventory.get(rel)
            if item is None:
                raise ValueError(f"SOURCE_FILE_NOT_IN_V4_01_INVENTORY:{rel}")
            size = path.stat().st_size
            if size % DAY_BYTES:
                raise ValueError(f"INCOMPLETE_RAW_RECORD:{rel}")
            raw = path.read_bytes()
            records = np.frombuffer(raw, dtype=DAY_DTYPE)
            identity, market, code = security_identity(path, extracted_root)
            table = daily_table(records, identity, market, code, rel, item.get("security_type_asof_hint", "UNKNOWN"), item.get("file_valid", "False").lower() == "true")
            if daily_writer is None:
                daily_writer = pq.ParquetWriter(daily_tmp, table.schema, compression="zstd", version="2.6")
            daily_writer.write_table(table, row_group_size=100000)
            row_count += len(records)
            invalid_record_count += int(np.count_nonzero(np.array(table.column("record_quality").to_pylist()) != "SOURCE_RECORD_RETAINED"))
            file_count += 1
            if identity is None or market not in calendars:
                continue
            for kind, writer, counter_name in (("WEEK", week_writer, "week"), ("MONTH", month_writer, "month")):
                rows = aggregate_periods(records, calendars[market]["dates"], calendars[market]["periods"][kind], asof, kind, identity, market, code, rel)
                if rows:
                    writer.write_table(pa.Table.from_pylist(rows, schema=PERIOD_SCHEMA))
                    if counter_name == "week":
                        week_count += len(rows)
                    else:
                        month_count += len(rows)
        if daily_writer is None:
            raise ValueError("NO_DAY_FILES_PROCESSED")
        daily_writer.close()
        daily_writer = None
        week_writer.close()
        week_writer = None
        month_writer.close()
        month_writer = None
        if row_count != expected_records:
            raise ValueError(f"RAW_RECORD_COUNT_MISMATCH:{row_count}:{expected_records}")
        for temp, final in ((daily_tmp, daily_final), (weekly_tmp, weekly_final), (monthly_tmp, monthly_final)):
            with temp.open("rb+") as handle:
                os.fsync(handle.fileno())
            os.replace(temp, final)
    except Exception:
        for writer in (daily_writer, week_writer, month_writer):
            if writer is not None:
                writer.close()
        for temp in (daily_tmp, weekly_tmp, monthly_tmp):
            temp.unlink(missing_ok=True)
        raise

    outputs = {
        "canonical_daily_raw": {"path": str(daily_final.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_file(daily_final), "row_count": row_count, "byte_count": daily_final.stat().st_size},
        "weekly_raw_diagnostic": {"path": str(weekly_final.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_file(weekly_final), "row_count": week_count, "byte_count": weekly_final.stat().st_size},
        "monthly_raw_diagnostic": {"path": str(monthly_final.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_file(monthly_final), "row_count": month_count, "byte_count": monthly_final.stat().st_size},
    }
    receipt = {
        "run_id": run_id,
        "stage": "V4-02",
        "execution_identity": execution_identity,
        "stage_contract": "V4.2.2 REV2 §§3B.6, 3C.1-3C.4, 5.2-5.3, 6A, 10N, 78; V4_CANONICAL_DAILY_PIT_PERIODS_V1",
        "consulted_upgrade": {"document": contract["consulted_upgrade"]["document"], "sha256": contract["consulted_upgrade"]["sha256"], "sections": contract["consulted_upgrade"]["sections"]},
        "entry_gate": {"phase0": "DEGRADED_PASS", "v4_01": "DEGRADED_PASS", "raw_archive_sha256": PACKAGE_SHA},
        "source_cutoff": "2026-09-24",
        "asof_trade_date": asof,
        "observed_at_utc": run_at,
        "status": "BLOCKED",
        "stage_completion_authorized": False,
        "acceptance": "RAW canonical and diagnostic periods were emitted from the verified ZIP-bound snapshot, but the R2 stage gate remains BLOCKED until source priority, canonical identity, dated lifecycle/PIT universe, formal calendar, CLOSED_ONLY/AS_OF temporal proofs, adjustment acceptance and price-limit rules are independently accepted.",
        "inventory": {"source_file_count": file_count, "expected_file_count": expected_files, "source_record_count": row_count, "expected_record_count": expected_records, "records_flagged_beyond_normal_source_record": invalid_record_count},
        "period_rows": {"weekly": week_count, "monthly": month_count},
        "calendar_evidence": calendar_evidence,
        "capabilities": contract["capabilities"],
        "limit_status": "UNKNOWN",
        "outputs": outputs,
        "extracted_snapshot_verification": snapshot_verification,
        "degraded_scopes": [],
        "blocked_scopes": ["R2_CANONICAL_SOURCE_SELECTION_OPEN", "R2_IDENTITY_AND_HISTORICAL_PIT_OPEN", "R2_FORMAL_PERIOD_AND_TEMPORAL_LEAKAGE_ACCEPTANCE_OPEN", "R2_ADJUSTMENT_AND_PRICE_LIMIT_ACCEPTANCE_OPEN"],
        "independent_audits_remain_open": ["V422-B01", "V422-B03", "V422-B04", "V422-B07", "V422-B08", "V422-B10", "AUD-AMOUNT-A-06"],
        "database_write_count": 0,
        "tdx_root_write_count": 0,
        "scanner_or_factor_run_count": 0,
        "next_stage": "V4-02_REPAIR_CANONICAL_IDENTITY_PIT_ADJUSTMENT_FORMAL_PERIODS_PRICE_LIMITS",
    }
    receipt_path = ROOT / "reports/v4_02" / f"{run_id}_stage_receipt.json"
    manifest_path = ROOT / "reports/v4_02" / f"{run_id}_source_manifest.json"
    atomic_json(receipt_path, receipt)
    manifest = {
        "run_id": run_id,
        "execution_identity": execution_identity,
        "contract_id": contract["contract_id"],
        "contract_sha256": sha256_file(contract_path),
        "source_package_sha256": PACKAGE_SHA,
        "source_bundle_id": SOURCE_BUNDLE_ID,
        "source_manifest_v4_01_sha256": sha256_file(source_manifest_path),
        "extracted_snapshot_verification": snapshot_verification,
        "stage01_receipt_sha256": sha256_file(stage01_path),
        "inventory_sha256": sha256_file(inventory_path),
        "extracted_root": str(extracted_root.relative_to(ROOT)).replace("\\", "/"),
        "calendar_evidence": calendar_evidence,
        "asof_trade_date": asof,
        "outputs": outputs,
        "receipt_sha256": sha256_file(receipt_path),
        "observed_at_utc": run_at,
        "lineage": "DIAGNOSTIC_NON_PIT; package bars lack per-record system-consumed publication history",
    }
    atomic_json(manifest_path, manifest)
    print(json.dumps({"stage_receipt": str(receipt_path), "source_manifest": str(manifest_path), "status": receipt["status"], "daily_rows": row_count, "weekly_rows": week_count, "monthly_rows": month_count}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
