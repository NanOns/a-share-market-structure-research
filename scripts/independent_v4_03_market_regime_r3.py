"""Independent full-session replay of V4-03 market regime primitive inputs."""

from collections import defaultdict
import gzip
import hashlib
import json
import math
import os
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "reports/v4_03/staging/V4_03_MARKET_REGIME_NATIVE_CANDIDATE_R3.jsonl.gz"
RECEIPT = ROOT / "reports/v4_03/V4_03_MARKET_REGIME_NATIVE_RECEIPT_R3.json"
OUTPUT = ROOT / "reports/v4_03/V4_03_MARKET_REGIME_NATIVE_INDEPENDENT_POSTCHECK_R3.json"
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


def same(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    return a == b


def main():
    head_path = ROOT / "data/v4/V4_DEV_BASELINE_HEAD.json"
    head = json.loads(head_path.read_text(encoding="utf-8"))
    bootstrap = json.loads((ROOT / head["bootstrap_manifest"]["path"]).read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / bootstrap["parent_artifacts"]["v4_02_manifest"]["path"]).read_text(encoding="utf-8"))
    daily_ref, calendar_ref, limit_ref = (manifest["components"][key] for key in ("DAILY_R7", "CALENDAR", "FROZEN_R3_BASE"))
    universe_ref = bootstrap["parent_artifacts"]["v4_01_universe"]
    if any(sha(ROOT / ref["path"]) != ref["sha256"] for ref in (daily_ref, calendar_ref, limit_ref, universe_ref)):
        raise RuntimeError("accepted source digest mismatch")
    found = [json.loads(line) for line in gzip.open(CANDIDATE, "rt", encoding="utf-8")]
    path_rows = [json.loads(line) for line in gzip.open(PATH, "rt", encoding="utf-8")]
    days = [row["trade_date"] for row in path_rows]
    candidate_sha = sha(CANDIDATE)
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    members, parts = defaultdict(set), defaultdict(list)
    day_set = set(days)
    with gzip.open(ROOT / universe_ref["path"], "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            day = row["trade_date"]
            if day in day_set and row["board_scope"] in REQUIRED:
                sid = row["security_id"]
                members[day].add(sid)
                parts[day].append((sid, row.get("membership_basis"), row.get("source_revision_id"), row.get("eligibility_status")))
    snapshots = {day: digest(sorted(parts[day])) for day in days}
    limits = defaultdict(lambda: [0, 0])
    with gzip.open(ROOT / limit_ref["path"], "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            day, sid = row["trade_date"], row["security_id"]
            if sid in members.get(day, ()) and row["limit_status"] in {"LIMIT_UP", "LIMIT_DOWN", "NOT_LIMIT"}:
                limits[day][0] += 1
                limits[day][1] += row["limit_status"] == "LIMIT_DOWN"
    # This read order differs from the producer's security-major scan. Each
    # day uses only the immediately preceding accepted market session.
    sql = """select canonical_security_id, trade_date, qfq_close, amount, price_basis,
                    adjustment_source_revision, adjusted_quality, trading_status
             from read_parquet(?) where board_scope in ('SH_MAIN','SZ_MAIN','CHINEXT','STAR')
             order by trade_date, canonical_security_id"""
    cursor = duckdb.connect().execute(sql, [(ROOT / daily_ref["path"]).as_posix()])
    aggregates = defaultdict(lambda: [0, 0, 0, 0.0, 0, set()])
    previous, current, current_day = {}, {}, None
    prior_day = {days[i]: days[i-1] for i in range(1, len(days))}
    while block := cursor.fetchmany(50000):
        for sid, raw_day, close, amount, basis, revision, quality, status in block:
            day = f"{raw_day // 10000:04d}-{raw_day // 100 % 100:02d}-{raw_day % 100:02d}"
            if day != current_day:
                previous, current, current_day = current, {}, day
            coord = f"{basis}:{revision}" if basis and revision else None
            current[sid] = (close, coord, quality, status)
            if sid not in members.get(day, ()):
                continue
            acc = aggregates[day]
            if quality == "READY" and status == "ACTUAL_TRADED" and amount is not None and math.isfinite(float(amount)) and amount >= 0:
                acc[3] += float(amount)
                acc[4] += 1
            prev = previous.get(sid)
            if prev and prior_day.get(day) and prev[1] == coord and coord and prev[2] == quality == "READY" and prev[3] == status == "ACTUAL_TRADED" and prev[0] and close is not None and float(prev[0]) > 0:
                change = float(close)/float(prev[0]) - 1
                acc[0] += change > 0
                acc[1] += change < 0
                acc[2] += 1
                acc[5].add((sid, coord))
    thresholds = json.loads((ROOT / "config/v4_03_parameter_set_v1.json").read_text(encoding="utf-8"))["engineering_candidate_thresholds"]
    source_digest = digest({"head": sha(head_path), "daily": daily_ref["sha256"], "universe": universe_ref["sha256"],
                            "calendar": calendar_ref["sha256"], "price_limit": limit_ref["sha256"], "path": sha(PATH)})
    amounts, levels, previous_stress, mismatches, samples = [], [], None, 0, []
    calendar_id = f"V4_02_CALENDAR_SHA256:{calendar_ref['sha256']}"
    for i, (day, row) in enumerate(zip(days, found)):
        advance, decline, ret_count, amount_sum, amount_count, basis_set = aggregates[day]
        limit_count, down = limits[day]
        count = len(members[day])
        level = path_rows[i]["level"]
        levels.append(level)
        baseline = sum(amounts[-20:])/20 if len(amounts) >= 20 and all(x is not None for x in amounts[-20:]) else None
        ma = sum(levels[-20:])/20 if len(levels) >= 20 and all(x is not None for x in levels[-20:]) else None
        old_ma = sum(levels[-25:-5])/20 if len(levels) >= 25 and all(x is not None for x in levels[-25:-5]) else None
        stress = down/limit_count if limit_count else None
        raw = {"advance": advance, "decline": decline, "breadth_denominator": ret_count,
               "amount_sum": amount_sum if amount_count else None, "amount_evaluable_count": amount_count,
               "amount_ma20": baseline, "limit_down_count": down, "limit_evaluable_count": limit_count,
               "limit_coverage": limit_count/count, "stress_ratio": stress, "prior_stress_ratio": previous_stress,
               "index_close": level, "index_ma20": ma, "index_ma20_t_minus_5": old_ma,
               "universe_count": count, "breadth_coverage": ret_count/count,
               "amount_coverage": amount_count/count, "limit_coverage_denominator": count,
               "index_source": "V4_03_MARKET_REFERENCE_PATH_V1"}
        breadth = (advance-decline)/ret_count if ret_count else None
        participation = amount_sum/baseline if baseline and amount_count else None
        coverage = limit_count/count
        axes = {"breadth_axis": ("IMPROVING" if breadth > thresholds["market_breadth_axis"] else "DETERIORATING" if breadth < -thresholds["market_breadth_axis"] else "STABLE") if breadth is not None else None,
                "participation_axis": ("EXPANDING" if participation >= thresholds["market_participation_expanding"] else "THIN" if participation < thresholds["market_participation_thin"] else "NORMAL") if participation is not None else None,
                "stress_level": ("HIGH" if stress >= thresholds["market_stress_high"] else "ELEVATED" if stress >= thresholds["market_stress_elevated"] else "LOW") if stress is not None and coverage >= thresholds["market_stress_min_limit_coverage"] else None,
                "stress_change": ("RISING" if stress > previous_stress else "DECLINING" if stress < previous_stress else "STABLE") if stress is not None and previous_stress is not None else None,
                "trend_axis": "UNKNOWN" if level is None or ma is None or old_ma is None else "STRONG" if level > ma > old_ma else "WEAK" if level < ma < old_ma else "NEUTRAL"}
        identity = {"trade_date": day, "market_calendar_id": calendar_id, "market_snapshot_id": snapshots[day],
                    "adjustment_basis_id": digest(sorted(basis_set)), "input_source_digest": source_digest}
        bad = [key for key, value in raw.items() if not same(value, row["raw"].get(key))]
        bad += [key for key, value in axes.items() if row.get(key) != value]
        if row.get("identity") != identity or row.get("input_digest") != digest([identity, raw]):
            bad.append("input_identity")
        if row.get("output_digest") != digest({k: v for k, v in row.items() if k != "output_digest"}):
            bad.append("output_digest")
        if bad:
            mismatches += 1
            if len(samples) < 20:
                samples.append({"trade_date": day, "fields": bad})
        amounts.append(amount_sum if amount_count else None)
        previous_stress = stress
    status = "PASS" if len(found) == len(days) and not mismatches and receipt["output_sha256"] == candidate_sha else "FAIL"
    report = {"contract_id": "V4_03_MARKET_REGIME_NATIVE_INDEPENDENT_POSTCHECK_R3", "status": status,
              "rows_checked": len(found), "expected_sessions": len(days), "mismatch_rows": mismatches,
              "mismatch_samples": samples, "candidate_sha256": candidate_sha,
              "candidate_receipt_sha_match": receipt["output_sha256"] == candidate_sha,
              "source_digest": source_digest, "governing_task": "docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md",
              "independent_producer_imports": []}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, OUTPUT)
    print(json.dumps({"status": status, "rows": len(found), "mismatches": mismatches}))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
