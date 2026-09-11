from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_m11_linkage_ui_has_three_subpages_and_collapsible_selection_bar():
    html = (ROOT / "src/workbench_service/static/v2/index.html").read_text(encoding="utf-8")
    app = (ROOT / "src/workbench_service/static/v2/app.js").read_text(encoding="utf-8")
    css = (ROOT / "src/workbench_service/static/v2/styles.css").read_text(encoding="utf-8")
    contract = (ROOT / "docs/M11_LINKAGE_UI_CONTRACT_V1.md").read_text(encoding="utf-8")
    for marker in ('id="linkage-page"', 'data-linkage-mode="attributes"', 'data-linkage-mode="linkage"', 'data-linkage-mode="intersection"', 'id="linkage-toggle-selection"', 'id="linkage-table"'):
        assert marker in html
    assert "setLinkageMode" in app
    assert "linkageState.selectionCollapsed" in app
    assert ".linkage-tabs" in css and ".linkage-selection-head" in css
    assert "M11_LINKAGE_UI_V1" in contract


def test_m11_linkage_ui_keeps_explicit_basis_and_non_reordering_copy():
    html = (ROOT / "src/workbench_service/static/v2/index.html").read_text(encoding="utf-8")
    app = (ROOT / "src/workbench_service/static/v2/app.js").read_text(encoding="utf-8")
    assert "筛选只影响展示，不重新排名" in html
    assert "basis: 'RECONSTRUCTED'" in app
    assert "linkageHistory" in app or "api.linkage" in app
