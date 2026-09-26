from __future__ import annotations

"""Bounded real-data suspension/ex-day and recent-listing adjustment acceptance evidence."""

import gzip
import hashlib
import json
import os
import socket
import struct
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "runtime/v4_baostock_093/Lib/site-packages"))
from adjustment.tdx_adjustment import build_affine_factors, xrxd_from_gbbq  # noqa: E402
from tdx.gbbq_reader import read_gbbq  # noqa: E402
from workbench_analysis.baostock_supplemental import RequestBudget  # noqa: E402

DAY_ROOT = ROOT / "data/input_staging/extracted/20260924/b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f"
METADATA = ROOT / "data/input_staging/metadata/20260924/4835127dd77534be17d8aeba65d91ebf0ec5bbf6b5348bc1aff4612272acafdc/T0002/hq_cache"
UNIVERSE = ROOT / "data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz"
ADJUSTED = ROOT / "data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R6_2_20260926.parquet"
OUTPUT = ROOT / "reports/v4_02/V4_02_ADJUSTMENT_REAL_SAMPLES_ACCEPTANCE_20260926.json"
LEDGER = ROOT / "reports/v4_baostock/request_ledger.json"
DAY_RECORD = struct.Struct("<IIIII f II")
CUTOFF = 20260924


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


def day_rows(security_id: str) -> list[tuple]:
    market, code = security_id.split(".")
    path = DAY_ROOT / market.lower() / "lday" / f"{market.lower()}{code}.day"
    payload = path.read_bytes()
    if len(payload) % DAY_RECORD.size:
        raise ValueError("TDX_DAY_RECORD_SIZE_INVALID:" + security_id)
    return [DAY_RECORD.unpack_from(payload, offset) for offset in range(0, len(payload), DAY_RECORD.size)]


def independent_qfq(trade_date: int, events: list) -> tuple:
    from decimal import Decimal, localcontext
    with localcontext() as ctx:
        ctx.prec = 40
        a, b = Decimal(1), Decimal(0)
        for event in sorted((e for e in events if trade_date < e.ex_day <= CUTOFF), key=lambda x: (x.ex_day, x.source_record_index), reverse=True):
            m, c = event.mc()
            a = a / m
            b = b / m - c / m
        return +a, +b


def main() -> int:
    import baostock as bs
    import baostock.common.context as context
    from decimal import Decimal, ROUND_HALF_UP
    from importlib.metadata import version
    if version("baostock") != "0.9.3":
        raise SystemExit("REAL_SAMPLE_REQUIRES_ISOLATED_BAOSTOCK_0_9_3")
    if hasattr(context, "apiKey"):
        delattr(context, "apiKey")
    events = read_gbbq(METADATA / "gbbq")
    target = "SZ.002075"
    target_events = [xrxd_from_gbbq(e) for e in events if e.security_id == target and e.category == 1 and e.event_date <= CUTOFF]
    bars = [r for r in day_rows(target) if r[0] <= CUTOFF and all(r[i] > 0 for i in (1, 2, 3, 4))]
    event_record = next(e for e in events if e.security_id == target and e.category == 1 and e.event_date == 20180910)
    before = max((r for r in bars if r[0] < 20180910), key=lambda x: x[0])
    after = min((r for r in bars if r[0] >= 20180910), key=lambda x: x[0])
    if before[0] != 20160914 or after[0] != 20181116:
        raise SystemExit("SUSPENSION_EVENT_SAMPLE_BAR_BOUNDARIES_CHANGED")
    factors = build_affine_factors([r[0] for r in bars], target_events)
    factor = factors[before[0]]
    expected_a, expected_b = independent_qfq(before[0], target_events)
    independent_close = ((expected_a * Decimal(before[4]) / Decimal(100) + expected_b).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    engine_close = factor.qfq_price(Decimal(before[4]) / Decimal(100))

    budget = RequestBudget(LEDGER)
    previous_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(45)
    login_ok = False
    normalized = []
    query_error = None
    try:
        budget.consume("login")
        login = bs.login()
        if str(getattr(login, "error_code", "")) != "0":
            raise RuntimeError("PUBLIC_LOGIN_FAILED:" + str(getattr(login, "error_msg", ""))[:160])
        login_ok = True
        sock = getattr(context, "default_socket", None)
        if sock is not None:
            sock.settimeout(45)
        budget.consume("query_long_suspension_xrxd_status")
        result = bs.query_history_k_data_plus(
            "sz.002075", "date,code,tradestatus,isST", start_date="2018-09-10", end_date="2018-11-16",
            frequency="d", adjustflag="3",
        )
        if str(getattr(result, "error_code", "")) != "0":
            query_error = str(getattr(result, "error_code", "UNKNOWN"))
        else:
            if list(getattr(result, "fields", [])) != ["date", "code", "tradestatus", "isST"]:
                raise RuntimeError("LONG_SUSPENSION_STATUS_FIELDS_CHANGED")
            while result.next():
                d, code, tradestatus, is_st = result.get_row_data()
                if code.lower() == "sz.002075" and tradestatus in {"0", "1"} and is_st in {"0", "1"}:
                    normalized.append((d, tradestatus, is_st))
    finally:
        if login_ok:
            try:
                budget.consume("logout", bypass_soft_stop=True)
                bs.logout()
            except Exception:
                pass
        socket.setdefaulttimeout(previous_timeout)
        sock = getattr(context, "default_socket", None)
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
    normalized_digest = hashlib.sha256("\n".join("\t".join(row) for row in normalized).encode()).hexdigest()
    between = [(d, status, st) for d, status, st in normalized if "2018-09-10" <= d < "2018-11-16"]
    resume_row = next((row for row in normalized if row[0] == "2018-11-16"), None)
    suspension_pass = (query_error is None and len(between) > 0 and all(status == "0" for _, status, _ in between)
                       and resume_row is not None and resume_row[1] == "1"
                       and engine_close == independent_close and factor.qfq_mul == expected_a and factor.qfq_add == expected_b)
    event_bars_in_suspension = [r[0] for r in bars if 20180910 <= r[0] < 20181116]

    first_by_key = {}
    security_id_by_key = {}
    with gzip.open(UNIVERSE, "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            key = row["source_security_key"]
            first_by_key[key] = min(first_by_key.get(key, row["trade_date"]), row["trade_date"])
            security_id_by_key[key] = row["security_id"]
    recent = []
    for key in ("SZ.301686", "SH.688837"):
        sid = security_id_by_key.get(key)
        if sid is None:
            raise SystemExit("RECENT_LISTING_CANDIDATE_NOT_IN_R6_2:" + key)
        listing_boundary = int(first_by_key[key].replace("-", ""))
        real_bars = [row for row in day_rows(key) if row[0] <= CUTOFF and all(row[i] > 0 for i in (1, 2, 3, 4))]
        first_bar = min((row[0] for row in real_bars), default=None)
        recent.append({"source_security_key": key, "canonical_security_id": sid,
                       "first_r6_2_membership_date": first_by_key[key], "first_tdx_actual_bar_date": first_bar,
                       "actual_bar_count_through_cutoff": len(real_bars),
                       "prelisting_tdx_bar_count": sum(row[0] < listing_boundary for row in real_bars),
                       "no_synthetic_prelisting_bar": first_bar == listing_boundary and not any(row[0] < listing_boundary for row in real_bars),
                       "observed_category1_event_count": sum(e.security_id == key and e.category == 1 and e.event_date <= CUTOFF for e in events)})
    recent_pass = len(recent) == 2 and all(x["no_synthetic_prelisting_bar"] for x in recent)

    import pyarrow.parquet as pq
    adjusted_file = pq.ParquetFile(ADJUSTED)
    adjusted_first_date = {}
    for row_group in range(adjusted_file.num_row_groups):
        table = adjusted_file.read_row_group(row_group, columns=["source_security_key", "trade_date", "adjusted_quality", "qfq_close"])
        for i in range(table.num_rows):
            key, d = table.column("source_security_key")[i].as_py(), int(table.column("trade_date")[i].as_py())
            if key in {"SZ.301686", "SH.688837"} and d == int(first_by_key[key].replace("-", "")):
                adjusted_first_date[key] = {"trade_date": d, "quality": table.column("adjusted_quality")[i].as_py(),
                                            "qfq_close": str(table.column("qfq_close")[i].as_py())}
    for row in recent:
        row["adjusted_daily_first_bar"] = adjusted_first_date.get(row["source_security_key"])
        row["adjusted_first_bar_present"] = row["adjusted_daily_first_bar"] is not None
    recent_pass = recent_pass and all(row["adjusted_first_bar_present"] for row in recent)

    receipt = {
        "contract_id": "V4_02_ADJUSTMENT_REAL_SUSPENSION_AND_LISTING_SAMPLES_V1",
        "status": "REAL_ADJUSTMENT_SAMPLES_PASS" if suspension_pass and recent_pass else "REAL_ADJUSTMENT_SAMPLES_BLOCKED",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "cutoff": "2026-09-24",
        "long_suspension_xrxd_sample": {
            "security_id": target, "event_date": 20180910, "category1_record_index": event_record.source_record_index,
            "event_parameters": {"c1": event_record.c1, "c2": event_record.c2, "c3": event_record.c3, "c4": event_record.c4},
            "previous_actual_bar_date": before[0], "first_actual_bar_after_suspension": after[0],
            "bao_status_query": {"range": ["2018-09-10", "2018-11-16"], "normalized_rows": len(normalized),
                                 "suspended_dates_in_event_gap": len(between),
                                 "all_gap_rows_tradestatus_zero": bool(between) and all(r[1] == "0" for r in between),
                                 "resumption_date_tradestatus": resume_row[1] if resume_row else None,
                                 "normalized_status_digest": normalized_digest, "query_error": query_error,
                                 "raw_payload_persisted": False},
            "tdx_bars_inside_suspension_gap": event_bars_in_suspension,
            "no_synthetic_ohlc_during_suspension": not event_bars_in_suspension,
            "qfq_factor_engine": {"A": str(factor.qfq_mul), "B": str(factor.qfq_add),
                                  "independent_A": str(expected_a), "independent_B": str(expected_b),
                                  "previous_raw_close": str(Decimal(before[4]) / Decimal(100)),
                                  "previous_qfq_close": str(engine_close), "engine_matches_independent_decimal": engine_close == independent_close},
            "pass": suspension_pass,
            "limitation": "BaoStock current snapshot status plus present TDX data verifies the observed historical path but does not establish as-recorded historical provider visibility.",
        },
        "recent_listing_samples": recent,
        "recent_listing_samples_pass": recent_pass,
        "input_hashes": {"gbbq_sha256": sha(METADATA / "gbbq"), "day_sample_002075_sha256": sha(DAY_ROOT / "sz/lday/sz002075.day"),
                         "universe_sha256": sha(UNIVERSE), "adjusted_daily_sha256": sha(ADJUSTED),
                         "script_sha256": sha(Path(__file__).resolve())},
        "acceptance": "This bounded sample receipt supplements the five previously accepted-math diagnostic samples; it does not close the V4-00E independent audit or establish PIT source visibility.",
    }
    atomic_json(OUTPUT, receipt)
    print(json.dumps({"status": receipt["status"], "suspension": suspension_pass,
                      "recent_listing": recent_pass, "long_suspension": receipt["long_suspension_xrxd_sample"]["bao_status_query"]["suspended_dates_in_event_gap"]}, ensure_ascii=False))
    return 0 if suspension_pass and recent_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
