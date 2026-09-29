from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.v4.base_seed import (
    _load_accepted_source_context,
    build_candidate_from_records,
    evaluate_facts,
)

ROOT = Path(__file__).resolve().parents[2]
VECTORS = json.loads((ROOT / "config/v4_07_machine_vectors_v1.json").read_text(encoding="utf-8"))


def _machine_fact(value, field):
    if field in {"research_universe", "actual_bar", "price_identity_READY", "minimum_liquidity", "core_price_damage", "severe_extension"}:
        mapped = True if value == "TRUE" else False if value == "FALSE" else None
    elif value == "UNKNOWN":
        mapped = None
    else:
        mapped = value
    return {"value": mapped, "reason": "MACHINE_VECTOR_UNKNOWN" if mapped is None else None}


def _vector_result(overrides):
    values = dict(VECTORS["base_input"])
    values.update(overrides)
    facts = {key: _machine_fact(value, key) for key, value in values.items()}
    result = evaluate_facts(facts)
    result["seed_paths"] = result["domain_states"]["seed_paths"]
    result.update(result["domain_states"])
    return result


@pytest.mark.parametrize(
    "vector",
    [v for v in VECTORS["vectors"] if v["suite"] not in {"temporal", "isolation"}],
    ids=lambda v: v["vector_id"],
)
def test_frozen_machine_vectors(vector):
    result = _vector_result(vector["overrides"])
    for field, expected in vector["expected"].items():
        assert result[field] == expected


def test_future_row_cannot_change_target_candidate():
    bindings, core, factors = _load_accepted_source_context(ROOT)
    before = build_candidate_from_records(core, factors, bindings, created_at="2026-09-29T00:00:00Z")
    future_core = dict(core[0], trade_date="2026-09-29", future_test_payload={"close": 999999.0, "ma20": 0.0})
    future_factor = dict(factors[0], trade_date="2026-09-29", fields={"rps5_delta3": {"quality_state": "OBSERVED", "value": 99.0}})
    after = build_candidate_from_records(core + [future_core], factors + [future_factor], bindings, created_at="2026-09-29T00:00:00Z")
    assert after["row_count"] == before["row_count"] == 5222
    assert after["logical_digest"] == before["logical_digest"]
    assert after["rows"] == before["rows"]


def _overlay(core_rows, scenario):
    rows = []
    for source in core_rows:
        row = dict(source)
        if scenario == "B_PENDING_SIDECAR":
            row["supplemental_sidecar"] = {"turnover_state": "PENDING", "supplemental_participation_context": "PENDING"}
        elif scenario == "C_SYNTHETIC_TURNOVER":
            row.update({"turnover_rate": 0.731, "turnover_state": "EXTREME", "turnover_pct60": 99.0})
        elif scenario == "D_EXTENSION_NOTE_CHANGED":
            row["supplemental_extension_note"] = {"contract_version": "SYNTHETIC", "value": "changed"}
        elif scenario == "E_BINDING_QUALITY_CONFLICT":
            row["binding_quality"] = "BOUND_STRICT_CONFLICT"
        rows.append(row)
    return rows


@pytest.mark.parametrize(
    "scenario",
    ["B_PENDING_SIDECAR", "C_SYNTHETIC_TURNOVER", "D_EXTENSION_NOTE_CHANGED", "E_BINDING_QUALITY_CONFLICT"],
)
def test_v4_06_forbidden_input_matrix_isolation(scenario):
    bindings, core, factors = _load_accepted_source_context(ROOT)
    baseline = build_candidate_from_records(core, factors, bindings, created_at="2026-09-29T00:00:00Z")
    mutated = build_candidate_from_records(_overlay(core, scenario), factors, bindings, created_at="2026-09-29T00:00:00Z")
    assert mutated["row_count"] == baseline["row_count"] == 5222
    assert mutated["logical_digest"] == baseline["logical_digest"]
    assert mutated["rows"] == baseline["rows"]


def test_two_fresh_source_loads_are_deterministic():
    first_bindings, first_core, first_factors = _load_accepted_source_context(ROOT)
    second_bindings, second_core, second_factors = _load_accepted_source_context(ROOT)
    first = build_candidate_from_records(first_core, first_factors, first_bindings, created_at="2026-09-29T00:00:00Z")
    second = build_candidate_from_records(second_core, second_factors, second_bindings, created_at="2026-09-30T00:00:00Z")
    assert first["row_count"] == second["row_count"] == 5222
    assert first["logical_digest"] == second["logical_digest"]
    assert [r["input_digest"] for r in first["rows"]] == [r["input_digest"] for r in second["rows"]]
    assert [r["fact_digest"] for r in first["rows"]] == [r["fact_digest"] for r in second["rows"]]
