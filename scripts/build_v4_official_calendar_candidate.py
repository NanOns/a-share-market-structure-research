from __future__ import annotations

"""Build bounded exchange-session calendar candidates from hash-bound notices."""

import hashlib
import json
import os
import re
import tempfile
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PATH = ROOT / "config/v4_official_exchange_calendar_expected_closures_v1.json"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def main() -> int:
    expected_bytes = EXPECTED_PATH.read_bytes()
    expected = json.loads(expected_bytes)
    capture_manifest_path = ROOT / expected["source_capture_manifest"]
    capture_manifest_bytes = capture_manifest_path.read_bytes()
    if sha256(capture_manifest_bytes) != expected["source_capture_manifest_sha256"]:
        raise ValueError("SOURCE_CAPTURE_MANIFEST_HASH_MISMATCH")
    capture = json.loads(capture_manifest_bytes)
    if capture["capture_id"] != expected["source_capture_id"]:
        raise ValueError("SOURCE_CAPTURE_ID_MISMATCH")
    capture_root = capture_manifest_path.parent
    capture_by_id = {item["source_id"]: item for item in capture["sources"]}
    output_root = ROOT / "data/v4/candidate_calendars" / expected["source_capture_id"]
    if output_root.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")

    start = date.fromisoformat(expected["coverage"]["start_date"])
    end = date.fromisoformat(expected["coverage"]["end_date"])
    weekdays = set(expected["coverage"]["weekdays"])
    summary = []
    for market, market_info in expected["markets"].items():
        market_closures: set[date] = set()
        source_records = []
        for year_text, year_info in market_info["years"].items():
            source = capture_by_id.get(year_info["source_id"])
            if source is None:
                raise ValueError(f"SOURCE_NOT_IN_CAPTURE:{market}:{year_text}")
            source_bytes = (capture_root / source["relative_path"]).read_bytes()
            if len(source_bytes) != source["byte_count"] or sha256(source_bytes) != source["sha256"]:
                raise ValueError(f"SOURCE_PAGE_HASH_MISMATCH:{source['source_id']}")
            parser = TextExtractor()
            parser.feed(source_bytes.decode("utf-8", errors="strict"))
            normalized = re.sub(r"\s+", "", "".join(parser.parts))
            for interval in year_info["ranges"]:
                phrase = re.sub(r"\s+", "", interval["evidence_phrase"])
                if phrase not in normalized:
                    raise ValueError(f"SOURCE_EVIDENCE_PHRASE_MISSING:{source['source_id']}:{interval['start']}")
                range_start = date.fromisoformat(interval["start"])
                range_end = date.fromisoformat(interval["end"])
                if range_end < range_start:
                    raise ValueError("INVALID_CLOSURE_RANGE")
                cursor = range_start
                while cursor <= range_end:
                    if start <= cursor <= end:
                        market_closures.add(cursor)
                    cursor += timedelta(days=1)
            source_records.append({"source_id": source["source_id"], "sha256": source["sha256"]})

        sessions = []
        cursor = start
        while cursor <= end:
            if cursor.weekday() in weekdays and cursor not in market_closures:
                sessions.append(cursor.isoformat())
            cursor += timedelta(days=1)
        payload = {
            "contract_id": "V4_OFFICIAL_EXCHANGE_SESSION_CALENDAR_CANDIDATE_V1",
            "capability": "CANDIDATE_ONLY_NOT_FORMAL_ACCEPTED",
            "market": market,
            "board_ids": market_info["board_ids"],
            "coverage": {"start_date": start.isoformat(), "end_date": end.isoformat()},
            "base_weekdays": sorted(weekdays),
            "closed_dates_from_official_notices": sorted(d.isoformat() for d in market_closures),
            "session_dates": sessions,
            "session_count": len(sessions),
            "input_contract_sha256": sha256((ROOT / "config/v4_official_exchange_calendar_v1.json").read_bytes()),
            "expected_values_sha256": sha256(expected_bytes),
            "source_capture_manifest_sha256": sha256(capture_manifest_bytes),
            "source_notices": source_records,
            "lineage": "RECONSTRUCTED_FROM_HASH_BOUND_OFFICIAL_NOTICES; NOT_PIT_OBSERVED",
            "acceptance": "PENDING_INDEPENDENT_MANUAL_REVIEW_CROSSCHECK_AND_POSTCHECK",
        }
        data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        relative = f"calendar_{market.lower()}_2024_2026.json"
        atomic_write(output_root / relative, data)
        summary.append({"market": market, "session_count": len(sessions), "closed_date_count": len(market_closures), "calendar_path": relative, "calendar_sha256": sha256(data)})

    receipt = {
        "contract_id": "V4_OFFICIAL_EXCHANGE_SESSION_CALENDAR_CANDIDATE_BUILD_RECEIPT_V1",
        "status": "CANDIDATE_BUILT_PARSE_AND_INDEPENDENT_ACCEPTANCE_PENDING",
        "source_capture_id": capture["capture_id"],
        "source_capture_manifest_sha256": sha256(capture_manifest_bytes),
        "expected_values_sha256": sha256(expected_bytes),
        "input_contract_sha256": sha256((ROOT / "config/v4_official_exchange_calendar_v1.json").read_bytes()),
        "markets": summary,
        "session_method": "Monday-Friday less official-notice closure dates; no stock-bar presence inference",
        "not_pit_observed": True,
        "next_stage": "INDEPENDENT_MANUAL_DATE_REVIEW_AND_OFFICIAL_INDEX_SESSION_CROSSCHECK",
    }
    atomic_write(output_root / "build_receipt.json", (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"output": output_root.relative_to(ROOT).as_posix(), "status": receipt["status"], "markets": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
