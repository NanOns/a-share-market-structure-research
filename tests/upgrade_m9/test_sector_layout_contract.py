from pathlib import Path


ROOT = Path(__file__).parents[2]
V2 = ROOT / "src/workbench_service/static/v2"


def test_sector_page_uses_separate_industry_tables_and_flat_table():
    index = (V2 / "index.html").read_text(encoding="utf-8")
    app = (V2 / "app.js").read_text(encoding="utf-8")

    assert 'id="sector-level"' not in index
    assert 'id="sector-root-table"' in index
    assert 'id="sector-leaf-table"' in index
    assert 'id="sector-flat-table"' in index
    assert "sectorRequest('ROOT'," in app
    assert "sectorRequest('LEAF'," in app
    assert "sectorRequest('FLAT'," in app
