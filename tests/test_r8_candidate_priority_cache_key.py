from types import SimpleNamespace

import pytest

from workbench_analysis.r43_owner_replay import ref
from workbench_service.core_product_bff_r1 import (
    CoreProductBFFR1,
    _candidate_priority_cache_key,
)
from workbench_db import forward_r7_store


def inputs():
    stock = {"path": "core/2026-10-21.jsonl.gz", "sha256": "a" * 64}
    sector = {"path": "sector/2026-10-21.jsonl.gz", "sha256": "b" * 64}
    lifecycle = {
        "candidate_digest": "c" * 64,
        "producer_sha256": "d" * 64,
        "parameter_sha256": "e" * 64,
    }
    return stock, sector, lifecycle


def test_priority_cache_key_is_stable_for_identical_owner_closure():
    stock, sector, lifecycle = inputs()
    first = _candidate_priority_cache_key("token", "2026-10-21", stock, sector,
                                          "f" * 64, "1" * 64, lifecycle)
    second = _candidate_priority_cache_key("token", "2026-10-21", stock, sector,
                                           "f" * 64, "1" * 64, lifecycle)
    assert first == second


def test_priority_cache_key_invalidates_when_a_source_or_rule_changes():
    stock, sector, lifecycle = inputs()
    original = _candidate_priority_cache_key("token", "2026-10-21", stock, sector,
                                             "f" * 64, "1" * 64, lifecycle)

    replaced_stock = dict(stock, sha256="2" * 64)
    changed_parameter = _candidate_priority_cache_key("token", "2026-10-21", stock, sector,
                                                      "3" * 64, "1" * 64, lifecycle)
    changed_lifecycle = dict(lifecycle, candidate_digest="4" * 64)
    changed_window = _candidate_priority_cache_key("token", "2026-10-21", stock, sector,
                                                   "f" * 64, "1" * 64, changed_lifecycle)

    assert _candidate_priority_cache_key("token", "2026-10-21", replaced_stock, sector,
                                         "f" * 64, "1" * 64, lifecycle) != original
    assert changed_parameter != original
    assert changed_window != original


def test_priority_source_replacement_under_same_binding_fails_closed(tmp_path):
    days = ["2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20", "2026-10-21"]
    owners = {}
    for day in days:
        owners[day] = {}
        domains = ("core", "adjusted", "sector", "rotation", "focus", "prewatch", "forward") if day == days[-1] else ("sector", "rotation")
        for domain in domains:
            path = tmp_path / "owners" / day / f"{domain}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"version":1}', encoding="utf-8")
            owners[day][domain] = ref(tmp_path, path)

    api = SimpleNamespace(root=tmp_path, candidate={"published_sessions": days, "owners": owners})
    bff = CoreProductBFFR1(api, None)
    bff._verify_candidate_priority_bindings(days[-1])

    changed = tmp_path / owners[days[-1]]["core"]["path"]
    changed.write_text('{"version":2}', encoding="utf-8")
    with pytest.raises(ValueError, match="CORRECTED_INPUT_DIGEST_MISMATCH"):
        bff._verify_candidate_priority_bindings(days[-1])


def test_priority_source_missing_is_not_cached_as_success(tmp_path):
    days = ["2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20", "2026-10-21"]
    owners = {day: {"sector": {}, "rotation": {}} for day in days[:-1]}
    owners[days[-1]] = {domain: {} for domain in ("core", "adjusted", "sector", "rotation", "focus", "prewatch", "forward")}
    owners[days[-1]].pop("adjusted")
    api = SimpleNamespace(root=tmp_path, candidate={"published_sessions": days, "owners": owners})
    bff = CoreProductBFFR1(api, None)

    with pytest.raises(ValueError, match="CANDIDATE_PRIORITY_OWNER_MISSING:2026-10-21:core"):
        bff._verify_candidate_priority_bindings(days[-1])


def test_focus_reason_derivation_reuses_shared_verified_copy(tmp_path, monkeypatch):
    from workbench_analysis import r6_reason_attribution

    prior, day = "2026-10-20", "2026-10-21"
    owners = {prior: {}, day: {}}
    for session, domains in ((prior, ("focus",)),
                             (day, ("prewatch", "focus", "forward"))):
        for domain in domains:
            path = tmp_path / "owners" / session / f"{domain}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"version":1}', encoding="utf-8")
            owners[session][domain] = ref(tmp_path, path)

    api = SimpleNamespace(root=tmp_path, token="candidate-token",
                          candidate={"published_sessions": [prior, day], "owners": owners},
                          cache={}, derived_cache={})
    bff = CoreProductBFFR1(api, None)
    calls = []

    def derive(*args, **kwargs):
        calls.append((args, kwargs))
        return {"status": "READY", "items": [{"entity_id": "SEC-1"}]}

    monkeypatch.setattr(r6_reason_attribution, "candidate_d0_reason_attribution", derive)
    first = bff._candidate_focus_reason_attribution(day, ["SEC-1"])
    first["items"].clear()
    second = bff._candidate_focus_reason_attribution(day, ["SEC-1"])

    assert len(calls) == 1
    assert second["items"] == [{"entity_id": "SEC-1"}]

    changed = tmp_path / owners[day]["focus"]["path"]
    changed.write_text('{"version":2}', encoding="utf-8")
    with pytest.raises(ValueError, match="CORRECTED_INPUT_DIGEST_MISMATCH"):
        bff._candidate_focus_reason_attribution(day, ["SEC-1"])
    assert len(calls) == 1


def test_forward_pg_read_outage_fails_closed_without_zero_or_stale_data(tmp_path, monkeypatch):
    class FailingStore:
        def __init__(self, root):
            self.root = root

        def read_settlement(self, **kwargs):
            raise forward_r7_store.psycopg.OperationalError("INJECTED_PG_CONNECTION_FAILURE")

    monkeypatch.setattr(forward_r7_store, "ForwardR7Store", FailingStore)
    bff = object.__new__(CoreProductBFFR1)
    bff.api = SimpleNamespace(root=tmp_path, token="candidate-token")
    bff.envelope = lambda day, **payload: payload

    status, result = bff._forward_r7_read(
        "/api/v4/forward/settlement", {"limit": "5", "offset": "0"}, "2026-10-21")

    assert status == 200
    assert result["status"] == "ERROR"
    assert result["reason"] == "FORWARD_SETTLEMENT_PG_READ_FAILED"
    assert result["items"] is None and result["total"] is None
    assert "counts" not in result and "aggregates" not in result


def test_matured_forward_count_cache_requires_stable_append_watermark(monkeypatch):
    store = object.__new__(forward_r7_store.ForwardR7Store)
    store.schema = "v4_test_forward"
    watermark = [("dev-db", 17)]
    computations = []

    monkeypatch.setattr(store, "_matured_count_watermark", lambda: watermark[0])
    monkeypatch.setattr(store, "_read_matured_count_exact", lambda: computations.append(1) or 3260)
    cache = {}

    assert store.read_matured_count(cache=cache) == 3260
    assert store.read_matured_count(cache=cache) == 3260
    assert len(computations) == 1

    watermark[0] = ("dev-db", 18)
    assert store.read_matured_count(cache=cache) == 3260
    assert len(computations) == 2

    cache.clear()
    calls = iter([("dev-db", 18), ("dev-db", 19), ("dev-db", 19), ("dev-db", 19)])
    monkeypatch.setattr(store, "_matured_count_watermark", lambda: next(calls))
    assert store.read_matured_count(cache=cache) == 3260
    assert len(computations) == 3
    assert ("forward-r7-matured-count-v1", store.schema) not in cache
