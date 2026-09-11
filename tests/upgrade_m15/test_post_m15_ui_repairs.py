from pathlib import Path


ROOT = Path(__file__).parents[2]
INDEX = (ROOT / "src/workbench_service/static/v2/index.html").read_text(encoding="utf-8")
APP = (ROOT / "src/workbench_service/static/v2/app.js").read_text(encoding="utf-8")
BUILDER = (ROOT / "scripts/build_m13_preview.py").read_text(encoding="utf-8")


def test_overview_has_ten_rows_and_priority_filters():
    assert "当前快照前 10 个" in INDEX
    assert 'id="overview-priority-q"' in INDEX
    assert 'id="overview-priority-grade"' in INDEX
    assert 'id="overview-priority-pattern"' in INDEX


def test_user_facing_mainline_and_sector_controls_exclude_style():
    assert 'id="mainline-style-table"' not in INDEX
    assert '<option value="STYLE">' not in INDEX
    assert "风格标签</b>" not in INDEX
    assert "mainline-style-table" not in APP


def test_linkage_accepts_names_and_translates_evidence():
    assert "resolveSectorTokens" in APP
    assert "名称或ID" in INDEX
    assert "PATTERN_NOT_CURRENT_STRENGTH_OR_REACCELERATION" in APP
    assert "股票-板块强势关联合同 V1" in APP


def test_m13_binds_hierarchy_to_new_snapshot():
    assert "M13_HIERARCHY_BINDING_MISSING" in BUILDER
    assert "analysis_snapshot_hierarchy" in BUILDER
    assert '"hierarchy_version": hierarchy_version' in BUILDER

