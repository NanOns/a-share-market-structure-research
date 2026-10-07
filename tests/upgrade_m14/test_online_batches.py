import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_online.base import FetchResult, OnlineFetchPolicy
from workbench_online.collector import collect_ths_hot_rank, collect_eastmoney_hot_rank, HotRankCaptureDisabled
import pytest
from workbench_online.ths_hot_rank import fetch_ths_hot_rank


ROOT = Path(__file__).parents[2]


def _fake_fetcher(_url, _policy, **_kwargs):
    payload = {
        "status_code": 0,
        "data": {
            "stock_list": [
                {"market": 33, "code": "000001", "name": "平安银行", "order": 1, "hot_rank_chg": 2},
                {"market": 17, "code": "600000", "name": "浦发银行", "order": 2, "hot_rank_chg": -1},
            ]
        },
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    now = datetime.now(timezone.utc).isoformat()
    return FetchResult(now, now, 200, "application/json", body, "https://example.invalid/hot")


def test_ths_normalization_uses_explicit_market_mapping_and_preserves_platform_rank():
    result, normalized = fetch_ths_hot_rank(OnlineFetchPolicy(), fetcher=_fake_fetcher)
    assert result.status_code == 200
    assert normalized["capability_status"] == "PERSONAL_RESEARCH_ONLY"
    assert normalized["source_as_of"] is None
    assert [row["platform_rank"] for row in normalized["rows"]] == [1, 2]
    assert [row["security_id"] for row in normalized["rows"]] == ["SZ.000001", "SH.600000"]


def test_online_migration_is_transactionally_available(tmp_path):
    connection = duckdb.connect(str(tmp_path / "m14.duckdb"))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    try:
        result = MigrationExecutor(connection).apply()
        assert "034_v3_signal_outcomes" in {row["version"] for row in result["applied"]}
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        assert {"online_fetch_runs", "online_payloads", "online_batches", "online_rank_entries", "online_security_map", "online_evidence", "online_quote_entries"}.issubset(tables)
    finally:
        connection.close()


def test_historical_registry_does_not_enable_retired_capture(tmp_path):
    registry = json.loads((ROOT / "config/m14_source_registry_v1.json").read_text(encoding="utf-8"))
    assert registry["publication_enabled"] is False
    assert registry["production_adapters_enabled"] is False
    # Historical collection metadata is not an executable capability grant.
    for collect in (collect_ths_hot_rank, collect_eastmoney_hot_rank):
        with pytest.raises(HotRankCaptureDisabled, match="HOT_RANK_CAPTURE_DISABLED_REQUEST_TIME_ONLY"):
            collect(tmp_path)
    assert list(tmp_path.rglob("*")) == []


def test_capture_disabled_even_with_existing_migration_tables(tmp_path):
    database=tmp_path/"historical_schema.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute("create table online_batches(batch_id varchar)")
    before={p.relative_to(tmp_path).as_posix():p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    for collect in (collect_ths_hot_rank,collect_eastmoney_hot_rank):
        with pytest.raises(HotRankCaptureDisabled):collect(tmp_path)
    after={p.relative_to(tmp_path).as_posix():p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert after==before
