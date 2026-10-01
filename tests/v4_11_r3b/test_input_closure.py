import pytest

from src.v4.confirmation_input_closure_r3b import (
    DIAGNOSTIC_FIELDS, EPISODE_PARAMETERS, EPISODE_PRODUCER, InputClosureError,
    diagnostic_fact, episode_identity, require_formal_scenario,
    safety_predicates, scenario_capability_matrix, validate_dependency_graph,
    validate_episode,
)
from src.v4.state_identity import digest

TARGET = "2026-09-30"
CUTOFF = "2026-10-01T12:00:00+00:00"


def valid_episode():
    episode = {"security_id": "fixture-entity", "episode_start": "2026-09-24",
        "producer_contract_id": EPISODE_PRODUCER, "parameter_set_id": EPISODE_PARAMETERS,
        "origin_publication_id": "episode-origin", "source_publication_ids": ["episode-origin", "episode-prior"],
        "prior_session_publication_id": "episode-prior", "prior_session_trade_date": "2026-09-29",
        "prior_session_status": "PULLING_BACK", "system_available_at": "2026-09-30T01:00:00+00:00",
        "knowledge_cutoff": CUTOFF}
    episode["episode_id"] = episode_identity(episode)
    episode["publication_id"] = "V4_11_EPISODE_PUBLICATION:" + digest(episode)
    sources = {key: {"publication_id": key, "time_role": "PRIOR_SESSION_EPISODE",
        "producer_contract_id": EPISODE_PRODUCER, "parameter_set_id": EPISODE_PARAMETERS,
        "system_available_at": "2026-09-30T01:00:00+00:00", "trade_date": day,
        "rows": [{"security_id": "fixture-entity", "episode_id": episode["episode_id"], "state": "PULLING_BACK"}]}
        for key, day in (("episode-origin", "2026-09-24"), ("episode-prior", "2026-09-29"))}
    return episode, sources


def validate(episode, sources):
    return validate_episode(episode, target_date=TARGET, cutoff=CUTOFF,
        source_publications=sources, prior_session_date="2026-09-29")


def graph():
    base = {"trade_date": TARGET, "system_available_at": "2026-09-30T08:00:00+00:00",
        "pure_upstream": True, "time_role": "UPSTREAM_RAW", "producer_contract_id": "FIXTURE_UPSTREAM_V1",
        "parameter_set_id": "FIXTURE_PARAMETERS_V1", "publication_id": "fixture-publication"}
    return {"root": "loo", "nodes": [dict(base, node_id="quote", dependencies=[]),
        dict(base, node_id="loo", dependencies=["quote"], time_role="PURE_UPSTREAM_LOO")]}


def test_valid_prior_episode_evidence_is_validated_without_promotion():
    episode, sources = valid_episode()
    validate(episode, sources)
    assert scenario_capability_matrix(r3a_sealed=True)["STRONG_PULLBACK"]["capability"] == "DIAGNOSTIC_ONLY"


@pytest.mark.parametrize("role", ["V4_10_D2", "FINAL_STATE", "FOCUS", "V4_11_D0", "SAME_DAY_DOWNSTREAM"])
def test_episode_downstream_and_focus_rejected(role):
    episode, sources = valid_episode()
    sources["episode-prior"]["time_role"] = role
    with pytest.raises(InputClosureError, match="DOWNSTREAM_FEEDBACK"):
        validate(episode, sources)


@pytest.mark.parametrize("field,value,message", [
    ("episode_start", "2026-10-02", "FUTURE_OR_SAME_DAY"),
    ("prior_session_trade_date", TARGET, "FUTURE_OR_SAME_DAY"),
    ("system_available_at", "2026-10-01T13:00:00+00:00", "FUTURE_EPISODE"),
    ("episode_id", "made-up", "FAKE_EPISODE_ID"),
    ("producer_contract_id", "wrong", "WRONG_EPISODE_PRODUCER"),
    ("parameter_set_id", "wrong", "WRONG_EPISODE_PARAMETER_SET"),
])
def test_episode_negative_identity_and_time(field, value, message):
    episode, sources = valid_episode()
    episode[field] = value
    if field in ("episode_start", "prior_session_trade_date"):
        episode["episode_id"] = episode_identity(episode)
    with pytest.raises(InputClosureError, match=message):
        validate(episode, sources)


def test_same_day_revision_cannot_be_laundered_as_prior_session_episode():
    episode, sources = valid_episode()
    sources["episode-prior"]["trade_date"] = TARGET
    with pytest.raises(InputClosureError, match="SAME_DAY_REVISION_CANNOT"):
        validate(episode, sources)


def test_older_episode_is_not_immediate_prior_master_session():
    episode, sources = valid_episode()
    episode["prior_session_trade_date"] = "2026-09-28"
    with pytest.raises(InputClosureError, match="IMMEDIATE_PRIOR_MASTER_SESSION"):
        validate(episode, sources)


@pytest.mark.parametrize("field,value,message", [
    ("publication_id", "fake-publication", "EPISODE_PUBLICATION_DIGEST_MISMATCH"),
    ("knowledge_cutoff", "2026-10-01T11:00:00+00:00", "EPISODE_KNOWLEDGE_CUTOFF_MISMATCH"),
])
def test_episode_publication_identity_and_cutoff_bound(field, value, message):
    episode, sources = valid_episode()
    episode[field] = value
    with pytest.raises(InputClosureError, match=message):
        validate(episode, sources)


def test_canonical_episode_id_without_matching_upstream_row_is_not_evidence():
    episode, sources = valid_episode()
    sources["episode-prior"]["rows"] = []
    with pytest.raises(InputClosureError, match="FAKE_EPISODE_OR_PRIOR_STATE"):
        validate(episode, sources)


@pytest.mark.parametrize("field,value,message", [
    ("producer_contract_id", "wrong", "WRONG_PRIOR_EPISODE_PRODUCER"),
    ("parameter_set_id", "wrong", "WRONG_PRIOR_EPISODE_PARAMETER_SET"),
    ("system_available_at", "2026-10-01T13:00:00+00:00", "FUTURE_EPISODE_SOURCE"),
])
def test_prior_episode_publication_contract_is_bound(field, value, message):
    episode, sources = valid_episode()
    sources["episode-prior"][field] = value
    with pytest.raises(InputClosureError, match=message):
        validate(episode, sources)


@pytest.mark.parametrize("role", ["V4_10_D2", "FOCUS", "V4_11_D0", "FINAL_STATE", "SAME_DAY_DOWNSTREAM"])
def test_same_day_d2_and_focus_loo_feedback_rejected(role):
    dependency = graph()
    dependency["nodes"][0]["time_role"] = role
    with pytest.raises(InputClosureError, match="LOO_SAME_DAY_FEEDBACK"):
        validate_dependency_graph(dependency, target_date=TARGET, cutoff=CUTOFF)


def test_loo_circular_dependency_detected():
    dependency = graph()
    dependency["nodes"][0]["dependencies"] = ["loo"]
    with pytest.raises(InputClosureError, match="CIRCULAR"):
        validate_dependency_graph(dependency, target_date=TARGET, cutoff=CUTOFF)


@pytest.mark.parametrize("field,value,message", [
    ("trade_date", "2026-10-01", "LOO_FUTURE_INPUT_REJECTED"),
    ("system_available_at", "2026-10-01T13:00:00+00:00", "LOO_FUTURE_INPUT_REJECTED"),
    ("pure_upstream", False, "LOO_PURE_UPSTREAM_PROOF_REQUIRED"),
    ("publication_id", None, "LOO_VERSIONED_PUBLICATION_REQUIRED"),
])
def test_loo_cutoff_and_producer_proof_fail_closed(field, value, message):
    dependency = graph()
    dependency["nodes"][0][field] = value
    with pytest.raises(InputClosureError, match=message):
        validate_dependency_graph(dependency, target_date=TARGET, cutoff=CUTOFF)


def test_disconnected_feedback_node_is_not_hidden():
    dependency = graph()
    bad = dict(dependency["nodes"][0], node_id="hidden", time_role="FOCUS")
    dependency["nodes"].append(bad)
    with pytest.raises(InputClosureError, match="LOO_SAME_DAY_FEEDBACK"):
        validate_dependency_graph(dependency, target_date=TARGET, cutoff=CUTOFF)


def test_pure_graph_proof_does_not_silently_promote_frozen_loo_role():
    proof = validate_dependency_graph(graph(), target_date=TARGET, cutoff=CUTOFF)
    assert proof["acyclic"] and proof["pure_upstream"]
    assert not proof["formal_candidate_admission"]


@pytest.mark.parametrize("scenario", ["STRONG_PULLBACK", "TREND_CONTINUE"])
def test_diagnostic_only_cannot_enter_formal_d0(scenario):
    with pytest.raises(InputClosureError, match="CANNOT_ENTER_FORMAL_D0"):
        require_formal_scenario(scenario, scenario_capability_matrix(r3a_sealed=True))


def test_r3a_dependency_is_explicit_per_scenario():
    matrix = scenario_capability_matrix()
    assert matrix["LAUNCH_CONFIRM"]["capability"] == "BLOCKED_UPSTREAM"
    assert matrix["RECOVERY_TURN"]["capability"] == "BLOCKED_UPSTREAM"
    sealed = scenario_capability_matrix(r3a_sealed=True)
    require_formal_scenario("LAUNCH_CONFIRM", sealed)
    require_formal_scenario("RECOVERY_TURN", sealed)


def test_common_safety_does_not_replace_exact_individual_facts():
    assert set(safety_predicates({"COMMON_SAFETY": {"quality": "KNOWN", "value": True}}).values()) == {None}
    facts = {"structure_break_v3": {"quality": "KNOWN", "value": False},
        "extended_v3": {"quality": "UNKNOWN", "value": False},
        "first_day_damage": {"quality": "KNOWN", "value": True},
        "severe_drop": {"quality": "KNOWN", "value": False}}
    assert safety_predicates(facts) == {"NOT_STRUCTURE_BREAK": True, "NOT_EXTENDED": None,
        "NOT_FIRST_DAY_DAMAGE": False, "NOT_SEVERE_DROP": True}


def test_diagnostic_facts_are_unknown_never_fake_false():
    for field in DIAGNOSTIC_FIELDS:
        fact = diagnostic_fact(field, trade_date=TARGET, cutoff=CUTOFF, source_publication_id="closure-contract")
        assert fact["value"] is None and fact["quality"] == "UNKNOWN"
        assert fact["acceptance"] == "DIAGNOSTIC_ONLY"
