import importlib.util
from datetime import datetime
from pathlib import Path

import duckdb

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_service.app import Api


ROOT = Path(__file__).parents[2]


def _builder():
    path = ROOT / "scripts/build_m13_preview.py"
    spec = importlib.util.spec_from_file_location("build_m13_preview", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _source_db(tmp_path):
    path = tmp_path / "m13-materializer.duckdb"
    connection = duckdb.connect(str(path))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("insert into schema_migrations values (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    MigrationExecutor(connection).apply()
    now = datetime(2026, 9, 11, 9, 0, 0)
    connection.execute("insert into publications values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ["p-m13", "2026-09-11", 1, "SUCCESS", 1, "m4-test", "", "", "", "", "", now])
    connection.execute("insert into publication_heads values (?, ?)", ["2026-09-11", "p-m13"])
    connection.execute("insert into analysis_snapshots values (?, ?, ?, ?, ?, ?, ?, ?)", ["snap-source", "2026-09-11", "2026-09-10", "CN_A_LISTED_V2", "config", "manifest", "SUCCESS", now])
    connection.execute("insert into publication_analysis_snapshots values (?, ?, ?, ?)", ["p-m13", "LOCAL_RECONSTRUCTED", "snap-source", now])
    for index, trade_date in enumerate(("2026-09-10", "2026-09-11")):
        slice_id = f"tech-{index}"
        connection.execute("insert into analysis_slices values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [slice_id, "technical", trade_date, "TECHNICAL_HISTORY_V1", "i", "d", "{}", 1, f"logical-{index}", "DUCKDB", None, now])
        connection.execute("insert into analysis_daily_basis values (?, ?, ?, ?, ?, ?, ?, ?)", [slice_id, "CN_A_LISTED_V2", None, "RAW", None, now, 1.0, "{}"])
        connection.execute("insert into analysis_snapshot_entries values (?, ?, ?, ?)", ["snap-source", "technical", trade_date, slice_id])
        connection.execute(
            """insert into stock_technical_daily
               (slice_id,security_id,trade_date,contract_id,price_basis,raw_close,adj_close,quote_ret1,raw_amount,raw_volume,
                ma5,ma10,ma20,ma60,ret5,ret10,ret20,ret60,rs5,rs10,rs20,rs60,amount_ma5,amount_ma10,amount_ma20,
                amount_ratio20,amount_vs_prior20,volume_vs_prior20,amount_class,ma_alignment,validity,quality_codes,basis_json)
               values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [slice_id, "SH.600001", trade_date, "TECHNICAL_HISTORY_V1", "RAW", 11.0 if index == 0 else 12.1, 11.0 if index == 0 else 12.1, 0.01, 100.0, 10.0, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, "VALID", "[]", "{}"],
        )
        connection.execute(
            "insert into market_reference_daily (slice_id,security_id,trade_date,quote_prev_close,limit_up_price,limit_down_price,float_shares,shares_basis,status_known,rule_id,source_ref,observed_at,contract_id,quality_codes,source_snapshot_id,quote_capability,reference_status,reference_basis,exchange,board,risk_status,listing_phase,ex_rights_reference_unknown,rule_verified,source_rule_sha256) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [slice_id, "SH.600001", trade_date, 10.0 if index == 0 else 11.0, 11.0 if index == 0 else 12.1, 9.0 if index == 0 else 9.9, None, None, True, "R1", "local-test", now, "REFERENCE_CAPABILITY_V1_1", "[]", "snap-source", "EXACT", "KNOWN", "LOCAL_EXACT_FIXTURE", "SSE", "MAIN", "NORMAL", "REGULAR", False, True, "fixture-hash"],
        )
        connection.execute("insert into analysis_snapshot_entries values (?,?,?,?)", ["snap-source", "market_reference", trade_date, slice_id])
        connection.execute("insert into security_metadata_versions (security_id,version_id,exchange,board,security_kind,listing_status,valid_from,valid_to,observed_at,source_id,source_ref,risk_status,listing_phase,metadata_confidence,source_snapshot_id) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ["SH.600001", f"META-{index}", "SSE", "MAIN", "A_STOCK", "ACTIVE", trade_date, None, now, "test", "local-test", "NORMAL", "REGULAR", "EXACT", "snap-source"])
    connection.execute("insert into limit_rule_versions (rule_id,exchange,board,risk_status,valid_from,valid_to,limit_ratio,tick,rounding_mode,special_period_policy,source_ref,contract_id,rule_verified,source_sha256,audit_status,audit_reason,audited_at) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ["R1", "SSE", "MAIN", "NORMAL", "2026-01-01", None, 0.1, 0.01, "HALF_UP", "{}", "local-rule", "LIMIT_RULES_V1_1", True, "fixture-hash", "VERIFIED", "fixture", now])
    connection.commit()
    connection.close()
    return path


def test_m13_materializer_builds_bound_domains_and_is_idempotent(tmp_path):
    path = _source_db(tmp_path)
    builder = _builder()
    first = builder.build(path, reference_registry_snapshot_id="snap-source")
    assert first["status"] == "BUILT"
    assert first["inserted"]["market_cycle"] == 2
    assert first["inserted"]["limit_ladder"] == 2
    assert first["inserted"]["limit_promotion"] == 4
    second = builder.build(path, reference_registry_snapshot_id="snap-source")
    assert second["status"] == "ALREADY_BUILT"
    assert second["snapshot_id"] == first["snapshot_id"]

    connection = duckdb.connect(str(path), read_only=True)
    try:
        assert connection.execute("select count(*) from market_cycle_daily").fetchone()[0] == 2
        assert connection.execute("select count(*) from limit_ladder_daily").fetchone()[0] == 2
        assert connection.execute("select count(*) from limit_promotion_daily").fetchone()[0] == 4
        assert connection.execute("select count(*) from analysis_snapshot_entries where snapshot_id=? and domain='market_cycle'", [first["snapshot_id"]]).fetchone()[0] == 2
        assert connection.execute("select count(*) from limit_ladder_daily where slice_id like 'tech-%'").fetchone()[0] == 0
    finally:
        connection.close()

    ladder = Api(path, root=ROOT).limit_ladder("p-m13", basis="RECONSTRUCTED")
    assert ladder["status"] == "AVAILABLE"
    assert ladder["capabilities"]["m8c_reference"] == "BOUND"
    assert ladder["capabilities"]["m8c_rules"] == "BOUND"
    market = Api(path, root=ROOT).market_cycle("p-m13", days=1, basis="RECONSTRUCTED")
    assert len(market["points"]) == 1


def test_m13_materializer_blocks_without_m8c_inputs(tmp_path):
    path = _source_db(tmp_path)
    connection = duckdb.connect(str(path))
    connection.execute("delete from market_reference_daily")
    connection.execute("delete from limit_rule_versions")
    connection.commit()
    connection.close()
    result = _builder().build(path, reference_registry_snapshot_id="snap-source")
    assert result["status"] == "BLOCKED_INPUTS_MISSING"
    assert result["writes"] == 0


def test_m13_materializer_requires_explicit_reference_registry_id(tmp_path):
    path = _source_db(tmp_path)
    result = _builder().build(path)
    assert result["status"] == "BLOCKED_REFERENCE_REGISTRY_ID_REQUIRED"
    assert result["writes"] == 0


def test_m13_materializer_preserves_known_empty_technical_date(tmp_path):
    path = _source_db(tmp_path)
    connection = duckdb.connect(str(path))
    connection.execute("delete from stock_technical_daily where trade_date='2026-09-10'")
    connection.commit()
    connection.close()
    result = _builder().build(path, reference_registry_snapshot_id="snap-source")
    assert result["status"] == "BUILT"
    market = Api(path, root=ROOT).market_cycle("p-m13", days=2, basis="RECONSTRUCTED")
    assert market["points"][0]["trade_date"] == "2026-09-10"
    assert market["points"][0]["display_count"] == 0
