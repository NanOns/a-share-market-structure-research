"""R4 PERIOD_ASOF_V1 replay with temporal view separated from data quality."""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import gzip
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_v4_05_r3_periods as accepted_source
from src.v4.r4_replay_paths import replay_report_path

OUT = replay_report_path(ROOT, "reports/v4_05/staging/V4_05_R4_PERIOD_ASOF.jsonl.gz")
RECEIPT = replay_report_path(ROOT, "reports/v4_05/V4_05_R4_PERIOD_ASOF.json")


def aggregate(*args, **kwargs):
    """Use the unchanged R3 window math, repairing only the accepted enum semantics."""
    rows = accepted_source.aggregate(*args, **kwargs)
    for row in rows:
        if row["period_status"] == "BLOCKED_BY_ADJUSTMENT":
            row["period_view"] = "AS_OF_PARTIAL" if row["period_last_session"] > row["asof_trade_date"] else "CLOSED_ONLY"
            row["ohlc"] = None
            row["adjusted_quality"] = "UNKNOWN"
    return rows


def main() -> dict:
    calendar_receipt = json.loads((ROOT / "reports/v4_05/V4_05_R3_CALENDAR_RECEIPT.json").read_text(encoding="utf-8"))
    if calendar_receipt["status"] != "PASS_GO_FORWARD_SOURCE_FROZEN":
        raise ValueError("frozen calendar not accepted")
    calendars = {}
    for market in ("SSE", "SZSE"):
        ref = calendar_receipt["calendar_bindings"][market]
        path = ROOT / ref["path"]
        if sha256(path.read_bytes()).hexdigest() != ref["sha256"]:
            raise ValueError("calendar digest mismatch")
        calendars[market] = json.loads(path.read_text(encoding="utf-8"))["session_dates"]
    history = json.loads((ROOT / "reports/v4_05/V4_05_R3_DAILY_HISTORY_RECEIPT.json").read_text(encoding="utf-8"))
    source = ROOT / history["artifact_path"]
    if sha256(source.read_bytes()).hexdigest() != history["artifact_sha256"]:
        raise ValueError("R3 T0 history changed")
    counts = Counter()
    logical = sha256()
    tmp = OUT.with_suffix(OUT.suffix + ".tmp")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tmp.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0, compresslevel=6) as zipped, gzip.open(source, "rt", encoding="utf-8") as stream:
        current, bars = None, []
        def flush() -> None:
            if not bars:
                return
            market = "SSE" if bars[0]["board_scope"] in ("SH_MAIN", "STAR") else "SZSE"
            for kind in ("WEEKLY", "MONTHLY"):
                for basis in ("RAW", "QFQ"):
                    for row in aggregate(bars, calendars[market], kind, basis, history["logical_digest"]):
                        payload = (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
                        zipped.write(payload)
                        logical.update(payload)
                        counts[f"{kind}:{basis}:{row['period_view']}:{row['period_status']}"] += 1
                        counts["rows"] += 1
        for line in stream:
            row = json.loads(line)
            if current is not None and row["security_id"] != current:
                flush()
                bars = []
            current = row["security_id"]
            bars.append(row)
        flush()
    os.replace(tmp, OUT)
    receipt = {"contract_id": "V4_05_R4_PERIOD_ASOF_V1", "period_contract": "PERIOD_ASOF_V1",
               "status": "PASS_WITH_FIELD_LOCAL_UNKNOWN", "artifact_path": OUT.relative_to(ROOT).as_posix(),
               "artifact_sha256": sha256(OUT.read_bytes()).hexdigest(), "logical_digest": logical.hexdigest(),
               "row_count": counts["rows"], "counts": {k: v for k, v in counts.items() if k != "rows"},
               "source_daily_digest": history["logical_digest"], "calendar_identity": calendar_receipt["calendar_bindings"],
               "target_week_closed_only": False, "target_month_closed_only": False,
               "future_price_rows_used": 0, "unknown_gap_policy": "MISSING_BAR_IS_UNKNOWN_NOT_SUSPENDED",
               "period_view_enum": ["CLOSED_ONLY", "AS_OF_PARTIAL"],
               "period_status_carries_adjustment_gate": True,
               "qfq_unavailable_rows": {"period_view_remains_temporal": True, "period_status": "BLOCKED_BY_ADJUSTMENT",
                                         "ohlc": None, "adjusted_quality": "UNKNOWN"}}
    temp = RECEIPT.with_suffix(RECEIPT.suffix + ".tmp")
    temp.write_bytes((json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    os.replace(temp, RECEIPT)
    return receipt


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, sort_keys=True))
