from pathlib import Path


ROOT = Path(__file__).parents[2]
V2 = ROOT / "src/workbench_service/static/v2"


def test_v2_preview_assets_are_modular_and_not_the_legacy_iframe():
    index = (V2 / "index.html").read_text(encoding="utf-8")
    assert "<iframe" not in index
    for asset in ("api.js", "format.js", "table.js", "modal.js", "app.js", "styles.css"):
        assert f'"/v2/{asset}"' in index or f"'/v2/{asset}'" in index


def test_v2_public_layer_has_versioned_contract_and_safe_evidence_flow():
    contract = (ROOT / "docs/M7A_UI_PREVIEW_CONTRACT_V1.md").read_text(encoding="utf-8")
    table = (V2 / "table.js").read_text(encoding="utf-8")
    modal = (V2 / "modal.js").read_text(encoding="utf-8")
    app = (V2 / "app.js").read_text(encoding="utf-8")
    assert "M7A UI Preview Contract v1" in contract
    assert "textContent" in table and "table-action" in table
    assert 'aria-modal' in modal and "Escape" in modal and "event.target===active" in modal
    assert "JSON.stringify(identity,null,2)" in app
    assert "innerHTML" not in app


def test_legacy_view_route_and_v2_route_are_both_bound():
    source = (ROOT / "src/workbench_service/app.py").read_text(encoding="utf-8")
    assert "u.path in ('/v2','/v2/','/v2/index.html')" in source
    assert "u.path=='/view'" in source
    assert "unquote(u.path[len('/v2/'):])" in source
