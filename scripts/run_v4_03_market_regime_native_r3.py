"""Materialize V4-03 daily market primitives from frozen PIT membership and facts."""

from collections import defaultdict
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path

import duckdb

from src.v4.factors.native import market_axis_primitives, market_trend_axis

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/v4_03/staging/V4_03_MARKET_REGIME_NATIVE_CANDIDATE_R3.jsonl.gz"
RECEIPT = ROOT / "reports/v4_03/V4_03_MARKET_REGIME_NATIVE_RECEIPT_R3.json"
PATH = ROOT / "reports/v4_03/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R3.jsonl.gz"
REQUIRED = {"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def atomic(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main():
    head_path = ROOT / "data/v4/V4_DEV_BASELINE_HEAD.json"
    head = json.loads(head_path.read_text(encoding="utf-8"))
    bootstrap = json.loads((ROOT / head["bootstrap_manifest"]["path"]).read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / bootstrap["parent_artifacts"]["v4_02_manifest"]["path"]).read_text(encoding="utf-8"))
    daily_ref, calendar_ref, limit_ref = (manifest["components"][key] for key in ("DAILY_R7", "CALENDAR", "FROZEN_R3_BASE"))
    universe_ref = bootstrap["parent_artifacts"]["v4_01_universe"]
    refs = (daily_ref, calendar_ref, limit_ref, universe_ref)
    if any(sha(ROOT / ref["path"]) != ref["sha256"] for ref in refs):
        raise RuntimeError("accepted source digest mismatch")
    path_receipt = json.loads((ROOT / "reports/v4_03/V4_03_MARKET_REFERENCE_PATH_RECEIPT_R3.json").read_text(encoding="utf-8"))
    if sha(PATH) != path_receipt["output_sha256"]:
        raise RuntimeError("market path artifact digest mismatch")
    path_rows = [json.loads(line) for line in gzip.open(PATH, "rt", encoding="utf-8")]
    sessions = [row["trade_date"] for row in path_rows]
    prior_session = {sessions[i]: sessions[i - 1] for i in range(1, len(sessions))}
    if sessions[-1] != head["accepted_data_cutoff"]:
        raise RuntimeError("market path cutoff mismatch")
    members = defaultdict(set)
    snapshot_parts = defaultdict(list)
    wanted = set(sessions)
    with gzip.open(ROOT / universe_ref["path"], "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            day = row["trade_date"]
            if day in wanted and row["board_scope"] in REQUIRED:
                sid = row["security_id"]
                if sid in members[day]:
                    raise RuntimeError("duplicate PIT member")
                members[day].add(sid)
                snapshot_parts[day].append((sid, row.get("membership_basis"), row.get("source_revision_id"), row.get("eligibility_status")))
    snapshot_ids = {day: digest(sorted(snapshot_parts[day])) for day in sessions}
    if any(not members[day] for day in sessions):
        raise RuntimeError("missing PIT market snapshot")
    aggregates = defaultdict(lambda: {"advance": 0, "decline": 0, "ret_evaluable": 0, "amount_sum": 0.0, "amount_count": 0, "basis": set()})
    sql = """select canonical_security_id, trade_date, qfq_close, amount, price_basis,
                    adjustment_source_revision, adjusted_quality, trading_status
             from read_parquet(?) where board_scope in ('SH_MAIN','SZ_MAIN','CHINEXT','STAR')
             order by canonical_security_id, trade_date"""
    cursor = duckdb.connect().execute(sql, [(ROOT / daily_ref["path"]).as_posix()])
    last = {}
    while block := cursor.fetchmany(50000):
        for sid, raw_day, close, amount, basis, revision, quality, status in block:
            day = f"{raw_day // 10000:04d}-{raw_day // 100 % 100:02d}-{raw_day % 100:02d}"
            current = (day, close, f"{basis}:{revision}" if basis and revision else None, quality, status)
            if sid in members.get(day, ()):
                agg = aggregates[day]
                if status == "ACTUAL_TRADED" and quality == "READY" and amount is not None and math.isfinite(float(amount)) and amount >= 0:
                    agg["amount_sum"] += float(amount)
                    agg["amount_count"] += 1
                previous = last.get(sid)
                if previous and previous[0] == prior_session.get(day):
                    if (previous[4] == status == "ACTUAL_TRADED" and previous[3] == quality == "READY"
                            and previous[2] is not None and previous[2] == current[2]
                            and previous[1] is not None and close is not None and float(previous[1]) > 0):
                        change = float(close) / float(previous[1]) - 1
                        agg["ret_evaluable"] += 1
                        agg["advance"] += int(change > 0)
                        agg["decline"] += int(change < 0)
                        agg["basis"].add((sid, current[2]))
            last[sid] = current
    limits = defaultdict(lambda: {"evaluable": 0, "down": 0})
    with gzip.open(ROOT / limit_ref["path"], "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            day, sid = row["trade_date"], row["security_id"]
            if sid in members.get(day, ()) and row["limit_status"] in {"LIMIT_UP", "LIMIT_DOWN", "NOT_LIMIT"}:
                limits[day]["evaluable"] += 1
                limits[day]["down"] += int(row["limit_status"] == "LIMIT_DOWN")
    source_digest = digest({"head": sha(head_path), "daily": daily_ref["sha256"], "universe": universe_ref["sha256"],
                            "calendar": calendar_ref["sha256"], "price_limit": limit_ref["sha256"], "path": sha(PATH)})
    amounts, levels, previous_stress = [], [], None
    output_rows = []
    calendar_id = f"V4_02_CALENDAR_SHA256:{calendar_ref['sha256']}"
    for index, day in enumerate(sessions):
        agg, lim, count = aggregates[day], limits[day], len(members[day])
        breadth = (agg["advance"] - agg["decline"]) / agg["ret_evaluable"] if agg["ret_evaluable"] else None
        baseline = sum(amounts[-20:]) / 20 if len(amounts) >= 20 and all(x is not None for x in amounts[-20:]) else None
        participation = agg["amount_sum"] / baseline if baseline and agg["amount_count"] else None
        amount_total = agg["amount_sum"] if agg["amount_count"] else None
        limit_coverage = lim["evaluable"] / count if count else None
        stress = lim["down"] / lim["evaluable"] if lim["evaluable"] else None
        level = path_rows[index]["level"]
        levels.append(level)
        ma20 = sum(levels[-20:]) / 20 if len(levels) >= 20 and all(x is not None for x in levels[-20:]) else None
        prior_ma20 = sum(levels[-25:-5]) / 20 if len(levels) >= 25 and all(x is not None for x in levels[-25:-5]) else None
        basis_id = digest(sorted(agg["basis"]))
        identity = {"trade_date": day, "market_calendar_id": calendar_id, "market_snapshot_id": snapshot_ids[day],
                    "adjustment_basis_id": basis_id, "input_source_digest": source_digest}
        axes = market_axis_primitives(breadth=breadth, participation=participation, limit_coverage=limit_coverage,
                                      stress_ratio=stress, prior_stress_ratio=previous_stress, **identity)
        trend = market_trend_axis(index_close=level, index_ma20=ma20, index_ma20_t_minus_5=prior_ma20, **identity)
        raw = {"advance": agg["advance"], "decline": agg["decline"], "breadth_denominator": agg["ret_evaluable"],
               "amount_sum": amount_total, "amount_evaluable_count": agg["amount_count"], "amount_ma20": baseline,
               "limit_down_count": lim["down"], "limit_evaluable_count": lim["evaluable"],
               "limit_coverage": limit_coverage, "stress_ratio": stress, "prior_stress_ratio": previous_stress,
               "index_close": level, "index_ma20": ma20, "index_ma20_t_minus_5": prior_ma20,
               "universe_count": count, "breadth_coverage": agg["ret_evaluable"] / count,
               "amount_coverage": agg["amount_count"] / count, "limit_coverage_denominator": count,
               "index_source": "V4_03_MARKET_REFERENCE_PATH_V1"}
        row = {"trade_date": day, "raw": raw, "identity": identity,
               "parameter_set_id": "V4_03_CORE_FACTOR_PARAMETER_SET_V1",
               "breadth_axis": axes["breadth_axis"], "participation_axis": axes["participation_axis"],
               "stress_level": axes["stress_level"], "stress_change": axes["stress_change"],
               "trend_axis": trend["trend_axis"], "axis_quality": {**axes["field_quality"], "trend_axis": {
                   "quality_state": trend["quality_state"], "unknown_reason": trend["unknown_reason"]}},
               "producer_contracts": {"breadth_axis": axes["contract_id"], "participation_axis": axes["contract_id"],
                                      "stress_level": axes["contract_id"], "stress_change": axes["contract_id"],
                                      "trend_axis": trend["contract_id"]}}
        row["input_digest"] = digest([identity, raw])
        row["output_digest"] = digest(row)
        output_rows.append(row)
        amounts.append(amount_total)
        previous_stress = stress
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    with tmp.open("wb") as raw_stream, gzip.GzipFile(fileobj=raw_stream, mode="wb", filename="", mtime=0, compresslevel=6) as zipped, io.TextIOWrapper(zipped, encoding="utf-8") as stream:
        for row in output_rows:
            stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
    os.replace(tmp, OUTPUT)
    receipt = {"contract_id": "V4_03_MARKET_REGIME_NATIVE_RECEIPT_R3", "status": "CANDIDATE_NOT_STAGE_ACCEPTANCE",
               "rows": len(output_rows), "first_session": sessions[0], "last_session": sessions[-1],
               "output_sha256": sha(OUTPUT), "input_source_digest": source_digest,
               "source_hashes": {"daily": daily_ref["sha256"], "universe": universe_ref["sha256"],
                                  "calendar": calendar_ref["sha256"], "price_limit": limit_ref["sha256"], "path": sha(PATH)},
               "governing_task": "docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md"}
    atomic(RECEIPT, receipt)
    print(json.dumps({"status": receipt["status"], "rows": receipt["rows"], "sha256": receipt["output_sha256"]}))


if __name__ == "__main__":
    main()
