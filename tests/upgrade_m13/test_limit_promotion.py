from datetime import datetime
from pathlib import Path

import duckdb
import pytest

from workbench_analysis.limit_promotion import (
    CONTRACT_VERSION,
    LimitPromotionError,
    annotate_promotion_states,
    build_promotion_points,
)
from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_service.app import Api


ROOT = Path(__file__).parents[2]
DB = ROOT / "data/database/market_research.duckdb"


def _rows_for_example():
    rows = []
    for index in range(1, 11):
        security_id = f"SH.6000{index:02d}"
        rows.append({"security_id": security_id, "trade_date": "2026-09-10", "limit_state": "UP", "streak": 1, "streak_known": True, "ladder_level": "1"})
        if index <= 6:
            rows.append({"security_id": security_id, "trade_date": "2026-09-11", "limit_state": "UP", "streak": 2, "streak_known": True, "ladder_level": "2"})
        elif index <= 8:
            rows.append({"security_id": security_id, "trade_date": "2026-09-11", "limit_state": "NONE", "streak": None, "streak_known": True, "ladder_level": None})
        elif index == 9:
            rows.append({"security_id": security_id, "trade_date": "2026-09-11", "limit_state": "SUSPENDED", "streak": None, "streak_known": True, "ladder_level": None})
        else:
            rows.append({"security_id": security_id, "trade_date": "2026-09-11", "limit_state": "UNKNOWN", "streak": None, "streak_known": False, "ladder_level": "UNKNOWN"})
    return rows


def test_promotion_uses_confirmed_denominator_and_keeps_exclusions_separate():
    point = build_promotion_points(_rows_for_example())[0]
    assert point["previous_up_count"] == 10
    assert point["previous_unconfirmed_count"] == 0
    assert point["success_count"] == 6
    assert point["eligible_count"] == 8
    assert point["excluded_suspended"] == 1
    assert point["excluded_unknown"] == 1
    assert point["excluded_no_limit"] == 0
    assert point["rate"] == pytest.approx(0.75)


def test_promotion_excludes_no_limit_and_unconfirmed_previous_up():
    rows = [
        {"security_id": "SH.600001", "trade_date": "2026-09-10", "limit_state": "UP", "streak": 1, "streak_known": True, "ladder_level": "1"},
        {"security_id": "SH.600001", "trade_date": "2026-09-11", "limit_state": "NO_LIMIT", "streak_known": True},
        {"security_id": "SH.600002", "trade_date": "2026-09-10", "limit_state": "UP", "streak": 1, "streak_known": False, "ladder_level": "UNKNOWN"},
        {"security_id": "SH.600002", "trade_date": "2026-09-11", "limit_state": "UP", "streak": 2, "streak_known": True, "ladder_level": "2"},
    ]
    point = build_promotion_points(rows, previous_levels=("1",))[0]
    assert point["previous_up_count"] == 2
    assert point["previous_unconfirmed_count"] == 1
    assert point["eligible_count"] == 0
    assert point["excluded_no_limit"] == 1
    assert point["rate"] is None


def test_promotion_missing_current_is_unknown_exclusion():
    rows = [{"security_id": "SZ.000001", "trade_date": "2026-09-10", "limit_state": "UP", "streak": 1, "streak_known": True, "ladder_level": "1"}]
    point = build_promotion_points(rows, market_dates=["2026-09-10", "2026-09-11"], previous_levels=("1",))[0]
    assert point["excluded_unknown"] == 1
    assert point["eligible_count"] == 0


def test_promotion_unconfirmed_is_global_not_other_confirmed_levels():
    rows = [
        {"security_id": "SH.600001", "trade_date": "2026-09-10", "limit_state": "UP", "streak": 1, "streak_known": True, "ladder_level": "1"},
        {"security_id": "SH.600002", "trade_date": "2026-09-10", "limit_state": "UP", "streak": 2, "streak_known": True, "ladder_level": "2"},
        {"security_id": "SH.600001", "trade_date": "2026-09-11", "limit_state": "NONE", "streak_known": True},
        {"security_id": "SH.600002", "trade_date": "2026-09-11", "limit_state": "NONE", "streak_known": True},
    ]
    points = build_promotion_points(rows, previous_levels=("1", "2"))
    assert [point["previous_unconfirmed_count"] for point in points] == [0, 0]


def test_promotion_unconfirmed_count_is_zero_for_confirmed_rows_across_levels():
    rows = [
        {"security_id": "SH.600001", "trade_date": "2026-09-10", "limit_state": "UP", "streak": 1, "streak_known": True, "ladder_level": "1"},
        {"security_id": "SH.600002", "trade_date": "2026-09-10", "limit_state": "UP", "streak": 2, "streak_known": True, "ladder_level": "2"},
        {"security_id": "SH.600001", "trade_date": "2026-09-11", "limit_state": "NONE", "streak_known": True},
        {"security_id": "SH.600002", "trade_date": "2026-09-11", "limit_state": "NONE", "streak_known": True},
    ]
    points = build_promotion_points(rows, previous_levels=("1", "2"))
    assert [(point["previous_level"], point["previous_up_count"], point["previous_unconfirmed_count"]) for point in points] == [("1", 2, 0), ("2", 2, 0)]


def test_row_level_promotion_state_is_annotated_for_api34_filter():
    rows = [
        {"security_id": "SH.600001", "trade_date": "2026-09-10", "limit_state": "UP", "streak": 1, "streak_known": True, "ladder_level": "1"},
        {"security_id": "SH.600001", "trade_date": "2026-09-11", "limit_state": "UP", "streak": 2, "streak_known": True, "ladder_level": "2"},
    ]
    result = annotate_promotion_states(rows, ["2026-09-10", "2026-09-11"])
    assert result[-1]["promotion_state"] == "SUCCESS"


def test_promotion_rejects_duplicate_security_date():
    with pytest.raises(LimitPromotionError, match="DUPLICATE_SECURITY_DATE"):
        build_promotion_points([
            {"security_id": "SH.600001", "trade_date": "2026-09-10", "limit_state": "UP"},
            {"security_id": "SH.600001", "trade_date": "2026-09-10", "limit_state": "NONE"},
        ])


def test_promotion_migration_is_atomic_and_has_contract_fields(tmp_path):
    connection = duckdb.connect(str(tmp_path / "promotion.duckdb"))
    try:
        connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
        connection.execute("insert into schema_migrations values (?, current_timestamp)", [BASE_SCHEMA_VERSION])
        MigrationExecutor(connection).apply()
        columns = {row[1] for row in connection.execute("pragma table_info('limit_promotion_daily')").fetchall()}
        assert {"previous_level", "success_count", "eligible_count", "excluded_unknown", "excluded_suspended", "excluded_no_limit", "rate", "contract_id"}.issubset(columns)
        assert connection.execute("select count(*) from limit_promotion_daily").fetchone()[0] == 0
    finally:
        connection.close()


def _promotion_api_db(tmp_path):
    path = tmp_path / "api35.duckdb"
    connection = duckdb.connect(str(path))
    now = datetime(2026, 9, 11, 9, 0, 0)
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("insert into schema_migrations values (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    MigrationExecutor(connection).apply()
    connection.execute("insert into publications values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ["p-promotion", "2026-09-11", 1, "SUCCESS", 1, "m4-test", "", "", "", "", "", now])
    connection.execute("insert into publication_heads values (?, ?)", ["2026-09-11", "p-promotion"])
    connection.execute("insert into analysis_snapshots values (?, ?, ?, ?, ?, ?, ?, ?)", ["snap-promotion", "2026-09-11", "2026-09-10", "CN_A_LISTED_V2", "c", "m", "SUCCESS", now])
    connection.execute("insert into publication_analysis_snapshots values (?, ?, ?, ?)", ["p-promotion", "LOCAL_RECONSTRUCTED", "snap-promotion", now])
    for index, (trade_date, previous_date, success) in enumerate((("2026-09-09", "2026-09-08", 4), ("2026-09-10", "2026-09-09", 5), ("2026-09-11", "2026-09-10", 6))):
        slice_id = f"slice-promotion-{index}"
        connection.execute("insert into analysis_slices values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [slice_id, "limit_promotion", trade_date, CONTRACT_VERSION, "i", "d", "{}", 1, "l" + str(index), "DUCKDB", None, now])
        connection.execute("insert into analysis_daily_basis values (?, ?, ?, ?, ?, ?, ?, ?)", [slice_id, "CN_A_LISTED_V2", None, "RAW", None, now, 1.0, "{}"])
        connection.execute("insert into analysis_snapshot_entries values (?, ?, ?, ?)", ["snap-promotion", "limit_promotion", trade_date, slice_id])
        connection.execute("insert into limit_promotion_daily values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [slice_id, previous_date, trade_date, "1", 10, 0, success, 8, 1, 1, 0, success / 8, CONTRACT_VERSION])
    connection.commit()
    connection.close()
    return path


def test_api35_reads_fixed_snapshot_and_filters_level(tmp_path):
    result = Api(_promotion_api_db(tmp_path), root=ROOT).limit_promotion_history("p-promotion", basis="RECONSTRUCTED", previous_level="1")
    assert result["status"] == "AVAILABLE"
    assert result["snapshot_id"] == "snap-promotion"
    assert result["points"][-1]["success_count"] == 6
    assert result["points"][-1]["previous_level"] == "1"


def test_api35_days_limits_actual_points_query(tmp_path):
    result = Api(_promotion_api_db(tmp_path), root=ROOT).limit_promotion_history("p-promotion", days=1, basis="RECONSTRUCTED", previous_level="1")
    assert [point["trade_date"] for point in result["points"]] == ["2026-09-11"]


def test_api35_is_explicitly_not_built_without_m8c_materialization(tmp_path):
    path = tmp_path / "api35-empty.duckdb"
    connection = duckdb.connect(str(path))
    try:
        connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
        connection.execute("insert into schema_migrations values (?, current_timestamp)", [BASE_SCHEMA_VERSION])
        MigrationExecutor(connection).apply()
        now = datetime(2026, 9, 11, 9, 0, 0)
        connection.execute(
            "insert into publications values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ["p-empty", "2026-09-10", 1, "SUCCESS", 1, "m4-test", "", "", "", "", "", now],
        )
        connection.execute("insert into publication_heads values (?, ?)", ["2026-09-10", "p-empty"])
        connection.execute(
            "insert into analysis_snapshots values (?, ?, ?, ?, ?, ?, ?, ?)",
            ["snap-empty", "2026-09-10", "2026-09-08", "CN_A_LISTED_V2", "c", "m", "SUCCESS", now],
        )
        connection.execute(
            "insert into publication_analysis_snapshots values (?, ?, ?, ?)",
            ["p-empty", "LOCAL_RECONSTRUCTED", "snap-empty", now],
        )
        connection.commit()
    finally:
        connection.close()

    api = Api(path, root=ROOT)
    result = api.limit_promotion_history("p-empty", basis="RECONSTRUCTED")
    assert result["contract_id"] == CONTRACT_VERSION
    assert result["status"] == "NOT_BUILT"
    assert result["points"] == []
    assert result["capabilities"]["limit_promotion"] == "NOT_BUILT"
