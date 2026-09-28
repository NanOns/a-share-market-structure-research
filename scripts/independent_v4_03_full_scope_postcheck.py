"""Independent formula replay for all 47 V4-03 candidate fields.

This file deliberately imports no V4 factor producer, rolling-window helper,
RPS function, or market-reference implementation. It reads only frozen V4-01/
V4-02 inputs and the versioned parameter registry, then compares its results
with the diagnostic candidate artifact.
"""

from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import time

import duckdb


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "reports/v4_03/staging/V4_03_CORE_REQUIRED_SCOPE_DIAGNOSTIC_R1.jsonl.gz"
CANDIDATE = ROOT / "reports/v4_03/staging/V4_03_FULL_SCOPE_CANDIDATE_R1.jsonl.gz"
CANDIDATE_RECEIPT = ROOT / "reports/v4_03/V4_03_FULL_SCOPE_CANDIDATE_RECEIPT_R1.json"
OUTPUT = ROOT / "reports/v4_03/V4_03_INDEPENDENT_POSTCHECK_R1.json"
REQUIRED = {"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"}
OFFSETS = (0, 1, 3, 5, 20, 6, 8, 23)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def valid_actual(rows):
    if any(r["state"] != "ACTUAL" or r["bar"] is None for r in rows):
        return "MISSING_OR_SUSPENDED_ENDPOINT"
    bars = [r["bar"] for r in rows]
    if any(not b["basis"] or not b["source"] for b in bars):
        return "ADJUSTMENT_OR_SOURCE_IDENTITY_UNKNOWN"
    if len({b["basis"] for b in bars}) != 1:
        return "MIXED_ADJUSTMENT_IDENTITY"
    if any(not all(finite(b[k]) for k in ("open", "high", "low", "close", "amount", "volume")) for b in bars):
        return "NONFINITE_INPUT"
    if any(min(b["open"], b["high"], b["low"], b["close"]) <= 0 or b["high"] < b["low"] for b in bars):
        return "INVALID_PRICE"
    return None


def tech_window(history, n, exclude_current=False):
    end = len(history) - int(exclude_current)
    if end <= 0:
        return [], "INSUFFICIENT_HISTORY"
    if not exclude_current and history[end - 1]["state"] in {"UNKNOWN", "ADJUSTMENT_UNKNOWN", "IDENTITY_UNKNOWN", "PRE_LISTING"}:
        state = history[end - 1]["state"]
        return [history[end - 1]], state if state in {"ADJUSTMENT_UNKNOWN", "IDENTITY_UNKNOWN"} else "CURRENT_BAR_UNAVAILABLE"
    actual = []
    start = end
    for i in range(end - 1, -1, -1):
        row = history[i]
        if row["state"] in {"UNKNOWN", "ADJUSTMENT_UNKNOWN", "IDENTITY_UNKNOWN"}:
            reason = "UNEXPLAINED_DATA_GAP" if row["state"] == "UNKNOWN" else row["state"]
            return history[i:end], reason
        if row["state"] == "PRE_LISTING":
            break
        if row["state"] == "ACTUAL":
            actual.append(row)
            if len(actual) == n:
                start = i
                break
    if len(actual) < n:
        return history[max(0, start):end], "INSUFFICIENT_HISTORY"
    return history[start:end], None


def bars(rows):
    return [r["bar"] for r in rows if r["state"] == "ACTUAL" and r["bar"] is not None]


def session_window(history, n):
    if len(history) < n + 1:
        return history, "INSUFFICIENT_SESSION_HISTORY"
    rows = history[-n - 1:]
    if rows[0]["state"] != "ACTUAL" or rows[-1]["state"] != "ACTUAL":
        special = next((r["state"] for r in (rows[0], rows[-1]) if r["state"] in {"ADJUSTMENT_UNKNOWN", "IDENTITY_UNKNOWN"}), None)
        return rows, special or "MISSING_OR_SUSPENDED_ENDPOINT"
    if any(r["state"] in {"UNKNOWN", "ADJUSTMENT_UNKNOWN", "IDENTITY_UNKNOWN"} for r in rows):
        special = next((r["state"] for r in rows if r["state"] in {"ADJUSTMENT_UNKNOWN", "IDENTITY_UNKNOWN"}), None)
        return rows, special or "UNEXPLAINED_DATA_GAP"
    return rows, None


def independent_core(history, sid, damage_multiple):
    out = {}

    def put(name, n, fn, prior=False, current_required=False, extra=0):
        rows, error = tech_window(history, n + extra, exclude_current=prior)
        reason = error or valid_actual([r for r in rows if r["state"] == "ACTUAL"])
        if current_required:
            row = history[-1]
            state = row["state"]
            current_error = state if state in {"ADJUSTMENT_UNKNOWN", "IDENTITY_UNKNOWN"} else "CURRENT_BAR_UNAVAILABLE" if state != "ACTUAL" else valid_actual([row])
            reason = reason or current_error
            if not reason and rows and bars(rows)[-1]["basis"] != row["bar"]["basis"]:
                reason = "MIXED_ADJUSTMENT_IDENTITY"
        values = bars(rows)
        value = None
        if not reason:
            try:
                value = fn(values)
                if value is None or (isinstance(value, float) and not math.isfinite(value)):
                    reason = "ZERO_DENOMINATOR"
            except ZeroDivisionError:
                reason = "ZERO_DENOMINATOR"
        out[name] = (None if reason else value, "UNKNOWN" if reason else "OBSERVED", reason)

    for n in (5, 20, 60):
        put(f"ma{n}", n, lambda b: mean([x["close"] for x in b]))
        put(f"hhv{n}", n, lambda b: max(x["high"] for x in b))
        put(f"llv{n}", n, lambda b: min(x["low"] for x in b))
        put(f"prior_high{n}", n, lambda b: max(x["high"] for x in b), prior=True)
        put(f"prior_low{n}", n, lambda b: min(x["low"] for x in b), prior=True)
    for n in (5, 20):
        for label in ("amount", "volume"):
            put(f"{label}_ratio{n}", n,
                lambda b, label=label: history[-1]["bar"][label] / mean([x[label] for x in b]) if mean([x[label] for x in b]) != 0 else None,
                prior=True, current_required=True)

    for n in (1, 3, 5, 20):
        rows, err = session_window(history, n)
        reason = err or valid_actual([rows[0], rows[-1]]) if rows else err
        if not reason and rows[0]["bar"]["close"] == 0:
            reason = "ZERO_DENOMINATOR"
        out[f"ret{n}"] = (None if reason else rows[-1]["bar"]["close"] / rows[0]["bar"]["close"] - 1,
                           "UNKNOWN" if reason else "OBSERVED", reason)
    for n in (5, 20):
        rows, err = session_window(history, n)
        reason = err or valid_actual(rows) if rows else err
        rets = [math.log(b["close"] / a["close"]) for a, b in zip([r["bar"] for r in rows[:-1]], [r["bar"] for r in rows[1:]])] if not reason else []
        value = math.sqrt(sum((x - mean(rets)) ** 2 for x in rets) / len(rets)) if rets else None
        out[f"vol{n}"] = (value, "UNKNOWN" if reason else "OBSERVED", reason)

    put("tr", 1, lambda b: max(b[-1]["high"] - b[-1]["low"], abs(b[-1]["high"] - b[-2]["close"]), abs(b[-1]["low"] - b[-2]["close"])), current_required=True, extra=1)
    for n in (5, 20):
        put(f"atr{n}", n, lambda b: mean([max(x["high"] - x["low"], abs(x["high"] - p["close"]), abs(x["low"] - p["close"])) for p, x in zip(b[:-1], b[1:])]), extra=1)
    for n, offset in ((20, 5), (60, 10)):
        rows, reason = tech_window(history, n + offset)
        reason = reason or valid_actual([r for r in rows if r["state"] == "ACTUAL"])
        seq = bars(rows)
        if not reason:
            atr = out["atr20"]
            reason = atr[2]
        value = None
        if not reason:
            if atr[0] <= 0:
                reason = "ZERO_ATR"
            else:
                now = mean([x["close"] for x in seq[-n:]])
                old = mean([x["close"] for x in seq[-n-offset:-offset]])
                value = (now - old) / atr[0]
        out[f"slope{n}"] = (None if reason else value, "UNKNOWN" if reason else "OBSERVED", reason)
    put("hh_progress", 10, lambda b: max(x["high"] for x in b[-5:]) > max(x["high"] for x in b[:5]))
    put("ll_progress", 10, lambda b: min(x["low"] for x in b[-5:]) < min(x["low"] for x in b[:5]))
    put("clv", 1, lambda b: (b[-1]["close"] - b[-1]["low"]) / (b[-1]["high"] - b[-1]["low"]) if b[-1]["high"] != b[-1]["low"] else None, current_required=True)

    rows, reason = tech_window(history, 60, exclude_current=True)
    reason = reason or valid_actual([r for r in rows if r["state"] == "ACTUAL"])
    target = history[-1]
    if not reason:
        reason = valid_actual([target])
    if not reason and bars(rows)[-1]["basis"] != target["bar"]["basis"]:
        reason = "MIXED_ADJUSTMENT_IDENTITY"
    values = [b["close"] for b in bars(rows)]
    pct = 100 * (sum(x < target["bar"]["close"] for x in values) + .5 * sum(x == target["bar"]["close"] for x in values)) / 60 if not reason else None
    out["prior60_percentile"] = (pct, "UNKNOWN" if reason else "OBSERVED", reason)

    def derived(name, num, den, dependencies, calc):
        reason = next((out[x][2] for x in dependencies if out[x][2]), None)
        value = None
        if not reason:
            value = calc(out[num][0], out[den][0])
            if value is None or isinstance(value, float) and not math.isfinite(value):
                reason = "ZERO_DENOMINATOR"
        out[name] = (None if reason else value, "UNKNOWN" if reason else "OBSERVED", reason)

    # The closures below evaluate already independently recalculated primitives.
    reason = next((out[x][2] for x in ("hhv60", "llv60") if out[x][2]), None)
    pos = None
    if not reason:
        current_state = history[-1]["state"]
        reason = current_state if current_state in {"ADJUSTMENT_UNKNOWN", "IDENTITY_UNKNOWN"} else "CURRENT_BAR_UNAVAILABLE" if current_state != "ACTUAL" else valid_actual([history[-1]])
        if not reason:
            den = out["hhv60"][0] - out["llv60"][0]
            pos = (history[-1]["bar"]["close"] - out["llv60"][0]) / den if den else None
            if pos is None:
                reason = "ZERO_DENOMINATOR"
    out["pos60"] = (None if reason else pos, "UNKNOWN" if reason else "OBSERVED", reason)
    derived("range_ratio", "hhv5", "hhv20", ("hhv5", "llv5", "hhv20", "llv20"),
            lambda a, b: (a - out["llv5"][0]) / (b - out["llv20"][0]) if b != out["llv20"][0] else None)
    derived("atr_ratio", "atr5", "atr20", ("atr5", "atr20"), lambda a, b: a / b if b and b > 0 else None)
    derived("vol_ratio", "vol5", "vol20", ("vol5", "vol20"), lambda a, b: a / b if b and b > 0 else None)
    deps = ("prior_low20", "atr20", "ret1")
    reason = next((out[x][2] for x in deps if out[x][2]), None)
    damage = None if reason else (history[-1]["bar"]["close"] < out["prior_low20"][0] - damage_multiple * out["atr20"][0] and out["ret1"][0] < 0)
    out["core_price_damage"] = (damage, "UNKNOWN" if reason else "OBSERVED", reason)
    return out


def midranks(values, members):
    vals = {s: values.get(s) for s in sorted(set(members)) if values.get(s) is not None and finite(values[s])}
    n = len(vals)
    scores = {}
    for sid in sorted(set(members)):
        value = vals.get(sid)
        scores[sid] = None if n < 2 or value is None else 100 * (sum(x < value for x in vals.values()) + .5 * (sum(x == value for x in vals.values()) - 1)) / (n - 1)
    return scores, {"total": len(set(members)), "evaluable": n}


def main():
    started = time.monotonic()
    head_path = ROOT / "data/v4/V4_DEV_BASELINE_HEAD.json"
    head = json.loads(head_path.read_text(encoding="utf-8"))
    if head["accepted_data_cutoff"] != "2026-09-24":
        raise RuntimeError("frozen DEV baseline cutoff drift")
    bootstrap_path = ROOT / head["bootstrap_manifest"]["path"]
    if sha(bootstrap_path) != head["bootstrap_manifest"]["sha256"]:
        raise RuntimeError("baseline bootstrap digest mismatch")
    bootstrap = json.loads(bootstrap_path.read_text(encoding="utf-8"))
    manifest_ref = bootstrap["parent_artifacts"]["v4_02_manifest"]
    manifest_path = ROOT / manifest_ref["path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    daily_ref = manifest["components"]["DAILY_R7"]
    daily_path = ROOT / daily_ref["path"]
    universe_ref = bootstrap["parent_artifacts"]["v4_01_universe"]
    universe_path = ROOT / universe_ref["path"]
    calendar_ref = manifest["components"]["CALENDAR"]
    calendar_path = ROOT / calendar_ref["path"]
    for path, ref, key in ((daily_path, daily_ref, "daily"), (universe_path, universe_ref, "universe"), (calendar_path, calendar_ref, "calendar")):
        if sha(path) != ref["sha256"]:
            raise RuntimeError(f"accepted {key} source digest mismatch")
    calendar = [d for d in json.loads(calendar_path.read_text(encoding="utf-8"))["session_dates"] if d <= head["accepted_data_cutoff"]][-200:]
    selected_dates = {calendar[-1 - offset] for offset in OFFSETS}
    snapshots = defaultdict(dict)
    with gzip.open(universe_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["trade_date"] in selected_dates and row["board_scope"] in REQUIRED:
                snapshots[row["trade_date"]][row["security_id"]] = row
    current_day = head["accepted_data_cutoff"]
    current_members = set(snapshots[current_day])
    target_ids = set().union(*(set(v) for v in snapshots.values()))
    actual, rejected = defaultdict(dict), defaultdict(dict)
    first_day = calendar[0]
    sql = """select canonical_security_id, trade_date, qfq_open, qfq_high, qfq_low, qfq_close,
                     amount, volume, price_basis, adjustment_source_revision, adjusted_quality, trading_status
              from read_parquet(?) where trade_date between ? and ? order by canonical_security_id, trade_date"""
    con = duckdb.connect()
    cur = con.execute(sql, [daily_path.as_posix(), int(first_day.replace("-", "")), int(current_day.replace("-", ""))])
    rows_in = 0
    while batch := cur.fetchmany(25000):
        for row in batch:
            sid, day, op, hi, lo, cl, amount, volume, basis, revision, quality, status = row
            if sid not in target_ids:
                continue
            rows_in += 1
            date = f"{day // 10000:04d}-{day // 100 % 100:02d}-{day % 100:02d}"
            if quality == "READY" and status == "ACTUAL_TRADED" and all(x is not None for x in (op, hi, lo, cl, amount, volume, basis, revision)):
                actual[sid][date] = {"open": float(op), "high": float(hi), "low": float(lo), "close": float(cl),
                                     "amount": float(amount), "volume": float(volume), "basis": f"{basis}:{revision}",
                                     "source": daily_ref["sha256"]}
            else:
                rejected[sid][date] = "ADJUSTMENT_UNKNOWN" if quality != "READY" else "UNKNOWN"
    status_path = ROOT / "data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz"
    if not status_path.exists():
        raise RuntimeError("required dated trading status input is missing")
    suspended = defaultdict(set)
    status_by = defaultdict(dict)
    with gzip.open(status_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["security_id"] in target_ids and first_day <= row["trade_date"] <= current_day:
                status_by[row["security_id"]][row["trade_date"]] = row["status"]
                if row["status"] == "SUSPENDED":
                    suspended[row["security_id"]].add(row["trade_date"])
    histories = {}
    for sid in current_members:
        items, seen = [], False
        for day in calendar:
            bar = actual[sid].get(day)
            rej = rejected[sid].get(day)
            if bar is not None or rej is not None or day in suspended[sid]:
                seen = True
            if bar is not None:
                state = "ACTUAL"
            elif rej is not None:
                state = rej
            elif day in suspended[sid]:
                state = "CONFIRMED_SUSPENSION"
            else:
                state = "UNKNOWN" if seen else "PRE_LISTING"
            items.append({"trade_date": day, "state": state, "bar": bar})
        histories[sid] = items
    params = json.loads((ROOT / "config/v4_03_parameter_registry_v1.json").read_text(encoding="utf-8"))
    param = {x["parameter_id"]: x["value"] for x in params["entries"]}
    damage_multiple = param["V4_03_CORE_PRICE_DAMAGE_ATR_MULTIPLE"]
    if damage_multiple is None:
        raise RuntimeError("price-damage parameter is not bound")
    candidate_rows = {}
    with gzip.open(CORE, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            candidate_rows[row["security_id"]] = row
    if set(candidate_rows) != current_members:
        raise RuntimeError("core artifact member set differs from frozen current PIT universe")
    full_rows = {}
    with gzip.open(CANDIDATE, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            full_rows[row["security_id"]] = row
    if set(full_rows) != current_members:
        raise RuntimeError("47-field candidate member set differs from frozen current PIT universe")
    mismatch_by_field = Counter()
    field_quality = Counter()
    digest_invalid = Counter()
    mismatch_samples = []
    checked_by_field = Counter()

    def compare(sid, field, expected, found):
        value, quality, reason = expected
        if (found.get("quality_state") != quality or found.get("unknown_reason") != reason or
                (value is None) != (found.get("value") is None) or
                (value is not None and (isinstance(value, bool) and found.get("value") is not value or
                 not isinstance(value, bool) and not math.isclose(float(value), float(found["value"]), rel_tol=1e-12, abs_tol=1e-12)))):
            mismatch_by_field[field] += 1
            if len(mismatch_samples) < 20:
                mismatch_samples.append({"security_id": sid, "field_id": field, "expected": {"value": value, "quality_state": quality, "unknown_reason": reason},
                                         "found": {k: found.get(k) for k in ("value", "quality_state", "unknown_reason")}})
        checked_by_field[field] += 1
        field_quality[(field, quality)] += 1
        for name in ("window_identity", "input_digest"):
            value_digest = found.get(name)
            if not isinstance(value_digest, str) or len(value_digest) != 64 or any(c not in "0123456789abcdef" for c in value_digest.lower()):
                digest_invalid[field] += 1
        output_payload = dict(found)
        output_digest = output_payload.pop("output_digest", None)
        if output_digest != digest(output_payload):
            digest_invalid[field] += 1

    for sid in sorted(current_members):
        core_expected = independent_core(histories[sid], sid, float(damage_multiple))
        core_found = candidate_rows[sid]["fields"]
        if set(core_expected) != set(core_found):
            raise RuntimeError(f"core field set mismatch for {sid}")
        for field, expected in core_expected.items():
            compare(sid, field, expected, core_found[field])

    # Independently replay relative fields from fixed-session closes and PIT snapshots.
    endpoint_offsets = (0, 1, 3, 5, 20, 6, 8, 23)
    dates = {offset: calendar[-1 - offset] for offset in endpoint_offsets}
    all_returns = {h: {} for h in (1, 3, 5, 20)}
    basis_pairs = set()
    for sid in target_ids:
        for h in (1, 3, 5, 20):
            start, end = dates[h], dates[0]
            start_bar, end_bar = actual[sid].get(start), actual[sid].get(end)
            if not start_bar or not end_bar or start_bar["basis"] != end_bar["basis"] or start_bar["close"] <= 0:
                all_returns[h][sid] = None
                continue
            start_i, end_i = calendar.index(start), calendar.index(end)
            valid = True
            for day in calendar[start_i + 1:end_i]:
                state = status_by[sid].get(day)
                if state == "SUSPENDED":
                    continue
                bar = actual[sid].get(day)
                if state != "ACTUAL_TRADED" or bar is None or bar["basis"] != start_bar["basis"]:
                    valid = False
                    break
            all_returns[h][sid] = end_bar["close"] / start_bar["close"] - 1 if valid else None
            if valid:
                basis_pairs.add((sid, start_bar["basis"]))
    expected_relative = {sid: {} for sid in current_members}
    missing_limit = float(param["V4_03_MARKET_REFERENCE_MAX_MISSING_FRACTION"])
    for h in (1, 3, 5):
        members = set(snapshots[dates[h]])
        vals = {s: all_returns[h].get(s) for s in members if all_returns[h].get(s) is not None}
        total, evaluable, missing = len(members), len(vals), len(members) - len(vals)
        reason = "EMPTY_START_UNIVERSE" if not total else "MISSING_COVERAGE_EXCEEDED" if missing / total > missing_limit else None
        ref = sum(vals.values()) / len(vals) if vals and reason is None else None
        for sid in current_members:
            r = all_returns[h].get(sid)
            field = f"rel_market_{h}"
            why = "RETURN_UNKNOWN" if r is None else reason
            expected_relative[sid][field] = (None if why else r - ref, "UNKNOWN" if why else "OBSERVED", why)
    for h in (5, 20):
        scores, _ = midranks(all_returns[h], current_members)
        for sid in current_members:
            value = scores[sid]
            reason = None if value is not None else "INSUFFICIENT_EVALUABLE_UNIVERSE" if sum(v is not None for v in scores.values()) < 2 else "RETURN_UNKNOWN"
            expected_relative[sid][f"rps{h}"] = (value, "UNKNOWN" if reason else "OBSERVED", reason)
    history_scores = {}
    for offset, h, member_offset, start_offset in ((1, 5, 1, 6), (3, 5, 3, 8), (3, 20, 3, 23)):
        start_date, end_date = dates[start_offset], dates[member_offset]
        members = set(snapshots[end_date])
        vals = {}
        for sid in members:
            a, b = actual[sid].get(start_date), actual[sid].get(end_date)
            evaluable = bool(a and b and a["close"] > 0 and a["basis"] == b["basis"])
            if evaluable:
                start_i, end_i = calendar.index(start_date), calendar.index(end_date)
                for day in calendar[start_i + 1:end_i]:
                    state = status_by[sid].get(day)
                    if state == "SUSPENDED":
                        continue
                    middle = actual[sid].get(day)
                    if state != "ACTUAL_TRADED" or middle is None or middle["basis"] != a["basis"]:
                        evaluable = False
                        break
            vals[sid] = b["close"] / a["close"] - 1 if evaluable else None
        score, _ = midranks(vals, members)
        history_scores[(offset, h)] = score
    for sid in current_members:
        for h, offset in ((5, 1), (5, 3), (20, 3)):
            current_score = expected_relative[sid][f"rps{h}"][0]
            previous = history_scores[(offset, h)].get(sid)
            reason = None if current_score is not None and previous is not None else "PRIOR_RPS_OR_CURRENT_SCORE_UNKNOWN"
            field = f"rps{h}_delta{offset}"
            expected_relative[sid][field] = (current_score - previous if not reason else None,
                                              "UNKNOWN" if reason else "OBSERVED", reason)
        found = full_rows[sid]["fields"]
        for field, expected in expected_relative[sid].items():
            compare(sid, field, expected, found[field])

    artifact_receipt = json.loads(CANDIDATE_RECEIPT.read_text(encoding="utf-8"))
    candidate_sha = sha(CANDIDATE)
    receipt_match = candidate_sha == artifact_receipt.get("output_sha256")
    field_ids = sorted(checked_by_field)
    reference_path = ROOT / "reports/v4_03/V4_03_MARKET_REFERENCE_CANDIDATE_R1.json"
    references = json.loads(reference_path.read_text(encoding="utf-8"))
    reference_digests_ok = all(ref.get("output_digest") == digest({k: v for k, v in ref.items() if k != "output_digest"})
                               for ref in references["market_references"].values())
    references_match = sha(reference_path) == artifact_receipt.get("references_sha256")
    status = "PASS" if (len(field_ids) == 47 and all(checked_by_field[x] == len(current_members) for x in field_ids)
                        and not mismatch_by_field and not digest_invalid and receipt_match
                        and reference_digests_ok and references_match) else "FAIL"
    report = {"contract_id": "V4_03_INDEPENDENT_POSTCHECK_R1",
              "status": status, "scope": "INDEPENDENT_DIAGNOSTIC_POSTCHECK_NOT_STAGE_ACCEPTANCE",
              "cutoff": current_day, "evidence_origin": "DIAGNOSTIC_NON_PIT",
              "independent_formula_module_imports": [],
              "inputs": {"dev_baseline_head_sha256": sha(head_path), "universe_sha256": universe_ref["sha256"],
                         "daily_sha256": daily_ref["sha256"], "calendar_sha256": calendar_ref["sha256"],
                         "trading_status_sha256": sha(status_path), "parameter_registry_sha256": sha(ROOT / "config/v4_03_parameter_registry_v1.json")},
              "candidate_output_sha256": candidate_sha, "candidate_receipt_sha256_matches": receipt_match,
              "market_reference_output_digests_recomputed": reference_digests_ok,
              "market_reference_receipt_sha256_matches": references_match,
              "rows_in": rows_in, "rows_checked": len(full_rows), "fields_checked": len(field_ids),
              "checks_per_field": dict(sorted(checked_by_field.items())),
              "quality_count": {f"{k[0]}:{k[1]}": v for k, v in sorted(field_quality.items())},
              "mismatch_count_by_field": dict(sorted(mismatch_by_field.items())),
              "invalid_digest_count_by_field": dict(sorted(digest_invalid.items())),
              "mismatch_samples": mismatch_samples,
              "comparison": "exact quality and reason; bool exact; numeric abs/rel tolerance 1e-12",
              "elapsed_seconds": round(time.monotonic() - started, 3),
              "limitations": ["This independently recomputes values and quality for all 47 fields and recomputes each field output_digest over its serialized identity/value/quality. It validates input_digest/window_identity format but does not independently regenerate those two producer identity hashes.",
                              "Relative RPS delta prior rows are recomputed from frozen historical PIT snapshots in the accepted universe input.",
                              "Candidate lineage remains DIAGNOSTIC_NON_PIT; this does not grant stage acceptance or publication."]}
    atomic_json(OUTPUT, report)
    print(json.dumps({"status": status, "rows_checked": len(full_rows), "fields_checked": len(field_ids),
                      "mismatches": sum(mismatch_by_field.values()), "elapsed_seconds": report["elapsed_seconds"]}))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
