from __future__ import annotations

"""Classify R6.2 daily membership rows using local bar presence and bounded status queries."""

import argparse
import gzip
import hashlib
import json
import os
import socket
import sys
import tempfile
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import RequestBudget  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", default="data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz")
    parser.add_argument("--output", default="data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R6_2_20260926.jsonl.gz")
    parser.add_argument("--receipt", default="reports/v4_02/V4_02_DATED_TRADING_STATUS_R6_2_20260926.json")
    parser.add_argument("--contract", default="config/v4_02_dated_trading_status_v1.json")
    parser.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    parser.add_argument("--offline-facts", help="Use an already captured normalized status fact file; do not call BaoStock.")
    parser.add_argument("--max-securities", type=int, default=0, help="Diagnostic bound; any nonzero value cannot pass acceptance.")
    args = parser.parse_args()

    universe_path = ROOT / args.universe
    output_path = ROOT / args.output
    receipt_path = ROOT / args.receipt
    contract_path = ROOT / args.contract
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    sha = {"universe": sha256(universe_path), "contract": sha256(contract_path)}
    missing: dict[str, set[str]] = defaultdict(set)
    first_last: dict[str, list[str]] = {}
    membership_count = actual_bar_count = 0
    with gzip.open(universe_path, "rt", encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            membership_count += 1
            code = row["source_security_key"].lower().replace(".", ".", 1)
            date = row["trade_date"]
            if row.get("source_bar_present") is True:
                actual_bar_count += 1
            else:
                missing[code].add(date)
                bounds = first_last.setdefault(code, [date, date])
                bounds[0] = min(bounds[0], date)
                bounds[1] = max(bounds[1], date)

    codes = sorted(missing)
    if args.max_securities:
        codes = codes[:args.max_securities]
    facts: dict[tuple[str, str], tuple[str, str]] = {}
    query_results: list[dict] = []
    failures: list[dict] = []
    elapsed = 0.0

    if args.offline_facts:
        facts_path = ROOT / args.offline_facts
        sha["offline_facts"] = sha256(facts_path)
        with gzip.open(facts_path, "rt", encoding="utf-8") as source:
            for line in source:
                row = json.loads(line)
                facts[(row["code"], row["date"])] = (row["tradestatus"], row["is_st"])
    else:
        if args.max_securities:
            raise SystemExit("LIVE_QUERY_FORBIDDEN_WITH_DIAGNOSTIC_SECURITY_LIMIT")
        import baostock as bs
        import baostock.common.context as context

        if hasattr(context, "apiKey"):
            delattr(context, "apiKey")
        if str(__import__("importlib.metadata", fromlist=["version"]).version("baostock")) != "0.9.3":
            raise SystemExit("PUBLIC_STATUS_REQUIRES_ISOLATED_BAOSTOCK_0_9_3")
        budget = RequestBudget(ROOT / args.ledger)
        prior_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(45)
        session_ok = False
        try:
            budget.consume("login")
            login = bs.login()
            if str(getattr(login, "error_code", "")) != "0":
                raise RuntimeError("BAOSTOCK_PUBLIC_LOGIN_FAILED:" + str(getattr(login, "error_msg", ""))[:120])
            session_ok = True
            sock = getattr(context, "default_socket", None)
            if sock is not None:
                sock.settimeout(45)
            for index, code in enumerate(codes, start=1):
                start, end = first_last[code]
                query_started = time.monotonic()
                row_count = 0
                row_digest = hashlib.sha256()
                try:
                    budget.consume("query_dated_status_gap_only")
                    result = bs.query_history_k_data_plus(
                        code, "date,code,tradestatus,isST", start_date=start, end_date=end,
                        frequency="d", adjustflag="3",
                    )
                    error_code = str(getattr(result, "error_code", "UNKNOWN"))
                    if error_code != "0":
                        raise RuntimeError("QUERY_ERROR:" + error_code + ":" + str(getattr(result, "error_msg", ""))[:100])
                    fields = list(getattr(result, "fields", []))
                    if fields != ["date", "code", "tradestatus", "isST"]:
                        raise RuntimeError("UNEXPECTED_STATUS_FIELDS")
                    wanted = missing[code]
                    gap_hits = 0
                    while result.next():
                        raw = dict(zip(fields, result.get_row_data(), strict=True))
                        date = str(raw["date"])
                        status = str(raw["tradestatus"]).strip()
                        is_st = str(raw["isST"]).strip()
                        normalized_code = str(raw["code"]).lower()
                        if normalized_code != code or status not in {"0", "1"} or is_st not in {"0", "1"}:
                            continue
                        facts[(code, date)] = (status, is_st)
                        row_digest.update(f"{date}\t{code}\t{status}\t{is_st}\n".encode("utf-8"))
                        row_count += 1
                        if date in wanted:
                            gap_hits += 1
                            if gap_hits > len(wanted):
                                raise RuntimeError("STATUS_GAP_FACT_ROW_BOUND_EXCEEDED")
                        if row_count > 1000:
                            raise RuntimeError("STATUS_QUERY_RANGE_ROW_BOUND_EXCEEDED")
                    query_results.append({"code": code, "start": start, "end": end,
                                          "gap_dates_expected": len(wanted), "gap_dates_returned": gap_hits,
                                          "normalized_status_fact_rows_in_query_range": row_count,
                                          "normalized_status_fact_sha256": row_digest.hexdigest(),
                                          "elapsed_seconds": round(time.monotonic() - query_started, 3),
                                          "status": "PASS"})
                except Exception as exc:
                    failures.append({"code": code, "start": start, "end": end,
                                     "error": type(exc).__name__ + ":" + str(exc)[:180]})
                    query_results.append({"code": code, "start": start, "end": end,
                                          "gap_dates_expected": len(missing[code]), "gap_dates_returned": 0,
                                          "normalized_status_fact_rows_in_query_range": 0,
                                          "status": "UNKNOWN"})
                if index % 50 == 0 or index == len(codes):
                    print(json.dumps({"securities_queried": index, "total": len(codes),
                                      "gap_facts": len(facts), "failures": len(failures)}, ensure_ascii=False), flush=True)
            elapsed = sum(float(row.get("elapsed_seconds", 0)) for row in query_results)
        finally:
            if session_ok:
                try:
                    budget.consume("logout", bypass_soft_stop=True)
                    bs.logout()
                except Exception:
                    pass
            socket.setdefaulttimeout(prior_timeout)
            sock = getattr(context, "default_socket", None)
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass

    missing_classification: Counter[str] = Counter()
    is_st_counts: Counter[str] = Counter()
    is_st_security_coverage: set[str] = set()
    actual_provider_status_conflicts = 0
    actual_provider_status_conflict_rows: list[dict] = []
    expected_codes = len(missing) if not args.max_securities else len(codes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=output_path.name + ".", suffix=".tmp", dir=output_path.parent, delete=False) as temporary:
        temp_path = Path(temporary.name)
    output_digest = hashlib.sha256()
    try:
        with gzip.open(universe_path, "rt", encoding="utf-8") as source, gzip.open(temp_path, "wt", encoding="utf-8", newline="") as target:
            for line in source:
                row = json.loads(line)
                code = row["source_security_key"].lower()
                date = row["trade_date"]
                if row.get("source_bar_present") is True:
                    status = "ACTUAL_TRADED"
                    fact = facts.get((code, date))
                    status_source = "LOCAL_TDX_BAR_PRESENCE" + ("+BAOSTOCK_DATED_ISST" if fact else "")
                    is_st = fact[1] if fact else None
                    if fact and fact[0] != "1":
                        actual_provider_status_conflicts += 1
                        actual_provider_status_conflict_rows.append({"source_security_key": row["source_security_key"],
                                                                     "trade_date": date, "provider_tradestatus": fact[0],
                                                                     "classification_precedence": "LOCAL_TDX_ACTUAL_BAR_REMAINS_ACTUAL_TRADED"})
                else:
                    fact = facts.get((code, date))
                    if fact == ("0", "0") or fact == ("0", "1"):
                        status = "SUSPENDED"
                    elif fact == ("1", "0") or fact == ("1", "1"):
                        status = "DATA_GAP"
                    else:
                        status = "UNKNOWN"
                    status_source = "BAOSTOCK_PUBLIC_STATUS_FACT" if fact else "NO_VALID_DATED_PROVIDER_FACT"
                    is_st = fact[1] if fact else None
                    missing_classification[status] += 1
                if is_st is not None:
                    is_st_counts[is_st] += 1
                    is_st_security_coverage.add(code)
                output_row = {"security_id": row["security_id"], "source_security_key": row["source_security_key"],
                              "trade_date": date, "status": status, "is_st": is_st,
                              "provider_tradestatus": fact[0] if fact else None, "status_source": status_source}
                encoded = json.dumps(output_row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                target.write(encoded + "\n")
                output_digest.update((encoded + "\n").encode("utf-8"))
        os.replace(temp_path, output_path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise

    output_sha = sha256(output_path)
    unknown = missing_classification["UNKNOWN"]
    acceptance_pass = (not args.max_securities and not failures and expected_codes == len(missing)
                       and missing_classification["DATA_GAP"] + missing_classification["SUSPENDED"] == sum(len(v) for v in missing.values())
                       and unknown == 0)
    receipt = {
        "contract_id": contract["contract_id"], "status": "DATED_TRADING_STATUS_PASS" if acceptance_pass else "DATED_TRADING_STATUS_BLOCKED",
        "capability": "DATED_TRADING_STATUS_PASS" if acceptance_pass else "DATED_TRADING_STATUS_EVIDENCE_INCOMPLETE",
        "stage_status": "BLOCKED_OPEN_OTHER_REQUIRED_CAPABILITIES",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {"universe_path": args.universe, "universe_sha256": sha["universe"],
                   "contract_sha256": sha["contract"], "membership_rows": membership_count,
                   "actual_bar_rows": actual_bar_count, "missing_bar_rows": sum(len(v) for v in missing.values()),
                   "missing_security_count": len(missing)},
        "provider": {"name": "BaoStock", "version": "0.9.3", "auth_mode": "PUBLIC_ANONYMOUS",
                     "query_security_count": len(query_results), "request_count_bound": len(codes),
                     "gap_only_queries": True, "price_fields_queried_or_persisted": False,
                     "normalized_status_facts_persisted_from_query_ranges": True,
                     "raw_payload_persisted": False},
        "output": {"path": args.output, "sha256": output_sha, "normalized_uncompressed_sha256": output_digest.hexdigest(),
                   "row_count": membership_count},
        "classification_counts": {"ACTUAL_TRADED": actual_bar_count, **dict(missing_classification)},
        "dated_is_st_fact_counts": dict(is_st_counts), "unknown_gap_status_count": unknown,
        "dated_is_st_coverage": {"rows_with_fact": sum(is_st_counts.values()),
                                 "security_count_with_any_fact": len(is_st_security_coverage),
                                 "provider_tradestatus_conflicts_on_local_actual_bar": actual_provider_status_conflicts},
        "provider_tradestatus_conflict_rows": actual_provider_status_conflict_rows,
        "query_failures": failures, "query_receipts": query_results,
        "elapsed_seconds": round(elapsed, 3),
        "execution_identity": {"script_sha256": sha256(Path(__file__).resolve()),
                               "contract_sha256": sha["contract"],
                               "universe_sha256": sha["universe"]},
        "acceptance_limits": ["Provider status fields still require independent semantic acceptance.",
                              "This receipt does not establish V4-01 acceptance or V4-02 stage completion."],
    }
    atomic_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "classification_counts": receipt["classification_counts"],
                      "unknown_gap_status_count": unknown, "query_failures": len(failures),
                      "output_sha256": output_sha}, ensure_ascii=False))
    return 0 if acceptance_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
