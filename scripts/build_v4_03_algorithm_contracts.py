"""Serialize the 47 stock/relative V4-03 formulas as RULE_AST_V2 contracts."""

import hashlib
import json
import os
from pathlib import Path

from src.v4.contracts.algorithm_contract_v12 import validate_contract_v12


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "config/v4_03_algorithm_contracts_v1.json"
TECH = "TECHNICAL_BAR_WINDOW_V1"
CROSS = "CROSS_SECTION_SESSION_WINDOW_V1"
MISSING = "PROPAGATE_UNKNOWN_NO_DROP_NO_SHORTEN"


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def field(name, value_type="SESSION_SERIES"):
    return {"type": "FIELD_REF", "field_id": name, "value_type": value_type}


def param(n):
    return {"type": "PARAM_REF", "parameter_id": f"V4_03_WINDOW_SIZE_{n}"}


def lag(source, n):
    return {"type": "LAG", "source": source, "offset": param(n), "direction": "PRIOR_ONLY"}


def arithmetic(op, a, b):
    return {"type": "ARITHMETIC", "operator": op, "args": [a, b]}


def transform(op, *args):
    return {"type": "TRANSFORM", "operator": op, "args": list(args)}


def aggregate(op, source, n, window=TECH, include=True):
    return {"type": "WINDOW_AGGREGATE", "operator": op, "source": source,
            "window_contract_id": window, "window_size": param(n),
            "include_current": include, "missing_policy": MISSING}


def simple_ret(n):
    return arithmetic("SUB", arithmetic("DIV", field("close"), lag(field("close"), n)),
                      {"type": "PARAM_REF", "parameter_id": "V4_03_ONE"})


def true_range():
    prev = lag(field("close"), 1)
    a = arithmetic("SUB", field("high"), field("low"))
    b = transform("ABS", arithmetic("SUB", field("high"), prev))
    c = transform("ABS", arithmetic("SUB", field("low"), prev))
    return {"type": "ARITHMETIC", "operator": "MAX", "args": [a, {"type": "ARITHMETIC", "operator": "MAX", "args": [b, c]}]}


def atr(n):
    return aggregate("MEAN", true_range(), n, TECH, True)


def ma(n):
    return aggregate("MEAN", field("close"), n)


def high_low(op, col, n, include=True):
    return aggregate(op, field(col), n, TECH, include)


def contract_ast(field_id):
    if field_id.startswith("ma"):
        return ma(int(field_id[2:]))
    if field_id.startswith("ret"):
        return simple_ret(int(field_id[3:]))
    if field_id.startswith("vol") and not field_id.startswith("volume") and field_id != "vol_ratio":
        n = int(field_id[3:])
        log_return = transform("LOG", arithmetic("DIV", field("close"), lag(field("close"), 1)))
        return aggregate("POP_STDDEV", log_return, n, CROSS, True)
    if field_id == "tr":
        return true_range()
    if field_id.startswith("atr") and field_id != "atr_ratio":
        return atr(int(field_id[3:]))
    for prefix, op, col, include in (("hhv", "MAX", "high", True), ("llv", "MIN", "low", True),
                                     ("prior_high", "MAX", "high", False), ("prior_low", "MIN", "low", False)):
        if field_id.startswith(prefix):
            return high_low(op, col, int(field_id[len(prefix):]), include)
    if field_id == "pos60":
        return arithmetic("DIV", arithmetic("SUB", field("close"), high_low("MIN", "low", 60)),
                          arithmetic("SUB", high_low("MAX", "high", 60), high_low("MIN", "low", 60)))
    if field_id in {"slope20", "slope60"}:
        n, offset = (20, 5) if field_id == "slope20" else (60, 10)
        return arithmetic("DIV", arithmetic("SUB", ma(n), lag(ma(n), offset)), atr(20))
    if field_id in {"hh_progress", "ll_progress"}:
        op, col, compare = ("MAX", "high", "GT") if field_id == "hh_progress" else ("MIN", "low", "LT")
        recent = high_low(op, col, 5)
        prior = aggregate(op, lag(field(col), 5), 5, TECH, True)
        return {"type": "COMPARE", "operator": compare, "args": [recent, prior]}
    if field_id in {"range_ratio", "atr_ratio", "vol_ratio"}:
        if field_id == "range_ratio":
            num = arithmetic("SUB", high_low("MAX", "high", 5), high_low("MIN", "low", 5))
            den = arithmetic("SUB", high_low("MAX", "high", 20), high_low("MIN", "low", 20))
        elif field_id == "atr_ratio":
            num, den = atr(5), atr(20)
        else:
            def vol(n):
                r = transform("LOG", arithmetic("DIV", field("close"), lag(field("close"), 1)))
                return aggregate("POP_STDDEV", r, n, CROSS, True)
            num, den = vol(5), vol(20)
        return arithmetic("DIV", num, den)
    if field_id.startswith("amount_ratio") or field_id.startswith("volume_ratio"):
        n = int(field_id.rsplit("ratio", 1)[1])
        col = "amount" if field_id.startswith("amount") else "volume"
        return arithmetic("DIV", field(col), aggregate("MEAN", field(col), n, TECH, False))
    if field_id == "prior60_percentile":
        return {"type": "WINDOW_RANK", "operator": "MIDRANK_PERCENTILE",
                "source": field("close"), "target_ref": "close",
                "window_contract_id": TECH, "window_size": param(60),
                "include_target": False, "tie_policy": "MIDRANK_PERCENTILE_V1",
                "missing_policy": MISSING}
    if field_id == "clv":
        return arithmetic("DIV", arithmetic("SUB", field("close"), field("low")),
                          arithmetic("SUB", field("high"), field("low")))
    if field_id == "core_price_damage":
        lhs = {"type": "COMPARE", "operator": "LT", "args": [field("close"),
               arithmetic("SUB", high_low("MIN", "low", 20, False),
                          arithmetic("MUL", {"type": "PARAM_REF", "parameter_id": "V4_03_CORE_PRICE_DAMAGE_ATR_MULTIPLE"}, atr(20)))]}
        rhs = {"type": "COMPARE", "operator": "LT", "args": [field("ret1", "NUMBER"),
               {"type": "PARAM_REF", "parameter_id": "V4_03_ZERO"}]}
        return {"type": "AND", "operator": "AND", "args": [lhs, rhs]}
    if field_id in {"rps5", "rps20"}:
        n = int(field_id[3:])
        return {"type": "CROSS_SECTION", "operator": "MIDRANK", "source": field(f"ret{n}", "NUMBER"),
                "universe_ref": "pit_universe", "evaluable_policy": "SAME_DATE_PIT_EVALUABLE_EXCLUDE_UNKNOWN_RETAIN_COUNTS",
                "tie_policy": "MIDRANK_PERCENTILE_V1"}
    if "delta" in field_id:
        base_field, offset = field_id.split("_delta")
        return arithmetic("SUB", field_ref(base_field), lag(field_ref(base_field), int(offset)))
    if field_id.startswith("rel_market_"):
        n = int(field_id.rsplit("_", 1)[1])
        return arithmetic("SUB", field(f"ret{n}", "NUMBER"), field(f"market_reference_return_{n}", "NUMBER"))
    raise ValueError(f"no V4-03 AST mapping for {field_id}")


def field_ref(name):
    return field(name, "NUMBER")


def walk(node):
    if isinstance(node, dict):
        if node.get("type") == "FIELD_REF":
            yield node["field_id"], node["value_type"]
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def input_meta(name, value_type):
    unit = "adjusted_price" if name in {"close", "high", "low", "open"} else "raw_CNY" if name == "amount" else "accepted_raw_volume" if name == "volume" else "return_fraction" if name.startswith("ret") or name.startswith("market_reference") else "same_date_historical_PIT_universe" if name == "pit_universe" else "percentage_points"
    source = "V4_02_ACCEPTED_ADJUSTED_DAILY" if unit in {"adjusted_price", "raw_CNY", "accepted_raw_volume"} else "V4_01_HISTORICAL_UNIVERSE_AND_V4_03_DERIVED_ARTIFACT"
    return {"field_id": name, "type": value_type, "unit": unit, "source": source, "required": True}


def window_ref(window):
    if window == TECH:
        identity = {"security_id": "bound_at_runtime", "source_snapshot_id": "bound_at_runtime",
                    "trade_date": "bound_at_runtime", "adjustment_basis_id": "bound_at_runtime"}
    else:
        identity = {"market_calendar_id": "bound_at_runtime", "start_session": "bound_at_runtime",
                    "end_session": "bound_at_runtime", "universe_snapshot_id": "bound_at_runtime",
                    "adjustment_basis_id": "bound_at_runtime"}
    return {"contract_id": window, "identity": identity}


def main():
    scope = json.loads((ROOT / "config/v4_03_field_scope_map_v1.json").read_text(encoding="utf-8"))
    output_schema = json.loads((ROOT / "config/v4_03_output_schema_v1.json").read_text(encoding="utf-8"))
    schemas = {item["field_id"]: item for item in output_schema["fields"]}
    registry = json.loads((ROOT / "config/v4_03_parameter_registry_v1.json").read_text(encoding="utf-8"))
    base = json.loads((ROOT / "config/v4_algorithm_contract_framework_v1.json").read_text(encoding="utf-8"))
    extension_path = ROOT / "config/v4_algorithm_contract_framework_v1_2_0.json"
    extension = json.loads(extension_path.read_text(encoding="utf-8"))
    extension_sha256 = hashlib.sha256(extension_path.read_bytes()).hexdigest()
    contracts = []
    for output_field in sorted(scope["produced_fields"]):
        ast = contract_ast(output_field)
        field_set = set(walk(ast))
        for node in walk_nodes(ast):
            if node.get("type") == "CROSS_SECTION":
                field_set.add((node["universe_ref"], "MEMBER_SET"))
            if node.get("type") == "WINDOW_RANK":
                field_set.add((node["target_ref"], "SESSION_SERIES"))
        fields = sorted(field_set)
        input_fields = [input_meta(name, typ) for name, typ in fields]
        windows = {ref for ref in walk_windows(ast)}
        if not windows:
            windows = {scope["produced_fields"][output_field]}
        outputs = [schemas[output_field]]
        source_digest = digest({"contract_id": output_field, "ast": ast, "outputs": outputs,
                                "framework": "V4_ALGORITHM_CONTRACT_FRAMEWORK_V1@1.2.0",
                                "framework_extension_sha256": extension_sha256})
        window_refs = [window_ref(w) for w in sorted(windows)]
        vectors = [{"vector_id": f"{output_field.upper()}_SHORT_HISTORY", "input": {"case": "one_sample_short"},
                    "expected": {"quality_state": "UNKNOWN", "unknown_reason": "INSUFFICIENT_HISTORY"},
                    "source_digest": source_digest}]
        if output_field == "ma20":
            vectors.insert(0, {"vector_id": "MA20_EXACT_20_SAMPLE", "input": {"close": list(range(1, 21))},
                               "expected": {"value": 10.5, "quality_state": "OBSERVED"},
                               "source_digest": source_digest})
        contract = {
            "contract_id": f"V4_03_{output_field.upper()}_V1", "contract_version": "1.0.0",
            "parameter_set_id": registry["parameter_set_id"], "ast_version": "RULE_AST_V2",
            "framework_extension_id": extension["contract_id"],
            "framework_extension_version": extension["version"],
            "framework_extension_sha256": extension_sha256,
            "inputs": input_fields,
            "producer": {"producer_contract_id": schemas[output_field]["producer_contract_id"], "version": "1.0.0"},
            "as_of": {"field_id": "trade_date", "timestamp_semantics": "fixed_market_session_t" if any(w == CROSS for w in windows) else "security_session_t"},
            "quality_requirements": {"acceptable_states": ["OBSERVED"], "unknown_action": "UNKNOWN"},
            "ast": ast, "window_refs": window_refs,
            "rounding": {"mode": "NONE", "precision": None}, "mutual_exclusion": [],
            "outputs": outputs, "identity_fields": ["security_id", "trade_date", "adjustment_basis_id", "source_digest"],
            "unknown_policy": {"action": "UNKNOWN", "reason_code": "FIELD_LOCAL_REQUIRED_INPUT_OR_WINDOW_UNKNOWN"},
            "independent_vectors": vectors, "source_digest": source_digest, "enum_contracts": {}}
        try:
            validate_contract_v12(contract, registry, base, extension, extension_sha256)
        except Exception as exc:
            raise RuntimeError(f"contract validation failed for {output_field}: {exc}") from exc
        contracts.append(contract)
    payload = {"contract_id": "V4_03_ALGORITHM_CONTRACT_SET_V1", "version": "1.0.0",
               "framework_extension": "V4_ALGORITHM_CONTRACT_FRAMEWORK_V1@1.2.0",
               "framework_extension_sha256": extension_sha256,
               "contracts": contracts, "contract_count": len(contracts),
               "validation_status": "ALL_CONTRACT_SCHEMAS_AND_AST_V2_VALIDATED"}
    temp = OUTPUT.with_suffix(".json.tmp")
    temp.write_bytes((json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    os.replace(temp, OUTPUT)
    print(f"{len(contracts)} contracts validated")


def walk_windows(node):
    if isinstance(node, dict):
        if node.get("type") in {"WINDOW_AGGREGATE", "WINDOW_RANK"}:
            yield node["window_contract_id"]
        for value in node.values():
            yield from walk_windows(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk_windows(value)


def walk_nodes(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk_nodes(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk_nodes(value)


if __name__ == "__main__":
    main()
