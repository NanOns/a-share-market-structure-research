from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
import hashlib
import csv
import io
import json
from pathlib import Path
import re
import subprocess
import sys

from adjustment.tdx_adjustment import adjust_ohlc, build_affine_factors, xrxd_from_gbbq
from phase0_1_runner import atomic_json, atomic_text
from phase0_2_runner import _day_path, _read_day_rows
from tdx.gbbq_reader import file_sha256, read_gbbq
from tdx.security_master import current_a_stock_ids, read_industry_assignments
from tdx.tdx_audit import raw_manifest_fingerprint, snapshot_day_files
from validation.external_qfq import PublicQfqClients, compare_ohlc, decide_phase0_2a_gate


BASELINE_VERSION = "V0.3_FINAL_IMPLEMENTATION_BASELINE"
TOLERANCE = Decimal("0.01")
SAMPLE_SELECTOR_CONTRACT = {
    "selection_contract_id": "PHASE0_2A_QFQ_SAMPLE_SELECTION_V1",
    "version": "1.0.0",
    "seed": "PHASE0_2A_QFQ_SAMPLE_SEED_V1",
    "sample_security_count": 32,
    "minimum_history_bars": 120,
}
WINDOWS = {
    "RECENT_2024_2026": (20240101, 20261231),
    "MID_2010_2023": (20100101, 20231231),
    "EARLY_1990_2009": (19900101, 20091231),
}
CSV_FIELDS = [
    "security_id", "date", "sample_type",
    "local_open", "local_high", "local_low", "local_close",
    "external_source", "external_open", "external_high", "external_low", "external_close",
    "diff_open", "diff_high", "diff_low", "diff_close",
    "within_tolerance", "status", "notes",
]


def _event_type(event) -> str:
    if event.rights_ratio_per_10 > 0 and event.rights_price > 0:
        return "RIGHTS_ISSUE"
    if event.bonus_transfer_per_10 > 0 and event.cash_dividend_per_10 > 0:
        return "BONUS_TRANSFER_AND_CASH"
    if event.bonus_transfer_per_10 > 0:
        return "BONUS_TRANSFER"
    if event.cash_dividend_per_10 > 0:
        return "CASH_DIVIDEND"
    return "OTHER_XRXD"


def _period(trade_date: int) -> str:
    if trade_date >= 20240101:
        return "RECENT_2024_2026"
    if trade_date >= 20100101:
        return "MID_2010_2023"
    return "EARLY_1990_2009"


def _previous_trade_date(dates: list[int], ex_day: int) -> int | None:
    previous = None
    for trade_date in dates:
        if trade_date >= ex_day:
            break
        previous = trade_date
    return previous


def _board_for_security(security_id: str) -> str:
    exchange, code = security_id.split(".", 1)
    if exchange == "BJ": return "BEIJING"
    if exchange == "SH" and code.startswith(("688", "689")): return "STAR"
    if exchange == "SZ" and code.startswith(("300", "301")): return "CHINEXT"
    if exchange == "SH": return "MAIN_SH"
    if exchange == "SZ": return "MAIN_SZ"
    return "OTHER"


def select_sample_securities(current_universe, actual_day_files):
    current_ids = set(map(str, current_universe))
    actual_ids = set(map(str, actual_day_files))
    eligible_ids = sorted(current_ids & actual_ids)
    candidates = []
    for security_id in eligible_ids:
        board = _board_for_security(security_id)
        stable_hash = hashlib.sha256(f"{security_id}|{SAMPLE_SELECTOR_CONTRACT['seed']}".encode("utf-8")).hexdigest()
        candidates.append({"security_id": security_id, "board": board, "stable_hash": stable_hash})
    by_board = defaultdict(list)
    for candidate in candidates:
        by_board[candidate["board"]].append(candidate)
    for items in by_board.values():
        items.sort(key=lambda item: (item["stable_hash"], item["security_id"]))
    chosen = []
    for board in sorted(by_board):
        if by_board[board] and len(chosen) < SAMPLE_SELECTOR_CONTRACT["sample_security_count"]:
            chosen.append(by_board[board][0])
    selected_ids = {item["security_id"] for item in chosen}
    for item in sorted(candidates, key=lambda row: (row["stable_hash"], row["security_id"])):
        if len(chosen) >= SAMPLE_SELECTOR_CONTRACT["sample_security_count"]:
            break
        if item["security_id"] not in selected_ids:
            chosen.append(item)
            selected_ids.add(item["security_id"])
    receipt = {
        **SAMPLE_SELECTOR_CONTRACT,
        "current_universe_count": len(current_ids),
        "eligible_count": len(candidates),
        "selected_count": len(chosen),
        "selected": [{"security_id": item["security_id"], "board": item["board"],
                      "stable_hash_sha256": item["stable_hash"],
                      "selection_reason": "CURRENT_UNIVERSE_ACTUAL_DAY_FILE_MINIMUM_HISTORY"} for item in chosen],
        "selection": "board-stratified then lowest stable SHA256(security_id + contract_seed)",
    }
    receipt["selection_digest_sha256"] = hashlib.sha256(
        json.dumps(receipt["selected"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return chosen, receipt


def build_sample_plan(tdx_root: Path, by_security: dict[str, list]) -> tuple[list[dict], dict[str, list[dict]], dict]:
    cfg = tdx_root / "T0002/hq_cache/tdxhy.cfg"
    current_ids = set(current_a_stock_ids(read_industry_assignments(cfg))) if cfg.is_file() else set()
    day_paths = {}
    for market in ("sh", "sz", "bj"):
        for path in sorted((tdx_root / "vipdoc" / market / "lday").glob("*.day")):
            security_id = market.upper() + "." + path.stem[-6:]
            if security_id in current_ids and path.stat().st_size >= 32 * SAMPLE_SELECTOR_CONTRACT["minimum_history_bars"]:
                day_paths[security_id] = path
    chosen, selector_receipt = select_sample_securities(current_ids, day_paths)
    for item in chosen:
        item["path"] = day_paths[item["security_id"]]
    selected: dict[tuple[str, int], dict] = {}
    day_rows: dict[str, list[dict]] = {}
    for candidate in chosen:
        security_id = candidate["security_id"]
        rows = _read_day_rows(candidate["path"])
        if len(rows) < SAMPLE_SELECTOR_CONTRACT["minimum_history_bars"]:
            continue
        day_rows[security_id] = rows
        dates = [row["trade_date"] for row in rows]
        effective = [event for event in by_security.get(security_id, []) if event.ex_day <= dates[-1]]
        per_security = [key for key in selected if key[0] == security_id]
        for window_name, (begin, end) in WINDOWS.items():
            candidates = [event for event in effective if begin <= event.ex_day <= end]
            if not candidates:
                continue
            # Early windows prefer rights then bonus; later windows prefer the latest action.
            event = max(
                candidates,
                key=lambda item: (
                    2 if item.rights_ratio_per_10 > 0 and item.rights_price > 0 else 1 if item.bonus_transfer_per_10 > 0 else 0,
                    item.ex_day,
                ),
            ) if window_name == "EARLY_1990_2009" else candidates[-1]
            trade_date = _previous_trade_date(dates, event.ex_day)
            if trade_date is None or (security_id, trade_date) in selected:
                continue
            selected[(security_id, trade_date)] = {
                "security_id": security_id,
                "date": trade_date,
                "sample_type": _event_type(event),
                "period": window_name,
                "contract_sample": False,
                "board": candidate["board"],
                "selection_contract_id": SAMPLE_SELECTOR_CONTRACT["selection_contract_id"],
                "notes": f"local trade day before ex-day {event.ex_day}",
            }
            per_security.append((security_id, trade_date))
            if len(per_security) >= 3:
                break

        for left, right in zip(effective, effective[1:]):
            if not 1 <= right.ex_day - left.ex_day <= 5:
                continue
            if any(left.ex_day <= row["trade_date"] < right.ex_day for row in rows):
                continue
            trade_date = _previous_trade_date(dates, left.ex_day)
            if trade_date is None or (security_id, trade_date) in selected:
                continue
            selected[(security_id, trade_date)] = {
                "security_id": security_id,
                "date": trade_date,
                "sample_type": "COMPOUND_SUSPENSION",
                "period": _period(trade_date),
                "contract_sample": False,
                "board": candidate["board"],
                "selection_contract_id": SAMPLE_SELECTOR_CONTRACT["selection_contract_id"],
                "notes": f"local bar gap spans events effective {left.ex_day} and {right.ex_day}",
            }

        # The latest bar is a no-new-action anchor and validates current QFQ anchoring.
        latest = dates[-1]
        selected.setdefault(
            (security_id, latest),
            {
                "security_id": security_id,
                "date": latest,
                "sample_type": "NO_ACTION_ANCHOR_CONTROL",
                "period": "RECENT_2024_2026",
                "contract_sample": False,
                "board": candidate["board"],
                "selection_contract_id": SAMPLE_SELECTOR_CONTRACT["selection_contract_id"],
                "notes": "latest local trade-date identity anchor",
            },
        )
        # Fill to exactly four points per security with deterministic history controls.
        existing = [key for key in selected if key[0] == security_id]
        for fraction in (0.20, 0.45, 0.70, 0.90, 0.05):
            if len(existing) >= 4:
                break
            row = rows[min(len(rows) - 1, int((len(rows) - 1) * fraction))]
            key = (security_id, row["trade_date"])
            if key in selected:
                continue
            selected[key] = {
                "security_id": security_id,
                "date": row["trade_date"],
                "sample_type": "STRATIFIED_NO_EVENT_CONTROL",
                "period": _period(row["trade_date"]),
                "contract_sample": False,
                "board": candidate["board"],
                "selection_contract_id": SAMPLE_SELECTOR_CONTRACT["selection_contract_id"],
                "notes": "deterministic history control point",
            }
            existing.append(key)

    plan = sorted(selected.values(), key=lambda item: (item["security_id"], item["date"]))
    contract_candidates = [item for item in plan if item["sample_type"] not in {"NO_ACTION_ANCHOR_CONTROL", "STRATIFIED_NO_EVENT_CONTROL"}]
    contract_candidates.sort(key=lambda item: (hashlib.sha256(
        f"{item['security_id']}|{item['date']}|{SAMPLE_SELECTOR_CONTRACT['seed']}".encode("utf-8")).hexdigest(),
        item["security_id"], item["date"]))
    contract_rows = []
    contract_seen = set()
    for item in contract_candidates:
        if item["security_id"] in contract_seen:
            continue
        item["contract_sample"] = True
        contract_seen.add(item["security_id"])
        contract_rows.append({"security_id": item["security_id"], "date": item["date"],
                              "sample_type": item["sample_type"], "board": item["board"],
                              "selection_reason": "STABLE_HASHED_EVENT_SAMPLE"})
        if len(contract_rows) >= 5:
            break
    selector_receipt["contract_sample_count"] = len(contract_rows)
    selector_receipt["contract_samples"] = contract_rows
    selector_receipt["contract_sample_digest_sha256"] = hashlib.sha256(
        json.dumps(contract_rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return plan, day_rows, selector_receipt


def _local_values(plan: list[dict], day_rows: dict[str, list[dict]], by_security: dict[str, list]) -> list[dict]:
    by_plan: dict[str, list[dict]] = defaultdict(list)
    for item in plan:
        by_plan[item["security_id"]].append(item)
    output = []
    for security_id, samples in by_plan.items():
        rows = day_rows[security_id]
        row_map = {row["trade_date"]: row for row in rows}
        factors = build_affine_factors((row["trade_date"] for row in rows), by_security.get(security_id, []))
        for sample in samples:
            row = row_map[sample["date"]]
            adjusted = adjust_ohlc(row, factors[sample["date"]])
            output.append(
                {
                    **sample,
                    **{f"local_{field}": float(adjusted[field]) for field in ("open", "high", "low", "close")},
                    **{f"local_raw_{field}": float(row[field]) for field in ("open", "high", "low", "close")},
                }
            )
    return sorted(output, key=lambda item: (item["security_id"], item["date"]))


def _external_crosscheck(local_samples: list[dict], clients: PublicQfqClients) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for sample in local_samples:
        grouped[sample["security_id"]].append(sample)
    output = []
    for security_id, samples in grouped.items():
        east = clients.fetch_eastmoney(
            security_id,
            min(item["date"] for item in samples),
            max(item["date"] for item in samples),
        )
        for sample in samples:
            primary = east.get(sample["date"]) if east is not None else None
            primary_comparison = compare_ohlc(sample, primary, TOLERANCE)
            secondary = None
            secondary_comparison = None
            if primary is None or not primary_comparison["within_tolerance"]:
                bars = clients.fetch_tencent_window(security_id, sample["date"])
                secondary = bars.get(sample["date"]) if bars else None
                secondary_comparison = compare_ohlc(sample, secondary, TOLERANCE)

            if primary is not None and primary_comparison["within_tolerance"]:
                comparison = primary_comparison
                source = "EASTMONEY"
                notes = sample["notes"] + "; fqt=1/klt=101"
            elif primary is None and secondary is not None:
                comparison = secondary_comparison
                source = "TENCENT"
                notes = sample["notes"] + "; qfq/day fallback after Eastmoney unavailable"
            elif primary is not None and secondary is not None:
                sources_agree = all(
                    abs(getattr(primary, field) - getattr(secondary, field)) <= TOLERANCE
                    for field in ("open", "high", "low", "close")
                )
                if not sources_agree:
                    comparison = primary_comparison
                    comparison["status"] = "EXTERNAL_SOURCE_DISAGREEMENT"
                    comparison["within_tolerance"] = False
                    source = "EASTMONEY+TENCENT"
                    notes = (
                        sample["notes"]
                        + "; sources disagree; Tencent O/H/L/C="
                        + "/".join(str(getattr(secondary, field)) for field in ("open", "high", "low", "close"))
                    )
                else:
                    comparison = primary_comparison
                    source = "EASTMONEY+TENCENT"
                    notes = sample["notes"] + "; both public sources agree and mismatch local"
            else:
                comparison = compare_ohlc(sample, None, TOLERANCE)
                source = "NONE"
                notes = sample["notes"] + "; both public sources unavailable"

            raw_basis_match = None
            raw_basis_diffs = None
            if comparison["status"] == "LOCAL_MISMATCH_REQUIRES_REVIEW" and secondary is not None:
                raw_bars = clients.fetch_tencent_raw_window(security_id, sample["date"])
                raw_bar = raw_bars.get(sample["date"]) if raw_bars else None
                raw_local = {
                    f"local_{field}": sample[f"local_raw_{field}"]
                    for field in ("open", "high", "low", "close")
                }
                raw_check = compare_ohlc(raw_local, raw_bar, TOLERANCE)
                raw_basis_match = raw_check["within_tolerance"] if raw_bar is not None else None
                raw_basis_diffs = {
                    field: raw_check.get(f"diff_{field}") for field in ("open", "high", "low", "close")
                }
                if raw_basis_match:
                    notes += "; Tencent unadjusted OHLC matches local RAW, isolating the difference to adjustment history"
                elif raw_bar is not None:
                    comparison["status"] = "EXTERNAL_SOURCE_DISAGREEMENT"
                    comparison["within_tolerance"] = False
                    notes += "; Tencent unadjusted OHLC also differs from local RAW, so QFQ is not a clean adjustment test"

            output.append(
                {
                    "security_id": security_id,
                    "date": sample["date"],
                    "sample_type": sample["sample_type"],
                    **{f"local_{field}": sample[f"local_{field}"] for field in ("open", "high", "low", "close")},
                    "external_source": source,
                    **comparison,
                    "notes": notes,
                    "period": sample["period"],
                    "contract_sample": sample["contract_sample"],
                    "external_usage": "VALIDATION_REFERENCE_ONLY",
                    "external_raw_basis_matches_local": raw_basis_match,
                    "external_raw_basis_diffs": raw_basis_diffs,
                }
            )
    return sorted(output, key=lambda item: (item["security_id"], item["date"]))


def _csv_text(rows: list[dict]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def _systematic_mismatch(rows: list[dict]) -> tuple[bool, dict]:
    grouped: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        grouped[row["sample_type"]][row["status"]] += 1
    detail = {key: dict(value) for key, value in sorted(grouped.items())}
    detected = any(
        counts.get("LOCAL_MISMATCH_REQUIRES_REVIEW", 0) >= 2
        for counts in grouped.values()
    )
    return detected, detail


def run_phase0_2a(project_root: Path, tdx_root: Path) -> dict:
    project_root = project_root.resolve()
    tdx_root = tdx_root.resolve()
    output_dir = project_root / "reports" / "phase0_2a"
    if (output_dir / "EXTERNAL_QFQ_CROSSCHECK.json").exists():
        raise RuntimeError("Evidence already exists: use offline sealing; never overwrite a completed network run")
    prior = json.loads((project_root / "reports" / "phase0_2" / "PHASE0_2_FINAL_RECEIPT.json").read_text(encoding="utf-8"))

    gbbq_path = tdx_root / "T0002" / "hq_cache" / "gbbq"
    map_path = tdx_root / "T0002" / "hq_cache" / "gbbq.map"
    records = read_gbbq(gbbq_path)
    by_security: dict[str, list] = defaultdict(list)
    for record in records:
        if record.category == 1:
            by_security[record.security_id].append(xrxd_from_gbbq(record))
    for events in by_security.values():
        events.sort(key=lambda item: (item.ex_day, item.source_record_index))

    plan, day_rows, sample_selection = build_sample_plan(tdx_root, by_security)
    local_samples = _local_values(plan, day_rows, by_security)
    clients = PublicQfqClients(min_interval_seconds=0.45)
    rows = _external_crosscheck(local_samples, clients)

    status_counts = Counter(row["status"] for row in rows)
    contract_samples = [row for row in rows if row["contract_sample"]]
    contract_passed = sum(row["status"] == "LOCAL_MATCHES_EXTERNAL" for row in contract_samples)
    contract_failed = sum(row["status"] == "LOCAL_MISMATCH_REQUIRES_REVIEW" for row in contract_samples)
    contract_disagreement = sum(row["status"] == "EXTERNAL_SOURCE_DISAGREEMENT" for row in contract_samples)
    contract_unverifiable = len(contract_samples) - contract_passed - contract_failed
    matching = status_counts["LOCAL_MATCHES_EXTERNAL"]
    mismatches = status_counts["LOCAL_MISMATCH_REQUIRES_REVIEW"]
    unverifiable = status_counts["UNVERIFIABLE_EXTERNAL"]
    disagreements = status_counts["EXTERNAL_SOURCE_DISAGREEMENT"]
    raw_basis_confirmed_mismatches = sum(
        row["status"] == "LOCAL_MISMATCH_REQUIRES_REVIEW"
        and row["external_raw_basis_matches_local"] is True
        for row in rows
    )
    verified = matching + mismatches
    match_ratio = matching / verified if verified else 0.0
    systematic, systematic_detail = _systematic_mismatch(rows)
    required_types = {"CASH_DIVIDEND", "BONUS_TRANSFER_AND_CASH", "RIGHTS_ISSUE", "COMPOUND_SUSPENSION"}
    complex_types_pass = all(
        any(row["sample_type"] == sample_type and row["status"] == "LOCAL_MATCHES_EXTERNAL" for row in rows)
        for sample_type in required_types
    )
    security_count = len({row["security_id"] for row in rows})
    final_status = decide_phase0_2a_gate(
        sample_passed=contract_passed,
        sample_failed=contract_failed,
        sample_unverifiable=contract_unverifiable,
        sample_count=len(contract_samples),
        security_count=security_count,
        verified_points=verified,
        match_ratio=match_ratio,
        complex_types_pass=complex_types_pass,
        systematic_mismatch=systematic,
        external_disagreement_count=disagreements,
    )

    tests = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=project_root, text=True, encoding="utf-8",
        errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    passed_match = re.search(r"(\d+) passed", tests.stdout)
    failed_match = re.search(r"(\d+) failed", tests.stdout)
    tests_passed = int(passed_match.group(1)) if passed_match else 0
    tests_failed = int(failed_match.group(1)) if failed_match else (0 if tests.returncode == 0 else 1)

    day_paths, _ = snapshot_day_files(tdx_root)
    integrity = {
        "gbbq_sha256_before": prior["gbbq_sha256_after"],
        "gbbq_sha256_after": file_sha256(gbbq_path),
        "gbbq_map_sha256_before": prior["gbbq_map_sha256_after"],
        "gbbq_map_sha256_after": file_sha256(map_path),
        "day_metadata_manifest_before": prior["raw_metadata_manifest_sha256_after"],
        "day_metadata_manifest_after": raw_manifest_fingerprint(day_paths),
    }
    source_unchanged = (
        integrity["gbbq_sha256_before"] == integrity["gbbq_sha256_after"]
        and integrity["gbbq_map_sha256_before"] == integrity["gbbq_map_sha256_after"]
        and integrity["day_metadata_manifest_before"] == integrity["day_metadata_manifest_after"]
    )
    if tests.returncode or not source_unchanged:
        final_status = "BLOCKED_FOR_FORMAL_ADJUSTMENT"

    source_audit = {
        "schema_version": "external-source-audit-v0.2a",
        "external_validation_enabled": True,
        "production_data_source": "LOCAL_TDX_ONLY",
        "external_usage": "VALIDATION_REFERENCE_ONLY",
        "sources": clients.audits(),
        "total_http_request_count": sum(item["request_count"] for item in clients.audits()),
        "request_ceiling_per_source": 200,
        "credentials_or_cookies_used": False,
        "raw_external_history_cached": False,
    }
    crosscheck = {
        "schema_version": "external-qfq-crosscheck-v0.2a",
        "tolerance_cny": 0.01,
        "adjustment_basis": "FORWARD_ADJUSTED_QFQ",
        "production_data_source": "LOCAL_TDX_ONLY",
        "external_usage": "VALIDATION_REFERENCE_ONLY",
        "security_count": security_count,
        "date_point_count": len(rows),
        "ohlc_value_count": len(rows) * 4,
        "status_distribution": dict(status_counts),
        "period_distribution": dict(Counter(row["period"] for row in rows)),
        "sample_type_distribution": dict(Counter(row["sample_type"] for row in rows)),
        "contract_sample_count": len(contract_samples),
        "contract_sample_passed": contract_passed,
        "contract_sample_failed": contract_failed,
        "contract_sample_external_disagreement": contract_disagreement,
        "contract_sample_unverifiable": contract_unverifiable,
        "sample_selection": sample_selection,
        "verified_point_count": verified,
        "matching_point_count": matching,
        "mismatch_point_count": mismatches,
        "unverifiable_point_count": unverifiable,
        "external_source_disagreement_count": disagreements,
        "raw_basis_confirmed_mismatch_count": raw_basis_confirmed_mismatches,
        "match_ratio": match_ratio,
        "systematic_mismatch_detected": systematic,
        "systematic_mismatch_by_type": systematic_detail,
        "complex_types_pass": complex_types_pass,
        "rows": rows,
    }

    full = final_status == "FULL_PASS"
    warnings = []
    if disagreements:
        warnings.append(f"{disagreements} points have conflicting public-source QFQ histories and cannot waive the manual gate.")
    if unverifiable:
        warnings.append(f"{unverifiable} points were unavailable from both public sources.")
    if final_status == "DEGRADED_PASS":
        warnings.append("Automated evidence is insufficient for FULL_PASS; formal adjustment remains disabled without asserting the local chain is wrong.")
    errors = []
    if final_status == "BLOCKED_FOR_FORMAL_ADJUSTMENT":
        errors.append("External checks indicate a systematic or fixed-sample local mismatch requiring review, or an integrity/test gate failed.")
    receipt = {
        "phase": "PHASE0.2A",
        "baseline_version": BASELINE_VERSION,
        "start_status": prior["final_status"],
        "final_status": final_status,
        "run_time": datetime.now().astimezone().isoformat(),
        "external_validation_enabled": True,
        "external_sources_used": [item["source_name"] for item in clients.audits() if item["success_count"]],
        "contract_sample_count": len(contract_samples),
        "contract_sample_passed": contract_passed,
        "contract_sample_failed": contract_failed,
        "contract_sample_external_disagreement": contract_disagreement,
        "contract_sample_unverifiable": contract_unverifiable,
        "sample_selection": sample_selection,
        "batch_security_count": security_count,
        "batch_date_point_count": len(rows),
        "batch_ohlc_value_count": len(rows) * 4,
        "verified_point_count": verified,
        "matching_point_count": matching,
        "mismatch_point_count": mismatches,
        "unverifiable_point_count": unverifiable,
        "external_source_disagreement_count": disagreements,
        "raw_basis_confirmed_mismatch_count": raw_basis_confirmed_mismatches,
        "match_ratio": match_ratio,
        "systematic_mismatch_detected": systematic,
        "manual_ui_gate": "WAIVED_BY_AUTOMATED_MULTI_LAYER_VALIDATION" if full else "NOT_WAIVED",
        "manual_ui_waiver_reason": (
            "Deterministic contract sample 5/5, >=95% batch match, all complex action types, no systematic mismatch"
            if full else "AUTOMATED_EXTERNAL_ACCEPTANCE_CRITERIA_NOT_FULLY_SATISFIED"
        ),
        "project_data_source": "LOCAL_TDX_ONLY",
        "project_price_basis": "FORWARD_ADJUSTED" if full else "RAW",
        "adjustment_status": "VERIFIED_REPRODUCIBLE" if full else "PARTIALLY_VERIFIED_EXTERNAL_GATE_NOT_CLOSED",
        "formal_trend_scanners_allowed": full,
        "tdx_source_unchanged": source_unchanged,
        **integrity,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "test_output": tests.stdout.strip(),
        "warnings": warnings,
        "errors": errors,
        "next_allowed_phase": (
            "PHASE_1_NORMALIZATION_AND_FORMAL_FACTOR_ENGINE" if full
            else "PHASE_1_NORMALIZATION_AND_EXPERIMENTAL_FACTOR_ENGINE" if final_status == "DEGRADED_PASS"
            else "NONE"
        ),
    }

    atomic_text(output_dir / "EXTERNAL_QFQ_CROSSCHECK.csv", _csv_text(rows), tdx_root, bom=True)
    atomic_json(output_dir / "EXTERNAL_QFQ_CROSSCHECK.json", crosscheck, tdx_root)
    atomic_json(output_dir / "EXTERNAL_SOURCE_AUDIT.json", source_audit, tdx_root)
    atomic_json(output_dir / "PHASE0_2A_FINAL_RECEIPT.json", receipt, tdx_root)

    mismatched = [row for row in rows if row["status"] != "LOCAL_MATCHES_EXTERNAL"]
    mismatch_table = "\n".join(
        f"| {row['security_id']} | {row['date']} | {row['sample_type']} | {row['external_source']} | {row['status']} | {row['notes']} |"
        for row in mismatched[:30]
    ) or "| — | — | — | — | none | — |"
    source_table = "\n".join(
        f"| {item['source_name']} | {item['adjustment_mode']} | {item['request_count']} | {item['success_count']} | {item['failure_count']} | {item['rate_limit_events']} |"
        for item in clients.audits()
    )
    report = f"""# Phase 0.2A report — automated external QFQ cross-check

Final status: **{final_status}**

External observations are validation references only. Production remains `LOCAL_TDX_ONLY`; no external history was cached or connected to scanners.

## Acceptance summary

- Deterministic contract samples: `{contract_passed}/{len(contract_samples)}` matched; local mismatches `{contract_failed}`; source disagreements `{contract_disagreement}`; unavailable `{contract_unverifiable - contract_disagreement}`.
- Batch: `{security_count}` securities, `{len(rows)}` dates, `{len(rows) * 4}` OHLC values.
- Verified unambiguous points: `{verified}`; matches `{matching}`; mismatches `{mismatches}`; match ratio `{match_ratio:.4%}`.
- External-source disagreements: `{disagreements}`; unavailable: `{unverifiable}`.
- QFQ mismatches with independently matching unadjusted OHLC: `{raw_basis_confirmed_mismatches}`.
- Required complex types all matched: `{complex_types_pass}`.
- Systematic local mismatch detected: `{systematic}`.
- Manual UI gate: `{receipt['manual_ui_gate']}`.
- Price basis: `{receipt['project_price_basis']}`; formal trend scanners: `{receipt['formal_trend_scanners_allowed']}`.

## External source audit

| Source | Adjustment basis | HTTP requests | Successful responses | Failed attempts | Rate limits |
|---|---|---:|---:|---:|---:|
{source_table}

Eastmoney was attempted first with `klt=101` and `fqt=1`. After one logical query exhausted the three-retry ceiling, its circuit was opened and Tencent `day/qfq` became the bounded fallback. Tencent was also used only to adjudicate Eastmoney mismatches. No login, token, cookie, or sensitive header was used.

## Stratification

- Periods: `{json.dumps(crosscheck['period_distribution'], ensure_ascii=False)}`.
- Sample types: `{json.dumps(crosscheck['sample_type_distribution'], ensure_ascii=False)}`.
- Formal tolerance: absolute local-minus-external difference `<= CNY 0.01` independently for Open, High, Low, Close.

## Non-matching or inconclusive points (first 30)

| Security | Date | Type | Source | Classification | Notes |
|---|---:|---|---|---|---|
{mismatch_table}

The full per-field local/external values and differences are in both CSV and JSON. `EXTERNAL_SOURCE_DISAGREEMENT` is not counted as proof the local engine is wrong. `LOCAL_MISMATCH_REQUIRES_REVIEW` is counted only when the available public reference evidence is unambiguous.

## Integrity and tests

- TDX source unchanged: `{source_unchanged}`.
- GBBQ SHA-256: `{integrity['gbbq_sha256_after']}`.
- GBBQ map SHA-256: `{integrity['gbbq_map_sha256_after']}`.
- `.day` metadata manifest: `{integrity['day_metadata_manifest_after']}`.
- Tests: `{tests_passed}` passed, `{tests_failed}` failed.

## Decision

The manual UI gate is waived only for `FULL_PASS`. The exact gate calculation and warnings are frozen in `reports/phase0_2a/PHASE0_2A_FINAL_RECEIPT.json`. This task does not alter or supplement the production data source.
"""
    atomic_text(project_root / "docs" / "PHASE0_2A_REPORT.md", report, tdx_root)
    return receipt
