import hashlib
from pathlib import Path

import duckdb
import pytest

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationError, MigrationExecutor


ROOT = Path(__file__).parents[2]


def _base_connection(tmp_path):
    connection = duckdb.connect(str(tmp_path / "migration.duckdb"))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    return connection


def test_007_applies_atomically_and_records_hash_identity(tmp_path):
    connection = _base_connection(tmp_path)
    try:
        result = MigrationExecutor(connection).apply()
        assert result["status"] == "APPLIED"
        assert result["applied"][0]["version"] == "007_history_identity"
        assert set(connection.execute("select version from schema_migrations").fetchall()) == {(BASE_SCHEMA_VERSION,), ("007_history_identity",), ("008_technical_history",), ("008_technical_history_rps",), ("009_sector_base_history",), ("010_historical_structure",), ("008_m8_contract_completion",), ("011_m9_sector_cycle",), ("012_m9_member_state",), ("013_m9_representative_state",), ("014_m10_mainline",), ("015_m9_sector_hierarchy",), ("016_m10_common_breadth",), ("017_m9_cycle_state_metrics",), ("018_m10_sector_amount",), ("019_m11_association",), ("020_m13_limit_ladder",), ("021_m13_limit_promotion",), ("022_m13_market_cycle",), ("023_m8c_audit_v11",), ("024_m14_online",), ("025_v3_relations",), ("026_v3_result_objects",), ("027_v3_technical_result_rows",), ("028_v3_strength_result_rows",), ("029_v3_high_result_rows",), ("030_v3_member_state_result_rows",), ("031_v3_structure_result_rows",), ("032_v3_structure_summary_result_rows",), ("033_v3_online_events",), ("034_v3_signal_outcomes",)}
        assert connection.execute("select count(*) from schema_migration_checks").fetchone()[0] == 30
        stored = connection.execute("select sql_sha256 from schema_migration_checks where version='007_history_identity'").fetchone()[0]
        expected = hashlib.sha256((ROOT / "src/workbench_db/migrations/007_history_identity.sql").read_text(encoding="utf-8").encode()).hexdigest()
        assert stored == expected
        assert connection.execute("select count(*) from analysis_snapshots").fetchone()[0] == 0
        assert "stock_technical_daily" in {row[0] for row in connection.execute("show tables").fetchall()}
        assert "stock_high_daily" in {row[0] for row in connection.execute("show tables").fetchall()}
        assert "stock_strength_daily" in {row[0] for row in connection.execute("show tables").fetchall()}
        assert "sector_base_daily" in {row[0] for row in connection.execute("show tables").fetchall()}
        assert "historical_structure_daily" in {row[0] for row in connection.execute("show tables").fetchall()}
        assert "stock_structure_summary_daily" in {row[0] for row in connection.execute("show tables").fetchall()}
        assert "historical_coverage_daily" in {row[0] for row in connection.execute("show tables").fetchall()}
        assert "trade_date" in {row[1] for row in connection.execute("pragma table_info('market_reference_daily')").fetchall()}
        assert {"sector_amount_vs_prior20", "amount_quality_codes", "amount_comparison_evidence"}.issubset({row[1] for row in connection.execute("pragma table_info('sector_cycle_daily')").fetchall()})
        assert {"current_sector_amount_vs_prior20", "sector_amount_comparison_evidence"}.issubset({row[1] for row in connection.execute("pragma table_info('mainline_daily')").fetchall()})
        assert "stock_sector_associations_daily" in {row[0] for row in connection.execute("show tables").fetchall()}
        assert {"limit_state", "streak_known", "streak_min_known", "ladder_level"}.issubset({row[1] for row in connection.execute("pragma table_info('limit_ladder_daily')").fetchall()})
        assert {"previous_level", "success_count", "eligible_count", "excluded_unknown", "excluded_suspended", "excluded_no_limit", "rate"}.issubset({row[1] for row in connection.execute("pragma table_info('limit_promotion_daily')").fetchall()})
        assert {"display_count", "quote_valid_count", "field_coverage", "capabilities"}.issubset({row[1] for row in connection.execute("pragma table_info('market_cycle_daily')").fetchall()})
        assert {"data_sources", "online_fetch_runs", "online_payloads", "online_batches", "online_rank_entries", "online_security_map"}.issubset({row[0] for row in connection.execute("show tables").fetchall()})
    finally:
        connection.close()


def test_failed_sql_rolls_back_tables_and_version_registration(tmp_path):
    connection = _base_connection(tmp_path)
    migration_dir = tmp_path / "migrations"
    migration_dir.mkdir()
    (migration_dir / "007_history_identity.sql").write_text("create table should_rollback (id integer);", encoding="utf-8")
    (migration_dir / "008_bad.sql").write_text("create table should_also_rollback (id integer); this is not valid sql;", encoding="utf-8")
    try:
        with pytest.raises(MigrationError, match="MIGRATION_APPLY_FAILED:008_bad"):
            MigrationExecutor(connection, migration_dir).apply()
        assert connection.execute("select count(*) from schema_migrations where version like '00%'").fetchone()[0] == 0
        assert "should_rollback" not in {row[0] for row in connection.execute("show tables").fetchall()}
        assert "should_also_rollback" not in {row[0] for row in connection.execute("show tables").fetchall()}
    finally:
        connection.close()


def test_applied_sql_change_is_rejected(tmp_path):
    connection = _base_connection(tmp_path)
    migration_dir = tmp_path / "migrations"
    migration_dir.mkdir()
    path = migration_dir / "007_history_identity.sql"
    path.write_text("create table immutable_contract (id integer);", encoding="utf-8")
    try:
        MigrationExecutor(connection, migration_dir).apply()
        path.write_text("create table immutable_contract (id bigint);", encoding="utf-8")
        with pytest.raises(MigrationError, match="MIGRATION_HASH_MISMATCH:007_history_identity"):
            MigrationExecutor(connection, migration_dir).apply()
    finally:
        connection.close()
