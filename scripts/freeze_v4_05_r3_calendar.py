"""Freeze the previously captured official SSE/SZSE schedule for Sep-28 replay."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/v4/candidate_calendars/capture_20260926T064500Z"
CAPTURE = ROOT / "data/v4/source_evidence/official_calendar_v1/capture_20260926T064500Z/source_capture_manifest.json"
OUT = ROOT / "reports/v4_05/V4_05_R3_CALENDAR_RECEIPT.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    capture = json.loads(CAPTURE.read_text(encoding="utf-8"))
    build = json.loads((SOURCE / "build_receipt.json").read_text(encoding="utf-8"))
    if capture["observed_at_utc"] >= "2026-09-28T00:00:00Z" or build["source_capture_manifest_sha256"] != sha(CAPTURE):
        raise ValueError("calendar source availability or identity mismatch")
    calendar = {}
    bindings = {}
    for market, filename in (("SSE", "calendar_sse_2024_2026.json"), ("SZSE", "calendar_szse_2024_2026.json")):
        path = SOURCE / filename
        rows = json.loads(path.read_text(encoding="utf-8"))["session_dates"]
        reference = next(x for x in build["markets"] if x["market"] == market)
        if sha(path) != reference["calendar_sha256"] or sorted(rows) != rows or len(rows) != len(set(rows)):
            raise ValueError(f"calendar integrity mismatch: {market}")
        if rows.count("2026-09-28") != 1 or any(day in rows for day in ("2026-09-25", "2026-10-01")):
            raise ValueError(f"target/closure calendar mismatch: {market}")
        calendar[market] = rows
        bindings[market] = {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)}
    if [day for day in calendar["SSE"] if "2026-09-28" <= day <= "2026-09-30"] != ["2026-09-28", "2026-09-29", "2026-09-30"]:
        raise ValueError("Sep-28 week/month completion basis mismatch")
    receipt = {"contract_id": "V4_05_R3_GO_FORWARD_OFFICIAL_CALENDAR_INPUT_V1", "status": "PASS_GO_FORWARD_SOURCE_FROZEN", "target_date": "2026-09-28", "source_authority": "SSE and SZSE official trading rules and closure notices", "source_urls": [x["source_url"] for x in capture["sources"]], "observed_at": capture["observed_at_utc"], "publication_available_before_target": True, "schedule_effective_range": ["2024-01-01", "2026-12-31"], "source_capture_sha256": sha(CAPTURE), "calendar_bindings": bindings, "target_week_remaining_sessions": ["2026-09-29", "2026-09-30"], "target_month_remaining_sessions": ["2026-09-29", "2026-09-30"], "source_status": build["status"], "note": "R3 stage-frozen calendar input for target classification; prior candidate was not a Sep-28 Accepted Head"}
    temp = OUT.with_suffix(".tmp")
    temp.write_bytes((json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    os.replace(temp, OUT)
    print(receipt["status"])


if __name__ == "__main__":
    main()
