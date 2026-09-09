import pandas as pd
import pytest
import duckdb
from datetime import datetime, timezone
from pathlib import Path

from workbench_analysis.sector_cycle import SectorCycleError, build_sector_cycle_daily, insert_sector_cycle_rows
from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_service.app import Api


def _inputs():
    technical = pd.DataFrame([
        {"security_id": "SH.1", "trade_date": "2026-09-07", "ret1": .01, "ret5": .05, "ret20": .20, "raw_amount": 100},
        {"security_id": "SH.2", "trade_date": "2026-09-07", "ret1": -.01, "ret5": .02, "ret20": .10, "raw_amount": 200},
        {"security_id": "SH.1", "trade_date": "2026-09-08", "ret1": .02, "ret5": .06, "ret20": .22, "raw_amount": 110},
        {"security_id": "SH.2", "trade_date": "2026-09-08", "ret1": .01, "ret5": .03, "ret20": .12, "raw_amount": 210},
    ])
    memberships = pd.DataFrame([
        {"security_id": "SH.1", "trade_date": "2026-09-07", "sector_id": "INDUSTRY:A", "sector_name": "A", "sector_type": "industry"},
        {"security_id": "SH.2", "trade_date": "2026-09-07", "sector_id": "INDUSTRY:A", "sector_name": "A", "sector_type": "industry"},
        {"security_id": "SH.1", "trade_date": "2026-09-08", "sector_id": "INDUSTRY:A", "sector_name": "A", "sector_type": "industry"},
        {"security_id": "SH.2", "trade_date": "2026-09-08", "sector_id": "INDUSTRY:A", "sector_name": "A", "sector_type": "industry"},
        {"security_id": "SH.1", "trade_date": "2026-09-08", "sector_id": "THEME:X", "sector_name": "X", "sector_type": "theme"},
    ])
    return technical, memberships


def test_daily_vector_keeps_board_quote_separate_and_deduplicates_by_sector():
    technical, memberships = _inputs()
    result = build_sector_cycle_daily(technical, memberships, cutoff="2026-09-08", board_quotes=pd.DataFrame([{"sector_id": "INDUSTRY:A", "trade_date": "2026-09-08", "board_quote_ret1": .03, "board_quote_source": "fixture"}]))
    row = result[(result.sector_id == "INDUSTRY:A") & (result.trade_date.astype(str) == "2026-09-08")].iloc[0]
    assert row.total_member_count == 2
    assert row.member_amount_sum == 320
    assert row.board_quote_ret1 == .03
    assert row.member_ret1_median == pytest.approx(.015)
    assert row.sector_rs20_pct == 1.0
    assert row["rank"] == 1


def test_daily_vector_is_stable_under_input_order_and_rejects_future_or_conflict():
    technical, memberships = _inputs()
    left = build_sector_cycle_daily(technical, memberships, cutoff="2026-09-08")
    right = build_sector_cycle_daily(technical.sample(frac=1, random_state=1), memberships.sample(frac=1, random_state=2), cutoff="2026-09-08")
    pd.testing.assert_frame_equal(left, right)
    with pytest.raises(SectorCycleError, match="FUTURE_SECTOR_CYCLE_INPUT"):
        build_sector_cycle_daily(technical.assign(trade_date="2026-09-09"), memberships, cutoff="2026-09-08")
    conflict = pd.concat([memberships, memberships.iloc[[0]].assign(sector_name="changed")], ignore_index=True)
    with pytest.raises(SectorCycleError, match="MEMBERSHIP_DUPLICATE_CONFLICT"):
        build_sector_cycle_daily(technical, conflict, cutoff="2026-09-08")


def test_cycle_and_timeline_apis_read_only_bound_sector_cycle_snapshot(tmp_path):
    root = Path(__file__).parents[2]
    (tmp_path / "config").mkdir()
    (tmp_path / "config/history_windows.yaml").write_text((root / "config/history_windows.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    con = duckdb.connect(str(tmp_path / "cycle.duckdb"))
    try:
        con.execute((root / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
        con.execute("insert into schema_migrations values (?, current_timestamp)", [BASE_SCHEMA_VERSION])
        MigrationExecutor(con).apply()
        now = datetime.now(timezone.utc)
        con.execute("insert into publications values (?,?,?,?,?,?,?,?,?,?,?,?)", ["pub-1", "2026-09-08", 1, "SUCCESS", 1, "test", None, None, None, None, "fixture", now])
        con.execute("insert into analysis_snapshots values (?,?,?,?,?,?,?,?)", ["snapshot-1", "2026-09-08", "2026-09-01", "CN_A_LISTED_V2", "config", "manifest", "SUCCESS", now])
        con.execute("insert into publication_analysis_snapshots values (?,?,?,?)", ["pub-1", "LOCAL_RECONSTRUCTED", "snapshot-1", now])
        tech, members = _inputs()
        vectors = build_sector_cycle_daily(tech, members, cutoff="2026-09-08")
        con.execute("insert into analysis_slices values (?,?,?,?,?,?,?,?,?,?,?,?)", ["slice-cycle", "sector_cycle", "2026-09-08", "c", "i", "d", "{}", len(vectors), "l", "DUCKDB", None, now])
        assert insert_sector_cycle_rows(con, "slice-cycle", vectors) == len(vectors)
        for day in vectors.trade_date.unique():
            con.execute("insert into analysis_snapshot_entries values (?,?,?,?)", ["snapshot-1", "sector_cycle", day, "slice-cycle"])
    finally:
        con.close()
    api = Api(tmp_path / "cycle.duckdb", root=tmp_path)
    matrix = api.sector_cycle("pub-1", days=2, size=20)
    assert matrix["dates"] == ["2026-09-07", "2026-09-08"]
    assert matrix["total"] == 2
    assert len(matrix["items"][0]["cells"]) == 2
    timeline = api.sector_timeline("pub-1", "INDUSTRY:A", days=2)
    assert [point["trade_date"] for point in timeline["points"]] == ["2026-09-07", "2026-09-08"]
    assert timeline["points"][-1]["hierarchy_rank"] == 1.0
    members_history = api.sector_members_history("pub-1", "INDUSTRY:A", days=2)
    assert members_history["total"] == 0
    leader_history = api.sector_leader_history("pub-1", "INDUSTRY:A", days=2)
    assert leader_history["status"] == "NOT_FOUND"
