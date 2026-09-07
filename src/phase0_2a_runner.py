from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
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
from tdx.tdx_audit import raw_manifest_fingerprint, snapshot_day_files
from validation.external_qfq import PublicQfqClients, compare_ohlc, decide_phase0_2a_gate


BASELINE_VERSION = "V0.3_FINAL_IMPLEMENTATION_BASELINE"
TOLERANCE = Decimal("0.01")
FIXED_SAMPLES = [
    {"security_id": "SH.600519", "date": 20250625, "sample_type": "CASH_DIVIDEND", "notes": "fixed Phase 0.2 sample; ex-day 20250626"},
    {"security_id": "SZ.000651", "date": 20150702, "sample_type": "BONUS_TRANSFER_AND_CASH", "notes": "fixed Phase 0.2 sample; ex-day 20150703"},
    {"security_id": "SZ.000651", "date": 20000803, "sample_type": "RIGHTS_ISSUE", "notes": "fixed Phase 0.2 sample; ex-day 20000804"},
    {"security_id": "SH.600519", "date": 20060425, "sample_type": "COMPOUND_SUSPENSION", "notes": "fixed Phase 0.2 sample; ex-days 20060519 and 20060524"},
    {"security_id": "SZ.000001", "date": 20260611, "sample_type": "RECENT_CASH_DIVIDEND", "notes": "fixed Phase 0.2 sample; ex-day 20260612"},
]
CANDIDATE_SECURITIES = [
    "SH.600000", "SH.600036", "SH.600276", "SH.600309", "SH.600519", "SH.600887",
    "SH.601012", "SH.601318", "SH.601398", "SH.601857", "SH.603259",
    "SZ.000001", "SZ.000002", "SZ.000333", "SZ.000651", "SZ.000858", "SZ.002415",
    "SZ.002475", "SZ.002594", "SZ.002714", "SZ.003816",
    "SZ.300059", "SZ.300122", "SZ.300274", "SZ.300750", "SZ.300760",
    "SH.688001", "SH.688008", "SH.688111", "SH.688981",
    "BJ.920000", "BJ.920099",
]
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


def build_sample_plan(tdx_root: Path, by_security: dict[str, list]) -> tuple[list[dict], dict[str, list[dict]]]:
    selected: dict[tuple[str, int], dict] = {
        (item["security_id"], item["date"]): {**item, "fixed_sample": True, "period": _period(item["date"])}
        for item in FIXED_SAMPLES
    }
    day_rows: dict[str, list[dict]] = {}
    available = [sid for sid in CANDIDATE_SECURITIES if _day_path(tdx_root, sid).is_file()]
    for security_id in available:
        rows = _read_day_rows(_day_path(tdx_root, security_id))
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
                "fixed_sample": False,
                "notes": f"local trade day before ex-day {event.ex_day}",
            }
            per_security.append((security_id, trade_date))
            if len(per_security) >= 3:
                break

        # The latest bar is a no-new-action anchor and validates current QFQ anchoring.
        latest = dates[-1]
        selected.setdefault(
            (security_id, latest),
            {
                "security_id": security_id,
                "date": latest,
                "sample_type": "NO_ACTION_ANCHOR_CONTROL",
                "period": "RECENT_2024_2026",
                "fixed_sample": False,
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
                "fixed_sample": False,
                "notes": "deterministic history control point",
            }
            existing.append(key)

    plan = sorted(selected.values(), key=lambda item: (item["security_id"], item["date"]))
    return plan, day_rows


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
                    "fixed_sample": sample["fixed_sample"],
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

    plan, day_rows = build_sample_plan(tdx_root, by_security)
    local_samples = _local_values(plan, day_rows, by_security)
    clients = PublicQfqClients(min_interval_seconds=0.45)
    rows = _external_crosscheck(local_samples, clients)

    status_counts = Counter(row["status"] for row in rows)
    fixed = [row for row in rows if row["fixed_sample"]]
    fixed_passed = sum(row["status"] == "LOCAL_MATCHES_EXTERNAL" for row in fixed)
    fixed_failed = sum(row["status"] == "LOCAL_MISMATCH_REQUIRES_REVIEW" for row in fixed)
    fixed_disagreement = sum(row["status"] == "EXTERNAL_SOURCE_DISAGREEMENT" for row in fixed)
    fixed_unverifiable = len(fixed) - fixed_passed - fixed_failed
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
        fixed_passed=fixed_passed,
        fixed_failed=fixed_failed,
        fixed_unverifiable=fixed_unverifiable,
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
        "fixed_sample_count": len(fixed),
        "fixed_sample_passed": fixed_passed,
        "fixed_sample_failed": fixed_failed,
        "fixed_sample_external_disagreement": fixed_disagreement,
        "fixed_sample_unverifiable": fixed_unverifiable,
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
        "fixed_sample_count": len(fixed),
        "fixed_sample_passed": fixed_passed,
        "fixed_sample_failed": fixed_failed,
        "fixed_sample_external_disagreement": fixed_disagreement,
        "fixed_sample_unverifiable": fixed_unverifiable,
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
            "Fixed 5/5, >=95% batch match, all complex action types, no systematic mismatch"
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

- Fixed samples: `{fixed_passed}/5` matched; local mismatches `{fixed_failed}`; source disagreements `{fixed_disagreement}`; unavailable `{fixed_unverifiable - fixed_disagreement}`.
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
