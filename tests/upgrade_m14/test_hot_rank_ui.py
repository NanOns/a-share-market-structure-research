from pathlib import Path


ROOT = Path(__file__).parents[2]
V2 = ROOT / "src/workbench_service/static/v2"


def test_hot_rank_is_mounted_in_market_cycle_view():
    index = (V2 / "index.html").read_text(encoding="utf-8")
    api = (V2 / "api.js").read_text(encoding="utf-8")
    app = (V2 / "app.js").read_text(encoding="utf-8")
    styles = (V2 / "styles.css").read_text(encoding="utf-8")

    assert 'class="panel hot-rank-panel"' in index
    for element_id in ("hot-rank-source", "hot-rank-refresh", "hot-rank-basis", "hot-rank-table", "hot-rank-prev", "hot-rank-next"):
        assert f'id="{element_id}"' in index
    assert "hotRankings:function" in api
    assert "function loadHotRank()" in app
    assert "loadHotRank();" in app
    assert "reason_status" in app and "quote_status" in app
    assert "时间语义" in app and "time_semantics" in app
    assert ".hot-rank-panel .context-table" in styles


def test_hot_rank_ui_declares_ephemeral_and_degraded_fields():
    index = (V2 / "index.html").read_text(encoding="utf-8")
    app = (V2 / "app.js").read_text(encoding="utf-8")

    assert "不保存热榜快照" in index
    assert "不可用（无已验证来源）" in app
    assert "_reason_status" in app
    assert "实时请求失败；未保存热榜快照。" in app
    assert "textContent" in app
