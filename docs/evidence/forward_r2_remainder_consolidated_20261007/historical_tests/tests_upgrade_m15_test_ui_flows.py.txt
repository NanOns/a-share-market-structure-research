from pathlib import Path
import re


ROOT = Path(__file__).parents[2]
V2 = ROOT / "src/workbench_service/static/v2"


def test_m15_v2_has_exactly_six_first_level_routes_and_secondary_pages():
    index = (V2 / "index.html").read_text(encoding="utf-8")
    pages = re.findall(r'class="nav-item(?: active)?" data-page="([^"]+)"', index)
    assert pages == ["overview", "sectors", "stocks", "linkage", "market", "data-info"]
    assert index.count('data-sector-subpage="sectors"') == 2
    assert index.count('data-sector-subpage="mainlines"') == 2
    assert 'id="data-info-page"' in index


def test_m15_router_whitelists_pages_and_persists_publication_context():
    router = (V2 / "router.js").read_text(encoding="utf-8")
    assert "['overview', 'sectors', 'stocks', 'linkage', 'market', 'data-info']" in router
    assert "URLSearchParams(window.location.search)" in router
    assert "publication_id" in router and "trade_date" in router and "basis" in router
    assert "history.pushState" in router and "history.replaceState" in router
    assert "valid(next.page, pages, 'overview')" in router


def test_m15_app_restores_page_route_and_keeps_insight_route_compatible():
    app = (V2 / "app.js").read_text(encoding="utf-8")
    assert "router.read()" in app
    assert "showPage(pageRoute.page, {fromRoute: true" in app
    assert "router.navigate(page" in app
    assert "router.setPublication(next.publication_id, 'push')" in app
    assert "security_id" in app and "modal.onClose" in app and "AbortController" in app
    assert "currentPage !== pageRoute.page" in app


def test_m15_v2_has_no_iframe_and_legacy_view_stays_bound():
    index = (V2 / "index.html").read_text(encoding="utf-8")
    source = (ROOT / "src/workbench_service/app.py").read_text(encoding="utf-8")
    assert "<iframe" not in index
    assert "u.path in ('/v2','/v2/','/v2/index.html')" in source
    assert "u.path=='/view'" in source


def test_m15_data_info_and_explicit_empty_states_are_present():
    index = (V2 / "index.html").read_text(encoding="utf-8")
    app = (V2 / "app.js").read_text(encoding="utf-8")
    assert "数据能力与来源" in index
    assert "请求时读取" in index
    assert "function renderDataInfo()" in app
    assert "当前不会用空数据替代市场统计" in app
    assert "历史数据暂不可用" in app
