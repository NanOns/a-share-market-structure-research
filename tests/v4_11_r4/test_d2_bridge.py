"""Isolated file-issuer fixtures; no fixture is a market publication."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from src.v4 import confirmation_d2_candidate_r4 as bridge
from src.v4.state_identity import digest


def put(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, sort_keys=True) + "\n").encode()
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)
    return dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


@pytest.fixture
def candidate_context(tmp_path, monkeypatch):
    original_root = bridge.ROOT
    for name in ("input_provenance", "input_schema", "output_schema"):
        source = original_root / f"config/v4_10_{name}_r1_2.json"
        target = tmp_path / source.relative_to(original_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    monkeypatch.setattr(bridge, "ROOT", tmp_path)
    bridge._read.cache_clear()
    bridge.candidate_policy.cache_clear()
    refs = {}
    refs["accepted_calendar"] = put(tmp_path, "fixture/calendar_source.json", {"session_dates": ["2026-09-29", "2026-09-30"]})
    refs["r3a"] = put(tmp_path, "fixture/r3a.json", {"status": "V4_11_R4A_ADJUSTMENT_BASIS_REPAIR_CANDIDATE_READY"})
    refs["r3b"] = put(tmp_path, "fixture/r3b.json", {"status": "V4_11_R3B_EPISODE_SAFETY_LOO_CANDIDATE_READY"})
    refs["data"] = put(tmp_path, "fixture/raw_source.json", {"scope": "DISPOSABLE_ISSUER_BOUNDARY_FIXTURE_NOT_MARKET_ACCEPTANCE"})
    calendar = dict(producer_contract_id="MARKET_CALENDAR_V1", mode=bridge.MODE,
        lineage_id="DISPOSABLE_CANDIDATE_CALENDAR_FIXTURE", source_bindings=[refs["accepted_calendar"]],
        sessions=[dict(trade_date=day, session_index=i) for i,day in enumerate(("2026-09-29", "2026-09-30"))])
    calendar["publication_id"] = "V4_11_R4B_CALENDAR:" + digest(calendar)
    refs["calendar"] = put(tmp_path, "fixture/calendar_candidate.json", calendar)
    # The isolated issuer root contains the exact real reducer source files.
    runtime_refs = {}
    for module, name in ((bridge.research_state, "research_state.py"), (bridge.state_provenance, "state_provenance.py")):
        source = Path(module.__file__)
        target = tmp_path / "fixture" / name
        shutil.copyfile(source, target)
        data = target.read_bytes()
        runtime_refs[name] = dict(path="fixture/" + name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        monkeypatch.setattr(module, "__file__", str(target))
    put(tmp_path, bridge.CONFIG, dict(contract_id=bridge.CONTRACT, permissions=bridge.PERMISSIONS,
        r4a_seal=refs["r3a"], r3b_seal=refs["r3b"], accepted_calendar_source=refs["accepted_calendar"],
        accepted_reducer_source=runtime_refs["research_state.py"],
        accepted_provenance_source=runtime_refs["state_provenance.py"], allowed_source_bindings=[refs["data"]]))

    def make(*, day="2026-09-29", prior=None, confirmed="TRUE"):
        index = 0 if day == "2026-09-29" else 1
        fields = {}
        for field,definition in bridge.candidate_policy()["fields"].items():
            value = {"CONFIRMED": confirmed, "PREWATCH": "FALSE", "SEED": "TRUE", "core_price_damage": "FALSE",
                "scenario": "LAUNCH_CONFIRM", "suspended": "FALSE", "delta3": 0, "risk": "LOW"}.get(field, "UNKNOWN")
            status = "IMPLEMENTED" if definition["implemented"] else "NOT_IMPLEMENTED"
            if field in ("WARM", "dq5") or field in ("frozen_invalidation", "episode_invalidation_contract_id") and prior is None:
                status = "NOT_APPLICABLE"
            fields[field] = bridge.candidate_envelope(field, value, status, session_index=index if definition["time_role"] == "T" else index-1,
                trade_date=day if definition["time_role"] == "T" else "2026-09-29",
                system_available_at="2026-10-01T11:00:00+00:00")
        manifest = bridge.seal_fact_manifest(dict(contract_id="V4_11_R4B_STATE_INPUT_FACT_PUBLICATION_V1",
            mode=bridge.MODE, accepted=False, AS_RECORDED=False, knowledge_lineage="RECONSTRUCTED_CORRECTED",
            trade_date=day, calendar_publication_id=calendar["publication_id"], source_bindings=[refs["data"]],
            rows=[dict(entity_id="fixture-entity", entity_type="STOCK", fields={k:{n:v for n,v in f.items() if n != "publication_id"}
                for k,f in fields.items() if f["status"] == "IMPLEMENTED"})]))
        source_ref = put(tmp_path, "fixture/facts_" + day + ".json", manifest)
        for field in fields.values():
            if field["status"] == "IMPLEMENTED":
                field["publication_id"] = manifest["publication_id"]
        source_set = put(tmp_path, "fixture/source_set_" + day + ".json", dict(contract_id="V4_11_R4B_D2_SOURCE_SET_V1",
            mode=bridge.MODE, accepted=False, permissions=bridge.PERMISSIONS, r4a_seal=refs["r3a"], r3b_seal=refs["r3b"],
            calendar=refs["calendar"], publications=[source_ref]))
        authority = json.loads((tmp_path / bridge.CONFIG).read_bytes())
        authority["authorized_source_sets"] = authority.get("authorized_source_sets", []) + [source_set]
        put(tmp_path, bridge.CONFIG, authority)
        x = bridge.input_skeleton(entity_id="fixture-entity", trade_date=day, session_index=index,
            cutoff="2026-10-01T12:00:00+00:00", calendar_manifest=calendar, fields=fields,
            prior_state=prior["rows"][0] if prior else None, prior_publication_id=prior["publication_id"] if prior else None)
        return x, source_set
    return tmp_path, refs, make


def refresh(x):
    x["input_publication_manifest_digest"] = digest(dict(input_publication_ids=x["input_publication_ids"], fields=x["input_provenance"]))


def test_real_candidate_mode_uses_exact_rules_without_accepted_or_synthetic_namespace(candidate_context):
    root, refs, make = candidate_context
    x, source_set = make()
    pub = bridge.candidate_d2_publication([x], producer_set=source_set)
    row = pub["rows"][0]
    assert row["maturity"] == "CONFIRMED" and row["tracking"] == "ACTIVE"
    assert row["mode"] == bridge.MODE and row["publication_id"].startswith(bridge.ROW_PREFIX)
    assert pub["accepted"] is False and pub["AS_RECORDED"] is False
    assert pub["bootstrap_status"] == "LEFT_CENSORED_NO_PRIOR_PUBLICATION"
    assert bridge.verify_candidate_d2_publication(pub, producer_set=source_set) == pub["rows"]


def test_real_prior_d2_file_is_frozen_and_v4_12_missing_stays_unknown(candidate_context):
    root, refs, make = candidate_context
    x, sources = make()
    prior = bridge.candidate_d2_publication([x], producer_set=sources)
    prior_ref = put(root, "fixture/prior_d2.json", prior)
    x2, sources2 = make(day="2026-09-30", prior=prior)
    current = bridge.candidate_d2_publication([x2], producer_set=sources2, prior_binding=prior_ref, prior_publication=prior)
    row = current["rows"][0]
    assert row["maturity"] == "CONFIRMED" and row["state_freshness"] == "STALE"
    assert row["final_eligibility"] == "UNKNOWN" and "frozen_invalidation" in row["unknown_predicates"]
    assert row["episode_id"] == prior["rows"][0]["episode_id"]


@pytest.mark.parametrize("mode", ["SYNTHETIC_CONTRACT_VECTOR", "ACCEPTED_FACT_INTERFACE"])
def test_legacy_modes_cannot_enter_candidate_admission(candidate_context, mode):
    root, refs, make = candidate_context
    x, sources = make()
    x["mode"] = mode
    with pytest.raises(ValueError, match="REAL_CANDIDATE_D2_INPUT_REQUIRED"):
        bridge.candidate_d2_publication([x], producer_set=sources)


def test_self_attested_field_change_rejected_despite_new_input_digest(candidate_context):
    root, refs, make = candidate_context
    x, sources = make()
    fact = x["input_provenance"]["CONFIRMED"]
    fact["value"] = "FALSE"
    fact["source_field_payload"]["value"] = "FALSE"
    fact["source_output_digest"] = digest(fact["source_field_payload"])
    refresh(x)
    with pytest.raises(ValueError, match="FIELD_NOT_IN_SEALED_SOURCE"):
        bridge.candidate_d2_publication([x], producer_set=sources)


@pytest.mark.parametrize("field,new_value,message", [
    ("producer_contract_id", "WRONG", "WRONG_FIELD_PRODUCER"),
    ("producer_parameter_set_id", "WRONG", "WRONG_FIELD_PRODUCER"),
    ("status", "SYNTHETIC", "SYNTHETIC_OR_INVALID_FIELD_STATUS"),
])
def test_producer_parameter_and_synthetic_envelope_rejected(candidate_context, field, new_value, message):
    root, refs, make = candidate_context
    x, sources = make()
    x["input_provenance"]["CONFIRMED"][field] = new_value
    refresh(x)
    with pytest.raises(ValueError, match=message):
        bridge.candidate_d2_publication([x], producer_set=sources)


def test_bare_model_boundary_rejected(candidate_context):
    root, refs, make = candidate_context
    x, sources = make()
    x["model_boundary"] = True
    with pytest.raises(ValueError, match="MODEL_BOUNDARY"):
        bridge.candidate_d2_publication([x], producer_set=sources)


def test_serialized_prior_is_not_trusted_without_byte_bound_real_publication(candidate_context):
    root, refs, make = candidate_context
    x, sources = make()
    prior = bridge.candidate_d2_publication([x], producer_set=sources)
    x2, sources2 = make(day="2026-09-30", prior=prior)
    with pytest.raises(ValueError, match="PRIOR_NOT_IN_SEALED_REAL_D2_PUBLICATION"):
        bridge.candidate_d2_publication([x2], producer_set=sources2)


def test_candidate_d2_row_tampering_rejected_by_rule_reexecution(candidate_context):
    root, refs, make = candidate_context
    x, sources = make()
    pub = bridge.candidate_d2_publication([x], producer_set=sources)
    pub["rows"][0]["final_eligibility"] = "FALSE"
    with pytest.raises(ValueError, match="RULE_REEXECUTION"):
        bridge.verify_candidate_d2_publication(pub)


def test_byte_bound_source_tampering_rejected(candidate_context):
    root, refs, make = candidate_context
    x, sources = make()
    path = root / refs["data"]["path"]
    temporary = path.with_suffix(".tmp")
    temporary.write_text("{}", encoding="utf8")
    temporary.replace(path)
    with pytest.raises(ValueError, match="BYTE_BINDING_MISMATCH"):
        bridge.candidate_d2_publication([x], producer_set=sources)


def test_self_sealed_source_set_not_in_external_authority_is_rejected(candidate_context):
    root, refs, make = candidate_context
    x, sources = make()
    fake = deepcopy(json.loads((root / sources["path"]).read_bytes()))
    fake["caller_self_attestation"] = True
    untrusted = put(root, "fixture/untrusted_source_set.json", fake)
    with pytest.raises(ValueError, match="NOT_AUTHORIZED_OUT_OF_BAND"):
        bridge.candidate_d2_publication([x], producer_set=untrusted)


def test_same_day_revision_cannot_become_prior_d2(candidate_context):
    root, refs, make = candidate_context
    x, sources = make()
    prior = bridge.candidate_d2_publication([x], producer_set=sources)
    prior_ref = put(root, "fixture/prior_d2.json", prior)
    x2, sources2 = make(prior=prior)
    with pytest.raises(ValueError, match="SAME_DAY_OR_NON_PRIOR_SESSION"):
        bridge.candidate_d2_publication([x2], producer_set=sources2, prior_binding=prior_ref)


@pytest.mark.parametrize("field,new_value,message", [
    ("system_available_at", "2026-10-01T13:00:00+00:00", "FUTURE_FIELD"),
    ("time_role", "FOCUS", "FIELD_POLICY"),
])
def test_admission_rejects_future_and_focus_even_in_issuer_envelope(candidate_context, field, new_value, message):
    root, refs, make = candidate_context
    x, sources = make()
    context = bridge.admission_context(sources)
    fact = x["input_provenance"]["CONFIRMED"]
    fact[field] = new_value
    authority_row = context["manifests"][fact["publication_id"]][1][("fixture-entity", "STOCK")]
    authority_row["fields"]["CONFIRMED"][field] = new_value
    refresh(x)
    with pytest.raises(ValueError, match=message):
        bridge._validate_inputs(x, context)


def test_frozen_invalidation_cannot_be_fake_false_to_avoid_unknown(candidate_context):
    root, refs, make = candidate_context
    x, sources = make()
    x["input_provenance"]["frozen_invalidation"]["value"] = "FALSE"
    x["input_provenance"]["frozen_invalidation"]["quality"] = "KNOWN"
    refresh(x)
    with pytest.raises(ValueError, match="UNAVAILABLE_FACT_MUST_STAY_UNKNOWN"):
        bridge.candidate_d2_publication([x], producer_set=sources)


def test_adapter_ast_diff_is_limited_to_six_explicit_admission_identity_changes():
    evidence = bridge.adapter_ast_evidence()
    assert set(evidence["mechanical_whitelist_changes"].values()) == {1}
    assert all(item["normalized_business_AST_exact"] for item in evidence["business_AST_comparisons"].values())
    assert evidence["exact_rule_order"] and evidence["exact_business_thresholds"]
    assert evidence["candidate_business_consumer_external_acceptance"] is False
