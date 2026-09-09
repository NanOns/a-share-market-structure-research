from pathlib import Path


ROOT = Path(__file__).parents[2]
V2 = ROOT / "src/workbench_service/static/v2"


def test_technical_page_exposes_m8a04_filters_and_pagination():
    index = (V2 / "index.html").read_text(encoding="utf-8")
    for marker in (
        'id="technical-page"',
        'id="technical-mode"',
        'id="technical-window"',
        'id="technical-rps-min"',
        'id="technical-ma-state"',
        'id="technical-amount-class"',
        'id="technical-prev"',
        'id="technical-next"',
    ):
        assert marker in index
    assert 'value="20"' in index and 'value="30"' in index and 'value="60"' in index and 'value="100"' in index


def test_technical_page_calls_api10_api11_api12_and_keeps_null_quality_visible():
    api = (V2 / "api.js").read_text(encoding="utf-8")
    app = (V2 / "app.js").read_text(encoding="utf-8")
    assert "'/api/stocks/technical'" in api
    assert "'/api/stocks/new-highs'" in api
    assert "'/api/stocks/'+securityId+'/technical-history'" in api
    assert "api.newHighs(technicalParams())" in app
    assert "api.technical(technicalParams())" in app
    assert "api.technicalHistory" in app
    assert "RPS 尚未构建" in app
    assert "NULL 保持 NULL" in app
    assert "innerHTML" not in app
