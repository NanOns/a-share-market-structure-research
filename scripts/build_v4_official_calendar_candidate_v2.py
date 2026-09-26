from __future__ import annotations

"""Build the bounded V2 official exchange calendar candidate."""

import hashlib
import json
import os
import re
import tempfile
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config/v4_official_exchange_calendar_v2.json"
EXPECTED_PATH = ROOT / "config/v4_official_exchange_calendar_expected_closures_v2.json"


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
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main() -> int:
    contract_bytes = CONTRACT_PATH.read_bytes()
    contract = json.loads(contract_bytes)
    expected_bytes = EXPECTED_PATH.read_bytes()
    expected = json.loads(expected_bytes)
    if contract["contract_id"] != expected["governing_calendar_contract"]:
        raise ValueError("CALENDAR_CONTRACT_BINDING_MISMATCH")
    if contract["coverage"]["start_date"] != expected["coverage"]["start_date"] or contract["coverage"]["end_date"] != expected["coverage"]["end_date"]:
        raise ValueError("CALENDAR_COVERAGE_BINDING_MISMATCH")
    if expected["coverage"]["end_date"] != contract["coverage"]["source_cutoff"]:
        raise ValueError("CALENDAR_MUST_END_AT_SOURCE_CUTOFF")

    manifests: dict[str, tuple[dict, Path, str]] = {}
    for item in expected["source_capture_manifests"]:
        path = ROOT / item["path"]
        raw = path.read_bytes()
        digest = sha256(raw)
        if digest != item["sha256"]:
            raise ValueError(f"SOURCE_MANIFEST_HASH_MISMATCH:{item['capture_id']}")
        manifest = json.loads(raw)
        if manifest["capture_id"] != item["capture_id"]:
            raise ValueError("SOURCE_MANIFEST_CAPTURE_ID_MISMATCH")
        manifests[item["capture_id"]] = (manifest, path.parent, digest)

    start = date.fromisoformat(expected["coverage"]["start_date"])
    end = date.fromisoformat(expected["coverage"]["end_date"])
    weekdays = set(expected["coverage"]["weekdays"])
    output_root = ROOT / "data/v4/candidate_calendars" / "V4_02_MARKET_CALENDAR_20230704_20260924_V2"
    if output_root.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    summary = []
    for market, market_info in expected["markets"].items():
        closures: set[date] = set()
        source_records = []
        for year_text, year_info in market_info["years"].items():
            found = []
            for manifest, capture_root, manifest_hash in manifests.values():
                found.extend((source, capture_root, manifest_hash) for source in manifest["sources"] if source["source_id"] == year_info["source_id"])
            if len(found) != 1:
                raise ValueError(f"SOURCE_ID_NOT_UNIQUE:{market}:{year_text}")
            source, capture_root, manifest_hash = found[0]
            source_id_parts = source["source_id"].split("_")
            source_market = source.get("market", source_id_parts[1].upper() if len(source_id_parts) >= 3 else None)
            source_year = source.get("year", source_id_parts[-1])
            if source_market != market or int(source_year) != int(year_text):
                raise ValueError(f"SOURCE_MARKET_YEAR_MISMATCH:{source['source_id']}")
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
                first = date.fromisoformat(interval["start"])
                last = date.fromisoformat(interval["end"])
                if last < first:
                    raise ValueError("INVALID_CLOSURE_RANGE")
                cursor = first
                while cursor <= last:
                    if start <= cursor <= end:
                        closures.add(cursor)
                    cursor += timedelta(days=1)
            source_records.append({"source_id": source["source_id"], "sha256": source["sha256"], "capture_manifest_sha256": manifest_hash})

        sessions = []
        cursor = start
        while cursor <= end:
            if cursor.weekday() in weekdays and cursor not in closures:
                sessions.append(cursor.isoformat())
            cursor += timedelta(days=1)
        payload = {
            "contract_id": "V4_OFFICIAL_EXCHANGE_SESSION_CALENDAR_CANDIDATE_V2",
            "capability": "CANDIDATE_ONLY_INDEPENDENT_POSTCHECK_PENDING",
            "market": market,
            "board_ids": market_info["board_ids"],
            "coverage": {"start_date": start.isoformat(), "end_date": end.isoformat(), "source_cutoff": end.isoformat()},
            "base_weekdays": sorted(weekdays),
            "closed_dates_from_official_notices": sorted(d.isoformat() for d in closures),
            "session_dates": sessions,
            "session_count": len(sessions),
            "calendar_contract_sha256": sha256(contract_bytes),
            "expected_values_sha256": sha256(expected_bytes),
            "source_capture_manifests": [{"capture_id": i["capture_id"], "sha256": manifests[i["capture_id"]][2]} for i in expected["source_capture_manifests"]],
            "source_notices": source_records,
            "lineage": "RECONSTRUCTED_FROM_HASH_BOUND_OFFICIAL_NOTICES; NOT_PIT_OBSERVED",
            "acceptance": "PENDING_INDEPENDENT_INDEX_CROSSCHECK_AND_POSTCHECK",
        }
        data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        relative = f"calendar_{market.lower()}_20230704_20260924.json"
        atomic_write(output_root / relative, data)
        summary.append({"market": market, "session_count": len(sessions), "closed_date_count": len(closures), "calendar_path": relative, "calendar_sha256": sha256(data)})

    receipt = {
        "contract_id": "V4_OFFICIAL_EXCHANGE_SESSION_CALENDAR_CANDIDATE_BUILD_RECEIPT_V2",
        "status": "CANDIDATE_BUILT_INDEPENDENT_POSTCHECK_PENDING",
        "calendar_contract_sha256": sha256(contract_bytes),
        "expected_values_sha256": sha256(expected_bytes),
        "source_capture_manifests": [{"capture_id": i["capture_id"], "sha256": manifests[i["capture_id"]][2]} for i in expected["source_capture_manifests"]],
        "coverage": {"start_date": start.isoformat(), "end_date": end.isoformat()},
        "markets": summary,
        "session_method": "Monday-Friday less captured official annual-notice closure dates; no stock-bar presence inference",
        "not_pit_observed": True,
        "next_stage": "INDEPENDENT_ACCEPTED_PRIMARY_INDEX_SESSION_CROSSCHECK_AND_POSTCHECK",
    }
    atomic_write(output_root / "build_receipt.json", (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"output": output_root.relative_to(ROOT).as_posix(), "status": receipt["status"], "markets": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
