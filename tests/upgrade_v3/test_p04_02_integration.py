from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_service.build_planner import DependencySummary, build_plan
from workbench_service.v3_daily_entry import run_v3_daily_entry


ROOT = Path(__file__).parents[2]


def _sessions(count=75):
    values = []
    cursor = date(2026, 1, 2)
    while len(values) < count:
        if cursor.weekday() < 5:
            values.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return values


def _source(tmp_path, sessions):
    rows = []
    for security_id, offset in (("A", 0.0), ("B", 4.0)):
        for index, value in enumerate(sessions):
            close = 10.0 + offset + index * 0.1
            rows.append(
                {
                    "security_id": security_id,
                    "date": value,
                    "raw_close": close,
                    "adj_close": close,
                    "raw_amount": 100.0 + index,
                    "raw_volume": 1000.0 + index,
                    "data_quality_flag": "OK",
                    "is_synthetic_fill": False,
                }
            )
    path = tmp_path / "adjusted_daily.parquet"
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def _database(tmp_path, cutoff):
    database = tmp_path / "v3-entry.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    receipt = MigrationExecutor(connection).apply()
    assert receipt["applied"][-1]["version"] == "032_v3_structure_summary_result_rows"
    connection.execute(
        "INSERT INTO publications VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ["pub-v3-entry", cutoff, 1, "SUCCESS", 1, "test", None, "a" * 64, None, None, "fixture", "2026-04-16 08:00:00"],
    )
    # This is the legacy bound source snapshot produced by the existing daily
    # builder.  Its strength slice intentionally has no frame_scope: the
    # integration contract accepts that legacy shape only when the slice is
    # explicitly bound in this source snapshot.
    connection.execute(
        "INSERT INTO analysis_snapshots VALUES (?,?,?,?,?,?,?,?)",
        ["legacy-source", cutoff, "2026-01-02", "CN_A_LISTED_V2", "c" * 64, "d" * 64, "SUCCESS", "2026-04-16 08:00:00"],
    )
    connection.execute(
        "INSERT INTO analysis_slices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ["legacy-strength-slice", "strength", cutoff, "legacy-strength-contract", "e" * 64, "f" * 64, "{}", 2, "1" * 64, "DUCKDB", None, "2026-04-16 08:00:00"],
    )
    connection.execute(
        "INSERT INTO analysis_result_objects VALUES (?,?,?,?,?,?,?,?)",
        ["legacy-strength-object", "strength", "legacy-strength-v1", "legacy", "2" * 64, 2, "DUCKDB", "2026-04-16 08:00:00"],
    )
    connection.execute(
        "INSERT INTO analysis_slice_result_bindings VALUES (?,?,?)",
        ["legacy-strength-slice", "legacy-strength-object", '{"source":"legacy-builder"}'],
    )
    connection.execute(
        "INSERT INTO analysis_snapshot_entries VALUES (?,?,?,?)",
        ["legacy-source", "strength", cutoff, "legacy-strength-slice"],
    )
    connection.execute(
        "INSERT INTO analysis_slices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ["legacy-coverage-slice", "coverage", cutoff, "legacy-coverage-contract", "3" * 64, "4" * 64, "{}", 1, "5" * 64, "DUCKDB", None, "2026-04-16 08:00:00"],
    )
    connection.execute(
        "INSERT INTO analysis_result_objects VALUES (?,?,?,?,?,?,?,?)",
        ["legacy-coverage-object", "coverage", "legacy-coverage-v1", "legacy", "6" * 64, 1, "DUCKDB", "2026-04-16 08:00:00"],
    )
    connection.execute(
        "INSERT INTO analysis_slice_result_bindings VALUES (?,?,?)",
        ["legacy-coverage-slice", "legacy-coverage-object", '{"source":"legacy-builder"}'],
    )
    connection.execute(
        "INSERT INTO analysis_snapshot_entries VALUES (?,?,?,?)",
        ["legacy-source", "coverage", cutoff, "legacy-coverage-slice"],
    )
    connection.execute(
        "INSERT INTO publication_analysis_snapshots VALUES (?,?,?,?)",
        ["pub-v3-entry", "LOCAL_RECONSTRUCTED", "legacy-source", "2026-04-16 08:00:00"],
    )
    connection.close()
    return database


def _seed_source_entries(database, plan):
    """Add legacy source-snapshot entries for every reused plan scope."""

    grouped = sorted({(str(item["domain"]), str(item["trade_date"])) for item in plan["tasks"] if item["domain"] != "technical"})
    with duckdb.connect(str(database)) as connection:
        for index, (domain, trade_date) in enumerate(grouped, start=3):
            if connection.execute(
                "SELECT 1 FROM analysis_snapshot_entries WHERE snapshot_id=? AND domain=? AND trade_date=?",
                ["legacy-source", domain, trade_date],
            ).fetchone():
                continue
            slice_id = f"legacy-{domain}-{trade_date}"
            object_id = f"legacy-object-{domain}-{trade_date}"
            value_hash = f"{index:064x}"
            connection.execute(
                "INSERT INTO analysis_slices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                [slice_id, domain, trade_date, f"legacy-{domain}-contract", value_hash, f"{index + 100:064x}", "{}", 1, f"{index + 200:064x}", "DUCKDB", None, "2026-04-16 08:00:00"],
            )
            connection.execute(
                "INSERT INTO analysis_result_objects VALUES (?,?,?,?,?,?,?,?)",
                [object_id, domain, f"legacy-{domain}-v1", "legacy", f"{index + 300:064x}", 1, "DUCKDB", "2026-04-16 08:00:00"],
            )
            connection.execute(
                "INSERT INTO analysis_slice_result_bindings VALUES (?,?,?)",
                [slice_id, object_id, '{"source":"legacy-builder"}'],
            )
            connection.execute(
                "INSERT INTO analysis_snapshot_entries VALUES (?,?,?,?)",
                ["legacy-source", domain, trade_date, slice_id],
            )


def test_v3_daily_entry_calculates_reuses_binds_and_is_idempotent(tmp_path):
    sessions = _sessions()
    cutoff = sessions[-1]
    source = _source(tmp_path, sessions)
    database = _database(tmp_path, cutoff)

    first = run_v3_daily_entry(
        tmp_path,
        database,
        publication_id="pub-v3-entry",
        source_path=source,
        target_domains=("technical", "strength"),
    )

    assert first["entrypoint"] == "V3_DAILY_INCREMENTAL"
    assert first["status"] == "BUILT"
    assert first["new_fact_rows"] == 2
    assert first["reused_rows"] == 2
    assert first["preserved_legacy_entry_count"] == 1
    assert first["snapshot_binding"]["snapshot_id"].startswith("v3-daily-")
    assert Path(first["plan_artifact"]).is_file()
    assert Path(first["report_artifact"]).is_file()

    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM technical_result_rows").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM analysis_snapshot_entries WHERE snapshot_id=?", [first["snapshot_binding"]["snapshot_id"]]).fetchone()[0] == 3
        assert connection.execute(
            "SELECT snapshot_id FROM publication_analysis_snapshots WHERE publication_id=? AND domain='LOCAL_RECONSTRUCTED'",
            ["pub-v3-entry"],
        ).fetchone()[0] == first["snapshot_binding"]["snapshot_id"]

    second = run_v3_daily_entry(
        tmp_path,
        database,
        publication_id="pub-v3-entry",
        source_path=source,
        target_domains=("technical", "strength"),
    )

    assert second["status"] == "BUILT"
    assert second["new_fact_rows"] == 0
    assert second["reused_rows"] == 4
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM technical_result_rows").fetchone()[0] == 2


def test_v3_daily_entry_accepts_historical_price_revision_plan_scope(tmp_path):
    sessions = _sessions()
    source = _source(tmp_path, sessions)
    database = _database(tmp_path, sessions[-1])
    changed_day = sessions[50]
    previous = DependencySummary(trading_days=tuple(sessions), quote={f"{changed_day}|A": "price-v1"})
    current = DependencySummary(trading_days=tuple(sessions), quote={f"{changed_day}|A": "price-v2"})
    plan = build_plan(
        previous,
        current,
        sessions=sessions,
        security_ids=("A", "B"),
        sector_ids=("S1",),
        security_to_sectors={"A": ("S1",), "B": ("S1",)},
        sector_members={"S1": ("A", "B")},
        cutoff_date=sessions[-1],
        target_domains=("technical", "strength"),
    )
    _seed_source_entries(database, plan)

    report = run_v3_daily_entry(
        tmp_path,
        database,
        publication_id="pub-v3-entry",
        source_path=source,
        plan=plan,
        source_snapshot_id="legacy-source",
        target_domains=("technical", "strength"),
    )

    assert report["status"] == "BUILT"
    technical_tasks = [item for item in plan["tasks"] if item["domain"] == "technical"]
    assert technical_tasks
    assert {item["security_id"] for item in technical_tasks} == {"A"}
    assert min(item["trade_date"] for item in technical_tasks) == changed_day
    assert report["new_fact_rows"] == len(technical_tasks)
    assert report["reused_rows"] > 0


def test_v3_daily_entry_accepts_relation_change_without_technical_recalculation(tmp_path):
    sessions = _sessions()
    source = _source(tmp_path, sessions)
    database = _database(tmp_path, sessions[-1])
    changed_day = sessions[50]
    relationship_key = f"{changed_day}|S1|A"
    previous = DependencySummary(trading_days=tuple(sessions), relationships={relationship_key: "edge-v1"})
    current = DependencySummary(trading_days=tuple(sessions), relationships={relationship_key: "edge-v2"})
    plan = build_plan(
        previous,
        current,
        sessions=sessions,
        security_ids=("A", "B"),
        sector_ids=("S1",),
        security_to_sectors={"A": ("S1",), "B": ("S1",)},
        sector_members={"S1": ("A", "B")},
        cutoff_date=sessions[-1],
        target_domains=("sector_base", "sector_cycle", "mainline", "member_state", "structure", "summary"),
    )
    _seed_source_entries(database, plan)

    report = run_v3_daily_entry(
        tmp_path,
        database,
        publication_id="pub-v3-entry",
        source_path=source,
        plan=plan,
        source_snapshot_id="legacy-source",
        target_domains=("sector_base", "sector_cycle", "mainline", "member_state", "structure", "summary"),
    )

    assert report["status"] == "BUILT"
    assert plan["tasks"]
    assert not any(item["domain"] in {"technical", "strength", "high"} for item in plan["tasks"])
    assert report["new_fact_rows"] == 0
    assert report["reused_rows"] > 0
