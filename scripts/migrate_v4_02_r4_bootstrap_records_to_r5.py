from __future__ import annotations

"""Normalize accepted R4 facts into R5 generic alias/event bootstrap tables."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = ROOT / "data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json"
ALIAS_AUDIT = ROOT / "reports/v4_02/V4_01_CODE_CHANGE_ALIAS_AUDIT_R7.json"
R4_EVENTS = ROOT / "reports/v4_02/V4_02_SPECIAL_PRICE_PHASE_EVENTS_R4.jsonl"
CAPTURE_POLICY = ROOT / "config/special_phase_source_capture_v1.json"
ALIAS_OUT = ROOT / "data/v4/bootstrap/dated_security_alias_r7.jsonl"
EVENTS_OUT = ROOT / "data/v4/bootstrap/special_price_phase_events_r4.jsonl"
REQUESTS_OUT = ROOT / "data/v4/bootstrap/special_phase_source_requests_r4.jsonl"


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def jsonl(rows: list[dict]) -> bytes:
    return b"".join((json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8") for row in rows)


def event_id(row: dict) -> str:
    material = "|".join(str(row.get(field) or "") for field in ("security_id", "trade_date", "phase", "source_ref"))
    return "SPPH-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20].upper()


def main() -> int:
    identity = json.loads(IDENTITY.read_text(encoding="utf-8"))
    audit = json.loads(ALIAS_AUDIT.read_text(encoding="utf-8"))
    capture_policy = json.loads(CAPTURE_POLICY.read_text(encoding="utf-8"))
    observed = str(identity.get("observed_at_utc") or audit.get("observed_at_utc") or "")
    target = audit.get("target") or {}
    security_id = str(target.get("security_id") or "")
    records = [row for row in identity.get("records", []) if row.get("security_id") == security_id]
    if not security_id or len(records) != 2:
        raise SystemExit("R5_ALIAS_BOOTSTRAP_EXPECTED_TWO_DATED_RECORDS")
    evidence = audit.get("evidence") or {}
    alias_rows = []
    for row in records:
        alias_rows.append({
            "contract_id": "DATED_SECURITY_ALIAS_V1", "revision": 1,
            "security_id": row["security_id"], "source_security_key": row["source_security_key"],
            "effective_from": row["symbol_effective_from"], "effective_to": row.get("symbol_effective_to"),
            "exchange": row["exchange"], "board": row["board"], "alias_role": row["alias_role"],
            "source_revision": row.get("source_revision_id") or "",
            "supersedes_revision_id": None,
            "evidence_ref": evidence.get("source_ref"), "evidence_hash": evidence.get("source_capture_sha256"),
            "evidence_capture_path": evidence.get("source_capture_path"),
            "observed_at": observed, "system_available_at": observed,
        })
    alias_rows.sort(key=lambda row: (row["security_id"], row["effective_from"]))

    r4_events = [json.loads(line) for line in R4_EVENTS.read_text(encoding="utf-8").splitlines() if line.strip()]
    event_rows, requests = [], []
    for old in r4_events:
        event = {
            "event_id": event_id(old), "security_id": old["security_id"],
            "trade_date": old["trade_date"], "phase": old["phase"],
            "phase_effective_from": old.get("effective_date") or old["trade_date"],
            "phase_effective_to": None, "exchange": str(old["source_security_key"]).split(".", 1)[0],
            "board": old["board_scope"], "board_scope": old["board_scope"], "event_type": old["event_type"],
            "official_reference_price": old.get("official_reference_price"),
            "official_reference_formula": old.get("official_reference_formula"),
            "source_ref": old["source_ref"], "source_capture_path": old["source_capture_path"],
            "source_capture_sha256": old["source_capture_sha256"],
            "observed_at": old["observed_at"], "system_available_at": old["observed_at"],
            "quality": "OFFICIAL_PRIMARY_SOURCE_CAPTURED", "contract_id": "SPECIAL_PRICE_PHASE_EVENT_V1",
            "revision": 1, "source_security_key": old["source_security_key"],
        }
        event["event_id"] = event_id(event)
        event_rows.append(event)
        requests.append({
            "event_id": event["event_id"], "security_id": event["security_id"],
            "phase": event["phase"], "effective_date": event["phase_effective_from"],
            "source_ref": event["source_ref"], "expected_content_type": capture_policy["expected_content_type"],
            "max_bytes": capture_policy["maximum_request_bytes"],
            "source_capture_path": event["source_capture_path"],
            "source_capture_sha256": event["source_capture_sha256"],
        })
    event_rows.sort(key=lambda row: (row["security_id"], row["trade_date"], row["event_id"]))
    requests.sort(key=lambda row: row["event_id"])
    atomic_bytes(ALIAS_OUT, jsonl(alias_rows))
    atomic_bytes(EVENTS_OUT, jsonl(event_rows))
    atomic_bytes(REQUESTS_OUT, jsonl(requests))
    print(json.dumps({"alias_records": len(alias_rows), "special_phase_events": len(event_rows),
                      "source_requests": len(requests), "status": "MIGRATED_FROM_ACCEPTED_R4_FACTS"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
