from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from workbench_analysis.technical import CONTRACT_VERSION as TECHNICAL_CONTRACT
from workbench_analysis.technical import TECHNICAL_RESULT_PRIMARY_KEY, calculate_technical_daily
from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_service.build_planner import DependencySummary, build_plan
from workbench_service.incremental_writer import (
    IncrementalBuildCoordinator,
    IncrementalBuildError,
    PreparedBuildObject,
    SnapshotBinding,
)


ROOT = Path(__file__).parents[2]


def _sessions(count=75):
    values = []
    cursor = date(2026, 1, 2)
    while len(values) < count:
        if cursor.weekday() < 5:
            values.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return values


def _database(tmp_path):
    database = tmp_path / "incremental.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    receipt = MigrationExecutor(connection).apply()
    assert receipt["applied"][-1]["version"] == "032_v3_structure_summary_result_rows"
    connection.execute(
        "INSERT INTO publications VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ["pub-incremental", "2026-04-20", 1, "SUCCESS", 1, "test", None, "a" * 64, None, None, "fixture", "2026-04-20 08:00:00"],
    )
    connection.close()
    return database


def _plan(sessions):
    changed = sessions[5]
    previous = DependencySummary(trading_days=tuple(sessions), quote={f"{changed}|A": "price-v1"})
    current = DependencySummary(trading_days=tuple(sessions), quote={f"{changed}|A": "price-v2"})
    return build_plan(
        previous,
        current,
        sessions=sessions,
        security_ids=["A"],
        security_to_sectors={"A": []},
        cutoff_date=sessions[-1],
    )


def _objects(plan, sessions, count=2):
    frame = pd.DataFrame({
        "security_id": ["A"] * len(sessions),
        "date": pd.to_datetime(sessions),
        "raw_close": [10.0 + index * 0.1 for index in range(len(sessions))],
        "adj_close": [10.0 + index * 0.1 for index in range(len(sessions))],
        "raw_amount": [100.0 + index for index in range(len(sessions))],
        "raw_volume": [1000.0 + index for index in range(len(sessions))],
        "data_quality_flag": ["OK"] * len(sessions),
        "is_synthetic_fill": [False] * len(sessions),
    })
    calculated = calculate_technical_daily(frame)
    technical_tasks = [item for item in plan["tasks"] if item["domain"] == "technical"][:count]
    objects = []
    for task in technical_tasks:
        daily = calculated[calculated["date"].astype(str).eq(task["trade_date"])].copy()
        assert len(daily) == 1
        objects.append(
            PreparedBuildObject.from_frame(
                task,
                daily,
                plan_id=plan["plan_id"],
                contract_id=TECHNICAL_CONTRACT,
                basis={"source_manifest_sha256": "b" * 64, "source_bundle_id": "fixture-bundle"},
                primary_key=("security_id", "date"),
            )
        )
    return objects


def test_real_technical_writer_repeated_three_times_adds_no_business_rows_on_retries(tmp_path):
    sessions = _sessions()
    plan = _plan(sessions)
    objects = _objects(plan, sessions, count=2)
    coordinator = IncrementalBuildCoordinator(_database(tmp_path))

    first = coordinator.execute(plan, objects)
    second = coordinator.execute(plan, objects)
    third = coordinator.execute(plan, objects)

    assert first["status"] == "BUILT"
    assert first["new_fact_rows"] == 2
    assert second["new_fact_rows"] == 0
    assert third["new_fact_rows"] == 0
    assert second["reused_result_objects"] == 2
    assert third["reused_result_objects"] == 2
    assert first["db_file_growth_bytes"] >= 0
    with duckdb.connect(str(coordinator.database_path), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM technical_result_rows").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM analysis_slice_result_bindings").fetchone()[0] == 2


def test_snapshot_binding_is_committed_only_after_all_planned_objects_succeed(tmp_path):
    sessions = _sessions()
    plan = _plan(sessions)
    objects = _objects(plan, sessions, count=2)
    database = _database(tmp_path)
    coordinator = IncrementalBuildCoordinator(database)
    binding = SnapshotBinding(
        snapshot_id="snapshot-incremental-1",
        publication_id="pub-incremental",
        binding_domain="LOCAL_RECONSTRUCTED",
        cutoff_date=sessions[-1],
        query_start=sessions[0],
        config_hash="c" * 64,
        manifest_hash="d" * 64,
        expected_task_keys=tuple(item.task_key for item in objects),
    )

    result = coordinator.execute(plan, objects, snapshot=binding)

    assert result["snapshot_binding"]["snapshot_id"] == binding.snapshot_id
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM analysis_snapshots WHERE snapshot_id=?", [binding.snapshot_id]).fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM analysis_snapshot_entries WHERE snapshot_id=?", [binding.snapshot_id]).fetchone()[0] == 2
        assert connection.execute("SELECT snapshot_id FROM publication_analysis_snapshots WHERE publication_id=?", [binding.publication_id]).fetchone()[0] == binding.snapshot_id


def test_same_domain_date_tasks_can_share_one_slice_before_snapshot_binding(tmp_path):
    sessions = _sessions()
    previous = DependencySummary(trading_days=tuple(sessions[:-1]))
    current = DependencySummary(trading_days=tuple(sessions))
    plan = build_plan(previous, current, sessions=sessions, security_ids=["A", "B"], cutoff_date=sessions[-1])
    latest_tasks = [item for item in plan["tasks"] if item["domain"] == "technical" and item["trade_date"] == sessions[-1]]
    assert {item["security_id"] for item in latest_tasks} == {"A", "B"}
    frame = pd.DataFrame({
        "security_id": ["A"] * len(sessions) + ["B"] * len(sessions),
        "date": pd.to_datetime(sessions + sessions),
        "raw_close": [10.0 + index * 0.1 for index in range(len(sessions))] * 2,
        "adj_close": [10.0 + index * 0.1 for index in range(len(sessions))] * 2,
        "raw_amount": [100.0 + index for index in range(len(sessions))] * 2,
        "raw_volume": [1000.0 + index for index in range(len(sessions))] * 2,
        "data_quality_flag": ["OK"] * (len(sessions) * 2),
        "is_synthetic_fill": [False] * (len(sessions) * 2),
    })
    calculated = calculate_technical_daily(frame)
    daily = calculated[calculated["date"].astype(str).eq(sessions[-1])].copy()
    combined = PreparedBuildObject.from_frame(
        latest_tasks[0],
        daily,
        plan_id=plan["plan_id"],
        contract_id=TECHNICAL_CONTRACT,
        primary_key=("security_id", "date"),
        covered_task_keys=[latest_tasks[1]["task_key"]],
    )
    database = _database(tmp_path)
    binding = SnapshotBinding(
        snapshot_id="snapshot-incremental-grouped",
        publication_id="pub-incremental",
        binding_domain="LOCAL_RECONSTRUCTED",
        cutoff_date=sessions[-1],
        query_start=sessions[0],
        config_hash="1" * 64,
        manifest_hash="2" * 64,
        expected_task_keys=tuple(item["task_key"] for item in latest_tasks),
    )

    result = IncrementalBuildCoordinator(database).execute(plan, [combined], snapshot=binding)

    assert result["executed_task_count"] == 2
    assert result["executed_object_count"] == 1
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM technical_result_rows").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM analysis_snapshot_entries WHERE snapshot_id=?", [binding.snapshot_id]).fetchone()[0] == 1


def test_failed_domain_writer_rolls_back_rows_and_does_not_bind_snapshot(tmp_path):
    sessions = _sessions()
    plan = _plan(sessions)
    objects = _objects(plan, sessions, count=2)
    database = _database(tmp_path)
    calls = {"count": 0}

    def failing_writer(connection, slice_id, frame):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("intentional-domain-failure")
        from workbench_analysis.technical import insert_technical_result_rows

        return insert_technical_result_rows(connection, slice_id, frame)

    coordinator = IncrementalBuildCoordinator(database, writers={"technical": failing_writer})
    binding = SnapshotBinding(
        snapshot_id="snapshot-incremental-failed",
        publication_id="pub-incremental",
        binding_domain="LOCAL_RECONSTRUCTED",
        cutoff_date=sessions[-1],
        query_start=sessions[0],
        config_hash="e" * 64,
        manifest_hash="f" * 64,
        expected_task_keys=tuple(item.task_key for item in objects),
    )

    with pytest.raises(RuntimeError, match="intentional-domain-failure"):
        coordinator.execute(plan, objects, snapshot=binding)
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM analysis_slices").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM analysis_snapshots").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM publication_analysis_snapshots").fetchone()[0] == 0


def test_object_outside_build_plan_is_rejected_before_database_write(tmp_path):
    sessions = _sessions()
    plan = _plan(sessions)
    objects = _objects(plan, sessions, count=1)
    task = dict(next(item for item in plan["tasks"] if item["domain"] == "technical"))
    task["security_id"] = "B"
    task.pop("task_key")
    frame = pd.DataFrame({
        "security_id": ["A"],
        "date": pd.to_datetime([task["trade_date"]]),
        "raw_close": [10.0],
        "adj_close": [10.0],
        "raw_amount": [100.0],
        "raw_volume": [1000.0],
        "data_quality_flag": ["OK"],
        "is_synthetic_fill": [False],
    })
    rogue = PreparedBuildObject.from_frame(task, calculate_technical_daily(frame), plan_id=plan["plan_id"], contract_id=TECHNICAL_CONTRACT, primary_key=("security_id", "date"))

    with pytest.raises(IncrementalBuildError, match="BUILD_OBJECT_NOT_IN_PLAN"):
        IncrementalBuildCoordinator(_database(tmp_path)).execute(plan, [objects[0], rogue])
