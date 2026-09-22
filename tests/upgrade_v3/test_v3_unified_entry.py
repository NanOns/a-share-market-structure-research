import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path

from workbench_db import WorkbenchRepository
import workbench_service.app as app


ROOT = Path(__file__).resolve().parents[2]


def test_v3_is_the_single_unified_workbench_entry(tmp_path):
    db = tmp_path / "entry.duckdb"
    with WorkbenchRepository(ROOT, db):
        pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(ROOT, db))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        response = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/")
        page = response.read().decode("utf-8")
        assert response.status == 200
        assert 'data-workbench-mode="v3"' in page
        assert 'data-workbench-base="/"' in page
        assert "<title>统一研究工作台</title>" in page
        assert "V3 单一入口" not in page
        for label in ("研究首页", "板块研究", "个股研究", "联动筛选", "市场与事件", "数据 / 运维"):
            assert label in page
        assert "旧功能 / 历史工作台" not in page
        assert "/v2?page=" not in page
        assert "/v2/v3-unified.js" in page
        assert "一键生成本地数据" in page
        assert "id=\"v3-build-research\"" in page
        assert "进入数据能力" in page
        assert "href=\"/operations\"" in page
        assert "进入运维中心" in page
        assert "今日总览 · 本地收盘数据" in page
        assert 'id="v3-local-market"' in page
        assert 'id="v3-local-sectors"' in page
        assert 'data-v3-page="linkage"' not in page
        assert '[data-workbench-mode="v3"] #v3-legacy-overview { display: none; }' in page
        assert 'href="/v3/online"' not in page
        assert "在线事件与热度工作台" in page
        assert 'id="v3-online-trade-date"' in page
        assert '<option value="super_stock" selected>强势股</option>' in page
        assert '<option value="limit_up">涨停</option>' not in page
        assert 'id="v3-online-pool-refresh"' not in page
        assert 'id="v3-online-topic-members"' not in page
        assert "刷新全部在线数据" in page
        assert 'href="/v3/events"' not in page
        assert 'class="panel local-limit-panel"' in page
        assert '[data-workbench-mode="v3"] .hot-rank-panel, [data-workbench-mode="v3"] .local-limit-panel { display: none; }' in page
        script = (ROOT / "src/workbench_service/static/v2/v3-unified.js").read_text(encoding="utf-8")
        assert "post('/api/jobs'" in script
        assert "get('/api/jobs?job_id='" in script
        assert "get('/api/v3/research/today?page='" in script
        assert "v3-priority-table" in script
        assert "structure_phase" in script
        assert "板块生命周期 · 前瞻与风险" not in page
        assert "loadLifecycle" not in script
        assert "expected_trade_date" in script
        assert "resolveOnlineTradeDate().then" in script
        assert "window.location.reload()" in script
        assert "X-CSRF-Token" in script
        assert "data-v3-sector-id" in script
        assert "data-v3-security-id" in script
        assert "openSectorModal(button.dataset.v3SectorId" in script
        assert "openStockModal(button.dataset.v3SecurityId" in script
        assert "get('/api/market/cycle?publication_id='" in script
        assert "/api/v3/online/latest-trade-date" in script
        assert "loadPool(1);" in script
        assert "modal(topicName + ' · 在线成员'" in script
        assert "source_enter_time" in script and "source_description" in script
        assert "v3-online-table-scroll" in script and "v3-pool-reason" in script
        assert "v3-online-table v3-pool-table" in script
        assert "sort=LIMIT_TIME" in script and "data-ladder-next" in script
        assert "北向（来源显示）" not in script
        assert "riseFall.limit_up" in script and "turnover.now" in script
        assert "查看全文" not in script
        assert "page_size=30" in script and "data-pool-next" in script
        assert "龙字诀" not in page + script
        assert "龙字决" not in page + script
        old_v1 = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/v1").read().decode("utf-8")
        old_v2 = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/v2").read().decode("utf-8")
        assert '<iframe id="workbench"' in old_v1
        assert 'data-workbench-mode="v2"' in old_v2
        assert "MIXED: '混合排列'" in script
        assert "场景判定证据" in script and "PULLBACK_EPISODE_CONFIRMED" in script
        assert "maximumFractionDigits: 2" in script
        assert "\\d{3,}" in script
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_job_status_route_does_not_acquire_page_database_request_scope(tmp_path, monkeypatch):
    db = tmp_path / "jobs.duckdb"
    with WorkbenchRepository(ROOT, db):
        pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(ROOT, db))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        def forbidden_scope(_self):
            raise AssertionError("job status opened page DB request scope")
        monkeypatch.setattr(app.Api, "request_scope", forbidden_scope)
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/api/jobs?job_id=missing")
        except urllib.error.HTTPError as error:
            assert error.code in (400, 404)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
