from pathlib import Path


ROOT = Path(__file__).parents[2]
APP = ROOT / "src/workbench_service/static/v2/app.js"
MODAL = ROOT / "src/workbench_service/static/v2/modal.js"
STYLE = ROOT / "src/workbench_service/static/v2/styles.css"
API = ROOT / "src/workbench_service/static/v2/api.js"


def test_stock_insight_has_shared_entry_and_explicit_tabs():
    source = APP.read_text(encoding="utf-8")
    assert "function showStockInsight" in source
    assert "stockInsight({" in source
    assert "概览" in source and "历史" in source and "证据" in source
    assert "api.technicalHistory" in source
    assert "api.structureHistory" in source
    assert "requestId !== insightRequestId" in source
    assert "innerHTML" not in source


def test_stock_insight_is_available_from_stock_result_tables():
    source = APP.read_text(encoding="utf-8")
    assert source.count("onClick: showStockInsight") >= 4


def test_modal_exposes_close_state_for_late_response_guard():
    source = MODAL.read_text(encoding="utf-8")
    assert "onClose" in source
    assert "isOpen" in source


def test_insight_tabs_have_visible_contract_styles():
    source = STYLE.read_text(encoding="utf-8")
    assert ".insight-tabs" in source
    assert ".insight-tab.active" in source


def test_history_tab_uses_one_date_anchored_chart_with_visible_gaps():
    source = APP.read_text(encoding="utf-8")
    style = STYLE.read_text(encoding="utf-8")
    assert "function renderHistoryChart" in source
    assert "createElementNS('http://www.w3.org/2000/svg'" in source
    assert "OHLC、均线、RPS20 和成交金额历史图表" in source
    assert "ADJUSTED" in source
    assert "chart-gap" in source
    assert "if (value === null || value === undefined || value === '') return null;" in source
    assert "insight-chart-panel" in style


def test_structure_history_window_is_date_based_and_association_evidence_is_structured():
    source = APP.read_text(encoding="utf-8")
    assert "function structureHistoryRows" in source
    assert "var structures = structureHistoryRows" in source
    assert "结构历史（最近' + route.days + '个交易日）" in source
    assert "evidence_items" in source
    assert "证据摘要" in source


def test_evidence_tab_uses_grouped_api15_details_and_safe_text_rendering():
    source = APP.read_text(encoding="utf-8")
    api_source = API.read_text(encoding="utf-8")
    style = STYLE.read_text(encoding="utf-8")
    assert "api.evidence" in source
    assert "format: 'groups'" in source
    assert "证据摘要（5项）" in source
    assert "evidenceDetails" in source
    assert "details.replaceChildren" in source
    assert "textContent" in source
    assert "evidence:function(params,options)" in api_source
    assert ".evidence-details" in style


def test_online_evidence_is_a_collapsed_non_blocking_m14_placeholder():
    source = APP.read_text(encoding="utf-8")
    assert "function externalEvidencePlaceholder" in source
    assert "在线增强 · 当前不可用（默认折叠）" in source
    assert "不阻塞本地个股透视首屏" in source
    assert "API38（M14）" in source
