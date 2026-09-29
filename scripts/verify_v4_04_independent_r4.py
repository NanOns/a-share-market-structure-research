"""Independent, read-only checks of the V4-04 full-market staging candidate."""

from __future__ import annotations

from collections import Counter, defaultdict
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.v4.accepted_input import BOARDS, CUTOFF, resolve  # noqa: E402

ARTIFACT = ROOT / "reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R4.jsonl.gz"
RECEIPT = ROOT / "reports/v4_04/V4_04_FULL_MARKET_CANDIDATE_RECEIPT_R4.json"
OUT = ROOT / "reports/v4_04/V4_04_INDEPENDENT_POSTCHECK_R4.json"
VECTOR_RECEIPT = ROOT / "reports/v4_04/V4_04_MACHINE_VECTOR_COVERAGE_R4.json"


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes((json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    os.replace(tmp, path)


def digest(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


from scripts.v4_04_machine_executor_r4 import OPERATORS, declared_operators, execute_rule, rule_keys


FIELD_RULE = {
    "trend_state": "TREND_STATE_V1.daily", "weekly_trend_state": "TREND_STATE_V1.closed_period",
    "monthly_trend_state": "TREND_STATE_V1.closed_period", "position_state": "POSITION_STATE_V1",
    "near_high20_state": "POSITION_STATE_V1.near_high", "near_high60_state": "POSITION_STATE_V1.near_high",
    "drawdown20_state": "POSITION_STATE_V1.drawdown", "drawdown60_state": "POSITION_STATE_V1.drawdown",
    "ma_structure_state": "MA_STRUCTURE_V1", "compression_state": "COMPRESSION_STATE_V1",
    "relative_market_state": "RELATIVE_STATE_V1", "amount_state": "AMOUNT_VOLUME_STATE_V1.ratio",
    "volume_state": "AMOUNT_VOLUME_STATE_V1.ratio",
    "core_participation_result": "AMOUNT_VOLUME_STATE_V1.participation",
    "core_extension_risk": "EXTENSION_RISK_V1", "severe_extension": "EXTENSION_RISK_V1.severe",
    "regime_ui": "MARKET_REGIME_V1.regime_ui",
}


def machine_expect(field, state, rules, parameters, regime_path):
    key = FIELD_RULE[field]
    evidence = dict(state["evidence"])
    if key == "TREND_STATE_V1.closed_period":
        evidence["period_type"] = "weekly" if field.startswith("weekly") else "monthly"
        ma = "ma5" if evidence["period_type"] == "weekly" else "ma3"
        evidence["ma_current"] = evidence.get(ma)
        evidence["ma_previous"] = evidence.get("previous_" + ma)
    elif key == "POSITION_STATE_V1.near_high":
        horizon = "20" if "20" in field else "60"
        evidence["prior_highN"] = evidence.get("prior_high" + horizon)
    elif key == "POSITION_STATE_V1.drawdown":
        horizon = "20" if "20" in field else "60"
        evidence["hhvN"] = evidence.get("hhv" + horizon)
    elif key == "AMOUNT_VOLUME_STATE_V1.ratio":
        evidence["ratio20"] = evidence.get("amount_ratio20" if field == "amount_state" else "volume_ratio20")
    elif key == "MARKET_REGIME_V1.regime_ui":
        evidence["path"] = regime_path
    return execute_rule(rules, key, evidence, parameters)


def main() -> None:
    from scripts.v4_04_machine_vectors_r4 import run as verify_vectors
    vector = verify_vectors(write_receipt=False)
    if not VECTOR_RECEIPT.exists() or json.loads(VECTOR_RECEIPT.read_text(encoding="utf-8")) != vector:
        raise ValueError("machine vector receipt missing or stale")
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
    algorithm = json.loads((ROOT / "config/v4_04_algorithm_contracts_v3.json").read_text(encoding="utf-8"))
    registry = json.loads((ROOT / "config/v4_04_field_registry_v2.json").read_text(encoding="utf-8"))
    registered_fields = {x["field_id"] for x in registry["fields"]}
    schema = json.loads((ROOT / "config/v4_04_output_schema_v2.json").read_text(encoding="utf-8"))
    parameter_file = json.loads((ROOT / "config/v4_04_parameter_set_v1.json").read_text(encoding="utf-8"))
    parameters = {x["parameter_id"]: x["value"] for x in parameter_file["parameters"]}
    mapping_path = ROOT / "config/v4_04_field_window_mapping_v1.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    accepted_mapping = ROOT / mapping["accepted_v4_03_mapping_path"]
    if sha256(accepted_mapping.read_bytes()).hexdigest() != mapping["accepted_v4_03_mapping_sha256"]:
        raise ValueError("accepted V4-03 field-window mapping identity mismatch")
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
    declared = declared_operators(algorithm["rules"])
    unsupported = sorted(declared - OPERATORS)
    registered_rules = rule_keys(algorithm["rules"])
    executed_rules = set()
    if unsupported:
        raise ValueError(f"unsupported machine operators: {unsupported}")
    regime_expected = execute_rule(algorithm["rules"], "MARKET_REGIME_V1.regime_ui", {"path": regime_path}, parameters)
    executed_rules.add("MARKET_REGIME_V1.regime_ui")
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
            if (row["field_window_mapping_id"] != mapping["contract_id"] or
                    row["field_window_mapping_digest"] != sha256(mapping_path.read_bytes()).hexdigest() or
                    row["accepted_v4_03_field_window_mapping_digest"] != mapping["accepted_v4_03_mapping_sha256"]):
                raise ValueError("row field-window mapping mismatch")
            for period_name in ("weekly_trend_state", "monthly_trend_state"):
                lineage = row["period_lineage"][period_name]
                if not {"window_identity", "period_last_session", "period_view", "source_daily_digest"} <= set(lineage):
                    raise ValueError("closed period lineage incomplete")
            for entry in registry["fields"]:
                name = entry["field_id"]
                locations = [k for k in ("states", "derived_fields", "primitive_quality") if name in row[k]]
                expected_location = ("primitive_quality" if entry["producer"] == "accepted_V4_03" else
                                     "derived_fields" if entry["producer"] == "src.v4.profile_primitives" else "states")
                if (locations != [expected_location] or
                        entry["required"] != schema["field_required"][name] or
                        row[expected_location][name]["contract_id"] != entry["producer_contract_id"] or
                        row[expected_location][name]["parameter_set_id"] != entry["parameter_set_id"]):
                    raise ValueError(f"registry/artifact identity mismatch: {name}")
            for field, quality in row["primitive_quality"].items():
                accepted = upstream["fields"].get(field)
                if accepted is None or any(quality[key] != accepted.get(key) for key in quality):
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
                    machine = machine_expect(field, state, algorithm["rules"], parameters, regime_path)
                    executed_rules.add(FIELD_RULE[field])
                    if state["value"] != (machine[0] if field == "regime_ui" else machine):
                        raise ValueError(f"independent machine rule mismatch: {field} {row['security_id']}")
            observed_count = sum(state["unknown_reason"] is None for state in row["states"].values())
            required_count = len(row["states"])
            expected_status = ("READY" if observed_count == required_count else
                               "UNKNOWN_DATA" if observed_count == 0 else "PARTIAL")
            if row["profile_component_status"] != expected_status:
                raise ValueError("profile component status mapping mismatch")
            for field, derived in row["derived_fields"].items():
                if not set(schema["derived_envelope"]).issubset(derived):
                    raise ValueError("derived envelope schema mismatch")
                if (derived["field_window_mapping_id"] != mapping["contract_id"] or
                        derived["actual_count"] > derived["calendar_span"] or
                        derived["suspended_count"] > derived["calendar_span"] - derived["actual_count"] or
                        (derived["window_start_trade_date"] and
                         derived["window_end_trade_date"] < derived["window_start_trade_date"])):
                    raise ValueError("derived window lineage mismatch")
                if (derived["unknown_reason"] is None) != (derived["value"] is not None):
                    raise ValueError("derived UNKNOWN/quality contradiction")
                derived_hash = derived.pop("output_digest")
                if (digest(derived) != derived_hash or derived["source_digest"] != expected_source or
                        derived["contract_digest"] != receipt["contract_digest"]):
                    raise ValueError(f"derived field identity mismatch: {field}")
                derived["output_digest"] = derived_hash
                if derived["value"] is not None and field in ("bias20_atr", "dist_high20_atr", "pos250"):
                    evidence = {"close": row["states"]["trend_state"]["evidence"].get("close"),
                                "ma20": row["states"]["trend_state"]["evidence"].get("ma20"),
                                "atr20": row["states"]["near_high20_state"]["evidence"].get("atr20"),
                                "prior_high20": row["states"]["near_high20_state"]["evidence"].get("prior_high20")}
                    if field == "pos250":
                        evidence.update({"HHV250": None, "LLV250": None})
                    if field != "pos250":
                        machine = execute_rule(algorithm["rules"], "V4_04_DERIVED_PRIMITIVES_V1." + field, evidence, parameters)
                        if machine is None or abs(machine - derived["value"]) > 1e-9:
                            raise ValueError(f"derived machine mismatch: {field}")
                        executed_rules.add("V4_04_DERIVED_PRIMITIVES_V1." + field)
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
    sample.extend([r for r in rows if r["primitive_quality"]["amount_ratio20"]["quality_state"] != "OBSERVED"][:12])
    nearest_boundary = min((r for r in rows if r["states"]["position_state"]["evidence"]["pos60"] is not None),
                           key=lambda r: abs(r["states"]["position_state"]["evidence"]["pos60"] - .8))
    sample.append(nearest_boundary)
    sample = list({r["security_id"]: r for r in sample}.values())
    sample_ids = {r["security_id"] for r in sample}
    sampled_statuses = defaultdict(dict)
    with gzip.open(inputs["trading_status"].path, "rt", encoding="utf-8") as stream:
        for line in stream:
            status_row = json.loads(line)
            if status_row["security_id"] in sample_ids:
                sampled_statuses[status_row["security_id"]][status_row["trade_date"]] = status_row["status"]
    calendars = {
        "SH": json.loads(inputs["calendar"].path.read_text(encoding="utf-8"))["session_dates"],
        "SZ": json.loads(inputs["calendar_szse"].path.read_text(encoding="utf-8"))["session_dates"],
    }
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
    minimum_liquidity_source_evaluable_count = 0
    minimum_liquidity_false_unknown_count = 0
    amount_ratio20_unknown_but_liquidity_evaluable_count = 0
    for row in sample:
        sid = row["security_id"]
        actual = con.execute("""
            SELECT trade_date, qfq_close, qfq_high, qfq_low, amount, adjusted_quality
            FROM read_parquet(?) WHERE canonical_security_id=? AND trade_date<=20260924
              AND trading_status='ACTUAL_TRADED'
            ORDER BY trade_date DESC LIMIT 251
        """, [str(inputs["daily"].path), sid]).fetchall()
        actual.reverse()
        if actual and actual[-1][0] == 20260924 and actual[-1][5] == "READY":
            prior = actual[-21:-1]
            if len(prior) == 20 and all(isinstance(x[4], (int, float)) for x in prior):
                start = f"{prior[0][0]:08d}"[:4] + "-" + f"{prior[0][0]:08d}"[4:6] + "-" + f"{prior[0][0]:08d}"[6:8]
                end = f"{prior[-1][0]:08d}"[:4] + "-" + f"{prior[-1][0]:08d}"[4:6] + "-" + f"{prior[-1][0]:08d}"[6:8]
                calendar_dates = [str(date) for date in calendars["SH" if row["board"] in ("SH_MAIN", "STAR") else "SZ"]
                                  if start <= str(date) <= end]
                source_dates = {f"{x[0]:08d}"[:4] + "-" + f"{x[0]:08d}"[4:6] + "-" + f"{x[0]:08d}"[6:8] for x in prior}
                status_map = sampled_statuses[sid]
                evaluable = (all(status_map.get(date) in ("ACTUAL_TRADED", "SUSPENDED") for date in calendar_dates)
                             and {date for date in calendar_dates if status_map[date] == "ACTUAL_TRADED"} == source_dates)
                if evaluable:
                    minimum_liquidity_source_evaluable_count += 1
                    if row["primitive_quality"]["amount_ratio20"]["quality_state"] != "OBSERVED":
                        amount_ratio20_unknown_but_liquidity_evaluable_count += 1
                    expected_liquid = sum(float(x[4]) for x in prior) / 20 >= parameters["V4_04_MINIMUM_LIQUIDITY_CNY"]
                    if row["derived_fields"]["minimum_liquidity"]["value"] is None:
                        minimum_liquidity_false_unknown_count += 1
                    elif row["derived_fields"]["minimum_liquidity"]["value"] != expected_liquid:
                        raise ValueError("minimum_liquidity independently evaluable value mismatch")
        for name, source_rows in (("ma10", actual[-10:]),
                                  ("minimum_liquidity", actual[-21:-1]),
                                  ("pos250", actual[-250:])):
            item = row["derived_fields"][name]
            if item["value"] is None:
                continue
            expected_dates = [str(date) for date in calendars["SH" if row["board"] in ("SH_MAIN", "STAR") else "SZ"]
                              if item["window_start_trade_date"] <= str(date) <= item["window_end_trade_date"]]
            source_dates = {f"{x[0]:08d}"[:4] + "-" + f"{x[0]:08d}"[4:6] + "-" + f"{x[0]:08d}"[6:8] for x in source_rows}
            statuses_for_window = sampled_statuses[sid]
            if (len(source_rows) != item["actual_count"] or len(expected_dates) != item["calendar_span"] or
                    any(statuses_for_window.get(date) not in ("ACTUAL_TRADED", "SUSPENDED") for date in expected_dates) or
                    {date for date in expected_dates if statuses_for_window[date] == "ACTUAL_TRADED"} != source_dates or
                    sum(statuses_for_window[date] == "SUSPENDED" for date in expected_dates) != item["suspended_count"]):
                raise ValueError(f"independent technical window status mismatch: {name}")
            sampled_checks[name + "_status_window"] += 1
        if actual and actual[-1][0] == 20260924 and actual[-1][5] == "READY":
            fields = row["derived_fields"]
            accepted_fields = factors[sid]["fields"]
            accepted_values = {name: accepted_fields[name]["value"] if accepted_fields[name]["quality_state"] == "OBSERVED" else None
                               for name in ("ma20", "atr20", "prior_high20")}
            source_close = float(actual[-1][1]) if actual[-1][1] is not None else None
            atr = accepted_values["atr20"]
            if source_close is not None and isinstance(atr, (int, float)) and atr > 0:
                for name, numerator in (("bias20_atr", None if accepted_values["ma20"] is None else source_close - accepted_values["ma20"]),
                                        ("dist_high20_atr", None if accepted_values["prior_high20"] is None else accepted_values["prior_high20"] - source_close)):
                    if numerator is not None and fields[name]["value"] is not None:
                        if abs(numerator / atr - fields[name]["value"]) > 1e-9:
                            raise ValueError(f"{name} direct accepted-source recompute mismatch")
                        sampled_checks[name] += 1
            if fields["ma10"]["value"] is not None:
                mean10 = sum(float(x[1]) for x in actual[-10:]) / 10
                if abs(mean10 - fields["ma10"]["value"]) > 1e-9:
                    raise ValueError("MA10 independent source mismatch")
                machine = execute_rule(algorithm["rules"], "V4_04_DERIVED_PRIMITIVES_V1.ma10",
                                       {"accepted_QFQ_close": [float(x[1]) for x in actual if x[1] is not None]}, parameters)
                if machine is None or abs(machine - mean10) > 1e-9:
                    raise ValueError("MA10 machine/source mismatch")
                executed_rules.add("V4_04_DERIVED_PRIMITIVES_V1.ma10")
                sampled_checks["ma10"] += 1
            if fields["minimum_liquidity"]["value"] is not None:
                prior20 = sum(float(x[4]) for x in actual[-21:-1]) / 20
                if (prior20 >= 20_000_000) != fields["minimum_liquidity"]["value"]:
                    raise ValueError("minimum liquidity independent source mismatch")
                machine = execute_rule(algorithm["rules"], "V4_04_DERIVED_PRIMITIVES_V1.minimum_liquidity",
                                       {"accepted_raw_CNY_amount": [float(x[4]) if x[4] is not None else None for x in actual]}, parameters)
                if machine != fields["minimum_liquidity"]["value"]:
                    raise ValueError("minimum liquidity machine/source mismatch")
                executed_rules.add("V4_04_DERIVED_PRIMITIVES_V1.minimum_liquidity")
                sampled_checks["minimum_liquidity"] += 1
            if fields["pos250"]["value"] is not None:
                high = max(float(x[2]) for x in actual[-250:])
                low = min(float(x[3]) for x in actual[-250:])
                pos = (float(actual[-1][1]) - low) / (high - low)
                if abs(pos - fields["pos250"]["value"]) > 1e-9:
                    raise ValueError("pos250 independent source mismatch")
                machine = execute_rule(algorithm["rules"], "V4_04_DERIVED_PRIMITIVES_V1.pos250",
                                       {"close": float(actual[-1][1]), "HHV250": high, "LLV250": low}, parameters)
                if machine is None or abs(machine - pos) > 1e-9:
                    raise ValueError("pos250 machine/source mismatch")
                executed_rules.add("V4_04_DERIVED_PRIMITIVES_V1.pos250")
                sampled_checks["pos250"] += 1
        for period_name, key, window in (("weekly", "ma5", 5), ("monthly", "ma3", 3)):
            state = row["states"][f"{period_name}_trend_state"]
            periods = con.execute("""
                SELECT close, period_status, period_last_session, period_view, price_basis, source_daily_digest FROM read_parquet(?)
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
                lineage = row["period_lineage"][f"{period_name}_trend_state"]
                source_rows = [{"period_last_session": f"{p[2]:08d}"[:4] + "-" + f"{p[2]:08d}"[4:6] + "-" + f"{p[2]:08d}"[6:8],
                                "period_view": p[3], "period_status": p[1], "price_basis": p[4],
                                "close": float(p[0]) if p[0] is not None else None,
                                "source_daily_digest": p[5]} for p in periods]
                if (lineage["window_identity"] != digest(source_rows) or
                        lineage["source_daily_digest"] != digest([p[5] for p in periods]) or
                        lineage["period_last_session"] != source_rows[-1]["period_last_session"]):
                    raise ValueError("closed-period independent lineage mismatch")
                sampled_checks[period_name] += 1
    if executed_rules != registered_rules:
        raise ValueError(f"unexecuted machine rules: {sorted(registered_rules - executed_rules)}")
    required_source_checks = ("ma10", "minimum_liquidity", "pos250", "bias20_atr",
                              "dist_high20_atr", "weekly", "monthly")
    if any(sampled_checks[name] <= 0 for name in required_source_checks):
        raise ValueError("required direct source recomputation sample missing")
    if minimum_liquidity_false_unknown_count:
        raise ValueError("minimum_liquidity false UNKNOWN on independently evaluable sample")
    from src.v4.profile_core import drawdown as production_drawdown
    for horizon in (20, 60):
        for close, expected in ((9.5, "SHALLOW"), (8.5, "MODERATE")):
            machine = execute_rule(algorithm["rules"], "POSITION_STATE_V1.drawdown",
                                   {"close": close, "hhvN": 10}, parameters)
            produced = production_drawdown({"close": close, f"hhv{horizon}": 10}, horizon).value
            if machine != expected or produced != expected:
                raise ValueError("drawdown inclusive contract boundary divergence")
    result = {"contract_id": "V4_04_INDEPENDENT_POSTCHECK_R4", "status": "PASS",
              "machine_vector_receipt_sha256": sha256(VECTOR_RECEIPT.read_bytes()).hexdigest(),
              "machine_branch_count": vector["branch_count"],
              "machine_rules_with_full_vector_coverage": len(vector["rules_with_full_vector_coverage"]),
              "machine_rule_count": len(registered_rules), "machine_rules_executed": sorted(executed_rules),
              "machine_rule_coverage": len(executed_rules) / len(registered_rules),
              "operators_declared": sorted(declared), "operators_supported": sorted(OPERATORS),
              "unsupported_operators": unsupported,
              "unexecuted_machine_rules": sorted(registered_rules - executed_rules),
              "artifact_sha256": actual_hash, "rows_checked": len(rows), "board_count": dict(boards),
              "unknown_by_state": dict(unknowns), "source_recompute_sample_count": len(sample),
              "sample_categories": categories,
              "sampled_checks": dict(sampled_checks), "limitations": ["sampled source recomputation; all state AST evidence independently checked"]}
    result.update({"minimum_liquidity_source_evaluable_count": minimum_liquidity_source_evaluable_count,
                   "minimum_liquidity_false_unknown_count": minimum_liquidity_false_unknown_count,
                   "amount_ratio20_unknown_but_liquidity_evaluable_count": amount_ratio20_unknown_but_liquidity_evaluable_count,
                   "drawdown_inclusive_boundary_check": "PASS_20_AND_60",
                   "semantic_machine_vector_status": vector["semantic_categories_status"]})
    atomic_json(OUT, result)
    atomic_json(OUT.parent / "V4_04_REGISTRY_ARTIFACT_CONSISTENCY_R4.json",
        {"contract_id": "V4_04_REGISTRY_ARTIFACT_CONSISTENCY_R4", "status": "PASS",
                     "artifact_sha256": actual_hash, "rows_checked": len(rows),
                     "fields_checked": len(registry["fields"]),
                     "registry_sha256": contract_hashes["config/v4_04_field_registry_v2.json"]})
    atomic_json(OUT.parent / "V4_04_WINDOW_TRACEABILITY_R4.json",
        {"contract_id": "V4_04_WINDOW_TRACEABILITY_R4", "status": "PASS",
                     "artifact_sha256": actual_hash, "rows_checked": len(rows),
                     "field_window_mapping_sha256": sha256(mapping_path.read_bytes()).hexdigest(),
                     "accepted_v4_03_mapping_sha256": mapping["accepted_v4_03_mapping_sha256"],
                     "lineage_fields": ["window_start_trade_date", "window_end_trade_date", "calendar_span",
                                        "actual_count", "suspended_count", "window_identity", "input_digest"],
                     "closed_period_lineage": ["window_identity", "period_last_session", "period_view",
                                               "source_daily_digest"]})
    print(json.dumps({"status": result["status"], "rows": len(rows), "sample": len(sample), "checks": sampled_checks}, default=dict))


if __name__ == "__main__":
    main()
