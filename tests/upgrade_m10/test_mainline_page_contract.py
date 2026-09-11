from pathlib import Path
from datetime import datetime, timezone

import duckdb
import pandas as pd

from workbench_analysis.mainline import insert_mainline_rows
from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_service.app import Api


ROOT = Path(__file__).parents[2]
V2 = ROOT / "src/workbench_service/static/v2"


def test_mainline_page_has_filters_table_and_evidence_route():
    index = (V2 / "index.html").read_text(encoding="utf-8")
    api = (V2 / "api.js").read_text(encoding="utf-8")
    app = (V2 / "app.js").read_text(encoding="utf-8")

    for marker in (
        'data-sector-subpage="mainlines"',
        'id="mainlines-page"',
        'id="mainline-class"',
        'id="mainline-days"',
        'id="mainline-status-cards"',
        'id="mainline-industry-root-table"',
        'id="mainline-industry-leaf-table"',
        'id="mainline-theme-table"',
    ):
        assert marker in index
    assert 'id="mainline-style-table"' not in index
    assert "mainlineEvidence" in api
    assert "api.mainlines" in app
    assert "MAINLINE_NOT_BUILT" in app
    assert "mainlinePredicateRows" in app
    assert "mainlinePredicateSections" in app
    assert "mainline-status-card" in app
    assert "class_counts" in app
    assert "mainlineClassMeaning" in app
    assert "INDUSTRY_ROOT" in app
    assert "mainlineHistoryStage(row.valid_observation_days, mainlineState.historyPolicy)" in app
    assert "mainlineHistoryStage(currentPoint.valid_observation_days, result.history_policy)" in app
    assert "mainlineClassText(row.mainline_class)" in app


def test_mainline_api_paginates_without_double_slicing_and_catalogs_fields(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/history_windows.yaml").write_text(
        (ROOT / "config/history_windows.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    database = tmp_path / "mainline.duckdb"
    con = duckdb.connect(str(database))
    now = datetime.now(timezone.utc)
    try:
        con.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
        con.execute("insert into schema_migrations values (?, current_timestamp)", [BASE_SCHEMA_VERSION])
        MigrationExecutor(con).apply()
        con.execute(
            "insert into publications values (?,?,?,?,?,?,?,?,?,?,?,?)",
            ["pub-1", "2026-09-08", 1, "SUCCESS", 1, "test", None, None, None, None, "fixture", now],
        )
        con.execute("insert into analysis_snapshots values (?,?,?,?,?,?,?,?)", ["snapshot-1", "2026-09-08", "2026-09-01", "CN_A_LISTED_V2", "config", "manifest", "SUCCESS", now])
        con.execute("insert into publication_analysis_snapshots values (?,?,?,?)", ["pub-1", "LOCAL_RECONSTRUCTED", "snapshot-1", now])
        con.execute(
            "insert into tdx_sector_hierarchy_versions values (?,?,?,?,?,?,?)",
            ["hierarchy-fixture-v1", "TDX_SECTOR_HIERARCHY_V1_1", "fixture", "{}", "fixture-hash", now, now],
        )
        con.executemany(
            "insert into tdx_sector_hierarchy_nodes values (?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                ["hierarchy-fixture-v1", "INDUSTRY", f"INDUSTRY:{index}", str(index), f"板块{index}", None, None, "ROOT", "FIXTURE", "fixture", "fixture-hash", "TDX_SECTOR_HIERARCHY_V1_1"]
                for index in range(3)
            ],
        )
        con.execute(
            "insert into analysis_snapshot_hierarchy values (?,?,?,?)",
            ["snapshot-1", "hierarchy-fixture-v1", "fixture-hash", now],
        )
        con.execute("insert into analysis_slices values (?,?,?,?,?,?,?,?,?,?,?,?)", ["slice-mainline", "mainline", "2026-09-08", "MAINLINE_STATE_V2_3_PREVIEW", "input", "manifest", "{}", 3, "logical", "DUCKDB", None, now])
        rows = []
        for index in range(3):
            rows.append({
                "sector_id": f"INDUSTRY:{index}", "trade_date": "2026-09-08", "sector_name": f"板块{index}", "sector_type": "INDUSTRY",
                "mainline_class": "DATA_INSUFFICIENT", "previous_class": None, "transition": None,
                "observation_days": 3, "valid_observation_days": 3, "on_list_days": {"5": None, "10": None, "20": None, "30": None},
                "consecutive_on_list": None, "current_percentile": None, "current_breadth": None, "current_amount_vs_prior20": None,
                "percentile_change_3d": None, "breadth_change_3d": None, "amount_change_3d": None, "retention_rate": None,
                "entered_count": None, "exited_count": None, "predicates": {"history_minimum_3_observations": False},
                "missing_fields": ["sector_rs20_pct_3_observations"], "conflict_resolution": "OBSERVATION_HISTORY_NOT_REACHED",
                "history_basis": "RECONSTRUCTED", "contract_id": "MAINLINE_STATE_V2_3_PREVIEW", "config_hash": "hash",
            })
        insert_mainline_rows(con, "slice-mainline", pd.DataFrame(rows))
        con.execute("insert into analysis_snapshot_entries values (?,?,?,?)", ["snapshot-1", "mainline", "2026-09-08", "slice-mainline"])
    finally:
        con.close()

    api = Api(database, root=tmp_path)
    result = api.mainlines("pub-1", page=2, size=2)
    assert result["total"] == 3
    assert result["page"] == 2
    assert [item["sector_id"] for item in result["items"]] == ["INDUSTRY:2"]
    grouped = api.mainlines("pub-1", group="INDUSTRY_ROOT", size=10)
    assert grouped["total"] == 3
    assert grouped["class_counts"] == {
        "FADING": 0,
        "HIGH_LEVEL_CONTRACTION": 0,
        "REACCELERATING": 0,
        "SUSTAINED": 0,
        "NEW": 0,
        "BROADENING": 0,
        "OBSERVING": 0,
        "DATA_INSUFFICIENT": 3,
    }
    assert {item["mainline_group"] for item in grouped["items"]} == {"INDUSTRY_ROOT"}
    filtered = api.mainlines("pub-1", group="INDUSTRY_ROOT", mainline_class="OBSERVING", size=10)
    assert filtered["total"] == 0
    assert filtered["class_counts"]["DATA_INSUFFICIENT"] == 3
    catalog = api.field_catalog()
    field_ids = {item["field_id"] for item in catalog["items"]}
    assert {"mainline_class", "predicates", "missing_fields"}.issubset(field_ids)
    assert catalog["enums"]["mainline_class"]["DATA_INSUFFICIENT"] == "数据不足"
    assert catalog["enums"]["mainline_transition"]["MODEL_CHANGE"] == "模型合同变化"
    assert catalog["enums"]["mainline_transition"]["BASIS_CHANGE"] == "历史口径变化"
