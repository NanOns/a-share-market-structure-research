"""Independent execution of every V4-04 machine rule; no production rule imports."""

from __future__ import annotations

from statistics import fmean

OPERATORS = frozenset({"AND", "OR", "NOT", "GT", "GE", "LT", "LE", "EQ", "IN",
                       "NEG", "MUL", "DIV", "SUB", "ADD", "MEAN", "FIRST_TRUE",
                       "CLOSED_PERIOD_TREND", "CLASSIFY_DISTANCE", "CLASSIFY_DRAWDOWN",
                       "HYSTERETIC_FIRST_TRUE"})


def declared_operators(node):
    found = set()
    if isinstance(node, dict):
        if "operator" in node:
            found.add(node["operator"])
        for value in node.values():
            found.update(declared_operators(value))
    elif isinstance(node, list):
        for value in node:
            found.update(declared_operators(value))
    return found


def rule_keys(rules):
    return (set(rules) - {"V4_04_DERIVED_PRIMITIVES_V1"}) | {
            f"V4_04_DERIVED_PRIMITIVES_V1.{field}"
            for field in rules["V4_04_DERIVED_PRIMITIVES_V1"]}


def execute(node, evidence, parameters):
    if "field" in node:
        value = evidence.get(node["field"])
        return None if value == "UNKNOWN" else value
    if "parameter_id" in node:
        return parameters[node["parameter_id"]]
    if "constant" in node:
        return node["constant"]
    if "set" in node:
        return node["set"]
    op = node["operator"]
    if op not in OPERATORS:
        raise ValueError(f"unsupported V4-04 operator: {op}")
    if op == "FIRST_TRUE":
        for branch in node["branches"]:
            condition = execute(branch["when"], evidence, parameters)
            if condition is None:
                return "UNKNOWN"
            if condition:
                return branch["value"]
        raise ValueError("FIRST_TRUE has no final branch")
    if op == "MEAN":
        size = int(execute(node["window_parameter_id"], evidence, parameters))
        source = evidence.get(node["source"])
        if source is None:
            return None
        values = source[-size:] if node["include_current"] else source[-size-1:-1]
        return fmean(values) if len(values) == size and all(isinstance(x, (int, float)) for x in values) else None
    if op == "CLOSED_PERIOD_TREND":
        if evidence.get("period_view") != node["required_period_view"]:
            return "UNKNOWN"
        required = ("close", "ma_current", "ma_previous")
        if any(evidence.get(field) is None for field in required):
            return "UNKNOWN"
        prefix = evidence["period_type"].upper()
        if execute(node["up"], evidence, parameters):
            return prefix + "_UP"
        if execute(node["down"], evidence, parameters):
            return prefix + "_DOWN"
        return prefix + "_" + node["else"]
    if op in ("CLASSIFY_DISTANCE", "CLASSIFY_DRAWDOWN"):
        computed = execute(node["distance_ast" if op == "CLASSIFY_DISTANCE" else "drawdown_ast"], evidence, parameters)
        if computed is None:
            return "UNKNOWN"
        local = dict(evidence)
        local["distance" if op == "CLASSIFY_DISTANCE" else
              "drawdown_ratio" if node.get("comparison_basis") == "PRICE_RATIO_V1" else "drawdown"] = computed
        return execute(node["branches"], local, parameters)
    if op == "HYSTERETIC_FIRST_TRUE":
        path = evidence["path"]
        accepted = pending = None
        count = 0
        result = label = "UNKNOWN"
        switch = int(execute(node["switch_sessions_parameter_id"], evidence, parameters))
        for axes in path:
            label = ("UNKNOWN" if any(axes.get(key) in (None, "UNKNOWN") for key in node["required_axes"])
                     else execute(node["candidate"], axes, parameters))
            if label == "UNKNOWN":
                pending, count, result = None, 0, "UNKNOWN"
            elif label in node["immediate_labels"]:
                accepted, pending, count, result = label, None, 0, label
            elif label == accepted:
                pending, count, result = None, 0, label
            else:
                count = count + 1 if pending == label else 1
                pending = label
                if count >= switch:
                    accepted, pending, count, result = label, None, 0, label
                else:
                    result = accepted or "UNKNOWN"
        return result, accepted, count, label
    args = [execute(arg, evidence, parameters) for arg in node["args"]]
    if op == "AND":
        return False if False in args else None if None in args else True
    if op == "OR":
        return True if True in args else None if None in args else False
    if op == "NOT":
        return None if args[0] is None else not args[0]
    if None in args:
        return None
    if op == "GT": return args[0] > args[1]
    if op == "GE": return args[0] >= args[1]
    if op == "LT": return args[0] < args[1]
    if op == "LE": return args[0] <= args[1]
    if op == "EQ": return args[0] == args[1]
    if op == "IN": return args[0] in args[1]
    if op == "NEG": return -args[0]
    if op == "MUL": return args[0] * args[1]
    if op == "SUB": return args[0] - args[1]
    if op == "ADD": return args[0] + args[1]
    if op == "DIV": return None if args[1] == 0 else args[0] / args[1]
    raise AssertionError(op)


def execute_rule(rules, key, evidence, parameters):
    prefix = "V4_04_DERIVED_PRIMITIVES_V1."
    node = rules["V4_04_DERIVED_PRIMITIVES_V1"][key[len(prefix):]] if key.startswith(prefix) else rules[key]
    required = node.get("required_fields", []) + node.get("required_enum_dependencies", [])
    if any(evidence.get(field) in (None, "UNKNOWN") for field in required):
        return node.get("unknown_output", "UNKNOWN")
    if node.get("unknown_policy") == "UNKNOWN_IF_RISK_UNKNOWN" and evidence.get("core_extension_risk") in (None, "UNKNOWN"):
        return None
    return execute(node, evidence, parameters)
