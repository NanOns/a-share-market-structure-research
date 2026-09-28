"""Frozen DEV baseline diagnostic sample; never publishes an accepted V4-03 head."""

from __future__ import annotations

from dataclasses import asdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

import duckdb

from src.v4.factors import Bar, Observation, compute_core


ROOT = Path(__file__).resolve().parents[1]
HEAD = ROOT / "data/v4/V4_DEV_BASELINE_HEAD.json"
MANIFEST = ROOT / "data/v4/bootstrap/V4_DM01_BOOTSTRAP_MANIFEST_R1.json"
STAGING = ROOT / "reports/v4_03/staging"
SECURITY_KEY = sys.argv[1] if len(sys.argv) > 1 else "SH.600006"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes((json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"))
    os.replace(temp, path)


def main() -> None:
    head = json.loads(HEAD.read_text(encoding="utf-8"))
    if head["accepted_data_cutoff"] != "2026-09-24" or head["baseline_id"] != "V4_DEV_BASELINE_R1_20260928":
        raise RuntimeError("frozen DEV baseline changed")
    if digest(MANIFEST) != head["bootstrap_manifest"]["sha256"]:
        raise RuntimeError("DEV baseline manifest digest mismatch")
    manifest = json.loads((ROOT / json.loads(MANIFEST.read_text(encoding="utf-8"))["parent_artifacts"]["v4_02_manifest"]["path"]).read_text(encoding="utf-8"))
    accepted = manifest["components"]["DAILY_R7"]
    daily = ROOT / accepted["path"]
    if digest(daily) != accepted["sha256"]:
        raise RuntimeError("accepted adjusted daily digest mismatch")
    calendar_ref = manifest["components"]["CALENDAR"]
    calendar_path = ROOT / calendar_ref["path"]
    if digest(calendar_path) != calendar_ref["sha256"]:
        raise RuntimeError("calendar digest mismatch")
    calendar = json.loads(calendar_path.read_text(encoding="utf-8"))["session_dates"]
    cutoff = head["accepted_data_cutoff"]
    calendar = [d for d in calendar if d <= cutoff]
    con = duckdb.connect()
    data = con.execute("select * from read_parquet(?) where source_security_key = ? and trade_date <= ? order by trade_date",
                       [daily.as_posix(), SECURITY_KEY, int(cutoff.replace("-", ""))]).fetch_df()
    if data.empty:
        raise RuntimeError("sample security absent from accepted daily")
    bars = {}
    rejected = {}
    for row in data.to_dict("records"):
        if row["adjusted_quality"] != "READY" or row["trading_status"] != "ACTUAL_TRADED":
            day = str(row["trade_date"])
            date = f"{day[:4]}-{day[4:6]}-{day[6:]}"
            if row["trading_status"] == "ACTUAL_TRADED":
                rejected[date] = "ADJUSTMENT_UNKNOWN"
            continue
        day = str(row["trade_date"])
        date = f"{day[:4]}-{day[4:6]}-{day[6:]}"
        basis = f"{row['price_basis']}:{row['adjustment_source_revision']}"
        bars[date] = Bar(float(row["qfq_open"]), float(row["qfq_high"]), float(row["qfq_low"]),
                         float(row["qfq_close"]), float(row["amount"]), float(row["volume"]),
                         basis, accepted["sha256"])
    status_path = ROOT / "data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz"
    status = {}
    with gzip.open(status_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["source_security_key"] == SECURITY_KEY and row["trade_date"] <= cutoff:
                status[row["trade_date"]] = row["status"]
    observations = []
    started = False
    for date in calendar:
        bar = bars.get(date)
        if bar is not None or date in rejected:
            started = True
        if bar is not None:
            observations.append(Observation(date, "ACTUAL", bar))
        elif not started:
            observations.append(Observation(date, "PRE_LISTING"))
        else:
            observations.append(Observation(date, rejected.get(date) or
                                            ("CONFIRMED_SUSPENSION" if status.get(date) == "SUSPENDED" else "UNKNOWN")))
    result = compute_core(observations, str(data.iloc[-1]["canonical_security_id"]))
    payload = {"contract_id": "V4_03_REAL_SAMPLE_DIAGNOSTIC_R1", "status": "DIAGNOSTIC_ONLY",
               "security_key": SECURITY_KEY, "security_id": str(data.iloc[-1]["canonical_security_id"]),
               "trade_date": cutoff, "evidence_origin": "DIAGNOSTIC_NON_PIT",
               "dev_baseline_head_sha256": digest(HEAD), "accepted_daily_sha256": accepted["sha256"],
               "calendar_sha256": calendar_ref["sha256"], "status_sha256": digest(status_path),
               "fields": {k: asdict(v) for k, v in sorted(result.items())}}
    atomic_json(STAGING / f"V4_03_CORE_FACTOR_REAL_SAMPLE_{SECURITY_KEY.replace('.', '')}_R1.json", payload)
    print(json.dumps({"status": payload["status"], "security_id": payload["security_id"],
                      "field_count": len(result), "observed": sum(v.quality_state == "OBSERVED" for v in result.values()),
                      "unknown": sum(v.quality_state == "UNKNOWN" for v in result.values())}))


if __name__ == "__main__":
    main()
