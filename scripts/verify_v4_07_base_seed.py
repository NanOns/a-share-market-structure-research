from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(os.environ.get("V4_07_ACCEPTED_INPUTS_ROOT", str(ROOT))).resolve()
TASK = "V4_06_R2_CONTRACT_REPAIR_AND_V4_07_BASE_SEED_STAGE_TASK_20260929"
MODEL = "BASE_SEED_V1"
PARAMETER_SET_ID = "V4_07_BASE_SEED_PARAMETER_SET_V1"
POSITION_BIAS_PARAMETER_ID = "V4_07_POSITION_BIAS20_ATR_MAX"
DELTA3_IMPROVING_PARAMETER_ID = "V4_07_DELTA3_IMPROVING_MIN_POINTS"
DELTA3_STRONG_PARAMETER_ID = "V4_07_DELTA3_STRONG_MIN_POINTS"


def canon(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canon(value)).hexdigest()


def file_sha(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def checked_path(root: Path, relative: str) -> Path:
    resolved_root = root.resolve()
    path = (resolved_root / relative).resolve()
    if not path.is_relative_to(resolved_root) or not path.is_file():
        raise ValueError(f"missing or unsafe accepted source: {relative}")
    return path


def verify_binding(root: Path, binding: Mapping[str, Any], label: str) -> tuple[Path, str]:
    path = checked_path(root, str(binding["path"]))
    actual = file_sha(path)
    if actual != str(binding["sha256"]).lower():
        raise ValueError(f"{label} SHA-256 mismatch")
    if "byte_count" in binding and path.stat().st_size != int(binding["byte_count"]):
        raise ValueError(f"{label} byte-count mismatch")
    return path, actual


def read_gzip(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def unknown(reason: str) -> dict[str, Any]:
    return {"value": None, "reason": reason or "UPSTREAM_UNKNOWN"}


def known(value: Any) -> dict[str, Any]:
    return {"value": value, "reason": None}


def tri(fact: Mapping[str, Any]) -> str:
    return "TRUE" if fact.get("value") is True else "FALSE" if fact.get("value") is False else "UNKNOWN"


def tri_not(value: str) -> str:
    return {"TRUE": "FALSE", "FALSE": "TRUE", "UNKNOWN": "UNKNOWN"}[value]


def tri_and(values: Sequence[str]) -> str:
    return "FALSE" if "FALSE" in values else "UNKNOWN" if "UNKNOWN" in values else "TRUE"


def tri_or(values: Sequence[str]) -> str:
    return "TRUE" if "TRUE" in values else "UNKNOWN" if "UNKNOWN" in values else "FALSE"


def unknown_reason(item: Any, fallback: str) -> str:
    if not isinstance(item, Mapping):
        return fallback
    return str(item.get("unknown_reason") or item.get("reason") or fallback)


def fact_from_value(item: Any, quality_key: str, value_key: str, field: str, kind: str) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        return unknown(f"MISSING_ACCEPTED_CORE_FIELD:{field}")
    if item.get(quality_key) != "OBSERVED":
        return unknown(unknown_reason(item, f"UPSTREAM_UNKNOWN:{field}"))
    value = item.get(value_key)
    if kind == "boolean" and isinstance(value, bool):
        return known(value)
    if kind == "number" and number(value) is not None:
        return known(number(value))
    if kind == "enum" and isinstance(value, str) and value and value != "UNKNOWN":
        return known(value)
    return unknown(f"INVALID_ACCEPTED_VALUE:{field}")


def fact_from_state(item: Any, field: str, kind: str) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        return unknown(f"MISSING_ACCEPTED_CORE_FIELD:{field}")
    value = item.get("value")
    if value is None or value == "UNKNOWN" or item.get("unknown_reason") is not None:
        return unknown(unknown_reason(item, f"UPSTREAM_UNKNOWN:{field}"))
    if kind == "boolean" and isinstance(value, bool):
        return known(value)
    if kind == "number" and number(value) is not None:
        return known(number(value))
    if kind == "enum" and isinstance(value, str) and value:
        return known(value)
    return unknown(f"INVALID_ACCEPTED_VALUE:{field}")


def core_facts(
    core: Mapping[str, Any], factor: Mapping[str, Any], run_context: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    facts: dict[str, dict[str, Any]] = {"research_universe": known(True)}
    status = core.get("trading_status")
    facts["actual_bar"] = known(True) if status == "ACTUAL_TRADED" else known(False) if status == "SUSPENDED" else unknown(
        f"UPSTREAM_TRADING_STATUS:{status or 'MISSING'}"
    )
    security_id, symbol, board = core.get("security_id"), core.get("symbol"), core.get("board")
    identity_ok = (
        isinstance(security_id, str)
        and re.fullmatch(r"SEC-[0-9A-F]{32}", security_id) is not None
        and isinstance(symbol, str)
        and re.fullmatch(r"(?:SH|SZ)\.[0-9]{6}", symbol) is not None
        and isinstance(board, str)
        and board in run_context["expected_board_counts"]
        and symbol.startswith(("SH.", "SZ."))
        and core.get("trade_date") == run_context["trade_date"]
        and core.get("publication_id") == run_context["profile_row_publication_id"]
        and core.get("historical_as_recorded_claim") is False
    )
    facts["price_identity_READY"] = known(True) if identity_ok else unknown("ACCEPTED_CORE_IDENTITY_BINDING_INVALID")

    derived = core.get("derived_fields", {})
    quality = core.get("primitive_quality", {})
    states = core.get("states", {})
    facts["minimum_liquidity"] = fact_from_value(derived.get("minimum_liquidity"), "quality", "value", "minimum_liquidity", "boolean")
    damage_meta = quality.get("core_price_damage")
    trend_state = states.get("trend_state", {})
    evidence = trend_state.get("evidence", {}) if isinstance(trend_state, Mapping) else {}
    damage = evidence.get("core_price_damage") if isinstance(evidence, Mapping) else None
    facts["core_price_damage"] = (
        known(damage)
        if isinstance(damage_meta, Mapping) and damage_meta.get("quality_state") == "OBSERVED" and isinstance(damage, bool)
        else unknown(unknown_reason(damage_meta, "UPSTREAM_UNKNOWN:core_price_damage"))
    )
    facts["severe_extension"] = fact_from_state(states.get("severe_extension"), "severe_extension", "boolean")
    facts["bias20_atr"] = fact_from_value(derived.get("bias20_atr"), "quality", "value", "bias20_atr", "number")
    facts["compression_state"] = fact_from_state(states.get("compression_state"), "compression_state", "enum")

    factor_delta = factor.get("fields", {}).get("rps5_delta3")
    core_delta = quality.get("rps5_delta3")
    if not isinstance(factor_delta, Mapping) or not isinstance(core_delta, Mapping):
        facts["delta3"] = unknown("MISSING_ACCEPTED_CORE_FIELD:rps5_delta3")
    else:
        shared = (
            "contract_id", "input_digest", "output_digest", "parameter_set_id", "quality_state",
            "unknown_reason", "window_identity", "actual_count", "calendar_span", "suspended_count",
            "window_start_trade_date", "window_end_trade_date",
        )
        facts["delta3"] = (
            unknown("ACCEPTED_FACTOR_PROFILE_BINDING_MISMATCH:rps5_delta3")
            if any(factor_delta.get(key) != core_delta.get(key) for key in shared)
            else fact_from_value(factor_delta, "quality_state", "value", "rps5_delta3", "number")
        )

    facts["ma_structure_state"] = fact_from_state(states.get("ma_structure_state"), "ma_structure_state", "enum")
    trend_evidence = evidence if isinstance(evidence, Mapping) else {}
    for output, source in (("close_t", "close"), ("ma20_t", "ma20")):
        facts[output] = known(number(trend_evidence.get(source))) if number(trend_evidence.get(source)) is not None else unknown(
            f"MISSING_ACCEPTED_CORE_FIELD:{output}"
        )
    facts["close_t_minus_1"] = unknown("ACCEPTED_T_MINUS_1_CORE_FIELD_UNAVAILABLE")
    facts["ma20_t_minus_1"] = unknown("ACCEPTED_T_MINUS_1_CORE_FIELD_UNAVAILABLE")
    facts["core_participation_result"] = fact_from_state(states.get("core_participation_result"), "core_participation_result", "enum")
    return facts


def parameter_values_from_document(parameter_set: Mapping[str, Any]) -> dict[str, float]:
    """Independent verifier resolves thresholds only from the supplied parameter instance."""
    if parameter_set.get("parameter_set_id") != PARAMETER_SET_ID or parameter_set.get("status") != "FROZEN_CANDIDATE":
        raise ValueError("independent verifier received an unsupported parameter instance")
    entries = parameter_set.get("parameters")
    if not isinstance(entries, list):
        raise ValueError("independent verifier parameter list is missing")
    by_id: dict[str, Mapping[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("independent verifier parameter entry is malformed")
        parameter_id = entry.get("parameter_id")
        if not isinstance(parameter_id, str) or parameter_id in by_id:
            raise ValueError("independent verifier parameter IDs are missing or duplicated")
        by_id[parameter_id] = entry
    specifications = {
        POSITION_BIAS_PARAMETER_ID: "STRICT_LT",
        DELTA3_IMPROVING_PARAMETER_ID: "GTE",
        DELTA3_STRONG_PARAMETER_ID: "GTE",
    }
    values: dict[str, float] = {}
    for parameter_id, comparison in specifications.items():
        entry = by_id.get(parameter_id)
        if not isinstance(entry, Mapping) or entry.get("status") != "FROZEN_CANDIDATE" or entry.get("comparison") != comparison:
            raise ValueError(f"independent verifier parameter binding mismatch: {parameter_id}")
        value = entry.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"independent verifier parameter value is invalid: {parameter_id}")
        values[parameter_id] = float(value)
    return values


def independent_eval(
    facts: Mapping[str, Mapping[str, Any]], parameters: Mapping[str, float]
) -> dict[str, Any]:
    safety = tri_and((
        tri(facts["research_universe"]), tri(facts["actual_bar"]), tri(facts["price_identity_READY"]),
        tri(facts["minimum_liquidity"]), tri_not(tri(facts["core_price_damage"])),
        tri_not(tri(facts["severe_extension"])),
    ))
    bias_value = number(facts["bias20_atr"].get("value"))
    bias = "UNKNOWN" if bias_value is None else "TRUE" if bias_value < parameters[POSITION_BIAS_PARAMETER_ID] else "FALSE"
    compression = facts["compression_state"].get("value")
    structure = "UNKNOWN" if compression is None else "TRUE" if compression in {"COMPRESSING", "COMPRESSING_STRONG"} else "FALSE"
    delta = number(facts["delta3"].get("value"))
    improving = "UNKNOWN" if delta is None else "TRUE" if delta >= parameters[DELTA3_IMPROVING_PARAMETER_ID] else "FALSE"
    strong = "UNKNOWN" if delta is None else "TRUE" if delta >= parameters[DELTA3_STRONG_PARAMETER_ID] else "FALSE"
    ma_state = facts["ma_structure_state"].get("value")
    bull = "UNKNOWN" if ma_state is None else "TRUE" if ma_state == "BULL_TRANSITION" else "FALSE"
    previous_close = number(facts["close_t_minus_1"].get("value"))
    previous_ma20 = number(facts["ma20_t_minus_1"].get("value"))
    current_close = number(facts["close_t"].get("value"))
    current_ma20 = number(facts["ma20_t"].get("value"))
    before = "UNKNOWN" if previous_close is None or previous_ma20 is None else "TRUE" if previous_close <= previous_ma20 else "FALSE"
    now = "UNKNOWN" if current_close is None or current_ma20 is None else "TRUE" if current_close > current_ma20 else "FALSE"
    transition = tri_or((bull, tri_and((before, now))))
    s1 = tri_and((bias, structure, improving))
    s2 = tri_and((bias, strong, transition))
    paths = tri_or((s1, s2))
    base = tri_and((safety, paths))
    domains = {
        "research_universe": tri(facts["research_universe"]),
        "actual_bar": tri(facts["actual_bar"]),
        "price_identity_READY": tri(facts["price_identity_READY"]),
        "minimum_liquidity": tri(facts["minimum_liquidity"]),
        "core_price_damage": tri(facts["core_price_damage"]),
        "severe_extension": tri(facts["severe_extension"]),
        "safety": safety,
        "position_ok": bias,
        "structure_improving": structure,
        "relative_change_improving": improving,
        "relative_change_strong": strong,
        "trend_transition_early": transition,
        "S1": s1,
        "S2": s2,
        "seed_paths": paths,
        "base_seed_state": base,
    }
    participation = facts["core_participation_result"].get("value")
    annotation = {
        "HIGH_PARTICIPATION_EFFECTIVE_ADVANCE": "SUPPORTED",
        "HIGH_PARTICIPATION_REVERSAL": "CONFLICTING",
        "HIGH_PARTICIPATION_LOW_EFFICIENCY": "CONFLICTING",
        "LOW_PARTICIPATION_ADVANCE": "NEUTRAL",
        "LOW_PARTICIPATION_DECLINE": "NEUTRAL",
        "NORMAL_PARTICIPATION": "NEUTRAL",
    }.get(participation, "UNKNOWN")
    relevant = {
        "research_universe", "actual_bar", "price_identity_READY", "minimum_liquidity",
        "core_price_damage", "severe_extension", "bias20_atr", "compression_state", "delta3",
        "ma_structure_state", "core_participation_result",
    }
    if transition == "UNKNOWN":
        relevant.update(("close_t_minus_1", "ma20_t_minus_1", "close_t", "ma20_t"))
    waiting = [
        {"field_id": field, "reason": str(facts[field].get("reason") or "UPSTREAM_UNKNOWN")}
        for field in sorted(relevant) if facts[field].get("value") is None
    ]
    invalid: list[dict[str, str]] = []
    if base != "TRUE":
        for field in ("research_universe", "actual_bar", "price_identity_READY", "minimum_liquidity"):
            if domains[field] == "FALSE":
                invalid.append({"predicate": field, "state": "FALSE"})
        for field in ("core_price_damage", "severe_extension"):
            if domains[field] == "TRUE":
                invalid.append({"predicate": f"NOT_{field}", "state": "FALSE"})
        if safety != "FALSE":
            for path, state in (("S1", s1), ("S2", s2)):
                if state == "FALSE":
                    invalid.append({"predicate": path, "state": "FALSE"})
    invalid.sort(key=lambda item: item["predicate"])
    codes = sorted({f"UNKNOWN_INPUT:{item['field_id']}:{item['reason']}" for item in waiting})
    return {
        "base_seed_state": base,
        "matched_seed_paths": [path for path, state in (("S1", s1), ("S2", s2)) if state == "TRUE"],
        "domain_states": domains,
        "waiting_for": waiting,
        "invalid_if": invalid,
        "quality": "COMPLETE" if not waiting else "PARTIAL_UNKNOWN",
        "quality_codes": codes,
        "seed_participation_annotation": annotation,
    }


def input_digest(core: Mapping[str, Any], facts: Mapping[str, Mapping[str, Any]], bindings: Mapping[str, Any]) -> str:
    return digest({
        "source_bindings": dict(bindings),
        "identity": {
            "trade_date": core.get("trade_date"),
            "security_id": core.get("security_id"),
            "symbol": core.get("symbol"),
            "board": core.get("board"),
        },
        "accepted_facts": facts,
    })


def row_fact_digest(row: Mapping[str, Any]) -> str:
    return digest({key: value for key, value in row.items() if key not in {"fact_digest", "created_at"}})


def logical_digest(rows: Sequence[Mapping[str, Any]], bindings: Mapping[str, Any]) -> str:
    logical_rows = [{key: value for key, value in row.items() if key != "created_at"} for row in rows]
    logical_rows.sort(key=lambda row: (row["trade_date"], row["security_id"]))
    return digest({
        "contract_id": bindings["model_contract_id"],
        "contract_sha256": bindings["contract_sha256"],
        "parameter_set_id": bindings["parameter_set_id"],
        "parameter_set_sha256": bindings["parameter_set_sha256"],
        "accepted_source_bindings": dict(bindings),
        "rows": logical_rows,
    })


def load_accepted_context() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    stage = read_json(checked_path(SOURCE_ROOT, "data/v4/V4_STAGE_ACCEPTED_HEAD.json"))
    head_path = checked_path(SOURCE_ROOT, "data/v4/V4_05_ACCEPTED_HEAD.json")
    head = read_json(head_path)
    if stage.get("v4_05_external_acceptance") != "EXTERNALLY_ACCEPTED":
        raise ValueError("global stage head does not accept V4-05")
    pointer = stage.get("v4_05_binding")
    if not isinstance(pointer, Mapping):
        raise ValueError("global stage head has no V4-05 binding")
    pointed_path, _ = verify_binding(SOURCE_ROOT, pointer, "global V4-05 head")
    if pointed_path != head_path:
        raise ValueError("global stage head points to another V4-05 head")
    if head.get("stage") != "V4-05" or head.get("external_acceptance") != "EXTERNALLY_ACCEPTED":
        raise ValueError("V4-05 accepted head is not externally accepted")
    trade_date = head.get("target_trade_date")
    expected_count = head.get("target_identity_count")
    core_digest = head.get("accepted_artifact", {}).get("logical_digest")
    if not isinstance(trade_date, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", trade_date) is None:
        raise ValueError("accepted target trade date is invalid")
    if isinstance(expected_count, bool) or not isinstance(expected_count, int) or expected_count <= 0:
        raise ValueError("accepted target identity count is invalid")
    if not isinstance(core_digest, str) or re.fullmatch(r"[0-9a-f]{64}", core_digest) is None:
        raise ValueError("accepted Core logical digest is invalid")

    exact_path, exact_sha = verify_binding(SOURCE_ROOT, head["evidence_bindings"]["exact_candidate_ledger_binding"], "exact candidate ledger")
    exact = read_json(exact_path)
    if exact.get("status") != "PASS" or exact.get("all_exact_bindings_match") is not True or exact.get("old_r4_binding_count") != 0:
        raise ValueError("accepted exact-candidate ledger gate failed")
    publication_id = exact.get("actual_postgresql", {}).get("publication_head", {}).get("publication_id")
    if not isinstance(publication_id, str) or not publication_id:
        raise ValueError("accepted publication identity is missing")

    core_path, core_sha = verify_binding(SOURCE_ROOT, head["accepted_artifact"], "accepted Core Profile")
    factor_path, factor_sha = verify_binding(SOURCE_ROOT, head["accepted_artifacts"]["full_scope_factors"], "accepted Full Scope Factors")
    core_receipt_path, core_receipt_sha = verify_binding(SOURCE_ROOT, head["evidence_bindings"]["r4_1_core_profile_receipt"], "Core Profile receipt")
    factor_receipt_path, factor_receipt_sha = verify_binding(SOURCE_ROOT, head["evidence_bindings"]["r4_1_full_scope_factors_receipt"], "Full Scope Factors receipt")
    core_receipt = read_json(core_receipt_path)
    factor_receipt = read_json(factor_receipt_path)
    if core_receipt.get("logical_digest") != core_digest or core_receipt.get("row_count") != expected_count:
        raise ValueError("Core Profile receipt does not bind the accepted run context")
    if core_receipt.get("artifact_sha256") != core_sha:
        raise ValueError("Core Profile artifact/receipt binding mismatch")
    if factor_receipt.get("logical_digest") != head["accepted_artifacts"]["full_scope_factors"].get("logical_digest"):
        raise ValueError("Full Scope Factors receipt logical digest mismatch")
    if factor_receipt.get("artifact_sha256") != factor_sha:
        raise ValueError("Full Scope Factors artifact/receipt binding mismatch")

    contract_path = ROOT / "config/v4_07_base_seed_contract_v1.json"
    parameter_path = ROOT / "config/v4_07_parameter_set_v1.json"
    contract = read_json(contract_path)
    parameter_set = read_json(parameter_path)
    freeze = read_json(ROOT / "reports/v4_07/V4_07_CONTRACT_FREEZE_RECEIPT.json")
    for relative, expected_sha in freeze["config_sha256"].items():
        if file_sha(ROOT / relative) != expected_sha:
            raise ValueError(f"frozen V4-07 package changed: {relative}")
    if freeze.get("status") != "PASS_CONTRACT_FREEZE_CANDIDATE" or contract.get("status") != "FROZEN_CANDIDATE":
        raise ValueError("V4-07 frozen package receipt failed")
    if contract.get("contract_id") != MODEL:
        raise ValueError("unsupported V4-07 model contract")
    if contract.get("rule_ast", {}).get("position_ok", {}).get("right_parameter") != POSITION_BIAS_PARAMETER_ID:
        raise ValueError("independent verifier found position parameter AST mismatch")
    if contract.get("rule_ast", {}).get("relative_change_improving", {}).get("right_parameter") != DELTA3_IMPROVING_PARAMETER_ID:
        raise ValueError("independent verifier found improving parameter AST mismatch")
    if contract.get("rule_ast", {}).get("relative_change_strong", {}).get("right_parameter") != DELTA3_STRONG_PARAMETER_ID:
        raise ValueError("independent verifier found strong parameter AST mismatch")
    parameter_values_from_document(parameter_set)
    contract_sha, parameter_sha = file_sha(contract_path), file_sha(parameter_path)

    core_rows = read_gzip(core_path)
    factor_rows = read_gzip(factor_path)
    if len(core_rows) != expected_count or len(factor_rows) != expected_count:
        raise ValueError("accepted artifact row count differs from accepted-head context")
    profile_ids = {row.get("publication_id") for row in core_rows}
    if len(profile_ids) != 1 or not all(isinstance(value, str) and value for value in profile_ids):
        raise ValueError("accepted Core row publication identity is missing or mixed")
    profile_publication_id = next(iter(profile_ids))
    boards = Counter(str(row.get("board")) for row in core_rows)
    if any(board in {"None", ""} for board in boards) or sum(boards.values()) != expected_count:
        raise ValueError("accepted Core board scope is invalid")
    if any(row.get("trade_date") != trade_date for row in core_rows + factor_rows):
        raise ValueError("accepted artifacts contain rows outside their accepted date")
    bindings = {
        "publication_id": publication_id,
        "profile_row_publication_id": profile_publication_id,
        "trade_date": trade_date,
        "core_logical_digest": core_digest,
        "core_profile_artifact_sha256": core_sha,
        "core_profile_receipt_sha256": core_receipt_sha,
        "full_scope_factors_logical_digest": head["accepted_artifacts"]["full_scope_factors"]["logical_digest"],
        "full_scope_factors_artifact_sha256": factor_sha,
        "full_scope_factors_receipt_sha256": factor_receipt_sha,
        "exact_ledger_binding_sha256": exact_sha,
        "model_contract_id": MODEL,
        "parameter_set_id": PARAMETER_SET_ID,
        "contract_sha256": contract_sha,
        "parameter_set_sha256": parameter_sha,
        "accepted_identity_count": expected_count,
        "expected_board_counts": dict(sorted(boards.items())),
    }
    context = {
        "source_bindings": bindings,
        "trade_date": trade_date,
        "publication_id": publication_id,
        "profile_row_publication_id": profile_publication_id,
        "core_logical_digest": core_digest,
        "expected_identity_count": expected_count,
        "expected_board_counts": dict(sorted(boards.items())),
        "parameter_set": parameter_set,
        "parameter_values": parameter_values_from_document(parameter_set),
    }
    return context, core_rows, factor_rows


def main() -> int:
    context, core_rows, factor_rows = load_accepted_context()
    bindings = context["source_bindings"]
    core_by_id: dict[str, Mapping[str, Any]] = {}
    factor_by_id: dict[str, Mapping[str, Any]] = {}
    for row in core_rows:
        security_id = row.get("security_id")
        if not isinstance(security_id, str) or security_id in core_by_id:
            raise ValueError("accepted Core identities are missing or duplicated")
        core_by_id[security_id] = row
    for row in factor_rows:
        security_id = row.get("security_id")
        if not isinstance(security_id, str) or security_id in factor_by_id:
            raise ValueError("accepted factor identities are missing or duplicated")
        factor_by_id[security_id] = row
    if set(core_by_id) != set(factor_by_id):
        raise ValueError("accepted factor/Core identity sets differ")
    board_counts = Counter(str(row["board"]) for row in core_rows)
    if dict(sorted(board_counts.items())) != context["expected_board_counts"]:
        raise ValueError("accepted Core board counts differ from the loaded context")

    candidate_path = ROOT / "reports/v4_07/staging/V4_07_BASE_SEED_CANDIDATE_R2.jsonl.gz"
    candidate = read_gzip(candidate_path)
    if len(candidate) != context["expected_identity_count"]:
        raise ValueError("candidate row count differs from accepted context")
    candidate_by_id = {row.get("security_id"): row for row in candidate}
    if len(candidate_by_id) != len(candidate) or set(candidate_by_id) != set(core_by_id):
        raise ValueError("candidate identities differ from accepted Core scope")

    mismatches: list[dict[str, Any]] = []
    expected_rows: list[dict[str, Any]] = []
    expected_states: Counter[str] = Counter()
    states_by_board: Counter[tuple[str, str]] = Counter()
    unknowns: Counter[tuple[str, str, str]] = Counter()
    annotations: Counter[str] = Counter()
    forbidden_terms = ("turnover", "baostock", "supplemental_extension_note", "binding_quality", "prewatch", "radar", "focus", "anchor", "forward")
    for security_id in sorted(core_by_id):
        core, factor, actual = core_by_id[security_id], factor_by_id[security_id], candidate_by_id[security_id]
        if factor.get("trade_date") != context["trade_date"] or factor.get("board_scope") != core.get("board") or factor.get("coordinate_basis") != core.get("coordinate_basis"):
            raise ValueError(f"accepted factor/Core row binding mismatch for {security_id}")
        facts = core_facts(core, factor, context)
        calculated = independent_eval(facts, context["parameter_values"])
        expected = {
            "publication_id": context["publication_id"],
            "source_publication_id": core["publication_id"],
            "trade_date": context["trade_date"],
            "security_id": security_id,
            "base_seed_state": calculated["base_seed_state"],
            "matched_seed_paths": calculated["matched_seed_paths"],
            "domain_states": calculated["domain_states"],
            "waiting_for": calculated["waiting_for"],
            "invalid_if": calculated["invalid_if"],
            "quality": calculated["quality"],
            "quality_codes": calculated["quality_codes"],
            "seed_participation_annotation": calculated["seed_participation_annotation"],
            "model_contract_id": bindings["model_contract_id"],
            "parameter_set_id": bindings["parameter_set_id"],
            "source_core_logical_digest": context["core_logical_digest"],
            "input_digest": input_digest(core, facts, bindings),
            "created_at": actual.get("created_at"),
        }
        expected["fact_digest"] = row_fact_digest(expected)
        differences = {
            key: (actual.get(key), expected.get(key))
            for key in expected
            if actual.get(key) != expected.get(key)
        }
        if differences:
            mismatches.append({"security_id": security_id, "fields": differences})
        if any(any(term in key.lower() for term in forbidden_terms) for key in actual):
            mismatches.append({"security_id": security_id, "fields": {"forbidden_output_key": True}})
        expected_rows.append(expected)
        expected_states[expected["base_seed_state"]] += 1
        states_by_board[(str(core["board"]), expected["base_seed_state"])] += 1
        annotations[expected["seed_participation_annotation"]] += 1
        if expected["base_seed_state"] == "UNKNOWN":
            for item in expected["waiting_for"]:
                unknowns[(str(core["board"]), item["field_id"], item["reason"])] += 1
    if mismatches:
        raise AssertionError(json.dumps(mismatches[:3], ensure_ascii=False))

    expected_rows.sort(key=lambda row: (row["trade_date"], row["security_id"]))
    logical = logical_digest(expected_rows, bindings)
    receipt = read_json(ROOT / "reports/v4_07/V4_07_R2_FULL_MARKET_CANDIDATE_RECEIPT.json")
    candidate_sha = file_sha(candidate_path)
    if candidate_sha != receipt.get("artifact_sha256"):
        raise AssertionError("R2 candidate artifact SHA-256 differs from its receipt")
    if receipt.get("source_bindings") != bindings or receipt.get("logical_artifact_digest") != logical:
        raise AssertionError("R2 candidate receipt source bindings or logical digest mismatch")
    state_counts = Counter(row["base_seed_state"] for row in candidate)
    if sum(state_counts.values()) != context["expected_identity_count"] or receipt.get("row_count") != context["expected_identity_count"]:
        raise AssertionError("R2 candidate state counts do not reconcile to accepted context")
    if any(not row.get("created_at", "").endswith("Z") for row in candidate):
        raise AssertionError("candidate row is missing an auditable UTC timestamp")

    evidence = {
        "contract_id": "V4_07_R2_INDEPENDENT_POSTCHECK_V1",
        "stage_contract": TASK,
        "status": "PASS_INDEPENDENT_SOURCE_RECOMPUTE",
        "oracle": "accepted V4-05 Core Profile + accepted V4-05 Full Scope Factors + frozen BASE_SEED_V1 contract and parameter instance",
        "accepted_inputs_root": str(SOURCE_ROOT),
        "independent_implementation": "scripts/verify_v4_07_base_seed.py (does not import src.v4.base_seed)",
        "parameter_source": "config/v4_07_parameter_set_v1.json, verified against frozen contract receipt",
        "parameter_set_sha256": bindings["parameter_set_sha256"],
        "contract_sha256": bindings["contract_sha256"],
        "checked_rows": len(expected_rows),
        "mismatch_count": 0,
        "target_trade_date": context["trade_date"],
        "publication_id": context["publication_id"],
        "accepted_core_logical_digest": context["core_logical_digest"],
        "candidate_logical_digest": logical,
        "expected_state_counts": dict(sorted(expected_states.items())),
        "state_counts_by_board": {
            board: dict(sorted({state: count for (item_board, state), count in states_by_board.items() if item_board == board}.items()))
            for board in sorted(context["expected_board_counts"])
        },
        "participation_annotation_counts": dict(sorted(annotations.items())),
        "accepted_delta3_unknown_count": sum(1 for row in core_rows if row.get("primitive_quality", {}).get("rps5_delta3", {}).get("quality_state") != "OBSERVED"),
        "accepted_t_minus_1_core_fields": "ABSENT; reclaim branch remains UNKNOWN where required",
        "source_bindings": bindings,
        "candidate_artifact_sha256": candidate_sha,
        "created_at_excluded_from_comparison": True,
        "next_stage": "V4_07_R2_EXTERNAL_INDEPENDENT_ACCEPTANCE",
    }
    output = ROOT / "reports/v4_07/V4_07_R2_INDEPENDENT_POSTCHECK.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=output.name + ".", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(json.dumps({
        "status": evidence["status"],
        "checked_rows": len(expected_rows),
        "mismatch_count": 0,
        "logical_digest": logical,
        "state_counts": dict(expected_states),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
