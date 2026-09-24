from datetime import date

import pytest

from src.focus_tracker.contracts import FocusKey
from src.focus_tracker.daily_plan import PlannedDay
from src.focus_tracker.input_manifest import (AuthorityBindings, build_manifest,
                                              require_release_ready, write_manifest)
from src.focus_tracker.materialize import PathRequest, StockFact
from src.focus_tracker.source_reader import AcceptedSources, SourceRow


DAY = date(2026, 9, 22)


def _inputs():
    key = FocusKey("V3_SHORTLIST_STOCK", "STOCK", "SH.600001", "V3_SHORTLIST")
    row = SourceRow(key, DAY, "CURRENT", "row", "a" * 64,
                    "source-contract", 1, "CURRENT_FOCUS", {})
    sources = AcceptedSources(DAY, "publication", "run", None,
                              {"V3_SHORTLIST_STOCK": "COMPLETE"}, (row,), "b" * 64)
    plan = PlannedDay(DAY, (), (key,), (PathRequest("SH.600001", DAY),), (), "c" * 64)
    bindings = AuthorityBindings("publication", "PUBLICATION_ID_ONLY", None,
                                 "snapshot", "membership", "parameter",
                                 None, None, None, None, None, None)
    fact = StockFact("SH.600001", DAY, DAY, "READY", "BAR", "10.00", "0",
                     "0", "0", "0", "0", "local-v1", "d" * 64)
    return sources, plan, bindings, fact


def _build(**overrides):
    sources, plan, bindings, fact = _inputs()
    args = dict(sources=sources, plan=plan, bindings=bindings,
                calendar=(DAY,), calendar_artifact_sha256="e" * 64,
                normalized_sha256="e" * 64, stock_facts=(fact,),
                baskets={}, strengths={}, state_contract_id="state-v1",
                parameter_set_id="params-v1", implementation_digest="f" * 64,
                dependency_lock_hash="0" * 64,
                evaluation_basis="HISTORICAL_RECONSTRUCTED",
                calendar_scope="RANGE_SLICE",
                dependency_lock_kind="RUNTIME_FINGERPRINT")
    args.update(overrides)
    return build_manifest(**args)


def test_manifest_records_release_gates_and_is_immutable(tmp_path):
    manifest = _build()
    assert manifest.payload["publication_source_identity_quality"] == "PUBLICATION_ID_ONLY"
    assert "CALENDAR_RANGE_ONLY" in manifest.release_gate_reasons
    with pytest.raises(ValueError, match="release gates"):
        require_release_ready(manifest)
    output = tmp_path / "manifest.json"
    write_manifest(output_path=output, manifest=manifest)
    write_manifest(output_path=output, manifest=manifest)
    assert output.is_file()
    changed = _build(implementation_digest="1" * 64)
    with pytest.raises(ValueError, match="immutable manifest conflict"):
        write_manifest(output_path=output, manifest=changed)


def test_manifest_rejects_missing_shared_fact():
    with pytest.raises(ValueError, match="stock fact set differs"):
        _build(stock_facts=())
