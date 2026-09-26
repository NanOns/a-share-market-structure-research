from __future__ import annotations

"""Independent structural and accepted-package index crosscheck for calendar candidates."""

import hashlib
import json
import os
import struct
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PATH = ROOT / "config/v4_official_exchange_calendar_expected_closures_v1.json"
PACKAGE_SOURCE_MANIFEST = ROOT / "reports/v4_01/v4_01_source_manifest_R4_20260925.json"
V4_02_CONTRACT = ROOT / "config/v4_02_canonical_daily_pit_contract_v1.json"
INDEX_RECORD = struct.Struct("<IIIII f II")
INDEX_BINDINGS = {
    "SSE": ("sh/lday/sh000001.day", "calendar_sse_2024_2026.json"),
    "SZSE": ("sz/lday/sz399001.day", "calendar_szse_2024_2026.json"),
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


def record_dates(path: Path) -> tuple[set[int], str]:
    data = path.read_bytes()
    if len(data) % INDEX_RECORD.size:
        raise ValueError(f"INDEX_FILE_BAD_SIZE:{path}")
    dates: set[int] = set()
    for offset in range(0, len(data), INDEX_RECORD.size):
        value = INDEX_RECORD.unpack_from(data, offset)[0]
        if 20240101 <= value <= 20260924:
            dates.add(value)
    return dates, sha256(data)


def main() -> int:
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    source_manifest = json.loads(PACKAGE_SOURCE_MANIFEST.read_text(encoding="utf-8"))
    v4_02 = json.loads(V4_02_CONTRACT.read_text(encoding="utf-8"))
    package_sha = source_manifest["source"]["package_sha256"]
    expected_package_sha = v4_02["inputs"]["source_package_sha256"]
    if package_sha != expected_package_sha:
        raise ValueError("INDEX_PACKAGE_NOT_BOUND_TO_V4_02_INPUT_CONTRACT")
    package_root = ROOT / "data/input_staging/extracted/20260924" / package_sha
    candidate_root = ROOT / "data/v4/candidate_calendars" / expected["source_capture_id"]
    start = date.fromisoformat(expected["coverage"]["start_date"])
    end = date.fromisoformat(expected["coverage"]["end_date"])
    receipt_markets = []
    check_summary = []
    for market, (index_rel, candidate_name) in INDEX_BINDINGS.items():
        payload_bytes = (candidate_root / candidate_name).read_bytes()
        payload = json.loads(payload_bytes)
        sessions = [date.fromisoformat(v) for v in payload["session_dates"]]
        if sessions != sorted(set(sessions)):
            raise ValueError(f"SESSION_ORDER_OR_DUPLICATE:{market}")
        if any(d < start or d > end or d.weekday() > 4 for d in sessions):
            raise ValueError(f"SESSION_OUTSIDE_WEEKDAY_COVERAGE:{market}")
        closed_dates = {date.fromisoformat(v) for v in payload["closed_dates_from_official_notices"]}
        if set(sessions) & closed_dates:
            raise ValueError(f"SESSION_CLOSED_CONFLICT:{market}")
        weekdays = set()
        cursor = start
        while cursor <= end:
            if cursor.weekday() < 5:
                weekdays.add(cursor)
            cursor += timedelta(days=1)
        weekday_closures = closed_dates & weekdays
        if set(sessions) | weekday_closures != weekdays or set(sessions) & weekday_closures:
            raise ValueError(f"WEEKDAY_PARTITION_INCOMPLETE:{market}")

        index_dates, index_sha = record_dates(package_root / index_rel)
        candidate_asof = {int(d.strftime("%Y%m%d")) for d in sessions if d <= date(2026, 9, 24)}
        missing = sorted(candidate_asof - index_dates)
        unexpected = sorted(index_dates - candidate_asof)
        check_summary.append({
            "market": market,
            "calendar_sha256": sha256(payload_bytes),
            "session_count_full_coverage": len(sessions),
            "weekday_closure_count": len(weekday_closures),
            "closure_calendar_day_count": len(closed_dates),
            "index_file": index_rel,
            "index_file_sha256": index_sha,
            "index_dates_through_20260924": len(index_dates),
            "candidate_sessions_through_20260924": len(candidate_asof),
            "candidate_sessions_missing_from_index": missing,
            "index_dates_not_in_candidate": unexpected,
            "candidate_invariants_pass": True,
            "index_date_match": not missing and not unexpected,
        })

    report = {
        "contract_id": "V4_OFFICIAL_EXCHANGE_CALENDAR_CANDIDATE_DIAGNOSTIC_POSTCHECK_V1",
        "status": "CANDIDATE_DIAGNOSTIC_CROSSCHECK_PASS_ACCEPTANCE_PENDING",
        "source_capture_id": expected["source_capture_id"],
        "expected_values_sha256": sha256(EXPECTED_PATH.read_bytes()),
        "v4_01_source_manifest_sha256": sha256(PACKAGE_SOURCE_MANIFEST.read_bytes()),
        "index_package_sha256": package_sha,
        "index_crosscheck_basis": "Accepted V4-01 R4 TDX complete-package primary-index series; diagnostic crosscheck only, not standalone exchange-calendar acceptance.",
        "coverage": {"start_date": start.isoformat(), "end_date": end.isoformat()},
        "markets": check_summary,
        "acceptance": "NOT_ACCEPTED",
        "remaining": [
            "independent manual review of every closure range",
            "review all applicable one-off exchange amendments through cutoff",
            "as-of and future-notice exclusion checks",
            "independent postcheck and formal dataset acceptance",
        ],
    }
    report_path = ROOT / "reports/v4_02/V4_OFFICIAL_CALENDAR_CANDIDATE_POSTCHECK_20260926.json"
    atomic_write(report_path, (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": report["status"], "report": report_path.relative_to(ROOT).as_posix(), "markets": check_summary}, ensure_ascii=False))
    if any(not item["candidate_invariants_pass"] or not item["index_date_match"] for item in check_summary):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
