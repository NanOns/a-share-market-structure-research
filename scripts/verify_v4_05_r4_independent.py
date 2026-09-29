"""Independent R4 numeric and identity verification; does not call final builders."""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from math import isfinite, log
from statistics import fmean, median, pstdev
import gzip
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = "2026-09-28"
TARGET_INT = 20260928
OUT = ROOT / "reports/v4_05"


def sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def h(value: object) -> str:
    return sha256(canonical(value).encode()).hexdigest()


def atomic_json(path: Path, value: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def iso_day(raw: int | str) -> str:
    text = str(raw)
    return text if "-" in text else f"{text[:4]}-{text[4:6]}-{text[6:8]}"


def path_and_market_checks() -> tuple[dict, dict, dict]:
    report = OUT
    daily_receipt = json.loads((report / "V4_05_R4_DAILY_HISTORY_RECEIPT.json").read_text(encoding="utf-8"))
    daily_path = ROOT / daily_receipt["artifact_path"]
    reference = json.loads((report / "V4_05_R4_MARKET_REFERENCE.json").read_text(encoding="utf-8"))
    snapshot = json.loads((report / "V4_05_R4_TARGET_MARKET_SNAPSHOT.json").read_text(encoding="utf-8"))
    snapshot_ids = {row["security_id"] for row in snapshot["identities"]}
    calendar_receipt = json.loads((report / "V4_05_R3_CALENDAR_RECEIPT.json").read_text(encoding="utf-8"))
    calendar_ref = calendar_receipt["calendar_bindings"]["SSE"]
    calendar_file = ROOT / calendar_ref["path"]
    calendar = json.loads(calendar_file.read_text(encoding="utf-8"))["session_dates"]
    ti = calendar.index(TARGET)
    starts = {n: calendar[ti - n] for n in (1, 3, 5)}
    source_universe_path = ROOT / "data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz"
    v401_head = json.loads((ROOT / "data/v4/V4_01_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))
    start_members: dict[str, list[dict]] = defaultdict(list)
    with gzip.open(source_universe_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["trade_date"] in starts.values() and row["board_scope"] in ("SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"):
                start_members[row["trade_date"]].append(row)
    start_ids = {}
    for horizon, day in starts.items():
        tuples = sorted((row["security_id"], row.get("membership_basis"), row.get("source_revision_id"), row.get("eligibility_status"))
                        for row in start_members[day])
        start_ids[horizon] = h(tuples)

    # Recalculate exact end-point returns and basis identities from daily source rows.
    endpoint_days = {TARGET, *starts.values()}
    endpoints: dict[tuple[str, str], dict] = {}
    endpoint_closes: dict[str, dict[str, tuple[float, dict]]] = defaultdict(dict)
    diagnostic_days = calendar[max(0, ti - 25):ti + 1]
    diagnostic_day_set = set(diagnostic_days)
    target_cohort_closes: dict[str, dict[str, tuple[float, dict]]] = defaultdict(dict)
    with gzip.open(daily_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            day = iso_day(row["trade_date"])
            sid = row["security_id"]
            if day in endpoint_days:
                endpoints[(day, sid)] = row
            if day in diagnostic_day_set and sid in snapshot_ids and row.get("adjusted_quality") == "READY" and row.get("qfq_ohlc"):
                target_cohort_closes[day][sid] = (float(row["qfq_ohlc"][3]), row)

    market_checks = {}
    basis_by_horizon = {}
    for horizon in (1, 3, 5):
        start = starts[horizon]
        members = sorted(row["security_id"] for row in start_members[start])
        values = {}
        basis_rows = []
        for sid in members:
            left, right = endpoints.get((start, sid)), endpoints.get((TARGET, sid))
            if not left or not right or left.get("adjusted_quality") != "READY" or right.get("adjusted_quality") != "READY":
                continue
            if not left.get("qfq_ohlc") or not right.get("qfq_ohlc"):
                continue
            left_basis = (left["coordinate_basis"], left["gbbq_snapshot_identity"], left["raw_package_identity"])
            right_basis = (right["coordinate_basis"], right["gbbq_snapshot_identity"], right["raw_package_identity"])
            if left_basis != right_basis:
                continue
            first, last = float(left["qfq_ohlc"][3]), float(right["qfq_ohlc"][3])
            if first <= 0 or not isfinite(first) or not isfinite(last):
                continue
            values[sid] = last / first - 1
            basis_rows.append((sid, *right_basis))
        count = len(members)
        observed = len(values)
        cov = observed / count if count else None
        missing = count - observed
        ref_value = sum(values.values()) / observed if observed and missing / count <= 0.2 else None
        evaluator = reference["horizons"][str(horizon)]
        basis_id = h(sorted(basis_rows))
        basis_by_horizon[str(horizon)] = basis_id
        computed = {"reference_return": ref_value, "universe_count": count, "evaluable_count": observed,
                    "missing_count": missing, "coverage": cov, "evaluable_set_identity": h(sorted(values)),
                    "start_universe_snapshot_id": start_ids[horizon], "adjustment_basis_id": basis_id,
                    "start_session": start, "end_session": TARGET}
        comparisons = {}
        for key, value in computed.items():
            persisted = evaluator.get(key)
            if isinstance(value, float) and isinstance(persisted, (float, int)):
                match = abs(value - persisted) <= 1e-14
            else:
                match = value == persisted
            comparisons[key] = {"computed": value, "persisted": persisted, "match": match}
        market_checks[str(horizon)] = {"computed": computed, "comparisons": comparisons,
                                       "status": "PASS" if all(x["match"] for x in comparisons.values()) else "FAIL"}

    target_tuples = sorted((row["security_id"], row["source_security_key"], row["membership_basis"],
                            row["source_revision_id"], row["eligibility_status"]) for row in snapshot["identities"])
    target_snapshot_id = h({"contract_id": "V4_05_TARGET_MARKET_SNAPSHOT_IDENTITY_V1",
                            "target_trade_date": TARGET, "identities": target_tuples})
    target_basis_rows = sorted((row["security_id"], row["coordinate_basis"], row["adjustment_snapshot_id"],
                                row["raw_source_snapshot_id"].removeprefix("sha256-"))
                               for row in snapshot["identities"] if row["eligibility_status"] == "ADJUSTED_READY")
    # This second form is the V4-02 candidate identity; compare with the daily-history endpoint identity below.
    target_daily_basis = sorted((sid, row["coordinate_basis"], row["gbbq_snapshot_identity"], row["raw_package_identity"])
                                for (day, sid), row in endpoints.items()
                                if day == TARGET and row.get("adjusted_quality") == "READY" and row.get("qfq_ohlc"))
    target_basis_id = h(target_daily_basis)
    target_snapshot_status = (target_snapshot_id == snapshot["market_snapshot_id"] and
                              target_snapshot_id == json.loads((report / "V4_05_R4_MARKET_SNAPSHOT_IDENTITY.json").read_text(encoding="utf-8"))["target_market_snapshot_id"])
    target_basis_status = target_basis_id == snapshot["target_adjustment_basis_id"]
    market_independent = {"contract_id": "V4_05_R4_MARKET_REFERENCE_INDEPENDENT_RECALC_V1",
                          "status": "PASS" if all(x["status"] == "PASS" for x in market_checks.values()) and target_snapshot_status and target_basis_status else "FAIL",
                          "independent_method": "daily endpoint selection, return arithmetic, aggregation, and identity hashing reimplemented in verifier",
                          "horizons": market_checks,
                          "target_market_snapshot_id": {"computed": target_snapshot_id, "persisted": snapshot["market_snapshot_id"], "match": target_snapshot_status},
                          "target_basis_id": {"computed": target_basis_id, "persisted": snapshot["target_adjustment_basis_id"], "match": target_basis_status,
                                              "candidate_identity_basis_id": h(target_basis_rows),
                                              "ready_member_count": len(target_basis_rows)},
                          "input_sha256": {"daily_history": sha(daily_path), "v4_01_universe": sha(source_universe_path),
                                           "v4_01_head": sha(ROOT / "data/v4/V4_01_ACCEPTED_HEAD.json"),
                                           "calendar": sha(calendar_file)}}
    atomic_json(report / "V4_05_R4_MARKET_REFERENCE_INDEPENDENT_RECALC.json", market_independent)

    # Coordinate path diagnostic. It deliberately uses a fixed Sep-28 target cohort and is not a PIT path.
    daily_coordinate = []
    level = 1.0
    for index in range(1, len(diagnostic_days)):
        previous, day = diagnostic_days[index - 1], diagnostic_days[index]
        old, new = target_cohort_closes.get(previous, {}), target_cohort_closes.get(day, {})
        returns = []
        for sid in snapshot_ids:
            if sid in old and sid in new:
                left_meta, right_meta = old[sid][1], new[sid][1]
                if (left_meta["coordinate_basis"], left_meta["gbbq_snapshot_identity"], left_meta["raw_package_identity"]) == (right_meta["coordinate_basis"], right_meta["gbbq_snapshot_identity"], right_meta["raw_package_identity"]):
                    p0, p1 = old[sid][0], new[sid][0]
                    if p0 > 0:
                        returns.append(p1 / p0 - 1)
        daily_return = sum(returns) / len(returns) if returns else None
        if daily_return is None:
            level = None
        elif level is not None:
            level *= 1 + daily_return
        daily_coordinate.append({"trade_date": day, "start_session": previous, "daily_return": daily_return,
                                 "level": level, "evaluable_count": len(returns),
                                 "universe_count": len(snapshot_ids),
                                 "coverage": len(returns) / len(snapshot_ids),
                                 "evaluable_set_identity": h(sorted(sid for sid in snapshot_ids if sid in old and sid in new)),
                                 "quality_state": "OBSERVED" if daily_return is not None else "UNKNOWN"})
    old_path_file = ROOT / "reports/v4_03/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R3.jsonl.gz"
    old_path_receipt = json.loads((ROOT / "reports/v4_03/V4_03_MARKET_REFERENCE_PATH_RECEIPT_R3.json").read_text(encoding="utf-8"))
    if sha(old_path_file) != old_path_receipt["output_sha256"]:
        raise ValueError("accepted path source digest mismatch")
    old_path = [json.loads(line) for line in gzip.open(old_path_file, "rt", encoding="utf-8")]
    old_by_day = {row["trade_date"]: row for row in old_path}
    coord_by_day = {row["trade_date"]: row for row in daily_coordinate}
    overlap = []
    for day in diagnostic_days:
        if day in old_by_day and day in coord_by_day:
            old, new = old_by_day[day], coord_by_day[day]
            overlap.append({"trade_date": day, "accepted_daily_return": old["daily_return"],
                            "t0_coordinate_daily_return": new["daily_return"],
                            "daily_return_difference": (new["daily_return"] - old["daily_return"])
                                if new["daily_return"] is not None and old["daily_return"] is not None else None,
                            "accepted_path_level": old["level"], "coordinate_path_level_unaligned": new["level"]})
    coordinate_levels = [row["level"] for row in daily_coordinate if row["level"] is not None]
    accepted_levels = [row["level"] for row in old_path if row["trade_date"] in diagnostic_day_set]
    coord_sep24 = [row["level"] for row in daily_coordinate if row["trade_date"] <= "2026-09-24"]
    accepted_sep24 = [row["level"] for row in old_path if row["trade_date"] <= "2026-09-24"]
    def ma_stats(values: list[float]) -> dict:
        ma20 = fmean(values[-20:]) if len(values) >= 20 else None
        ma20_tminus5 = fmean(values[-25:-5]) if len(values) >= 25 else None
        return {"ma20": ma20, "ma20_t_minus_5": ma20_tminus5}
    diagnostic_ma = ma_stats(coordinate_levels)
    accepted_ma = ma_stats(accepted_sep24)
    coordinate_sep24_ma = ma_stats(coord_sep24)
    target_level = coordinate_levels[-1] if coordinate_levels else None
    reconstructed_trend = ("STRONG" if target_level is not None and diagnostic_ma["ma20"] is not None and diagnostic_ma["ma20_t_minus_5"] is not None and target_level > diagnostic_ma["ma20"] > diagnostic_ma["ma20_t_minus_5"] else
                           "WEAK" if target_level is not None and diagnostic_ma["ma20"] is not None and diagnostic_ma["ma20_t_minus_5"] is not None and target_level < diagnostic_ma["ma20"] < diagnostic_ma["ma20_t_minus_5"] else
                           "NEUTRAL" if target_level is not None and diagnostic_ma["ma20"] is not None and diagnostic_ma["ma20_t_minus_5"] is not None else "UNKNOWN")
    path_diag = {"contract_id": "V4_05_R4_MARKET_PATH_COORDINATE_DIAGNOSTIC_V1",
                 "status": "PASS" if len(daily_coordinate) >= 25 else "BLOCKED_INSUFFICIENT_COORDINATE_SESSIONS",
                 "target_trade_date": TARGET, "diagnostic_sessions": len(daily_coordinate),
                 "cohort_identity": "fixed Sep-28 target identity set; diagnostic only, not historical PIT membership",
                 "coordinate_path_series_version": "R4_T0_CURRENT_COORDINATE_FIXED_TARGET_COHORT_DIAGNOSTIC_V1",
                 "accepted_path_series_version": old_path_receipt["series_version"],
                 "accepted_path_sha256": old_path_receipt["output_sha256"],
                 "coordinate_daily_rows": daily_coordinate, "overlap_comparison": overlap,
                 "accepted_path_ma_as_of_sep24": accepted_ma,
                 "coordinate_path_ma_as_of_sep24": coordinate_sep24_ma,
                 "coordinate_path_ma_as_of_target": diagnostic_ma,
                 "ma20_difference_as_of_sep24": (coordinate_sep24_ma["ma20"] - accepted_ma["ma20"])
                    if coordinate_sep24_ma["ma20"] is not None and accepted_ma["ma20"] is not None else None,
                 "ma20_t_minus_5_difference_as_of_sep24": (coordinate_sep24_ma["ma20_t_minus_5"] - accepted_ma["ma20_t_minus_5"])
                    if coordinate_sep24_ma["ma20_t_minus_5"] is not None and accepted_ma["ma20_t_minus_5"] is not None else None,
                 "trend_axis_effect": {"coordinate_reconstruction_as_of_target": reconstructed_trend,
                                       "accepted_continuation": "UNKNOWN_NOT_AUTHORIZED",
                                       "r4_published_trend_axis": "UNKNOWN"},
                 "target_coordinate_path_row": daily_coordinate[-1] if daily_coordinate else None,
                 "accepted_history_rewritten": False}
    atomic_json(report / "V4_05_R4_MARKET_PATH_COORDINATE_DIAGNOSTIC.json", path_diag)
    continuation = {"contract_id": "V4_05_R4_MARKET_PATH_CONTINUATION_V1", "decision": "OPTION_C_FAIL_CLOSED",
                    "status": "DEGRADED_PASS", "rebase_policy": old_path_receipt["rebase_policy"],
                    "prior_path_artifact": old_path_file.relative_to(ROOT).as_posix(),
                    "prior_path_sha256": old_path_receipt["output_sha256"],
                    "prior_series_version": old_path_receipt["series_version"],
                    "prior_row_trade_date": old_path[-1]["trade_date"],
                    "prior_row_output_digest": old_path[-1]["output_digest"],
                    "target_reference_output_digest": reference["horizons"]["1"]["output_digest"],
                    "target_start_universe_snapshot_id": reference["horizons"]["1"]["start_universe_snapshot_id"],
                    "target_evaluable_set_identity": reference["horizons"]["1"]["evaluable_set_identity"],
                    "target_adjustment_basis_id": reference["horizons"]["1"]["adjustment_basis_id"],
                    "path_level": None, "output_digest": None,
                    "target_path_row_published": False, "trend_axis": "UNKNOWN",
                    "reason": "accepted R3 series prohibits unknown suffix until a new series version; no R4 contract migration authorizes appending a T0 fixed-cohort row",
                    "coordinate_diagnostic_artifact": "reports/v4_05/V4_05_R4_MARKET_PATH_COORDINATE_DIAGNOSTIC.json",
                    "accepted_rows_modified": False}
    atomic_json(report / "V4_05_R4_MARKET_PATH_CONTINUATION.json", continuation)
    return market_independent, path_diag, continuation


def load_field(row: dict, name: str):
    item = row["fields"].get(name, {})
    return item.get("value") if item.get("quality_state") == "OBSERVED" else None


def independent_samples() -> dict:
    report = OUT
    factors_receipt = json.loads((report / "V4_05_R4_FULL_SCOPE_FACTORS_RECEIPT.json").read_text(encoding="utf-8"))
    factor_path = ROOT / factors_receipt["artifact_path"]
    factor_rows = {row["security_id"]: row for row in (json.loads(line) for line in gzip.open(factor_path, "rt", encoding="utf-8"))}
    target_snapshot = json.loads((report / "V4_05_R4_TARGET_MARKET_SNAPSHOT.json").read_text(encoding="utf-8"))
    target_meta = {row["security_id"]: row for row in target_snapshot["identities"]}
    v401_head = json.loads((ROOT / "data/v4/V4_01_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))
    relation = v401_head["relation_resolution"]
    code_change_key = relation["new_code"]
    params = json.loads((ROOT / "config/v4_04_parameter_set_v1.json").read_text(encoding="utf-8"))
    p = {item["parameter_id"].removeprefix("V4_04_"): item["value"] for item in params["parameters"]}
    calendars_receipt = json.loads((report / "V4_05_R3_CALENDAR_RECEIPT.json").read_text(encoding="utf-8"))
    calendars = {}
    for market in ("SSE", "SZSE"):
        bind = calendars_receipt["calendar_bindings"][market]
        calendars[market] = json.loads((ROOT / bind["path"]).read_text(encoding="utf-8"))["session_dates"]

    labeled: dict[str, set[str]] = defaultdict(set)
    by_board = defaultdict(list)
    for sid, row in factor_rows.items():
        by_board[row["board_scope"]].append(sid)
        eligibility = target_meta[sid]["eligibility_status"]
        if eligibility == "ADJUSTED_UNAVAILABLE_NO_T0_RAW":
            labeled[sid].add("no_T0_bar")
        if eligibility != "ADJUSTED_READY":
            labeled[sid].add("adjustment_unknown")
        if row["source_security_key"] == code_change_key:
            labeled[sid].add("code_change_confirmed_same_entity")
        if row["fields"]["ret20"].get("unknown_reason") in ("INSUFFICIENT_SESSION_HISTORY",) or row["fields"]["ma60"].get("unknown_reason") == "INSUFFICIENT_HISTORY":
            labeled[sid].add("short_history")
    # Three fully observed normal examples per board.
    for board, ids in by_board.items():
        picks = 0
        for sid in sorted(ids):
            row = factor_rows[sid]
            if target_meta[sid]["eligibility_status"] == "ADJUSTED_READY" and all(load_field(row, field) is not None for field in ("ret1", "ret5", "ret20", "ma20", "ma60", "atr20", "amount_ratio20")):
                labeled[sid].add("normal_ready")
                picks += 1
                if picks == 3:
                    break
    for category, maximum in (("no_T0_bar", 4), ("adjustment_unknown", 4), ("short_history", 2), ("code_change_confirmed_same_entity", 1)):
        already = sum(category in cats for cats in labeled.values())
        for sid in sorted(factor_rows):
            if already >= maximum:
                break
            if category in labeled[sid] and "normal_ready" not in labeled[sid]:
                already += 1
    # Boundary-like means a return-distribution tail sample; it is not a limit-event claim.
    observed_ret = [(abs(float(row["fields"]["ret1"]["value"])), sid) for sid, row in factor_rows.items()
                    if row["fields"]["ret1"]["quality_state"] == "OBSERVED" and target_meta[sid]["eligibility_status"] == "ADJUSTED_READY"]
    for _, sid in sorted(observed_ret, reverse=True)[:2]:
        labeled[sid].add("boundary_like_return_tail")
    selected = {sid: sorted(cats) for sid, cats in labeled.items() if cats}

    histories: dict[str, list[dict]] = defaultdict(list)
    sample_target_seen = set()
    endpoint_bars = {}
    diagnostics_days = set()
    daily_receipt = json.loads((report / "V4_05_R4_DAILY_HISTORY_RECEIPT.json").read_text(encoding="utf-8"))
    daily_path = ROOT / daily_receipt["artifact_path"]
    rps_endpoints: dict[str, dict[str, dict]] = {"5": {}, "20": {}}
    rps_calendar_by_board = {}
    for sid, row in factor_rows.items():
        market = "SSE" if row["board_scope"] in ("SH_MAIN", "STAR") else "SZSE"
        cal = calendars[market]
        index = cal.index(TARGET)
        rps_calendar_by_board[sid] = {"1": cal[index - 1], "5": cal[index - 5], "20": cal[index - 20]}
    start_dates = {"1": next(iter(rps_calendar_by_board.values()))["1"],
                   "5": next(iter(rps_calendar_by_board.values()))["5"],
                   "20": next(iter(rps_calendar_by_board.values()))["20"]}
    with gzip.open(daily_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            sid, day = row["security_id"], iso_day(row["trade_date"])
            if sid in selected:
                histories[sid].append(row)
                if day == TARGET:
                    sample_target_seen.add(sid)
            if day in set(start_dates.values()) | {TARGET}:
                endpoint_bars[(day, sid)] = row
    # Independent return fields for all target entities provide a separate RPS ranking.
    returns_by_horizon = {}
    for horizon in (5, 20):
        start = start_dates[str(horizon)]
        values = {}
        for sid in factor_rows:
            left, right = endpoint_bars.get((start, sid)), endpoint_bars.get((TARGET, sid))
            if left and right and left.get("qfq_ohlc") and right.get("qfq_ohlc") and left["adjusted_quality"] == right["adjusted_quality"] == "READY":
                p0, p1 = float(left["qfq_ohlc"][3]), float(right["qfq_ohlc"][3])
                if p0 > 0:
                    values[sid] = p1 / p0 - 1
        returns_by_horizon[horizon] = values
    rps_values = {}
    for horizon, values in returns_by_horizon.items():
        denominator = len(values) - 1
        ranked = {}
        for sid, value in values.items():
            less = sum(x < value for x in values.values())
            equal = sum(x == value for x in values.values())
            ranked[sid] = 100 * (less + 0.5 * (equal - 1)) / denominator if denominator > 0 else None
        rps_values[horizon] = ranked
    ref_receipt = json.loads((report / "V4_05_R4_MARKET_REFERENCE_INDEPENDENT_RECALC.json").read_text(encoding="utf-8"))
    ref1 = ref_receipt["horizons"]["1"]["computed"]["reference_return"]
    market_parameters = json.loads((ROOT / "config/v4_03_parameter_set_v1.json").read_text(encoding="utf-8"))["engineering_candidate_thresholds"]
    all_amount_ratios = [float(load_field(row, "amount_ratio20")) for row in factor_rows.values() if load_field(row, "amount_ratio20") is not None]
    amount_median = median(all_amount_ratios) if all_amount_ratios else None
    participation_expected = ("EXPANDING" if amount_median >= market_parameters["market_participation_expanding"] else
                              "THIN" if amount_median < market_parameters["market_participation_thin"] else "NORMAL") if amount_median is not None else None
    regime = json.loads((report / "V4_05_R4_MARKET_REGIME.json").read_text(encoding="utf-8"))
    participation_match = participation_expected == regime["target_row"]["participation_axis"]
    trend_fail_closed_match = regime["target_row"]["trend_axis"] == "UNKNOWN" and regime["trend"]["quality_state"] == "UNKNOWN"
    profile_path = ROOT / "reports/v4_05/staging/V4_05_R4_FULL_MARKET_CORE_PROFILE.jsonl.gz"
    profiles = {row["security_id"]: row for row in (json.loads(line) for line in gzip.open(profile_path, "rt", encoding="utf-8")) if row["security_id"] in selected}
    period_path = ROOT / "reports/v4_05/staging/V4_05_R4_PERIOD_ASOF.jsonl.gz"
    period_rows: dict[str, dict[str, list[dict]]] = defaultdict(lambda: {"WEEKLY": [], "MONTHLY": []})
    with gzip.open(period_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["security_id"] in selected and row["price_basis"] == "QFQ":
                period_rows[row["security_id"]][row["period_type"]].append(row)

    def factor_num(row, name):
        field = row["fields"].get(name, {})
        return field.get("value") if field.get("quality_state") == "OBSERVED" else None

    def state_from(inputs: dict, kind: str) -> str:
        if kind == "weekly_trend_state" or kind == "monthly_trend_state":
            period = "weekly" if kind.startswith("weekly") else "monthly"
            rows = [x for x in inputs["period_rows"] if x["period_last_session"] <= TARGET and x["period_view"] == "CLOSED_ONLY"]
            window = 5 if period == "weekly" else 3
            needed = rows[-window-1:]
            if len(needed) != window + 1 or any(x["period_status"] != "CLOSED_ONLY_READY" or x["ohlc"] is None for x in needed):
                return "UNKNOWN"
            closes = [float(x["ohlc"][3]) for x in needed]
            ma_now, ma_before, close = fmean(closes[-window:]), fmean(closes[-window-1:-1]), closes[-1]
            if period == "weekly":
                return "WEEKLY_UP" if close > ma_now > ma_before else "WEEKLY_DOWN" if close < ma_now < ma_before else "WEEKLY_FLAT"
            return "MONTHLY_UP" if close > ma_now > ma_before else "MONTHLY_DOWN" if close < ma_now < ma_before else "MONTHLY_FLAT"
        f = inputs["fields"]
        def n(name): return inputs.get(name)
        if kind == "position_state":
            bias, pos = n("bias20_atr"), n("pos60")
            if bias is None or pos is None: return "UNKNOWN"
            return "EXTENDED" if bias >= p["POSITION_EXTENDED_BIAS"] else "HIGH_ZONE" if pos >= p["POSITION_HIGH"] else "MID_HIGH" if pos >= p["POSITION_MID_HIGH"] else "MID_ZONE" if pos >= p["POSITION_MID"] else "MID_LOW" if pos >= p["POSITION_MID_LOW"] else "LOW_ZONE"
        if kind == "trend_state":
            c, ma20, ma60, s20, s60, hh, ll, damage, atr = (n(x) for x in ("close","ma20","ma60","slope20","slope60","hh_progress","ll_progress","core_price_damage","atr20"))
            if any(x is None for x in (c,ma20,ma60,s20,s60,hh,ll,damage,atr)): return "UNKNOWN"
            db=p["SLOPE_DEADBAND_ATR"]
            if c<ma20 and s20<-db and s60<-db and ll: return "DOWNTREND_STRONG"
            if c>ma20 and s20>db and (c>ma60 or s60>db) and hh and not damage: return "UPTREND_STRONG"
            if c<ma20 and s20<-db: return "DOWNTREND"
            if c>ma20 and s20>db and not damage: return "UPTREND"
            if c<ma20: return "SIDEWAYS_WEAK"
            if c>ma20: return "SIDEWAYS_STRONG"
            return "SIDEWAYS"
        if kind == "compression_state":
            ran, atrr, volr, amount, liquid = (n(x) for x in ("range_ratio","atr_ratio","vol_ratio","amount_ratio20","minimum_liquidity"))
            if any(x is None for x in (ran,atrr,volr,amount,liquid)): return "UNKNOWN"
            if atrr>=p["COMPRESS_EXTREME"] or volr>=p["COMPRESS_EXTREME"]: return "EXPANDING_EXTREME"
            if atrr>=p["COMPRESS_EXPAND"] or volr>=p["COMPRESS_EXPAND"]: return "EXPANDING"
            if ran<=p["COMPRESS_STRONG_RANGE"] and atrr<=p["COMPRESS_STRONG_ATR_VOL"] and volr<=p["COMPRESS_STRONG_ATR_VOL"] and amount<=p["COMPRESS_STRONG_AMOUNT"] and liquid: return "COMPRESSING_STRONG"
            if ran<=p["COMPRESS_RANGE"] and atrr<=p["COMPRESS_ATR_VOL"] and volr<=p["COMPRESS_ATR_VOL"] and liquid: return "COMPRESSING"
            return "NORMAL"
        return "UNKNOWN"

    sample_rows = []
    numeric_mismatches = []
    state_mismatches = []
    fields_checked = Counter()
    target_start_dates = {horizon: starts for horizon, starts in [(1, None)]} if False else None
    market_start_1 = json.loads((report / "V4_05_R4_MARKET_REFERENCE.json").read_text(encoding="utf-8"))["horizons"]["1"]["start_session"]
    rps_target_dates = {horizon: (calendars["SSE"][calendars["SSE"].index(TARGET)-horizon]) for horizon in (1,5,20)}
    for sid, categories in sorted(selected.items()):
        artifact = factor_rows[sid]
        bars = [row for row in histories.get(sid, []) if row.get("qfq_ohlc") and row.get("adjusted_quality") == "READY"]
        bars.sort(key=lambda row: row["trade_date"])
        closebars = [{"date": iso_day(x["trade_date"]), "open": float(x["qfq_ohlc"][0]), "high": float(x["qfq_ohlc"][1]),
                      "low": float(x["qfq_ohlc"][2]), "close": float(x["qfq_ohlc"][3]), "amount": float(x["amount"]),
                      "volume": float(x["volume"])} for x in bars]
        calc = {"close": closebars[-1]["close"] if closebars and closebars[-1]["date"] == TARGET and target_meta[sid]["eligibility_status"] == "ADJUSTED_READY" else None}
        closes = [x["close"] for x in closebars]
        highs = [x["high"] for x in closebars]
        lows = [x["low"] for x in closebars]
        amounts = [x["amount"] for x in closebars]
        def put_mean(name, values): calc[name] = fmean(values) if values else None
        put_mean("ma20", closes[-20:] if len(closes)>=20 else [])
        put_mean("ma60", closes[-60:] if len(closes)>=60 else [])
        tr20 = [max(closebars[i]["high"]-closebars[i]["low"], abs(closebars[i]["high"]-closebars[i-1]["close"]), abs(closebars[i]["low"]-closebars[i-1]["close"])) for i in range(len(closebars)-20,len(closebars))] if len(closebars)>=21 else []
        put_mean("atr20", tr20)
        calc["amount_ratio20"] = (amounts[-1]/fmean(amounts[-21:-1])) if len(amounts)>=21 and fmean(amounts[-21:-1]) else None
        calendar_id = "SSE" if artifact["board_scope"] in ("SH_MAIN","STAR") else "SZSE"
        cal=calendars[calendar_id]; endpoint_index=cal.index(TARGET)
        for horizon in (1,5,20):
            start=cal[endpoint_index-horizon]
            left=next((x for x in closebars if x["date"]==start),None)
            right=next((x for x in closebars if x["date"]==TARGET),None)
            calc[f"ret{horizon}"]=(right["close"]/left["close"]-1) if left and right and left["close"]>0 else None
        calc["rps5"]=rps_values[5].get(sid)
        calc["rps20"]=rps_values[20].get(sid)
        calc["rel_market_1"]=(calc["ret1"]-ref1) if calc["ret1"] is not None and ref1 is not None else None
        # Independent state inputs from the same raw history windows.
        if len(closebars)>=70 and calc["atr20"] and calc["atr20"]>0:
            calc["slope20"]=(fmean(closes[-20:])-fmean(closes[-25:-5]))/calc["atr20"]
            calc["slope60"]=(fmean(closes[-60:])-fmean(closes[-70:-10]))/calc["atr20"]
        else: calc["slope20"]=calc["slope60"]=None
        calc["hh_progress"]=(max(highs[-5:])>max(highs[-10:-5])) if len(highs)>=10 else None
        calc["ll_progress"]=(min(lows[-5:])<min(lows[-10:-5])) if len(lows)>=10 else None
        calc["core_price_damage"]=(closebars[-1]["close"] < min(lows[-21:-1]) - 0.5*calc["atr20"] and calc["ret1"]<0) if len(lows)>=21 and calc["atr20"] is not None and calc["ret1"] is not None else None
        calc["pos60"]=(closebars[-1]["close"]-min(lows[-60:]))/(max(highs[-60:])-min(lows[-60:])) if len(lows)>=60 and max(highs[-60:])>min(lows[-60:]) else None
        calc["bias20_atr"]=(closebars[-1]["close"]-calc["ma20"])/calc["atr20"] if closebars and calc["ma20"] is not None and calc["atr20"] else None
        ran=(max(highs[-5:])-min(lows[-5:]))/(max(highs[-20:])-min(lows[-20:])) if len(highs)>=20 and max(highs[-20:])>min(lows[-20:]) else None
        atr5_vals=[max(closebars[i]["high"]-closebars[i]["low"],abs(closebars[i]["high"]-closebars[i-1]["close"]),abs(closebars[i]["low"]-closebars[i-1]["close"])) for i in range(len(closebars)-5,len(closebars))] if len(closebars)>=6 else []
        atr5=fmean(atr5_vals) if atr5_vals else None
        calc["range_ratio"]=ran
        calc["atr_ratio"]=atr5/calc["atr20"] if atr5 is not None and calc["atr20"] else None
        # Volatility uses the exact calendar-session return window and fails closed when a bar is missing.
        for n in (5,20):
            dates=cal[endpoint_index-n:endpoint_index+1]
            obs=[]
            close_by_day={x["date"]:x["close"] for x in closebars}
            if all(day in close_by_day for day in dates):
                obs=[log(close_by_day[b]/close_by_day[a]) for a,b in zip(dates,dates[1:])]
            calc[f"vol{n}"]=pstdev(obs) if len(obs)==n else None
        calc["vol_ratio"]=calc["vol5"]/calc["vol20"] if calc["vol5"] is not None and calc["vol20"] else None
        calc["minimum_liquidity"]=(fmean(amounts[-21:-1])>=p["MINIMUM_LIQUIDITY_CNY"]) if len(amounts)>=21 else None
        calc["range_ratio"]=ran
        profile=profiles.get(sid,{})
        periods_for_id=period_rows[sid]
        inputs={**calc,"fields":artifact["fields"],"period_rows":periods_for_id["WEEKLY"]}
        state_expectations={name: state_from(inputs,name) for name in ("trend_state","position_state","compression_state")}
        inputs["period_rows"]=periods_for_id["MONTHLY"]
        state_expectations["monthly_trend_state"]=state_from(inputs,"monthly_trend_state")
        inputs["period_rows"]=periods_for_id["WEEKLY"]
        state_expectations["weekly_trend_state"]=state_from(inputs,"weekly_trend_state")
        comparisons={}
        for name in ("ret1","ret5","ret20","ma20","ma60","atr20","amount_ratio20","rps5","rps20","rel_market_1"):
            actual=load_field(artifact,name)
            expected=calc.get(name)
            if actual is None and expected is None: match=True
            elif actual is None or expected is None: match=False
            else: match=abs(float(actual)-float(expected)) <= 1e-10*max(1,abs(float(actual)))
            comparisons[name]={"independently_recomputed":expected,"artifact":actual,"match":match}
            fields_checked[name]+=1
            if not match: numeric_mismatches.append({"security_id":sid,"field":name,"expected":expected,"actual":actual})
        state_comparisons={}
        for name, expected in state_expectations.items():
            actual=profile.get("states",{}).get(name,{}).get("value")
            match=expected==actual
            state_comparisons[name]={"independently_recomputed":expected,"artifact":actual,"match":match}
            if not match: state_mismatches.append({"security_id":sid,"state":name,"expected":expected,"actual":actual})
        sample_rows.append({"security_id":sid,"source_security_key":artifact["source_security_key"],"board_scope":artifact["board_scope"],
                            "sample_categories":categories,"target_bar_present":sid in sample_target_seen,
                            "independently_recomputed":{name:calc.get(name) for name in ("ret1","ret5","ret20","ma20","ma60","atr20","amount_ratio20","rps5","rps20","rel_market_1")},
                            "field_comparisons":comparisons,"state_comparisons":state_comparisons})
    matrix={}
    for category in ("normal_ready","no_T0_bar","adjustment_unknown","short_history","code_change_confirmed_same_entity","boundary_like_return_tail"):
        group=[sid for sid,cats in selected.items() if category in cats]
        matrix[category]={"count":len(group),"security_ids":group}
    check_ok=(len(selected)>=20 and len({factor_rows[sid]["board_scope"] for sid in selected})==4 and
              not numeric_mismatches and not state_mismatches and
              participation_match and trend_fail_closed_match and
              all(len([sid for sid,cats in selected.items() if category in cats])>0 for category in ("normal_ready","no_T0_bar","adjustment_unknown","short_history","code_change_confirmed_same_entity","boundary_like_return_tail")))
    result={"contract_id":"V4_05_R4_INDEPENDENT_NUMERIC_POSTCHECK_V1","status":"PASS" if check_ok else "FAIL",
            "unique_sample_count":len(selected),"board_coverage":sorted({factor_rows[sid]["board_scope"] for sid in selected}),
            "sample_category_matrix":matrix,"sample_recomputations":sample_rows,
            "field_comparison_count":dict(fields_checked),"numeric_mismatches":numeric_mismatches,"state_mismatches":state_mismatches,
            "rps_reference_set_counts":{"5":len(returns_by_horizon[5]),"20":len(returns_by_horizon[20])},
            "independent_market_reference_1_3_5":ref_receipt["horizons"],
            "market_axis_recalculation":{"participation_axis":{"median_amount_ratio20":amount_median,
                "expanding_threshold":market_parameters["market_participation_expanding"],
                "thin_threshold":market_parameters["market_participation_thin"],
                "computed":participation_expected,"persisted":regime["target_row"]["participation_axis"],"match":participation_match},
                "trend_axis":{"computed":"UNKNOWN_FAIL_CLOSED","persisted":regime["target_row"]["trend_axis"],"match":trend_fail_closed_match}},
            "target_snapshot_identity_recomputed":json.loads((report/"V4_05_R4_MARKET_REFERENCE_INDEPENDENT_RECALC.json").read_text(encoding="utf-8"))["target_market_snapshot_id"],
            "target_basis_identity_recomputed":json.loads((report/"V4_05_R4_MARKET_REFERENCE_INDEPENDENT_RECALC.json").read_text(encoding="utf-8"))["target_basis_id"],
            "target_path_row":json.loads((report/"V4_05_R4_MARKET_PATH_COORDINATE_DIAGNOSTIC.json").read_text(encoding="utf-8"))["target_coordinate_path_row"],
            "trend_axis":{"published":"UNKNOWN","diagnostic":json.loads((report/"V4_05_R4_MARKET_PATH_COORDINATE_DIAGNOSTIC.json").read_text(encoding="utf-8"))["trend_axis_effect"]},
            "independent_method":"manual endpoint/window selection, summary arithmetic, midrank, state branch rules, and period window selection; no production final builder invoked",
            "limits":{"boundary_like_return_tail":"return-distribution boundary sample, not an exchange price-limit event claim",
                      "code_change_sample":"uses externally accepted V4-01 confirmed same-entity relation resolution"}}
    atomic_json(report/"V4_05_R4_INDEPENDENT_NUMERIC_POSTCHECK.json",result)
    return result


def main() -> dict:
    market, path, continuation=path_and_market_checks()
    numeric=independent_samples()
    overall={"contract_id":"V4_05_R4_INDEPENDENT_POSTCHECK_V1",
             "status":"PASS" if market["status"]=="PASS" and path["status"]=="PASS" and continuation["decision"]=="OPTION_C_FAIL_CLOSED" and numeric["status"]=="PASS" else "FAIL",
             "market_reference_status":market["status"],"market_path_diagnostic_status":path["status"],
             "continuation_decision":continuation["decision"],"numeric_postcheck_status":numeric["status"],
             "sample_count":numeric["unique_sample_count"],"external_acceptance":"PENDING"}
    atomic_json(OUT/"V4_05_R4_INDEPENDENT_POSTCHECK.json",overall)
    return overall


if __name__=="__main__":
    print(json.dumps(main(),ensure_ascii=False,sort_keys=True))
