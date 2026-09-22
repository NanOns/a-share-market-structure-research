"""Pure, fail-closed turnover context layer for frozen V3.3 candidates."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Mapping


ALGORITHM_CONTRACT_ID = "TURNOVER_CONTEXT_V3_3_V1"
PARAMETER_CONTRACT_ID = "TURNOVER_CONTEXT_PARAMS_V1"
DEFAULT_PARAMS = {
    "global_semantic_coverage_min": .80, "global_degraded_coverage_min": .60,
    "group_coverage_min": .70, "group_size_min": 5, "small_group_max": 9,
    "activity_low_max": .20, "activity_high_min": .80,
    "trend_high_churn_bias20_min": .08, "turnover_rate_min": 0.0,
    "turnover_rate_max": 1.0, "effect_status": "EFFECT_OBSERVATION_PENDING",
}


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def parameter_hash(params: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical(dict(params))).hexdigest()


def load_params(path: str | Path | None = None) -> dict:
    if path is None:
        path = Path(__file__).resolve().parents[2] / "config/turnover_context_params_v1.json"
    try:
        loaded = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        loaded = {}
    return {**DEFAULT_PARAMS, **{k: v for k, v in loaded.items() if k in DEFAULT_PARAMS}}


def _finite(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _group(row: Mapping[str, object]) -> tuple[str, str, str]:
    return tuple(str(row.get(k) or "UNKNOWN") for k in ("primary_category", "selection_mode", "rank_status"))


def _source_group(evidence: Mapping[str, object]) -> tuple[str, str, str, str]:
    return tuple(str(evidence.get(k) or "UNKNOWN") for k in ("source_id", "source_contract_id", "field_map_version", "turnover_basis"))


def _rule(path: str, actual: object, operator: str, threshold: object, result: bool | None) -> dict:
    return {"field_path": path, "actual": actual, "operator": operator, "threshold": threshold, "result": result}


def _price_context(row: Mapping[str, object]) -> dict:
    category = str(row.get("primary_category") or "")
    factor = row.get("factor_evidence") if isinstance(row.get("factor_evidence"), Mapping) else {}
    scanner = row.get("scanner_evidence") if isinstance(row.get("scanner_evidence"), Mapping) else {}
    scenario_name = {"LAUNCH_CONFIRM": "launch", "RECOVERY_TURN": "recovery_turn", "STRONG_PULLBACK": "pullback", "TREND_CONTINUE": "trend_continue"}.get(category)
    scenario = scanner.get(scenario_name, {}) if scenario_name else {}
    eligible = scenario.get("eligible") if isinstance(scenario, Mapping) else None
    rules = [_rule(f"scanner_evidence.{scenario_name}.eligible", eligible, "==", True, eligible is True)]
    if eligible is not True:
        return {"status": "CORE_EVIDENCE_CONFLICT" if eligible is False else "UNKNOWN", "rules": rules,
                "reason_codes": ["CORE_EVIDENCE_CONFLICT" if eligible is False else "CORE_ELIGIBILITY_UNKNOWN"]}

    def value(name: str) -> float | None:
        top = _finite(row.get(name)); nested = _finite(factor.get(name))
        if top is not None and nested is not None and not math.isclose(top, nested, rel_tol=1e-12, abs_tol=1e-12):
            conflicts.append(name); return None
        return nested if nested is not None else top

    conflicts: list[str] = []
    checks: list[tuple[str, object, str, object, bool | None]] = []
    clv, amr, bias = value("clv"), value("amr20_mean_prior"), value("bias20")
    if category == "LAUNCH_CONFIRM":
        margin = value("break_margin_close20"); reject = factor.get("intraday_reject_high20", row.get("intraday_reject_high20"))
        checks = [("clv", clv, ">=", .75, None if clv is None else clv >= .75), ("break_margin_close20", margin, ">=", .01, None if margin is None else margin >= .01), ("intraday_reject_high20", reject, "==", False, None if not isinstance(reject, bool) else reject is False), ("amr20_mean_prior", amr, ">=", 1.2, None if amr is None else amr >= 1.2)]
    elif category == "RECOVERY_TURN":
        r5, r20 = scenario.get("r5"), scenario.get("r20")
        branch = True if r5 is True or r20 is True else False if r5 is False and r20 is False else None
        checks = [("clv", clv, ">=", .70, None if clv is None else clv >= .70), ("bias20", bias, ">=", 0, None if bias is None else bias >= 0), ("amr20_mean_prior", amr, ">=", 1.05, None if amr is None else amr >= 1.05), ("recovery_r5_or_r20", branch, "==", True, branch)]
    elif category == "STRONG_PULLBACK":
        contraction, confirm = value("pullback_contraction"), value("confirm_amount_ratio")
        reject = factor.get("intraday_reject_high20", row.get("intraday_reject_high20"))
        checks = [("clv", clv, ">=", .70, None if clv is None else clv >= .70), ("pullback_contraction", contraction, "<=", .85, None if contraction is None else contraction <= .85), ("confirm_amount_ratio", confirm, ">=", 1, None if confirm is None else confirm >= 1), ("intraday_reject_high20", reject, "==", False, None if not isinstance(reject, bool) else reject is False)]
    elif category == "TREND_CONTINUE":
        close_above = (scenario.get("checks") or {}).get("CLOSE_ABOVE_PRIOR_HIGH") if isinstance(scenario.get("checks"), Mapping) else None
        checks = [("clv", clv, ">=", .70, None if clv is None else clv >= .70), ("scanner_evidence.trend_continue.checks.CLOSE_ABOVE_PRIOR_HIGH", close_above, "==", True, close_above if isinstance(close_above, bool) else None), ("amr20_mean_prior", amr, "between", [.8, 2.5], None if amr is None else .8 <= amr <= 2.5), ("bias20", bias, "finite", True, bias is not None)]
    else:
        return {"status": "UNKNOWN", "rules": rules, "reason_codes": ["CATEGORY_UNSUPPORTED"]}
    rules.extend(_rule(*check) for check in checks)
    if conflicts:
        return {"status": "LOCAL_FACT_CONFLICT", "rules": rules, "reason_codes": ["LOCAL_FACT_CONFLICT"]}
    if any(check[4] is None for check in checks):
        return {"status": "UNKNOWN", "rules": rules, "reason_codes": ["PRICE_CONTEXT_INCOMPLETE"]}
    return {"status": "STRONG" if all(check[4] for check in checks) else "MARGINAL", "rules": rules, "reason_codes": []}


def _combine(row: Mapping[str, object], band: str, price: str, params: Mapping[str, object]) -> tuple[str, str, list[str]]:
    if price not in {"STRONG", "MARGINAL"}:
        return ("PRICE_CONTEXT_UNKNOWN", "T2", [price])
    table = {
        ("HIGH", "STRONG"): ("HIGH_PARTICIPATION_ACCEPTED", "T1"),
        ("NORMAL", "STRONG"): ("NORMAL_PARTICIPATION_ACCEPTED", "T1"),
        ("LOW", "STRONG"): ("LOW_CHURN_EFFICIENT_ADVANCE", "T2"),
        ("HIGH", "MARGINAL"): ("HIGH_CHURN_MARGINAL_ACCEPTANCE", "T3"),
        ("NORMAL", "MARGINAL"): ("NORMAL_NEUTRAL", "T2"),
        ("LOW", "MARGINAL"): ("LOW_PARTICIPATION_WEAK_CONFIRMATION", "T2"),
    }
    context, tier = table[(band, price)]
    category = str(row.get("primary_category") or "")
    if category == "STRONG_PULLBACK" and band in {"HIGH", "NORMAL"} and price == "STRONG": context = "PULLBACK_CONFIRM_WITH_PARTICIPATION"
    elif category == "STRONG_PULLBACK" and band == "HIGH" and price == "MARGINAL": context = "PULLBACK_HIGH_CHURN_WEAK_ACCEPTANCE"
    elif category == "RECOVERY_TURN" and band in {"HIGH", "NORMAL"} and price == "STRONG": context = "RECOVERY_WITH_PARTICIPATION"
    elif category == "RECOVERY_TURN" and band == "HIGH" and price == "MARGINAL": context = "RECOVERY_HIGH_CHURN_CAUTION"
    elif category == "TREND_CONTINUE" and band == "HIGH" and price == "MARGINAL" and (_finite(row.get("bias20")) or -math.inf) >= float(params["trend_high_churn_bias20_min"]): context = "HIGH_CHURN_TREND_RISK"
    return context, tier, []


def build_turnover_context(candidates: Iterable[Mapping[str, object]], evidence: Iterable[Mapping[str, object]], *, bundle_digest: str = "", observation_digest: str = "", params: Mapping[str, object] | None = None) -> dict:
    p = {**DEFAULT_PARAMS, **dict(params or {})}; source_rows = list(evidence); rows = [dict(row) for row in candidates]
    ids = [str(row.get("security_id") or "") for row in rows]
    if not all(ids) or len(ids) != len(set(ids)): raise ValueError("TURNOVER_CONTEXT_CANDIDATE_IDENTITY_INVALID")
    evidence_by_id: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for item in source_rows:
        sid = str(item.get("security_id") or "")
        if sid in set(ids): evidence_by_id[sid].append(item)
    output = []
    for position, row in enumerate(rows, 1):
        sid = str(row["security_id"]); matches = evidence_by_id.get(sid, []); reasons: list[str] = []
        item = matches[0] if len(matches) == 1 else {}
        if len(matches) > 1:
            signatures = {(x.get("turnover_rate"), x.get("source_id"), x.get("source_contract_id"), x.get("turnover_basis")) for x in matches}
            if len(signatures) == 1: item = matches[0]
            else: reasons.append("EVIDENCE_CONFLICT")
        rate = _finite(item.get("turnover_rate")); binding = str(item.get("binding_status") or item.get("capability_status") or "UNAVAILABLE")
        fact = binding == "BOUND" and rate is not None and float(p["turnover_rate_min"]) <= rate <= float(p["turnover_rate_max"])
        if not matches: reasons.append("SOURCE_ROW_MISSING")
        elif not fact: reasons.append(str(item.get("reason") or "TURNOVER_FACT_INVALID"))
        elif rate == 0 and _finite(row.get("raw_volume")) not in {None, 0}: reasons.append("ZERO_PRECISION_AMBIGUOUS")
        basis_verification = str(item.get("basis_verification") or "UNKNOWN")
        session_status = str(item.get("session_binding_status") or "FINGERPRINT_ONLY")
        basis = str(item.get("turnover_basis") or "UNKNOWN")
        comparable = fact and not reasons and basis in {"FLOAT_SHARE", "FREE_FLOAT_SHARE"} and basis_verification == "VERIFIED" and session_status == "SESSION_VERIFIED" and all(item.get(k) for k in ("source_id", "source_contract_id", "field_map_version"))
        if fact and not comparable:
            if basis_verification != "VERIFIED": reasons.append("TURNOVER_BASIS_NOT_VERIFIED")
            if session_status != "SESSION_VERIFIED": reasons.append("SESSION_NOT_VERIFIED")
            if not all(item.get(k) for k in ("source_contract_id", "field_map_version")): reasons.append("SOURCE_IDENTITY_INCOMPLETE")
        output.append({**row, "core_display_rank": position, "turnover_rate": rate if fact else None, "turnover_basis": basis,
            "basis_verification": basis_verification, "binding_status": binding, "semantic_status": "COMPARABLE" if comparable else "FACT_AVAILABLE" if fact else "UNAVAILABLE",
            "turnover_activity_percentile": None, "turnover_activity_band": None, "comparison_group_id": None, "comparison_n": 0, "comparison_coverage": None,
            "price_acceptance": "UNKNOWN", "base_context": "TURNOVER_UNKNOWN", "turnover_context": "TURNOVER_UNKNOWN", "turnover_priority_tier": "T2",
            "turnover_reason_codes": list(dict.fromkeys(reasons)), "turnover_risk_codes": [], "rule_evidence": [], "turnover_enhanced_rank": None,
            "enhanced_display_order": position, "position_policy": "LOCKED", "effect_status": p["effect_status"], "_comparable": comparable, "_source_group": _source_group(item)})
    n = len(output); fact_n = sum(x["turnover_rate"] is not None for x in output); comparable_n = sum(x["_comparable"] for x in output)
    coverage = comparable_n / n if n else 0.0
    layer_status = "EMPTY" if not n else "AVAILABLE" if coverage >= float(p["global_semantic_coverage_min"]) else "DEGRADED" if coverage >= float(p["global_degraded_coverage_min"]) else "BYPASSED"
    if layer_status == "AVAILABLE":
        business_groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
        for row in output: business_groups[_group(row)].append(row)
        for business_key, group_rows in business_groups.items():
            source_groups: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
            for row in group_rows:
                if row["_comparable"]: source_groups[row["_source_group"]].append(row)
            for source_key, comparable_rows in source_groups.items():
                group_coverage = len(comparable_rows) / len(group_rows)
                if len(comparable_rows) < int(p["group_size_min"]) or group_coverage < float(p["group_coverage_min"]):
                    for row in comparable_rows: row["turnover_reason_codes"].append("COMPARISON_GROUP_TOO_SMALL_OR_SPARSE")
                    continue
                group_id = hashlib.sha256(_canonical([business_key, source_key, sorted(x["security_id"] for x in comparable_rows)])).hexdigest()[:16]
                values = [x["turnover_rate"] for x in comparable_rows]
                for row in comparable_rows:
                    value = row["turnover_rate"]; pct = (sum(v < value for v in values) + .5 * sum(v == value for v in values)) / len(values)
                    band = "LOW" if pct <= float(p["activity_low_max"]) else "HIGH" if pct > float(p["activity_high_min"]) else "NORMAL"
                    price = _price_context(row); context, tier, extra = _combine(row, band, price["status"], p)
                    row.update({"turnover_activity_percentile": pct, "turnover_activity_band": band, "comparison_group_id": group_id, "comparison_n": len(comparable_rows), "comparison_coverage": group_coverage,
                        "price_acceptance": price["status"], "base_context": context, "turnover_context": context, "turnover_priority_tier": tier,
                        "semantic_status": "CONTEXT_READY" if price["status"] in {"STRONG", "MARGINAL"} else "PRICE_CONTEXT_UNKNOWN", "rule_evidence": price["rules"]})
                    row["turnover_reason_codes"].extend(price["reason_codes"] + extra)
                    if len(comparable_rows) <= int(p["small_group_max"]): row["turnover_risk_codes"].append("SMALL_COMPARISON_GROUP")
            ready = [x for x in group_rows if x["rank_status"] == "QUALIFIED_UNRANKED" and x["semantic_status"] == "CONTEXT_READY"]
            slots = sorted(x["core_display_rank"] for x in ready); ordered = sorted(ready, key=lambda x: ({"T1": 1, "T2": 2, "T3": 3}[x["turnover_priority_tier"]], x["core_display_rank"]))
            group_positions = {x["core_display_rank"]: index for index, x in enumerate(sorted(group_rows, key=lambda y: y["core_display_rank"]), 1)}
            for slot, row in zip(slots, ordered): row.update({"enhanced_display_order": slot, "turnover_enhanced_rank": group_positions[slot], "position_policy": "MOVABLE_WITHIN_READY_SLOTS"})
    for row in output:
        row["turnover_reason_codes"] = list(dict.fromkeys(row["turnover_reason_codes"])); row["turnover_enhancement_status"] = row["semantic_status"]; row["turnover_usage"] = "CONTEXT_AND_OPTIONAL_LOCKED_SLOT_ORDER"; row.pop("_comparable", None); row.pop("_source_group", None)
    return {"algorithm_contract_id": ALGORITHM_CONTRACT_ID, "parameter_contract_id": PARAMETER_CONTRACT_ID, "parameter_hash": parameter_hash(p), "bundle_digest": bundle_digest, "observation_digest": observation_digest,
        "layer_status": layer_status, "coverage": {"candidate_n": n, "fact_n": fact_n, "comparable_n": comparable_n, "fact_coverage": fact_n / n if n else 0.0, "semantic_coverage": coverage}, "items": output}


__all__ = ["ALGORITHM_CONTRACT_ID", "PARAMETER_CONTRACT_ID", "build_turnover_context", "load_params", "parameter_hash"]
