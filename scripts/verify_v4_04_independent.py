"""Independent, read-only checks of the V4-04 full-market staging candidate."""

from __future__ import annotations

from collections import Counter, defaultdict
import gzip
from hashlib import sha256
import json
from pathlib import Path
import sys

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.v4.accepted_input import BOARDS, CUTOFF, resolve  # noqa: E402

ARTIFACT = ROOT / "reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R1.jsonl.gz"
RECEIPT = ROOT / "reports/v4_04/V4_04_FULL_MARKET_CANDIDATE_RECEIPT_R1.json"
OUT = ROOT / "reports/v4_04/V4_04_INDEPENDENT_POSTCHECK_R1.json"


def digest(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def eval_node(node: dict, evidence: dict, parameters: dict):
    if "field" in node:
        return evidence[node["field"]]
    if "parameter_id" in node:
        return parameters[node["parameter_id"]]
    if "constant" in node:
        return node["constant"]
    if "set" in node:
        return node["set"]
    op = node["operator"]
    if op == "AND":
        values = [eval_node(arg, evidence, parameters) for arg in node["args"]]
        return False if False in values else None if None in values else True
    if op == "OR":
        for arg in node["args"]:
            value = eval_node(arg, evidence, parameters)
            if value is True:
                return True
        return None if any(eval_node(arg, evidence, parameters) is None for arg in node["args"]) else False
    args = [eval_node(arg, evidence, parameters) for arg in node["args"]]
    if op == "NOT": return None if args[0] is None else not args[0]
    if None in args: return None
    if op == "GT": return args[0] > args[1]
    if op == "GE": return args[0] >= args[1]
    if op == "LT": return args[0] < args[1]
    if op == "LE": return args[0] <= args[1]
    if op == "NEG": return -args[0]
    if op == "IN": return args[0] in args[1]
    if op == "MUL": return args[0] * args[1]
    if op == "DIV": return args[0] / args[1]
    raise ValueError(f"unknown AST operator {op}")


def machine_expect(field: str, state: dict, rules: dict, parameters: dict):
    contract = state["contract_id"]
    if contract == "TREND_STATE_V1" and field == "trend_state":
        key = "TREND_STATE_V1.daily"
    elif contract == "POSITION_STATE_V1" and field == "position_state":
        key = "POSITION_STATE_V1"
    elif contract == "AMOUNT_VOLUME_STATE_V1" and field in ("amount_state", "volume_state"):
        key = "AMOUNT_VOLUME_STATE_V1.ratio"
    elif contract == "AMOUNT_VOLUME_STATE_V1" and field == "core_participation_result":
        key = "AMOUNT_VOLUME_STATE_V1.participation"
    elif contract == "EXTENSION_RISK_V1" and field == "core_extension_risk":
        key = "EXTENSION_RISK_V1"
    elif contract in ("MA_STRUCTURE_V1", "RELATIVE_STATE_V1", "COMPRESSION_STATE_V1"):
        key = contract
    else:
        return None
    evidence = dict(state["evidence"])
    if key == "AMOUNT_VOLUME_STATE_V1.ratio":
        evidence["ratio20"] = next(iter(evidence.values()))
    for branch in rules[key]["branches"]:
        result = eval_node(branch["when"], evidence, parameters)
        if result is None:
            return "UNKNOWN"
        if result:
            return branch["value"]
    raise ValueError(f"machine rule has no final branch: {key}")


def independent_regime(path: list[dict], switch_sessions: int) -> tuple[str, str | None, int, str]:
    accepted = pending = None
    count = 0
    value = "UNKNOWN"
    label = "UNKNOWN"
    for row in path:
        if any(row.get(key) in (None, "UNKNOWN") for key in ("trend_axis", "breadth_axis", "participation_axis", "stress_level", "stress_change")):
            label = "UNKNOWN"
        elif row["trend_axis"] == "WEAK" and row["stress_level"] == "HIGH":
            label = "CAPITULATION"
        elif row["trend_axis"] == "WEAK" and row["breadth_axis"] == "IMPROVING" and row["stress_change"] == "DECLINING":
            label = "RECOVERY_ATTEMPT"
        elif row["trend_axis"] == "STRONG" and row["breadth_axis"] != "DETERIORATING" and row["stress_level"] == "LOW":
            label = "RISK_ON"
        elif row["trend_axis"] == "WEAK" or row["stress_level"] == "HIGH":
            label = "RISK_OFF"
        else:
            label = "NEUTRAL"
        if label == "UNKNOWN":
            pending, count, value = None, 0, "UNKNOWN"
        elif label == "CAPITULATION":
            accepted, pending, count, value = label, None, 0, label
        elif label == accepted:
            pending, count, value = None, 0, label
        else:
            count = count + 1 if pending == label else 1
            pending = label
            if count >= switch_sessions:
                accepted, pending, count, value = label, None, 0, label
            else:
                value = accepted or "UNKNOWN"
    return value, accepted, count, label


def expect(state: dict) -> object:
    c, e = state["contract_id"], state["evidence"]
    if state["unknown_reason"]:
        return state["value"]
    if c == "TREND_STATE_V1":
        if "period_view" in e:
            key = "ma5" if "ma5" in e else "ma3"
            prefix = "WEEKLY" if key == "ma5" else "MONTHLY"
            if e["period_view"] != "CLOSED_ONLY":
                return "UNKNOWN"
            return (prefix + "_UP" if e["close"] > e[key] > e[f"previous_{key}"] else
                    prefix + "_DOWN" if e["close"] < e[key] < e[f"previous_{key}"] else prefix + "_FLAT")
        close, ma20, ma60 = e["close"], e["ma20"], e["ma60"]
        s20, s60 = e["slope20"], e["slope60"]
        if close < ma20 and s20 < -.1 and s60 < -.1 and e["ll_progress"]:
            return "DOWNTREND_STRONG"
        if close > ma20 and s20 > .1 and (close > ma60 or s60 > .1) and e["hh_progress"] and not e["core_price_damage"]:
            return "UPTREND_STRONG"
        if close < ma20 and s20 < -.1:
            return "DOWNTREND"
        if close > ma20 and s20 > .1 and not e["core_price_damage"]:
            return "UPTREND"
        return "SIDEWAYS_WEAK" if close < ma20 else "SIDEWAYS_STRONG" if close > ma20 else "SIDEWAYS"
    if c == "POSITION_STATE_V1":
        if "bias20_atr" in e:
            b, p = e["bias20_atr"], e["pos60"]
            return "EXTENDED" if b >= 3 else "HIGH_ZONE" if p >= .8 else "MID_HIGH" if p >= .6 else "MID_ZONE" if p >= .4 else "MID_LOW" if p >= .2 else "LOW_ZONE"
        if "prior_high20" in e or "prior_high60" in e:
            prior = e.get("prior_high20", e.get("prior_high60"))
            d = (prior - e["close"]) / e["atr20"]
            return "ABOVE_PRIOR_HIGH" if d < 0 else "NEAR" if d <= .5 else "BELOW"
        high = e.get("hhv20", e.get("hhv60"))
        d = e["close"] / high - 1
        return "SHALLOW" if d >= -.05 else "MODERATE" if d >= -.15 else "DEEP"
    if c == "MA_STRUCTURE_V1":
        a, b, d, s = e["ma5"], e["ma10"], e["ma20"], e["slope20"]
        return "BULL_ALIGNED" if a > b > d and s > 0 else "BEAR_ALIGNED" if a < b < d and s < 0 else "BULL_TRANSITION" if a > d and s >= 0 else "BEAR_TRANSITION" if a < d and s <= 0 else "MIXED"
    if c == "COMPRESSION_STATE_V1":
        r, a, v, m, l = (e[k] for k in ("range_ratio", "atr_ratio", "vol_ratio", "amount_ratio20", "minimum_liquidity"))
        return "EXPANDING_EXTREME" if a >= 1.5 or v >= 1.5 else "EXPANDING" if a >= 1.1 or v >= 1.1 else "COMPRESSING_STRONG" if r <= .35 and a <= .7 and v <= .7 and m <= .8 and l else "COMPRESSING" if r <= .6 and a <= .9 and v <= .9 and l else "NORMAL"
    if c == "RELATIVE_STATE_V1":
        d, r, m = e["rps20_delta3"], e["rps20"], e["rel_market_1"]
        active = d >= 10 and (e["compression_state"] in ("COMPRESSING", "COMPRESSING_STRONG") or e["ma_structure_state"] in ("BULL_TRANSITION", "BULL_ALIGNED"))
        return "ACTIVE_EMERGENCE" if active else "PASSIVE_RESILIENCE" if m > 0 and d <= 0 else "LEADING_ACCELERATING" if r >= 80 and d > 0 else "LEADING_STABLE" if r >= 80 and d >= -3 else "IMPROVING" if d > 3 else "WEAKENING" if d < -3 else "LAGGING" if r < 20 else "NEUTRAL"
    if c == "AMOUNT_VOLUME_STATE_V1":
        if "amount_ratio20" in e and "ret1" in e:
            a, ret, clv = e["amount_ratio20"], e["ret1"], e["clv"]
            return "HIGH_PARTICIPATION_REVERSAL" if a >= 1.2 and ret < 0 else "HIGH_PARTICIPATION_EFFECTIVE_ADVANCE" if a >= 1.2 and ret > 0 and clv >= .7 else "HIGH_PARTICIPATION_LOW_EFFICIENCY" if a >= 1.2 else "LOW_PARTICIPATION_ADVANCE" if a < .8 and ret > 0 else "LOW_PARTICIPATION_DECLINE" if a < .8 and ret < 0 else "NORMAL_PARTICIPATION"
        a = next(iter(e.values()))
        return "VERY_DRY" if a < .5 else "CONTRACTED" if a < .8 else "NORMAL" if a < 1.2 else "EXPANDED" if a < 2 else "VERY_EXPANDED"
    if c == "EXTENSION_RISK_V1":
        if "core_extension_risk" in e:
            return e["core_extension_risk"] == "EXTREME"
        b = e["bias20_atr"]
        return "EXTREME" if b >= 4 else "HIGH" if b >= 3 or (e["ret5"] >= 3 * e["atr20"] / e["close"] and e["amount_ratio20"] >= 2 and e["ret1"] <= 0) else "MEDIUM" if b >= 2 else "LOW"
    if c == "MARKET_REGIME_V1":
        return state["value"]
    raise ValueError(f"unhandled contract {c}")


def main() -> None:
    inputs = resolve(ROOT)
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    actual_hash = sha256(ARTIFACT.read_bytes()).hexdigest()
    if actual_hash != receipt["artifact"]["sha256"]:
        raise ValueError("artifact hash mismatch")
    contract_hashes = {name: sha256((ROOT / name).read_bytes()).hexdigest()
                       for name in receipt["contract_files"]}
    if contract_hashes != receipt["contract_files"] or digest(contract_hashes) != receipt["contract_digest"]:
        raise ValueError("contract or parameter identity mismatch")
    expected_source = digest({key: value.sha256 for key, value in sorted(inputs.items())})
    algorithm = json.loads((ROOT / "config/v4_04_algorithm_contracts_v1.json").read_text(encoding="utf-8"))
    registry = json.loads((ROOT / "config/v4_04_field_registry_v1.json").read_text(encoding="utf-8"))
    registered_fields = {x["field_id"] for x in registry["fields"]}
    schema = json.loads((ROOT / "config/v4_04_output_schema_v1.json").read_text(encoding="utf-8"))
    parameter_file = json.loads((ROOT / "config/v4_04_parameter_set_v1.json").read_text(encoding="utf-8"))
    parameters = {x["parameter_id"]: x["value"] for x in parameter_file["parameters"]}
    factors = {}
    with gzip.open(inputs["factors"].path, "rt", encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            sid = item["security_id"]
            if sid in factors:
                raise ValueError("duplicate accepted V4-03 factor identity")
            factors[sid] = item
    with gzip.open(inputs["market_regime"].path, "rt", encoding="utf-8") as stream:
        regime_path = [json.loads(line) for line in stream]
    if not regime_path or regime_path[-1]["trade_date"] != CUTOFF:
        raise ValueError("accepted market regime cutoff mismatch")
    regime_expected = independent_regime(regime_path, int(parameters["V4_04_REGIME_SWITCH_SESSIONS"]))
    rows, boards, unknowns = [], Counter(), Counter()
    with gzip.open(ARTIFACT, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["source_digest"] != expected_source or row["trade_date"] != CUTOFF or row["contract_digest"] != receipt["contract_digest"]:
                raise ValueError("row source or cutoff mismatch")
            upstream = factors.get(row["security_id"])
            if upstream is None or upstream["board_scope"] != row["board"] or upstream["trade_date"] != CUTOFF:
                raise ValueError("upstream factor row identity mismatch")
            if not set(schema["required_row_identity"]).issubset(row) or not set(schema["required_envelopes"]).issubset(row):
                raise ValueError("full market row schema mismatch")
            if not registered_fields.issubset(set(row["states"]) | set(row["derived_fields"]) | set(row["primitive_quality"])):
                raise ValueError("registered field completeness mismatch")
            for field, quality in row["primitive_quality"].items():
                accepted = upstream["fields"].get(field)
                if accepted is None or any(quality[key] != accepted[key] for key in ("quality_state", "unknown_reason", "output_digest")):
                    raise ValueError(f"accepted primitive quality mismatch: {field}")
            row_hash = row.pop("output_digest")
            if digest(row) != row_hash:
                raise ValueError("row output digest mismatch")
            row["output_digest"] = row_hash
            for field, state in row["states"].items():
                if not set(schema["state_envelope"]).issubset(state):
                    raise ValueError("state envelope schema mismatch")
                if (state["unknown_reason"] is None) != (state["value"] not in ("UNKNOWN", None)):
                    raise ValueError("state UNKNOWN/quality contradiction")
                if state["contract_digest"] != receipt["contract_digest"]:
                    raise ValueError("state contract identity mismatch")
                state_hash = state.pop("output_digest")
                if digest(state) != state_hash or digest(state["evidence"]) != state["input_digest"]:
                    raise ValueError(f"state hash mismatch: {field}")
                state["output_digest"] = state_hash
                if field == "regime_ui":
                    if (state["value"], state["last_known"], state["consecutive_count"], state["candidate"]) != regime_expected:
                        raise ValueError("independent market regime hysteresis mismatch")
                    last_market = regime_path[-1]
                    if any(state["evidence"][key] != last_market[key] for key in ("trend_axis", "breadth_axis", "participation_axis", "stress_level", "stress_change")):
                        raise ValueError("accepted market axis evidence mismatch")
                for name, value in state["evidence"].items():
                    if field in ("weekly_trend_state", "monthly_trend_state"):
                        continue
                    accepted = upstream["fields"].get(name)
                    if accepted is not None:
                        expected_value = accepted["value"] if accepted["quality_state"] == "OBSERVED" else None
                        if value != expected_value:
                            raise ValueError(f"accepted primitive evidence mismatch: {field}.{name}")
                if state["unknown_reason"]:
                    unknowns[field] += 1
                else:
                    expected = expect(state)
                    machine = machine_expect(field, state, algorithm["rules"], parameters)
                    if state["value"] != expected or (machine is not None and machine != expected):
                        raise ValueError(f"independent rule mismatch: {field} {row['security_id']}")
            for field, derived in row["derived_fields"].items():
                if not set(schema["derived_envelope"]).issubset(derived):
                    raise ValueError("derived envelope schema mismatch")
                if (derived["unknown_reason"] is None) != (derived["value"] is not None):
                    raise ValueError("derived UNKNOWN/quality contradiction")
                derived_hash = derived.pop("output_digest")
                if (digest(derived) != derived_hash or derived["source_digest"] != expected_source or
                        derived["contract_digest"] != receipt["contract_digest"]):
                    raise ValueError(f"derived field identity mismatch: {field}")
                derived["output_digest"] = derived_hash
            rows.append(row)
            boards[row["board"]] += 1
    if len(rows) != len({x["security_id"] for x in rows}) or set(boards) != set(BOARDS):
        raise ValueError("row identity or board coverage mismatch")
    if dict(boards) != receipt["board_count"] or len(rows) != receipt["row_count"]:
        raise ValueError("receipt count mismatch")
    # Source recomputation on a deterministic sample spanning all boards and quality levels.
    sample = []
    for board in BOARDS:
        subset = [r for r in rows if r["board"] == board]
        sample.extend([subset[0], subset[len(subset)//2], subset[-1]])
        sample.extend([r for r in subset if r["profile_quality"] != "COMPLETE"][:2])
    sample.extend([r for r in rows if r["derived_fields"]["pos250"]["value"] is None][:2])
    sample.extend([r for r in rows if r["states"]["position_state"]["value"] == "HIGH_ZONE"][:2])
    sample.extend([r for r in rows if r["states"]["position_state"]["value"] == "LOW_ZONE"][:2])
    sample.extend([r for r in rows if r["trading_status"] == "SUSPENDED"][:2])
    nearest_boundary = min((r for r in rows if r["states"]["position_state"]["evidence"]["pos60"] is not None),
                           key=lambda r: abs(r["states"]["position_state"]["evidence"]["pos60"] - .8))
    sample.append(nearest_boundary)
    sample = list({r["security_id"]: r for r in sample}.values())
    categories = {
        "boards": sorted({r["board"] for r in sample}),
        "unknown": sum(r["profile_quality"] != "COMPLETE" for r in sample),
        "recent_or_short_history": sum(r["derived_fields"]["pos250"]["actual_count"] < 250 for r in sample),
        "high_zone": sum(r["states"]["position_state"]["value"] == "HIGH_ZONE" for r in sample),
        "low_zone": sum(r["states"]["position_state"]["value"] == "LOW_ZONE" for r in sample),
        "suspended": sum(r["trading_status"] == "SUSPENDED" for r in sample),
        "nearest_pos60_0_8_distance": abs(nearest_boundary["states"]["position_state"]["evidence"]["pos60"] - .8),
    }
    if categories["boards"] != sorted(BOARDS) or any(categories[key] == 0 for key in ("unknown", "recent_or_short_history", "high_zone", "low_zone", "suspended")):
        raise ValueError("independent source sample category coverage incomplete")
    con = duckdb.connect()
    sampled_checks = Counter()
    for row in sample:
        sid = row["security_id"]
        actual = con.execute("""
            SELECT trade_date, qfq_close, qfq_high, qfq_low, amount, adjusted_quality
            FROM read_parquet(?) WHERE canonical_security_id=? AND trade_date<=20260924
            ORDER BY trade_date DESC LIMIT 251
        """, [str(inputs["daily"].path), sid]).fetchall()
        actual.reverse()
        if actual and actual[-1][0] == 20260924 and actual[-1][5] == "READY":
            fields = row["derived_fields"]
            if fields["ma10"]["value"] is not None:
                mean10 = sum(float(x[1]) for x in actual[-10:]) / 10
                if abs(mean10 - fields["ma10"]["value"]) > 1e-9:
                    raise ValueError("MA10 independent source mismatch")
                sampled_checks["ma10"] += 1
            if fields["minimum_liquidity"]["value"] is not None:
                prior20 = sum(float(x[4]) for x in actual[-21:-1]) / 20
                if (prior20 >= 20_000_000) != fields["minimum_liquidity"]["value"]:
                    raise ValueError("minimum liquidity independent source mismatch")
                sampled_checks["minimum_liquidity"] += 1
            if fields["pos250"]["value"] is not None:
                high = max(float(x[2]) for x in actual[-250:])
                low = min(float(x[3]) for x in actual[-250:])
                pos = (float(actual[-1][1]) - low) / (high - low)
                if abs(pos - fields["pos250"]["value"]) > 1e-9:
                    raise ValueError("pos250 independent source mismatch")
                sampled_checks["pos250"] += 1
        for period_name, key, window in (("weekly", "ma5", 5), ("monthly", "ma3", 3)):
            state = row["states"][f"{period_name}_trend_state"]
            periods = con.execute("""
                SELECT close, period_status FROM read_parquet(?)
                WHERE canonical_security_id=? AND price_basis='QFQ'
                  AND period_view='CLOSED_ONLY' AND period_last_session<=20260924
                ORDER BY period_last_session DESC LIMIT ?
            """, [str(inputs[period_name].path), sid, window + 1]).fetchall()
            periods.reverse()
            if state["value"] != "UNKNOWN":
                if len(periods) != window + 1 or any(p[1] != "CLOSED_ONLY_READY" for p in periods):
                    raise ValueError("closed-period input quality mismatch")
                values = [float(p[0]) for p in periods]
                ma = sum(values[-window:]) / window
                prev_ma = sum(values[:-1]) / window
                evidence = state["evidence"]
                if (abs(values[-1] - evidence["close"]) > 1e-9 or
                        abs(ma - evidence[key]) > 1e-9 or
                        abs(prev_ma - evidence[f"previous_{key}"]) > 1e-9):
                    raise ValueError("closed-period independent source mismatch")
                sampled_checks[period_name] += 1
    result = {"contract_id": "V4_04_INDEPENDENT_POSTCHECK_R1", "status": "PASS",
              "artifact_sha256": actual_hash, "rows_checked": len(rows), "board_count": dict(boards),
              "unknown_by_state": dict(unknowns), "source_recompute_sample_count": len(sample),
              "sample_categories": categories,
              "sampled_checks": dict(sampled_checks), "limitations": ["sampled source recomputation; all state AST evidence independently checked"]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "rows": len(rows), "sample": len(sample), "checks": sampled_checks}, default=dict))


if __name__ == "__main__":
    main()
