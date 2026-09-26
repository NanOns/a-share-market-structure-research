from __future__ import annotations

"""Independent structural and accepted-package index postcheck for V2 calendar."""

import hashlib
import json
import os
import struct
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PATH = ROOT / "config/v4_official_exchange_calendar_expected_closures_v2.json"
PACKAGE_SOURCE_MANIFEST = ROOT / "reports/v4_01/v4_01_source_manifest_R4_20260925.json"
V4_02_CONTRACT = ROOT / "config/v4_02_canonical_daily_pit_contract_v1.json"
INDEX_RECORD = struct.Struct("<IIIII f II")
OUTPUT_ID = "V4_02_MARKET_CALENDAR_20230704_20260924_V2"
INDEX_BINDINGS = {
    "SSE": ("sh/lday/sh000001.day", "calendar_sse_20230704_20260924.json"),
    "SZSE": ("sz/lday/sz399001.day", "calendar_szse_20230704_20260924.json"),
}


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


def read_index_dates(path: Path, start: date, end: date) -> tuple[set[int], str]:
    data = path.read_bytes()
    if len(data) % INDEX_RECORD.size:
        raise ValueError(f"INDEX_FILE_BAD_SIZE:{path}")
    dates: set[int] = set()
    for offset in range(0, len(data), INDEX_RECORD.size):
        value = INDEX_RECORD.unpack_from(data, offset)[0]
        if int(start.strftime("%Y%m%d")) <= value <= int(end.strftime("%Y%m%d")):
            dates.add(value)
    return dates, sha256(data)


def main() -> int:
    expected_bytes = EXPECTED_PATH.read_bytes()
    expected = json.loads(expected_bytes)
    package_manifest_bytes = PACKAGE_SOURCE_MANIFEST.read_bytes()
    package_manifest = json.loads(package_manifest_bytes)
    v4_02 = json.loads(V4_02_CONTRACT.read_text(encoding="utf-8"))
    package_sha = package_manifest["source"]["package_sha256"]
    if package_sha != v4_02["inputs"]["source_package_sha256"]:
        raise ValueError("INDEX_PACKAGE_NOT_BOUND_TO_V4_02_INPUT_CONTRACT")
    start = date.fromisoformat(expected["coverage"]["start_date"])
    end = date.fromisoformat(expected["coverage"]["end_date"])
    if expected["coverage"]["source_cutoff"] != end.isoformat():
        raise ValueError("CALENDAR_END_EXCEEDS_OR_DIFFERS_FROM_SOURCE_CUTOFF")
    package_root = ROOT / "data/input_staging/extracted/20260924" / package_sha
    candidate_root = ROOT / "data/v4/candidate_calendars" / OUTPUT_ID
    market_results = []
    for market, (index_rel, candidate_name) in INDEX_BINDINGS.items():
        calendar_bytes = (candidate_root / candidate_name).read_bytes()
        calendar = json.loads(calendar_bytes)
        sessions = [date.fromisoformat(item) for item in calendar["session_dates"]]
        if calendar["coverage"] != {"start_date": start.isoformat(), "end_date": end.isoformat(), "source_cutoff": end.isoformat()}:
            raise ValueError(f"COVERAGE_MISMATCH:{market}")
        if sessions != sorted(set(sessions)):
            raise ValueError(f"SESSION_ORDER_OR_DUPLICATE:{market}")
        if any(day < start or day > end or day.weekday() > 4 for day in sessions):
            raise ValueError(f"SESSION_OUTSIDE_WEEKDAY_COVERAGE:{market}")
        closed_dates = {date.fromisoformat(item) for item in calendar["closed_dates_from_official_notices"]}
        if any(day < start or day > end for day in closed_dates) or set(sessions) & closed_dates:
            raise ValueError(f"CLOSURE_SCOPE_OR_SESSION_CONFLICT:{market}")
        weekdays = set()
        cursor = start
        while cursor <= end:
            if cursor.weekday() < 5:
                weekdays.add(cursor)
            cursor += timedelta(days=1)
        weekday_closures = closed_dates & weekdays
        if set(sessions) | weekday_closures != weekdays or set(sessions) & weekday_closures:
            raise ValueError(f"WEEKDAY_PARTITION_INCOMPLETE:{market}")
        index_dates, index_sha = read_index_dates(package_root / index_rel, start, end)
        calendar_dates = {int(day.strftime("%Y%m%d")) for day in sessions}
        missing = sorted(calendar_dates - index_dates)
        unexpected = sorted(index_dates - calendar_dates)
        market_results.append({
            "market": market,
            "board_ids": calendar["board_ids"],
            "calendar_sha256": sha256(calendar_bytes),
            "session_count": len(sessions),
            "weekday_closure_count": len(weekday_closures),
            "official_closure_date_count": len(closed_dates),
            "index_file": index_rel,
            "index_file_sha256": index_sha,
            "index_session_count": len(index_dates),
            "calendar_sessions_missing_from_index": missing,
            "index_sessions_missing_from_calendar": unexpected,
            "structural_postcheck": "PASS",
            "index_crosscheck": "PASS" if not missing and not unexpected else "FAIL",
        })
    if set(item["board_ids"][0] for item in market_results) != {"SH_MAIN", "SZ_MAIN"}:
        raise ValueError("MARKET_BINDING_INVALID")
    if sorted(board for item in market_results for board in item["board_ids"]) != ["CHINEXT", "SH_MAIN", "STAR", "SZ_MAIN"]:
        raise ValueError("REQUIRED_BOARD_SCOPE_INCOMPLETE")
    passed = all(item["structural_postcheck"] == "PASS" and item["index_crosscheck"] == "PASS" for item in market_results)
    report = {
        "contract_id": "V4_OFFICIAL_EXCHANGE_CALENDAR_INDEPENDENT_POSTCHECK_V2",
        "status": "FORMAL_MARKET_CALENDAR_PASS" if passed else "FORMAL_MARKET_CALENDAR_BLOCKED_MISMATCH",
        "calendar_contract_sha256": sha256((ROOT / "config/v4_official_exchange_calendar_v2.json").read_bytes()),
        "expected_values_sha256": sha256(expected_bytes),
        "v4_01_source_manifest_sha256": sha256(package_manifest_bytes),
        "v4_02_input_package_sha256": package_sha,
        "coverage": {"start_date": start.isoformat(), "end_date": end.isoformat(), "source_cutoff": end.isoformat()},
        "index_crosscheck_basis": "Accepted V4-01 R4 complete-package primary index session series; crosscheck only, not source inference.",
        "markets": market_results,
        "audit_scope_disposition": "No one-off amendment expansion triggered because unexplained index mismatch count is zero." if passed else "Investigate only the dated mismatches; do not infer sessions from stock-bar presence.",
        "pit_observed": False,
        "overall_v4_02_stage": "BLOCKED_OPEN_OTHER_REQUIRED_CAPABILITIES" if passed else "BLOCKED_CALENDAR_MISMATCH",
        "next_stage": "ADJUSTED_CANONICAL_DAILY_REAL_ACTION_ACCEPTANCE",
    }
    report_path = ROOT / "reports/v4_02/V4_OFFICIAL_CALENDAR_V2_INDEPENDENT_POSTCHECK_20260926.json"
    atomic_write(report_path, (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": report["status"], "report": report_path.relative_to(ROOT).as_posix(), "markets": market_results}, ensure_ascii=False))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
