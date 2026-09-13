import ast
from datetime import date
import importlib.util
from pathlib import Path

import duckdb
import pandas as pd

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor


ROOT = Path(__file__).parents[2]


def test_run_today_uses_single_incremental_analysis_process():
    source = (ROOT / "src/workbench_service/app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    run_today = next(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "run_today"
    )
    segment = ast.get_source_segment(source, run_today)
    assert "'--incremental-current'" in segment
    assert "run_v3_daily_entry(" not in segment
    assert segment.count("build_m8_m9_preview.py") == 1


def test_incremental_preview_filters_inputs_and_preserves_history():
    source = (ROOT / "scripts/build_m8_m9_preview.py").read_text(encoding="utf-8")
    assert 'membership = membership[membership["trade_date"].eq(cutoff)].copy()' in source
    assert "preserve_prior_entries=args.incremental_current" in source
    assert '"full_window_rebuild": False' in source
    assert 'ROOT / "reports/v3/daily"' in source


def test_incremental_preview_preserves_prior_dates_without_rewriting_them(tmp_path, monkeypatch):
    module_path = ROOT / "scripts/build_m8_m9_preview.py"
    spec = importlib.util.spec_from_file_location("v3_incremental_preview_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    database = tmp_path / "preview.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
        connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
        MigrationExecutor(connection).apply()
        connection.execute(
            "INSERT INTO publications VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            ["pub", "2026-09-10", 1, "SUCCESS", 1, "test", None, "a" * 64, None, None, "fixture", "2026-09-10 08:00:00"],
        )
        connection.execute("INSERT INTO publication_heads VALUES (?,?)", [date(2026, 9, 10), "pub"])
        connection.execute(
            "INSERT INTO analysis_snapshots VALUES (?,?,?,?,?,?,?,?)",
            ["prior", "2026-09-09", "2026-09-08", "CN_A_LISTED_V2", "ba" * 64, "b" * 64, "SUCCESS", "2026-09-10 08:00:00"],
        )
        connection.execute(
            "INSERT INTO analysis_slices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            ["prior-technical", "technical", "2026-09-09", "old", "c" * 64, "d" * 64, "{}", 1, "e" * 64, "DUCKDB", None, "2026-09-10 08:00:00"],
        )
        connection.execute("INSERT INTO analysis_snapshot_entries VALUES (?,?,?,?)", ["prior", "technical", "2026-09-09", "prior-technical"])
        connection.execute("INSERT INTO publication_analysis_snapshots VALUES (?,?,?,?)", ["pub", "LOCAL_RECONSTRUCTED", "prior", "2026-09-10 08:00:00"])
        connection.execute(
            "INSERT INTO tdx_sector_hierarchy_versions VALUES (?,?,?,?,?,?,?)",
            ["hierarchy", "test", "fixture", "{}", "hash", "2026-09-10 08:00:00", "2026-09-10 08:00:00"],
        )

    monkeypatch.setattr(module, "DB_PATH", database)
    monkeypatch.setattr(module, "ensure_hierarchy", lambda *_args, **_kwargs: ("hierarchy", "hash", 0))
    monkeypatch.setattr(module, "build_semantic_version_rows", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(module, "insert_semantic_version_rows", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(module, "insert_technical_result_rows", lambda *_args, **_kwargs: 1)

    result = module.insert_preview(
        {"technical": pd.DataFrame([{"trade_date": date(2026, 9, 10), "security_id": "A"}])},
        [date(2026, 9, 10)],
        date(2026, 9, 1),
        {"normalized": "n", "membership": "m"},
        pd.DataFrame([{"trade_date": date(2026, 9, 10), "sector_id": "S", "security_id": "A"}]),
        {"membership_fallback": "m"},
        "membership-v1",
        preserve_prior_entries=True,
    )

    assert result["preserved_entry_count"] == 1
    with duckdb.connect(str(database), read_only=True) as connection:
        entries = connection.execute(
            "SELECT domain,cast(trade_date as varchar),slice_id FROM analysis_snapshot_entries WHERE snapshot_id=? ORDER BY trade_date",
            [result["snapshot_id"]],
        ).fetchall()
    assert entries[0] == ("technical", "2026-09-09", "prior-technical")
    assert entries[1][0:2] == ("technical", "2026-09-10")

    with duckdb.connect(str(database)) as connection:
        connection.execute(
            "INSERT INTO publications VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            ["pub-2", "2026-09-10", 2, "SUCCESS", 1, "test", None, "f" * 64, None, None, "fixture", "2026-09-10 09:00:00"],
        )
        connection.execute("UPDATE publication_heads SET publication_id='pub-2' WHERE trade_date=?", [date(2026, 9, 10)])
    reused = module.insert_preview(
        {"technical": pd.DataFrame([{"trade_date": date(2026, 9, 10), "security_id": "A"}])},
        [date(2026, 9, 10)],
        date(2026, 9, 1),
        {"normalized": "n", "membership": "m"},
        pd.DataFrame([{"trade_date": date(2026, 9, 10), "sector_id": "S", "security_id": "A"}]),
        {"membership_fallback": "m"},
        "membership-v1",
        preserve_prior_entries=True,
    )
    assert reused["status"] == "ALREADY_BUILT"
    assert reused["binding_reused"] is True
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute(
            "SELECT snapshot_id FROM publication_analysis_snapshots WHERE publication_id='pub-2' AND domain='LOCAL_RECONSTRUCTED'"
        ).fetchone()[0] == result["snapshot_id"]
