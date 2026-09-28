"""Integrate 39 core + 8 PIT relative fields at the frozen 2026-09-24 cutoff.

This creates an unaccepted candidate. All inputs remain immutable accepted V4-01/V4-02 data.
"""

from collections import Counter, defaultdict
import argparse
from dataclasses import asdict
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import threading
import time

import duckdb
import psutil

from src.v4.factors import Bar
from src.v4.factors.core import rps_midrank
from src.v4.factors.relative import relative_factors
from scripts.build_v4_03_prior_rps_staging import validate_artifact


ROOT = Path(__file__).resolve().parents[1]
CORE_RECEIPT = ROOT / "reports/v4_03/V4_03_CORE_REQUIRED_SCOPE_DIAGNOSTIC_RECEIPT_R1.json"
CORE_DATA = ROOT / "reports/v4_03/staging/V4_03_CORE_REQUIRED_SCOPE_DIAGNOSTIC_R1.jsonl.gz"
OUTPUT = ROOT / "reports/v4_03/staging/V4_03_FULL_SCOPE_CANDIDATE_R1.jsonl.gz"
REFERENCES = ROOT / "reports/v4_03/V4_03_MARKET_REFERENCE_CANDIDATE_R1.json"
RECEIPT = ROOT / "reports/v4_03/V4_03_FULL_SCOPE_CANDIDATE_RECEIPT_R1.json"
MARKET_PATH = ROOT / "reports/v4_03/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R1.jsonl.gz"
MARKET_PATH_RECEIPT = ROOT / "reports/v4_03/V4_03_MARKET_PATH_CANDIDATE_RECEIPT_R1.json"
REQUIRED = {"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"}
SNAPSHOT_OFFSETS = (0, 1, 3, 5, 20, 6, 8, 23)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def hash_object(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes((json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"))
    os.replace(temp, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-history", action="store_true", help="Use the full accepted daily history core candidate")
    parser.add_argument("--r3", action="store_true", help="Consume stage-owned prior RPS and full historical market path")
    args = parser.parse_args()
    suffix = "R3" if args.r3 else "R2" if args.full_history else "R1"
    core_receipt_path = ROOT / ("reports/v4_03/V4_03_CORE_FULL_HISTORY_CANDIDATE_RECEIPT_R2.json" if args.full_history or args.r3 else "reports/v4_03/V4_03_CORE_REQUIRED_SCOPE_DIAGNOSTIC_RECEIPT_R1.json")
    core_data_path = ROOT / ("reports/v4_03/staging/V4_03_CORE_FULL_HISTORY_CANDIDATE_R2.jsonl.gz" if args.full_history or args.r3 else "reports/v4_03/staging/V4_03_CORE_REQUIRED_SCOPE_DIAGNOSTIC_R1.jsonl.gz")
    output_path = ROOT / f"reports/v4_03/staging/V4_03_FULL_SCOPE_CANDIDATE_{suffix}.jsonl.gz"
    references_path = ROOT / f"reports/v4_03/V4_03_MARKET_REFERENCE_CANDIDATE_{suffix}.json"
    receipt_path = ROOT / f"reports/v4_03/V4_03_FULL_SCOPE_CANDIDATE_RECEIPT_{suffix}.json"
    market_path = ROOT / f"reports/v4_03/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_{suffix}.jsonl.gz"
    market_path_receipt = ROOT / ("reports/v4_03/V4_03_MARKET_REFERENCE_PATH_RECEIPT_R3.json" if args.r3 else f"reports/v4_03/V4_03_MARKET_PATH_CANDIDATE_RECEIPT_{suffix}.json")
    core_receipt = json.loads(core_receipt_path.read_text(encoding="utf-8"))
    if sha(core_data_path) != core_receipt["output_sha256"]:
        raise RuntimeError("core candidate digest mismatch")
    started = time.monotonic()
    process = psutil.Process()
    cpu_started = process.cpu_times()
    peak_rss = [process.memory_info().rss]
    sample_stop = threading.Event()

    def sample_memory():
        while not sample_stop.wait(0.05):
            try:
                peak_rss[0] = max(peak_rss[0], process.memory_info().rss)
            except psutil.Error:
                return

    sampler = threading.Thread(target=sample_memory, name="v4-03-memory-sampler", daemon=True)
    sampler.start()
    head_path = ROOT / "data/v4/V4_DEV_BASELINE_HEAD.json"
    head = json.loads(head_path.read_text(encoding="utf-8"))
    if head["accepted_data_cutoff"] != "2026-09-24":
        raise RuntimeError("frozen DEV baseline cutoff changed")
    bootstrap_path = ROOT / head["bootstrap_manifest"]["path"]
    if sha(bootstrap_path) != head["bootstrap_manifest"]["sha256"]:
        raise RuntimeError("DEV baseline bootstrap digest mismatch")
    bootstrap = json.loads(bootstrap_path.read_text(encoding="utf-8"))
    manifest_path = ROOT / bootstrap["parent_artifacts"]["v4_02_manifest"]["path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    daily_ref = manifest["components"]["DAILY_R7"]
    daily_path = ROOT / daily_ref["path"]
    universe_ref = bootstrap["parent_artifacts"]["v4_01_universe"]
    universe_path = ROOT / universe_ref["path"]
    calendar_ref = manifest["components"]["CALENDAR"]
    calendar_path = ROOT / calendar_ref["path"]
    if sha(daily_path) != daily_ref["sha256"] or sha(universe_path) != universe_ref["sha256"] or sha(calendar_path) != calendar_ref["sha256"]:
        raise RuntimeError("accepted V4-01/V4-02 input digest mismatch")
    status_path = ROOT / "data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz"
    calendar = [d for d in json.loads(calendar_path.read_text(encoding="utf-8"))["session_dates"]
                if d <= head["accepted_data_cutoff"]]
    cutoff_index = calendar.index(head["accepted_data_cutoff"])
    dates = {offset: calendar[cutoff_index - offset] for offset in SNAPSHOT_OFFSETS}
    selected_dates = set(dates.values())

    snapshots: dict[str, dict] = defaultdict(dict)
    with gzip.open(universe_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["trade_date"] in selected_dates and row["board_scope"] in REQUIRED:
                date = row["trade_date"]
                sid = row["security_id"]
                if sid in snapshots[date]:
                    raise RuntimeError(f"duplicate PIT universe member {sid} at {date}")
                snapshots[date][sid] = row
    if any(not snapshots[d] for d in selected_dates):
        raise RuntimeError("required PIT snapshot missing")
    snapshot_ids = {d: hash_object([(sid, row.get("membership_basis"), row.get("source_revision_id"), row.get("eligibility_status"))
                                    for sid, row in sorted(snapshots[d].items())]) for d in selected_dates}
    target_ids = set().union(*(set(snapshots[d]) for d in selected_dates))

    endpoint_days = sorted(set(selected_dates))
    query = """select canonical_security_id, trade_date, qfq_open, qfq_high, qfq_low,
                       qfq_close, amount, volume, price_basis, adjustment_source_revision,
                       adjusted_quality, trading_status, board_scope
                from read_parquet(?) where trade_date between ? and ?
                  and board_scope in ('SH_MAIN','SZ_MAIN','CHINEXT','STAR')"""
    endpoint_rows = duckdb.connect().execute(
        query, [daily_path.as_posix(), int(min(selected_dates).replace("-", "")),
                int(head["accepted_data_cutoff"].replace("-", ""))]).fetchall()
    daily: dict[tuple[str, str], dict] = {}
    for row in endpoint_rows:
        sid, day, op, hi, lo, cl, amount, volume, basis, revision, quality, trading_status, board = row
        if sid not in target_ids:
            continue
        date = f"{day // 10000:04d}-{day // 100 % 100:02d}-{day % 100:02d}"
        daily[(sid, date)] = {"open": op, "high": hi, "low": lo, "close": cl, "amount": amount,
                              "volume": volume, "basis": f"{basis}:{revision}" if basis and revision else None,
                              "quality": quality, "status": trading_status, "board": board}

    earliest = min(selected_dates)
    status: dict[tuple[str, str], str] = {}
    with gzip.open(status_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if earliest <= row["trade_date"] <= head["accepted_data_cutoff"] and row["security_id"] in target_ids:
                status[(row["security_id"], row["trade_date"])] = row["status"]

    def endpoint_bar(sid: str, date: str) -> tuple[dict | None, str | None]:
        value = daily.get((sid, date))
        state = status.get((sid, date))
        if state != "ACTUAL_TRADED":
            return None, "MISSING_OR_SUSPENDED_ENDPOINT"
        if value is None or value["quality"] != "READY":
            return None, "ADJUSTMENT_UNKNOWN"
        if value["close"] is None or value["basis"] is None:
            return None, "ADJUSTMENT_OR_SOURCE_IDENTITY_UNKNOWN"
        return value, None

    def session_return(sid: str, start_offset: int, end_offset: int) -> tuple[float | None, str | None, str | None]:
        start_date, end_date = dates[start_offset], dates[end_offset]
        start_row, reason = endpoint_bar(sid, start_date)
        if reason:
            return None, reason, None
        end_row, reason = endpoint_bar(sid, end_date)
        if reason:
            return None, reason, start_row["basis"]
        if start_row["basis"] != end_row["basis"]:
            return None, "MIXED_ADJUSTMENT_IDENTITY", None
        a, b = calendar.index(start_date), calendar.index(end_date)
        for date in calendar[a + 1:b]:
            state = status.get((sid, date))
            if state == "SUSPENDED":
                continue
            if state != "ACTUAL_TRADED":
                return None, "UNEXPLAINED_DATA_GAP", start_row["basis"]
            bar = daily.get((sid, date))
            if bar is None or bar["quality"] != "READY" or bar["basis"] != start_row["basis"]:
                return None, "UNEXPLAINED_DATA_GAP", start_row["basis"]
        if float(start_row["close"]) <= 0:
            return None, "NONPOSITIVE_PRICE", start_row["basis"]
        return float(end_row["close"]) / float(start_row["close"]) - 1, None, start_row["basis"]

    # The ids below mean current as-of t; integer horizon maps to t-N.
    date_map = {head["accepted_data_cutoff"]: {h: dates[h] for h in (1, 3, 5, 20)} | {-1: dates[1], -3: dates[3]}}
    current = {h: {} for h in (1, 3, 5, 20)}
    basis_pairs = set()
    current_members = set(snapshots[head["accepted_data_cutoff"]])
    for sid in target_ids:
        for h in (1, 3, 5, 20):
            ret, reason, basis = session_return(sid, h, 0)
            current[h][sid] = ret
            if basis:
                basis_pairs.add((sid, basis))

    historical_rps = {1: {}, 3: {}}
    prior_digests = {1: {}, 3: {}}
    prior_universe_ids = {1: {}, 3: {}}
    prior_specs = ((1, 5, 1, 6), (3, 5, 3, 8), (3, 20, 3, 23))
    prior_artifact_sha = None
    if args.r3:
        prior_path = ROOT / "reports/v4_03/staging/V4_03_PRIOR_RPS_STAGING_R3.json"
        prior_artifact, prior_artifact_sha = validate_artifact(
            prior_path, ROOT / "reports/v4_03/V4_03_PRIOR_RPS_STAGING_RECEIPT_R3.json")
        prior_rows = {(row["trade_date"], row["field_id"]): row for row in prior_artifact["rows"]}
        for offset, horizon, snapshot_offset, start_offset in prior_specs:
            snap_date, field = dates[snapshot_offset], f"rps{horizon}"
            row = prior_rows[(snap_date, field)]
            if row["universe_snapshot_id"] != snapshot_ids[snap_date] or row["output_digest"] != hash_object({k: v for k, v in row.items() if k != "output_digest"}):
                raise RuntimeError("prior RPS PIT identity or row digest mismatch")
            historical_rps[offset][field] = dict(row["scores"])
            prior_digests[offset][field] = hash_object([prior_artifact_sha, row["output_digest"]])
            prior_universe_ids[offset][field] = row["universe_snapshot_id"]
            for sid in snapshots[snap_date]:
                _, _, basis = session_return(sid, start_offset, snapshot_offset)
                if basis:
                    basis_pairs.add((sid, basis))
    else:
        for offset, horizon, snapshot_offset, start_offset in prior_specs:
            snap_date = dates[snapshot_offset]
            members = sorted(snapshots[snap_date])
            returns = {}
            for sid in members:
                returns[sid], _, basis = session_return(sid, start_offset, snapshot_offset)
                if basis:
                    basis_pairs.add((sid, basis))
            scores, _ = rps_midrank(returns, members)
            field = f"rps{horizon}"
            historical_rps[offset][field] = scores
            prior_digests[offset][field] = hash_object({"origin": "DIAGNOSTIC_NON_PIT_RECOMPUTED",
                                                        "trade_date": snap_date, "members": members,
                                                        "scores": sorted(scores.items()),
                                                        "universe_snapshot_id": snapshot_ids[snap_date],
                                                        "daily_sha256": daily_ref["sha256"]})
            prior_universe_ids[offset][field] = snapshot_ids[snap_date]

    basis_identity = hash_object(sorted(basis_pairs))
    source_digest = hash_object({"dev_baseline": sha(head_path), "universe": universe_ref["sha256"],
                                 "daily": daily_ref["sha256"], "calendar": calendar_ref["sha256"],
                                 "trading_status": sha(status_path), "endpoint_dates": endpoint_days})
    current_universe_id = snapshot_ids[head["accepted_data_cutoff"]]
    relative, market_refs = relative_factors(
        current_returns=current, historical_rps=historical_rps, asof_universe=sorted(current_members),
        start_universes={h: sorted(snapshots[dates[h]]) for h in (1, 3, 5)},
        asof_trade_date=head["accepted_data_cutoff"], session_dates=date_map,
        market_calendar_id=f"V4_02_CALENDAR_SHA256:{calendar_ref['sha256']}",
        universe_snapshot_id=current_universe_id,
        start_universe_snapshot_ids={h: snapshot_ids[dates[h]] for h in (1, 3, 5)},
        adjustment_basis_id=basis_identity, input_source_digest=source_digest,
        prior_rps_artifact_digests=prior_digests,
        prior_rps_universe_snapshot_ids=prior_universe_ids)

    core_rows = {}
    with gzip.open(core_data_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            core_rows[row["security_id"]] = row
    if set(core_rows) != current_members:
        raise RuntimeError("core diagnostic member set differs from current required PIT universe")
    field_quality = Counter()
    temp = output_path.with_suffix(output_path.suffix + ".tmp")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with temp.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0, compresslevel=6) as zipped, io.TextIOWrapper(zipped, encoding="utf-8") as stream:
        for sid, core_row in sorted(core_rows.items()):
            fields = dict(core_row["fields"])
            fields.update({name: value.to_dict() for name, value in relative[sid].items()})
            if len(fields) != 47:
                raise RuntimeError(f"expected 47 fields for {sid}, found {len(fields)}")
            for name, value in fields.items():
                field_quality[(name, value["quality_state"])] += 1
            row = {"security_id": sid, "trade_date": head["accepted_data_cutoff"],
                   "board_scope": core_row["board_scope"], "membership_basis": snapshots[head["accepted_data_cutoff"]][sid]["membership_basis"],
                   "evidence_origin": "V4_03_PIT_STAGING_CANDIDATE" if args.r3 else "DIAGNOSTIC_NON_PIT", "universe_snapshot_id": current_universe_id,
                   "source_digest": source_digest, "fields": fields}
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
    for attempt in range(20):
        try:
            os.replace(temp, output_path)
            break
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(.5)
    references = {"contract_id": f"V4_03_MARKET_REFERENCE_CANDIDATE_{suffix}", "as_of": head["accepted_data_cutoff"],
                  "evidence_origin": "V4_03_PIT_STAGING_CANDIDATE" if args.r3 else "DIAGNOSTIC_NON_PIT", "market_references": market_refs,
                  "input_source_digest": source_digest,
                  "market_path_status": "NOT_COMPUTED_HISTORICAL_DAILY_CHAIN_PENDING",
                  "forward_benchmark_published": False}
    if market_path.exists() and market_path_receipt.exists():
        path_receipt = json.loads(market_path_receipt.read_text(encoding="utf-8"))
        if sha(market_path) != path_receipt.get("output_sha256"):
            raise RuntimeError("market path candidate digest mismatch")
        references["market_path"] = {"contract_id": "V4_03_MARKET_REFERENCE_PATH_V1",
                                     "series_version": path_receipt["series_version"],
                                     "path_identity": path_receipt["path_identity"],
                                     "rows": path_receipt["sessions"],
                                     "output_sha256": path_receipt["output_sha256"],
                                     "status": path_receipt["status"]}
        references["market_path_status"] = path_receipt["status"]
    atomic_json(references_path, references)
    elapsed = time.monotonic() - started
    sample_stop.set()
    sampler.join(timeout=1)
    cpu_ended = process.cpu_times()
    cpu_seconds = (cpu_ended.user + cpu_ended.system) - (cpu_started.user + cpu_started.system)
    memory = process.memory_info()
    logical_cpus = os.cpu_count() or 1
    measurement = {"factor_compute_time_seconds": round(elapsed, 3),
                   "stage_wall_time_seconds": round(elapsed, 3),
                   "process_cpu_seconds": round(cpu_seconds, 3),
                   "process_cpu_percent_of_one_logical_cpu": round(cpu_seconds / elapsed * 100, 2) if elapsed else 0,
                   "process_cpu_percent_of_host_capacity": round(cpu_seconds / elapsed / logical_cpus * 100, 2) if elapsed else 0,
                   "sampled_peak_rss_bytes": peak_rss[0],
                   "os_peak_working_set_bytes": getattr(memory, "peak_wset", None),
                   "hardware": {"platform": platform.platform(), "processor": platform.processor(),
                                "logical_cpu_count": logical_cpus},
                   "cache_state": "OS_AND_DUCKDB_CACHE_NOT_CONTROLLED_OR_CLEARED",
                   "dataset_identity": source_digest}
    receipt = {"contract_id": f"V4_03_FULL_SCOPE_CANDIDATE_RECEIPT_{suffix}",
               "status": "FULL_47_FIELD_CANDIDATE_NOT_STAGE_ACCEPTANCE",
               "cutoff": head["accepted_data_cutoff"], "rows_out": len(core_rows), "field_count": 47,
               "board_count": {k: v for k, v in sorted(Counter(x["board_scope"] for x in core_rows.values()).items())},
               "field_quality_count": {f"{k[0]}:{k[1]}": v for k, v in sorted(field_quality.items())},
               "required_scope_member_set_identity": current_universe_id,
               "adjustment_basis_set_identity": basis_identity,
               "input_source_digest": source_digest, "output_sha256": sha(output_path),
               "references_sha256": sha(references_path), "elapsed_seconds": round(elapsed, 3),
               "performance_measurement": measurement,
               "market_path_candidate_sha256": sha(market_path) if market_path.exists() else None,
               "prior_rps_origin": "DIAGNOSTIC_NON_PIT_RECOMPUTED_NOT_PREVIOUSLY_ACCEPTED",
               "limitations": ["No accepted sector membership input or sector full-market materialization",
                               "Full historical Data/Factor Replay Gate remains V4-05 scope" if args.r3 else "Core uses all accepted daily sessions for the cutoff candidate, but first availability was not replayed at every historical as-of date" if args.full_history else "Core stock history is a 200-session bounded diagnostic, not full historical replay",
                               "No accepted publication or final stage receipt"]}
    receipt["core_candidate_sha256"] = core_receipt["output_sha256"]
    if args.r3:
        receipt["evidence_origin"] = "V4_03_PIT_STAGING_CANDIDATE"
        receipt["prior_rps_origin"] = "V4_03_STAGE_OWNED_HISTORICAL_STAGING_R3"
        receipt["prior_rps_artifact_sha256"] = prior_artifact_sha
        receipt["governing_task"] = "docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md"
    atomic_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "rows_out": receipt["rows_out"],
                      "field_count": receipt["field_count"], "elapsed_seconds": receipt["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
