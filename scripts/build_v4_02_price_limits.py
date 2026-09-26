from __future__ import annotations

"""Build date-bound V4-02 price-limit states with UNKNOWN on unproved inputs."""

import argparse
import gzip
import hashlib
import json
import os
import sys
import tempfile
from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from adjustment.tdx_adjustment import xrxd_from_gbbq  # noqa: E402
from tdx.gbbq_reader import read_gbbq  # noqa: E402
from workbench_analysis.limit_rules import LimitStateService  # noqa: E402
from workbench_analysis.v4_02_closure import ex_right_reference_price  # noqa: E402


DEFAULT_GBBQ = ROOT / "data/input_staging/metadata/20260924/4835127dd77534be17d8aeba65d91ebf0ec5bbf6b5348bc1aff4612272acafdc/T0002/hq_cache/gbbq"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def atomic_gzip_writer(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    return Path(name)


def board_rule_key(board_scope: str) -> tuple[str, str]:
    if board_scope == "SH_MAIN":
        return "SH", "MAIN"
    if board_scope == "SZ_MAIN":
        return "SZ", "MAIN"
    if board_scope == "CHINEXT":
        return "SZ", "GROWTH"
    if board_scope == "STAR":
        return "SH", "STAR"
    return "", ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", default="data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz")
    parser.add_argument("--trading-status", default="data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R6_2_20260926.jsonl.gz")
    parser.add_argument("--dated-isst", default="data/v4/artifact_store/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926_RECOVERED_R1.jsonl.gz")
    parser.add_argument("--daily", default="data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R6_2_20260926.parquet")
    parser.add_argument("--raw", default="data/v4/canonical/V4_02_RAW_SELECTED_20260924_062040Z/canonical_daily_raw_selected.parquet")
    parser.add_argument("--identity", default="data/v4/artifact_store/v4_01/security_entity_map_R5_20260925.json")
    parser.add_argument("--calendar", default="config/v4_official_exchange_calendar_v2.json")
    parser.add_argument("--calendar-sse", default="data/v4/candidate_calendars/V4_02_MARKET_CALENDAR_20230704_20260924_V2/calendar_sse_20230704_20260924.json")
    parser.add_argument("--calendar-szse", default="data/v4/candidate_calendars/V4_02_MARKET_CALENDAR_20230704_20260924_V2/calendar_szse_20230704_20260924.json")
    parser.add_argument("--calendar-receipt", default="reports/v4_02/V4_02_FORMAL_MARKET_CALENDAR_ACCEPTANCE_V2.json")
    parser.add_argument("--rule-contract", default="config/v4_02_price_limit_rules_v1.json")
    parser.add_argument("--classification", default="config/v4_02_gbbq_price_impact_classification_v1.json")
    parser.add_argument("--gbbq", default=str(DEFAULT_GBBQ.relative_to(ROOT)).replace("\\", "/"))
    parser.add_argument("--gbbq-map", default=str(DEFAULT_GBBQ.with_suffix(".map").relative_to(ROOT)).replace("\\", "/"))
    parser.add_argument("--output", default="data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R6_2_20260926.jsonl.gz")
    parser.add_argument("--receipt", default="reports/v4_02/V4_02_PRICE_LIMIT_ACCEPTANCE_R1_20260926.json")
    args = parser.parse_args()

    import duckdb

    universe_path, status_path, isst_path = ROOT / args.universe, ROOT / args.trading_status, ROOT / args.dated_isst
    daily_path, raw_path, identity_path = ROOT / args.daily, ROOT / args.raw, ROOT / args.identity
    calendar_path, calendar_receipt_path = ROOT / args.calendar, ROOT / args.calendar_receipt
    calendar_sse_path, calendar_szse_path = ROOT / args.calendar_sse, ROOT / args.calendar_szse
    rule_path, class_path = ROOT / args.rule_contract, ROOT / args.classification
    gbbq_path, gbbq_map_path = ROOT / args.gbbq, ROOT / args.gbbq_map
    out_path, receipt_path = ROOT / args.output, ROOT / args.receipt
    calendar = json.loads(calendar_path.read_text(encoding="utf-8"))
    cal_receipt = json.loads(calendar_receipt_path.read_text(encoding="utf-8"))
    if cal_receipt.get("status") != "FORMAL_MARKET_CALENDAR_PASS":
        raise SystemExit("PRICE_LIMIT_FORMAL_CALENDAR_NOT_ACCEPTED")
    sse_cal = json.loads(calendar_sse_path.read_text(encoding="utf-8"))
    szse_cal = json.loads(calendar_szse_path.read_text(encoding="utf-8"))
    sessions = [str(value).replace("-", "") for value in sse_cal.get("session_dates", [])]
    szse_sessions = [str(value).replace("-", "") for value in szse_cal.get("session_dates", [])]
    if not sessions or sessions != szse_sessions or len(sessions) != 786:
        raise SystemExit("PRICE_LIMIT_CALENDAR_SESSION_BINDING_FAILED")
    session_index = {day: i for i, day in enumerate(sessions)}
    previous_session = {day: sessions[i - 1] if i else None for i, day in enumerate(sessions)}
    previous_session[sessions[0]] = "20230703"  # accepted RAW warm-up session immediately before the formal window

    rule_doc = json.loads(rule_path.read_text(encoding="utf-8"))
    rules = rule_doc["rules"]
    service = LimitStateService(rules)
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    list_dates_by_id: dict[str, set[str]] = defaultdict(set)
    delist_dates_by_id: dict[str, set[str]] = defaultdict(set)
    source_to_id: dict[str, set[str]] = defaultdict(set)
    for record in identity.get("records", []):
        security_id = str(record.get("security_id") or "")
        source_key = str(record.get("source_security_key") or record.get("symbol") or "").lower()
        if security_id:
            if record.get("list_date"):
                list_dates_by_id[security_id].add(str(record["list_date"]).replace("-", ""))
            if record.get("delist_date"):
                delist_dates_by_id[security_id].add(str(record["delist_date"]).replace("-", ""))
            if source_key:
                source_to_id[source_key].add(security_id)
    first_listing_session_by_id: dict[str, int] = {}
    ambiguous_listing_date: set[str] = set()
    for security_id, dates in list_dates_by_id.items():
        if len(dates) != 1:
            ambiguous_listing_date.add(security_id)
            continue
        list_day = next(iter(dates))
        position = bisect_left(sessions, list_day)
        if position < len(sessions) and sessions[position] == list_day:
            first_listing_session_by_id[security_id] = position
    class_doc = json.loads(class_path.read_text(encoding="utf-8"))
    cat_disp = {int(key): str(value["formal_disposition"]) for key, value in class_doc["dispositions"].items()}
    from collections import namedtuple
    Action = namedtuple("Action", "record event disposition")
    events_by_key: dict[tuple[str, str], list[Action]] = defaultdict(list)
    source_key_to_id: dict[str, str] = {}
    source_key_ambiguous: set[str] = set()
    # Universe aliases supply the dated symbol -> accepted stable identity binding.
    with gzip.open(universe_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            key = str(item["source_security_key"]).lower()
            security_id = str(item["security_id"])
            if key in source_key_to_id and source_key_to_id[key] != security_id:
                source_key_ambiguous.add(key)
            source_key_to_id[key] = security_id
    for record in read_gbbq(gbbq_path):
        category = int(record.category)
        event_day = str(record.event_date).zfill(8)
        source_key = str(record.security_id).lower()
        ids = source_to_id.get(source_key, set())
        if len(ids) != 1:
            continue
        security_id = next(iter(ids))
        events_by_key[(security_id, event_day)].append(Action(record, xrxd_from_gbbq(record) if category == 1 else None, cat_disp.get(category, "UNKNOWN_PRICE_IMPACT")))

    # Prior session close is sourced from the accepted TDX RAW artifact for 2023-07-03.
    raw_sql_path = str(raw_path).replace("'", "''")
    conn = duckdb.connect()
    # The parquet is grouped by security, not by trade_date. Materialize the
    # narrow price projection once so the 786 session lookups do not rescan the
    # full parquet file 786 times. Keep this cache ephemeral in DuckDB only.
    daily_sql = str(daily_path).replace("'", "''")
    conn.execute(
        "create temp table v4_02_price_bars as "
        f"select canonical_security_id, source_security_key, board_scope, raw_close, trade_date "
        f"from read_parquet('{daily_sql}')"
    )
    conn.execute("create index v4_02_price_bars_day_security on v4_02_price_bars(trade_date, canonical_security_id)")
    warmup = conn.execute(
        f"select source_security_key, close_price_raw, price_scale from read_parquet('{raw_sql_path}') where trade_date=20230703 and record_quality='SOURCE_FILE_VALIDATED_RECORD'"
    ).fetchall()
    previous_actual: dict[str, tuple[str, Decimal]] = {}
    for source_key, close_raw, scale in warmup:
        key = str(source_key).lower()
        security_id = source_key_to_id.get(key)
        if security_id and key not in source_key_ambiguous:
            previous_actual[security_id] = ("20230703", Decimal(int(close_raw)) / Decimal(int(scale)))

    counts: Counter[str] = Counter()
    by_board: Counter[str] = Counter()
    by_reason: Counter[str] = Counter()
    samples: dict[str, dict] = {}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = atomic_gzip_writer(out_path)
    output_digest = hashlib.sha256()
    row_count = 0
    current_day = None
    day_members: list[tuple[dict, dict, dict]] = []
    query_count = 0
    boundary_days = {"20260703", "20260706"}

    def process_day(day: str, members: list[tuple[dict, dict, dict]], target) -> None:
        nonlocal row_count, query_count
        table = conn.execute(
            "select canonical_security_id,source_security_key,board_scope,raw_close,trade_date "
            "from v4_02_price_bars where trade_date=? order by canonical_security_id",
            [int(day)],
        ).fetchall()
        actual = {str(row[0]): {"source_security_key": row[1], "board_scope": row[2], "raw_close": Decimal(str(row[3])), "trade_date": str(row[4])} for row in table}
        query_count += 1
        for universe_row, status_row, isst_row in members:
            security_id = str(universe_row["security_id"])
            source_key = str(universe_row["source_security_key"])
            board = str(universe_row["board_scope"])
            market = "SSE" if board in {"SH_MAIN", "STAR"} else "SZSE"
            status = str(status_row["status"])
            is_st = isst_row.get("is_st")
            result = {"contract_id": "PRICE_LIMIT_RULE_V1", "security_id": security_id,
                      "source_security_key": source_key, "trade_date": str(universe_row["trade_date"]), "board_scope": board,
                      "trading_status": status, "is_st": is_st, "risk_status": None,
                      "reference_price": None, "reference_basis": "UNKNOWN", "rule_id": None,
                      "limit_up_price": None, "limit_down_price": None, "limit_status": "UNKNOWN",
                      "reason": None, "knowledge_lineage": "DIAGNOSTIC_NON_PIT"}
            row = actual.get(security_id)
            if status == "SUSPENDED":
                result.update(limit_status="SUSPENDED", reference_basis="SUSPENSION_FACT", reason="SUSPENDED")
            elif status != "ACTUAL_TRADED":
                result["reason"] = "TRADING_STATUS_" + status
            elif row is None or str(row["trade_date"]) != day:
                result["reason"] = "ACTUAL_BAR_BINDING_MISSING"
            elif is_st not in {"0", "1"}:
                result["reason"] = "RISK_STATUS_UNKNOWN"
            else:
                risk_status = "RISK_WARNING" if is_st == "1" else "NORMAL"
                result["risk_status"] = risk_status
                if day in delist_dates_by_id.get(security_id, set()):
                    result.update(reference_basis="UNKNOWN", reason="DELISTING_PHASE_UNRESOLVED")
                elif security_id not in ambiguous_listing_date:
                    first_session = first_listing_session_by_id.get(security_id)
                    if first_session is not None and first_session <= session_index[day] < first_session + 5:
                        result.update(limit_status="NO_LIMIT", reference_basis="LISTING_PHASE", reason="IPO_FIRST_5_TRADING_DAYS")
                        samples.setdefault("IPO_NO_LIMIT", dict(result))
                        if row:
                            previous_actual[security_id] = (day, row["raw_close"])
                        _write(target, output_digest, result)
                        row_count += 1
                        counts[result["limit_status"]] += 1
                        by_board[board] += 1
                        continue

                events = events_by_key.get((security_id, day), [])
                if day in delist_dates_by_id.get(security_id, set()):
                    result.update(reference_basis="UNKNOWN", reason="DELISTING_PHASE_UNRESOLVED")
                elif security_id in ambiguous_listing_date:
                    result.update(reference_basis="UNKNOWN", reason="LISTING_DATE_AMBIGUOUS")
                elif any(event.disposition in {"UNKNOWN_PRICE_IMPACT", "PRICE_AFFECTING_UNSUPPORTED"} for event in events):
                    result.update(reference_basis="UNKNOWN", reason="CORPORATE_ACTION_REFERENCE_UNSUPPORTED")
                else:
                    prior = previous_actual.get(security_id)
                    expected_prior = previous_session.get(day)
                    if not prior or prior[0] != expected_prior:
                        result.update(reference_basis="UNKNOWN", reason="PREVIOUS_SESSION_ACTUAL_CLOSE_UNAVAILABLE")
                    else:
                        ref = prior[1]
                        cat1_events = [event.event for event in events if event.event is not None]
                        try:
                            if cat1_events:
                                ref = ex_right_reference_price(ref, cat1_events, "0.01")
                                basis = "TDX_XRXD_REFERENCE_TRANSFORM_DIAGNOSTIC_NON_PIT"
                            else:
                                basis = "PREVIOUS_TDX_ACTUAL_CLOSE"
                            exchange, rule_board = board_rule_key(board)
                            limit = service.evaluate({
                                "security_id": security_id, "trade_date": day, "exchange": exchange,
                                "board": rule_board, "risk_status": risk_status, "suspended": False,
                                "reference_status": "KNOWN", "quote_prev_close": str(ref),
                                "close": str(row["raw_close"]), "listing_phase": "REGULAR",
                                "ex_rights_reference_unknown": False,
                            })
                            result.update(reference_price=str(ref), reference_basis=basis,
                                          rule_id=limit.get("rule_id"),
                                          limit_up_price=str(limit["limit_up_price"]) if limit.get("limit_up_price") is not None else None,
                                          limit_down_price=str(limit["limit_down_price"]) if limit.get("limit_down_price") is not None else None,
                                          limit_status=limit.get("limit_state", "UNKNOWN"), reason=limit.get("reason"))
                            if cat1_events:
                                samples.setdefault("EX_RIGHT", {**result, "previous_close": str(prior[1]),
                                                               "action_count": len(cat1_events),
                                                               "action_formula": "(previous_close-cash_dividend_per_share+rights_price*rights_ratio)/(1+bonus_transfer_ratio+rights_ratio)"})
                        except Exception as exc:
                            result.update(reference_basis="UNKNOWN", reason="REFERENCE_PRICE_CALCULATION_FAILED:" + type(exc).__name__)

                    # 2026-07-06 is the risk-warning ratio rule boundary.
                    if day in boundary_days and risk_status == "RISK_WARNING":
                        samples.setdefault("RULE_BOUNDARY_" + day + "_" + board, dict(result))
            _write(target, output_digest, result)
            row_count += 1
            counts[result["limit_status"]] += 1
            by_board[board] += 1
            if result["limit_status"] == "LIMIT_UP":
                samples.setdefault("SH_NORMAL_LIMIT_UP" if board == "SH_MAIN" and result["risk_status"] == "NORMAL" else
                                   "SZ_NORMAL_LIMIT_UP" if board == "SZ_MAIN" and result["risk_status"] == "NORMAL" else
                                   "CHINEXT_LIMIT_UP" if board == "CHINEXT" else
                                   "STAR_LIMIT_UP" if board == "STAR" else "OTHER_LIMIT_UP", dict(result))
            if result["risk_status"] == "RISK_WARNING" and result["limit_status"] == "LIMIT_UP":
                samples.setdefault(("SH" if board in {"SH_MAIN", "STAR"} else "SZ") + "_ST_LIMIT_UP", dict(result))
            if result["limit_status"] != "UNKNOWN" and result["risk_status"] in {"NORMAL", "RISK_WARNING"}:
                samples.setdefault(board + "_" + result["risk_status"] + "_SAMPLE", dict(result))
            if result["limit_status"] == "UNKNOWN" and result.get("reason"):
                by_reason[str(result["reason"])] += 1
            if row:
                previous_actual[security_id] = (day, row["raw_close"])

    def _write(target, digest, item):
        encoded = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        target.write(encoded + "\n")
        digest.update((encoded + "\n").encode("utf-8"))

    def flush(day: str, members: list[tuple[dict, dict, dict]], target):
        process_day(day, members, target)
        if query_count % 50 == 0 or query_count == len(sessions):
            print(json.dumps({"days_processed": query_count, "days_expected": len(sessions), "rows": row_count,
                              "unknown": counts["UNKNOWN"]}, ensure_ascii=False), flush=True)

    try:
        with gzip.open(temp_path, "wt", encoding="utf-8", newline="\n", compresslevel=6) as out:
            with gzip.open(universe_path, "rt", encoding="utf-8") as u, gzip.open(status_path, "rt", encoding="utf-8") as s, gzip.open(isst_path, "rt", encoding="utf-8") as i:
                for ul, sl, il in zip(u, s, i, strict=True):
                    ur, sr, ir = json.loads(ul), json.loads(sl), json.loads(il)
                    day = str(ur["trade_date"]).replace("-", "")
                    if sr.get("trade_date") != ur.get("trade_date") or ir.get("trade_date") != ur.get("trade_date") or sr.get("security_id") != ur.get("security_id") or ir.get("security_id") != ur.get("security_id"):
                        raise RuntimeError("STATUS_OR_ISST_UNIVERSE_BINDING_MISMATCH")
                    if current_day is None:
                        current_day = day
                    if day != current_day:
                        flush(current_day, day_members, out)
                        current_day, day_members = day, []
                    day_members.append((ur, sr, ir))
                if current_day is not None:
                    flush(current_day, day_members, out)
            with temp_path.open("rb+") as stream:
                stream.flush()
                os.fsync(stream.fileno())
        if query_count != len(sessions):
            raise RuntimeError("PRICE_LIMIT_DAY_COUNT_MISMATCH")
        os.replace(temp_path, out_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
        conn.close()

    artifact_sha = sha256(out_path)
    receipt = {
        "contract_id": "V4_02_PRICE_LIMIT_RULE_V1",
        "version": "1.0.0",
        "status": "PRICE_LIMIT_CANDIDATE_PASS_WITH_FAIL_CLOSED_UNKNOWN" if counts["UNKNOWN"] else "PRICE_LIMIT_PASS",
        "stage_contract": "PRICE_LIMIT_RULE_V1",
        "scope": {"start_date": "2023-07-04", "end_date": "2026-09-24", "session_count": len(sessions), "required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"]},
        "row_count": row_count,
        "limit_status_counts": dict(counts),
        "unknown_reason_counts": dict(by_reason),
        "by_board": dict(by_board),
        "samples": samples,
        "artifact": {"path": args.output, "row_count": row_count, "sha256": artifact_sha},
        "normalized_output_sha256": output_digest.hexdigest(),
        "input_hashes": {"universe": sha256(universe_path), "trading_status": sha256(status_path), "dated_isst": sha256(isst_path),
                         "daily": sha256(daily_path), "raw": sha256(raw_path), "identity": sha256(identity_path),
                         "calendar_contract": sha256(calendar_path), "calendar_receipt": sha256(calendar_receipt_path),
                         "calendar_sse": sha256(calendar_sse_path), "calendar_szse": sha256(calendar_szse_path),
                         "rule_contract": sha256(rule_path), "classification_contract": sha256(class_path),
                         "gbbq": sha256(gbbq_path), "gbbq_map": sha256(gbbq_map_path)},
        "rule_registry_contract": rule_doc["contract_id"],
        "authority": "OFFICIAL_DATED_RULES; LOCAL_TDX_PRICES; BAOSTOCK_DATED_ISST_SUPPLEMENT",
        "reference_policy": "Previous local TDX actual close for adjacent sessions; category-1 XRXD transform for supported ex-right dates; all other unresolved cases UNKNOWN.",
        "knowledge_lineage": "DIAGNOSTIC_NON_PIT_FOR_HISTORICAL_PROVIDER_AND_GBBQ_FACTS",
        "limitations": [
            "Identity lifecycle input has effective list and delist dates but no separately dated relisting events; no relisting-phase claim is made.",
            "Delisting-date and ambiguous lifecycle rows remain UNKNOWN; unsupported corporate actions remain UNKNOWN per security.",
            "Historical limit labels are diagnostic because dated isST and GBBQ action visibility are not historical as-recorded snapshots."
        ],
        "execution_identity": {"script_sha256": sha256(Path(__file__).resolve()), "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()},
        "next_stage": "WHOLE_STAGE_STAGING_MANIFEST_AND_INDEPENDENT_FINAL_POSTCHECK",
    }
    atomic_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "row_count": row_count,
                      "unknown": counts["UNKNOWN"], "artifact_sha256": artifact_sha}, ensure_ascii=False))
    return 0 if counts["UNKNOWN"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
