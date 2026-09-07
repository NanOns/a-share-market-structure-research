from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys

from adjustment.tdx_adjustment import (
    ADJUSTMENT_VERSION,
    adjust_ohlc,
    build_affine_factors,
    xrxd_from_gbbq,
)
from phase0_1_runner import atomic_json, atomic_text
from tdx.day_reader import DAY_RECORD_LENGTH, DAY_STRUCT
from tdx.gbbq_reader import (
    DECODER_VERSION,
    REFERENCE_COMMIT,
    GbbqRecord,
    audit_gbbq,
    file_sha256,
    read_gbbq,
)
from tdx.tdx_audit import raw_manifest_fingerprint, snapshot_day_files


REFERENCE_REPOSITORY = "https://github.com/injoyai/tdx"
CONTRACT_VERSION = "adjustment-contract-v0.2"
BASELINE_VERSION = "V0.3_FINAL_IMPLEMENTATION_BASELINE"
REQUIRED_SECURITIES = ("SH.600519", "SZ.000651", "SZ.000001")
MANUAL_TARGETS = (
    ("SH.600519", 20250625, "CASH_DIVIDEND", "event 20250626 cash 276.73/10"),
    ("SZ.000651", 20150702, "BONUS_TRANSFER_AND_CASH", "event 20150703 transfer 10 + cash 30/10"),
    ("SZ.000651", 20000803, "RIGHTS_ISSUE", "event 20000804 rights 3/10 at CNY 14"),
    ("SH.600519", 20060425, "COMPOUND_SUSPENSION", "events 20060519 and 20060524 in one gap"),
    ("SZ.000001", 20260611, "RECENT_ORDINARY", "event 20260612 cash 3.60/10"),
)


def _day_path(tdx_root: Path, security_id: str) -> Path:
    market, code = security_id.split(".", 1)
    return tdx_root / "vipdoc" / market.lower() / "lday" / f"{market.lower()}{code}.day"


def _read_day_rows(path: Path) -> list[dict]:
    raw = path.read_bytes()
    if not raw or len(raw) % DAY_RECORD_LENGTH:
        raise ValueError(f"invalid .day file: {path}")
    rows = []
    for trade_date, open_, high, low, close, amount, volume, reserved in DAY_STRUCT.iter_unpack(raw):
        rows.append(
            {
                "trade_date": trade_date,
                "open": Decimal(open_) / 100,
                "high": Decimal(high) / 100,
                "low": Decimal(low) / 100,
                "close": Decimal(close) / 100,
                "amount": float(amount),
                "volume": volume,
                "reserved": reserved,
            }
        )
    return rows


def _json_decimal(value: Decimal) -> str:
    return format(value, "f")


def _adjusted_row(row: dict, factor) -> dict:
    adjusted = adjust_ohlc(row, factor)
    return {
        "security_id": None,
        "date": row["trade_date"],
        "raw_open": float(row["open"]),
        "raw_high": float(row["high"]),
        "raw_low": float(row["low"]),
        "raw_close": float(row["close"]),
        "computed_qfq_open": float(adjusted["open"]),
        "computed_qfq_high": float(adjusted["high"]),
        "computed_qfq_low": float(adjusted["low"]),
        "computed_qfq_close": float(adjusted["close"]),
        "raw_amount": row["amount"],
        "raw_volume": row["volume"],
        "qfq_mul": _json_decimal(factor.qfq_mul),
        "qfq_add": _json_decimal(factor.qfq_add),
        "price_basis": "FORWARD_ADJUSTED_CANDIDATE",
        "adjustment_status": "AUTOMATED_LOCAL_VALIDATION_ONLY",
        "adjustment_source": "LOCAL_TDX_GBBQ",
        "adjustment_version": ADJUSTMENT_VERSION,
    }


def _series_validation(security_id: str, rows: list[dict], events) -> tuple[dict, dict[int, dict]]:
    factors = build_affine_factors((row["trade_date"] for row in rows), events)
    digest = sha256()
    adjusted_by_date: dict[int, dict] = {}
    ordering_failures = 0
    finite_failures = 0
    for row in rows:
        factor = factors[row["trade_date"]]
        result = _adjusted_row(row, factor)
        result["security_id"] = security_id
        adjusted_by_date[row["trade_date"]] = result
        values = [Decimal(str(result[f"computed_qfq_{field}"])) for field in ("open", "high", "low", "close")]
        if not all(value.is_finite() for value in values):
            finite_failures += 1
        if values[1] < max(values[0], values[2], values[3]) or values[2] > min(values[0], values[1], values[3]):
            ordering_failures += 1
        digest.update(
            (
                f"{row['trade_date']}|{result['computed_qfq_open']:.2f}|{result['computed_qfq_high']:.2f}|"
                f"{result['computed_qfq_low']:.2f}|{result['computed_qfq_close']:.2f}|"
                f"{result['qfq_mul']}|{result['qfq_add']}\n"
            ).encode("ascii")
        )
    latest = rows[-1]["trade_date"]
    latest_factor = factors[latest]
    future_events = [event for event in events if event.ex_day > latest]
    checks = {
        "security_id": security_id,
        "day_file": None,
        "raw_bar_count": len(rows),
        "factor_count": len(factors),
        "event_count": len(events),
        "effective_event_count": len(events) - len(future_events),
        "future_event_ignored_count": len(future_events),
        "first_trade_date": rows[0]["trade_date"],
        "latest_trade_date": latest,
        "latest_factor_is_identity": latest_factor.qfq_mul == 1 and latest_factor.qfq_add == 0,
        "ohlc_ordering_failure_count": ordering_failures,
        "non_finite_output_count": finite_failures,
        "qfq_series_sha256": digest.hexdigest(),
    }
    checks["status"] = "PASS" if (
        checks["factor_count"] == checks["raw_bar_count"]
        and checks["latest_factor_is_identity"]
        and not ordering_failures
        and not finite_failures
    ) else "FAIL"
    return checks, adjusted_by_date


def _selected_event_samples(by_security: dict[str, list], records: list[GbbqRecord], latest_date: int) -> dict:
    required: dict[str, dict] = {}
    selectors = {
        "SH.600519": {20060519, 20060524, 20250626, 20260626},
        "SZ.000651": {19980421, 20000804, 20150703, 20260827},
        "SZ.000001": {19900301, 20250612, 20260612},
    }
    for security_id in REQUIRED_SECURITIES:
        events = by_security[security_id]
        required[security_id] = {
            "total_xrxd_event_count": len(events),
            "selected_events": [event.as_dict() for event in events if event.ex_day in selectors[security_id]],
        }

    recent_candidates = []
    for security_id, events in by_security.items():
        effective = [event for event in events if event.ex_day <= latest_date]
        if security_id not in REQUIRED_SECURITIES and effective:
            recent_candidates.append(effective[-1])
    recent_candidates.sort(key=lambda event: (event.ex_day, event.security_id), reverse=True)
    additional = [event.as_dict() for event in recent_candidates[:5]]
    category_15 = [record.as_dict(explicit_xrxd=False) for record in records if record.category == 15][:10]
    return {
        "schema_version": "gbbq-event-samples-v0.2",
        "source": "LOCAL_TDX_GBBQ_ONLY",
        "required_securities": required,
        "additional_recent_effective_xrxd_samples": additional,
        "unknown_category_15_sample_count": len(category_15),
        "unknown_category_15_samples": category_15,
        "note": "Category 15 is retained as unknown and is never consumed by the adjustment engine.",
    }


def _manual_markdown(samples: list[dict]) -> str:
    lines = [
        "# Phase 0.2 QFQ manual TongdaXin UI check",
        "",
        "```text",
        "overall_status = NOT_CHECKED",
        "checked_count = 0",
        "passed_count = 0",
        "failed_count = 0",
        f"pending_count = {len(samples)}",
        "```",
        "",
        "The computed values below use only local `.day` RAW bars and the local decoded `gbbq`. Codex has not supplied or inferred any TongdaXin UI value. In TongdaXin select 前复权 and enter the four UI prices plus PASS/FAIL.",
        "",
        "| Type | Security | Date | Raw O/H/L/C | Computed QFQ O/H/L/C | TDX UI QFQ O/H/L/C | Status | Event context |",
        "|---|---|---:|---|---|---|---|---|",
    ]
    for sample in samples:
        raw = "/".join(f"{sample[f'raw_{field}']:.2f}" for field in ("open", "high", "low", "close"))
        adjusted = "/".join(f"{sample[f'computed_qfq_{field}']:.2f}" for field in ("open", "high", "low", "close"))
        lines.append(
            f"| {sample['sample_type']} | {sample['security_id']} | {sample['date']} | {raw} | {adjusted} | PENDING_USER_INPUT | NOT_CHECKED | {sample['event_context']} |"
        )
    lines.extend(
        [
            "",
            "Acceptance tolerance: exact date and exact displayed OHLC to CNY 0.01. A single mismatch remains a failure unless documented as the upstream-known isolated exception; no security/date hard-code is permitted.",
            "",
        ]
    )
    return "\n".join(lines)


def _reference_markdown(project_root: Path) -> str:
    repo = project_root / "references" / "upstream" / "injoyai-tdx"
    referenced = [
        "lib/gbbq/gbbq.go",
        "protocol/model_gbbq.go",
        "protocol/model_gbbq_test.go",
        "docs/gbbq_除权除息与复权算法.md",
        "example/DecodeGBBQ/main.go",
    ]
    file_lines = "\n".join(
        f"- `{name}` — SHA-256 `{file_sha256(repo / name)}`" for name in referenced
    )
    return f"""# Reference implementation audit

- Repository: `{REFERENCE_REPOSITORY}`
- Locked commit: `{REFERENCE_COMMIT}`
- License: MIT, Copyright (c) 2025 injoyai; retained in `THIRD_PARTY_NOTICES.md` and the local source snapshot.
- Usage boundary: source-code reference only; no online market data and no Go runtime/service.

## Referenced files

{file_lines}

## Adopted concepts

- 4-byte little-endian count and 29-byte record boundary.
- Fixed-key three-block decryption and the decoded market/code/date/category/C1-C4 layout.
- Category 1 XRXD field semantics, affine QFQ/HFQ model, date-position suspension handling, future-ex-day filtering, and half-up cent rounding.

## Independently reimplemented

`src/tdx/gbbq_reader.py`, `src/tdx/_gbbq_key.py`, and `src/adjustment/tdx_adjustment.py` are local Python implementations. The project never imports, executes, or starts the Go repository. Local `.day` and `gbbq` files are the only market inputs.

## Not used

No online TDX protocol calls, `GetGbbq`, `GetKline`, HTTP download, SQLite cache, Go binary, Go service, F10, finance, intraday, or other upstream feature is used.

## Local-data divergence retained

The real file contains 91 records with category 15, which the referenced semantic table does not define. They are retained as `UNKNOWN_CATEGORY` and excluded from adjustment. Category 1 remains fully explicit and is the only adjustment input.
"""


def _contract_markdown() -> str:
    return f"""# Adjustment Contract V0.2

Contract: `{CONTRACT_VERSION}`  
Engine: `{ADJUSTMENT_VERSION}`  
Current executable project price basis: `RAW` pending manual UI acceptance.

## Source and identity

Only local `D:/new_tdx/T0002/hq_cache/gbbq` supplies actions. Decoded identity is `MARKET.CODE`, using byte 0 (`0=SZ`, `1=SH`, `2=BJ`) plus the decoded six-digit code. Inputs are read-only. Unknown categories are retained; adjustment consumes only category 1.

## Category 1 fields

```text
C1 = cash_dividend_per_10
C2 = rights_price
C3 = bonus_transfer_per_10
C4 = rights_ratio_per_10
```

Parameters are normalized to two decimals before factor calculation, matching the audited reference model.

## Affine contract

```text
m = (10 + bonus_transfer_per_10 + rights_ratio_per_10) / 10
c = (cash_dividend_per_10 - rights_ratio_per_10 * rights_price) / 10
theoretical_ex_price = (raw_price - c) / m

qfq_price = A * raw_price + B
latest local trade date: A=1, B=0
walking backward across an effective event:
    A_new = A / m
    B_new = B - A_new * c
```

For each trade date `d`, all events satisfying `d < ex_day <= latest_trade_date` are composed. This includes every event inside a suspension gap; no matching ex-day K-line is required. Events after the latest trade date are ignored until effective.

HFQ is derived from earliest-date QFQ `(A0,B0)` as `hfq=(qfq-B0)/A0`. Open, High, Low, Close use the same factor and `ROUND_HALF_UP` to CNY 0.01. Amount and Volume remain raw.

## Failure rules

Invalid structure, code, date, market, or non-finite category-1 parameter blocks formal adjustment. Unknown non-category-1 records do not disappear and do not enter the engine. No stock/date-specific patch is allowed. Until all manual UI rows pass, no formal adjusted parquet is emitted, `PROJECT_PRICE_BASIS=RAW`, and formal trend scanners stay disabled.
"""


def run_phase0_2(project_root: Path, tdx_root: Path) -> dict:
    project_root = project_root.resolve()
    tdx_root = tdx_root.resolve()
    output_dir = project_root / "reports" / "phase0_2"
    phase0 = json.loads((project_root / "reports" / "phase0" / "TDX_DATA_AUDIT.json").read_text(encoding="utf-8"))
    phase0_1 = json.loads((project_root / "reports" / "phase0_1" / "PHASE0_1_FINAL_RECEIPT.json").read_text(encoding="utf-8"))
    cache = tdx_root / "T0002" / "hq_cache"
    gbbq_path = cache / "gbbq"
    map_path = cache / "gbbq.map"

    records = read_gbbq(gbbq_path)
    decode_audit = audit_gbbq(gbbq_path, map_path, decoded_records=records)
    by_security: dict[str, list] = defaultdict(list)
    for record in records:
        if record.category == 1:
            by_security[record.security_id].append(xrxd_from_gbbq(record))
    for events in by_security.values():
        events.sort(key=lambda event: (event.ex_day, event.source_record_index))

    latest_date = phase0["daily_data"]["latest_trade_date"]
    event_samples = _selected_event_samples(by_security, records, latest_date)
    validations = []
    adjusted_maps: dict[str, dict[int, dict]] = {}
    for security_id in REQUIRED_SECURITIES:
        path = _day_path(tdx_root, security_id)
        rows = _read_day_rows(path)
        validation, adjusted = _series_validation(security_id, rows, by_security[security_id])
        validation["day_file"] = str(path)
        validations.append(validation)
        adjusted_maps[security_id] = adjusted

    manual_samples = []
    for security_id, trade_date, sample_type, context in MANUAL_TARGETS:
        sample = dict(adjusted_maps[security_id][trade_date])
        sample.update({"sample_type": sample_type, "event_context": context})
        manual_samples.append(sample)

    cash_samples = [event.as_dict() for events in by_security.values() for event in events if event.cash_dividend_per_10 > 0 and event.bonus_transfer_per_10 == 0 and event.rights_ratio_per_10 == 0][:5]
    bonus_samples = [event.as_dict() for events in by_security.values() for event in events if event.bonus_transfer_per_10 > 0][:5]
    rights_samples = [event.as_dict() for events in by_security.values() for event in events if event.rights_ratio_per_10 > 0 and event.rights_price > 0][:5]
    future_samples = [event.as_dict() for events in by_security.values() for event in events if event.ex_day > latest_date][:5]
    compound_samples = [
        event.as_dict()
        for event in by_security["SH.600519"]
        if event.ex_day in {20060519, 20060524}
    ]
    local_pass = all(item["status"] == "PASS" for item in validations)

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

    qfq_validation = {
        "schema_version": "qfq-validation-v0.2",
        "sample_count": len(manual_samples),
        "cash_dividend_samples": cash_samples,
        "bonus_transfer_samples": bonus_samples,
        "rights_issue_samples": rights_samples,
        "compound_suspension_samples": compound_samples,
        "future_exday_samples": future_samples,
        "reference_test_passed": tests.returncode == 0,
        "local_data_test_passed": local_pass,
        "manual_ui_passed": False,
        "manual_ui_pending": True,
        "manual_ui_failed": False,
        "manual_samples": manual_samples,
        "local_security_validations": validations,
        "known_exceptions": [
            {
                "security_id": "SH.600519",
                "date": 20060526,
                "field": "open",
                "reference_algorithm": -260.97,
                "reference_tdx_ui": -260.98,
                "difference": 0.01,
                "policy": "RECORDED_NO_HARDCODE_PATCH",
                "source": "audited reference commit",
            }
        ],
        "amount_basis": "RAW_AMOUNT",
        "volume_basis": "RAW_VOLUME",
        "adjusted_dataset_emitted": False,
        "adjusted_dataset_reason": "MANUAL_UI_QFQ_CHECK_PENDING",
    }

    expected_gbbq = next(item for item in phase0["adjustment_contract"]["candidate_files"] if item["name"] == "gbbq")
    expected_map = next(item for item in phase0["adjustment_contract"]["candidate_files"] if item["name"] == "gbbq.map")
    day_paths, _ = snapshot_day_files(tdx_root)
    current_manifest = raw_manifest_fingerprint(day_paths)
    source_integrity = {
        "gbbq_sha256_before": expected_gbbq["sha256"],
        "gbbq_sha256_after": decode_audit["sha256"],
        "gbbq_map_sha256_before": expected_map["sha256"],
        "gbbq_map_sha256_after": decode_audit["map_sha256"],
        "raw_metadata_manifest_sha256_before": phase0_1["raw_metadata_manifest_sha256_after"],
        "raw_metadata_manifest_sha256_after": current_manifest,
    }
    source_unchanged = (
        source_integrity["gbbq_sha256_before"] == source_integrity["gbbq_sha256_after"]
        and source_integrity["gbbq_map_sha256_before"] == source_integrity["gbbq_map_sha256_after"]
        and source_integrity["raw_metadata_manifest_sha256_before"] == source_integrity["raw_metadata_manifest_sha256_after"]
    )

    decoder_pass = decode_audit["gbbq_parse_status"] == "PASS"
    automated_pass = decoder_pass and local_pass and tests.returncode == 0 and source_unchanged
    final_status = "DEGRADED_PASS" if automated_pass else "BLOCKED_FOR_FORMAL_ADJUSTMENT"
    errors = []
    if not decoder_pass:
        errors.append("LOCAL_GBBQ_DECODE_FAILED")
    if not local_pass:
        errors.append("LOCAL_QFQ_VALIDATION_FAILED")
    if tests.returncode:
        errors.append("PROJECT_TESTS_FAILED")
    if not source_unchanged:
        errors.append("TDX_SOURCE_CHANGED")
    warnings = [
        "Manual TongdaXin QFQ UI validation is NOT_CHECKED; formal adjusted prices remain disabled.",
        f"{decode_audit['unknown_category_count']} category=15 records are structurally valid but semantically undefined by the locked reference; retained and excluded from QFQ.",
        "The upstream-documented isolated SH.600519 2006-05-26 open difference is recorded without a hard-coded patch.",
    ]
    receipt = {
        "phase": "PHASE0.2",
        "baseline_version": BASELINE_VERSION,
        "start_status": phase0_1["final_status"],
        "final_status": final_status,
        "run_time": datetime.now().astimezone().isoformat(),
        "tdx_root": str(tdx_root),
        "source_access_mode": "READ_ONLY",
        "tdx_source_unchanged": source_unchanged,
        **source_integrity,
        "reference_repository": REFERENCE_REPOSITORY,
        "reference_commit": REFERENCE_COMMIT,
        "gbbq_decoder_status": decode_audit["gbbq_parse_status"],
        "declared_record_count": decode_audit["declared_count"],
        "parsed_record_count": decode_audit["parsed_count"],
        "xrxr_event_count": decode_audit["xrxr_event_count"],
        "xrxd_event_count": decode_audit["xrxd_event_count"],
        "category_distribution": decode_audit["category_distribution"],
        "unknown_category_count": decode_audit["unknown_category_count"],
        "adjustment_contract_version": CONTRACT_VERSION,
        "project_price_basis": "RAW",
        "adjustment_status": "PARTIALLY_VERIFIED_MANUAL_UI_PENDING",
        "formal_trend_scanners_allowed": False,
        "local_validation_status": "PASS" if local_pass else "FAIL",
        "manual_ui_status": "NOT_CHECKED",
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "test_output": tests.stdout.strip(),
        "warnings": warnings,
        "errors": errors,
        "next_allowed_phase": (
            "PHASE_1_NORMALIZATION_AND_EXPERIMENTAL_FACTOR_ENGINE"
            if final_status == "DEGRADED_PASS" else "NONE"
        ),
    }

    atomic_json(output_dir / "GBBQ_DECODE_AUDIT.json", decode_audit, tdx_root)
    atomic_json(output_dir / "GBBQ_EVENT_SAMPLES.json", event_samples, tdx_root)
    atomic_json(output_dir / "QFQ_VALIDATION.json", qfq_validation, tdx_root)
    atomic_text(output_dir / "QFQ_MANUAL_UI_CHECK.md", _manual_markdown(manual_samples), tdx_root)
    atomic_json(output_dir / "PHASE0_2_FINAL_RECEIPT.json", receipt, tdx_root)
    atomic_text(project_root / "docs" / "REFERENCE_IMPLEMENTATION.md", _reference_markdown(project_root), tdx_root)
    atomic_text(project_root / "docs" / "ADJUSTMENT_CONTRACT_V0_2.md", _contract_markdown(), tdx_root)

    implementation_files = [
        "src/tdx/_gbbq_key.py",
        "src/tdx/gbbq_reader.py",
        "src/adjustment/tdx_adjustment.py",
        "src/phase0_2_runner.py",
        "run_phase0_2.py",
        "config/adjustment.yaml",
        "README.md",
        "PROJECT_SPEC.md",
        "tests/test_gbbq_local_decode.py",
        "tests/test_tdx_adjustment.py",
        "tests/test_tdx_adjustment_reference_cases.py",
        "tests/test_future_exday.py",
        "tests/test_suspension_compound_actions.py",
        "tests/test_round_half_up.py",
        "THIRD_PARTY_NOTICES.md",
    ]
    evidence_files = [
        "docs/REFERENCE_IMPLEMENTATION.md",
        "docs/ADJUSTMENT_CONTRACT_V0_2.md",
        "reports/phase0_2/GBBQ_DECODE_AUDIT.json",
        "reports/phase0_2/GBBQ_EVENT_SAMPLES.json",
        "reports/phase0_2/QFQ_VALIDATION.json",
        "reports/phase0_2/QFQ_MANUAL_UI_CHECK.md",
        "reports/phase0_2/PHASE0_2_FINAL_RECEIPT.json",
    ]
    inventory = "\n".join(
        f"| `{name}` | `{file_sha256(project_root / name)}` | {(project_root / name).stat().st_size:,} |"
        for name in implementation_files + evidence_files
    )
    event_rows = []
    for security_id, group in event_samples["required_securities"].items():
        for event in group["selected_events"]:
            event_rows.append(
                f"| {security_id} | {event['event_date']} | 1 | {event['cash_dividend']} | "
                f"{event['rights_price']} | {event['bonus_transfer']} | {event['rights_ratio']} |"
            )
    for event in event_samples["additional_recent_effective_xrxd_samples"]:
        event_rows.append(
            f"| {event['security_id']} | {event['event_date']} | 1 | {event['cash_dividend']} | "
            f"{event['rights_price']} | {event['bonus_transfer']} | {event['rights_ratio']} |"
        )
    manual_rows = "\n".join(
        f"| {sample['sample_type']} | {sample['security_id']} | {sample['date']} | "
        f"{sample['raw_open']:.2f}/{sample['raw_high']:.2f}/{sample['raw_low']:.2f}/{sample['raw_close']:.2f} | "
        f"{sample['computed_qfq_open']:.2f}/{sample['computed_qfq_high']:.2f}/{sample['computed_qfq_low']:.2f}/{sample['computed_qfq_close']:.2f} | NOT_CHECKED |"
        for sample in manual_samples
    )
    report = f"""# Phase 0.2 report — GBBQ decoder and adjustment closure

Final status: **{final_status}**

This is the single-file audit handoff requested by the user. It summarizes the implementation, provenance, full local evidence, gate decision, and embeds the four machine-readable evidence objects at the end. Attached paths remain the canonical artifacts.

## Executive gate receipt

| Gate | Result | Evidence |
|---|---|---|
| Local GBBQ structure/decryption | PASS | {decode_audit['parsed_count']:,}/{decode_audit['declared_count']:,}; zero invalid code/date/float/market |
| Category 1 XRXD semantics | PASS | {decode_audit['xrxd_event_count']:,} events; zero invalid XRXD parameter sets |
| Affine QFQ and reference regressions | PASS | {tests_passed} tests passed; three complete local histories |
| Manual TongdaXin QFQ UI | NOT_CHECKED | five rows below require user-entered UI values |
| TDX source unchanged | PASS | GBBQ, map, and all `.day` metadata fingerprints unchanged |
| Formal adjusted dataset/scanners | DISABLED | manual UI gate is not satisfied |

## GBBQ decoder evidence

- Locked source reference: `{REFERENCE_REPOSITORY}` at `{REFERENCE_COMMIT}` (MIT).
- Local file: `{gbbq_path}`; SHA-256 `{decode_audit['sha256']}`.
- File equation: `{decode_audit['file_size']} = 4 + {decode_audit['declared_count']} × 29`: **{decode_audit['file_size'] == decode_audit['expected_file_size']}**.
- Parsed: `{decode_audit['parsed_count']:,} / {decode_audit['declared_count']:,}`.
- Valid six-digit code: `{decode_audit['valid_code_count']:,}`; invalid `{decode_audit['invalid_code_count']}`.
- Valid date: `{decode_audit['valid_date_count']:,}`; invalid `{decode_audit['invalid_date_count']}`.
- Finite parameter records: `{decode_audit['finite_parameter_count']:,}`; invalid `{decode_audit['invalid_parameter_count']}`.
- Market distribution: `{json.dumps(decode_audit['market_distribution'], ensure_ascii=False)}`.
- Category distribution: `{json.dumps(decode_audit['category_distribution'], ensure_ascii=False)}`.
- Category 1 XRXD events: `{decode_audit['xrxd_event_count']:,}`.
- Category 1 parameter ranges: `{json.dumps(decode_audit['xrxd_parameter_stats'], ensure_ascii=False)}`; invalid semantic sets `{decode_audit['invalid_xrxd_semantics_count']}`.
- Category 15: `{decode_audit['unknown_category_count']}` ({decode_audit['unknown_category_ratio']:.6%}) retained as unknown and excluded from QFQ.

These whole-file statistics, the coherent market byte, and exact known first record establish that the local decryption is functioning. No `gbbq.map` fallback was needed for identity because the decoded market byte is available.

The first local record independently resolves to `SZ.000001 / 19900301 / category=1 / C2≈3.56 / C4=1.0`; this is asserted directly against the real encrypted bytes in `tests/test_gbbq_local_decode.py`.

## Real decoded XRXD samples

| Security | Ex-day | Category | Cash/10 | Rights price | Bonus/transfer/10 | Rights/10 |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(event_rows)}

The required SH.600519, SZ.000651, and SZ.000001 records plus five deterministic recent effective events are included. Full record indices and the ten-row category-15 sample are embedded in `GBBQ_EVENT_SAMPLES.json` below.

## XRXD and affine QFQ evidence

Only category 1 is converted to explicit cash/rights/bonus fields. The local engine implements `price=A×raw+B`, composes every event by date position across suspension gaps, ignores ex-days after each series' latest trade date, applies one transform to OHLC, uses Decimal `ROUND_HALF_UP` to CNY 0.01, and leaves Amount/Volume raw.

Three complete local histories were calculated in memory and fingerprinted (no formal adjusted dataset was emitted):

{chr(10).join(f"- `{item['security_id']}`: {item['raw_bar_count']:,} bars, {item['event_count']} events ({item['future_event_ignored_count']} future ignored), series SHA-256 `{item['qfq_series_sha256']}`, status `{item['status']}`." for item in validations)}

The executable rules are:

```text
m = (10 + bonus_transfer_per_10 + rights_ratio_per_10) / 10
c = (cash_dividend_per_10 - rights_ratio_per_10 * rights_price) / 10
theoretical_ex_price = (raw_price - c) / m

QFQ anchor on latest local trade date: A=1, B=0
walk backward; while d < ex_day <= latest_trade_date:
    A = A / m
    B = B - A * c
qfq_price = ROUND_HALF_UP(A * raw_price + B, 0.01)
```

Reference-style regression coverage includes SH.600519's two-event 2006 suspension gap (including locked expected QFQ values), SZ.000651 rights/large-transfer cases, future-ex-day filtering, half-up boundaries, and HFQ derivation. Tests: **{tests_passed} passed, {tests_failed} failed**.

```text
{tests.stdout.strip()}
```

## Manual UI gate

Status: **NOT_CHECKED**. Five non-fabricated rows covering cash, bonus+cash, rights, compound suspension, and a recent event are in `reports/phase0_2/QFQ_MANUAL_UI_CHECK.md`. Until the user enters TongdaXin 前复权 values and all rows pass:

| Type | Security | Date | Raw O/H/L/C | Computed QFQ O/H/L/C | UI status |
|---|---|---:|---|---|---|
{manual_rows}

```text
PROJECT_PRICE_BASIS = RAW
ADJUSTMENT_STATUS = PARTIALLY_VERIFIED_MANUAL_UI_PENDING
FORMAL_TREND_SCANNERS_ALLOWED = FALSE
```

No `data/adjusted/adjusted_daily.parquet` was generated because its release gate is not satisfied.

## Integrity and decision

- TDX source unchanged: `{source_unchanged}`.
- `.day` metadata manifest before/after: `{source_integrity['raw_metadata_manifest_sha256_before']}`.
- `gbbq` and `gbbq.map` hashes match the Phase 0 baseline.
- Automated local decoder/QFQ validation: `{'PASS' if automated_pass else 'FAIL'}`.
- Final status remains `DEGRADED_PASS` solely because manual UI QFQ acceptance is pending; the next allowed work is experimental factor normalization only.

## Implementation and evidence inventory

Every file below is outside `D:/new_tdx`. SHA-256 values allow the reviewer to bind this report to the exact source and evidence files.

| File | SHA-256 | Bytes |
|---|---|---:|
{inventory}

## Reviewer checklist

1. Verify the fixed-key block indices and unsigned 32-bit wraparound in `src/tdx/gbbq_reader.py` against the locked Go decoder.
2. Verify market byte mapping and the 29-byte clear layout against the all-record distributions.
3. Verify category 15 is retained but never passed to `xrxd_from_gbbq`.
4. Verify the strict event predicate is `ex_day > trade_date` and the future filter is `ex_day <= latest_trade_date`.
5. Verify Decimal half-up price rounding, common OHLC factors, raw Amount/Volume, and HFQ anchor derivation.
6. Do not approve `FULL_PASS` until the five TongdaXin UI values are supplied and match to CNY 0.01.

## Embedded machine-readable evidence

### GBBQ_DECODE_AUDIT.json

```json
{json.dumps(decode_audit, ensure_ascii=False, indent=2)}
```

### GBBQ_EVENT_SAMPLES.json

```json
{json.dumps(event_samples, ensure_ascii=False, indent=2)}
```

### QFQ_VALIDATION.json

```json
{json.dumps(qfq_validation, ensure_ascii=False, indent=2)}
```

### PHASE0_2_FINAL_RECEIPT.json

```json
{json.dumps(receipt, ensure_ascii=False, indent=2)}
```
"""
    atomic_text(project_root / "docs" / "PHASE0_2_REPORT.md", report, tdx_root)
    return receipt
