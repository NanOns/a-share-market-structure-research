from __future__ import annotations

"""Run bounded §3C.4 replay and future perturbation cases across all four boards."""

import gzip
import hashlib
import json
import os
import tempfile
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

from sys import path as sys_path
ROOT = Path(__file__).resolve().parents[1]
sys_path.insert(0, str(ROOT / "src"))
from adjustment.tdx_adjustment import XrxdEvent, build_affine_factors, xrxd_from_gbbq  # noqa: E402
from tdx.gbbq_reader import read_gbbq  # noqa: E402

ARTIFACT = ROOT / "data/v4/artifact_store/v4_02"
DAILY = ARTIFACT / "V4_02_ADJUSTED_CANONICAL_DAILY_R6_2_20260926.parquet"
STATUS = ARTIFACT / "V4_02_DATED_TRADING_STATUS_R6_2_20260926.jsonl.gz"
UNIVERSE = ROOT / "data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz"
GBBQ = ROOT / "data/input_staging/metadata/20260924/4835127dd77534be17d8aeba65d91ebf0ec5bbf6b5348bc1aff4612272acafdc/T0002/hq_cache/gbbq"
CAL_ROOT = ROOT / "data/v4/candidate_calendars/V4_02_MARKET_CALENDAR_20230704_20260924_V2"
OUT = ROOT / "reports/v4_02/V4_02_SECTION_3C4_TEMPORAL_LEAKAGE_REPLAY_20260926.json"
CODES = ["SH.600006", "SZ.000001", "SZ.300750", "SH.688981"]
ASOF = 20260924


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def ymd(value: str) -> int:
    return int(value.replace("-", ""))


def load_sessions() -> list[int]:
    vals = []
    for name in ("calendar_sse_20230704_20260924.json", "calendar_szse_20230704_20260924.json"):
        doc = json.loads((CAL_ROOT / name).read_text(encoding="utf-8"))
        vals.append({ymd(x) for x in doc["session_dates"]})
    if vals[0] != vals[1]:
        raise SystemExit("FROZEN_EXCHANGE_CALENDAR_SESSION_MISMATCH")
    return sorted(vals[0])


def cases(sessions: list[int]) -> list[dict]:
    session_set = set(sessions)
    last_by_week = {}
    count_by_week = defaultdict(int)
    for encoded in sessions:
        d = date(encoded // 10000, (encoded // 100) % 100, encoded % 100)
        iso = d.isocalendar()
        key = f"{iso.year}-W{iso.week:02d}"
        count_by_week[key] += 1
        last_by_week[key] = encoded
    short = next((last_by_week[k] for k in sorted(last_by_week, reverse=True)
                  if count_by_week[k] < 5 and last_by_week[k] < 20260924), None)
    month_last_session = {}
    for encoded in sessions:
        month_last_session[encoded // 100] = encoded
    nontrade_month_end = None
    for ym in sorted(month_last_session, reverse=True):
        year, month = divmod(ym, 100)
        natural = date(year, month, __import__("calendar").monthrange(year, month)[1])
        natural_code = natural.year * 10000 + natural.month * 100 + natural.day
        if natural_code <= sessions[-1] and natural_code not in session_set:
            nontrade_month_end = month_last_session[ym]
            break
    result = [
        {"case": "WEEKLY_MONDAY", "asof": 20260921},
        {"case": "WEEKLY_WEDNESDAY", "asof": 20260923},
        {"case": "WEEKLY_FRIDAY", "asof": 20260918},
        {"case": "MONTH_START", "asof": 20260901},
        {"case": "MONTH_MIDDLE", "asof": 20260915},
        {"case": "MONTH_END", "asof": 20260831},
    ]
    if short is not None:
        result.append({"case": "HOLIDAY_SHORTENED_WEEK", "asof": short})
    if nontrade_month_end is not None:
        result.append({"case": "NONTRADING_CALENDAR_MONTH_END", "asof": nontrade_month_end})
    for row in result:
        if row["asof"] not in session_set:
            raise ValueError("TEMPORAL_CASE_NOT_A_CALENDAR_SESSION:" + row["case"])
    return result


def independent_factor(trade_date: int, events: list) -> tuple[Decimal, Decimal]:
    with localcontext() as context:
        context.prec = 40
        a, b = Decimal("1"), Decimal("0")
        for event in sorted((e for e in events if trade_date < e.ex_day <= ASOF),
                            key=lambda e: (e.ex_day, e.source_record_index), reverse=True):
            m, c = event.mc()
            a = a / m
            b = b / m - c / m
        return +a, +b


def build_case_digest(daily_rows: list[dict], status_rows: list[dict], actions: list, asof: int) -> tuple[str, int]:
    selected_daily = sorted((r for r in daily_rows if r["trade_date"] <= asof), key=lambda r: (r["source_security_key"], r["trade_date"]))
    selected_status = sorted((r for r in status_rows if r["trade_date"] <= asof), key=lambda r: (r["source_security_key"], r["trade_date"]))
    selected_actions = sorted((e for e in actions if e.ex_day <= asof), key=lambda e: (e.security_id, e.ex_day, e.source_record_index))
    facts: list[dict] = []
    independent_mismatches = 0
    by_code = defaultdict(list)
    for row in selected_daily:
        by_code[row["source_security_key"]].append(row)
    events_by_code = defaultdict(list)
    for event in selected_actions:
        events_by_code[event.security_id].append(event)
    for code in CODES:
        rows = by_code.get(code, [])
        factors = build_affine_factors([row["trade_date"] for row in rows], events_by_code.get(code, []))
        weekly, monthly = defaultdict(list), defaultdict(list)
        for row in rows:
            factor = factors.get(row["trade_date"])
            raw = [row[k] for k in ("raw_open", "raw_high", "raw_low", "raw_close")]
            qfq = [str(factor.qfq_price(value)) for value in raw] if factor else [None] * 4
            expected_a, expected_b = independent_factor(row["trade_date"], events_by_code.get(code, []))
            expected_prices = [str((expected_a * value + expected_b).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) for value in raw]
            if factor is None or factor.qfq_mul != expected_a or factor.qfq_add != expected_b or qfq != expected_prices:
                independent_mismatches += 1
            facts.append({"kind": "DAILY", "code": code, "date": row["trade_date"],
                          "raw": [str(x) for x in raw], "qfq": qfq,
                          "factor": [str(factor.qfq_mul), str(factor.qfq_add)] if factor else None})
            d = date(row["trade_date"] // 10000, row["trade_date"] // 100 % 100, row["trade_date"] % 100)
            iso = d.isocalendar()
            weekly[f"{iso.year}-W{iso.week:02d}"].append((row, qfq))
            monthly[f"{d.year}-{d.month:02d}"].append((row, qfq))
        for kind, groups in (("WEEKLY", weekly), ("MONTHLY", monthly)):
            for key, points in sorted(groups.items()):
                for basis, index in (("RAW", 0), ("QFQ", 1)):
                    if basis == "RAW":
                        opens = [point[0]["raw_open"] for point in points]
                        highs = [point[0]["raw_high"] for point in points]
                        lows = [point[0]["raw_low"] for point in points]
                        closes = [point[0]["raw_close"] for point in points]
                    else:
                        opens = [Decimal(point[1][0]) for point in points if point[1][0] is not None]
                        highs = [Decimal(point[1][1]) for point in points if point[1][1] is not None]
                        lows = [Decimal(point[1][2]) for point in points if point[1][2] is not None]
                        closes = [Decimal(point[1][3]) for point in points if point[1][3] is not None]
                    facts.append({"kind": kind, "basis": basis, "code": code, "key": key,
                                  "open": str(opens[0]) if opens else None,
                                  "high": str(max(highs)) if highs else None,
                                  "low": str(min(lows)) if lows else None,
                                  "close": str(closes[-1]) if closes else None,
                                  "actual_count": len(points)})
    for row in selected_status:
        facts.append({"kind": "STATUS", "code": row["source_security_key"], "date": row["trade_date"],
                      "status": row["status"], "is_st": row["is_st"]})
    for event in selected_actions:
        facts.append({"kind": "ACTION", "code": event.security_id, "date": event.ex_day,
                      "record_index": event.source_record_index,
                      "params": [event.cash_dividend_per_10, event.rights_price,
                                 event.bonus_transfer_per_10, event.rights_ratio_per_10]})
    facts.sort(key=lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")))
    digest = hashlib.sha256()
    for item in facts:
        digest.update((json.dumps(item, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")) + "\n").encode())
    return digest.hexdigest(), independent_mismatches


def main() -> int:
    sessions = load_sessions()
    temporal_cases = cases(sessions)
    db = duckdb.connect(database=":memory:")
    daily_ref = str(DAILY).replace("'", "''")
    code_sql = ",".join("'" + code + "'" for code in CODES)
    daily_rows = db.execute(f"SELECT source_security_key,trade_date,raw_open,raw_high,raw_low,raw_close FROM read_parquet('{daily_ref}') WHERE source_security_key IN ({code_sql})").fetch_arrow_table().to_pylist()
    status_rows = []
    with gzip.open(STATUS, "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row["source_security_key"] in CODES:
                row["trade_date"] = ymd(row["trade_date"])
                status_rows.append(row)
    events = [xrxd_from_gbbq(e) for e in read_gbbq(GBBQ) if e.category == 1 and e.security_id in CODES]
    row_count = len(daily_rows)
    # Future perturbations are deliberately beyond the latest required source cutoff.
    checks = []
    for case in temporal_cases:
        t0 = case["asof"]
        a_digest, a_qfq_mismatches = build_case_digest(daily_rows, status_rows, events, t0)
        repeated_digest, repeated_qfq_mismatches = build_case_digest(daily_rows, status_rows, events, t0)
        b_digest, b_qfq_mismatches = build_case_digest([r for r in daily_rows if r["trade_date"] <= t0],
                                                        [r for r in status_rows if r["trade_date"] <= t0],
                                                        [e for e in events if e.ex_day <= t0], t0)
        perturbed_daily = list(daily_rows)
        perturbed_status = list(status_rows)
        perturbed_actions = list(events)
        synthetic_code = CODES[len(checks) % len(CODES)]
        td = date(t0 // 10000, t0 // 100 % 100, t0 % 100) + timedelta(days=7)
        future_date = td.year * 10000 + td.month * 100 + td.day
        perturbed_daily.append({"source_security_key": synthetic_code, "trade_date": future_date,
                                "raw_open": Decimal("9876.54"), "raw_high": Decimal("9999.99"),
                                "raw_low": Decimal("9000.01"), "raw_close": Decimal("9876.54")})
        perturbed_status.append({"source_security_key": synthetic_code,
                                 "trade_date": future_date, "status": "UNKNOWN", "is_st": "1"})
        perturbed_actions.append(XrxdEvent(synthetic_code, future_date, cash_dividend_per_10=Decimal("9.99")))
        p_digest, p_qfq_mismatches = build_case_digest(perturbed_daily, perturbed_status, perturbed_actions, t0)
        checks.append({"case": case["case"], "asof_trade_date": t0, "security_count": len(CODES),
                       "full_source_digest": a_digest, "physically_deleted_future_digest": b_digest,
                       "future_perturbation_digest": p_digest,
                       "repeat_digest": repeated_digest,
                       "delete_future_equal": a_digest == b_digest,
                       "future_perturbation_invariant": a_digest == p_digest,
                       "same_input_same_cutoff_deterministic": a_digest == repeated_digest,
                       "independent_decimal_qfq_mismatches": {"full_source": a_qfq_mismatches,
                                                              "repeat": repeated_qfq_mismatches,
                                                              "deleted_future": b_qfq_mismatches,
                                                              "perturbed_future": p_qfq_mismatches}})
    passed = all(row["delete_future_equal"] and row["future_perturbation_invariant"]
                 and row["same_input_same_cutoff_deterministic"]
                 and all(value == 0 for value in row["independent_decimal_qfq_mismatches"].values()) for row in checks)
    receipt = {"contract_id": "V4_02_SECTION_3C4_TEMPORAL_LEAKAGE_REPLAY_V1",
               "status": "BOUNDED_TEMPORAL_REPLAY_PASS" if passed else "TEMPORAL_LEAKAGE_BLOCKED",
               "acceptance_scope": "FOUR_SECURITY_CROSS_BOARD_REPLAY; FULL_REQUIRED_UNIVERSE_REPLAY_PENDING",
               "observed_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).replace(microsecond=0).isoformat(),
               "cases": checks,
               "case_count": len(checks), "securities": CODES, "daily_source_rows_loaded": row_count,
               "status_fact_rows_loaded": len(status_rows), "category1_action_rows_loaded": len(events),
               "source_hashes": {"adjusted_daily_raw_basis_sha256": sha(DAILY), "dated_status_sha256": sha(STATUS),
                                 "universe_sha256": sha(UNIVERSE), "gbbq_sha256": sha(GBBQ)},
               "execution_identity": {"script_sha256": sha(Path(__file__).resolve())},
               "limitation": "The replay covers required boundary cases and all four boards on a bounded cross-board sample. It does not constitute an exhaustive full-universe temporal proof.",
               "pack_a_acceptance": "OPEN_FULL_SCOPE_TEMPORAL_REPLAY_REQUIRED"}
    atomic_json(OUT, receipt)
    print(json.dumps({"status": receipt["status"], "cases": len(checks),
                      "all_delete_equal": all(x["delete_future_equal"] for x in checks),
                      "all_future_invariant": all(x["future_perturbation_invariant"] for x in checks)}, ensure_ascii=False))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
