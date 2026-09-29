"""Target-date equal-weight market reference with accepted start-universe snapshots."""
from __future__ import annotations

from collections import defaultdict
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.v4.factors.core import market_reference

OUT = ROOT / "reports/v4_05/V4_05_R3_MARKET_REFERENCE.json"
TARGET = "2026-09-28"


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def sha(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    factor_receipt = json.loads((ROOT / "reports/v4_05/V4_05_R3_FACTOR_SOURCE_TIME.json").read_text(encoding="utf-8"))
    calendar_receipt = json.loads((ROOT / "reports/v4_05/V4_05_R3_CALENDAR_RECEIPT.json").read_text(encoding="utf-8"))
    ref = calendar_receipt["calendar_bindings"]["SSE"]
    calendar = json.loads((ROOT / ref["path"]).read_text(encoding="utf-8"))["session_dates"]
    index = calendar.index(TARGET)
    starts = {h: calendar[index - h] for h in (1, 3, 5)}
    universe_path = ROOT / "data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz"
    accepted = json.loads((ROOT / "data/v4/V4_01_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))
    if sha(universe_path) != accepted["historical_universe"]["sha256"]:
        raise ValueError("accepted start universe changed")
    members = defaultdict(set)
    with gzip.open(universe_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["trade_date"] in starts.values() and row["board_scope"] in ("SH_MAIN", "SZ_MAIN", "STAR", "CHINEXT"):
                members[row["trade_date"]].add(row["security_id"])
    factors = {}
    with gzip.open(ROOT / factor_receipt["artifact_path"], "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            factors[row["security_id"]] = row
    rows = {}
    for horizon, start in starts.items():
        returns = {sid: row["fields"][f"ret{horizon}"]["value"] for sid, row in factors.items() if row["fields"][f"ret{horizon}"]["quality_state"] == "OBSERVED"}
        value, coverage = market_reference(returns, members[start])
        row = {"contract_id": "MARKET_RELATIVE_REFERENCE_V1", "target_trade_date": TARGET, "start_session": start, "end_session": TARGET,
               "start_universe_snapshot_id": digest(sorted(members[start])), "start_universe_source": "V4_01_EXTERNALLY_ACCEPTED_HISTORICAL_UNIVERSE",
               "evaluable_set_identity": coverage["evaluable_set_identity"], "adjustment_basis_id": "T0_CURRENT_COORDINATE",
               "input_source_digest": factor_receipt["logical_digest"], "reference_return": value,
               "coverage": coverage["coverage"], "missing_count": coverage["missing_count"], "universe_count": coverage["universe_count"],
               "evaluable_count": coverage["evaluable_count"], "quality_state": "UNKNOWN" if value is None else "OBSERVED", "unknown_reason": coverage["unknown_reason"],
               "max_source_trade_date": 20260928, "formal_publication_at": next(iter(factors.values()))["formal_publication_at"],
               "historical_as_recorded_claim": False, "evidence_origin": "V4_05_R3_CURRENT_FORWARD_WITH_ACCEPTED_START_UNIVERSE"}
        row["output_digest"] = digest(row)
        rows[str(horizon)] = row
    result = {"contract_id": "V4_05_R3_MARKET_REFERENCE_REPLAY_V1", "status": "PASS" if all(r["quality_state"] == "OBSERVED" for r in rows.values()) else "DEGRADED_PASS", "target_trade_date": TARGET, "horizons": rows, "accepted_v4_01_universe_sha256": sha(universe_path), "calendar_sha256": ref["sha256"], "factor_digest": factor_receipt["logical_digest"], "max_source_trade_date": 20260928}
    tmp = OUT.with_suffix(".tmp")
    tmp.write_bytes((json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    os.replace(tmp, OUT)
    print(json.dumps({h: (r["quality_state"], r["coverage"]) for h, r in rows.items()}))


if __name__ == "__main__":
    main()
