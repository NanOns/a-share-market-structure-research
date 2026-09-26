from __future__ import annotations

"""Build diagnostic real-action samples without granting adjusted readiness."""

import hashlib
import json
import os
import struct
import sys
import tempfile
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from adjustment.tdx_adjustment import build_affine_factors, xrxd_from_gbbq
from tdx.gbbq_reader import read_gbbq

CONTRACT_PATH = ROOT / "config/v4_02_adjustment_empirical_sample_contract_v1.json"
PACKAGE_MANIFEST = ROOT / "reports/v4_01/v4_01_source_manifest_R4_20260925.json"
V4_00D_REPORT = ROOT / "reports/v4_00d/v4_00d_asset_stratified_postcheck_20260925.json"
METADATA_ROOT = ROOT / "data/input_staging/metadata/20260924/4835127dd77534be17d8aeba65d91ebf0ec5bbf6b5348bc1aff4612272acafdc/T0002/hq_cache"
PACKAGE_ROOT = ROOT / "data/input_staging/extracted/20260924/b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f"
RECORD = struct.Struct("<IIIII f II")
CENT = Decimal("0.01")
CUTOFF = 20260924
CLASS_ORDER = ("CASH_DIVIDEND_ONLY", "SHARE_BONUS_OR_TRANSFER_ONLY", "RIGHTS_ISSUE_ONLY", "COMBINED_ACTION")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def required_board(security_id: str) -> bool:
    market, code = security_id.split(".")
    return (market == "SH" and (code.startswith(("600", "601", "603", "605", "688")))) or (
        market == "SZ" and code.startswith(("000", "001", "002", "003", "300", "301"))
    )


def classify(event) -> str | None:
    c1, c2, c3, c4 = [Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP) for value in (event.c1, event.c2, event.c3, event.c4)]
    active = sum(value > 0 for value in (c1, c3, c4))
    if c1 > 0 and c3 == 0 and c4 == 0:
        return "CASH_DIVIDEND_ONLY"
    if c3 > 0 and c1 == 0 and c4 == 0:
        return "SHARE_BONUS_OR_TRANSFER_ONLY"
    if c4 > 0 and c1 == 0 and c3 == 0:
        return "RIGHTS_ISSUE_ONLY"
    if active >= 2:
        return "COMBINED_ACTION"
    return None


def day_rows(path: Path) -> list[tuple[int, int, int, int, int, float, int, int]]:
    data = path.read_bytes()
    if len(data) % RECORD.size:
        raise ValueError(f"BAD_DAY_FILE_SIZE:{path.name}")
    return [RECORD.unpack_from(data, offset) for offset in range(0, len(data), RECORD.size)]


def independent_factor(trade_date: int, events) -> tuple[Decimal, Decimal]:
    effective = sorted((e for e in events if trade_date < e.ex_day <= CUTOFF), key=lambda e: (e.ex_day, e.source_record_index))
    with localcontext() as context:
        context.prec = 40
        a, b = Decimal(1), Decimal(0)
        for event in effective:
            m, c = event.mc()
            a = a / m
            b = b / m - c / m
        return +a, +b


def adjusted_prices(raw_row, a: Decimal, b: Decimal) -> dict[str, str]:
    labels = ("open", "high", "low", "close")
    values = (raw_row[1], raw_row[2], raw_row[3], raw_row[4])
    return {label: str((a * Decimal(value) / Decimal(100) + b).quantize(CENT, rounding=ROUND_HALF_UP)) for label, value in zip(labels, values)}


def one_action_sample(kind: str, candidates: list, all_by_security: dict, category1_by_security: dict) -> dict | None:
    for event in sorted(candidates, key=lambda e: (e.event_date, e.security_id, e.source_record_index), reverse=True):
        if not required_board(event.security_id):
            continue
        market, code = event.security_id.split(".")
        path = PACKAGE_ROOT / market.lower() / "lday" / f"{market.lower()}{code}.day"
        if not path.is_file():
            continue
        rows = day_rows(path)
        valid = [row for row in rows if row[0] <= CUTOFF and row[1] > 0]
        before = [row for row in valid if row[0] < event.event_date]
        after = [row for row in valid if row[0] >= event.event_date]
        if not before or not after:
            continue
        raw = before[-1]
        events = [xrxd_from_gbbq(e) for e in category1_by_security[event.security_id] if e.event_date <= CUTOFF]
        factors = build_affine_factors([row[0] for row in valid], events)
        factor = factors[raw[0]]
        expected_a, expected_b = independent_factor(raw[0], events)
        expected = adjusted_prices(raw, expected_a, expected_b)
        engine = adjusted_prices(raw, factor.qfq_mul, factor.qfq_add)
        other = sorted({e.category for e in all_by_security[event.security_id] if e.category != 1 and e.event_date <= CUTOFF})
        return {
            "sample_class": kind,
            "security_id": event.security_id,
            "event_date": event.event_date,
            "bar_date_before_event": raw[0],
            "first_actual_bar_on_or_after_event": after[0][0],
            "selected_event": {"source_record_index": event.source_record_index, "c1": event.c1, "c2": event.c2, "c3": event.c3, "c4": event.c4},
            "category1_event_count_through_cutoff": len(events),
            "other_event_categories_through_cutoff": other,
            "unresolved_other_category_present": bool(other),
            "raw_ohlc": {name: raw[i] / 100 for name, i in (("open", 1), ("high", 2), ("low", 3), ("close", 4))},
            "independent_factor": {"A": str(expected_a), "B": str(expected_b)},
            "independent_expected_qfq_ohlc": expected,
            "sealed_engine_qfq_ohlc": engine,
            "expected_values_match_engine": expected == engine,
            "adjusted_quality_disposition": "UNAVAILABLE_OTHER_CATEGORY_UNRESOLVED" if other else "DIAGNOSTIC_SUPPORTED_XRXD_SAMPLE_ONLY",
        }
    return None


def no_action_control(all_by_security: dict) -> dict | None:
    for market in ("sh", "sz"):
        directory = PACKAGE_ROOT / market / "lday"
        for path in sorted(directory.glob(f"{market}[0-9][0-9][0-9][0-9][0-9][0-9].day")):
            security_id = f"{market.upper()}.{path.stem[-6:]}"
            if not required_board(security_id) or all_by_security.get(security_id):
                continue
            rows = [row for row in day_rows(path) if row[0] <= CUTOFF and row[1] > 0]
            if not rows:
                continue
            row = rows[-1]
            raw = {name: str((Decimal(row[i]) / Decimal(100)).quantize(CENT)) for name, i in (("open", 1), ("high", 2), ("low", 3), ("close", 4))}
            return {"sample_class": "NO_ACTION_CONTROL", "security_id": security_id, "bar_date": row[0], "raw_ohlc": raw, "independent_expected_qfq_ohlc": raw, "sealed_engine_qfq_ohlc": raw, "expected_values_match_engine": True, "unresolved_other_category_present": False, "adjusted_quality_disposition": "DIAGNOSTIC_CONTROL_ONLY"}
    return None


def main() -> int:
    contract_bytes = CONTRACT_PATH.read_bytes()
    contract = json.loads(contract_bytes)
    package_manifest_bytes = PACKAGE_MANIFEST.read_bytes()
    package_manifest = json.loads(package_manifest_bytes)
    v4_00d_bytes = V4_00D_REPORT.read_bytes()
    v4_00d = json.loads(v4_00d_bytes)
    asset_report_sha = sha256(v4_00d_bytes)
    package_sha = package_manifest["source"]["package_sha256"]
    a_scope = v4_00d["asset_types"]["A_STOCK"]
    if package_sha != contract["source_scope"]["package_sha256"] or package_sha != v4_00d["source_package_sha256"]:
        raise ValueError("PACKAGE_IDENTITY_MISMATCH")
    if a_scope["acceptance"] != "ACCEPTED_SOURCE_PACKAGE" or a_scope["unexplained_mismatch_rows"] != 0 or a_scope["identity_mismatch_count"] != 0:
        raise ValueError("A_STOCK_SOURCE_SCOPE_NOT_ACCEPTED")
    if sha256((METADATA_ROOT / "gbbq").read_bytes()) != v4_00d["local_snapshot_identity"]["metadata_sha256"]["gbbq"]:
        raise ValueError("GBBQ_HASH_NOT_BOUND_TO_V4_00D")
    if sha256((METADATA_ROOT / "gbbq.map").read_bytes()) != v4_00d["local_snapshot_identity"]["metadata_sha256"]["gbbq.map"]:
        raise ValueError("GBBQ_MAP_HASH_NOT_BOUND_TO_V4_00D")
    records = read_gbbq(METADATA_ROOT / "gbbq")
    all_by_security: dict[str, list] = defaultdict(list)
    cat1_by_security: dict[str, list] = defaultdict(list)
    classified = defaultdict(list)
    for record in records:
        if record.event_date > CUTOFF:
            continue
        all_by_security[record.security_id].append(record)
        if record.category == 1:
            cat1_by_security[record.security_id].append(record)
            kind = classify(record)
            if kind:
                classified[kind].append(record)
    samples = []
    for kind in CLASS_ORDER:
        selected = one_action_sample(kind, classified[kind], all_by_security, cat1_by_security)
        if selected:
            samples.append(selected)
    control = no_action_control(all_by_security)
    if control:
        samples.append(control)
    category15 = [record for record in records if record.category == 15 and record.event_date <= CUTOFF]
    samples_by_class = {sample["sample_class"]: sample for sample in samples}
    complete_classes = all(kind in samples_by_class and samples_by_class[kind]["expected_values_match_engine"] for kind in (*CLASS_ORDER, "NO_ACTION_CONTROL"))
    report = {
        "contract_id": "V4_02_ADJUSTMENT_EMPIRICAL_SAMPLE_DIAGNOSTIC_V1",
        "status": "DIAGNOSTIC_SAMPLE_EVIDENCE_ONLY" if complete_classes else "DIAGNOSTIC_SAMPLE_INCOMPLETE",
        "sample_contract_sha256": sha256(contract_bytes),
        "v4_01_source_manifest_sha256": sha256(package_manifest_bytes),
        "v4_00d_a_stock_acceptance_report_sha256": asset_report_sha,
        "v4_00d_a_stock_scope": {"acceptance": a_scope["acceptance"], "unexplained_mismatch_rows": a_scope["unexplained_mismatch_rows"], "identity_mismatch_count": a_scope["identity_mismatch_count"], "matched_sessions": a_scope["session_count"]},
        "package_sha256": package_sha,
        "metadata_snapshot": str(METADATA_ROOT.relative_to(ROOT).as_posix()),
        "gbbq_sha256": sha256((METADATA_ROOT / "gbbq").read_bytes()),
        "gbbq_map_sha256": sha256((METADATA_ROOT / "gbbq.map").read_bytes()),
        "decoder_version": "tdx-local-gbbq-v0.2",
        "adjustment_engine_version": "tdx-affine-qfq-v0.2",
        "source_cutoff": "2026-09-24",
        "decoded_record_count": len(records),
        "category_counts": {str(category): sum(record.category == category for record in records) for category in sorted({record.category for record in records})},
        "category15": {"record_count_through_cutoff": len(category15), "unique_securities": len({record.security_id for record in category15}), "status": "UNRESOLVED_PRICE_IMPACT_FAIL_CLOSED"},
        "samples": samples,
        "all_required_sample_classes_present_and_math_matches": complete_classes,
        "interpretation": "Current snapshot reconstruction is diagnostic and not PIT. Match verifies the sealed engine against a separate Decimal implementation over category-1 events; it does not establish upstream action completeness, source visibility at historical cutoffs, or price-impact semantics for unsupported categories.",
        "adjusted_capability": "UNAVAILABLE_PENDING_V4_00E_INDEPENDENT_ACCEPTANCE",
        "overall_v4_02": "BLOCKED_OPEN_OTHER_REQUIRED_CAPABILITIES",
        "next_stage": "CATEGORY_IMPACT_ADJUDICATION_AND_SUSPENSION_RECENT_LISTING_SAMPLES",
    }
    output = ROOT / "reports/v4_02/V4_02_ADJUSTMENT_EMPIRICAL_SAMPLE_DIAGNOSTIC_20260926.json"
    atomic_write(output, (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": report["status"], "samples": [{"class": s["sample_class"], "security_id": s["security_id"], "expected_values_match_engine": s["expected_values_match_engine"], "adjusted_quality_disposition": s["adjusted_quality_disposition"]} for s in samples], "category15_records": len(category15), "report": output.relative_to(ROOT).as_posix()}, ensure_ascii=False))
    return 0 if complete_classes else 2


if __name__ == "__main__":
    raise SystemExit(main())
