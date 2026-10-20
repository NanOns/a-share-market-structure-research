import hashlib
import json
import sys
from types import ModuleType

from workbench_analysis import producer_bootstrap_v1 as producer
from workbench_analysis import producer_candidate_index_pg_v1 as pg_index


def _binding(root, relative):
    raw = (root / relative).read_bytes()
    return {"path": relative, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def _module(name, **values):
    module = ModuleType(name)
    for key, value in values.items():
        setattr(module, key, value)
    return module


def test_exact_daily_index_producer_passes_fresh_document_without_reading_file(
    monkeypatch, tmp_path
):
    root = tmp_path
    day = "2026-10-16"
    candidate_path = root / "data/v4/candidates/exact.json"
    candidate_path.parent.mkdir(parents=True)
    candidate_path.write_text(json.dumps({
        "accepted_trade_date": day,
        "exact_daily_adjustment_contract": {"contract_id": "EXACT_DAILY_V1"},
    }), encoding="utf-8")
    candidate_binding = _binding(root, "data/v4/candidates/exact.json")
    index_path = root / "data/v4/producer_candidate_index_v2.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    old_index = b'{"contract_id":"OLD","sessions":{"2026-10-15":{"stale":true}}}'
    index_path.write_bytes(old_index)

    monkeypatch.setattr(producer, "produce_daily_state", lambda *_: {"path": "state.json", "sha256": "a" * 64})
    monkeypatch.setattr(producer, "produce_daily_sector", lambda *_: {"path": "sector.json", "sha256": "b" * 64})
    monkeypatch.setattr(producer, "produce_first_observed_state", lambda *_: {"status": "SOURCE_INCOMPLETE"})
    from workbench_analysis import market_source_acquisition
    monkeypatch.setattr(market_source_acquisition, "official_sessions", lambda *_: ["2026-10-16", "2026-10-19"])
    monkeypatch.setitem(sys.modules, "workbench_analysis.full_market_state_publisher_v1",
                        _module("workbench_analysis.full_market_state_publisher_v1",
                                build=lambda **_: {"status": "SOURCE_INCOMPLETE"}))

    result = pg_index.build_review_and_display_candidates(
        root, day, candidate_binding, {"candidate": None})

    index = result["index_document"]
    entry = index["sessions"][day]
    assert index["contract_id"] == "PRODUCER_CANDIDATE_INDEX_V2"
    assert entry["head"] == candidate_binding and entry["next_session"] == "2026-10-19"
    assert entry["production"] is False
    assert entry["sector"] == {"path": "sector.json", "sha256": "b" * 64}
    assert entry["full_state"] == {"path": "state.json", "sha256": "a" * 64}
    assert entry["strict_source_failure"] == "INITIAL_CAPTURE_FAILED"
    assert entry["source_capture_failure"] is None
    assert result["index"]["source"] == "IN_MEMORY_TO_PG_OWNER"
    assert result["index"]["persisted"] is False
    assert index_path.read_bytes() == old_index


def test_executor_exact_daily_branch_consumes_producer_document_without_file_read():
    from pathlib import Path
    import inspect
    from workbench_analysis import operational_daily_executor_v1 as executor

    source = inspect.getsource(executor.derive_ready_sources)
    assert "index_document" in source
    assert "producer_candidate_index_v2.json" not in source
    assert Path("data/v4/producer_candidate_index_v2.json").name not in source
