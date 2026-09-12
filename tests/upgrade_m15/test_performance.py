from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / "src" / "workbench_service" / "static" / "v2"


def read(name: str) -> str:
    return (V2 / name).read_text(encoding="utf-8")


def test_api_has_bounded_cache_and_perf_contract():
    text = read("api.js")
    assert "CACHE_LIMIT=24" in text
    assert "CACHE_TTL_MS=30000" in text
    assert "cache:false" in text
    assert "window.WorkbenchV2Perf" in text
    assert "cache_limit:CACHE_LIMIT" in text
    assert "cache_ttl_ms:CACHE_TTL_MS" in text


def test_hot_rankings_is_request_time_only():
    text = read("api.js")
    assert "hotRankings:function(params,options){return get('/api/hot-rankings',params||{},Object.assign({cache:false},options||{}));}" in text


def test_view_requests_cancel_and_reject_stale_results():
    text = read("app.js")
    assert "function beginViewRequest(key)" in text
    assert "function cancelHiddenViewRequests(page, subpage)" in text
    assert "new AbortController()" in text
    assert "controller.abort()" in text
    assert "function viewRequestActive(key, token)" in text
    assert text.count("viewRequestActive(") >= 15
    for key in ("overview", "technical", "sectors", "mainlines", "linkage", "limit", "hot", "market"):
        assert f"viewRequestActive('{key}'" in text
    assert "cancelHiddenViewRequests(page, sectorSubpage);" in text


def test_assets_are_versioned_for_m15_04():
    text = read("index.html")
    for asset in ("styles.css", "api.js", "format.js", "table.js", "modal.js", "router.js", "app.js"):
        assert f"{asset}?v=m15-04" in text


def test_layout_keeps_only_intentional_internal_vertical_scrollers():
    text = read("styles.css")
    assert ".modal-body{overflow:auto" in text
    assert ".table-wrap{overflow-x:auto}" in text
    assert "body{overflow-y:auto" not in text
    assert "html{overflow-y:auto" not in text


def test_stage_contract_records_targets_and_degraded_evidence():
    text = (ROOT / "docs" / "M15_03_PERFORMANCE_CONTRACT_V1.md").read_text(encoding="utf-8")
    for marker in ("1440×900", "1920×1080", "p50", "p95", "800ms", "500KB", "DEGRADED_PASS", "M15-04"):
        assert marker in text
