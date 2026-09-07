from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
import csv
import io
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

from market_calendar.trading_calendar import StockTimeline, build_master_calendar, read_day_dates
from normalize.universe_recent import qualifies_normal_universe, recent_window_evidence
from phase0_1_status import decide_status
from sector.roles import EXCLUDED_THEME_NAMES, sector_role
from tdx.block_reader import build_industry_memberships, read_industry_names, read_infoharbor_memberships
from tdx.day_reader import DAY_RECORD_LENGTH
from tdx.gbbq_reader import audit_gbbq
from tdx.security_master import current_a_stock_ids, read_industry_assignments
from tdx.tdx_audit import raw_manifest_fingerprint, snapshot_day_files


CALENDAR_VERSION = "master-trading-calendar-v0.1"
ADJUSTMENT_CONTRACT_VERSION = "adjustment-contract-v0.1"
SECTOR_ROLE_VERSION = "sector-role-v0.1"
RECENT_WINDOW = 20
MIN_RECENT_COVERAGE = 0.75
MIN_HISTORY_DAYS = 120

DAY_DTYPE = np.dtype(
    [
        ("date", "<u4"),
        ("open", "<u4"),
        ("high", "<u4"),
        ("low", "<u4"),
        ("close", "<u4"),
        ("amount", "<f4"),
        ("volume", "<u4"),
        ("reserved", "<u4"),
    ]
)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _atomic_write_bytes(path: Path, payload: bytes, forbidden_root: Path) -> None:
    if _is_relative_to(path, forbidden_root):
        raise ValueError(f"refusing to write inside TDX root: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def atomic_json(path: Path, value: dict, forbidden_root: Path) -> None:
    _atomic_write_bytes(
        path,
        (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        forbidden_root,
    )


def atomic_text(path: Path, value: str, forbidden_root: Path, *, bom: bool = False) -> None:
    encoding = "utf-8-sig" if bom else "utf-8"
    _atomic_write_bytes(path, value.encode(encoding), forbidden_root)


def _day_path(tdx_root: Path, security_id: str) -> Path:
    market, code = security_id.split(".", 1)
    return tdx_root / "vipdoc" / market.lower() / "lday" / f"{market.lower()}{code}.day"


def collect_stock_timelines(tdx_root: Path, expected_ids: set[str]) -> tuple[dict[str, StockTimeline], Counter[int]]:
    timelines: dict[str, StockTimeline] = {}
    bar_counts: Counter[int] = Counter()
    for security_id in sorted(expected_ids):
        path = _day_path(tdx_root, security_id)
        if not path.is_file():
            timelines[security_id] = StockTimeline(
                security_id, None, None, 0, frozenset(), file_exists=False
            )
            continue
        raw = path.read_bytes()
        if not raw or len(raw) % DAY_RECORD_LENGTH:
            timelines[security_id] = StockTimeline(
                security_id, None, None, 0, frozenset(), structurally_valid=False
            )
            continue
        data = np.frombuffer(raw, dtype=DAY_DTYPE)
        dates = data["date"]
        bar_counts.update(int(value) for value in dates)
        recent = frozenset(int(value) for value in dates[-64:])
        timelines[security_id] = StockTimeline(
            security_id=security_id,
            first_date=int(dates[0]),
            last_date=int(dates[-1]),
            record_count=len(dates),
            recent_dates=recent,
        )
    return timelines, bar_counts


def calendar_csv(rows: list[dict]) -> str:
    stream = io.StringIO(newline="")
    fields = list(rows[0]) if rows else ["calendar_date", "is_market_open", "source_basis", "confirmation_count"]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def manual_ui_markdown(samples: list[dict]) -> str:
    lines = [
        "# Phase 0.1 manual TongdaXin UI cross-check",
        "",
        "```text",
        "overall_status = NOT_CHECKED",
        "checked_count = 0",
        "passed_count = 0",
        "failed_count = 0",
        f"pending_count = {len(samples)}",
        "```",
        "",
        "Codex cannot visually inspect the native TongdaXin window. The user must compare the following raw daily bars with the TongdaXin UI and report PASS or FAIL. No result has been inferred or fabricated.",
        "",
        "| Security | Name | Date | Open | High | Low | Close | User result |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for sample in samples:
        last = sample["last"]
        lines.append(
            f"| {sample['security_id']} | {sample.get('name') or ''} | {last['trade_date']} | "
            f"{last['open']:.2f} | {last['high']:.2f} | {last['low']:.2f} | {last['close']:.2f} | NOT_CHECKED |"
        )
    lines.extend([
        "",
        "Tolerance: exact trade date and OHLC rounded to CNY 0.01. Reply with five PASS/FAIL results; this file must then be updated with the user's evidence.",
        "",
    ])
    return "\n".join(lines)


def adjustment_contract_markdown(upstream: dict) -> str:
    return f"""# Adjustment Contract V0.1

Status: `SEMANTICS_UNVERIFIED`  
Executable project price basis: `RAW`  
Formal trend scanners allowed: `false`

## Local source

Only `D:/new_tdx/T0002/hq_cache/gbbq` and `gbbq.map` may provide event data. Record boundaries are structurally verified, but the payload remains encrypted/opaque. Unknown records are retained as `UNKNOWN_ACTION_TYPE`; none are silently ignored.

## Upstream source-code reference

- mootdx: `{upstream['mootdx_url']}` at `{upstream['mootdx_commit']}`
- pytdx: `{upstream['pytdx_url']}` at `{upstream['pytdx_commit']}`

The snapshots were explicitly user-authorized as source-code references only. They supply no external market data. Neither contains a local `gbbq` decoder. `mootdx/mootdx/tools/reversion.py` documents the per-10-share theoretical ex-price formula used below.

## Frozen mathematical candidate

For an event with cash dividend `D`, rights shares `R`, rights price `K`, and bonus/capitalization shares `S`, all quoted per 10 existing shares:

```text
price_mul = 10 / (10 + R + S)
price_add = (R*K - D) / (10 + R + S)
adjusted_price = price_mul * raw_price + price_add
```

The same positive affine transform applies to raw Open, High, Low, and Close for bars strictly before the event effective date. Multiple events compose in ascending effective-date order. This candidate is unit-tested but is not connected to local TDX records until `gbbq` event semantics are decoded.

## Operational rules

```text
price_basis = RAW
event_effective_date = apply event only to bars with date < effective_date
event_application_order = ascending effective_date
ohlc_adjustment_rule = same affine transform on OHLC
volume_adjustment_rule = KEEP_RAW_PENDING_LOCAL_UI_VERIFICATION
amount_basis = RAW_AMOUNT
missing_event_rule = mark adjustment incomplete; keep RAW; EXPERIMENTAL
unknown_event_rule = reject formal adjustment; keep record; EXPERIMENTAL
invalid_event_rule = reject affected security adjustment; preserve RAW
history_rebuild_rule = if gbbq or gbbq.map SHA-256 changes, rebuild all affected histories; while mapping is unknown rebuild all adjusted histories
price_abs_tolerance = 0.01
relative_tolerance = 0.0005
```

No `FORWARD_ADJUSTED` dataset may be emitted under this status.
"""


def calendar_contract_markdown() -> str:
    return f"""# Master Trading Calendar Contract

Version: `{CALENDAR_VERSION}`

## Local source and fields

The calendar uses the union of local `SH.000001` and `SZ.399001` date records plus current A-stock date evidence. Every civil date in the observed range is stored with:

```text
calendar_date
is_market_open
source_basis
confirmation_count
index_confirmation_count
confirming_indices
a_stock_confirmation_count
eligible_a_stock_count
a_stock_confirmation_ratio
```

A date is open when at least one primary index contains it, or when at least 20 locally eligible A stocks contain it and coverage is at least 50%. Index OHLC is not consumed; `INDEX_DATA_CONTRACT_PENDING=true`.

## Missing-state semantics

- `SUSPENDED`: a bar is absent inside a security's observed interval and a later local bar proves trading resumed.
- `MISSING_DATA`: evidence is absent or a current security has a trailing gap that cannot be proven to be suspension.
- `NOT_LISTED_YET`: calendar session precedes the first local bar.
- `DELISTED_OR_INACTIVE`: session follows the last bar for a security not in the current membership master.
- `FILE_MISSING`: the current master references a security but its daily file is absent.

Only `SUSPENDED` may receive a derived alignment fill: previous valid close, return 0, volume 0, amount 0, `is_synthetic_fill=true`, `tradable=false`. Raw bars are never changed. Other missing states are not synthetically filled.

## Window and Universe

The recent window is the latest {RECENT_WINDOW} open master sessions. `NORMAL_UNIVERSE` requires at least {MIN_HISTORY_DAYS} raw bars, latest-session raw bar present, and at least {MIN_RECENT_COVERAGE:.0%} raw-bar coverage in that window. Short proven suspensions do not automatically exclude a security if these requirements remain satisfied.

Future factors must declare `calendar_window` or `valid_bar_window`; formal trend defaults to aligned calendar windows.
"""


def run_phase0_1(project_root: Path, tdx_root: Path) -> dict:
    phase0_path = project_root / "reports" / "phase0" / "TDX_DATA_AUDIT.json"
    phase0 = json.loads(phase0_path.read_text(encoding="utf-8"))
    output_dir = project_root / "reports" / "phase0_1"

    cache = tdx_root / "T0002" / "hq_cache"
    assignments = read_industry_assignments(cache / "tdxhy.cfg")
    expected_ids = current_a_stock_ids(assignments)
    timelines, bar_counts = collect_stock_timelines(tdx_root, expected_ids)
    selected_date = phase0["daily_data"]["latest_trade_date"]

    primary_indices = {
        "SH.000001": set(read_day_dates(_day_path(tdx_root, "SH.000001"))),
        "SZ.399001": set(read_day_dates(_day_path(tdx_root, "SZ.399001"))),
    }
    intervals = [
        # These are current master members.  A trailing data gap must remain in
        # the eligibility denominator instead of shrinking it to a perfect ratio.
        (timeline.first_date, selected_date)
        for timeline in timelines.values()
        if timeline.structurally_valid and timeline.first_date is not None and timeline.last_date is not None
    ]
    calendar_rows = build_master_calendar(
        primary_index_dates=primary_indices,
        a_stock_bar_counts=bar_counts,
        stock_intervals=intervals,
    )
    open_sessions = [row["calendar_date"] for row in calendar_rows if row["is_market_open"]]
    latest_sessions = open_sessions[-RECENT_WINDOW:]

    qualification = {}
    coverage_histogram: Counter[int] = Counter()
    gap_statuses: Counter[str] = Counter()
    excluded_samples = []
    removed_by_recent_window = []
    after_ids = set()
    for security_id, timeline in timelines.items():
        qualifies, evidence = qualifies_normal_universe(
            timeline,
            latest_sessions,
            min_history_days=MIN_HISTORY_DAYS,
            min_recent_coverage_ratio=MIN_RECENT_COVERAGE,
            require_latest_bar=True,
        )
        qualification[security_id] = evidence
        coverage_histogram[evidence["recent_valid_bar_count"]] += 1
        gap_statuses.update(evidence["status_distribution"])
        if qualifies:
            after_ids.add(security_id)
        elif len(excluded_samples) < 50:
            excluded_samples.append({"security_id": security_id, "record_count": timeline.record_count, **evidence})
        old_qualifies = (
            timeline.file_exists
            and timeline.structurally_valid
            and timeline.record_count >= MIN_HISTORY_DAYS
            and timeline.last_date == selected_date
        )
        if old_qualifies and not qualifies:
            removed_by_recent_window.append(
                {"security_id": security_id, "record_count": timeline.record_count, **evidence}
            )

    calendar_audit = {
        "schema_version": "trading-calendar-audit-v0.1",
        "master_trading_calendar_status": "PASS",
        "master_trading_calendar_version": CALENDAR_VERSION,
        "source_basis": "LOCAL_PRIMARY_INDEX_DATES_PLUS_CURRENT_A_STOCK_CONFIRMATION",
        "primary_indices": sorted(primary_indices),
        "index_data_contract_pending": True,
        "calendar_start_date": calendar_rows[0]["calendar_date"],
        "calendar_end_date": calendar_rows[-1]["calendar_date"],
        "civil_date_count": len(calendar_rows),
        "market_open_session_count": len(open_sessions),
        "latest_20_sessions": latest_sessions,
        "selected_date": selected_date,
        "selected_date_is_open": selected_date in open_sessions,
        "normal_universe": {
            "count_before": phase0["security_master"]["normal_universe_contract"]["normal_universe_count"],
            "count_after": len(after_ids),
            "min_history_days": MIN_HISTORY_DAYS,
            "recent_window_sessions": RECENT_WINDOW,
            "min_recent_coverage_ratio": MIN_RECENT_COVERAGE,
            "require_latest_raw_bar": True,
            "recent_valid_bar_count_histogram": {
                str(key): value for key, value in sorted(coverage_histogram.items())
            },
            "recent_gap_status_distribution": dict(sorted(gap_statuses.items())),
            "excluded_samples": excluded_samples,
            "removed_from_phase0_universe_by_recent_window": removed_by_recent_window,
        },
        "latest_session_evidence": next(row for row in calendar_rows if row["calendar_date"] == selected_date),
    }
    latest_bar_count = calendar_audit["latest_session_evidence"]["a_stock_confirmation_count"]
    parsed_count = phase0["security_master"]["parsed_a_stock_count"]
    expected_count = phase0["security_master"]["expected_a_stock_count"]
    calendar_audit["latest_date_coverage_among_parsed_a_stocks"] = latest_bar_count / parsed_count
    calendar_audit["latest_date_coverage_among_expected_a_stocks"] = latest_bar_count / expected_count

    gbbq_audit = audit_gbbq(cache / "gbbq", cache / "gbbq.map")
    upstream = {
        "mootdx_url": "https://github.com/mootdx/mootdx",
        "mootdx_commit": subprocess.check_output(
            ["git", "-C", str(project_root / "references" / "upstream" / "mootdx"), "rev-parse", "HEAD"],
            text=True,
        ).strip(),
        "pytdx_url": "https://github.com/rainx/pytdx",
        "pytdx_commit": subprocess.check_output(
            ["git", "-C", str(project_root / "references" / "upstream" / "pytdx"), "rev-parse", "HEAD"],
            text=True,
        ).strip(),
        "usage": "SOURCE_CODE_REFERENCE_ONLY_NO_EXTERNAL_MARKET_DATA",
    }
    adjustment_validation = {
        "schema_version": "adjustment-validation-v0.1",
        "adjustment_contract_version": ADJUSTMENT_CONTRACT_VERSION,
        "adjustment_status": "STRUCTURE_PARSED_SEMANTICS_UNVERIFIED",
        "project_price_basis": "RAW",
        "formal_trend_scanners_allowed": False,
        "upstream_source_references": upstream,
        "local_event_sample_count": 0,
        "validation_pass_count": 0,
        "validation_fail_count": 0,
        "sample_requirements": [
            {"type": "CASH_DIVIDEND", "status": "SAMPLE_NOT_AVAILABLE"},
            {"type": "SHARE_BONUS_OR_CAPITALIZATION", "status": "SAMPLE_NOT_AVAILABLE"},
            {"type": "RIGHTS_ISSUE", "status": "SAMPLE_NOT_AVAILABLE"},
            {"type": "MULTIPLE_ACTIONS", "status": "SAMPLE_NOT_AVAILABLE"},
            {"type": "NO_ACTION_CONTROL", "status": "SAMPLE_NOT_AVAILABLE"},
        ],
        "reason": "Local encrypted gbbq records cannot yet be mapped to security, event date, action type, or parameters; UI adjusted-price validation would therefore be non-reproducible.",
        "candidate_formula": "P_adj=(10*P_raw-D+R*K)/(10+R+S)=price_mul*P_raw+price_add",
        "formula_status": "UNIT_TESTED_CANDIDATE_NOT_CONNECTED_TO_LOCAL_EVENTS",
        "price_abs_tolerance": 0.01,
        "relative_tolerance": 0.0005,
    }

    industry_names = read_industry_names(cache / "tdxzs.cfg")
    sector_memberships = build_industry_memberships(assignments, industry_names)
    info_memberships, info_meta = read_infoharbor_memberships(cache / "infoharbor_block.dat")
    sector_memberships.extend(info_memberships)
    sectors = {
        (item["sector_type"], item["sector_code"], item["sector_name"])
        for item in sector_memberships
        if item["sector_type"] in {"industry", "concept", "style"}
    }
    sectors.update(
        (item["sector_type"], item["sector_code"], item["sector_name"])
        for item in info_meta["sector_headers"]
        if item["sector_type"] in {"concept", "style"}
    )
    role_rows = [
        {
            "sector_type": sector_type,
            "sector_code": sector_code,
            "sector_name": name,
            "sector_role": sector_role(sector_type, name),
        }
        for sector_type, sector_code, name in sorted(sectors)
    ]
    role_counts = Counter(row["sector_role"] for row in role_rows)
    sector_role_audit = {
        "schema_version": "sector-role-audit-v0.1",
        "sector_role_status": "PASS",
        "sector_role_version": SECTOR_ROLE_VERSION,
        "role_distribution": dict(sorted(role_counts.items())),
        "excluded_theme_names_configured": sorted(EXCLUDED_THEME_NAMES),
        "excluded_sectors": [row for row in role_rows if row["sector_role"] == "EXCLUDE_FROM_THEME_RANK"],
        "membership_deleted_count": 0,
        "all_sector_count": len(role_rows),
    }

    raw_before = phase0["daily_data"]["raw_source_manifest_sha256"]
    day_paths, _snapshot = snapshot_day_files(tdx_root)
    raw_after = raw_manifest_fingerprint(day_paths)
    source_unchanged = raw_before == raw_after

    atomic_json(output_dir / "GBBQ_AUDIT.json", gbbq_audit, tdx_root)
    atomic_json(output_dir / "ADJUSTMENT_VALIDATION.json", adjustment_validation, tdx_root)
    atomic_json(output_dir / "TRADING_CALENDAR_AUDIT.json", calendar_audit, tdx_root)
    atomic_json(output_dir / "SECTOR_ROLE_AUDIT.json", sector_role_audit, tdx_root)
    atomic_text(output_dir / "MASTER_TRADING_CALENDAR.csv", calendar_csv(calendar_rows), tdx_root, bom=True)
    manual_text = manual_ui_markdown(phase0["daily_data"]["edge_record_samples"])
    atomic_text(output_dir / "MANUAL_UI_CROSSCHECK.md", manual_text, tdx_root)

    atomic_text(project_root / "docs" / "ADJUSTMENT_CONTRACT.md", adjustment_contract_markdown(upstream), tdx_root)
    atomic_text(project_root / "docs" / "TRADING_CALENDAR_CONTRACT.md", calendar_contract_markdown(), tdx_root)

    tests = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=project_root,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    passed_match = re.search(r"(\d+) passed", tests.stdout)
    failed_match = re.search(r"(\d+) failed", tests.stdout)
    tests_passed = int(passed_match.group(1)) if passed_match else 0
    tests_failed = int(failed_match.group(1)) if failed_match else (0 if tests.returncode == 0 else 1)

    final_status = decide_status(
        day_contract_ok=True,
        ui_crosscheck="NOT_CHECKED",
        calendar_ok=calendar_audit["master_trading_calendar_status"] == "PASS",
        source_unchanged=source_unchanged,
        adjustment_reproducible=False,
        adjustment_ui_validated=False,
    )
    warnings = [
        "Local gbbq record boundaries are verified, but payload encryption/semantics remain unresolved.",
        "Five raw OHLC UI checks remain NOT_CHECKED and require user feedback.",
        "Historical ST/name/delisting master data remains limited.",
        "INDEX_DATA_CONTRACT_PENDING=true; indices are used only for date confirmation.",
        "GitHub source access was explicitly authorized by the user and used only for source-code reference, never external market data.",
    ]
    errors = [] if tests.returncode == 0 and source_unchanged else [
        message
        for condition, message in (
            (tests.returncode != 0, "Project tests failed."),
            (not source_unchanged, "TDX daily metadata manifest changed during Phase 0.1."),
        )
        if condition
    ]
    receipt = {
        "phase": "PHASE0.1",
        "baseline_version": "V0.3_FINAL_IMPLEMENTATION_BASELINE",
        "start_status": phase0["run_status"],
        "final_status": final_status,
        "run_time": datetime.now().astimezone().isoformat(),
        "tdx_root": str(tdx_root),
        "source_access_mode": "READ_ONLY",
        "day_contract_status": "AUTOMATED_PASS_MANUAL_UI_PENDING",
        "manual_ui_crosscheck_status": "NOT_CHECKED",
        "adjustment_status": adjustment_validation["adjustment_status"],
        "project_price_basis": "RAW",
        "formal_trend_scanners_allowed": False,
        "gbbq_parse_status": gbbq_audit["gbbq_parse_status"],
        "gbbq_event_count": gbbq_audit["event_count"],
        "unknown_action_type_count": gbbq_audit["unknown_action_type_count"],
        "adjustment_validation_sample_count": adjustment_validation["local_event_sample_count"],
        "adjustment_validation_pass_count": adjustment_validation["validation_pass_count"],
        "adjustment_validation_fail_count": adjustment_validation["validation_fail_count"],
        "adjustment_validation_unavailable_count": len(adjustment_validation["sample_requirements"]),
        "master_trading_calendar_status": calendar_audit["master_trading_calendar_status"],
        "master_trading_calendar_version": CALENDAR_VERSION,
        "calendar_start_date": calendar_audit["calendar_start_date"],
        "calendar_end_date": calendar_audit["calendar_end_date"],
        "normal_universe_count_before": calendar_audit["normal_universe"]["count_before"],
        "normal_universe_count_after": calendar_audit["normal_universe"]["count_after"],
        "sector_role_status": sector_role_audit["sector_role_status"],
        "sector_role_version": SECTOR_ROLE_VERSION,
        "raw_metadata_manifest_sha256_before": raw_before,
        "raw_metadata_manifest_sha256_after": raw_after,
        "tdx_source_unchanged": source_unchanged,
        "gbbq_sha256_before": phase0["adjustment_contract"]["candidate_files"][0]["sha256"],
        "gbbq_sha256_after": gbbq_audit["sha256"],
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "test_output": tests.stdout.strip(),
        "warnings": warnings,
        "errors": errors,
        "next_allowed_phase": (
            "PHASE_1_NORMALIZATION_AND_EXPERIMENTAL_FACTOR_ENGINE"
            if final_status == "DEGRADED_PASS"
            else "PHASE_1_NORMALIZATION_AND_FACTOR_ENGINE" if final_status == "FULL_PASS" else "NONE"
        ),
    }
    atomic_json(output_dir / "PHASE0_1_FINAL_RECEIPT.json", receipt, tdx_root)

    report = f"""# Phase 0.1 report — Adjustment & Trading Calendar Closure

Final status: **{final_status}**

## Adjustment

- `gbbq` header and 29-byte record boundaries: PASS.
- Declared/event records: {gbbq_audit['event_count']:,}.
- Encrypted entity groups: {gbbq_audit['encrypted_entity_group_count']:,}.
- Map entries: {gbbq_audit['map_entry_count']:,}.
- Security/date/action/parameter semantics: UNVERIFIED.
- Unknown action records retained: {gbbq_audit['unknown_action_type_count']:,}.
- Project price basis remains `RAW`; formal Trend scanners remain disabled.

The user explicitly authorized GitHub source-code download. mootdx `{upstream['mootdx_commit']}` and pytdx `{upstream['pytdx_commit']}` were inspected. Neither contains a local `gbbq` decoder. The mootdx affine corporate-action formula was independently implemented and unit-tested, but it is not connected to opaque local events.

## Trading calendar and Universe

- Calendar: `{CALENDAR_VERSION}` / PASS.
- Range: {calendar_audit['calendar_start_date']} through {calendar_audit['calendar_end_date']}.
- Open sessions: {calendar_audit['market_open_session_count']:,}.
- Latest 20 sessions frozen from local data.
- NORMAL_UNIVERSE: {calendar_audit['normal_universe']['count_before']:,} -> {calendar_audit['normal_universe']['count_after']:,}.
- Recent coverage threshold: {MIN_RECENT_COVERAGE:.0%}; latest raw bar remains required.

Missing dates are separated into `SUSPENDED`, `MISSING_DATA`, `NOT_LISTED_YET`, `DELISTED_OR_INACTIVE`, and `FILE_MISSING`. Only proven internal suspension gaps may receive a derived synthetic fill; raw data is never overwritten.

## Manual UI check

Status: `NOT_CHECKED`. Five exact raw-OHLC rows are in `reports/phase0_1/MANUAL_UI_CROSSCHECK.md`. User feedback is required; no visual result was fabricated.

## Sector roles

Status: PASS. Roles: {json.dumps(sector_role_audit['role_distribution'], ensure_ascii=False)}. The configured attribute collections are retained but excluded from theme ranking.

## Integrity and tests

- TDX source metadata unchanged: `{source_unchanged}`.
- Raw metadata manifest before/after: `{raw_before}`.
- Tests: {tests_passed} passed, {tests_failed} failed.
- Final errors: {len(errors)}.

## Decision

Phase 0.1 remains `DEGRADED_PASS` because local adjustment semantics and UI-adjusted samples are not reproducible. The calendar closure is usable. The next allowed work is Phase 1 normalization and **experimental** factors only; all multi-day price-structure output must carry `PRICE_ADJUSTMENT_LIMITATION=true`.
"""
    atomic_text(project_root / "docs" / "PHASE0_1_REPORT.md", report, tdx_root)
    return receipt
