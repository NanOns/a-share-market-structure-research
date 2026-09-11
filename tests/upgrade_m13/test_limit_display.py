from pathlib import Path


ROOT = Path(__file__).parents[2]
V2 = ROOT / "src/workbench_service/static/v2"


def test_m13b_display_contract_binds_plan_and_empty_state_rules():
    contract = (ROOT / "docs/M13B_DISPLAY_CONTRACT_V1.md").read_text(encoding="utf-8")
    plan = (ROOT / "docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md").read_text(encoding="utf-8")
    assert "LIMIT_DISPLAY_V1_0" in contract
    assert "/api/limit-ladder" in contract
    assert "NOT_BUILT" in contract and "不能显示为 0%" in contract
    assert "API34" in plan and "API35" in plan


def test_m13b_display_is_bound_to_api34_api35_and_explicit_capabilities():
    index = (V2 / "index.html").read_text(encoding="utf-8")
    api = (V2 / "api.js").read_text(encoding="utf-8")
    app = (V2 / "app.js").read_text(encoding="utf-8")
    for element_id in ("limit-ladder-level", "limit-ladder-state", "limit-ladder-promotion", "limit-promotion-level", "limit-ladder-table", "limit-promotion-table", "limit-ladder-counts", "limit-ladder-prev", "limit-ladder-next"):
        assert f'id="{element_id}"' in index
    assert "limitLadder:function" in api
    assert "limitPromotionHistory:function" in api
    assert "/api/limit-ladder/promotion-history" in api
    assert "renderLimitCapabilityEmpty" in app
    assert "result.status === 'NOT_BUILT'" in app
    assert "excluded_unknown" in app and "excluded_suspended" in app and "excluded_no_limit" in app
    assert "limitLadderState" in app and "level_counts" in app and "raw_amount" in app and "association_ref" in app


def test_m13b_display_does_not_use_html_injection():
    app = (V2 / "app.js").read_text(encoding="utf-8")
    assert "innerHTML" not in app
    assert "textContent" in app
