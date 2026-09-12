import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_online.base import FetchResult, OnlineFetchPolicy
from workbench_online.collector import _commit_raw_and_batch
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
        assert result["applied"][-1]["version"] == "026_v3_result_objects"
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        assert {"online_fetch_runs", "online_payloads", "online_batches", "online_rank_entries", "online_security_map", "online_evidence", "online_quote_entries"}.issubset(tables)
    finally:
        connection.close()


def test_personal_registry_does_not_enable_production_adapter():
    registry = json.loads((ROOT / "config/m14_source_registry_v1.json").read_text(encoding="utf-8"))
    ths = next(item for item in registry["source_candidates"] if item["source_id"] == "TONGHUASHUN_HOT_RANK")
    assert registry["personal_research_mode"] is True
    assert registry["publication_enabled"] is False
    assert registry["production_adapters_enabled"] is False
    assert ths["personal_collection_enabled"] is True
    assert ths["enabled"] is False


def test_batch_commit_rolls_back_new_raw_when_batch_commit_fails(tmp_path):
    raw_path = tmp_path / "raw" / "payload.json"
    batch_path = tmp_path / "batches" / "batch.json"
    batch_path.mkdir(parents=True)
    try:
        _commit_raw_and_batch(raw_path, b"payload", batch_path, {"batch_id": "b1"})
    except OSError:
        pass
    else:
        raise AssertionError("a directory at the batch target must fail the commit")
    assert not raw_path.exists()
    assert not list((tmp_path / "raw").glob("*"))
