"""Apply PERIOD_ASOF_V1 to the replay-only T0-coordinate daily series."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from hashlib import sha256
import gzip
import io
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/v4_05/staging/V4_05_R3_PERIOD_ASOF.jsonl.gz"
RECEIPT = ROOT / "reports/v4_05/V4_05_R3_PERIOD_ASOF.json"
TARGET = "2026-09-28"


def date_string(value: int) -> str:
    return f"{value // 10000:04d}-{value // 100 % 100:02d}-{value % 100:02d}"


def key(day: str, kind: str) -> str:
    dt = date.fromisoformat(day)
    if kind == "WEEKLY":
        iso = dt.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    return day[:7]


def aggregate(bars: list[dict], calendar: list[str], kind: str, basis: str, source_digest: str) -> list[dict]:
    bars = [bar for bar in bars if date_string(bar["trade_date"]) <= TARGET]
    if not bars:
        return []
    by_period = defaultdict(list)
    for bar in bars:
        by_period[key(date_string(bar["trade_date"]), kind)].append(bar)
    by_period.setdefault(key(TARGET, kind), [])
    sessions = defaultdict(list)
    for day in calendar:
        if date_string(bars[0]["trade_date"]) <= day:
            sessions[key(day, kind)].append(day)
    result = []
    for period, actual in sorted(by_period.items()):
        scheduled = sessions[period]
        dates = {date_string(x["trade_date"]) for x in actual}
        observed = [x for x in actual if x["raw_ohlc"]]
        missing = [day for day in scheduled if day <= TARGET and day not in dates]
        future = [day for day in scheduled if day > TARGET]
        quality_unknown = basis == "QFQ" and any(x["qfq_ohlc"] is None for x in observed)
        valid = observed and not missing and not quality_unknown
        view = "AS_OF_PARTIAL" if future else "CLOSED_ONLY"
        status = "BLOCKED_BY_ADJUSTMENT" if quality_unknown else "BLOCKED_BY_UNKNOWN_STATUS" if missing else "AS_OF_PARTIAL_READY" if future else "CLOSED_ONLY_READY"
        vectors = [x["raw_ohlc" if basis == "RAW" else "qfq_ohlc"] for x in observed]
        ohlc = None
        if valid and vectors:
            ohlc = [vectors[0][0], str(max(float(x[1]) for x in vectors)), str(min(float(x[2]) for x in vectors)), vectors[-1][3]]
        source = actual[0] if actual else bars[0]
        result.append({"security_id": source["security_id"], "source_security_key": source["source_security_key"], "board_scope": source["board_scope"],
                       "period_type": kind, "price_basis": basis, "period_key": period, "period_start_date": scheduled[0] if scheduled else date_string(source["trade_date"]),
                       "period_end_date": scheduled[-1] if scheduled else date_string(source["trade_date"]), "period_last_session": scheduled[-1] if scheduled else date_string(source["trade_date"]),
                       "asof_trade_date": TARGET, "period_view": "BLOCKED" if quality_unknown else view, "period_status": status,
                       "ohlc": ohlc, "volume": sum(x["volume"] for x in observed), "amount": sum(x["amount"] for x in observed),
                       "max_source_trade_date": max((x["trade_date"] for x in actual), default=bars[-1]["trade_date"]), "source_daily_digest": sha256(json.dumps(actual, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                       "calendar_count": len([day for day in scheduled if day <= TARGET]), "actual_count": len(observed),
                       "suspended_count": 0, "unknown_count": len(missing), "adjusted_quality": "UNKNOWN" if quality_unknown else "READY",
                       "coordinate_basis": "T0_CURRENT_COORDINATE", "historical_as_recorded_claim": False,
                       "formal_publication_at": source["formal_publication_at"]})
    return result


def main() -> None:
    calendar_receipt = json.loads((ROOT / "reports/v4_05/V4_05_R3_CALENDAR_RECEIPT.json").read_text(encoding="utf-8"))
    if calendar_receipt["status"] != "PASS_GO_FORWARD_SOURCE_FROZEN":
        raise ValueError("calendar not frozen")
    cal = {}
    for market in ("SSE", "SZSE"):
        ref = calendar_receipt["calendar_bindings"][market]
        path = ROOT / ref["path"]
        if sha256(path.read_bytes()).hexdigest() != ref["sha256"]:
            raise ValueError("calendar changed")
        cal[market] = json.loads(path.read_text(encoding="utf-8"))["session_dates"]
    history = json.loads((ROOT / "reports/v4_05/V4_05_R3_DAILY_HISTORY_RECEIPT.json").read_text(encoding="utf-8"))
    path = ROOT / history["artifact_path"]
    if sha256(path.read_bytes()).hexdigest() != history["artifact_sha256"]:
        raise ValueError("daily history changed")
    counts = Counter()
    logical = sha256()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(OUT.suffix + ".tmp")
    with tmp.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0, compresslevel=6) as zipped, gzip.open(path, "rt", encoding="utf-8") as source:
        current = None
        bars = []

        def flush() -> None:
            if not bars:
                return
            market = "SSE" if bars[0]["board_scope"] in ("SH_MAIN", "STAR") else "SZSE"
            for kind in ("WEEKLY", "MONTHLY"):
                for basis in ("RAW", "QFQ"):
                    for row in aggregate(bars, cal[market], kind, basis, history["logical_digest"]):
                        payload = (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
                        zipped.write(payload)
                        logical.update(payload)
                        counts[f"{kind}:{basis}:{row['period_view']}:{row['period_status']}"] += 1
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
    receipt = {"contract_id": "V4_05_R3_PERIOD_ASOF_V1", "status": "PASS_WITH_FIELD_LOCAL_UNKNOWN", "artifact_path": OUT.relative_to(ROOT).as_posix(),
               "artifact_sha256": sha256(OUT.read_bytes()).hexdigest(), "logical_digest": logical.hexdigest(), "counts": dict(counts),
               "source_daily_digest": history["logical_digest"], "calendar_identity": calendar_receipt["calendar_bindings"],
               "target_week_closed_only": False, "target_month_closed_only": False, "future_price_rows_used": 0,
               "unknown_gap_policy": "MISSING_BAR_IS_UNKNOWN_NOT_SUSPENDED", "suspended_count_claim": 0}
    tmp = RECEIPT.with_suffix(".tmp")
    tmp.write_bytes((json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode())
    os.replace(tmp, RECEIPT)
    print(json.dumps({"rows": counts["rows"], "sha256": receipt["artifact_sha256"]}))


if __name__ == "__main__":
    main()
