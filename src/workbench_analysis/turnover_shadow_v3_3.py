"""Immutable turnover shadow observations and coverage readiness for P12-14."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from workbench_analysis.forward_v3_3 import atomic_write, digest


CONTRACT_ID = "P12_14_TURNOVER_SHADOW_OBSERVATION_V1"
MIN_BOUND_DAYS = 20
MIN_BOUND_ROWS = 50


def build_observation(
    *,
    active: dict,
    enrichment: dict,
    captured_at_utc: str,
) -> dict:
    identity = active["identity"]
    trade_date = str(identity["trade_date"])
    enhanced_by_id = {str(row.get("security_id") or ""): row for row in enrichment.get("enhanced_items", [])}
    items = []
    seen: set[str] = set()
    for source in enrichment.get("items", []):
        if source.get("capability_status") != "BOUND":
            continue
        security_id = str(source.get("security_id") or "")
        if not security_id or security_id in seen or str(source.get("trade_date")) != trade_date:
            raise ValueError("TURNOVER_SHADOW_IDENTITY_INVALID")
        value = float(source["turnover_rate"])
        if not 0 <= value <= 1:
            raise ValueError("TURNOVER_SHADOW_VALUE_INVALID")
        seen.add(security_id)
        enhanced = enhanced_by_id.get(security_id, {})
        items.append({
            "security_id": security_id,
            "trade_date": trade_date,
            "turnover_rate": value,
            "turnover_basis": str(source.get("turnover_basis") or ""),
            "source_id": str(source.get("source_id") or ""),
            "source_identity_sha256": source.get("source_identity_sha256"),
            "observed_at_utc": source.get("observed_at_utc"),
            "source_quote_time": source.get("source_quote_time"),
            "source_contract_id": source.get("source_contract_id"),
            "field_map_version": source.get("field_map_version"),
            "basis_verification": source.get("basis_verification", "UNKNOWN"),
            "session_binding_status": source.get("session_binding_status", "FINGERPRINT_ONLY"),
            "turnover_activity_percentile": enhanced.get("turnover_activity_percentile"),
            "turnover_activity_band": enhanced.get("turnover_activity_band"),
            "turnover_enhanced_rank": enhanced.get("turnover_enhanced_rank"),
            "turnover_usage": enhanced.get("turnover_usage"),
            "semantic_status": enhanced.get("semantic_status"),
            "price_acceptance": enhanced.get("price_acceptance"),
            "turnover_context": enhanced.get("turnover_context"),
            "turnover_priority_tier": enhanced.get("turnover_priority_tier"),
            "turnover_reason_codes": enhanced.get("turnover_reason_codes", []),
        })
    items.sort(key=lambda row: row["security_id"])
    requested = int((enrichment.get("request") or {}).get("candidate_count") or 0)
    logical = {
        "contract_id": CONTRACT_ID,
        "trade_date": trade_date,
        "bundle_digest": str(active["output_digest"]),
        "research_run_id": str(identity["research_run_id"]),
        "captured_at_utc": captured_at_utc,
        "source_status": str(enrichment.get("status") or "UNAVAILABLE"),
        "source_error": enrichment.get("source_error"),
        "requested_count": requested,
        "bound_count": len(items),
        "coverage_ratio": len(items) / requested if requested else 0.0,
        "items": items,
        "guardrails": {
            "raw_payload_persisted": False,
            "core_score_or_category_rank_changed": False,
            "effect_claimed": False,
        },
    }
    return {**logical, "observation_digest": digest(logical)}


def seal(root: str | Path, observation: dict) -> dict:
    target = Path(root) / observation["trade_date"] / f"{observation['observation_digest']}.json"
    if target.exists():
        if json.loads(target.read_text(encoding="utf-8")) != observation:
            raise ValueError("TURNOVER_SHADOW_DIGEST_CONFLICT")
        return {"path": str(target), "reused": True}
    atomic_write(target, observation)
    return {"path": str(target), "reused": False}


def canonical_observations(observations: Iterable[dict]) -> list[dict]:
    selected: dict[tuple[str, str], dict] = {}
    for observation in observations:
        key = (str(observation["trade_date"]), str(observation["bundle_digest"]))
        quality = (int(observation.get("bound_count") or 0), str(observation.get("captured_at_utc") or ""), str(observation.get("observation_digest") or ""))
        old = selected.get(key)
        old_quality = (-1, "", "") if old is None else (int(old.get("bound_count") or 0), str(old.get("captured_at_utc") or ""), str(old.get("observation_digest") or ""))
        if quality > old_quality:
            selected[key] = observation
    return sorted(selected.values(), key=lambda value: (value["trade_date"], value["bundle_digest"]))


def report(observations: Iterable[dict]) -> dict:
    canonical = canonical_observations(observations)
    bound = [observation for observation in canonical if int(observation.get("bound_count") or 0) > 0]
    values = sorted(float(item["turnover_rate"]) for observation in bound for item in observation.get("items", []))
    bound_days = len({observation["trade_date"] for observation in bound})
    ready = bound_days >= MIN_BOUND_DAYS and len(values) >= MIN_BOUND_ROWS
    distribution: dict[str, Any] = {"available": len(values), "status": "UNAVAILABLE"}
    if values:
        pick = lambda q: values[round((len(values) - 1) * q)]
        distribution = {"available": len(values), "status": "DESCRIPTIVE_ONLY", "min": values[0], "p25": pick(.25), "median": pick(.5), "p75": pick(.75), "max": values[-1]}
    return {
        "contract_id": CONTRACT_ID,
        "status": "SHADOW_COVERAGE_READY" if ready else "SHADOW_COVERAGE_PENDING",
        "gate": {
            "minimum_bound_days": MIN_BOUND_DAYS,
            "minimum_bound_rows": MIN_BOUND_ROWS,
            "attempt_days": len({observation["trade_date"] for observation in canonical}),
            "bound_days": bound_days,
            "bound_rows": len(values),
        },
        "turnover_distribution": distribution,
        "effect_status": "EFFECT_NOT_EVALUATED",
        "observation_digests": [observation["observation_digest"] for observation in canonical],
    }


def load_all(root: str | Path) -> list[dict]:
    path = Path(root)
    if not path.exists():
        return []
    return [json.loads(file.read_text(encoding="utf-8")) for file in sorted(path.glob("*/*.json"))]


__all__ = ["CONTRACT_ID", "MIN_BOUND_DAYS", "MIN_BOUND_ROWS", "build_observation", "canonical_observations", "load_all", "report", "seal"]
