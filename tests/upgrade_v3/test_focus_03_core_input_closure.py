from dataclasses import replace
from datetime import date

import pytest

from src.focus_tracker.contracts import FocusKey, source_item_digest
from src.focus_tracker.core_input_closure import (ObservationItem,
                                                  validate_core_input_closure)
from src.focus_tracker.daily_plan import PlannedDay
from src.focus_tracker.input_manifest import AuthorityBindings, build_manifest
from src.focus_tracker.lifecycle import Decision
from src.focus_tracker.materialize import PathRequest, StockFact
from src.focus_tracker.observation import assemble_observation
from src.focus_tracker.predicates import Tri
from src.focus_tracker.source_reader import AcceptedSources, SourceRow


DAY = date(2026, 9, 22)
V3 = "RESEARCH_V3_PREVIEW_6_CURRENT_FOCUS_COMPLETE"


def _batch():
    key = FocusKey("V3_SHORTLIST_STOCK", "STOCK", "SH.600001", "V3_SHORTLIST")
    facts = {"list_type": "CURRENT_FOCUS"}
    row = SourceRow(key, DAY, "CURRENT", "row-1",
                    source_item_digest("row-1", V3, facts), V3, 1,
                    "CURRENT_FOCUS", facts)
    sources = AcceptedSources(DAY, "publication", "v3-run", None,
                              {key.source_family: "COMPLETE"}, (row,), "b" * 64)
    decision = Decision(key, "CURRENT", "NEW", "episode-1", None, (),
                        "SOURCE_MEMBERSHIP")
    plan = PlannedDay(DAY, (decision,), (key,),
                      (PathRequest(key.entity_id, DAY),), (), "c" * 64)
    stock = StockFact(key.entity_id, DAY, DAY, "READY", "BAR", "10.00",
                      "0", "0", "0", "0", "0", "local-v1", "d" * 64)
    observation = assemble_observation(decision=decision, source_contract_id=V3,
                                       stock_fact=stock, predicate_facts={},
                                       invalidation=Tri.UNKNOWN)
    bindings = AuthorityBindings("publication", "PUBLICATION_ID_ONLY", None,
                                 "snapshot", "membership", "parameter",
                                 None, None, None, None, None, None)
    manifest = build_manifest(
        sources=sources, plan=plan, bindings=bindings, calendar=(DAY,),
        calendar_artifact_sha256="e" * 64, normalized_sha256="e" * 64,
        stock_facts=(stock,), baskets={}, strengths={},
        state_contract_id="FOCUS_PATH_STATE_V1", parameter_set_id="params-v1",
        implementation_digest="f" * 64, dependency_lock_hash="0" * 64,
        evaluation_basis="HISTORICAL_RECONSTRUCTED",
        calendar_scope="MASTER_COMPLETE", dependency_lock_kind="VERSIONED_LOCK")
    return manifest, sources, plan, (stock,), (ObservationItem(key, observation),)


def test_exact_batch_has_stable_closure_digest():
    manifest, sources, plan, stocks, observations = _batch()
    result = validate_core_input_closure(manifest=manifest, sources=sources,
                                         plan=plan, stock_facts=stocks,
                                         observations=observations)
    assert (result.source_count, result.observation_count,
            result.stock_fact_count) == (1, 1, 1)
    assert len(result.input_digest) == 64


def test_missing_or_duplicate_observation_blocks_core_batch():
    manifest, sources, plan, stocks, observations = _batch()
    with pytest.raises(ValueError, match="observation set"):
        validate_core_input_closure(manifest=manifest, sources=sources,
                                    plan=plan, stock_facts=stocks, observations=())
    with pytest.raises(ValueError, match="duplicate core observation"):
        validate_core_input_closure(manifest=manifest, sources=sources,
                                    plan=plan, stock_facts=stocks,
                                    observations=observations * 2)


def test_pending_followup_not_covered_by_plan_blocks_publication():
    manifest, sources, plan, stocks, observations = _batch()
    other = FocusKey("V3_SHORTLIST_STOCK", "STOCK", "SH.600002", "V3_SHORTLIST")
    bad_plan = replace(plan, pending_followup_keys=(other,))
    with pytest.raises(ValueError, match="pending follow-up entity missing"):
        validate_core_input_closure(manifest=manifest, sources=sources,
                                    plan=bad_plan, stock_facts=stocks,
                                    observations=observations)


def test_changed_source_or_stock_digest_blocks_core_batch():
    manifest, sources, plan, stocks, observations = _batch()
    bad_source = replace(sources.rows[0], source_item_digest="0" * 64)
    with pytest.raises(ValueError, match="source row identity"):
        validate_core_input_closure(manifest=manifest,
                                    sources=replace(sources, rows=(bad_source,)),
                                    plan=plan, stock_facts=stocks,
                                    observations=observations)
    with pytest.raises(ValueError, match="stock fact digest"):
        validate_core_input_closure(manifest=manifest, sources=sources,
                                    plan=plan,
                                    stock_facts=(replace(stocks[0], input_digest="1" * 64),),
                                    observations=observations)
