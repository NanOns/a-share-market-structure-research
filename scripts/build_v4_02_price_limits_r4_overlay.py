from __future__ import annotations

"""Apply R4 special phases over the immutable accepted R3 price artifact."""

import gzip
import hashlib
import json
import os
import tempfile
import sys
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
R3_PRICE = ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R7_20260927.jsonl.gz"
DAILY = ROOT / "data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R7_20260927.parquet"
CAL = ROOT / "data/v4/candidate_calendars/V4_02_MARKET_CALENDAR_20230704_20260924_V2/calendar_sse_20230704_20260924.json"
RULES = ROOT / "config/v4_02_price_limit_rules_r3.json"
EVENTS = ROOT / "reports/v4_02/V4_02_SPECIAL_PRICE_PHASE_EVENTS_R4.jsonl"
OUT = ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R4_20260927.jsonl.gz"
RECEIPT = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_ACCEPTANCE_R4_20260927.json"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(obj, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main() -> int:
    import duckdb
    from workbench_analysis.limit_rules import LimitStateService

    sessions = [str(x).replace("-", "") for x in json.loads(CAL.read_text(encoding="utf-8"))["session_dates"]]
    index = {day: n for n, day in enumerate(sessions)}
    events = [json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_security = {}
    for event in events:
        if event.get("phase") != "DELISTING_FIRST_DAY" or str(event.get("trade_date", "")).replace("-", "") not in sessions:
            raise SystemExit("R4_SPECIAL_PHASE_EVENT_INVALID")
        if len(event.get("source_capture_sha256", "")) != 64 or not event.get("source_ref"):
            raise SystemExit("R4_SPECIAL_PHASE_EVENT_SOURCE_UNBOUND")
        if event["security_id"] in by_security:
            raise SystemExit("R4_DUPLICATE_SPECIAL_PHASE_START")
        by_security[event["security_id"]] = event

    close_by_key = {}
    if events:
        ids = sorted(by_security)
        # Parameters avoid interpolating identifiers into SQL.
        conn = duckdb.connect()
        relation = conn.read_parquet(str(DAILY))
        bars = relation.filter("canonical_security_id IN (" + ",".join("'" + sid.replace("'", "''") + "'" for sid in ids) + ")").project("canonical_security_id, source_security_key, board_scope, trade_date, raw_close").fetchall()
        for sid, source_key, board, day, close in bars:
            close_by_key[(str(sid), str(day).replace("-", ""))] = (str(source_key), str(board), str(close))
        conn.close()

    rule_doc = json.loads(RULES.read_text(encoding="utf-8"))
    service = LimitStateService(rule_doc["rules"])
    source_digest = sha(R3_PRICE)
    output_digest = hashlib.sha256()
    counts: Counter[str] = Counter()
    phase_counts: Counter[str] = Counter()
    range_disposition_candidates = []
    event_index = {sid: index[str(event["trade_date"]).replace("-", "")] for sid, event in by_security.items()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=OUT.name + ".", suffix=".tmp", dir=OUT.parent)
    os.close(fd)
    rows = 0
    try:
        with gzip.open(R3_PRICE, "rt", encoding="utf-8") as src, gzip.open(temp, "wt", encoding="utf-8", newline="\n", compresslevel=6) as dst:
            for line in src:
                row = json.loads(line)
                sid, day = str(row["security_id"]), str(row["trade_date"]).replace("-", "")
                row["contract_id"] = "PRICE_LIMIT_RULE_R4"
                row["special_price_phase"] = "REGULAR"
                event = by_security.get(sid)
                if event:
                    offset = index.get(day, -1) - event_index[sid]
                    if 0 <= offset < 15:
                        phase_counts["DELISTING_FIRST_DAY" if offset == 0 else "DELISTING_PERIOD"] += 1
                        row.update(special_price_phase="DELISTING_FIRST_DAY" if offset == 0 else "DELISTING_PERIOD",
                                   special_phase_source_ref=event["source_ref"],
                                   special_phase_source_capture_sha256=event["source_capture_sha256"],
                                   special_phase_effective_date=event["effective_date"],
                                   special_phase_observed_at=event["observed_at"])
                        if offset == 0:
                            row.update(limit_status="NO_LIMIT", reason="DELISTING_FIRST_DAY_NO_LIMIT",
                                       reference_basis="OFFICIAL_DELISTING_PHASE", limit_up_price=None,
                                       limit_down_price=None, rule_id="SPECIAL_PRICE_PHASE_V1_DELISTING_FIRST_DAY")
                        else:
                            # Delisting-period ratio supersedes the ordinary ST 5% rule.
                            board = str(row["board_scope"])
                            risk_status = "NORMAL"
                            bar = close_by_key.get((sid, day))
                            close = bar[2] if bar else None
                            if row.get("reference_price") is None or close is None:
                                row.update(limit_status="UNKNOWN", reason="DELISTING_PERIOD_REFERENCE_UNAVAILABLE",
                                           risk_status=risk_status, limit_up_price=None, limit_down_price=None)
                            else:
                                exchange, rule_board = ("SH", "MAIN") if board == "SH_MAIN" else ("SZ", "MAIN") if board == "SZ_MAIN" else ("SZ", "GROWTH") if board == "CHINEXT" else ("SH", "STAR") if board == "STAR" else ("", "")
                                result = service.evaluate({"security_id": sid, "trade_date": day,
                                    "exchange": exchange, "board": rule_board, "risk_status": risk_status,
                                    "suspended": False, "reference_status": "KNOWN",
                                    "quote_prev_close": row["reference_price"], "close": close,
                                    "listing_phase": "REGULAR", "ex_rights_reference_unknown": False})
                                row.update(risk_status=risk_status, rule_id=result.get("rule_id"),
                                           limit_up_price=str(result["limit_up_price"]) if result.get("limit_up_price") is not None else None,
                                           limit_down_price=str(result["limit_down_price"]) if result.get("limit_down_price") is not None else None,
                                           limit_status=result.get("limit_state", "UNKNOWN"),
                                           reason=result.get("reason"), reference_basis="DELISTING_PERIOD_OFFICIAL_RULE")
                        row["is_st"] = row.get("is_st")
                    elif row.get("reason") == "CLOSE_OUTSIDE_LIMIT_RANGE":
                        # A dated event applies only from its effective session
                        # forward; never project a later lifecycle phase backward.
                        missing_reason = ("SPECIAL_REFERENCE_PRICE_UNAVAILABLE"
                                          if str(row.get("reference_basis", "")).startswith("TDX_XRXD_REFERENCE_TRANSFORM")
                                          else "SPECIAL_PHASE_EVIDENCE_UNAVAILABLE")
                        row.update(special_price_phase="UNKNOWN_SPECIAL_PHASE", limit_status="UNKNOWN",
                                   reason=missing_reason, limit_up_price=None, limit_down_price=None)
                        range_disposition_candidates.append({"security_id": sid, "source_security_key": row.get("source_security_key"),
                            "trade_date": row.get("trade_date"), "board_scope": row.get("board_scope"),
                            "reference_price": row.get("reference_price"), "risk_status": row.get("risk_status"),
                            "unknown_reason": missing_reason})
                elif row.get("reason") == "IPO_FIRST_5_TRADING_DAYS":
                    row["special_price_phase"] = "IPO_FIRST_5_TRADING_DAYS"
                elif row.get("reason") == "CLOSE_OUTSIDE_LIMIT_RANGE":
                    # Do not infer a phase or official reference from the price move.
                    missing_reason = ("SPECIAL_REFERENCE_PRICE_UNAVAILABLE"
                                      if str(row.get("reference_basis", "")).startswith("TDX_XRXD_REFERENCE_TRANSFORM")
                                      else "SPECIAL_PHASE_EVIDENCE_UNAVAILABLE")
                    row.update(special_price_phase="UNKNOWN_SPECIAL_PHASE", limit_status="UNKNOWN",
                               reason=missing_reason, limit_up_price=None,
                               limit_down_price=None)
                    range_disposition_candidates.append({"security_id": sid, "source_security_key": row.get("source_security_key"),
                        "trade_date": row.get("trade_date"), "board_scope": row.get("board_scope"),
                        "reference_price": row.get("reference_price"), "risk_status": row.get("risk_status"),
                        "unknown_reason": missing_reason})
                encoded = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                dst.write(encoded)
                output_digest.update(encoded.encode("utf-8"))
                rows += 1
                counts[str(row.get("limit_status") or "UNKNOWN")] += 1
        with open(temp, "r+b") as stream:
            os.fsync(stream.fileno())
        os.replace(temp, OUT)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

    result = {"contract_id": "V4_02_PRICE_LIMIT_ACCEPTANCE_R4", "version": "4.0.0",
        "status": "PRICE_LIMIT_R4_CANDIDATE_PASS_WITH_FAIL_CLOSED_UNKNOWN", "stage_contract": "PRICE_LIMIT_RULE_R4 + SPECIAL_PRICE_PHASE_V1",
        "row_count": rows, "limit_status_counts": dict(counts), "special_phase_counts": dict(phase_counts),
        "r3_range_exception_rows": len(range_disposition_candidates), "range_exception_candidates": range_disposition_candidates,
        "artifact": {"path": str(OUT.relative_to(ROOT)).replace("\\", "/"), "bytes": OUT.stat().st_size, "sha256": sha(OUT), "normalized_output_sha256": output_digest.hexdigest()},
        "inputs": {"r3_price": {"path": str(R3_PRICE.relative_to(ROOT)).replace("\\", "/"), "sha256": source_digest},
                   "daily_r7": {"path": str(DAILY.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(DAILY)},
                   "events": {"path": str(EVENTS.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(EVENTS)},
                   "phase_contract": {"path": "config/v4_02_special_price_phase_v1.json", "sha256": sha(ROOT / "config/v4_02_special_price_phase_v1.json")}},
        "scope": {"required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"], "bse": "OPTIONAL_DEGRADED_EXCLUDED"},
        "reference_policy": "R3 previous-close states are frozen; official delisting first-day events remove the limit check; subsequent delisting-period sessions use effective non-ST board limits; unproved phases fail closed.",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "tdx_root_write_count": 0}
    atomic_json(RECEIPT, result)
    print(json.dumps({"rows": rows, "states": dict(counts), "phases": dict(phase_counts), "unknown_range_rows": len(range_disposition_candidates), "artifact_sha256": result["artifact"]["sha256"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
