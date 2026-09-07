from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import argparse
import json
import os
import tempfile
import time

from .block_reader import (
    build_industry_memberships,
    membership_audit,
    read_industry_names,
    read_infoharbor_memberships,
)
from .day_reader import DAY_RECORD_LENGTH, PRICE_DIVISOR, read_edge_records, record_as_dict, validate_day_file
from .security_master import current_a_stock_ids as select_current_a_stock_ids
from .security_master import read_industry_assignments, read_tnf, summarize_types


MARKETS = ("sh", "sz", "bj")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def atomic_write_json(path: Path, payload: dict, forbidden_root: Path) -> None:
    path = path.resolve()
    forbidden_root = forbidden_root.resolve()
    if _is_relative_to(path, forbidden_root):
        raise ValueError(f"refusing to write audit output inside TDX root: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_day_files(tdx_root: Path) -> tuple[list[Path], dict[str, tuple[int, int]]]:
    files = []
    snapshot = {}
    for market in MARKETS:
        directory = tdx_root / "vipdoc" / market / "lday"
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.day")):
            stat = path.stat()
            files.append(path)
            snapshot[str(path)] = (stat.st_size, stat.st_mtime_ns)
    return files, snapshot


def stable_day_files(tdx_root: Path, stable_window_seconds: float = 1.0) -> tuple[list[Path], dict]:
    first_files, first = snapshot_day_files(tdx_root)
    time.sleep(stable_window_seconds)
    second_files, second = snapshot_day_files(tdx_root)
    changed = sorted(path for path in set(first) | set(second) if first.get(path) != second.get(path))
    stable = [path for path in second_files if str(path) not in changed]
    return stable, {
        "stable_window_seconds": stable_window_seconds,
        "first_file_count": len(first_files),
        "second_file_count": len(second_files),
        "changed_file_count": len(changed),
        "changed_file_samples": changed[:30],
        "status": "PASS" if not changed else "FILE_UNSTABLE",
    }


def raw_manifest_fingerprint(paths: list[Path]) -> str:
    digest = sha256()
    for path in sorted(paths, key=lambda item: str(item).lower()):
        stat = path.stat()
        digest.update(f"{path}|{stat.st_size}|{stat.st_mtime_ns}\n".encode("utf-8"))
    return digest.hexdigest()


def parse_gbbq_map(path: Path) -> dict:
    text = path.read_bytes().decode("ascii", errors="replace")
    lines = [line.strip() for line in text.replace("\r", "\n").split("\n") if line.strip()]
    valid = [line for line in lines if len(line) >= 7 and line[:6].isdigit()]
    return {
        "entry_count": len(valid),
        "sample_entries": valid[:10],
        "format_status": "INDEX_MAP_TEXT_RECOGNIZED_BINARY_PAYLOAD_UNVERIFIED",
    }


def determine_latest_trade_date(valid_results: list[dict], a_stock_ids: set[str]) -> dict:
    a_results = [item for item in valid_results if item["security_id"] in a_stock_ids]
    counts = Counter(item["last_date"] for item in a_results)
    latest_observed = max(counts) if counts else None
    # The dominant most-recent date is safer than a simple maximum from one file.
    candidates = sorted(counts.items(), reverse=True)
    selected = None
    for trade_date, count in candidates:
        if a_results and count / len(a_results) >= 0.50:
            selected = trade_date
            break
    if selected is None and counts:
        selected = counts.most_common(1)[0][0]
    coverage = counts[selected] / len(a_results) if selected is not None and a_results else 0.0
    future_anomaly_count = sum(count for trade_date, count in counts.items() if selected and trade_date > selected)
    return {
        "method": "LATEST_DATE_WITH_AT_LEAST_50_PERCENT_A_STOCK_FILE_COVERAGE_ELSE_MODE",
        "selected_date": selected,
        "latest_observed_date": latest_observed,
        "selected_date_file_count": counts.get(selected, 0),
        "a_stock_file_count": len(a_results),
        "selected_date_coverage_ratio": round(coverage, 6),
        "future_date_anomaly_count": future_anomaly_count,
        "top_date_distribution": [
            {"date": trade_date, "file_count": count, "coverage_ratio": round(count / len(a_results), 6)}
            for trade_date, count in counts.most_common(10)
        ] if a_results else [],
    }


def run_audit(tdx_root: Path, output: Path, requested_root: str | None = None) -> dict:
    started = time.perf_counter()
    tdx_root = tdx_root.resolve()
    if not tdx_root.is_dir():
        raise FileNotFoundError(tdx_root)
    cache = tdx_root / "T0002" / "hq_cache"
    warnings: list[str] = []
    errors: list[str] = []

    day_paths, stability = stable_day_files(tdx_root)
    if stability["changed_file_count"]:
        warnings.append("One or more .day files changed during the stability window and were excluded.")

    with ThreadPoolExecutor(max_workers=min(12, (os.cpu_count() or 4) + 2)) as executor:
        day_results = list(
            executor.map(lambda path: validate_day_file(path, path.parent.parent.name), day_paths)
        )
    valid_results = [item for item in day_results if item["valid"]]
    invalid_results = [item for item in day_results if not item["valid"]]

    assignments_path = cache / "tdxhy.cfg"
    assignments = read_industry_assignments(assignments_path) if assignments_path.is_file() else []
    current_a_stock_ids = select_current_a_stock_ids(assignments)
    day_by_id = {item["security_id"]: item for item in day_results}
    # Keep missing daily files in the denominator.  Excluding them would make
    # parse success circular (a file would need to exist before being expected).
    expected_ids = set(current_a_stock_ids)
    parsed_ids = {item["security_id"] for item in valid_results} & expected_ids
    missing_day_ids = sorted(current_a_stock_ids - set(day_by_id))
    parse_success_ratio = len(parsed_ids) / len(expected_ids) if expected_ids else 0.0
    a_stock_valid_results = [item for item in valid_results if item["security_id"] in expected_ids]
    turnover_checks = sum(item["turnover_price_check_count"] for item in a_stock_valid_results)
    turnover_plausible = sum(item["turnover_price_plausible_count"] for item in a_stock_valid_results)
    turnover_plausibility_ratio = turnover_plausible / turnover_checks if turnover_checks else 0.0

    latest = determine_latest_trade_date(valid_results, expected_ids)
    selected_date = latest["selected_date"]
    index_dates = {}
    for index_id in ("SH.000001", "SZ.399001"):
        item = day_by_id.get(index_id)
        if item and item.get("last_date"):
            index_dates[index_id] = item["last_date"]
    latest["index_confirmation_dates"] = index_dates
    latest["index_confirmation"] = bool(index_dates) and all(
        value == selected_date for value in index_dates.values()
    )
    valid_latest_ids = {
        item["security_id"] for item in valid_results if selected_date is not None and item["last_date"] == selected_date
    }
    normal_universe_ids = {
        item["security_id"]
        for item in valid_results
        if item["security_id"] in expected_ids
        and item["record_count"] >= 120
        and item["last_date"] == selected_date
    }

    tnf_names = {}
    tnf_audits = []
    for market in MARKETS:
        path = cache / f"{market}s.tnf"
        if path.is_file():
            names, details = read_tnf(path, market)
            tnf_names.update(names)
            tnf_audits.append(details)

    industry_names_path = cache / "tdxzs.cfg"
    industry_names = read_industry_names(industry_names_path) if industry_names_path.is_file() else {}
    memberships = build_industry_memberships(assignments, industry_names)
    infoharbor_path = cache / "infoharbor_block.dat"
    infoharbor_meta = {}
    if infoharbor_path.is_file():
        infoharbor_memberships, infoharbor_meta = read_infoharbor_memberships(infoharbor_path)
        memberships.extend(infoharbor_memberships)
    known_ids = set(day_by_id) | set(tnf_names)
    sector_audit = membership_audit(
        memberships,
        known_security_ids=known_ids,
        valid_latest_ids=valid_latest_ids,
        a_stock_ids=expected_ids,
    )

    adjustment_files = []
    for name in ("gbbq", "gbbq.map"):
        path = cache / name
        if path.is_file():
            adjustment_files.append(
                {
                    "name": name,
                    "path": str(path),
                    "size": path.stat().st_size,
                    "mtime": datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(),
                    "sha256": file_sha256(path),
                }
            )
    adjustment_map = parse_gbbq_map(cache / "gbbq.map") if (cache / "gbbq.map").is_file() else None

    samples = []
    for security_id in ("SH.600000", "SZ.000001", "SZ.300750", "SH.688001"):
        item = day_by_id.get(security_id)
        if not item:
            continue
        path = Path(item["path"])
        first, last = read_edge_records(path)
        samples.append(
            {
                "security_id": security_id,
                "name": tnf_names.get(security_id),
                "first": record_as_dict(first),
                "last": record_as_dict(last),
            }
        )
    bj_sample = next((item for item in valid_results if item["market"] == "BJ" and item["security_id"] in expected_ids), None)
    if bj_sample:
        first, last = read_edge_records(Path(bj_sample["path"]))
        samples.append(
            {
                "security_id": bj_sample["security_id"],
                "name": tnf_names.get(bj_sample["security_id"]),
                "first": record_as_dict(first),
                "last": record_as_dict(last),
            }
        )

    if not day_paths:
        errors.append("No .day files found in sh/sz/bj lday directories.")
    if invalid_results:
        warnings.append(f"{len(invalid_results)} .day files failed complete structural validation.")
    if parse_success_ratio < 0.95:
        errors.append(f"A-stock parse success ratio below 95%: {parse_success_ratio:.4%}")
    if turnover_plausibility_ratio < 0.98:
        errors.append(
            "Amount/volume implied prices do not support the proposed currency-unit/share-unit contract: "
            f"{turnover_plausibility_ratio:.4%} plausible"
        )
    if not assignments:
        errors.append("tdxhy.cfg could not provide current A-stock/industry assignments.")
    if not memberships:
        errors.append("No sector memberships could be parsed.")
    if latest["selected_date_coverage_ratio"] < 0.50:
        errors.append("No trade date reaches 50% coverage across expected A-stock files.")

    adjustment_status = "UNVERIFIED_LOCAL_BINARY"
    warnings.append(
        "Local gbbq data exists, but its binary payload and corporate-action semantics are not independently verified; adjusted-price scanners must remain EXPERIMENTAL."
    )
    warnings.append(
        "Direct visual comparison with the TongdaXin UI remains a manual acceptance check; structural and cross-file checks were automated."
    )
    if errors:
        run_status = "BLOCKED"
    elif adjustment_status != "VERIFIED_REPRODUCIBLE":
        run_status = "DEGRADED_PASS"
    else:
        run_status = "FULL_PASS"

    earliest_dates = [item["first_date"] for item in valid_results]
    by_market = {}
    for market in ("SH", "SZ", "BJ"):
        typed = [item for item in day_results if item["market"] == market]
        by_market[market] = {
            "file_count": len(typed),
            "valid_file_count": sum(item["valid"] for item in typed),
            "invalid_file_count": sum(not item["valid"] for item in typed),
            "record_count": sum(item["record_count"] for item in typed),
        }

    audit = {
        "schema_version": "phase0-audit-v1",
        "run_time": datetime.now().astimezone().isoformat(),
        "run_status": run_status,
        "requested_tdx_root": requested_root or str(tdx_root),
        "resolved_tdx_root": str(tdx_root),
        "source_access_mode": "READ_ONLY",
        "path_correction_applied": bool(requested_root and Path(requested_root) != tdx_root),
        "file_stability": stability,
        "day_contract": {
            "record_length": DAY_RECORD_LENGTH,
            "endianness": "little",
            "struct": "<IIIIIfII",
            "date_encoding": "YYYYMMDD unsigned integer",
            "price_unit": f"stored integer / {PRICE_DIVISOR:g}",
            "amount_unit": "float32 currency units (CNY for A shares), cross-field verified",
            "volume_unit": "uint32 shares for A shares, cross-field verified",
            "unit_crosscheck": {
                "method": "amount / volume compared with stored low/100 and high/100, with 5% tolerance",
                "a_stock_record_count": turnover_checks,
                "plausible_record_count": turnover_plausible,
                "plausibility_ratio": round(turnover_plausibility_ratio, 8),
                "status": "PASS" if turnover_plausibility_ratio >= 0.98 else "FAIL",
            },
            "reserved_field": "uint32 preserved, semantics not required",
            "include_t": True,
            "automated_validation": "COMPLETE_RECORD_SCAN",
            "manual_ui_crosscheck": "PENDING",
        },
        "daily_data": {
            "total_file_count": len(day_results),
            "valid_file_count": len(valid_results),
            "invalid_file_count": len(invalid_results),
            "total_record_count": sum(item["record_count"] for item in day_results),
            "earliest_trade_date": min(earliest_dates) if earliest_dates else None,
            "latest_trade_date": selected_date,
            "by_market": by_market,
            "invalid_file_samples": invalid_results[:50],
            "raw_source_manifest_sha256": raw_manifest_fingerprint(day_paths),
            "edge_record_samples": samples,
        },
        "latest_trade_date_contract": latest,
        "security_master": {
            "capability": "LIMITED",
            "basis": "tdxhy.cfg current industry assignments + local TNF names + frozen code rules",
            "tnf_contracts": tnf_audits,
            "industry_assignment_count": len(assignments),
            "unique_current_a_stock_ids": len(current_a_stock_ids),
            "excluded_b_share_assignment_count": len(assignments) - len(current_a_stock_ids),
            "expected_a_stock_basis": "TDXHY_CURRENT_A_SHARE_MEMBERS_INCLUDING_MISSING_DAY_FILES",
            "expected_a_stock_count": len(expected_ids),
            "parsed_a_stock_count": len(parsed_ids),
            "parse_success_ratio": round(parse_success_ratio, 8),
            "normal_universe_contract": {
                "security_type": "A_STOCK",
                "min_history_days": 120,
                "must_have_selected_trade_date_record": True,
                "normal_universe_count": len(normal_universe_ids),
                "excluded_missing_or_invalid_day_count": len(expected_ids - parsed_ids),
                "excluded_history_below_120_count": sum(
                    1
                    for item in valid_results
                    if item["security_id"] in expected_ids and item["record_count"] < 120
                ),
                "excluded_not_current_on_selected_date_count": sum(
                    1
                    for item in valid_results
                    if item["security_id"] in expected_ids and item["last_date"] != selected_date
                ),
            },
            "tdxhy_members_without_day_file_count": len(missing_day_ids),
            "tdxhy_members_without_day_file_samples": missing_day_ids[:30],
            "security_type_counts_for_day_files": summarize_types(day_results, current_a_stock_ids),
            "limitations": [
                "Historical ST status is unavailable.",
                "Historical names and delisting state are incomplete.",
                "Non-stock subtypes rely partly on conservative code-prefix rules.",
            ],
        },
        "sector_membership": {
            "membership_basis": "CURRENT_TDX_MEMBERSHIP",
            "replay_mode": "APPROXIMATE_CURRENT_MEMBERSHIP",
            "current_membership_bias": True,
            "industry_name_count": len(industry_names),
            "infoharbor": infoharbor_meta,
            **sector_audit,
        },
        "adjustment_contract": {
            "project_price_basis": "RAW",
            "adjustment_status": adjustment_status,
            "adjustment_source": "LOCAL_TDX_GBBQ_CANDIDATE",
            "candidate_files": adjustment_files,
            "map_audit": adjustment_map,
            "ohlc_adjustment_rule": None,
            "volume_adjustment_rule": None,
            "amount_basis": "RAW_AMOUNT",
            "formal_trend_scanners_allowed": False,
            "requires_adjusted_price_policy": "Any multi-day price-structure factor or scanner is EXPERIMENTAL until adjustment semantics are verified.",
        },
        "contracts": {
            "factor_contract_version": "factor-contract-v0.3-phase0",
            "universe_version": "normal-universe-v0.3-phase0",
            "sector_validity_version": "sector-validity-v0.3-phase0",
            "score_mapping_version": None,
            "scanner_version": None,
        },
        "runtime_seconds": round(time.perf_counter() - started, 3),
        "warnings": warnings,
        "errors": errors,
    }
    atomic_write_json(output, audit, tdx_root)
    return audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Phase 0 audit of local TongdaXin data")
    parser.add_argument("--tdx-root", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/phase0/TDX_DATA_AUDIT.json"))
    parser.add_argument("--requested-root", default=None, help="Original user-supplied path for traceability")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = run_audit(args.tdx_root, args.output, requested_root=args.requested_root)
    print(json.dumps({
        "run_status": audit["run_status"],
        "output": str(args.output.resolve()),
        "latest_trade_date": audit["daily_data"]["latest_trade_date"],
        "valid_day_files": audit["daily_data"]["valid_file_count"],
        "invalid_day_files": audit["daily_data"]["invalid_file_count"],
        "parse_success_ratio": audit["security_master"]["parse_success_ratio"],
        "runtime_seconds": audit["runtime_seconds"],
    }, ensure_ascii=False, indent=2))
    return 0 if audit["run_status"] != "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
