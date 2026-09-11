from datetime import datetime
from pathlib import Path

import duckdb
import pytest

from workbench_analysis.limit_ladder import (
    CONTRACT_VERSION,
    LimitLadderError,
    canonical_limit_state,
    derive_limit_ladder_rows,
)
from workbench_service.app import Api
from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor


ROOT = Path(__file__).parents[2]
DB = ROOT / "data/database/market_research.duckdb"


def test_canonical_state_does_not_turn_unknown_into_none():
    assert canonical_limit_state("LIMIT_UP") == "UP"
    assert canonical_limit_state("LIMIT_DOWN") == "DOWN"
    assert canonical_limit_state("NOT_LIMIT") == "NONE"
    assert canonical_limit_state("unverified") == "UNKNOWN"


def test_ladder_recursion_tracks_known_up_streak_and_suspension_break():
    rows = derive_limit_ladder_rows(
        [
            {"security_id": "SH.600001", "trade_date": "2026-09-08", "limit_state": "NONE"},
            {"security_id": "SH.600001", "trade_date": "2026-09-09", "limit_state": "LIMIT_UP"},
            {"security_id": "SH.600001", "trade_date": "2026-09-10", "limit_state": "LIMIT_UP"},
            {"security_id": "SH.600001", "trade_date": "2026-09-11", "suspended": True},
            {"security_id": "SH.600001", "trade_date": "2026-09-12", "limit_state": "LIMIT_UP"},
        ],
        ["2026-09-08", "2026-09-09", "2026-09-10", "2026-09-11", "2026-09-12"],
    )
    by_date = {row["trade_date"]: row for row in rows}
    assert (by_date["2026-09-09"]["streak"], by_date["2026-09-09"]["ladder_level"]) == (1, "1")
    assert (by_date["2026-09-10"]["streak"], by_date["2026-09-10"]["ladder_level"]) == (2, "2")
    assert by_date["2026-09-11"]["exclusion_reason"] == "SUSPENSION_BREAK"
    assert (by_date["2026-09-12"]["streak"], by_date["2026-09-12"]["streak_known"]) == (1, True)


def test_left_censor_missing_observation_and_unknown_are_not_none():
    rows = derive_limit_ladder_rows(
        [
            {"security_id": "SZ.000001", "trade_date": "2026-09-08", "limit_state": "UP"},
            {"security_id": "SZ.000001", "trade_date": "2026-09-10", "limit_state": "UP"},
        ],
        ["2026-09-08", "2026-09-09", "2026-09-10"],
    )
    by_date = {row["trade_date"]: row for row in rows}
    assert by_date["2026-09-08"]["exclusion_reason"] == "LEFT_CENSORED"
    assert by_date["2026-09-08"]["streak_min_known"] == 1
    assert by_date["2026-09-09"]["limit_state"] == "UNKNOWN"
    assert by_date["2026-09-09"]["exclusion_reason"] == "MISSING_MARKET_OBSERVATION"
    assert by_date["2026-09-10"]["streak_known"] is False
    assert by_date["2026-09-10"]["exclusion_reason"] == "UNKNOWN_PREVIOUS_BOUNDARY"
    assert by_date["2026-09-10"]["ladder_level"] == "UNKNOWN"


def test_duplicate_security_date_is_rejected():
    with pytest.raises(LimitLadderError, match="DUPLICATE_SECURITY_DATE"):
        derive_limit_ladder_rows(
            [
                {"security_id": "SH.600001", "trade_date": "2026-09-08", "limit_state": "UP"},
                {"security_id": "SH.600001", "trade_date": "2026-09-08", "limit_state": "NONE"},
            ]
        )


def test_limit_ladder_migration_is_atomic_and_has_contract_fields(tmp_path):
    connection = duckdb.connect(str(tmp_path / "ladder.duckdb"))
    try:
        connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
        connection.execute("insert into schema_migrations values (?, current_timestamp)", [BASE_SCHEMA_VERSION])
        result = MigrationExecutor(connection).apply()
        assert result["status"] == "APPLIED"
        columns = {row[1] for row in connection.execute("pragma table_info('limit_ladder_daily')").fetchall()}
        assert {"limit_state", "streak_known", "streak_min_known", "promotion_state", "contract_id"}.issubset(columns)
        assert connection.execute("select count(*) from limit_ladder_daily").fetchone()[0] == 0
    finally:
        connection.close()


def test_api34_is_explicitly_not_built_without_m8c_materialization(tmp_path):
    path = tmp_path / "api34-empty.duckdb"
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
    result = api.limit_ladder("p-empty", basis="RECONSTRUCTED")
    assert result["contract_id"] == CONTRACT_VERSION
    assert result["status"] == "NOT_BUILT"
    assert result["items"] == []
    assert result["capabilities"]["limit_ladder"] == "NOT_BUILT"
    assert result["capabilities"]["m8c_reference"] == "NOT_BUILT"
    assert result["capabilities"]["m8c_rules"] == "NOT_BUILT"


def test_api34_reads_fixed_snapshot_and_applies_level_filter(tmp_path):
    path = tmp_path / "api34.duckdb"
    connection = duckdb.connect(str(path))
    try:
        connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
        connection.execute("insert into schema_migrations values (?, current_timestamp)", [BASE_SCHEMA_VERSION])
        MigrationExecutor(connection).apply()
        now = datetime(2026, 9, 11, 9, 0, 0)
        connection.execute(
            "insert into publications values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ["p-ladder", "2026-09-10", 1, "SUCCESS", 1, "m4-test", "", "", "", "", "", now],
        )
        connection.execute("insert into publication_heads values (?, ?)", ["2026-09-10", "p-ladder"])
        connection.execute(
            "insert into analysis_snapshots values (?, ?, ?, ?, ?, ?, ?, ?)",
            ["snap-ladder", "2026-09-10", "2026-09-08", "CN_A_LISTED_V2", "c", "m", "SUCCESS", now],
        )
        connection.execute("insert into publication_analysis_snapshots values (?, ?, ?, ?)", ["p-ladder", "LOCAL_RECONSTRUCTED", "snap-ladder", now])
        connection.execute(
            "insert into analysis_slices values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ["slice-ladder", "limit_ladder", "2026-09-10", CONTRACT_VERSION, "i", "d", "{}", 1, "l", "DUCKDB", None, now],
        )
        connection.execute("insert into analysis_daily_basis values (?, ?, ?, ?, ?, ?, ?, ?)", ["slice-ladder", "CN_A_LISTED_V2", None, "RAW", None, now, 1.0, "{}"])
        connection.execute("insert into analysis_snapshot_entries values (?, ?, ?, ?)", ["snap-ladder", "limit_ladder", "2026-09-10", "slice-ladder"])
        connection.execute(
            "insert into limit_ladder_daily values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ["slice-ladder", "SH.600001", "2026-09-10", "UP", "RULE_VERSIONED", "R1", 11.0, 9.0, 2, True, 2, "UP", 1, "2", "NOT_EVALUATED", None, None, None, CONTRACT_VERSION],
        )
        connection.commit()
    finally:
        connection.close()

    result = Api(path, root=ROOT).limit_ladder("p-ladder", basis="RECONSTRUCTED", level="2")
    assert result["status"] == "AVAILABLE"
    assert result["snapshot_id"] == "snap-ladder"
    assert result["total"] == 1 and result["items"][0]["security_id"] == "SH.600001"
    assert result["capabilities"]["m8c_reference"] == "PARTIAL"
    assert result["capabilities"]["m8c_rules"] == "PARTIAL"
