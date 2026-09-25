from __future__ import annotations

"""V4-01 bounded TDX history bootstrap from an already accepted package.

All package, extraction, and TDX paths are read-only inputs. Outputs are
written atomically under the project root and never under D:/new_tdx.
"""

import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tdx.day_reader import validate_day_file
from tdx.security_master import classify_security, current_a_stock_ids, read_industry_assignments
from market_calendar.trading_calendar import read_day_dates

PACKAGE_SHA = "b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f"
SOURCE_BUNDLE_ID = "6122afa9db83170f7b442d5ecc5c7c9287b9dd6b04c4d53729d55f71f7dd99d2"
PAGE_URL = "https://www.tdx.com.cn/article/vipdata.html"
PACKAGE_URL = "https://data.tdx.com.cn/vipdoc/hsjday.zip?cache_bust=5349e64987e14b318b12fbd268335dfa"
TDX_ROOT = Path("D:/new_tdx")
PAGE_OBSERVED_AT = "2026-09-25T08:27:38+00:00"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def atomic_copy(source: Path, destination: Path, expected_sha: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256_file(destination) != expected_sha:
            raise ValueError("IMMUTABLE_ARCHIVE_IDENTITY_COLLISION")
        return
    free_bytes = shutil.disk_usage(destination.parent).free
    if free_bytes < source.stat().st_size + 64 * 1024 * 1024:
        raise OSError("INSUFFICIENT_SPACE_FOR_ATOMIC_ARCHIVE_COPY")
    fd, tmp_name = tempfile.mkstemp(prefix=".archive-", suffix=".tmp", dir=destination.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    digest = hashlib.sha256()
    try:
        with source.open("rb") as src, tmp.open("wb") as dst:
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                digest.update(chunk)
                dst.write(chunk)
            dst.flush()
            os.fsync(dst.fileno())
        if digest.hexdigest() != expected_sha:
            raise ValueError("SOURCE_PACKAGE_SHA256_MISMATCH")
        os.replace(tmp, destination)
        try:
            destination.chmod(0o444)
        except OSError:
            pass
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def atomic_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    run_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    contract = json.loads((ROOT / "config/v4_01_bootstrap_contract_v1.json").read_text(encoding="utf-8"))
    if contract.get("contract_id") != "V4_TDX_HISTORY_BOOTSTRAP_V1":
        raise ValueError("V4_01_CONTRACT_ID_MISMATCH")
    bundle_path = ROOT / "data/source_bundles" / SOURCE_BUNDLE_ID / "source_bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    if bundle.get("source_bundle_id") != SOURCE_BUNDLE_ID or bundle.get("package", {}).get("sha256") != PACKAGE_SHA:
        raise ValueError("SOURCE_BUNDLE_IDENTITY_MISMATCH")
    package_path = ROOT / bundle["package"]["staged_path"]
    if not package_path.is_file() or package_path.stat().st_size != bundle["package"]["byte_count"]:
        raise ValueError("SOURCE_PACKAGE_MISSING_OR_SIZE_MISMATCH")
    actual_package_sha = sha256_file(package_path)
    if actual_package_sha != PACKAGE_SHA:
        raise ValueError("SOURCE_PACKAGE_SHA256_MISMATCH")

    extracted_root = ROOT / bundle["extraction"]["root"]
    expected_entries = int(bundle["extraction"]["entry_count"])
    archive_output = ROOT / "data/v4/raw_archive" / PACKAGE_SHA / "hsjday.zip"
    atomic_copy(package_path, archive_output, PACKAGE_SHA)

    with zipfile.ZipFile(package_path) as archive:
        infos = archive.infolist()
        if len(infos) != expected_entries:
            raise ValueError("ZIP_ENTRY_COUNT_MISMATCH")
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError("ZIP_CRC_FAILURE:" + bad_member)

    # Current TDX name tables are used only for a descriptive as-of type hint.
    # They never filter the archived universe or establish PIT membership.
    metadata_root = ROOT / bundle["metadata"]["root"]
    cache = metadata_root / "T0002/hq_cache"
    assignments = read_industry_assignments(cache / "tdxhy.cfg")
    current_asof_a_ids = current_a_stock_ids(assignments)

    inventory = []
    content_digest = hashlib.sha256()
    day_file_count = 0
    day_record_count = 0
    malformed = []
    malformed_a_stock_files = 0
    invalid_identity_files = 0
    all_first = None
    all_last = None
    for path in sorted(extracted_root.rglob("*.day"), key=lambda item: item.as_posix().casefold()):
        stem = path.stem.lower()
        market = stem[:2]
        if market not in ("sh", "sz", "bj"):
            continue
        rel = path.relative_to(extracted_root).as_posix()
        item = validate_day_file(path, market)
        if not item["valid"]:
            malformed.append({"relative_path": rel, "errors": item["errors"]})
            if len(stem) == 8 and stem[2:].isdigit() and classify_security(market, stem[2:], current_asof_a_ids) == "A_STOCK":
                malformed_a_stock_files += 1
        stat = path.stat()
        file_sha = sha256_file(path)
        content_digest.update(rel.encode("utf-8"))
        content_digest.update(b"\0")
        content_digest.update(str(stat.st_size).encode("ascii"))
        content_digest.update(b"\0")
        content_digest.update(file_sha.encode("ascii"))
        content_digest.update(b"\n")
        day_file_count += 1
        day_record_count += int(item["record_count"])
        first_date = item.get("first_date")
        last_date = item.get("last_date")
        if first_date is not None:
            all_first = first_date if all_first is None else min(all_first, first_date)
        if last_date is not None:
            all_last = last_date if all_last is None else max(all_last, last_date)
        valid_security_code = len(stem) == 8 and stem[2:].isdigit()
        invalid_identity_files += int(not valid_security_code)
        security_id = item["security_id"] if valid_security_code else None
        inventory.append({
            "security_id": security_id,
            "relative_path": rel,
            "security_type_asof_hint": classify_security(market, stem[2:], current_asof_a_ids) if valid_security_code else "UNKNOWN_INVALID_FILENAME",
            "security_identity_status": "VALID_TDX_FILENAME" if valid_security_code else "INVALID_TDX_FILENAME_RETAINED_BUT_NOT_CLASSIFIABLE",
            "first_observed_bar_date": first_date,
            "last_observed_bar_date": last_date,
            "bar_count": item["record_count"],
            "file_valid": item["valid"],
            "membership_basis": "DIAGNOSTIC_NON_PIT",
            "historical_lifecycle_status": "UNKNOWN_UNLESS_SUPPORTED_BY_VERSIONED_FACT",
            "missing_bar_semantics": "UNKNOWN_NOT_SUSPENSION_OR_DELISTING",
        })

    if day_file_count != len(list(extracted_root.rglob("*.day"))) or day_file_count != int(bundle["validation"]["file_count"]):
        raise ValueError("DAY_FILE_COUNT_MISMATCH")
    if day_record_count != int(bundle["validation"]["record_count"]):
        raise ValueError("DAY_RECORD_COUNT_MISMATCH")
    if bundle.get("validation", {}).get("status") != "PASS" or bundle["validation"].get("normal_a_share_invalid_count") != 0:
        raise ValueError("CURRENT_A_STOCK_VALIDATION_NOT_ACCEPTED")

    index_dates = read_day_dates(extracted_root / "sh/lday/sh000001.day")
    formal_start = 20240925
    formal_end = int(bundle["validation"]["target_trade_date"])
    pre_formal_sessions = [value for value in index_dates if value < formal_start]
    formal_sessions = [value for value in index_dates if formal_start <= value <= formal_end]
    warmup_session_count = min(300, len(pre_formal_sessions))
    warmup_start_date = pre_formal_sessions[-warmup_session_count] if warmup_session_count else None

    overlap_path = ROOT / "reports/v4_00d/v4_00d_asset_stratified_postcheck_20260925.json"
    overlap = json.loads(overlap_path.read_text(encoding="utf-8"))
    a_stock = overlap.get("asset_types", {}).get("A_STOCK", {})
    if overlap.get("source_package_sha256") != PACKAGE_SHA or a_stock.get("acceptance") != "ACCEPTED_SOURCE_PACKAGE":
        raise ValueError("ACCEPTED_A_STOCK_OVERLAP_EVIDENCE_MISSING")
    if int(a_stock.get("session_count", 0)) < 60:
        raise ValueError("OVERLAP_SESSION_COVERAGE_BELOW_CONTRACT")

    page_snapshot_path = ROOT / "docs/evidence/V4_01_OFFICIAL_SOURCE_PAGE_OBSERVATION_20260925.json"
    page_snapshot = {
        "source_page_url": PAGE_URL,
        "observed_at_utc": PAGE_OBSERVED_AT,
        "page_title": "个人行情数据 - 通达信软件 - 深圳市财富趋势科技股份有限公司",
        "observed_content": {
            "scope": "适用于通达信个人版PC端软件的盘后数据下载",
            "package_contents": "沪深京日线数据完整包（A股、B股、交易所指数和板块指数、回购、可交易基金、可转债等）",
            "same_day_rule": "如需下载包括当日的，请在更新日期变为当日之后再下载。",
            "displayed_package_update_date": None,
        },
        "decision": "NO_NEW_DOWNLOAD; displayed update date is blank; reuse only the already sealed 2026-09-24 package.",
    }
    atomic_json(page_snapshot_path, page_snapshot)
    page_snapshot_sha = sha256_file(page_snapshot_path)

    columns = list(inventory[0]) if inventory else []
    inventory_path = ROOT / "reports/v4_01/v4_01_security_inventory_20260925.csv"
    atomic_csv(inventory_path, inventory, columns)

    manifest = {
        "contract_id": "V4_TDX_HISTORY_BOOTSTRAP_V1",
        "stage": "V4-01",
        "run_id": "V4_01_TDX_HISTORY_BOOTSTRAP_20260925",
        "observed_at_utc": run_at,
        "source": {
            "source_bundle_id": SOURCE_BUNDLE_ID,
            "package_id": PACKAGE_SHA,
            "source_page_url": PAGE_URL,
            "page_observed_at_utc": PAGE_OBSERVED_AT,
            "page_declared_update_date": None,
            "page_evidence": "Official page says a same-day package should only be downloaded after update date changes to the target day; field was blank at observation. No new download was started.",
            "download_url": PACKAGE_URL,
            "target_trade_date": bundle["target_trade_date"],
            "frozen_source_cutoff": bundle["target_trade_date"],
            "download_started_at": None,
            "download_finished_at": None,
            "transfer_timestamp_status": "UNAVAILABLE_FOR_REUSED_SEALED_PACKAGE",
            "package_last_modified": bundle["package"].get("last_modified"),
            "source_page_snapshot_path": page_snapshot_path.relative_to(ROOT).as_posix(),
            "source_page_snapshot_sha256": page_snapshot_sha,
            "filename": "hsjday.zip",
            "byte_count": bundle["package"]["byte_count"],
            "package_sha256": actual_package_sha,
            "raw_archive_path": archive_output.relative_to(ROOT).as_posix(),
            "zip_entry_count": len(infos),
            "zip_crc_status": "PASS",
            "extracted_content_digest": content_digest.hexdigest(),
            "extracted_content_digest_algorithm": "SHA256(sorted relative_path NUL byte_count NUL file_sha256 LF)",
            "parser_version": "v4-day-raw-v1.1",
            "status": "ACCEPTED_A_STOCK_SOURCE_PACKAGE_WITH_SCOPED_DEGRADATIONS",
            "failure_reason": None,
        },
        "inventory": {
            "all_recognized_day_files_retained": True,
            "current_universe_filter_applied": False,
            "day_file_count": day_file_count,
            "day_record_count": day_record_count,
            "first_observed_date": all_first,
            "last_observed_date": all_last,
            "invalid_day_file_count": len(malformed),
            "invalid_day_file_samples": malformed[:100],
            "invalid_current_a_stock_file_count": malformed_a_stock_files,
            "invalid_security_filename_count": invalid_identity_files,
            "all_day_files_retained_and_profiled": True,
            "research_window": {"start": formal_start, "end": formal_end, "market_session_count": len(formal_sessions)},
            "warmup_window": {"required_market_sessions": 300, "available_market_sessions_before_research_window": len(pre_formal_sessions), "last_300_sessions_start": warmup_start_date, "market_calendar_coverage_pass": len(pre_formal_sessions) >= 300},
            "security_inventory_path": inventory_path.relative_to(ROOT).as_posix(),
            "security_inventory_rows": len(inventory),
            "membership_basis": "DIAGNOSTIC_NON_PIT",
            "pit_lifecycle_asserted": False,
        },
        "overlap": {
            "acceptance": "ACCEPTED_SOURCE_PACKAGE",
            "source_report": overlap_path.relative_to(ROOT).as_posix(),
            "source_report_sha256": sha256_file(overlap_path),
            "source_package_sha256": PACKAGE_SHA,
            "sessions": a_stock["session_count"],
            "first_session": a_stock["sessions"]["first"],
            "last_session": a_stock["sessions"]["last"],
            "comparable_rows": a_stock["comparable_rows"],
            "exact_match_rows": a_stock["exact_match_rows"],
            "normalized_match_rows": a_stock["normalized_match_rows"],
            "unexplained_mismatch_rows": a_stock["unexplained_mismatch_rows"],
            "identity_mismatch_count": a_stock["identity_mismatch_count"],
            "rerun": False,
        },
        "tdx_read_only_boundary": {
            "configured_root": str(TDX_ROOT),
            "read_only": True,
            "writes_under_tdx_root": 0,
        },
    }
    manifest_path = ROOT / "reports/v4_01/v4_01_source_manifest_20260925.json"
    atomic_json(manifest_path, manifest)
    manifest_sha = sha256_file(manifest_path)
    archive_sha = sha256_file(archive_output)
    status = "DEGRADED_PASS"
    degraded_scopes = [
        "HISTORICAL_PIT_LIFECYCLE_UNAVAILABLE",
        "SOURCE_PAGE_UPDATE_DATE_EMPTY",
        "TRANSFER_TIMESTAMPS_UNAVAILABLE_FOR_REUSED_PACKAGE",
        "ADJUSTED_CANONICAL_SCOPE_DEFERRED_TO_V4_02_CONTRACT",
    ]
    if malformed or invalid_identity_files:
        degraded_scopes.append("NONCORE_OR_UNIDENTIFIED_BAR_VALIDATION_ERRORS")
    receipt = {
        "stage": "V4-01",
        "stage_contract": "V4.2.2 REV2 §§3B.1-3B.6, §78; V4_TDX_HISTORY_BOOTSTRAP_V1",
        "consulted_upgrade": {
            "technical_contract": "DA-MSR-V4.2.2-CODEX-REV2",
            "technical_contract_sha256": "744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd",
            "contract_reaudit_open_items": ["V422-B01", "V422-B03", "V422-B04", "V422-B07", "V422-B08", "V422-B10"],
            "external_phase0_authority": "DA-MSR-V4-PHASE0-FINAL-EXTERNAL-ACCEPTANCE-R4",
            "external_phase0_entry_permission": "AUTHORIZED",
            "phase0_status": "DEGRADED_PASS",
        },
        "evidence": {
            "source_manifest": manifest_path.relative_to(ROOT).as_posix(),
            "source_manifest_sha256": manifest_sha,
            "raw_archive": archive_output.relative_to(ROOT).as_posix(),
            "raw_archive_sha256": archive_sha,
            "security_inventory": inventory_path.relative_to(ROOT).as_posix(),
            "security_inventory_rows": len(inventory),
            "overlap_report": overlap_path.relative_to(ROOT).as_posix(),
            "overlap_acceptance": "ACCEPTED_SOURCE_PACKAGE",
        },
        "status": status,
        "degraded_scopes": degraded_scopes,
        "blocked_scopes": [],
        "acceptance": f"Immutable raw archive hash/ZIP integrity, {day_file_count} profiled .day files / {day_record_count} records, current A-stock source validation, and prior 60-session A_STOCK overlap acceptance verified. {len(malformed)} files contain non-core or unidentified validation errors ({invalid_identity_files} unclassifiable filename); those raw entries are retained and scoped. Historical PIT membership/lifecycle was not inferred from bars; no canonical adjusted history, scanner, or production capability was produced.",
        "next_stage": "V4-02 Canonical Daily / PIT Periods (with PIT lifecycle and adjustment scopes remaining explicitly limited)",
        "tdx_root_write_count": 0,
        "database_write_count": 0,
        "network_download_count": 0,
    }
    receipt_path = ROOT / "reports/v4_01/v4_01_stage_receipt_20260925.json"
    atomic_json(receipt_path, receipt)
    print(json.dumps({
        "stage": "V4-01",
        "status": status,
        "source_package_sha256": actual_package_sha,
        "archive_path": archive_output.relative_to(ROOT).as_posix(),
        "inventory_rows": len(inventory),
        "day_records": day_record_count,
        "invalid_day_files": len(malformed),
        "overlap": {"status": a_stock["acceptance"], "sessions": a_stock["session_count"], "comparable_rows": a_stock["comparable_rows"]},
        "source_manifest_sha256": manifest_sha,
        "receipt": receipt_path.relative_to(ROOT).as_posix(),
        "next_stage": receipt["next_stage"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
