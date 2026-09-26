from __future__ import annotations

"""Build hash-bound R6.2 adjusted daily and RAW/QFQ weekly/monthly artifacts."""

import argparse
import array
import calendar as calendar_module
import gzip
import hashlib
import json
import math
import os
import tempfile
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from adjustment.tdx_adjustment import build_affine_factors, xrxd_from_gbbq  # noqa: E402
from tdx.gbbq_reader import read_gbbq  # noqa: E402

ASOF = 20260924
START = 20230704
CENT = Decimal("0.01")
SCALE = Decimal("100")
CONTRACT = ROOT / "config/v4_02_formal_period_contract_v1.json"
UNIVERSE = ROOT / "data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz"
STATUS = ROOT / "data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R6_2_20260926.jsonl.gz"
RAW = ROOT / "data/v4/canonical/V4_02_RAW_SELECTED_20260924_062040Z/canonical_daily_raw_selected.parquet"
CLASSIFICATION = ROOT / "reports/v4_02/V4_02_GBBQ_PRICE_IMPACT_CLASSIFICATION_V1.json"
DISPOSITIONS = ROOT / "data/v4/artifact_store/v4_02/V4_02_GBBQ_SECURITY_DISPOSITIONS_R6_2_20260926.jsonl.gz"
GBBQ = ROOT / "data/input_staging/metadata/20260924/4835127dd77534be17d8aeba65d91ebf0ec5bbf6b5348bc1aff4612272acafdc/T0002/hq_cache/gbbq"
MAP = ROOT / "data/input_staging/metadata/20260924/4835127dd77534be17d8aeba65d91ebf0ec5bbf6b5348bc1aff4612272acafdc/T0002/hq_cache/gbbq.map"
CAL_ROOT = ROOT / "data/v4/candidate_calendars/V4_02_MARKET_CALENDAR_20230704_20260924_V2"
OUT_DIR = ROOT / "data/v4/artifact_store/v4_02"
RECEIPT = ROOT / "reports/v4_02/V4_02_FORMAL_PERIODS_R6_2_20260926.json"


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


def atomic_stage(final: Path) -> Path:
    final.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=final.name + ".", suffix=".tmp", dir=final.parent)
    os.close(fd)
    return Path(tmp)


def period_key(value: int, kind: str) -> str:
    d = date(value // 10000, (value // 100) % 100, value % 100)
    if kind == "WEEKLY":
        iso = d.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    return f"{d.year}-{d.month:02d}"


def natural_period_end(key: str, kind: str) -> int:
    if kind == "WEEKLY":
        year, week = key.split("-W")
        value = date.fromisocalendar(int(year), int(week), 5)
    else:
        year, month = map(int, key.split("-"))
        value = date(year, month, calendar_module.monthrange(year, month)[1])
    return value.year * 10000 + value.month * 100 + value.day


def get_calendar(markets: list[str]) -> dict[str, dict[str, dict]]:
    result = {}
    for market, fname in (("SH", "calendar_sse_20230704_20260924.json"), ("SZ", "calendar_szse_20230704_20260924.json")):
        if market not in markets:
            continue
        doc = json.loads((CAL_ROOT / fname).read_text(encoding="utf-8"))
        sessions = [int(x.replace("-", "")) for x in doc["session_dates"]]
        data = {"WEEKLY": {}, "MONTHLY": {}}
        for value in sessions:
            for kind in data:
                key = period_key(value, kind)
                item = data[kind].setdefault(key, {"calendar_count": 0, "first_session": value, "last_session": value})
                item["calendar_count"] += 1
                item["first_session"] = min(item["first_session"], value)
                item["last_session"] = max(item["last_session"], value)
        result[market] = data
    return result


def schemas() -> tuple[pa.Schema, pa.Schema]:
    daily = pa.schema([
        ("canonical_security_id", pa.string()), ("source_security_key", pa.string()), ("board_scope", pa.string()),
        ("trade_date", pa.uint32()), ("raw_open", pa.decimal128(18, 2)), ("raw_high", pa.decimal128(18, 2)),
        ("raw_low", pa.decimal128(18, 2)), ("raw_close", pa.decimal128(18, 2)),
        ("qfq_open", pa.decimal128(18, 2)), ("qfq_high", pa.decimal128(18, 2)),
        ("qfq_low", pa.decimal128(18, 2)), ("qfq_close", pa.decimal128(18, 2)),
        ("qfq_mul", pa.decimal128(38, 18)), ("qfq_add", pa.decimal128(38, 18)),
        ("volume", pa.uint64()), ("amount", pa.float64()), ("price_basis", pa.string()),
        ("adjusted_quality", pa.string()), ("adjustment_reason", pa.string()),
        ("adjustment_source_revision", pa.string()), ("adjustment_contract_id", pa.string()),
        ("trading_status", pa.string()), ("membership_basis", pa.string()), ("knowledge_lineage", pa.string()),
    ])
    period = pa.schema([
        ("canonical_security_id", pa.string()), ("source_security_key", pa.string()), ("board_scope", pa.string()),
        ("period_type", pa.string()), ("period_start_date", pa.uint32()), ("period_end_date", pa.uint32()),
        ("period_last_session", pa.uint32()),
        ("asof_trade_date", pa.uint32()), ("open", pa.decimal128(18, 2)), ("high", pa.decimal128(18, 2)),
        ("low", pa.decimal128(18, 2)), ("close", pa.decimal128(18, 2)),
        ("volume", pa.uint64()), ("amount", pa.float64()), ("price_basis", pa.string()),
        ("period_view", pa.string()), ("period_status", pa.string()), ("calendar_count", pa.uint16()),
        ("actual_count", pa.uint16()), ("suspended_count", pa.uint16()), ("data_gap_count", pa.uint16()),
        ("unknown_count", pa.uint16()), ("invalid_actual_count", pa.uint16()),
        ("max_source_trade_date", pa.uint32()), ("source_daily_digest", pa.string()),
        ("adjusted_quality", pa.string()), ("adjustment_contract_id", pa.string()),
        ("membership_basis", pa.string()), ("knowledge_lineage", pa.string()),
    ])
    return daily, period


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asof", type=int, default=ASOF)
    args = parser.parse_args()
    asof = args.asof
    if not START <= asof <= ASOF:
        raise SystemExit("ASOF_OUTSIDE_FROZEN_REQUIRED_SCOPE")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    calendar_receipt = json.loads((ROOT / contract["calendar_acceptance_receipt"]).read_text(encoding="utf-8"))
    if calendar_receipt.get("status") != "FORMAL_MARKET_CALENDAR_PASS":
        raise SystemExit("FORMAL_CALENDAR_GATE_NOT_PASS")
    calendars = get_calendar(["SH", "SZ"])

    gap_facts = {}
    status_sha = sha(STATUS)
    with gzip.open(STATUS, "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row["status"] != "ACTUAL_TRADED":
                gap_facts[(row["source_security_key"], int(row["trade_date"].replace("-", "")))] = row["status"]

    # Exact membership-session counts and actual bar date lists; uint32 arrays keep the index compact.
    members: dict[str, dict] = {}
    membership_sessions = 0
    with gzip.open(UNIVERSE, "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            key, sid, board = row["source_security_key"], row["security_id"], row["board_scope"]
            market = "SH" if key.startswith("SH.") else "SZ"
            d = int(row["trade_date"].replace("-", ""))
            if d > asof:
                continue
            membership_sessions += 1
            item = members.setdefault(key, {"security_id": sid, "board": board, "market": market,
                                            "actual_dates": array.array("I"), "stats": defaultdict(Counter)})
            if item["security_id"] != sid or item["board"] != board:
                raise ValueError("UNIVERSE_SECURITY_ID_OR_BOARD_CHANGED_WITHIN_SOURCE_KEY")
            for kind in ("WEEKLY", "MONTHLY"):
                counts = item["stats"][period_key(d, kind)]
                counts["calendar"] += 1
                if row.get("source_bar_present") is True:
                    counts["actual"] += 1
                else:
                    status_value = gap_facts.get((key, d), "UNKNOWN")
                    if status_value == "SUSPENDED":
                        counts["suspended"] += 1
                    elif status_value == "DATA_GAP":
                        counts["data_gap"] += 1
                    else:
                        counts["unknown"] += 1
            if row.get("source_bar_present") is True:
                item["actual_dates"].append(d)

    for item in members.values():
        item["actual_dates"] = sorted(item["actual_dates"])

    disposition_by_sid = {}
    with gzip.open(DISPOSITIONS, "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            disposition_by_sid[row["security_id"]] = row

    records = read_gbbq(GBBQ)
    events_by_code: dict[str, list] = defaultdict(list)
    categories_by_code: dict[str, set[int]] = defaultdict(set)
    for event in records:
        if event.event_date <= asof:
            events_by_code[event.security_id].append(event)
            categories_by_code[event.security_id].add(event.category)
    xrxd_by_code = {key: [xrxd_from_gbbq(event) for event in values if event.category == 1]
                    for key, values in events_by_code.items()}

    raw_file = pq.ParquetFile(RAW)
    output_names = [
        "V4_02_ADJUSTED_CANONICAL_DAILY_R6_2_20260926.parquet",
        "V4_02_FORMAL_WEEKLY_RAW_QFQ_R6_2_20260926.parquet",
        "V4_02_FORMAL_MONTHLY_RAW_QFQ_R6_2_20260926.parquet",
    ]
    finals = [OUT_DIR / name for name in output_names]
    temps = [atomic_stage(path) for path in finals]
    daily_schema, period_schema = schemas()
    daily_writer = pq.ParquetWriter(temps[0], daily_schema, compression="zstd", version="2.6")
    weekly_writer = pq.ParquetWriter(temps[1], period_schema, compression="zstd", version="2.6")
    monthly_writer = pq.ParquetWriter(temps[2], period_schema, compression="zstd", version="2.6")
    writers = {"WEEKLY": weekly_writer, "MONTHLY": monthly_writer}
    daily_count = invalid_actual_count = 0
    period_rows = Counter()
    matched_by_code = Counter()
    daily_columns = ["source_security_key", "trade_date", "open_price_raw", "high_price_raw", "low_price_raw",
                     "close_price_raw", "amount_source_native", "volume_source_native", "record_quality"]
    raw_sha = sha(RAW)
    action_sha = sha(GBBQ)
    contract_sha = sha(CONTRACT)
    try:
        for group_index in range(raw_file.num_row_groups):
            table = raw_file.read_row_group(group_index, columns=daily_columns)
            if not table.num_rows:
                continue
            key = str(table.column("source_security_key")[0].as_py())
            info = members.get(key)
            if info is None:
                continue
            targets = info["actual_dates"]
            if not targets:
                continue
            date_values = table.column("trade_date").to_numpy(zero_copy_only=False)
            start_pos = 0
            target_pos = 0
            day_rows: list[dict] = []
            period_aggs = {kind: defaultdict(dict) for kind in ("WEEKLY", "MONTHLY")}
            invalid_by_period = defaultdict(int)
            events = xrxd_by_code.get(key, [])
            factors = build_affine_factors(targets, events)
            disposition = disposition_by_sid.get(info["security_id"], {})
            blocking_categories = disposition.get("blocking_categories", [])
            quality_base = "UNAVAILABLE_UNKNOWN_PRICE_IMPACT" if any(
                str(category) in {"4", "12", "15"} for category in blocking_categories
            ) else ("UNAVAILABLE_PRICE_AFFECTING_UNSUPPORTED" if blocking_categories else "READY")
            reason = ("UNSUPPORTED_OR_UNKNOWN_GBBQ_CATEGORIES:" + ",".join(map(str, blocking_categories))) if blocking_categories else "CATEGORY_SCOPE_SUPPORTED_BY_BOUND_LOCAL_REFERENCE"
            security = key
            expected_dates = targets
            for row_index, raw_date in enumerate(date_values):
                d = int(raw_date)
                if d < START or d > asof:
                    continue
                while target_pos < len(expected_dates) and expected_dates[target_pos] < d:
                    target_pos += 1
                if target_pos >= len(expected_dates) or expected_dates[target_pos] != d:
                    continue
                target_pos += 1
                matched_by_code[key] += 1
                vals = []
                for col in ("open_price_raw", "high_price_raw", "low_price_raw", "close_price_raw"):
                    vals.append(int(table.column(col)[row_index].as_py()))
                amount = float(table.column("amount_source_native")[row_index].as_py())
                volume = int(table.column("volume_source_native")[row_index].as_py())
                source_quality = str(table.column("record_quality")[row_index].as_py())
                valid = (all(v > 0 for v in vals) and vals[1] >= max(vals[0], vals[2], vals[3])
                         and vals[2] <= min(vals[0], vals[1], vals[3]) and math.isfinite(amount) and amount >= 0
                         and source_quality in {"SOURCE_FILE_VALIDATED_RECORD", "SOURCE_RECORD_RETAINED", "VALID"})
                factor = factors.get(d)
                adjusted_quality = quality_base if valid else "UNAVAILABLE_INVALID_RAW_DAILY"
                if factor is not None and adjusted_quality == "READY":
                    raw_prices = [Decimal(v) / SCALE for v in vals]
                    qprices = [factor.qfq_price(v) for v in raw_prices]
                    qmul = factor.qfq_mul.quantize(Decimal("0.000000000000000001"), rounding=ROUND_HALF_UP)
                    qadd = factor.qfq_add.quantize(Decimal("0.000000000000000001"), rounding=ROUND_HALF_UP)
                else:
                    qprices, qmul, qadd = [None] * 4, None, None
                row = {"canonical_security_id": info["security_id"], "source_security_key": key,
                       "board_scope": info["board"], "trade_date": d,
                       "raw_open": Decimal(vals[0]) / SCALE, "raw_high": Decimal(vals[1]) / SCALE,
                       "raw_low": Decimal(vals[2]) / SCALE, "raw_close": Decimal(vals[3]) / SCALE,
                       "qfq_open": qprices[0], "qfq_high": qprices[1], "qfq_low": qprices[2], "qfq_close": qprices[3],
                       "qfq_mul": qmul, "qfq_add": qadd, "volume": volume, "amount": amount,
                       "price_basis": "TDX_NATIVE_AFFINE_QFQ", "adjusted_quality": adjusted_quality,
                       "adjustment_reason": reason if adjusted_quality == "READY" else (reason if not valid else adjusted_quality),
                       "adjustment_source_revision": action_sha, "adjustment_contract_id": "GBBQ_PRICE_IMPACT_CLASSIFICATION_V1",
                       "trading_status": "ACTUAL_TRADED", "membership_basis": "R6_2_NORMALIZED_INTERVAL",
                       "knowledge_lineage": "DIAGNOSTIC_NON_PIT_CURRENT_METADATA_SNAPSHOT"}
                day_rows.append(row)
                if not valid:
                    invalid_actual_count += 1
                    for kind in ("WEEKLY", "MONTHLY"):
                        invalid_by_period[(kind, period_key(d, kind))] += 1
                    continue
                for kind in ("WEEKLY", "MONTHLY"):
                    pkey = period_key(d, kind)
                    for basis, prices in (("RAW", [row["raw_open"], row["raw_high"], row["raw_low"], row["raw_close"]]),
                                          ("QFQ", qprices)):
                        agg = period_aggs[kind].setdefault((pkey, basis), {"first_date": d, "open": prices[0], "high": prices[1],
                                                                           "low": prices[2], "close": prices[3], "volume": 0,
                                                                           "amount": 0.0, "actual": 0, "max_date": d,
                                                                           "digest": hashlib.sha256()})
                        if d < agg["first_date"]:
                            agg["first_date"], agg["open"] = d, prices[0]
                        if prices[1] is not None:
                            agg["high"] = prices[1] if agg["high"] is None else max(agg["high"], prices[1])
                        if prices[2] is not None:
                            agg["low"] = prices[2] if agg["low"] is None else min(agg["low"], prices[2])
                        if d >= agg["max_date"]:
                            agg["max_date"], agg["close"] = d, prices[3]
                        agg["volume"] += volume
                        agg["amount"] += amount
                        agg["actual"] += 1
                        fact = [d, *(str(p) if p is not None else None for p in prices), volume, repr(amount)]
                        agg["digest"].update((json.dumps(fact, separators=(",", ":")) + "\n").encode())

            if not day_rows:
                continue
            daily_count += len(day_rows)
            daily_writer.write_table(pa.Table.from_pylist(day_rows, schema=daily_schema), row_group_size=100000)
            for kind in ("WEEKLY", "MONTHLY"):
                cal = calendars[info["market"]][kind]
                stats = info["stats"]
                pkeys = sorted({pk for pk, _basis in period_aggs[kind]} | set(stats))
                period_out = []
                for pkey in pkeys:
                    meta = cal.get(pkey)
                    if meta is None:
                        continue
                    counts = stats.get(pkey, Counter())
                    calendar_count = int(counts.get("calendar", 0))
                    actual = int(counts.get("actual", 0))
                    suspended = int(counts.get("suspended", 0))
                    data_gap = int(counts.get("data_gap", 0))
                    unknown = int(counts.get("unknown", 0))
                    period_last = int(meta["last_session"])
                    is_source_edge = asof == ASOF and period_last == ASOF and natural_period_end(pkey, kind) > asof
                    view = "AS_OF_PARTIAL" if period_last > asof or is_source_edge else "CLOSED_ONLY"
                    end_date = natural_period_end(pkey, kind) if is_source_edge else period_last
                    period_last_field = None if is_source_edge else period_last
                    accounted = calendar_count == actual + suspended + data_gap + unknown
                    invalid_count = invalid_by_period[(kind, pkey)]
                    if data_gap:
                        status = "BLOCKED_BY_DATA_GAP"
                    elif unknown or not accounted:
                        status = "BLOCKED_BY_UNKNOWN_STATUS"
                    elif invalid_count:
                        status = "BLOCKED_BY_INVALID_ACTUAL_BAR"
                    elif not period_aggs[kind].get((pkey, "RAW")):
                        status = "NO_ACTUAL_BARS"
                    elif view == "CLOSED_ONLY":
                        status = "CLOSED_ONLY_READY"
                    else:
                        status = "AS_OF_PARTIAL_READY"
                    for basis in ("RAW", "QFQ"):
                        agg = period_aggs[kind].get((pkey, basis))
                        ready = basis == "RAW" or quality_base == "READY"
                        if basis == "QFQ" and not ready:
                            status_view = "BLOCKED_BY_ADJUSTMENT"
                            prices = [None] * 4
                            raw_agg = period_aggs[kind].get((pkey, "RAW"))
                            amount = raw_agg["amount"] if raw_agg else 0.0
                            volume = raw_agg["volume"] if raw_agg else 0
                            max_date = raw_agg["max_date"] if raw_agg else None
                            digest = hashlib.sha256(("BLOCKED_BY_ADJUSTMENT:" + (raw_agg["digest"].hexdigest() if raw_agg else "NO_RAW_DAILY")).encode()).hexdigest()
                            qquality = quality_base
                        elif agg:
                            status_view = status
                            prices = [agg["open"], agg["high"], agg["low"], agg["close"]]
                            amount, volume, max_date = agg["amount"], agg["volume"], agg["max_date"]
                            digest = agg["digest"].hexdigest()
                            qquality = "READY" if basis == "QFQ" else quality_base
                        else:
                            status_view = status if status == "NO_ACTUAL_BARS" else "NO_ACTUAL_BARS"
                            prices = [None] * 4
                            amount, volume, max_date, digest = 0.0, 0, None, ""
                            qquality = quality_base
                        period_out.append({"canonical_security_id": info["security_id"], "source_security_key": security,
                                           "board_scope": info["board"], "period_type": kind,
                                           "period_start_date": int(meta["first_session"]),
                                           "period_end_date": end_date, "period_last_session": period_last_field,
                                           "asof_trade_date": asof,
                                           "open": prices[0], "high": prices[1], "low": prices[2], "close": prices[3],
                                           "volume": volume, "amount": amount, "price_basis": basis,
                                           "period_view": view if status_view != "BLOCKED_BY_ADJUSTMENT" else "BLOCKED",
                                           "period_status": status_view, "calendar_count": calendar_count,
                                           "actual_count": actual, "suspended_count": suspended, "data_gap_count": data_gap,
                                           "unknown_count": unknown, "invalid_actual_count": invalid_count,
                                           "max_source_trade_date": max_date, "source_daily_digest": digest,
                                           "adjusted_quality": qquality, "adjustment_contract_id": "GBBQ_PRICE_IMPACT_CLASSIFICATION_V1",
                                           "membership_basis": "R6_2_NORMALIZED_INTERVAL", "knowledge_lineage": "DIAGNOSTIC_NON_PIT_CURRENT_METADATA_SNAPSHOT"})
                if period_out:
                    writers[kind].write_table(pa.Table.from_pylist(period_out, schema=period_schema), row_group_size=100000)
                    period_rows[kind] += len(period_out)
        for writer in (daily_writer, weekly_writer, monthly_writer):
            writer.close()
        expected_actuals = sum(len(item["actual_dates"]) for item in members.values())
        if daily_count != expected_actuals:
            raise ValueError(f"REQUIRED_SCOPE_ACTUAL_BAR_MISMATCH:{daily_count}:{expected_actuals}")
        for tmp, final in zip(temps, finals, strict=True):
            with tmp.open("rb+") as f:
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, final)
    except BaseException:
        for writer in (daily_writer, weekly_writer, monthly_writer):
            try:
                writer.close()
            except Exception:
                pass
        for tmp in temps:
            tmp.unlink(missing_ok=True)
        raise

    output_receipts = {final.name: {"path": str(final.relative_to(ROOT)).replace("\\", "/"),
                                    "sha256": sha(final), "bytes": final.stat().st_size,
                                    "row_count": pq.ParquetFile(final).metadata.num_rows}
                       for final in finals}
    classification = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))
    receipt = {
        "contract_id": contract["contract_id"], "status": "FORMAL_PERIODS_CANDIDATE_PASS",
        "capability": "RAW_QFQ_WEEKLY_MONTHLY_CLOSED_ONLY_AS_OF_EMITTED",
        "stage_status": "BLOCKED_OPEN_ADJUSTMENT_REAL_ACCEPTANCE_AND_TEMPORAL_REPLAY",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "asof_trade_date": asof, "source_cutoff": "2026-09-24",
        "inputs": {"contract_sha256": sha(CONTRACT), "raw_sha256": raw_sha,
                   "status_sha256": status_sha, "universe_sha256": sha(UNIVERSE),
                   "gbbq_sha256": action_sha, "gbbq_map_sha256": sha(MAP),
                   "classification_report_sha256": sha(CLASSIFICATION),
                   "security_dispositions_sha256": sha(DISPOSITIONS),
                   "calendar_receipt_sha256": sha(ROOT / contract["calendar_acceptance_receipt"])},
        "scope": {"membership_sessions": membership_sessions,
                  "actual_required_bars": expected_actuals, "actual_adjusted_bars_emitted": daily_count,
                  "invalid_actual_rows": invalid_actual_count, "per_security_categories_localized": classification["per_security_scope_counts"]},
        "period_rows": dict(period_rows), "outputs": output_receipts,
        "execution_identity": {"script_sha256": sha(Path(__file__).resolve()),
                               "contract_sha256": contract_sha, "raw_sha256": raw_sha},
        "acceptance_gaps": ["V4-00E independent adjusted-source/semantics acceptance remains open.",
                            "Long-suspension corporate-action and recent-listing acceptance evidence is pending.",
                            "§3C.4 full temporal replay is pending; this output alone does not close Pack A."],
        "atomicity": "each component staged, fsynced, then atomically promoted; no whole-stage accepted head published",
        "tdx_root_write_count": 0, "scanner_or_factor_run_count": 0,
        "next_stage": "V4_02_TEMPORAL_LEAKAGE_REPLAY_AFTER_ADJUSTMENT_REAL_ACCEPTANCE",
    }
    atomic_json(RECEIPT, receipt)
    print(json.dumps({"status": receipt["status"], "actual_daily": daily_count,
                      "weekly_rows": period_rows["WEEKLY"], "monthly_rows": period_rows["MONTHLY"],
                      "outputs": output_receipts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
