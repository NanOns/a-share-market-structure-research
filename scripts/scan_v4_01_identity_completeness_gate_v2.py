from __future__ import annotations

"""Read-only full Required Scope source-key boundary and TDX-first scan."""

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tdx.day_reader import DAY_RECORD_LENGTH, decode_record  # noqa: E402

CONTRACT_PATH = Path("config/v4_01_identity_completeness_gate_v2.json")
FINGERPRINT_CONTRACT_PATH = Path("config/v4_01_source_fingerprint_candidate_v1.json")
UNIVERSE_PATH = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz")
IDENTITY_PATH = Path("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
DISCOVERY_PATH = Path("reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_3.json")
R8_POSTCHECK_PATH = Path("reports/v4_01/V4_01_R8_IDENTITY_UNIVERSE_POSTCHECK_20260928.json")
R83_POSTCHECK_PATH = Path("reports/v4_01/V4_01_R8_3_INDEPENDENT_POSTCHECK.json")
R83_RECEIPT_PATH = Path("reports/v4_01/v4_01_final_stage_receipt_R8_3_20260928.json")
GLOBAL_HEAD_PATH = Path("data/v4/V4_STAGE_ACCEPTED_HEAD.json")
TDX_ARCHIVE_PATH = Path("data/v4/raw_archive/b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f/hsjday.zip")
OUTPUT_PATH = Path("reports/v4_01/V4_01_FULL_SCOPE_SOURCE_FINGERPRINT_SCAN_R1.json")
REQUIRED_BOARDS = {"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"}
SEMANTIC_FIELDS = ("open", "high", "low", "close", "amount", "volume")
STRICT_FIELDS = ("open", "high", "low", "close", "amount")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rel_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def input_identity(path: Path) -> dict[str, Any]:
    absolute = ROOT / path
    return {"path": path.as_posix(), "sha256": sha256_file(absolute), "byte_count": absolute.stat().st_size}


def tdx_file_path(tdx_root: Path, code: str) -> Path:
    market, digits = code.upper().split(".", 1)
    return tdx_root / "vipdoc" / market.lower() / "lday" / f"{market.lower()}{digits}.day"


def safe_artifact_write(path: Path, payload: bytes, tdx_root: Path) -> None:
    destination = path.resolve()
    source_root = tdx_root.resolve()
    if destination == source_root or source_root in destination.parents:
        raise ValueError("PROJECT_ARTIFACT_MUST_BE_OUTSIDE_TDX_ROOT")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def archive_member(code: str) -> str:
    market, digits = code.upper().split(".", 1)
    return f"{market.lower()}/lday/{market.lower()}{digits}.day"


def source_snapshot(archive: zipfile.ZipFile, code: str, archive_sha256: str) -> dict[str, Any]:
    member = archive_member(code)
    try:
        info = archive.getinfo(member)
    except KeyError:
        return {
            "code": code,
            "exists": False,
            "source_archive": TDX_ARCHIVE_PATH.as_posix(),
            "archive_sha256": archive_sha256,
            "member": member,
            "byte_count": None,
            "first_record_sha256": None,
        }
    with archive.open(info, "r") as stream:
        first = stream.read(DAY_RECORD_LENGTH)
    return {
        "code": code,
        "exists": True,
        "source_archive": TDX_ARCHIVE_PATH.as_posix(),
        "archive_sha256": archive_sha256,
        "member": member,
        "byte_count": info.file_size,
        "crc32": f"{info.CRC:08x}",
        "first_record_sha256": hashlib.sha256(first).hexdigest() if len(first) == DAY_RECORD_LENGTH else None,
        "first_date": (
            datetime.strptime(str(decode_record(first).trade_date), "%Y%m%d").date().isoformat()
            if len(first) == DAY_RECORD_LENGTH else None
        ),
    }


def decode_tdx(raw: bytes, code: str) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    tail = len(raw) % DAY_RECORD_LENGTH
    records: dict[str, dict[str, Any]] = {}
    duplicates = 0
    non_increasing = 0
    previous = None
    for offset in range(0, len(raw) - tail, DAY_RECORD_LENGTH):
        item = decode_record(raw[offset:offset + DAY_RECORD_LENGTH])
        day = datetime.strptime(str(item.trade_date), "%Y%m%d").date().isoformat()
        if day in records:
            duplicates += 1
        if previous is not None and item.trade_date <= previous:
            non_increasing += 1
        previous = item.trade_date
        records[day] = {field: getattr(item, field) for field in SEMANTIC_FIELDS}
    return records, {
        "code": code,
        "exists": True,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw),
        "record_count": len(records),
        "trailing_bytes": tail,
        "duplicate_date_count": duplicates,
        "non_increasing_date_count": non_increasing,
        "first_date": next(iter(records), None),
        "last_date": next(reversed(records), None),
    }


def semantic_overlap(
    archive: zipfile.ZipFile,
    old_code: str,
    new_code: str,
    effective_date: str,
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    try:
        old_info = archive.getinfo(archive_member(old_code))
        new_info = archive.getinfo(archive_member(new_code))
    except KeyError:
        return {
            "classification": "TDX_UNRESOLVED",
            "old_exists": archive_member(old_code) in archive.namelist(),
            "new_exists": archive_member(new_code) in archive.namelist(),
        }
    with archive.open(old_info, "r") as stream:
        old_raw = stream.read()
    with archive.open(new_info, "r") as stream:
        new_raw = stream.read()
    old, old_meta = decode_tdx(old_raw, old_code)
    new, new_meta = decode_tdx(new_raw, new_code)
    common = sorted(day for day in old.keys() & new.keys() if day < effective_date)
    strict_matches = 0
    volume_matches = 0
    strict_mismatches: dict[str, int] = Counter()
    for day in common:
        left, right = old[day], new[day]
        strict_matches += int(all(left[field] == right[field] for field in STRICT_FIELDS))
        volume_matches += int(left["volume"] == right["volume"])
        for field in STRICT_FIELDS:
            if left[field] != right[field]:
                strict_mismatches[field] += 1
    ratio = volume_matches / len(common) if common else None
    min_shared = int(thresholds.get("minimum_shared_sessions", 20))
    min_volume = float(thresholds.get("tdx_volume_exact_ratio_minimum", 0.95))
    structural_ok = all(
        not meta["trailing_bytes"] and not meta["duplicate_date_count"] and not meta["non_increasing_date_count"]
        for meta in (old_meta, new_meta)
    )
    strong = structural_ok and len(common) >= min_shared and strict_matches == len(common) and ratio is not None and ratio >= min_volume
    classification = "TDX_STRONG_SEMANTIC_ALIAS_CANDIDATE" if strong else (
        "TDX_NO_ALIAS_SIGNAL" if structural_ok else "TDX_UNRESOLVED"
    )
    return {
        "classification": classification,
        "old": old_meta,
        "new": new_meta,
        "shared_pre_effective_sessions": len(common),
        "ohlc_amount_exact_count": strict_matches,
        "ohlc_amount_mismatch_counts": dict(sorted(strict_mismatches.items())),
        "volume_exact_count": volume_matches,
        "volume_exact_ratio": ratio,
        "minimum_shared_sessions": min_shared,
        "minimum_volume_exact_ratio": min_volume,
        "reserved_compared": False,
        "raw_record_prefix_required": False,
        "amount_tolerance": "NONE",
    }


def scan_source_boundaries(universe_path: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    exits: list[dict[str, Any]] = []
    session_dates: list[str] = []
    board_rows: Counter[str] = Counter()
    source_key_count: set[str] = set()
    duplicate_source_rows = 0
    rows_scanned = 0
    day_key = None
    day_rows: dict[str, dict[str, Any]] = {}
    previous_day = None
    previous_keys: set[str] = set()
    first_session_baseline_key_count = None

    def finish_session(current_day: str, current_rows: dict[str, dict[str, Any]]) -> set[str]:
        nonlocal duplicate_source_rows, first_session_baseline_key_count
        current_keys = set(current_rows)
        if previous_day is not None:
            for code in sorted(current_keys - previous_keys):
                entries.append({"source_security_key": code, "entry_date": current_day, **current_rows[code]})
            for code in sorted(previous_keys - current_keys):
                exits.append({"source_security_key": code, "last_present_session": previous_day, "first_absent_session": current_day})
        else:
            first_session_baseline_key_count = len(current_keys)
        return current_keys

    with gzip.open(ROOT / universe_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            rows_scanned += 1
            day = str(row.get("trade_date") or "")
            code = str(row.get("source_security_key") or "").upper()
            board = str(row.get("board_scope") or "")
            if board not in REQUIRED_BOARDS or not code or not day:
                raise ValueError("REQUIRED_UNIVERSE_ROW_INVALID")
            date.fromisoformat(day)
            if day_key is None:
                day_key = day
            if day != day_key:
                if day < day_key:
                    raise ValueError("REQUIRED_UNIVERSE_NOT_SORTED_BY_SESSION")
                previous_keys = finish_session(day_key, day_rows)
                session_dates.append(day_key)
                previous_day = day_key
                day_key = day
                day_rows = {}
            if code in day_rows:
                duplicate_source_rows += 1
                if day_rows[code]["security_id"] != str(row.get("security_id") or ""):
                    raise ValueError("SOURCE_KEY_HAS_MULTIPLE_IDENTITIES_ON_SESSION")
            else:
                day_rows[code] = {
                    "security_id": str(row.get("security_id") or ""),
                    "board_scope": board,
                }
            source_key_count.add(code)
            board_rows[board] += 1
    if day_key is not None:
        previous_keys = finish_session(day_key, day_rows)
        session_dates.append(day_key)
    return {
        "session_dates": session_dates,
        "entries": entries,
        "exits": exits,
        "rows_scanned": rows_scanned,
        "source_key_count": len(source_key_count),
        "duplicate_source_key_session_rows": duplicate_source_rows,
        "board_rows": dict(sorted(board_rows.items())),
        "first_session_baseline_key_count": first_session_baseline_key_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tdx-root", type=Path, default=Path("D:/new_tdx"), help="recorded read-only root; accepted archive is authoritative")
    parser.add_argument("--output", type=Path, default=ROOT / OUTPUT_PATH)
    args = parser.parse_args()
    tdx_root = args.tdx_root.resolve()
    if not tdx_root.is_dir():
        raise SystemExit("TDX_ROOT_NOT_FOUND")

    contract = json.loads((ROOT / CONTRACT_PATH).read_text(encoding="utf-8"))
    fingerprint_contract = json.loads((ROOT / FINGERPRINT_CONTRACT_PATH).read_text(encoding="utf-8"))
    discovery = json.loads((ROOT / DISCOVERY_PATH).read_text(encoding="utf-8"))
    r8_postcheck = json.loads((ROOT / R8_POSTCHECK_PATH).read_text(encoding="utf-8"))
    r83_postcheck = json.loads((ROOT / R83_POSTCHECK_PATH).read_text(encoding="utf-8"))
    r83_receipt = json.loads((ROOT / R83_RECEIPT_PATH).read_text(encoding="utf-8"))
    global_head = json.loads((ROOT / GLOBAL_HEAD_PATH).read_text(encoding="utf-8"))
    archive_path = ROOT / TDX_ARCHIVE_PATH
    archive_hash = sha256_file(archive_path)
    accepted_archive_hash = str(global_head.get("bindings", {}).get("tdx_archive", {}).get("sha256") or "").lower()
    if not accepted_archive_hash or archive_hash != accepted_archive_hash:
        raise SystemExit("ACCEPTED_TDX_ARCHIVE_HASH_MISMATCH")
    universe = scan_source_boundaries(UNIVERSE_PATH)
    sessions = universe["session_dates"]
    previous_for = {sessions[index]: sessions[index - 1] for index in range(1, len(sessions))}

    r7_rows_expected = int(r8_postcheck.get("scope", {}).get("expected_rows_after_alias_dedup", -1))
    source_input_ok = (
        universe["rows_scanned"] == r7_rows_expected
        and universe["duplicate_source_key_session_rows"] == 0
        and len(sessions) == int(discovery.get("scope", {}).get("formal_history_window", {}).get("session_count", -1))
        and set(universe["board_rows"]) == REQUIRED_BOARDS
        and r8_postcheck.get("status") == "PASS"
        and r83_postcheck.get("status") == "PASS"
    )

    exits_by_market_date: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for item in universe["exits"]:
        market = item["source_security_key"].split(".", 1)[0]
        exits_by_market_date[(market, item["last_present_session"])][item["source_security_key"]].add("R7_SOURCE_KEY_TRANSITION")
    for item in discovery.get("boundary_events", []):
        if item.get("event_type") not in {"SECURITY_EXIT", "LISTING_END"}:
            continue
        code = str(item.get("source_security_key") or "").upper()
        if "." not in code:
            continue
        exit_day = (
            item.get("details", {}).get("last_present_session")
            if item.get("event_type") == "SECURITY_EXIT"
            else item.get("effective_date")
        )
        if exit_day:
            exits_by_market_date[(code.split(".", 1)[0], str(exit_day))][code].add(
                f"R8_3_{item['event_type']}:{item.get('event_id')}"
            )

    entry_checks = []
    anomalies = []
    missing_or_invalid_entry_file_count = 0
    with zipfile.ZipFile(archive_path) as archive:
        for entry in universe["entries"]:
            code = entry["source_security_key"]
            entry_day = entry["entry_date"]
            snapshot = source_snapshot(archive, code, archive_hash)
            if not snapshot["exists"] or not snapshot.get("first_date"):
                missing_or_invalid_entry_file_count += 1
                entry_checks.append({**entry, "tdx_file": snapshot, "status": "MISSING_OR_INVALID_TDX_ENTRY_FILE"})
                continue
            entry_check = {**entry, "tdx_file": snapshot, "status": "NO_PRE_EFFECTIVE_HISTORY_ANOMALY"}
            if snapshot["first_date"] < entry_day:
                anomaly = {
                    "anomaly_id": hashlib.sha256(f"{code}|{entry_day}".encode("ascii")).hexdigest()[:24],
                    "anomaly_type": "NEW_CODE_PRE_EFFECTIVE_HISTORY_ANOMALY",
                    "new_source_security_key": code,
                    "entry_date": entry_day,
                    "previous_market_session": previous_for.get(entry_day),
                    "board_scope": entry["board_scope"],
                    "security_id": entry["security_id"],
                    "tdx_first_date": snapshot["first_date"],
                    "tdx_first_record_sha256": snapshot["first_record_sha256"],
                    "adjacent_old_exit_candidates": [],
                }
                entry_check["status"] = "PRE_EFFECTIVE_HISTORY_ANOMALY"
                anomaly_exits: dict[str, set[str]] = defaultdict(set)
                market = code.split(".", 1)[0]
                for exit_day in {entry_day, previous_for.get(entry_day)} - {None}:
                    for old_code, origins in exits_by_market_date.get((market, exit_day), {}).items():
                        if old_code != code:
                            anomaly_exits[old_code].update(origins)
                for old_code in sorted(anomaly_exits):
                    overlap = semantic_overlap(
                        archive, old_code, code, entry_day, fingerprint_contract["research_thresholds"]
                    )
                    pair = {
                        "old_source_security_key": old_code,
                        "new_source_security_key": code,
                        "effective_date": entry_day,
                        "exit_evidence": sorted(anomaly_exits[old_code]),
                        "tdx_semantic_comparison": overlap,
                    }
                    anomaly["adjacent_old_exit_candidates"].append(pair)
                if not anomaly["adjacent_old_exit_candidates"]:
                    anomaly["disposition"] = "UNLINKED_PRE_EFFECTIVE_HISTORY_ANOMALY"
                elif any(
                    pair["tdx_semantic_comparison"].get("classification") == "TDX_STRONG_SEMANTIC_ALIAS_CANDIDATE"
                    for pair in anomaly["adjacent_old_exit_candidates"]
                ):
                    anomaly["disposition"] = "TDX_STRONG_SEMANTIC_ALIAS_CANDIDATE"
                else:
                    anomaly["disposition"] = "TDX_NO_ALIAS_SIGNAL_OR_UNRESOLVED"
                anomalies.append(anomaly)
            entry_checks.append(entry_check)

    # The hash-bound accepted source archive is immutable input; verify it again after scanning.
    tdx_unchanged = sha256_file(archive_path) == archive_hash
    candidates = []
    seen_pairs = set()
    for anomaly in anomalies:
        for pair in anomaly["adjacent_old_exit_candidates"]:
            key = (pair["old_source_security_key"], pair["new_source_security_key"], pair["effective_date"])
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            candidates.append({
                "candidate_id": hashlib.sha256("|".join(key).encode("ascii")).hexdigest()[:24],
                **pair,
            })

    unresolved_scan_anomalies = sum(
        anomaly["disposition"] != "TDX_STRONG_SEMANTIC_ALIAS_CANDIDATE" for anomaly in anomalies
    )
    scan_ready = source_input_ok and tdx_unchanged and not missing_or_invalid_entry_file_count and not unresolved_scan_anomalies
    observed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    report = {
        "contract_id": contract["contract_id"],
        "contract_version": contract["version"],
        "stage": "V4-01 FULL REQUIRED-SCOPE SOURCE-FINGERPRINT SCAN",
        "status": "PASS_TDX_FIRST_SCAN" if scan_ready else "BLOCKED",
        "observed_at": observed_at,
        "stage_contract": {
            "candidate_contract_sha256": sha256_file(ROOT / CONTRACT_PATH),
            "frozen_source_fingerprint_contract_sha256": sha256_file(ROOT / FINGERPRINT_CONTRACT_PATH),
            "source_fingerprint_thresholds_changed": False,
            "canonical_identity_mutation": False,
            "historical_universe_mutation": False,
            "tdx_root_write_count": 0,
            "scanner_or_trading_run_count": 0,
            "official_event_index_exhaustiveness_claimed": False,
        },
        "inputs": {
            path.as_posix(): input_identity(path)
            for path in (
                CONTRACT_PATH, FINGERPRINT_CONTRACT_PATH, UNIVERSE_PATH, IDENTITY_PATH,
                DISCOVERY_PATH, R8_POSTCHECK_PATH, R83_POSTCHECK_PATH, R83_RECEIPT_PATH,
                GLOBAL_HEAD_PATH, TDX_ARCHIVE_PATH,
            )
        },
        "scope": {
            "required_boards": sorted(REQUIRED_BOARDS),
            "optional_bse": "DEGRADED_OPTIONAL_EXCLUDED_FROM_REQUIRED_SCOPE",
            "first_session": sessions[0] if sessions else None,
            "last_session": sessions[-1] if sessions else None,
            "session_count": len(sessions),
            "accepted_r7_rows_scanned": universe["rows_scanned"],
            "r7_postcheck_expected_rows_after_alias_dedup": r7_rows_expected,
            "r8_3_pre_dedup_membership_rows_scanned": int(discovery.get("scope", {}).get("required_universe_rows_scanned", 0)),
            "r8_3_alias_dedup_removed_rows": int(r8_postcheck.get("scope", {}).get("duplicate_rows_removed", 0)),
            "source_key_count": universe["source_key_count"],
            "first_session_baseline_source_key_count": universe["first_session_baseline_key_count"],
            "source_key_entry_boundaries": len(universe["entries"]),
            "source_key_exit_boundaries": len(universe["exits"]),
            "r8_3_atomic_boundary_event_count": int(discovery.get("boundary_event_count", 0)),
            "r8_3_unlinked_boundary_anomaly_count": int(discovery.get("unlinked_boundary_anomaly_count", -1)),
            "r8_3_unresolved_required_scope_candidate_count": int(discovery.get("unresolved_required_scope_candidate_count", -1)),
            "source_key_duplicate_session_rows": universe["duplicate_source_key_session_rows"],
            "board_rows": universe["board_rows"],
            "entry_boundary_tdx_file_count": len(universe["entries"]),
            "entry_tdx_files_missing_or_invalid": missing_or_invalid_entry_file_count,
            "tdx_entry_source_unchanged_during_scan": tdx_unchanged,
            "tdx_source_archive": {
                "path": TDX_ARCHIVE_PATH.as_posix(),
                "sha256": archive_hash,
                "accepted_global_head_binding_matches": archive_hash == accepted_archive_hash,
                "authoritative_for_this_scan": True,
            },
            "configured_tdx_root": {
                "path": str(tdx_root),
                "access": "READ_ONLY_OBSERVED_NOT_USED_AS_AUTHORITATIVE_DATA_SOURCE",
                "writes_attempted": 0,
            },
        },
        "atomic_boundaries": {
            "source_entries": universe["entries"],
            "source_exits": universe["exits"],
            "entry_tdx_checks": entry_checks,
        },
        "source_fingerprint_anomalies": anomalies,
        "relation_candidates": candidates,
        "summary": {
            "source_fingerprint_triggered_entry_count": len(anomalies),
            "candidate_relation_count": len(candidates),
            "unlinked_or_non_strong_anomaly_count": unresolved_scan_anomalies,
            "source_inputs_complete": source_input_ok,
            "next_stage": "RESOLVE_TDX_FIRST_RELATION_CANDIDATES_WITH_FROZEN_BAOSTOCK_AND_INDEPENDENT_EVIDENCE" if scan_ready else "BLOCKED_REPAIR_SCAN_INPUT_OR_BOUNDARY_ANOMALY",
        },
        "execution_identity": {
            "input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "script_sha256": sha256_file(Path(__file__)),
            "python_version": sys.version.split()[0],
            "tdx_root": str(tdx_root),
            "tdx_root_write_count": 0,
        },
    }
    output = args.output.resolve()
    if output == tdx_root or tdx_root in output.parents:
        raise SystemExit("PROJECT_ARTIFACT_MUST_BE_OUTSIDE_TDX_ROOT")
    data = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    safe_artifact_write(output, data, tdx_root)
    print(json.dumps({
        "status": report["status"],
        "source_entries": len(universe["entries"]),
        "source_exits": len(universe["exits"]),
        "triggered_entries": len(anomalies),
        "relation_candidates": len(candidates),
        "unresolved_scan_anomalies": unresolved_scan_anomalies,
        "r7_rows_scanned": universe["rows_scanned"],
        "output": str(output),
        "output_sha256": hashlib.sha256(data).hexdigest(),
    }, ensure_ascii=False, indent=2))
    return 0 if scan_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
