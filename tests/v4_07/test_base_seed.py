from __future__ import annotations

import copy
import hashlib
import inspect
import json
import os
from pathlib import Path

import pytest

from src.v4.base_seed import (
    _eval,
    _load_accepted_source_context,
    build_candidate_from_records,
    evaluate_facts,
)
from scripts.verify_v4_07_base_seed import independent_eval, parameter_values_from_document
from scripts.verify_v4_07_machine_vectors import execute_facts, execute_vector, machine_fact

ROOT = Path(__file__).resolve().parents[2]
ACCEPTED_INPUTS_ROOT = Path(os.environ.get("V4_07_ACCEPTED_INPUTS_ROOT", str(ROOT))).resolve()
VECTORS = json.loads((ROOT / "config/v4_07_machine_vectors_v1.json").read_text(encoding="utf-8"))
PARAMETERS = json.loads((ROOT / "config/v4_07_parameter_set_v1.json").read_text(encoding="utf-8"))


def _vector_facts(overrides):
    values = dict(VECTORS["base_input"])
    values.update(overrides)
    return {key: machine_fact(value, key) for key, value in values.items()}


def _vector_result(overrides, parameter_set=PARAMETERS):
    return execute_vector(overrides, parameter_set, VECTORS["base_input"])


@pytest.mark.parametrize(
    "vector",
    [v for v in VECTORS["vectors"] if v["suite"] not in {"temporal", "isolation"}],
    ids=lambda v: v["vector_id"],
)
def test_frozen_machine_vectors(vector):
    result = _vector_result(vector["overrides"])
    for field, expected in vector["expected"].items():
        assert result[field] == expected


@pytest.mark.parametrize(
    ("parameter_id", "new_value", "overrides", "predicate", "expected_before", "expected_after"),
    [
        ("V4_07_POSITION_BIAS20_ATR_MAX", 2.5, {"bias20_atr": 2.75, "delta3": 10.5}, "position_ok", "TRUE", "FALSE"),
        ("V4_07_DELTA3_IMPROVING_MIN_POINTS", 4, {"bias20_atr": 2.0, "delta3": 3.5}, "relative_change_improving", "TRUE", "FALSE"),
        ("V4_07_DELTA3_STRONG_MIN_POINTS", 11, {"bias20_atr": 2.0, "delta3": 10.5}, "relative_change_strong", "TRUE", "FALSE"),
    ],
)
def test_parameter_instance_drives_machine_production_and_independent_evaluators(
    parameter_id, new_value, overrides, predicate, expected_before, expected_after
):
    facts = _vector_facts(overrides)
    fixture = copy.deepcopy(PARAMETERS)
    entry = next(item for item in fixture["parameters"] if item["parameter_id"] == parameter_id)
    entry["value"] = new_value

    machine_before = execute_facts(facts, PARAMETERS)
    production_before = evaluate_facts(facts, PARAMETERS)
    independent_before = independent_eval(facts, parameter_values_from_document(PARAMETERS))
    machine_after = execute_facts(facts, fixture)
    production_after = evaluate_facts(facts, fixture)
    independent_after = independent_eval(facts, parameter_values_from_document(fixture))

    assert machine_before["domain_states"][predicate] == expected_before
    assert machine_after["domain_states"][predicate] == expected_after
    assert machine_before == production_before
    assert machine_after == production_after
    assert production_before == independent_before
    assert production_after == independent_after
    assert PARAMETERS["parameters"] != fixture["parameters"]


def test_evaluator_has_no_threshold_literal_fallback():
    source = inspect.getsource(_eval)
    assert "3.0" not in source
    assert "10.0" not in source


def test_future_row_cannot_change_target_candidate():
    context, core, factors = _load_accepted_source_context(ROOT, ACCEPTED_INPUTS_ROOT)
    before = build_candidate_from_records(core, factors, context, created_at="2026-09-29T00:00:00Z")
    future_core = dict(core[0], trade_date="2026-09-29", future_test_payload={"close": 999999.0, "ma20": 0.0})
    future_factor = dict(factors[0], trade_date="2026-09-29", fields={"rps5_delta3": {"quality_state": "OBSERVED", "value": 99.0}})
    after = build_candidate_from_records(core + [future_core], factors + [future_factor], context, created_at="2026-09-29T00:00:00Z")
    assert after["row_count"] == before["row_count"] == context["expected_identity_count"]
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
    context, core, factors = _load_accepted_source_context(ROOT, ACCEPTED_INPUTS_ROOT)
    baseline = build_candidate_from_records(core, factors, context, created_at="2026-09-29T00:00:00Z")
    mutated = build_candidate_from_records(_overlay(core, scenario), factors, context, created_at="2026-09-29T00:00:00Z")
    assert mutated["row_count"] == baseline["row_count"] == context["expected_identity_count"]
    assert mutated["logical_digest"] == baseline["logical_digest"]
    assert mutated["rows"] == baseline["rows"]


def test_two_fresh_source_loads_are_deterministic():
    first_context, first_core, first_factors = _load_accepted_source_context(ROOT, ACCEPTED_INPUTS_ROOT)
    second_context, second_core, second_factors = _load_accepted_source_context(ROOT, ACCEPTED_INPUTS_ROOT)
    first = build_candidate_from_records(first_core, first_factors, first_context, created_at="2026-09-29T00:00:00Z")
    second = build_candidate_from_records(second_core, second_factors, second_context, created_at="2026-09-30T00:00:00Z")
    assert first["row_count"] == second["row_count"] == first_context["expected_identity_count"]
    assert first["logical_digest"] == second["logical_digest"]
    assert [r["input_digest"] for r in first["rows"]] == [r["input_digest"] for r in second["rows"]]
    assert [r["fact_digest"] for r in first["rows"]] == [r["fact_digest"] for r in second["rows"]]


def _synthetic_context(trade_date, publication_id, profile_id, core_digest, core_rows, template):
    boards = {}
    for row in core_rows:
        boards[row["board"]] = boards.get(row["board"], 0) + 1
    identity_count = len(core_rows)
    bindings = copy.deepcopy(template["source_bindings"])
    bindings.update({
        "publication_id": publication_id,
        "profile_row_publication_id": profile_id,
        "trade_date": trade_date,
        "core_logical_digest": core_digest,
        "accepted_identity_count": identity_count,
        "expected_board_counts": dict(sorted(boards.items())),
        "core_profile_artifact_sha256": hashlib.sha256((core_digest + ":core").encode()).hexdigest(),
        "full_scope_factors_logical_digest": hashlib.sha256((core_digest + ":factor-logical").encode()).hexdigest(),
        "full_scope_factors_artifact_sha256": hashlib.sha256((core_digest + ":factors").encode()).hexdigest(),
    })
    return {
        "source_bindings": bindings,
        "trade_date": trade_date,
        "publication_id": publication_id,
        "profile_row_publication_id": profile_id,
        "core_logical_digest": core_digest,
        "expected_identity_count": identity_count,
        "expected_board_counts": dict(sorted(boards.items())),
        "parameter_set": copy.deepcopy(template["parameter_set"]),
        "contract_digest": template["contract_digest"],
        "parameter_set_digest": template["parameter_set_digest"],
    }


def test_producer_uses_two_accepted_run_contexts_without_cross_date_identity_leakage():
    template, source_core, source_factors = _load_accepted_source_context(ROOT, ACCEPTED_INPUTS_ROOT)
    source_factor_by_id = {row["security_id"]: row for row in source_factors}
    t_rows = [copy.deepcopy(source_core[0]), copy.deepcopy(source_core[1])]
    t1_rows = [copy.deepcopy(source_core[2])]
    contexts = []
    all_core = []
    all_factors = []
    for trade_date, pub, profile_id, digest_value, rows in (
        ("2026-09-28", "SYNTHETIC-PUBLICATION-T", "SYNTHETIC-PROFILE-T", "a" * 64, t_rows),
        ("2026-09-29", "SYNTHETIC-PUBLICATION-T1", "SYNTHETIC-PROFILE-T1", "b" * 64, t1_rows),
    ):
        updated_core = []
        updated_factors = []
        for source in rows:
            core = dict(source, trade_date=trade_date, publication_id=profile_id)
            factor = copy.deepcopy(source_factor_by_id[source["security_id"]])
            factor["trade_date"] = trade_date
            updated_core.append(core)
            updated_factors.append(factor)
        contexts.append(_synthetic_context(trade_date, pub, profile_id, digest_value, updated_core, template))
        all_core.extend(updated_core)
        all_factors.extend(updated_factors)

    t_result = build_candidate_from_records(all_core, all_factors, contexts[0], created_at="2026-09-30T00:00:00Z")
    t1_result = build_candidate_from_records(all_core, all_factors, contexts[1], created_at="2026-09-30T00:00:00Z")
    assert t_result["row_count"] == 2
    assert t1_result["row_count"] == 1
    assert {row["trade_date"] for row in t_result["rows"]} == {"2026-09-28"}
    assert {row["trade_date"] for row in t1_result["rows"]} == {"2026-09-29"}
    assert {row["publication_id"] for row in t_result["rows"]} == {"SYNTHETIC-PUBLICATION-T"}
    assert {row["publication_id"] for row in t1_result["rows"]} == {"SYNTHETIC-PUBLICATION-T1"}
    assert t_result["source_bindings"]["core_logical_digest"] != t1_result["source_bindings"]["core_logical_digest"]
    assert t_result["logical_digest"] != t1_result["logical_digest"]
    changed_future = [dict(row, future_test_payload="must-not-enter-T") if row["trade_date"] == "2026-09-29" else row for row in all_core]
    unchanged_t = build_candidate_from_records(changed_future, all_factors, contexts[0], created_at="2026-09-30T00:00:00Z")
    assert unchanged_t["logical_digest"] == t_result["logical_digest"]
