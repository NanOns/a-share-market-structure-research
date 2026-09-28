"""Independent check of the bounded V4-03 daily rebalanced market path."""

from collections import defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import time

import duckdb


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/v4_03/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R1.jsonl.gz"
RECEIPT = ROOT / "reports/v4_03/V4_03_MARKET_PATH_CANDIDATE_RECEIPT_R1.json"
POSTCHECK = ROOT / "reports/v4_03/V4_03_MARKET_PATH_INDEPENDENT_POSTCHECK_R1.json"
REQUIRED = {"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def main():
    started = time.monotonic()
    head_path = ROOT / "data/v4/V4_DEV_BASELINE_HEAD.json"
    head = json.loads(head_path.read_text(encoding="utf-8"))
    bootstrap_path = ROOT / head["bootstrap_manifest"]["path"]
    if head.get("accepted_data_cutoff") != "2026-09-24" or sha(bootstrap_path) != head["bootstrap_manifest"]["sha256"]:
        raise RuntimeError("frozen DEV baseline identity mismatch")
    bootstrap = json.loads(bootstrap_path.read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / bootstrap["parent_artifacts"]["v4_02_manifest"]["path"]).read_text(encoding="utf-8"))
    daily_ref, calendar_ref = manifest["components"]["DAILY_R7"], manifest["components"]["CALENDAR"]
    universe_ref = bootstrap["parent_artifacts"]["v4_01_universe"]
    daily_path, calendar_path, universe_path = ROOT / daily_ref["path"], ROOT / calendar_ref["path"], ROOT / universe_ref["path"]
    for path, ref in ((daily_path, daily_ref), (calendar_path, calendar_ref), (universe_path, universe_ref)):
        if sha(path) != ref["sha256"]:
            raise RuntimeError(f"accepted source digest mismatch: {path.name}")
    sessions = [x for x in json.loads(calendar_path.read_text(encoding="utf-8"))["session_dates"] if x <= head["accepted_data_cutoff"]][-200:]
    session_set = set(sessions)
    universe_by = defaultdict(dict)
    with gzip.open(universe_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["trade_date"] in session_set and row["board_scope"] in REQUIRED:
                universe_by[row["trade_date"]][row["security_id"]] = row
    if any(not universe_by[d] for d in sessions):
        raise RuntimeError("missing PIT snapshot in market path range")
    snapshot_id = {d: digest([(s, x.get("membership_basis"), x.get("source_revision_id"), x.get("eligibility_status"))
                              for s, x in sorted(universe_by[d].items())]) for d in sessions}
    all_members = set().union(*(set(universe_by[d]) for d in sessions))
    first_day, last_day = sessions[0], sessions[-1]
    sql = """select canonical_security_id, trade_date, qfq_close, price_basis, adjustment_source_revision,
                     adjusted_quality, trading_status
              from read_parquet(?) where trade_date between ? and ?
                and board_scope in ('SH_MAIN','SZ_MAIN','CHINEXT','STAR')"""
    conn = duckdb.connect()
    cursor = conn.execute(sql, [daily_path.as_posix(), int(first_day.replace("-", "")), int(last_day.replace("-", ""))])
    daily = {}
    rows_in = 0
    while block := cursor.fetchmany(50000):
        for sid, raw_day, close, basis, revision, quality, status in block:
            if sid not in all_members:
                continue
            rows_in += 1
            day = f"{raw_day // 10000:04d}-{raw_day // 100 % 100:02d}-{raw_day % 100:02d}"
            daily[(sid, day)] = {"close": close, "basis": f"{basis}:{revision}" if basis and revision else None,
                                 "quality": quality, "daily_status": status}
    status_path = ROOT / "data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz"
    status_by = defaultdict(dict)
    with gzip.open(status_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["security_id"] in all_members and first_day <= row["trade_date"] <= last_day:
                status_by[row["security_id"]][row["trade_date"]] = row["status"]
    parameters = json.loads((ROOT / "config/v4_03_parameter_registry_v1.json").read_text(encoding="utf-8"))
    threshold = next(p["value"] for p in parameters["entries"] if p["parameter_id"] == "V4_03_MARKET_REFERENCE_MAX_MISSING_FRACTION")
    source_digest = digest({"dev_baseline": sha(head_path), "daily": daily_ref["sha256"], "universe": universe_ref["sha256"],
                           "calendar": calendar_ref["sha256"], "trading_status": sha(status_path), "sessions": sessions})
    expected = [{"trade_date": sessions[0], "start_session": None, "end_session": sessions[0],
                 "reference_return": None, "level": 1.0, "quality_state": "OBSERVED",
                 "unknown_reason": None, "universe_count": len(universe_by[sessions[0]]),
                 "evaluable_count": None, "missing_count": None, "coverage": None,
                 "start_universe_snapshot_id": snapshot_id[sessions[0]], "evaluable_set_identity": None,
                 "adjustment_basis_id": None}]
    previous_level, broken = 1.0, False
    for index in range(1, len(sessions)):
        start, end = sessions[index - 1], sessions[index]
        members = sorted(universe_by[start])
        returns, bases = {}, set()
        for sid in members:
            left, right = daily.get((sid, start)), daily.get((sid, end))
            if (left is None or right is None or status_by[sid].get(start) != "ACTUAL_TRADED"
                    or status_by[sid].get(end) != "ACTUAL_TRADED" or left["daily_status"] != "ACTUAL_TRADED"
                    or right["daily_status"] != "ACTUAL_TRADED" or left["quality"] != "READY" or right["quality"] != "READY"
                    or left["basis"] is None or left["basis"] != right["basis"] or left["close"] is None
                    or right["close"] is None or float(left["close"]) <= 0):
                returns[sid] = None
            else:
                returns[sid] = float(right["close"]) / float(left["close"]) - 1
                bases.add((sid, left["basis"]))
        evaluable = {s: r for s, r in returns.items() if r is not None and math.isfinite(r)}
        missing = len(members) - len(evaluable)
        coverage = len(evaluable) / len(members) if members else None
        reason = "EMPTY_START_UNIVERSE" if not members else "MISSING_COVERAGE_EXCEEDED" if missing / len(members) > threshold else None
        ref = sum(evaluable.values()) / len(evaluable) if evaluable and reason is None else None
        if ref is None or ref <= -1:
            broken, previous_level = True, None
        elif not broken:
            previous_level *= 1 + ref
        expected.append({"trade_date": end, "start_session": start, "end_session": end,
                         "reference_return": ref, "level": previous_level,
                         "quality_state": "OBSERVED" if previous_level is not None else "UNKNOWN",
                         "unknown_reason": None if previous_level is not None else "DAILY_RETURN_UNKNOWN_BREAKS_SERIES_SUFFIX",
                         "daily_return_quality_state": "UNKNOWN" if reason else "OBSERVED",
                         "daily_return_unknown_reason": reason,
                         "universe_count": len(members), "evaluable_count": len(evaluable),
                         "missing_count": missing, "coverage": coverage,
                         "evaluable_set_identity": digest(sorted(evaluable)),
                         "start_universe_snapshot_id": snapshot_id[start],
                         "adjustment_basis_id": digest(sorted(bases))})
    found = []
    with gzip.open(OUTPUT, "rt", encoding="utf-8") as stream:
        found = [json.loads(line) for line in stream]
    candidate_sha = sha(OUTPUT)
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    mismatches, samples = 0, []
    for idx, (want, got) in enumerate(zip(expected, found)):
        check_fields = ("trade_date", "start_session", "end_session", "reference_return", "level", "quality_state",
                        "unknown_reason", "universe_count", "evaluable_count", "missing_count", "coverage",
                        "start_universe_snapshot_id", "evaluable_set_identity", "adjustment_basis_id")
        bad = []
        for key in check_fields:
            a, b = want.get(key), got.get(key)
            if isinstance(a, float):
                if b is None or not math.isclose(a, float(b), rel_tol=1e-12, abs_tol=1e-12):
                    bad.append(key)
            elif a != b:
                bad.append(key)
        if got.get("input_source_digest") != source_digest:
            bad.append("input_source_digest")
        if got.get("contract_id") != "V4_03_MARKET_REFERENCE_PATH_V1" or got.get("path_identity") != "DAILY_REBALANCED_RESEARCH_INDEX":
            bad.append("contract_identity")
        if len(got.get("input_digest", "")) != 64 or len(got.get("window_identity", "")) != 64:
            bad.append("digest_shape")
        output_without_digest = dict(got)
        stored_output_digest = output_without_digest.pop("output_digest", None)
        if stored_output_digest != digest(output_without_digest):
            bad.append("output_digest")
        if bad:
            mismatches += 1
            if len(samples) < 20:
                samples.append({"row": idx, "fields": bad, "date": got.get("trade_date")})
    status = "PASS" if len(expected) == len(found) == len(sessions) and mismatches == 0 and candidate_sha == receipt.get("output_sha256") else "FAIL"
    report = {"contract_id": "V4_03_MARKET_PATH_INDEPENDENT_POSTCHECK_R1", "status": status,
              "scope": "INDEPENDENT_MARKET_PATH_CANDIDATE_POSTCHECK_NOT_STAGE_ACCEPTANCE",
              "cutoff": last_day, "rows_checked": len(found), "expected_rows": len(expected), "rows_in": rows_in,
              "candidate_output_sha256": candidate_sha, "receipt_sha_match": candidate_sha == receipt.get("output_sha256"),
              "input_source_digest": source_digest, "mismatch_rows": mismatches, "mismatch_samples": samples,
              "formula": "PIT-start-universe equal-weight daily return then chained product; no current-survivor substitution",
              "rebase_policy": "UNKNOWN_SUFFIX_UNTIL_NEW_SERIES_VERSION",
              "tolerance": "numeric abs/rel tolerance 1e-12", "elapsed_seconds": round(time.monotonic() - started, 3),
              "scanner_run_count": 0, "trading_run_count": 0, "tdx_root_write_count": 0,
              "evidence_origin": "DIAGNOSTIC_NON_PIT"}
    POSTCHECK.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "rows_checked": len(found), "mismatch_rows": mismatches,
                      "elapsed_seconds": report["elapsed_seconds"]}))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
