from __future__ import annotations

"""Light replay of the frozen R4 price-limit artifact through generic R5 phase consumption."""

import gzip
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.special_price_phases import PhasePolicyRegistry, SpecialPhaseEventStore, resolve_event_phase

SOURCE = ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R4_20260927.jsonl.gz"
EVENTS = ROOT / "data/v4/bootstrap/special_price_phase_events_r4.jsonl"
POLICY = ROOT / "config/special_price_phase_policy_v1.json"
CALENDAR = ROOT / "data/v4/candidate_calendars/V4_02_MARKET_CALENDAR_20230704_20260924_V2/calendar_sse_20230704_20260924.json"
R4_AUDIT = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R4.json"
R4_ACCEPTANCE = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_ACCEPTANCE_R4_20260927.json"
R4_POSTCHECK = ROOT / "reports/v4_02/V4_02_FINAL_INDEPENDENT_POSTCHECK_R4.json"
OUT = ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R5_20260927.jsonl.gz"
RECEIPT = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_REPLAY_R5.json"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main() -> int:
    if not all(p.is_file() for p in (SOURCE, EVENTS, POLICY, CALENDAR, R4_AUDIT, R4_ACCEPTANCE, R4_POSTCHECK)):
        raise SystemExit("R5_REPLAY_INPUT_MISSING")
    r4 = json.loads(R4_ACCEPTANCE.read_text(encoding="utf-8"))
    if sha(SOURCE) != r4["artifact"]["sha256"]:
        raise SystemExit("R5_REPLAY_R4_ARTIFACT_HASH_MISMATCH")
    store = SpecialPhaseEventStore.from_jsonl(EVENTS)
    policies = PhasePolicyRegistry.from_json(POLICY)
    sessions = json.loads(CALENDAR.read_text(encoding="utf-8"))["session_dates"]
    audit = json.loads(R4_AUDIT.read_text(encoding="utf-8"))
    dispositions = audit.get("dispositions", [])
    resolved = sum(x.get("disposition") == "RESOLVED_SPECIAL_PHASE" for x in dispositions)
    if not resolved:
        resolved = sum(x.get("disposition") == "RESOLVED_DELISTING_FIRST_DAY_NO_LIMIT" for x in dispositions)
    fail_closed = int(audit.get("scope", {}).get("r3_fail_closed_dispositioned", 0))
    r4_postcheck = json.loads(R4_POSTCHECK.read_text(encoding="utf-8"))
    event_ids = {event.security_id for event in store.events}
    event_phase_counts: Counter[str] = Counter()
    all_phase_counts: Counter[str] = Counter()
    unknown_reasons: Counter[str] = Counter()
    rows = 0
    output_digest = hashlib.sha256()
    mismatch = None
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=OUT.name + ".", suffix=".tmp", dir=OUT.parent)
    os.close(fd)
    try:
        with gzip.open(SOURCE, "rt", encoding="utf-8") as src, gzip.open(temp, "wt", encoding="utf-8", newline="\n", compresslevel=6) as dst:
            for line in src:
                row = json.loads(line)
                sid, day = str(row.get("security_id") or ""), str(row.get("trade_date") or "")
                if sid in event_ids:
                    phase, event = resolve_event_phase(store, sid, day, sessions, policies, str(row.get("board_scope") or ""))
                    actual = str(row.get("special_price_phase") or "REGULAR")
                    event_phase = phase.value in {"DELISTING_FIRST_DAY", "DELISTING_PERIOD"}
                    row_event_phase = actual in {"DELISTING_FIRST_DAY", "DELISTING_PERIOD"}
                    if event_phase != row_event_phase or (event_phase and phase.value != actual):
                        if mismatch is None:
                            mismatch = {"security_id": sid, "trade_date": day, "r4_phase": actual, "r5_phase": phase.value}
                    if phase.value in {"DELISTING_FIRST_DAY", "DELISTING_PERIOD"}:
                        event_phase_counts[phase.value] += 1
                    if event is None and phase.value in {"DELISTING_FIRST_DAY", "DELISTING_PERIOD"}:
                        mismatch = mismatch or {"security_id": sid, "trade_date": day, "reason": "EVENT_BINDING_MISSING"}
                phase_value = str(row.get("special_price_phase") or "REGULAR")
                all_phase_counts[phase_value] += 1
                if row.get("limit_status") == "UNKNOWN":
                    unknown_reasons[str(row.get("reason") or "<blank>")] += 1
                encoded = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                dst.write(encoded)
                output_digest.update(encoded.encode("utf-8"))
                rows += 1
        with open(temp, "r+b") as stream:
            stream.flush()
            os.fsync(stream.fileno())
        if mismatch:
            raise SystemExit("R5_REPLAY_PHASE_MISMATCH:" + json.dumps(mismatch, ensure_ascii=False))
        os.replace(temp, OUT)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

    expected_phases = {"DELISTING_FIRST_DAY": 22, "DELISTING_PERIOD": 308}
    expected_unknown = {str(k): int(v) for k, v in r4.get("limit_status_counts", {}).items()}
    unknown_count = sum(unknown_reasons.values())
    phases_match = dict(all_phase_counts) == r4_postcheck.get("counts", {}).get("special_price_phases", {})
    reasons_match = dict(unknown_reasons) == r4_postcheck.get("counts", {}).get("unknown_reasons", {})
    payloads_match = output_digest.hexdigest() == r4["artifact"]["normalized_output_sha256"]
    if rows != int(r4["row_count"]) or dict(event_phase_counts) != expected_phases or resolved != 22 or fail_closed != 31 or unknown_count != int(expected_unknown.get("UNKNOWN", -1)) or not phases_match or not reasons_match or not payloads_match:
        status = "BLOCKED"
    else:
        status = "PASS"
    result = {
        "contract_id": "V4_02_PRICE_LIMIT_REPLAY_R5", "version": "1.0.0", "status": status,
        "stage_contract": "SPECIAL_PRICE_PHASE_EVENT_V1 + SPECIAL_PRICE_PHASE_POLICY_V1; R4 data frozen",
        "row_count": rows, "r4_row_count": int(r4["row_count"]), "resolved_special_events": resolved,
        "r4_fail_closed_dispositions": fail_closed, "event_derived_phase_counts": dict(event_phase_counts),
        "all_phase_counts": dict(all_phase_counts), "all_phase_counts_match_r4": phases_match,
        "unknown_rows": unknown_count, "unknown_reason_inventory_matches_r4": reasons_match,
        "unknown_reason_inventory": dict(unknown_reasons), "unknown_reason_count_matches_r4": unknown_count == int(expected_unknown.get("UNKNOWN", -1)),
        "row_payloads_preserved": payloads_match,
        "output": {"path": str(OUT.relative_to(ROOT)).replace("\\", "/"), "bytes": OUT.stat().st_size,
                   "sha256": sha(OUT), "normalized_output_sha256": output_digest.hexdigest()},
        "inputs": {"r4_price_sha256": sha(SOURCE), "events_sha256": sha(EVENTS), "phase_policy_sha256": sha(POLICY),
                   "r4_audit_sha256": sha(R4_AUDIT), "r4_acceptance_sha256": sha(R4_ACCEPTANCE)},
        "equivalence": {"r4_price_unknown_count": int(expected_unknown.get("UNKNOWN", -1)), "r5_price_unknown_count": unknown_count,
                        "outcome_equivalent": payloads_match},
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "next_stage": "R5_INDEPENDENT_POSTCHECK_AND_FINAL_RECEIPT; V4-03_REMAINS_BLOCKED_PENDING_EXTERNAL_ACCEPTANCE",
    }
    atomic_json(RECEIPT, result)
    print(json.dumps({"status": status, "rows": rows, "events": dict(event_phase_counts), "fail_closed": fail_closed,
                      "unknown": unknown_count, "payload_equivalent": result["equivalence"]["outcome_equivalent"]}, ensure_ascii=False))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
