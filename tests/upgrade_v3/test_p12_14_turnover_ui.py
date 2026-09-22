import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pandas as pd

from workbench_online.base import FetchResult
from workbench_service.research_bundle_v3_3 import activate_bundle, build_bundle
from workbench_service.today_research_bundle import TodayResearchBundleReader
from workbench_service.turnover_enrichment_service import TurnoverEnrichmentService
from workbench_service import app


ROOT = Path(__file__).resolve().parents[2]


def _service(tmp_path, fetcher):
    daily = tmp_path / "data/normalized"
    daily.mkdir(parents=True)
    pd.DataFrame([{
        "security_id": "SZ.002491", "date": "2026-09-15", "raw_close": 22.23,
        "raw_amount": 5_840_461_313.31, "raw_volume": 267_049_400,
    }]).to_parquet(daily / "adjusted_daily.parquet", index=False)
    identity = {"publication_id": "pub", "snapshot_id": "snap", "membership_snapshot_id": "members", "research_run_id": "run", "parameter_hash": "params", "dependency_lock_hash": "deps", "trade_date": "2026-09-15"}
    built = build_bundle(tmp_path / "bundles", identity, [{"security_id": "SZ.002491"}], {"factor": "v1"})
    pointer = tmp_path / "current.json"
    activate_bundle(Path(built["path"]), pointer)
    reader = TodayResearchBundleReader(tmp_path, pointer)
    return TurnoverEnrichmentService(tmp_path, reader, fetcher=fetcher), built


def test_ui_service_binds_once_and_reuses_failure_or_success_cache(tmp_path):
    calls = []
    def fetcher(ids, policy):
        calls.append(list(ids))
        result = FetchResult("a", "2026-09-16T01:00:00+00:00", 200, "application/json", b"{}", "url")
        return result, [{"source_id": "EASTMONEY_QUOTES_LATEST", "security_id": "SZ.002491", "price": 22.23, "amount": 5_840_461_313.31, "volume": 267_049_400, "turnover_rate": .227, "observed_at_utc": result.received_at_utc}]
    service, built = _service(tmp_path, fetcher)
    first = service.load(expected_digest=built["output_digest"])
    second = service.load(expected_digest=built["output_digest"])
    assert first["status"] == "AVAILABLE" and first["items"][0]["turnover_rate"] == .227
    assert first["cached"] is False and second["cached"] is True
    assert len(calls) == 1
    assert first["guardrails"]["core_score_or_category_rank_changed"] is False
    assert first["enhanced_items"][0]["turnover_enhancement_status"] == "FACT_AVAILABLE"
    assert first["layer_status"] == "BYPASSED"


def test_ui_service_source_failure_is_visible_and_nonblocking(tmp_path):
    def failed(*_args, **_kwargs):
        raise TimeoutError("secret detail must not leak")
    service, _ = _service(tmp_path, failed)
    result = service.load()
    assert result["status"] == "UNAVAILABLE"
    assert result["source_error"] == "TimeoutError"
    assert result["items"][0]["turnover_rate"] is None
    assert result["guardrails"]["local_pipeline_blocked"] is False


def test_page_api_reads_materialized_enhancement_without_calling_source(tmp_path):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("page read must not fetch online")
    service, built = _service(tmp_path, forbidden)
    store = tmp_path / "data/turnover_shadow_v3_3/2026-09-15"
    store.mkdir(parents=True)
    (store / "observation.json").write_text(json.dumps({
        "bundle_digest": built["output_digest"], "captured_at_utc": "2026-09-16T01:00:00Z",
        "requested_count": 1, "bound_count": 1, "source_error": None, "observation_digest": "obs",
        "items": [{"security_id": "SZ.002491", "trade_date": "2026-09-15", "turnover_rate": .227,
                   "turnover_basis": "TENCENT_FLOAT_SHARE_BASIS", "source_id": "TENCENT_QUOTES_LATEST"}],
    }), encoding="utf-8")
    result = service.load_materialized(expected_digest=built["output_digest"])
    assert result["status"] == "AVAILABLE"
    assert result["materialized"] is True
    assert result["guardrails"]["online_request_from_page"] is False
    assert result["enhanced_items"][0]["turnover_enhanced_rank"] is None


def test_ui_service_enriches_every_supported_candidate_in_sequential_batches(tmp_path):
    ids = [f"SZ.{index:06d}" for index in range(56)]
    daily = tmp_path / "data/normalized"
    daily.mkdir(parents=True)
    pd.DataFrame([{"security_id": value, "date": "2026-09-15", "raw_close": 10.0, "raw_amount": 1000.0, "raw_volume": 100.0} for value in ids]).to_parquet(daily / "adjusted_daily.parquet", index=False)
    identity = {"publication_id": "pub", "snapshot_id": "snap", "membership_snapshot_id": "members", "research_run_id": "run", "parameter_hash": "params", "dependency_lock_hash": "deps", "trade_date": "2026-09-15"}
    candidates = [{"security_id": value, "primary_category": "A", "selection_mode": "X", "rank_status": "QUALIFIED_UNRANKED"} for value in ids]
    built = build_bundle(tmp_path / "bundles", identity, candidates, {"factor": "v1"})
    pointer = tmp_path / "current.json"
    activate_bundle(Path(built["path"]), pointer)
    calls = []
    def fetcher(batch, _policy):
        calls.append(list(batch))
        result = FetchResult(f"sha-{len(calls)}", "2026-09-16T01:00:00+00:00", 200, "application/json", b"{}", "url")
        return result, [{"source_id": "EASTMONEY_QUOTES_LATEST", "security_id": value, "price": 10.0, "amount": 1000.0, "volume": 100.0, "turnover_rate": .01 + index / 10000, "observed_at_utc": result.received_at_utc} for index, value in enumerate(batch)]
    service = TurnoverEnrichmentService(tmp_path, TodayResearchBundleReader(tmp_path, pointer), fetcher=fetcher)
    result = service.load(expected_digest=built["output_digest"])
    assert [len(batch) for batch in calls] == [50, 6]
    assert result["request"] == {"candidate_count": 56, "planned_batch_count": 2, "completed_batch_count": 2, "batch_size": 50, "retries": 0}
    assert len(result["enhanced_items"]) == 56
    assert result["counts"] == {"BOUND": 56}


def test_page_exposes_turnover_context_and_core_rank_guardrail():
    html = (ROOT / "src/workbench_service/static/v2/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/workbench_service/static/v2/v3-unified.js").read_text(encoding="utf-8")
    assert 'id="v3-load-turnover"' in html
    assert "today-turnover?bundle_digest=" in script
    assert "data-turnover-stock" in script
    assert "换手判断" in html + script
    assert "turnover_priority_tier" in script
    assert "不改核心V3.3评分和类别排名" in html + script
    assert "换手率证据" in script


def test_http_turnover_route_is_not_misread_as_security_detail(tmp_path, monkeypatch):
    from workbench_db import WorkbenchRepository

    expected = {"api_contract": "P12_14_EASTMONEY_CANDIDATE_TURNOVER_V1", "status": "UNAVAILABLE", "items": []}
    class FakeTurnover:
        def __init__(self, *_args, **_kwargs):
            pass
        def load_materialized(self, *, expected_digest=""):
            return {**expected, "expected_digest": expected_digest}

    monkeypatch.setattr(app, "TurnoverEnrichmentService", FakeTurnover)
    database = tmp_path / "api.duckdb"
    with WorkbenchRepository(ROOT, database):
        pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(ROOT, database))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/v3/research/today-turnover?bundle_digest=abc"
        result = json.load(urllib.request.urlopen(url))
        assert result["api_contract"] == expected["api_contract"]
        assert result["expected_digest"] == "abc"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
