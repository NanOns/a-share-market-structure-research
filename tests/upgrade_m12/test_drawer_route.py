from pathlib import Path


ROOT = Path(__file__).parents[2]
APP = ROOT / "src/workbench_service/static/v2/app.js"
API = ROOT / "src/workbench_service/static/v2/api.js"
MODAL = ROOT / "src/workbench_service/static/v2/modal.js"


def test_m12_route_contains_publication_security_tab_and_days_and_restores_on_popstate():
    source = APP.read_text(encoding="utf-8")
    assert "publication_id" in source and "security_id" in source
    assert "tab" in source and "days" in source
    assert "pushState" in source and "replaceState" in source
    assert "addEventListener('popstate'" in source
    assert "restoreInsightRoute" in source


def test_m12_insight_cancels_inflight_requests_and_ignores_abort_errors():
    source = APP.read_text(encoding="utf-8")
    api_source = API.read_text(encoding="utf-8")
    assert "AbortController" in source
    assert ".abort()" in source
    assert "error.name === 'AbortError'" in source
    assert "options.signal" in api_source
    assert "stockInsight:function(params,options)" in api_source


def test_m12_modal_has_accessible_title_and_focus_trap():
    source = MODAL.read_text(encoding="utf-8")
    assert "aria-labelledby" in source
    assert "aria-modal" in source
    assert "event.key!=='Tab'" in source
    assert "lastFocus.focus" in source
