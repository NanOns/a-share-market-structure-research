"""Execute V4-03 RULE_AST_V2 numeric vectors without factor producer imports.

The structural validator remains versioned separately.  This interpreter is
deliberately small: it supports exactly the nodes admitted by that validator
and reads a frozen synthetic fixture with explicit session and PIT membership.
"""

from __future__ import annotations

import math
from pathlib import Path
from statistics import fmean, median, pstdev
from typing import Any, Mapping

from .algorithm_contract import ContractValidationError
from .algorithm_contract_v12 import validate_contract_v12


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class NumericContext:
    def __init__(self, fixture: Mapping[str, Any], parameters: Mapping[str, Any], *, missing: bool = False):
        self.history = [] if missing else fixture["history"]
        self.relative = {} if missing else fixture["relative"]
        self.parameters = parameters
        self.target = self.relative.get("target_security_id")

    def prior(self, position: int, count: int, mode: str) -> int | None:
        if mode == "CROSS_SECTION_SESSION_WINDOW_V1":
            prior = position - count
            return prior if prior >= 0 else None
        found = 0
        for index in range(position - 1, -1, -1):
            state = self.history[index]["state"]
            if state not in {"ACTUAL", "CONFIRMED_SUSPENSION"}:
                return None
            if state == "ACTUAL":
                found += 1
                if found == count:
                    return index
        return None

    def positions(self, position: int, count: int, mode: str, include_current: bool) -> list[int] | None:
        if mode == "CROSS_SECTION_SESSION_WINDOW_V1":
            end = position + 1 if include_current else position
            start = end - count
            if start < 0:
                return None
            indexes = list(range(start, end))
            return indexes if all(self.history[i]["state"] == "ACTUAL" for i in indexes) else None
        indexes = []
        start = position if include_current else position - 1
        for index in range(start, -1, -1):
            state = self.history[index]["state"]
            if state not in {"ACTUAL", "CONFIRMED_SUSPENSION"}:
                return None
            if state == "ACTUAL":
                indexes.append(index)
                if len(indexes) == count:
                    return list(reversed(indexes))
        return None

    def field(self, name: str, position: int, member: str | None) -> Any:
        if member is not None and member != self.target:
            return self.relative.get("cross_section", {}).get(name, {}).get(member)
        series = self.relative.get("field_series", {}).get(name)
        if series is not None:
            offset = len(self.history) - 1 - position
            return series[-1 - offset] if 0 <= offset < len(series) else None
        scalar = self.relative.get("target_scalar", {})
        if name in scalar:
            return scalar[name] if position == len(self.history) - 1 else None
        if position < 0 or position >= len(self.history):
            return None
        row = self.history[position]
        return row["bar"].get(name) if row["state"] == "ACTUAL" and row.get("bar") else None

    def eval(self, node: Mapping[str, Any], position: int, mode: str, member: str | None = None) -> Any:
        kind = node["type"]
        if kind == "FIELD_REF":
            return self.field(node["field_id"], position, member)
        if kind == "PARAM_REF":
            return self.parameters[node["parameter_id"]]
        if kind == "MATH_LITERAL":
            return {"PI": math.pi, "E": math.e}[node["constant_id"]]
        if kind == "LAG":
            previous = self.prior(position, int(self.eval(node["offset"], position, mode)), mode)
            return None if previous is None else self.eval(node["source"], previous, mode, member)
        if kind == "WINDOW_AGGREGATE":
            window_mode = node["window_contract_id"]
            count = int(self.eval(node["window_size"], position, mode))
            indexes = self.positions(position, count, window_mode, node["include_current"])
            if indexes is None:
                return None
            values = [self.eval(node["source"], index, window_mode, member) for index in indexes]
            if any(not _number(value) for value in values):
                return None
            op = node["operator"]
            return {"MEAN": lambda: fmean(values), "SUM": lambda: sum(values),
                    "MIN": lambda: min(values), "MAX": lambda: max(values),
                    "COUNT": lambda: len(values), "POP_STDDEV": lambda: pstdev(values)}[op]()
        if kind == "WINDOW_RANK":
            count = int(self.eval(node["window_size"], position, mode))
            indexes = self.positions(position, count, node["window_contract_id"], node["include_target"])
            target = self.field(node["target_ref"], position, member)
            if indexes is None or not _number(target):
                return None
            values = [self.eval(node["source"], index, node["window_contract_id"], member) for index in indexes]
            if any(not _number(value) for value in values):
                return None
            return 100 * (sum(value < target for value in values) + .5 * sum(value == target for value in values)) / len(values)
        if kind == "CROSS_SECTION":
            members = sorted(set(self.relative.get("pit_universe", [])))
            values = {sid: self.eval(node["source"], position, mode, sid) for sid in members}
            values = {sid: value for sid, value in values.items() if _number(value)}
            op = node["operator"]
            if op == "MIDRANK":
                current = values.get(self.target)
                if current is None or len(values) < 2:
                    return None
                less = sum(value < current for value in values.values())
                equal = sum(value == current for value in values.values())
                return 100 * (less + .5 * (equal - 1)) / (len(values) - 1)
            sequence = list(values.values())
            if not sequence:
                return None
            return {"MEAN": lambda: fmean(sequence), "MEDIAN": lambda: median(sequence),
                    "COUNT": lambda: len(sequence), "COUNT_TRUE": lambda: sum(bool(v) for v in sequence),
                    "SUM": lambda: sum(sequence), "MIN": lambda: min(sequence),
                    "MAX": lambda: max(sequence)}[op]()
        if kind == "TRANSFORM":
            values = [self.eval(child, position, mode, member) for child in node["args"]]
            if any(not _number(value) for value in values):
                return None
            op = node["operator"]
            if op == "LOG":
                return math.log(values[0]) if values[0] > 0 else None
            if op == "ABS":
                return abs(values[0])
            if op == "SIMPLE_RETURN":
                return values[0] / values[1] - 1 if values[1] != 0 else None
            return values[0] - values[1]
        values = [self.eval(child, position, mode, member) for child in node["args"]]
        if any(value is None for value in values):
            return None
        op = node["operator"]
        if kind == "ARITHMETIC":
            if any(not _number(value) for value in values):
                return None
            a, b = values
            return {"ADD": lambda: a + b, "SUB": lambda: a - b,
                    "MUL": lambda: a * b, "DIV": lambda: a / b if b else None,
                    "MIN": lambda: min(a, b), "MAX": lambda: max(a, b)}[op]()
        if kind == "COMPARE":
            a, b = values
            return {"GT": lambda: a > b, "GTE": lambda: a >= b,
                    "LT": lambda: a < b, "LTE": lambda: a <= b,
                    "EQ": lambda: a == b, "NE": lambda: a != b}[op]()
        if kind == "NOT":
            return not values[0]
        if kind == "AND":
            return all(values)
        if kind == "OR":
            return any(values)
        raise ContractValidationError(f"AST_V2_EXECUTOR_UNSUPPORTED_NODE:{kind}")


def validate_contract_with_vectors_v12(contract: Mapping[str, Any], registry: Mapping[str, Any],
                                       base_framework: Mapping[str, Any], framework_extension: Mapping[str, Any],
                                       framework_extension_sha256: str, fixture: Mapping[str, Any],
                                       fixture_sha256: str) -> int:
    """Validate schema, then execute every frozen positive and negative vector."""
    validate_contract_v12(contract, registry, base_framework, framework_extension, framework_extension_sha256)
    parameters = {entry["parameter_id"]: entry["value"] for entry in registry["entries"]}
    mode = contract["window_refs"][0]["contract_id"]
    checked_cases = set()
    for vector in contract["independent_vectors"]:
        spec = vector["input"]
        if (spec.get("fixture_id") != fixture.get("contract_id") or
                spec.get("fixture_sha256") != fixture_sha256 or
                spec.get("case") not in {"OBSERVED", "UNKNOWN_INPUT"}):
            raise ContractValidationError(f"AST_V2_VECTOR_FIXTURE_IDENTITY_INVALID:{vector['vector_id']}")
        case = spec["case"]
        checked_cases.add(case)
        context = NumericContext(fixture, parameters, missing=case == "UNKNOWN_INPUT")
        position = len(context.history) - 1
        actual = context.eval(contract["ast"], position, mode)
        expected = vector["expected"]
        expected_quality = expected.get("quality_state")
        if expected_quality not in {"OBSERVED", "UNKNOWN"}:
            raise ContractValidationError(f"AST_V2_VECTOR_QUALITY_INVALID:{vector['vector_id']}")
        actual_quality = "UNKNOWN" if actual is None else "OBSERVED"
        if actual_quality != expected_quality:
            raise ContractValidationError(f"AST_V2_VECTOR_QUALITY_MISMATCH:{vector['vector_id']}")
        wanted = expected.get("value")
        if (wanted is None) != (actual is None):
            raise ContractValidationError(f"AST_V2_VECTOR_VALUE_MISMATCH:{vector['vector_id']}")
        if wanted is not None:
            if isinstance(wanted, bool) or isinstance(actual, bool):
                good = actual is wanted
            else:
                good = math.isclose(float(actual), float(wanted), rel_tol=1e-12, abs_tol=1e-12)
            if not good:
                raise ContractValidationError(f"AST_V2_VECTOR_VALUE_MISMATCH:{vector['vector_id']}")
    if checked_cases != {"OBSERVED", "UNKNOWN_INPUT"}:
        raise ContractValidationError(f"AST_V2_POSITIVE_NEGATIVE_VECTORS_REQUIRED:{contract['contract_id']}")
    return len(contract["independent_vectors"])
