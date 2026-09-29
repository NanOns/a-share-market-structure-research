"""Recompute Sep-28 CORE_FACTOR_V1 with explicit forward bootstrap boundaries."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.v4.factors.core import Bar, Observation, compute_core

OUT = ROOT / "reports/v4_05/staging/V4_05_R3_PURE_CORE_FACTORS.jsonl.gz"
RECEIPT = ROOT / "reports/v4_05/V4_05_R3_FACTOR_SOURCE_TIME.json"
TARGET = "2026-09-28"
RELATIVE = ("rps5", "rps20", "rps5_delta1", "rps5_delta3", "rps20_delta3", "rel_market_1", "rel_market_3", "rel_market_5")


def sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def day(value: int) -> str:
    return f"{value // 10000:04d}-{value // 100 % 100:02d}-{value % 100:02d}"


def main() -> None:
    history = json.loads((ROOT / "reports/v4_05/V4_05_R3_DAILY_HISTORY_RECEIPT.json").read_text(encoding="utf-8"))
    calendar_receipt = json.loads((ROOT / "reports/v4_05/V4_05_R3_CALENDAR_RECEIPT.json").read_text(encoding="utf-8"))
    calendars = {}
    for market in ("SSE", "SZSE"):
        ref = calendar_receipt["calendar_bindings"][market]
        calendars[market] = [x for x in json.loads((ROOT / ref["path"]).read_text(encoding="utf-8"))["session_dates"] if x <= TARGET]
    suspended = defaultdict(set)
    status_path = ROOT / "data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz"
    with gzip.open(status_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            if item["status"] == "SUSPENDED":
                suspended[item["security_id"]].add(item["trade_date"])
    counts = Counter()
    unknown = Counter()
    logical = sha256()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(OUT.suffix + ".tmp")
    with tmp.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0, compresslevel=6) as compressed, gzip.open(ROOT / history["artifact_path"], "rt", encoding="utf-8") as source:
        current = None
        bars = []

        def flush() -> None:
            if not bars:
                return
            first = bars[0]
            sid = first["security_id"]
            market = "SSE" if first["board_scope"] in ("SH_MAIN", "STAR") else "SZSE"
            by_date = {day(x["trade_date"]): x for x in bars}
            sessions = [x for x in calendars[market] if x >= day(first["trade_date"])]
            observations = []
            for session in sessions:
                item = by_date.get(session)
                if item is not None and item["qfq_ohlc"] is not None:
                    op, hi, lo, cl = map(float, item["qfq_ohlc"])
                    bar = Bar(op, hi, lo, cl, float(item["amount"]), float(item["volume"]),
                              f"T0_CURRENT_COORDINATE:{item['gbbq_snapshot_identity']}", history["artifact_sha256"])
                    observations.append(Observation(session, "ACTUAL", bar))
                elif item is not None and item["qfq_ohlc"] is None:
                    observations.append(Observation(session, "ADJUSTMENT_UNKNOWN"))
                elif session in suspended[sid] and session < TARGET:
                    observations.append(Observation(session, "CONFIRMED_SUSPENSION"))
                else:
                    observations.append(Observation(session, "UNKNOWN"))
            if not observations or observations[-1].trade_date != TARGET:
                raise ValueError(f"missing target calendar endpoint: {sid}")
            fields = {name: asdict(value) for name, value in compute_core(observations, sid, asof=TARGET).items()}
            for name in RELATIVE:
                fields[name] = {"value": None, "quality_state": "UNKNOWN", "unknown_reason": "BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY", "contract_id": "V4_03_RELATIVE_FACTOR_V1", "parameter_set_id": "V4_03_CORE_FACTOR_PARAMETER_SET_V1", "window_identity": sha256(f"{sid}:{name}:{TARGET}".encode()).hexdigest(), "input_digest": history["logical_digest"], "output_digest": None, "max_source_trade_date": 20260928, "source_asof": TARGET, "formal_publication_at": first["formal_publication_at"], "evidence_origin": "FORWARD_BOOTSTRAP_UNKNOWN"}
            for name, value in fields.items():
                value.update({"target_trade_date": TARGET, "max_source_trade_date": min(20260928, int((value.get("window_end_trade_date") or TARGET).replace("-", ""))), "source_asof": TARGET, "formal_publication_at": first["formal_publication_at"], "available_at": first["formal_publication_at"], "evidence_origin": "V4_05_R3_T0_COORDINATE_REPLAY" if name not in RELATIVE else "FORWARD_BOOTSTRAP_UNKNOWN"})
                counts[f"{name}:{value['quality_state']}"] += 1
                if value.get("unknown_reason"):
                    unknown[f"{name}:{value['unknown_reason']}"] += 1
            row = {"security_id": sid, "source_security_key": first["source_security_key"], "board_scope": first["board_scope"], "trade_date": TARGET,
                   "evidence_origin": "V4_05_R3_T0_COORDINATE_REPLAY", "coordinate_basis": "T0_CURRENT_COORDINATE", "historical_as_recorded_claim": False,
                   "formal_publication_at": first["formal_publication_at"], "source_digest": history["logical_digest"], "fields": fields}
            line = (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
            compressed.write(line)
            logical.update(line)
            counts["rows"] += 1

        for line in source:
            row = json.loads(line)
            sid = row["security_id"]
            if current is not None and sid != current:
                flush()
                bars = []
            current = sid
            bars.append(row)
        flush()
    os.replace(tmp, OUT)
    receipt = {"contract_id": "V4_05_R3_PURE_CORE_FACTOR_REPLAY_V1", "status": "DEGRADED_PASS_BOOTSTRAP_UNKNOWN", "target_trade_date": TARGET,
               "artifact_path": OUT.relative_to(ROOT).as_posix(), "artifact_sha256": sha(OUT), "logical_digest": logical.hexdigest(),
               "row_count": counts["rows"], "field_quality_count": {k: v for k, v in counts.items() if k != "rows"}, "unknown_reasons": dict(unknown),
               "historical_as_recorded_claim": False, "accepted_core_contract": "CORE_FACTOR_V1", "max_source_trade_date": 20260928,
               "relative_bootstrap": "UNKNOWN_NOT_RECONSTRUCTED_AS_PIT", "source_daily_digest": history["logical_digest"], "calendar_bindings": calendar_receipt["calendar_bindings"]}
    temp = RECEIPT.with_suffix(".tmp")
    temp.write_bytes((json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    os.replace(temp, RECEIPT)
    print(json.dumps({"rows": counts["rows"], "sha256": receipt["artifact_sha256"]}))


if __name__ == "__main__":
    main()
