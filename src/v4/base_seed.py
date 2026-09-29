from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping, Sequence

CONTRACT_ID = "BASE_SEED_V1"
CONTRACT_VERSION = "1.0.0"
PARAMETER_SET_ID = "V4_07_BASE_SEED_PARAMETER_SET_V1"
TRADE_DATE = "2026-09-28"
FORMAL_PUBLICATION_ID = "PUB-3c03e227-c60a-4d8c-86ae-2861507c257b"
PROFILE_ROW_PUBLICATION_ID = "V4_05_R4_T0_CURRENT_COORDINATE"
CORE_LOGICAL_DIGEST = "d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74"
EXPECTED_BOARD_COUNTS = {"SH_MAIN": 1702, "SZ_MAIN": 1494, "CHINEXT": 1408, "STAR": 618}


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_path(root: Path, relative: str) -> Path:
    root = root.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"accepted input path is missing or escapes repository: {relative}")
    return path


def _verify_file_binding(root: Path, binding: Mapping[str, Any], label: str) -> tuple[Path, str]:
    path = _repo_path(root, str(binding["path"]))
    actual = sha256_file(path)
    expected = str(binding["sha256"]).lower()
    if actual != expected:
        raise ValueError(f"accepted input SHA-256 mismatch for {label}: {actual} != {expected}")
    if "byte_count" in binding and path.stat().st_size != int(binding["byte_count"]):
        raise ValueError(f"accepted input byte count mismatch for {label}")
    return path, actual


def _validate_frozen_package(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    contract_path = root / "config/v4_07_base_seed_contract_v1.json"
    params_path = root / "config/v4_07_parameter_set_v1.json"
    fields_path = root / "config/v4_07_field_registry_v1.json"
    vectors_path = root / "config/v4_07_machine_vectors_v1.json"
    receipt_path = root / "reports/v4_07/V4_07_CONTRACT_FREEZE_RECEIPT.json"
    contract, params, fields, vectors, receipt = map(_read_json, (contract_path, params_path, fields_path, vectors_path, receipt_path))
    if receipt.get("status") != "PASS_CONTRACT_FREEZE_CANDIDATE":
        raise ValueError("BASE_SEED_V1 contract freeze receipt is not PASS")
    if receipt.get("starting_head") != "0f13e1b55d86ee74dfc489a48e95a766111a617a":
        raise ValueError("contract freeze receipt starting HEAD mismatch")
    if contract.get("contract_id") != CONTRACT_ID or contract.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("unsupported BASE_SEED contract identity")
    if contract.get("status") != "FROZEN_CANDIDATE" or params.get("status") != "FROZEN_CANDIDATE":
        raise ValueError("BASE_SEED_V1 package is not frozen")
    if params.get("parameter_set_id") != PARAMETER_SET_ID or fields.get("source_contract_id") != CONTRACT_ID:
        raise ValueError("BASE_SEED_V1 package identity mismatch")
    frozen = receipt.get("config_sha256", {})
    for path in (contract_path, params_path, fields_path, vectors_path):
        relative = path.relative_to(root).as_posix()
        if sha256_file(path) != frozen.get(relative):
            raise ValueError(f"frozen contract package changed after freeze: {relative}")
    return contract, params, fields, receipt


def _load_accepted_source_context(
    root: Path, accepted_inputs_root: Path | None = None
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    root = root.resolve()
    source_root = (accepted_inputs_root or root).resolve()
    contract, _params, _fields, freeze = _validate_frozen_package(root)
    stage_head = _read_json(_repo_path(source_root, "data/v4/V4_STAGE_ACCEPTED_HEAD.json"))
    accepted_head = _read_json(_repo_path(source_root, "data/v4/V4_05_ACCEPTED_HEAD.json"))
    if stage_head.get("accepted_stage_range") != "V4_00_TO_V4_05_ACCEPTED":
        raise ValueError("global accepted range moved from the V4-05 boundary")
    if stage_head.get("v4_05_external_acceptance") != "EXTERNALLY_ACCEPTED":
        raise ValueError("V4-05 is not externally accepted")
    if accepted_head.get("external_acceptance_decision") != "V4_05_EXTERNAL_ACCEPTANCE_PASS_R4_2":
        raise ValueError("unexpected V4-05 accepted head")
    if accepted_head.get("accepted_artifact", {}).get("logical_digest") != CORE_LOGICAL_DIGEST:
        raise ValueError("accepted Core logical digest mismatch")
    if accepted_head.get("target_trade_date") != TRADE_DATE or accepted_head.get("target_identity_count") != 5222:
        raise ValueError("accepted V4-05 target scope mismatch")

    bindings = accepted_head.get("evidence_bindings", {})
    ledger_binding = bindings.get("exact_candidate_ledger_binding")
    if not ledger_binding:
        raise ValueError("V4-05 exact ledger binding is absent")
    ledger_path, ledger_sha = _verify_file_binding(source_root, ledger_binding, "V4-05 exact candidate ledger")
    ledger = _read_json(ledger_path)
    if ledger.get("status") != "PASS" or ledger.get("all_exact_bindings_match") is not True or ledger.get("old_r4_binding_count") != 0:
        raise ValueError("V4-05 exact ledger acceptance gate failed")
    formal_publication_id = ledger.get("actual_postgresql", {}).get("publication_head", {}).get("publication_id")
    if formal_publication_id != FORMAL_PUBLICATION_ID:
        raise ValueError("accepted V4-05 publication identity mismatch")

    core_binding = accepted_head.get("accepted_artifact", {})
    factors_binding = accepted_head.get("accepted_artifacts", {}).get("full_scope_factors", {})
    core_path, core_sha = _verify_file_binding(source_root, core_binding, "accepted Core Profile")
    factors_path, factors_sha = _verify_file_binding(source_root, factors_binding, "accepted Full Scope Factors")
    if core_sha != "9a6ebedc715bc4b310ecf76c77e01cb6dfe9dadc17d335b5fc9afbcc2f6f3fa0":
        raise ValueError("accepted Core Profile artifact identity is not the frozen R4.1 input")
    if factors_sha != "17ae571629b76399e32d9e8a243268ea1fac619e1c5168d307bfd8ebf1494c48":
        raise ValueError("accepted Full Scope Factors artifact identity mismatch")
    if factors_binding.get("logical_digest") != "0cfe708567935726f0ad51ae4bb47237ec7aee556db3437c12f21f0c623bd0d2":
        raise ValueError("accepted Full Scope Factors logical digest mismatch")

    # Receipts named by the Accepted Head independently bind candidate file scope and logical identity.
    core_receipt_binding = bindings.get("r4_1_core_profile_receipt")
    factor_receipt_binding = bindings.get("r4_1_full_scope_factors_receipt")
    if not core_receipt_binding or not factor_receipt_binding:
        raise ValueError("accepted V4-05 profile/factor receipts are missing")
    core_receipt_path, core_receipt_sha = _verify_file_binding(source_root, core_receipt_binding, "Core Profile receipt")
    factor_receipt_path, factor_receipt_sha = _verify_file_binding(source_root, factor_receipt_binding, "Full Scope Factors receipt")
    core_receipt = _read_json(core_receipt_path)
    factor_receipt = _read_json(factor_receipt_path)
    if core_receipt.get("logical_digest") != CORE_LOGICAL_DIGEST or core_receipt.get("row_count") != 5222:
        raise ValueError("accepted Core Profile receipt does not bind the target digest/scope")
    if core_receipt.get("artifact_sha256") != core_sha:
        raise ValueError("Core Profile receipt/artifact binding mismatch")
    if factor_receipt.get("logical_digest") != factors_binding.get("logical_digest"):
        raise ValueError("Full Scope Factors receipt does not bind accepted artifact")
    if factor_receipt.get("artifact_sha256") != factors_sha:
        raise ValueError("Full Scope Factors receipt/artifact binding mismatch")

    source_bindings = {
        "publication_id": formal_publication_id,
        "profile_row_publication_id": PROFILE_ROW_PUBLICATION_ID,
        "trade_date": TRADE_DATE,
        "core_logical_digest": CORE_LOGICAL_DIGEST,
        "core_profile_artifact_sha256": core_sha,
        "core_profile_receipt_sha256": core_receipt_sha,
        "full_scope_factors_logical_digest": factors_binding["logical_digest"],
        "full_scope_factors_artifact_sha256": factors_sha,
        "full_scope_factors_receipt_sha256": factor_receipt_sha,
        "exact_ledger_binding_sha256": ledger_sha,
        "model_contract_id": contract["contract_id"],
        "parameter_set_id": PARAMETER_SET_ID,
    }
    frozen_sources = freeze.get("source_bindings", {})
    if frozen_sources.get("core_profile", {}).get("sha256") != core_sha or frozen_sources.get("full_scope_factors", {}).get("sha256") != factors_sha:
        raise ValueError("accepted data source identity differs from contract freeze receipt")

    with gzip.open(core_path, "rt", encoding="utf-8") as stream:
        core_rows = [json.loads(line) for line in stream if line.strip()]
    with gzip.open(factors_path, "rt", encoding="utf-8") as stream:
        factor_rows = [json.loads(line) for line in stream if line.strip()]
    if len(core_rows) != 5222 or len(factor_rows) != 5222:
        raise ValueError("accepted V4-05 input row count mismatch")
    return source_bindings, core_rows, factor_rows


def _unknown(reason: str) -> dict[str, Any]:
    return {"value": None, "reason": reason or "UPSTREAM_UNKNOWN"}


def _known(value: Any) -> dict[str, Any]:
    return {"value": value, "reason": None}


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _unknown_reason(item: Mapping[str, Any] | None, fallback: str) -> str:
    if not isinstance(item, Mapping):
        return fallback
    return str(item.get("unknown_reason") or item.get("reason") or fallback)


def _observed_value(item: Any, quality_key: str, value_key: str, field_id: str, expected_type: str) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        return _unknown(f"MISSING_ACCEPTED_CORE_FIELD:{field_id}")
    if item.get(quality_key) != "OBSERVED":
        return _unknown(_unknown_reason(item, f"UPSTREAM_UNKNOWN:{field_id}"))
    value = item.get(value_key)
    if expected_type == "boolean":
        if isinstance(value, bool):
            return _known(value)
    elif expected_type == "number":
        number = _number(value)
        if number is not None:
            return _known(number)
    elif expected_type == "enum":
        if isinstance(value, str) and value and value != "UNKNOWN":
            return _known(value)
    return _unknown(f"INVALID_ACCEPTED_VALUE:{field_id}")


def _state_value(item: Any, field_id: str, expected_type: str) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        return _unknown(f"MISSING_ACCEPTED_CORE_FIELD:{field_id}")
    value = item.get("value")
    if value == "UNKNOWN" or item.get("unknown_reason") is not None or value is None:
        return _unknown(_unknown_reason(item, f"UPSTREAM_UNKNOWN:{field_id}"))
    if expected_type == "boolean" and isinstance(value, bool):
        return _known(value)
    if expected_type == "number":
        number = _number(value)
        if number is not None:
            return _known(number)
    if expected_type == "enum" and isinstance(value, str) and value:
        return _known(value)
    return _unknown(f"INVALID_ACCEPTED_VALUE:{field_id}")


def _identity_fact(row: Mapping[str, Any]) -> dict[str, Any]:
    security_id = row.get("security_id")
    symbol = row.get("symbol")
    board = row.get("board")
    row_valid = (
        isinstance(security_id, str)
        and re.fullmatch(r"SEC-[0-9A-F]{32}", security_id) is not None
        and isinstance(symbol, str)
        and re.fullmatch(r"(?:SH|SZ)\.[0-9]{6}", symbol) is not None
        and isinstance(board, str)
        and board in EXPECTED_BOARD_COUNTS
        and ((board in {"SH_MAIN", "STAR"} and symbol.startswith("SH."))
             or (board in {"SZ_MAIN", "CHINEXT"} and symbol.startswith("SZ.")))
        and row.get("trade_date") == TRADE_DATE
        and row.get("publication_id") == PROFILE_ROW_PUBLICATION_ID
        and row.get("historical_as_recorded_claim") is False
    )
    return _known(True) if row_valid else _unknown("ACCEPTED_CORE_IDENTITY_BINDING_INVALID")


def _normalize_facts(core: Mapping[str, Any], factor: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    facts: dict[str, dict[str, Any]] = {}
    facts["research_universe"] = _known(True)  # Membership is the validated row in the exact accepted full-scope profile.
    status = core.get("trading_status")
    if status == "ACTUAL_TRADED":
        facts["actual_bar"] = _known(True)
    elif status == "SUSPENDED":
        facts["actual_bar"] = _known(False)
    else:
        facts["actual_bar"] = _unknown(f"UPSTREAM_TRADING_STATUS:{status or 'MISSING'}")
    facts["price_identity_READY"] = _identity_fact(core)

    derived = core.get("derived_fields", {})
    primitive_quality = core.get("primitive_quality", {})
    states = core.get("states", {})
    facts["minimum_liquidity"] = _observed_value(derived.get("minimum_liquidity"), "quality", "value", "minimum_liquidity", "boolean")
    damage_meta = primitive_quality.get("core_price_damage")
    trend_evidence = states.get("trend_state", {}).get("evidence", {}) if isinstance(states.get("trend_state"), Mapping) else {}
    damage_value = trend_evidence.get("core_price_damage")
    if isinstance(damage_meta, Mapping) and damage_meta.get("quality_state") == "OBSERVED" and isinstance(damage_value, bool):
        facts["core_price_damage"] = _known(damage_value)
    else:
        facts["core_price_damage"] = _unknown(_unknown_reason(damage_meta, "UPSTREAM_UNKNOWN:core_price_damage"))
    facts["severe_extension"] = _state_value(states.get("severe_extension"), "severe_extension", "boolean")
    facts["bias20_atr"] = _observed_value(derived.get("bias20_atr"), "quality", "value", "bias20_atr", "number")
    facts["compression_state"] = _state_value(states.get("compression_state"), "compression_state", "enum")

    factor_delta = factor.get("fields", {}).get("rps5_delta3")
    core_delta_meta = primitive_quality.get("rps5_delta3")
    if not isinstance(factor_delta, Mapping) or not isinstance(core_delta_meta, Mapping):
        facts["delta3"] = _unknown("MISSING_ACCEPTED_CORE_FIELD:rps5_delta3")
    else:
        shared = ("contract_id", "input_digest", "output_digest", "parameter_set_id", "quality_state", "unknown_reason", "window_identity", "actual_count", "calendar_span", "suspended_count", "window_start_trade_date", "window_end_trade_date")
        if any(factor_delta.get(key) != core_delta_meta.get(key) for key in shared):
            facts["delta3"] = _unknown("ACCEPTED_FACTOR_PROFILE_BINDING_MISMATCH:rps5_delta3")
        else:
            facts["delta3"] = _observed_value(factor_delta, "quality_state", "value", "rps5_delta3", "number")

    facts["ma_structure_state"] = _state_value(states.get("ma_structure_state"), "ma_structure_state", "enum")
    if isinstance(trend_evidence, Mapping):
        for field, source in (("close_t", "close"), ("ma20_t", "ma20")):
            number = _number(trend_evidence.get(source))
            facts[field] = _known(number) if number is not None else _unknown(f"MISSING_ACCEPTED_CORE_FIELD:{field}")
    else:
        facts["close_t"] = _unknown("MISSING_ACCEPTED_CORE_FIELD:close_t")
        facts["ma20_t"] = _unknown("MISSING_ACCEPTED_CORE_FIELD:ma20_t")
    # R4.1 Core Profile has no accepted t-1 close/MA20 fields. Do not rebuild them from raw bars.
    facts["close_t_minus_1"] = _unknown("ACCEPTED_T_MINUS_1_CORE_FIELD_UNAVAILABLE")
    facts["ma20_t_minus_1"] = _unknown("ACCEPTED_T_MINUS_1_CORE_FIELD_UNAVAILABLE")
    facts["core_participation_result"] = _state_value(states.get("core_participation_result"), "core_participation_result", "enum")
    return facts


def _tri(fact: Mapping[str, Any]) -> str:
    value = fact.get("value")
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    return "UNKNOWN"


def _tri_not(value: str) -> str:
    return {"TRUE": "FALSE", "FALSE": "TRUE", "UNKNOWN": "UNKNOWN"}[value]


def _tri_and(values: Iterable[str]) -> str:
    values = tuple(values)
    if "FALSE" in values:
        return "FALSE"
    if "UNKNOWN" in values:
        return "UNKNOWN"
    return "TRUE"


def _tri_or(values: Iterable[str]) -> str:
    values = tuple(values)
    if "TRUE" in values:
        return "TRUE"
    if "UNKNOWN" in values:
        return "UNKNOWN"
    return "FALSE"


def _compare_number(fact: Mapping[str, Any], comparator: str, threshold: float) -> str:
    number = _number(fact.get("value"))
    if number is None:
        return "UNKNOWN"
    return "TRUE" if (number < threshold if comparator == "LT" else number >= threshold) else "FALSE"


def _eval(facts: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    safety = _tri_and((
        _tri(facts["research_universe"]), _tri(facts["actual_bar"]),
        _tri(facts["price_identity_READY"]), _tri(facts["minimum_liquidity"]),
        _tri_not(_tri(facts["core_price_damage"])), _tri_not(_tri(facts["severe_extension"])),
    ))
    bias = _compare_number(facts["bias20_atr"], "LT", 3.0)
    compression = facts["compression_state"].get("value")
    structure = "UNKNOWN" if compression is None else "TRUE" if compression in {"COMPRESSING", "COMPRESSING_STRONG"} else "FALSE"
    delta_improving = _compare_number(facts["delta3"], "GTE", 3.0)
    delta_strong = _compare_number(facts["delta3"], "GTE", 10.0)
    ma_state = facts["ma_structure_state"].get("value")
    bull_transition = "UNKNOWN" if ma_state is None else "TRUE" if ma_state == "BULL_TRANSITION" else "FALSE"
    previous_close = _number(facts["close_t_minus_1"].get("value"))
    previous_ma20 = _number(facts["ma20_t_minus_1"].get("value"))
    current_close = _number(facts["close_t"].get("value"))
    current_ma20 = _number(facts["ma20_t"].get("value"))
    reclaim_before = "UNKNOWN" if previous_close is None or previous_ma20 is None else "TRUE" if previous_close <= previous_ma20 else "FALSE"
    reclaim_now = "UNKNOWN" if current_close is None or current_ma20 is None else "TRUE" if current_close > current_ma20 else "FALSE"
    reclaim = _tri_and((reclaim_before, reclaim_now))
    trend_early = _tri_or((bull_transition, reclaim))
    s1 = _tri_and((bias, structure, delta_improving))
    s2 = _tri_and((bias, delta_strong, trend_early))
    seed_paths = _tri_or((s1, s2))
    base_state = _tri_and((safety, seed_paths))

    domain_states = {
        "research_universe": _tri(facts["research_universe"]),
        "actual_bar": _tri(facts["actual_bar"]),
        "price_identity_READY": _tri(facts["price_identity_READY"]),
        "minimum_liquidity": _tri(facts["minimum_liquidity"]),
        "core_price_damage": _tri(facts["core_price_damage"]),
        "severe_extension": _tri(facts["severe_extension"]),
        "safety": safety,
        "position_ok": bias,
        "structure_improving": structure,
        "relative_change_improving": delta_improving,
        "relative_change_strong": delta_strong,
        "trend_transition_early": trend_early,
        "S1": s1,
        "S2": s2,
        "seed_paths": seed_paths,
        "base_seed_state": base_state,
    }
    map_values = {
        "HIGH_PARTICIPATION_EFFECTIVE_ADVANCE": "SUPPORTED",
        "HIGH_PARTICIPATION_REVERSAL": "CONFLICTING",
        "HIGH_PARTICIPATION_LOW_EFFICIENCY": "CONFLICTING",
        "LOW_PARTICIPATION_ADVANCE": "NEUTRAL",
        "LOW_PARTICIPATION_DECLINE": "NEUTRAL",
        "NORMAL_PARTICIPATION": "NEUTRAL",
    }
    participation_value = facts["core_participation_result"].get("value")
    annotation = map_values.get(participation_value, "UNKNOWN")

    waiting: list[dict[str, str]] = []
    # Include hard-safety inputs and rule inputs that can affect the evaluated paths.
    relevant_fields = {
        "research_universe", "actual_bar", "price_identity_READY", "minimum_liquidity",
        "core_price_damage", "severe_extension", "bias20_atr", "compression_state", "delta3",
        "ma_structure_state", "core_participation_result",
    }
    if trend_early == "UNKNOWN":
        relevant_fields.update(("close_t_minus_1", "ma20_t_minus_1", "close_t", "ma20_t"))
    for field in sorted(relevant_fields):
        if facts[field].get("value") is None:
            waiting.append({"field_id": field, "reason": str(facts[field].get("reason") or "UPSTREAM_UNKNOWN")})
    invalid: list[dict[str, str]] = []
    if base_state != "TRUE":
        for field in ("research_universe", "actual_bar", "price_identity_READY", "minimum_liquidity"):
            if domain_states[field] == "FALSE":
                invalid.append({"predicate": field, "state": "FALSE"})
        for field in ("core_price_damage", "severe_extension"):
            if domain_states[field] == "TRUE":
                invalid.append({"predicate": f"NOT_{field}", "state": "FALSE"})
        if safety != "FALSE":
            for path, state in (("S1", s1), ("S2", s2)):
                if state == "FALSE":
                    invalid.append({"predicate": path, "state": "FALSE"})
    invalid.sort(key=lambda item: item["predicate"])
    quality_codes = sorted({f"UNKNOWN_INPUT:{item['field_id']}:{item['reason']}" for item in waiting})
    matched = [path for path, state in (("S1", s1), ("S2", s2)) if state == "TRUE"]
    return {
        "base_seed_state": base_state,
        "matched_seed_paths": matched,
        "domain_states": domain_states,
        "waiting_for": waiting,
        "invalid_if": invalid,
        "quality": "COMPLETE" if not waiting else "PARTIAL_UNKNOWN",
        "quality_codes": quality_codes,
        "seed_participation_annotation": annotation,
    }



def evaluate_facts(facts: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Evaluate one already projected BASE_SEED_V1 fact map."""
    return _eval(facts)

def _input_digest(core: Mapping[str, Any], facts: Mapping[str, Mapping[str, Any]], source_bindings: Mapping[str, Any]) -> str:
    payload = {
        "source_bindings": {
            "publication_id": source_bindings["publication_id"],
            "profile_row_publication_id": source_bindings["profile_row_publication_id"],
            "trade_date": source_bindings["trade_date"],
            "core_logical_digest": source_bindings["core_logical_digest"],
            "core_profile_artifact_sha256": source_bindings["core_profile_artifact_sha256"],
            "full_scope_factors_logical_digest": source_bindings["full_scope_factors_logical_digest"],
            "full_scope_factors_artifact_sha256": source_bindings["full_scope_factors_artifact_sha256"],
        },
        "identity": {"trade_date": core.get("trade_date"), "security_id": core.get("security_id"), "symbol": core.get("symbol"), "board": core.get("board")},
        "accepted_facts": facts,
    }
    return sha256_bytes(canonical_json(payload))


def _row_fact_digest(row: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in row.items() if key not in {"fact_digest", "created_at"}}
    return sha256_bytes(canonical_json(payload))


def _logical_digest(rows: Sequence[Mapping[str, Any]], source_bindings: Mapping[str, Any]) -> str:
    logical_rows = [{key: value for key, value in row.items() if key != "created_at"} for row in rows]
    logical_rows.sort(key=lambda row: (row["trade_date"], row["security_id"]))
    payload = {
        "contract_id": CONTRACT_ID,
        "parameter_set_id": PARAMETER_SET_ID,
        "accepted_source_bindings": {
            "publication_id": source_bindings["publication_id"],
            "trade_date": source_bindings["trade_date"],
            "core_logical_digest": source_bindings["core_logical_digest"],
            "core_profile_artifact_sha256": source_bindings["core_profile_artifact_sha256"],
            "full_scope_factors_logical_digest": source_bindings["full_scope_factors_logical_digest"],
            "full_scope_factors_artifact_sha256": source_bindings["full_scope_factors_artifact_sha256"],
        },
        "rows": logical_rows,
    }
    return sha256_bytes(canonical_json(payload))


def build_candidate_from_records(
    core_records: Sequence[Mapping[str, Any]],
    factor_records: Sequence[Mapping[str, Any]],
    source_bindings: Mapping[str, Any],
    *,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Pure BASE_SEED_V1 evaluation over the frozen accepted Core projection.

    Records later than T are ignored before identity joins; no future fact can enter the logical result.
    Unknown accepted inputs remain UNKNOWN. Arbitrary extra record keys are not projected or hashed.
    """
    target_core = [row for row in core_records if row.get("trade_date") == TRADE_DATE]
    target_factors = [row for row in factor_records if row.get("trade_date") == TRADE_DATE]
    if len(target_core) != 5222 or len(target_factors) != 5222:
        raise ValueError("target date must contain the exact accepted 5,222-row scope")
    core_by_id: dict[str, Mapping[str, Any]] = {}
    factor_by_id: dict[str, Mapping[str, Any]] = {}
    for row in target_core:
        sid = row.get("security_id")
        if not isinstance(sid, str) or sid in core_by_id:
            raise ValueError("accepted Core profile has missing or duplicate security_id")
        core_by_id[sid] = row
    for row in target_factors:
        sid = row.get("security_id")
        if not isinstance(sid, str) or sid in factor_by_id:
            raise ValueError("accepted factor artifact has missing or duplicate security_id")
        factor_by_id[sid] = row
    if set(core_by_id) != set(factor_by_id):
        raise ValueError("accepted factor/Core identity sets differ")
    board_counts = Counter(str(row.get("board")) for row in target_core)
    if dict(board_counts) != EXPECTED_BOARD_COUNTS:
        raise ValueError(f"accepted Core board count mismatch: {dict(board_counts)}")
    now = created_at or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    rows: list[dict[str, Any]] = []
    for sid in sorted(core_by_id):
        core = core_by_id[sid]
        factor = factor_by_id[sid]
        if factor.get("board_scope") != core.get("board") or factor.get("coordinate_basis") != core.get("coordinate_basis"):
            raise ValueError(f"accepted factor/Core row binding mismatch for {sid}")
        if core.get("publication_id") != PROFILE_ROW_PUBLICATION_ID:
            raise ValueError(f"accepted Core row publication namespace mismatch for {sid}")
        facts = _normalize_facts(core, factor)
        derived = _eval(facts)
        row = {
            "publication_id": source_bindings["publication_id"],
            "source_publication_id": core["publication_id"],
            "trade_date": TRADE_DATE,
            "security_id": sid,
            "base_seed_state": derived["base_seed_state"],
            "matched_seed_paths": derived["matched_seed_paths"],
            "domain_states": derived["domain_states"],
            "waiting_for": derived["waiting_for"],
            "invalid_if": derived["invalid_if"],
            "quality": derived["quality"],
            "quality_codes": derived["quality_codes"],
            "seed_participation_annotation": derived["seed_participation_annotation"],
            "model_contract_id": CONTRACT_ID,
            "parameter_set_id": PARAMETER_SET_ID,
            "source_core_logical_digest": CORE_LOGICAL_DIGEST,
            "input_digest": _input_digest(core, facts, source_bindings),
            "created_at": now,
        }
        row["fact_digest"] = _row_fact_digest(row)
        rows.append(row)
    rows.sort(key=lambda row: (row["trade_date"], row["security_id"]))
    state_by_board = Counter((core_by_id[row["security_id"]]["board"], row["base_seed_state"]) for row in rows)
    return {
        "rows": rows,
        "row_count": len(rows),
        "logical_digest": _logical_digest(rows, source_bindings),
        "board_counts": dict(sorted(board_counts.items())),
        "state_counts": dict(sorted(Counter(row["base_seed_state"] for row in rows).items())),
        "state_counts_by_board": {board: dict(sorted({state: count for (b, state), count in state_by_board.items() if b == board}.items())) for board in sorted(board_counts)},
        "participation_annotation_counts": dict(sorted(Counter(row["seed_participation_annotation"] for row in rows).items())),
        "source_bindings": dict(source_bindings),
    }


def atomic_write_gzip_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    try:
        with open(temporary, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", compresslevel=9, fileobj=raw, mtime=0) as compressed:
                for row in rows:
                    compressed.write(canonical_json(row) + b"\n")
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def run_accepted_candidate(
    root: Path,
    output_path: Path,
    *,
    created_at: str | None = None,
    accepted_inputs_root: Path | None = None,
) -> dict[str, Any]:
    source_bindings, core_rows, factor_rows = _load_accepted_source_context(root, accepted_inputs_root)
    result = build_candidate_from_records(core_rows, factor_rows, source_bindings, created_at=created_at)
    board_by_security_id = {str(row["security_id"]): str(row["board"]) for row in core_rows if row.get("trade_date") == TRADE_DATE}
    result["unknown_reason_inventory"] = unknown_reason_inventory(result["rows"], board_by_security_id)
    atomic_write_gzip_jsonl(output_path, result["rows"])
    result["artifact_path"] = str(output_path)
    result["artifact_sha256"] = sha256_file(output_path)
    return result


def unknown_reason_inventory(rows: Sequence[Mapping[str, Any]], board_by_security_id: Mapping[str, str] | None = None) -> dict[str, Any]:
    inventory: Counter[tuple[str, str, str]] = Counter()
    by_board: Counter[tuple[str, str, str]] = Counter()
    board_by_security_id = board_by_security_id or {}
    for row in rows:
        if row["base_seed_state"] != "UNKNOWN":
            continue
        board = board_by_security_id.get(row["security_id"], "UNKNOWN")
        for item in row["waiting_for"]:
            key = (item["field_id"], item["reason"], row["base_seed_state"])
            inventory[key] += 1
            by_board[(board, item["field_id"], item["reason"])] += 1
    return {
        "by_reason": [
            {"field_id": field, "reason": reason, "base_seed_state": state, "count": count}
            for (field, reason, state), count in sorted(inventory.items())
        ],
        "by_board": [
            {"board": board, "field_id": field, "reason": reason, "count": count}
            for (board, field, reason), count in sorted(by_board.items())
        ],
    }
