from __future__ import annotations

"""Independently verify V4-01 Gate V2 scan and create candidate-only receipts."""

import gzip
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from v4_01_generic_relation_resolution import (
        build_candidate_union,
        candidates_from_events,
        validate_resolution_coverage,
    )
except ModuleNotFoundError:  # imported by tests as scripts.postcheck_...
    from scripts.v4_01_generic_relation_resolution import (
        build_candidate_union,
        candidates_from_events,
        validate_resolution_coverage,
    )

ROOT = Path(__file__).resolve().parents[1]
UNIVERSE = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz")
IDENTITY = Path("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
GLOBAL_HEAD = Path("data/v4/V4_STAGE_ACCEPTED_HEAD.json")
ARCHIVE = Path("data/v4/raw_archive/b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f/hsjday.zip")
DISCOVERY = Path("reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_3.json")
R8_POSTCHECK = Path("reports/v4_01/V4_01_R8_IDENTITY_UNIVERSE_POSTCHECK_20260928.json")
R83_POSTCHECK = Path("reports/v4_01/V4_01_R8_3_INDEPENDENT_POSTCHECK.json")
SCAN = Path("reports/v4_01/V4_01_FULL_SCOPE_SOURCE_FINGERPRINT_SCAN_R1.json")
GATE = Path("config/v4_01_identity_completeness_gate_v2.json")
FINGERPRINT_CONTRACT = Path("config/v4_01_source_fingerprint_candidate_v1.json")
OFFICIAL_INDEX = Path("data/v4/source_evidence/official_code_change_event_index/official_security_code_change_events_v1.jsonl")
OFFICIAL_COVERAGE = Path("data/v4/source_evidence/official_code_change_event_index/coverage_receipt_v1.json")
REPORTS_V401 = Path("reports/v4_01")
BLIND_RECEIPT = Path("reports/v4_01/V4_01_SOURCE_FINGERPRINT_CANDIDATE_BLIND_VALIDATION_R1.json")
BLIND_LABELS = Path("config/v4_01_source_fingerprint_blind_labels_v1.json")
EXTERNAL_CODE_REVIEW = Path("docs/evidence/V4_01_CODE_CHANGE_SOURCE_FINGERPRINT_EXTERNAL_ACCEPTANCE_20260929.md")
EXTERNAL_BLIND_REVIEW = Path("docs/evidence/V4_01_SOURCE_FINGERPRINT_BLIND_STUDY_EXTERNAL_ACCEPTANCE_R1_20260929.md")
EXTERNAL_AUDIT = Path("docs/evidence/V4_00_01_02_03_FOUNDATION_CANDIDATE_EXTERNAL_AUDIT_R1_20260929.md")
REPAIR_TASK = Path("docs/evidence/V4_00_01_02_03_FOUNDATION_FINAL_REPAIR_TASK_R3_20260929.md")
EXTERNAL_REVIEW_HEAD = "ecfcc3209404df5ccc7daaf6af905459cc075542"
CALIBRATION_AUDIT = Path("docs/audits/V4_01_SOURCE_FINGERPRINT_CALIBRATION_AUDIT_ITEM_R1_20260929.md")
OUTPUT_RESOLUTION = Path("reports/v4_01/V4_01_IDENTITY_RELATION_RESOLUTION_R2.json")
OUTPUT_POSTCHECK = Path("reports/v4_01/V4_01_IDENTITY_COMPLETENESS_GATE_V2_POSTCHECK_R2.json")
OUTPUT_FINAL_CANDIDATE = Path("reports/v4_01/V4_01_FINAL_STAGE_CANDIDATE_R10.json")
OUTPUT_HEAD_CANDIDATE = Path("data/v4/V4_01_ACCEPTED_HEAD_CANDIDATE.json")
REQUIRED_BOARDS = {"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"}
DAY = struct.Struct("<IIIIIfII")
PRICE = 100.0
BUSINESS_FIELDS = ("open", "high", "low", "close", "amount", "volume")
STRICT_FIELDS = ("open", "high", "low", "close", "amount")


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_identity(path: Path) -> dict[str, Any]:
    absolute = ROOT / path
    return {"path": path.as_posix(), "sha256": file_sha(path), "byte_count": absolute.stat().st_size}


def load_json(path: Path) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def archive_member(code: str) -> str:
    market, digits = code.upper().split(".", 1)
    return f"{market.lower()}/lday/{market.lower()}{digits}.day"


def day_text(value: int) -> str:
    return date(value // 10000, value // 100 % 100, value % 100).isoformat()


def decode_day(raw: bytes, code: str) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    tail = len(raw) % DAY.size
    rows: dict[str, dict[str, Any]] = {}
    previous = None
    duplicates = 0
    decreasing = 0
    for offset in range(0, len(raw) - tail, DAY.size):
        trade_date, open_, high, low, close, amount, volume, _reserved = DAY.unpack_from(raw, offset)
        key = day_text(trade_date)
        if key in rows:
            duplicates += 1
        if previous is not None and trade_date <= previous:
            decreasing += 1
        previous = trade_date
        rows[key] = {
            "open": open_ / PRICE,
            "high": high / PRICE,
            "low": low / PRICE,
            "close": close / PRICE,
            "amount": float(amount),
            "volume": volume,
        }
    return rows, {
        "code": code,
        "byte_count": len(raw),
        "record_count": len(rows),
        "tail_bytes": tail,
        "duplicate_dates": duplicates,
        "non_increasing_dates": decreasing,
        "first_date": next(iter(rows), None),
        "last_date": next(reversed(rows), None),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def independent_tdx_comparison(archive: zipfile.ZipFile, candidate: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    old_code = str(candidate["old_source_security_key"]).upper()
    new_code = str(candidate["new_source_security_key"]).upper()
    effective_date = str(candidate["effective_date"])
    try:
        old_raw = archive.read(archive_member(old_code))
        new_raw = archive.read(archive_member(new_code))
    except KeyError as exc:
        return {
            "decoded": False,
            "error": "TDX_MEMBER_MISSING",
            "missing_member": str(exc),
            "old": None,
            "new": None,
            "shared_pre_effective_sessions": 0,
            "ohlc_amount_exact_count": 0,
            "volume_exact_count": 0,
            "volume_exact_ratio": None,
            "semantic_candidate_match": False,
        }
    old_rows, old_meta = decode_day(old_raw, old_code)
    new_rows, new_meta = decode_day(new_raw, new_code)
    shared = sorted(day for day in old_rows.keys() & new_rows.keys() if day < effective_date)
    strict_exact = sum(
        all(old_rows[day][field] == new_rows[day][field] for field in STRICT_FIELDS)
        for day in shared
    )
    volume_exact = sum(old_rows[day]["volume"] == new_rows[day]["volume"] for day in shared)
    threshold = contract.get("research_thresholds", {})
    minimum_sessions = int(threshold.get("minimum_shared_sessions", 20))
    minimum_volume_ratio = float(threshold.get("tdx_volume_exact_ratio_minimum", 0.95))
    decoded = all(
        meta["tail_bytes"] == 0
        and meta["duplicate_dates"] == 0
        and meta["non_increasing_dates"] == 0
        for meta in (old_meta, new_meta)
    )
    ratio = volume_exact / len(shared) if shared else None
    return {
        "decoded": decoded,
        "old": old_meta,
        "new": new_meta,
        "shared_pre_effective_sessions": len(shared),
        "ohlc_amount_exact_count": strict_exact,
        "volume_exact_count": volume_exact,
        "volume_exact_ratio": ratio,
        "semantic_candidate_match": bool(
            decoded
            and len(shared) >= minimum_sessions
            and strict_exact == len(shared)
            and ratio is not None
            and ratio >= minimum_volume_ratio
        ),
        "thresholds": {
            "minimum_shared_sessions": minimum_sessions,
            "tdx_volume_exact_ratio_minimum": minimum_volume_ratio,
            "used_for_identity_confirmation": False,
        },
    }


def frozen_baostock_evidence(candidate: dict[str, Any]) -> dict[str, Any]:
    old_code = str(candidate["old_source_security_key"]).lower()
    new_code = str(candidate["new_source_security_key"]).lower()
    old_digits, new_digits = old_code.split(".", 1)[-1], new_code.split(".", 1)[-1]
    stem = f"V4_01_CODE_CHANGE_SOURCE_FINGERPRINT_{old_digits}_{new_digits}_R1.json"
    relative = REPORTS_V401 / stem
    source_path = ROOT / relative
    compressed = False
    if not source_path.is_file():
        relative = REPORTS_V401 / f"{stem}.gz"
        source_path = ROOT / relative
        compressed = source_path.is_file()
    if not source_path.is_file():
        return {"available": False, "status": "NOT_AVAILABLE_FOR_CANDIDATE"}
    try:
        if compressed:
            with gzip.open(source_path, "rt", encoding="utf-8") as stream:
                diagnostic = json.load(stream)
        else:
            diagnostic = json.loads(source_path.read_text(encoding="utf-8"))
        long_history = diagnostic.get("baostock", {}).get("long_history", {})
        old_rows = long_history.get(old_code, {}).get("raw_rows", [])
        new_rows = long_history.get(new_code, {}).get("raw_rows", [])
        old_by_date = {str(row.get("date")): row for row in old_rows}
        new_by_date = {str(row.get("date")): row for row in new_rows}
        shared_dates = sorted((old_by_date.keys() & new_by_date.keys()))
        value_fields = sorted((old_by_date[shared_dates[0]].keys() & new_by_date[shared_dates[0]].keys()) - {"code", "date"}) if shared_dates else []
        exact_dates = [
            day for day in shared_dates
            if all(old_by_date[day].get(field) == new_by_date[day].get(field) for field in value_fields)
        ]
        return {
            "available": True,
            "status": "FROZEN_PAIR_EVIDENCE_READ" if old_rows and new_rows else "FROZEN_REPORT_PAIR_ROWS_INCOMPLETE",
            "path": relative.as_posix(),
            "sha256": file_sha(relative),
            "compressed": compressed,
            "old_query_row_count": len(old_rows),
            "new_query_row_count": len(new_rows),
            "shared_date_count": len(shared_dates),
            "exact_shared_bar_count_excluding_query_code": len(exact_dates),
            "compared_fields": value_fields,
            "used_for_identity_confirmation": False,
        }
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "available": True,
            "status": "FROZEN_REPORT_READ_FAILED",
            "path": relative.as_posix(),
            "sha256": file_sha(relative),
            "error": type(exc).__name__,
            "used_for_identity_confirmation": False,
        }


def _dated_identity_pair(
    candidate: dict[str, Any], identity_records: list[dict[str, Any]]
) -> dict[str, Any]:
    old_code = candidate["old_source_security_key"]
    new_code = candidate["new_source_security_key"]
    effective = candidate["effective_date"]
    prior = (date.fromisoformat(effective) - timedelta(days=1)).isoformat()
    old_rows = [row for row in identity_records if row.get("source_security_key") == old_code]
    new_rows = [row for row in identity_records if row.get("source_security_key") == new_code]
    old = next((row for row in old_rows if row.get("symbol_effective_to") == prior or row.get("effective_to") == prior), None)
    new = next((row for row in new_rows if row.get("symbol_effective_from") == effective or row.get("effective_from") == effective), None)
    old_id = (old or {}).get("security_id")
    new_id = (new or {}).get("security_id")
    return {
        "boundary_facts_match": old is not None and new is not None,
        "same_security_id": bool(old_id and old_id == new_id),
        "distinct_security_ids": bool(old_id and new_id and old_id != new_id),
        "old_fact": old,
        "new_fact": new,
    }


def _verified_official_event(
    candidate: dict[str, Any], official_events: list[dict[str, Any]]
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    key = (
        candidate["old_source_security_key"],
        candidate["new_source_security_key"],
        candidate["effective_date"],
    )
    for event in official_events:
        event_key = (
            str(event.get("old_source_security_key") or "").upper(),
            str(event.get("new_source_security_key") or "").upper(),
            str(event.get("effective_date") or ""),
        )
        if event_key != key:
            continue
        relative = Path(str(event.get("source_capture_path") or ""))
        resolved = (ROOT / relative).resolve()
        root_resolved = ROOT.resolve()
        safe_path = resolved == root_resolved or root_resolved in resolved.parents
        actual_hash = file_sha(relative) if safe_path and (ROOT / relative).is_file() else None
        bound_hash = str(event.get("source_capture_sha256") or "")
        return event, {
            "event_index_match": True,
            "capture_path": relative.as_posix(),
            "capture_sha256_bound": bound_hash or None,
            "capture_sha256_actual": actual_hash,
            "capture_hash_verified": bool(bound_hash and actual_hash == bound_hash),
            "entity_relation": event.get("entity_relation"),
            "evidence_class": event.get("evidence_class"),
        }
    return None, {"event_index_match": False, "capture_hash_verified": False}


def resolve_candidate(
    candidate: dict[str, Any],
    *,
    archive: zipfile.ZipFile,
    identity_records: list[dict[str, Any]],
    official_events: list[dict[str, Any]],
    fingerprint_contract: dict[str, Any],
) -> dict[str, Any]:
    tdx = independent_tdx_comparison(archive, candidate, fingerprint_contract)
    baostock = frozen_baostock_evidence(candidate)
    identity_pair = _dated_identity_pair(candidate, identity_records)
    official_event, official_evidence = _verified_official_event(candidate, official_events)
    relation = str((official_event or {}).get("entity_relation") or "").upper()
    identity_revision_bound = bool(
        identity_pair["boundary_facts_match"]
        and identity_pair["same_security_id"]
        and identity_pair["old_fact"].get("source_revision_id")
        and identity_pair["old_fact"].get("source_revision_id") == identity_pair["new_fact"].get("source_revision_id")
    )
    official_verified = official_evidence.get("capture_hash_verified") is True

    resolution = "UNRESOLVED_IDENTITY_RELATION"
    basis = "NO_MATCHING_INDEPENDENT_OFFICIAL_OR_ACCEPTED_DATED_IDENTITY_EVIDENCE"
    if identity_revision_bound and (official_verified or str(identity_pair["old_fact"].get("source_revision_id", "")).startswith("sha256:")):
        resolution = "CONFIRMED_SAME_ENTITY_CODE_CHANGE"
        basis = "ACCEPTED_DATED_IDENTITY_INTERVALS_WITH_SHARED_SECURITY_ID_AND_BOUND_SOURCE_REVISION"
    if official_verified and identity_pair["boundary_facts_match"]:
        if relation in {"SAME_ENTITY", "SAME_ENTITY_CODE_CHANGE", "CODE_CHANGE_SAME_ENTITY"} and identity_pair["same_security_id"]:
            resolution = "CONFIRMED_SAME_ENTITY_CODE_CHANGE"
            basis = "HASH_VERIFIED_OFFICIAL_SAME_ENTITY_EVENT_AND_ACCEPTED_DATED_IDENTITY_FACTS"
        elif relation in {"DISTINCT_MERGER_SUCCESSOR", "MERGER_SUCCESSOR", "DISTINCT_ENTITY_MERGER_SUCCESSOR"} and identity_pair["distinct_security_ids"]:
            resolution = "CONFIRMED_DISTINCT_MERGER_SUCCESSOR"
            basis = "HASH_VERIFIED_OFFICIAL_MERGER_SUCCESSOR_EVENT_AND_DISTINCT_ACCEPTED_IDENTITY_FACTS"
        elif relation in {"DISTINCT_CODE_REUSE", "CODE_REUSE", "REUSED_CODE_DISTINCT_ENTITY"} and identity_pair["distinct_security_ids"]:
            resolution = "CONFIRMED_DISTINCT_CODE_REUSE"
            basis = "HASH_VERIFIED_OFFICIAL_CODE_REUSE_EVENT_AND_DISTINCT_ACCEPTED_IDENTITY_FACTS"

    return {
        **candidate,
        "resolution": resolution,
        "resolution_basis": basis,
        "source_fingerprint_candidate": "CANDIDATE_DISCOVERY_ONLY" if "source_fingerprint_scan" in candidate.get("sources", []) else "NOT_A_SOURCE_FINGERPRINT_SCAN_CANDIDATE",
        "independent_confirmation": {
            "official_event": official_evidence,
            "accepted_dated_identity": {
                "boundary_facts_match": identity_pair["boundary_facts_match"],
                "same_security_id": identity_pair["same_security_id"],
                "distinct_security_ids": identity_pair["distinct_security_ids"],
                "old_fact": identity_pair["old_fact"],
                "new_fact": identity_pair["new_fact"],
            },
        },
        "independent_source_replay": {
            "tdx_semantic_redecode": tdx,
            "frozen_baostock_evidence": baostock,
        },
        "canonical_identity_mutation": False,
    }


def independent_boundary_scan() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    exits: list[dict[str, Any]] = []
    session_dates: list[str] = []
    board_rows: Counter[str] = Counter()
    source_keys: set[str] = set()
    row_count = 0
    duplicate_rows = 0
    day_key: str | None = None
    rows: dict[str, dict[str, str]] = {}
    previous_day: str | None = None
    previous_keys: set[str] = set()
    baseline_count = None

    def close_session(current_day: str, members: dict[str, dict[str, str]]) -> set[str]:
        nonlocal baseline_count, duplicate_rows
        current = set(members)
        if previous_day is None:
            baseline_count = len(current)
        else:
            for code in sorted(current - previous_keys):
                entries.append({"source_security_key": code, "entry_date": current_day, **members[code]})
            for code in sorted(previous_keys - current):
                exits.append({"source_security_key": code, "last_present_session": previous_day, "first_absent_session": current_day})
        return current

    with gzip.open(ROOT / UNIVERSE, "rt", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            row_count += 1
            session = str(row.get("trade_date") or "")
            code = str(row.get("source_security_key") or "").upper()
            board = str(row.get("board_scope") or "")
            if not session or not code or board not in REQUIRED_BOARDS:
                raise ValueError("REQUIRED_UNIVERSE_ROW_INVALID")
            date.fromisoformat(session)
            if day_key is None:
                day_key = session
            elif session != day_key:
                if session < day_key:
                    raise ValueError("REQUIRED_UNIVERSE_NOT_SESSION_SORTED")
                previous_keys = close_session(day_key, rows)
                session_dates.append(day_key)
                previous_day = day_key
                day_key = session
                rows = {}
            if code in rows:
                duplicate_rows += 1
                if rows[code]["security_id"] != str(row.get("security_id") or ""):
                    raise ValueError("SOURCE_KEY_IDENTITY_CHANGED_WITHIN_SESSION")
            else:
                rows[code] = {"security_id": str(row.get("security_id") or ""), "board_scope": board}
            source_keys.add(code)
            board_rows[board] += 1
    if day_key is not None:
        previous_keys = close_session(day_key, rows)
        session_dates.append(day_key)
    return {
        "session_dates": session_dates,
        "entries": entries,
        "exits": exits,
        "rows_scanned": row_count,
        "source_key_count": len(source_keys),
        "duplicate_source_key_session_rows": duplicate_rows,
        "board_rows": dict(sorted(board_rows.items())),
        "first_session_baseline_key_count": baseline_count,
    }


def atomic_write(path: Path, value: dict[str, Any]) -> bytes:
    destination = ROOT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd, temp_path = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, destination)
    finally:
        Path(temp_path).unlink(missing_ok=True)
    return payload


def main() -> int:
    scan = load_json(SCAN)
    discovery = load_json(DISCOVERY)
    global_head = load_json(GLOBAL_HEAD)
    identity_map = load_json(IDENTITY)
    r8_check = load_json(R8_POSTCHECK)
    r83_check = load_json(R83_POSTCHECK)
    blind_receipt = load_json(BLIND_RECEIPT)
    labels = load_json(BLIND_LABELS)
    coverage_receipt = load_json(OFFICIAL_COVERAGE)

    independent = independent_boundary_scan()
    scan_boundaries = scan["atomic_boundaries"]
    boundary_equal = (
        independent["entries"] == scan_boundaries["source_entries"]
        and independent["exits"] == scan_boundaries["source_exits"]
        and independent["rows_scanned"] == scan["scope"]["accepted_r7_rows_scanned"]
        and independent["session_dates"][0] == scan["scope"]["first_session"]
        and independent["session_dates"][-1] == scan["scope"]["last_session"]
        and len(independent["session_dates"]) == scan["scope"]["session_count"]
        and independent["duplicate_source_key_session_rows"] == 0
    )

    archive_hash = file_sha(ARCHIVE)
    bound_archive_hash = global_head.get("bindings", {}).get("tdx_archive", {}).get("sha256")
    bound_identity = global_head.get("bindings", {}).get("v4_01_identity_map", {})
    bound_universe = global_head.get("bindings", {}).get("v4_01_universe", {})
    identity_hash = file_sha(IDENTITY)
    universe_hash = file_sha(UNIVERSE)
    input_bindings_match = (
        archive_hash == bound_archive_hash
        and identity_hash == bound_identity.get("sha256")
        and universe_hash == bound_universe.get("sha256")
    )

    identity_records = identity_map.get("records", [])
    official_events = [json.loads(line) for line in (ROOT / OFFICIAL_INDEX).read_text(encoding="utf-8").splitlines() if line.strip()]
    window_start = str(scan["scope"]["first_session"])
    window_end = str(scan["scope"]["last_session"])
    r8_generic_candidates = candidates_from_events(
        discovery.get("events", []),
        source="r8_generic_relation",
        window_start=window_start,
        window_end=window_end,
        identity_records=identity_records,
        require_required_scope=True,
    )
    known_official_candidates = candidates_from_events(
        official_events,
        source="known_official_event",
        window_start=window_start,
        window_end=window_end,
    )
    candidate_union = build_candidate_union(
        scan.get("relation_candidates", []),
        r8_generic_candidates,
        known_official_candidates,
        window_start=window_start,
        window_end=window_end,
    )

    entry_expectations = {item["source_security_key"]: item for item in scan_boundaries["source_entries"]}
    entry_checks = {item["source_security_key"]: item for item in scan_boundaries["entry_tdx_checks"]}
    recomputed_pre_effective: list[dict[str, Any]] = []
    archive_entry_hashes_match = True
    candidate_resolutions = []
    with zipfile.ZipFile(ROOT / ARCHIVE) as archive:
        for code, entry in entry_expectations.items():
            member = archive_member(code)
            try:
                info = archive.getinfo(member)
            except KeyError:
                archive_entry_hashes_match = False
                continue
            with archive.open(info, "r") as source:
                first = source.read(DAY.size)
            if len(first) != DAY.size:
                archive_entry_hashes_match = False
                continue
            trade_date = DAY.unpack(first)[0]
            first_date = day_text(trade_date)
            expected = entry_checks.get(code, {}).get("tdx_file", {})
            if first_date != expected.get("first_date") or hashlib.sha256(first).hexdigest() != expected.get("first_record_sha256"):
                archive_entry_hashes_match = False
            if first_date < entry["entry_date"]:
                recomputed_pre_effective.append({"source_security_key": code, "entry_date": entry["entry_date"], "tdx_first_date": first_date})
        fingerprint_contract = load_json(FINGERPRINT_CONTRACT)
        for candidate in candidate_union.values():
            candidate_resolutions.append(resolve_candidate(
                candidate,
                archive=archive,
                identity_records=identity_records,
                official_events=official_events,
                fingerprint_contract=fingerprint_contract,
            ))

    resolution_coverage = validate_resolution_coverage(candidate_union, candidate_resolutions)
    candidate_tdx_decode_complete = all(
        item["independent_source_replay"]["tdx_semantic_redecode"].get("decoded") is True
        for item in candidate_resolutions
    )
    scan_candidate_by_key = {
        (item["old_source_security_key"], item["new_source_security_key"], item["effective_date"]): item
        for item in scan.get("relation_candidates", [])
    }
    scan_candidate_replays_match = True
    for item in candidate_resolutions:
        key = (item["old_source_security_key"], item["new_source_security_key"], item["effective_date"])
        scanned = scan_candidate_by_key.get(key)
        replay = item["independent_source_replay"]["tdx_semantic_redecode"]
        if scanned is not None:
            expected = scanned.get("tdx_semantic_comparison", {})
            scan_candidate_replays_match &= (
                expected.get("shared_pre_effective_sessions") == replay.get("shared_pre_effective_sessions")
                and expected.get("ohlc_amount_exact_count") == replay.get("ohlc_amount_exact_count")
                and expected.get("volume_exact_count") == replay.get("volume_exact_count")
                and expected.get("old", {}).get("sha256") == replay.get("old", {}).get("sha256")
                and expected.get("new", {}).get("sha256") == replay.get("new", {}).get("sha256")
            )
    # Fixed blind labels stay inside known_bounded_validation_crosschecks and
    # never contribute keys to the Required Scope candidate union.
    blind_case_pairs = {
        "BLIND-01": ("SZ.300114", "SZ.302132", "CONFIRMED_SAME_ENTITY_CODE_CHANGE"),
        "BLIND-02": ("SZ.000022", "SZ.001872", "CONFIRMED_SAME_ENTITY_CODE_CHANGE"),
        "BLIND-03": ("SZ.000024", "SZ.001979", "CONFIRMED_DISTINCT_MERGER_SUCCESSOR"),
        "BLIND-04": ("SZ.000562", "SZ.000166", "CONFIRMED_DISTINCT_MERGER_SUCCESSOR"),
    }
    blind_results = {item["case_id"]: item for item in blind_receipt.get("cases", [])}
    blind_labels = {item["case_id"]: item for item in labels.get("labels", [])}
    benchmark_resolutions = []
    benchmark_evidence_ok = True
    for case_id, (old_code, new_code, disposition) in blind_case_pairs.items():
        result = blind_results.get(case_id, {})
        label = blind_labels.get(case_id, {})
        expected_positive = disposition == "CONFIRMED_SAME_ENTITY_CODE_CHANGE"
        source_evidence = []
        for source in label.get("source_evidence", []):
            path = Path(source["repository_capture_path"])
            actual = file_sha(path) if (ROOT / path).is_file() else None
            valid = actual == source.get("sha256")
            benchmark_evidence_ok &= valid
            source_evidence.append({**source, "captured_file_sha256_verified": valid})
        case_valid = (
            result.get("old_code") == old_code
            and result.get("new_code") == new_code
            and result.get("predicted_positive") == expected_positive
            and result.get("evaluation_match") is True
            and result.get("candidate_auto_link_allowed") is False
            and result.get("production_identity_mutation_authorized") is False
            and bool(source_evidence)
            and all(item["captured_file_sha256_verified"] for item in source_evidence)
        )
        benchmark_evidence_ok &= case_valid
        benchmark_resolutions.append({
            "case_id": case_id,
            "old_source_security_key": old_code,
            "new_source_security_key": new_code,
            "resolution": disposition,
            "required_scope_scan_window": case_id == "BLIND-01",
            "independent_official_evidence": source_evidence,
            "candidate_evaluation_matches_label_without_auto_link": case_valid,
            "canonical_identity_changed": False,
        })

    r8_keys = {
        (item["old_source_security_key"], item["new_source_security_key"], item["effective_date"])
        for item in r8_generic_candidates
    }
    official_keys = {
        (item["old_source_security_key"], item["new_source_security_key"], item["effective_date"])
        for item in known_official_candidates
    }
    union_keys = set(candidate_union)
    unresolved = resolution_coverage["unresolved_count"]

    checks = {
        "accepted_input_hash_bindings_match_global_head": input_bindings_match,
        "independent_boundary_inventory_matches_scan": boundary_equal,
        "all_330_entry_tdx_files_present_and_first_records_match": archive_entry_hashes_match,
        "pre_effective_tdx_anomalies_match_scan": recomputed_pre_effective == [
            {"source_security_key": item["new_source_security_key"], "entry_date": item["entry_date"], "tdx_first_date": item["tdx_first_date"]}
            for item in scan.get("source_fingerprint_anomalies", [])
        ],
        "all_union_candidates_independently_tdx_decoded": candidate_tdx_decode_complete,
        "scan_candidate_tdx_replays_match_scan": scan_candidate_replays_match,
        "four_bounded_official_label_crosschecks_verified": benchmark_evidence_ok,
        "r8_generic_candidates_included_in_union": r8_keys.issubset(union_keys),
        "in_window_known_official_candidates_included_in_union": official_keys.issubset(union_keys),
        "r8_and_r8_3_postchecks_pass": r8_check.get("status") == "PASS" and r83_check.get("status") == "PASS",
        "official_event_index_incomplete_but_retained_as_cross_check": (
            bool(coverage_receipt.get("coverage_receipts"))
            and all(item.get("coverage_complete") is False for item in coverage_receipt.get("coverage_receipts", []))
            and any(item.get("unresolved_source_windows") for item in coverage_receipt.get("coverage_receipts", []))
        ),
        "calibration_audit_deferred_non_blocking": (
            "DEFERRED_NON_BLOCKING_RESEARCH" in (ROOT / CALIBRATION_AUDIT).read_text(encoding="utf-8")
            and "owner_stage_blocker = false" in (ROOT / CALIBRATION_AUDIT).read_text(encoding="utf-8")
            and "production_confirmation_authority = false" in (ROOT / CALIBRATION_AUDIT).read_text(encoding="utf-8")
        ),
        "tdx_archive_unchanged_during_postcheck": file_sha(ARCHIVE) == archive_hash,
        "production_identity_unchanged": file_sha(IDENTITY) == identity_hash and file_sha(UNIVERSE) == universe_hash,
    }
    checks["resolution_complete"] = resolution_coverage["status"] == "PASS" and unresolved == 0
    postcheck_status = "PASS_INDEPENDENT_POSTCHECK" if all(checks.values()) else "BLOCKED"
    observed_at = datetime.now().astimezone().isoformat(timespec="seconds")

    resolution = {
        "contract_id": "V4_01_IDENTITY_RELATION_RESOLUTION_R2",
        "version": "2.0.0-candidate",
        "stage": "V4-01 RELATION CANDIDATE RESOLUTION",
        "status": "RESOLVED_CANDIDATE" if checks["resolution_complete"] else "BLOCKED",
        "observed_at": observed_at,
        "stage_contract": {
            "gate_contract_path": GATE.as_posix(),
            "gate_contract_sha256": file_sha(GATE),
            "candidate_threshold_contract_path": FINGERPRINT_CONTRACT.as_posix(),
            "candidate_threshold_contract_sha256": file_sha(FINGERPRINT_CONTRACT),
            "candidate_thresholds_changed": False,
            "fingerprint_auto_confirmation": False,
            "production_identity_mutation": False,
            "candidate_union_key": ["old_source_security_key", "new_source_security_key", "effective_date"],
            "candidate_union_sources": ["source_fingerprint_scan", "r8_generic_relation", "known_official_event"],
            "resolution_coverage_must_equal_candidate_union": True,
        },
        "inputs": {
            path.as_posix(): file_identity(path)
            for path in (
                SCAN, DISCOVERY, IDENTITY, OFFICIAL_INDEX, OFFICIAL_COVERAGE,
                BLIND_RECEIPT, BLIND_LABELS, EXTERNAL_CODE_REVIEW, EXTERNAL_BLIND_REVIEW,
                EXTERNAL_AUDIT, REPAIR_TASK, CALIBRATION_AUDIT,
            )
        },
        "candidate_union": [candidate_union[key] for key in sorted(candidate_union)],
        "required_scope_relation_candidates": candidate_resolutions,
        "known_bounded_validation_crosschecks": benchmark_resolutions,
        "resolution_coverage": resolution_coverage,
        "summary": {
            "required_scope_candidate_count": len(candidate_union),
            "resolution_count": len(candidate_resolutions),
            "required_scope_confirmed_same_entity_count": sum(item["resolution"] == "CONFIRMED_SAME_ENTITY_CODE_CHANGE" for item in candidate_resolutions),
            "required_scope_confirmed_distinct_merger_successor_count": sum(item["resolution"] == "CONFIRMED_DISTINCT_MERGER_SUCCESSOR" for item in candidate_resolutions),
            "required_scope_confirmed_distinct_code_reuse_count": sum(item["resolution"] == "CONFIRMED_DISTINCT_CODE_REUSE" for item in candidate_resolutions),
            "required_scope_unresolved_count": unresolved,
            "candidate_union_source_counts": {
                "source_fingerprint_scan": len(scan.get("relation_candidates", [])),
                "r8_generic_relation": len(r8_generic_candidates),
                "in_window_known_official_event": len(known_official_candidates),
            },
            "known_event_index_coverage_complete": all(item.get("coverage_complete") is True for item in coverage_receipt.get("coverage_receipts", [])),
            "known_event_index_role": "KNOWN_EVENT_CROSS_CHECK_AND_CONFIRMATION_SOURCE; NOT_SOLE_EXHAUSTIVE_COMPLETENESS_GATE",
            "canonical_identity_changed": False,
            "next_stage": "INDEPENDENT_COMPLETENESS_POSTCHECK_AND_CANDIDATE_RECEIPT" if checks["resolution_complete"] else "BLOCKED_LIST_UNRESOLVED_PAIR_AND_MINIMUM_CONFIRMATION_GAP",
        },
        "stage_record": {
            "evidence": "Full candidate union, one independent TDX decode per canonical relation key, matching accepted identity and hash-bound official evidence where available, frozen BaoStock evidence where available, and blind crosschecks",
            "acceptance_result": "CANDIDATE_RESOLUTION_COMPLETE" if checks["resolution_complete"] else "BLOCKED",
            "next_stage": "INDEPENDENT_COMPLETENESS_POSTCHECK" if checks["resolution_complete"] else "RESOLVE_ONLY_LISTED_PAIR",
        },
    }
    resolution_bytes = atomic_write(OUTPUT_RESOLUTION, resolution)
    resolution_sha = hashlib.sha256(resolution_bytes).hexdigest()

    postcheck = {
        "contract_id": "V4_01_IDENTITY_COMPLETENESS_GATE_V2_POSTCHECK_R2",
        "version": "2.0.0-candidate",
        "stage": "V4-01 INDEPENDENT IDENTITY COMPLETENESS POSTCHECK",
        "status": postcheck_status,
        "observed_at": observed_at,
        "stage_contract": {
            "independent_implementation": True,
            "imports_production_scanner": False,
            "imports_production_tdx_decoder": False,
            "canonical_identity_mutation": False,
            "historical_universe_mutation": False,
            "tdx_root_write_count": 0,
        },
        "inputs": {
            path.as_posix(): file_identity(path)
            for path in (UNIVERSE, IDENTITY, GLOBAL_HEAD, ARCHIVE, DISCOVERY, R8_POSTCHECK, R83_POSTCHECK, SCAN, BLIND_RECEIPT, BLIND_LABELS, OFFICIAL_INDEX, OFFICIAL_COVERAGE, EXTERNAL_AUDIT, REPAIR_TASK, CALIBRATION_AUDIT)
        },
        "recomputed_scope": {
            "rows_scanned": independent["rows_scanned"],
            "source_key_count": independent["source_key_count"],
            "session_count": len(independent["session_dates"]),
            "first_session": independent["session_dates"][0] if independent["session_dates"] else None,
            "last_session": independent["session_dates"][-1] if independent["session_dates"] else None,
            "entry_count": len(independent["entries"]),
            "exit_count": len(independent["exits"]),
            "first_session_baseline_key_count": independent["first_session_baseline_key_count"],
            "duplicate_source_key_session_rows": independent["duplicate_source_key_session_rows"],
            "board_rows": independent["board_rows"],
        },
        "candidate_resolution_replay_count": len(candidate_resolutions),
        "candidate_tdx_decode_complete": candidate_tdx_decode_complete,
        "candidate_union_key_set": [list(key) for key in sorted(candidate_union)],
        "checks": checks,
        "resolution_receipt": {"path": OUTPUT_RESOLUTION.as_posix(), "sha256": resolution_sha},
        "summary": {
            "unlinked_boundary_anomalies": int(discovery.get("unlinked_boundary_anomaly_count", -1)),
            "required_scope_unresolved_identity_relations": unresolved,
            "official_event_index_exhaustiveness_claimed": False,
            "source_fingerprint_calibration": "DEFERRED_NON_BLOCKING_RESEARCH",
            "next_stage": "BUILD_FINAL_STAGE_CANDIDATE_WITH_EXTERNAL_ACCEPTANCE_PENDING" if postcheck_status == "PASS_INDEPENDENT_POSTCHECK" else "BLOCKED_REPAIR_FAILED_CHECKS",
        },
        "stage_record": {
            "evidence": "Independent gzip row scan, struct-only TDX decode, frozen BaoStock report replay, accepted R7 identity and official-event evidence",
            "acceptance_result": postcheck_status,
            "next_stage": "V4-01 FINAL CANDIDATE" if postcheck_status == "PASS_INDEPENDENT_POSTCHECK" else "REPAIR_CHECK_FAILURES",
        },
        "execution_identity": {
            "input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "script_sha256": file_sha(Path(__file__).resolve().relative_to(ROOT)),
            "python_version": sys.version.split()[0],
        },
    }
    postcheck_bytes = atomic_write(OUTPUT_POSTCHECK, postcheck)
    postcheck_sha = hashlib.sha256(postcheck_bytes).hexdigest()

    head_candidate = {
        "contract_id": "V4_01_ACCEPTED_HEAD_CANDIDATE_V1",
        "stage": "V4-01",
        "status": "FULL_PASS_CANDIDATE" if postcheck_status == "PASS_INDEPENDENT_POSTCHECK" else "BLOCKED",
        "external_acceptance": "PENDING_EXTERNAL_REVIEW",
        "candidate_only": True,
        "required_scope": {
            "status": "FULL_PASS_CANDIDATE" if postcheck_status == "PASS_INDEPENDENT_POSTCHECK" else "BLOCKED",
            "boards": sorted(REQUIRED_BOARDS),
            "history_start": scan["scope"]["first_session"],
            "history_end": scan["scope"]["last_session"],
            "sessions": scan["scope"]["session_count"],
            "unresolved_identity_relations": unresolved,
            "unlinked_boundary_anomalies": int(discovery.get("unlinked_boundary_anomaly_count", -1)),
        },
        "optional_scope": {"BSE": "DEGRADED_OPTIONAL_EXCLUDED_FROM_REQUIRED_GATE"},
        "canonical_identity": {
            "path": IDENTITY.as_posix(),
            "sha256": identity_hash,
            "changed": False,
        },
        "historical_universe": {
            "path": UNIVERSE.as_posix(),
            "sha256": universe_hash,
            "changed": False,
        },
        "evidence_bindings": {
            "completeness_gate_contract": file_identity(GATE),
            "full_scope_scan": {"path": SCAN.as_posix(), "sha256": file_sha(SCAN)},
            "relation_resolution": {"path": OUTPUT_RESOLUTION.as_posix(), "sha256": resolution_sha},
            "independent_postcheck": {"path": OUTPUT_POSTCHECK.as_posix(), "sha256": postcheck_sha},
            "known_official_event_index": file_identity(OFFICIAL_INDEX),
            "r8_3_boundary_inventory": file_identity(DISCOVERY),
            "r7_identity": file_identity(IDENTITY),
            "r7_required_universe": file_identity(UNIVERSE),
        },
        "constraints": {
            "source_fingerprint_auto_confirmation": False,
            "canonical_identity_mutation": False,
            "external_acceptance_granted": False,
            "global_accepted_head_updated": False,
            "v4_04_authorized": False,
        },
        "stage_record": {
            "evidence": "Full Required Scope R7 boundary inventory; R8.3 cross-check; TDX-first scan; official resolution; independent postcheck",
            "acceptance_result": "CANDIDATE_PENDING_EXTERNAL_ACCEPTANCE" if postcheck_status == "PASS_INDEPENDENT_POSTCHECK" else "BLOCKED",
            "next_stage": "INDEPENDENT_EXTERNAL_ACCEPTANCE",
        },
    }
    head_bytes = atomic_write(OUTPUT_HEAD_CANDIDATE, head_candidate)
    head_sha = hashlib.sha256(head_bytes).hexdigest()

    final_candidate = {
        "contract_id": "V4_01_FINAL_STAGE_CANDIDATE_R10",
        "version": "10.0.0-candidate",
        "stage": "V4-01 FINAL STAGE",
        "status": "FULL_PASS_CANDIDATE" if postcheck_status == "PASS_INDEPENDENT_POSTCHECK" and checks["resolution_complete"] else "BLOCKED",
        "external_acceptance": "PENDING_EXTERNAL_REVIEW",
        "gate_contract_external_acceptance": "ACCEPTED_BY_EXTERNAL_AUDIT_20260929",
        "gate_contract_acceptance_evidence": {
            "external_review_head": EXTERNAL_REVIEW_HEAD,
            "audit_document": file_identity(EXTERNAL_AUDIT),
            "repair_task_document": file_identity(REPAIR_TASK),
        },
        "observed_at": observed_at,
        "identity_candidate": {"path": OUTPUT_HEAD_CANDIDATE.as_posix(), "sha256": head_sha},
        "canonical_identity_unchanged": True,
        "required_scope": head_candidate["required_scope"],
        "known_event_index": {
            "status": "COVERAGE_INCOMPLETE_RETAINED_AS_HISTORICAL_FACT",
            "role": "KNOWN_EVENT_CROSS_CHECK_AND_CONFIRMATION_SOURCE",
            "exhaustiveness_claimed": False,
        },
        "source_fingerprint_calibration": "DEFERRED_NON_BLOCKING_RESEARCH",
        "evidence": {
            "scan": {"path": SCAN.as_posix(), "sha256": file_sha(SCAN)},
            "resolution": {"path": OUTPUT_RESOLUTION.as_posix(), "sha256": resolution_sha},
            "postcheck": {"path": OUTPUT_POSTCHECK.as_posix(), "sha256": postcheck_sha},
        },
        "next_stage": "WAIT_FOR_INDEPENDENT_EXTERNAL_ACCEPTANCE; DO_NOT_UPDATE_GLOBAL_HEAD_OR_START_V4_04",
        "stage_record": head_candidate["stage_record"],
    }
    final_bytes = atomic_write(OUTPUT_FINAL_CANDIDATE, final_candidate)

    print(json.dumps({
        "status": postcheck_status,
        "required_scope_candidate_count": len(candidate_union),
        "required_scope_resolution_count": len(candidate_resolutions),
        "required_scope_unresolved_count": unresolved,
        "resolution_coverage": resolution_coverage["status"],
        "checks_passed": sum(bool(value) for value in checks.values()),
        "checks_total": len(checks),
        "source_rows": independent["rows_scanned"],
        "sessions": len(independent["session_dates"]),
        "entry_boundaries": len(independent["entries"]),
        "exit_boundaries": len(independent["exits"]),
        "candidate_tdx_redecoded": candidate_tdx_decode_complete,
        "resolution_sha256": resolution_sha,
        "postcheck_sha256": postcheck_sha,
        "head_candidate_sha256": head_sha,
        "final_candidate_sha256": hashlib.sha256(final_bytes).hexdigest(),
        "canonical_identity_changed": False,
    }, ensure_ascii=False, indent=2))
    return 0 if postcheck_status == "PASS_INDEPENDENT_POSTCHECK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
