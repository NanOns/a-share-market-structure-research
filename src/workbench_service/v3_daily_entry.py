"""V3 P04-02 daily entry integration.

The legacy daily job remains responsible for producing the current compatible
publication and its already-bound analytical slices.  This entry then uses a
V3 build plan to calculate the technical domain from the real normalized
source, explicitly reuse the other target-domain slices from that bound
snapshot, and atomically bind a complete V3 target snapshot.  Unsupported
domains are never silently omitted: callers must keep them outside the target
context or receive the executor's fail-closed error.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping

import duckdb
import pandas as pd

from workbench_db import DuckDBIncrementalWriterRepository, IncrementalWriterRepository
from .build_planner import DependencySummary, build_plan, task_key, verify_build_plan
from .incremental_writer import (
    DomainExecutor,
    IncrementalBuildCoordinator,
    IncrementalBuildError,
    ReusedBuildObject,
    SnapshotBinding,
    default_executor_matrix,
    write_growth_report,
)


# These are the domains for which the current P03 migration provides immutable
# V3 result objects. Legacy-only domains remain copied into the new snapshot
# for compatibility, but are not silently promoted to V3 target completeness.
# A caller that explicitly includes an absent/unbound domain still fails closed
# in _reuse_entries.
V3_DAILY_TARGET_DOMAINS = (
    "technical",
    "strength",
    "high",
    "structure",
    "summary",
    "member_state",
)


def _sync_postgres_if_enabled(root: Path, trade_date: str) -> dict[str, Any] | None:
    """Fail closed if the standalone V3 entry leaves PostgreSQL stale."""
    if str(os.environ.get("WORKBENCH_API_BACKEND", "")).lower() != "postgresql":
        return None
    result = subprocess.run(
        [sys.executable, str(root / "scripts/sync_latest_publication_to_postgres.py"), "--trade-date", str(trade_date)],
        cwd=root, capture_output=True, text=True, timeout=3600,
    )
    if result.returncode:
        raise IncrementalBuildError("POSTGRES_SYNC_FAILED:" + (result.stderr[-1000:] or result.stdout[-1000:]))
    try:
        payload = json.loads(result.stdout)
    except Exception as exc:
        raise IncrementalBuildError("POSTGRES_SYNC_REPORT_INVALID") from exc
    if payload.get("status") != "FULL_PASS":
        raise IncrementalBuildError("POSTGRES_SYNC_FAILED:" + str(payload.get("error") or "sync did not pass"))
    return payload


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _date_column(frame: pd.DataFrame) -> str:
    if "date" in frame.columns:
        return "date"
    if "trade_date" in frame.columns:
        return "trade_date"
    raise IncrementalBuildError("V3_DAILY_SOURCE_DATE_COLUMN_REQUIRED")


def _iso(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise IncrementalBuildError(f"DATE_INVALID:{value}") from exc


def _load_source(path: Path) -> tuple[pd.DataFrame, tuple[str, ...]]:
    if not path.is_file():
        raise IncrementalBuildError(f"V3_DAILY_SOURCE_NOT_FOUND:{path}")
    frame = pd.read_parquet(path)
    column = _date_column(frame)
    frame = frame.copy()
    frame[column] = pd.to_datetime(frame[column], errors="raise").dt.date
    sessions = tuple(sorted({value.isoformat() for value in frame[column].dropna().unique()}))
    if len(sessions) < 2:
        raise IncrementalBuildError("V3_DAILY_SOURCE_NEEDS_PREVIOUS_SESSION")
    if "security_id" not in frame.columns:
        raise IncrementalBuildError("V3_DAILY_SOURCE_SECURITY_ID_REQUIRED")
    return frame, sessions


class _ParquetSourceReader:
    """Read only the rows needed by one verified V3 task.

    The normalized source is a large immutable parquet input. Loading the
    entire file into pandas before filtering can require a multi-gigabyte
    temporary allocation. Row-group reads keep the source read-only and only
    materialize the requested security/date window.
    """

    _TECHNICAL_COLUMNS = (
        "security_id", "date", "raw_close", "adj_close", "raw_amount",
        "raw_volume", "data_quality_flag", "is_synthetic_fill", "quote_prev_close",
    )

    def __init__(self, path: Path):
        self.path = path
        if not path.is_file():
            raise IncrementalBuildError(f"V3_DAILY_SOURCE_NOT_FOUND:{path}")
        try:
            from pyarrow import parquet as pq
        except ImportError as exc:
            raise IncrementalBuildError("V3_DAILY_PARQUET_READER_REQUIRED") from exc
        self.parquet = pq.ParquetFile(str(path))
        self.columns = set(self.parquet.schema.names)
        required = {"security_id", "date", "adj_close", "raw_close", "raw_amount", "raw_volume"}
        missing = sorted(required.difference(self.columns))
        if missing:
            raise IncrementalBuildError("V3_DAILY_SOURCE_COLUMNS_MISSING:" + ",".join(missing))
        self._security_groups: dict[str, list[int]] = {}
        self._unknown_groups: list[int] = []
        security_index = self.parquet.schema.names.index("security_id")
        for group_index in range(self.parquet.num_row_groups):
            statistics = self.parquet.metadata.row_group(group_index).column(security_index).statistics
            if statistics is not None and statistics.min == statistics.max and statistics.min is not None:
                self._security_groups.setdefault(str(statistics.min), []).append(group_index)
            else:
                self._unknown_groups.append(group_index)
        session_values: set[str] = set()
        for batch in self.parquet.iter_batches(columns=["date"], batch_size=1_000_000):
            session_values.update(
                str(value)[:10]
                for value in batch.column(0).unique().to_pylist()
                if value is not None
            )
        self.sessions = tuple(sorted(session_values))
        if len(self.sessions) < 2:
            raise IncrementalBuildError("V3_DAILY_SOURCE_NEEDS_PREVIOUS_SESSION")
        self._security_cache: dict[str, tuple[str, ...]] = {}

    def close(self) -> None:
        return None

    def _read_group(self, group_index: int, columns: list[str], *, tail_rows: int | None = None) -> pd.DataFrame:
        table = self.parquet.read_row_group(group_index, columns=columns)
        if tail_rows is not None and table.num_rows > tail_rows:
            table = table.slice(table.num_rows - tail_rows)
        frame = table.to_pandas()
        if "date" in frame:
            frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.date
        if "security_id" in frame:
            frame["security_id"] = frame["security_id"].astype(str)
        return frame

    def _all_group_indexes(self) -> list[int]:
        known = {index for values in self._security_groups.values() for index in values}
        return sorted(known | set(self._unknown_groups))

    def current_security_ids(self, cutoff: str) -> tuple[str, ...]:
        cached = self._security_cache.get(str(cutoff))
        if cached is not None:
            return cached
        result_ids: set[str] = set()
        for group_index in self._all_group_indexes():
            frame = self._read_group(group_index, ["security_id", "date"])
            matched = frame[frame["date"].astype(str).eq(str(cutoff))]
            result_ids.update(str(value) for value in matched["security_id"].dropna().tolist())
        result = tuple(sorted(result_ids))
        if not result:
            raise IncrementalBuildError("V3_DAILY_CURRENT_UNIVERSE_EMPTY")
        self._security_cache[str(cutoff)] = result
        return result

    def frame_for_task(self, task: Mapping[str, Any]) -> pd.DataFrame:
        cutoff = _iso(task["trade_date"])
        if cutoff not in self.sessions:
            raise IncrementalBuildError(f"V3_DAILY_TASK_DATE_NOT_IN_SOURCE:{cutoff}")
        end_index = self.sessions.index(cutoff)
        # Technical RET60 needs the current session plus 60 preceding source
        # sessions. This is an input lookback, not an output range.
        start = self.sessions[max(0, end_index - 60)]
        security_ids = tuple(sorted({str(value) for value in task.get("security_ids", ()) if value}))
        if not security_ids and task.get("security_id") is not None:
            security_ids = (str(task["security_id"]),)
        if not security_ids:
            raise IncrementalBuildError(f"V3_DAILY_TASK_SECURITY_SCOPE_REQUIRED:{task_key(task)}")
        selected = set(security_ids)
        selected_columns = [name for name in self._TECHNICAL_COLUMNS if name in self.columns]
        if len(selected) > 1000:
            group_indexes = self._all_group_indexes()
        else:
            group_indexes = sorted({index for security_id in selected for index in self._security_groups.get(security_id, ())})
            group_indexes.extend(index for index in self._unknown_groups if index not in group_indexes)
        parts: list[pd.DataFrame] = []
        start_date = date.fromisoformat(start)
        cutoff_date = date.fromisoformat(cutoff)
        tail_rows = 61 if len(selected) > 1000 and cutoff == self.sessions[-1] else None
        for group_index in group_indexes:
            frame = self._read_group(group_index, selected_columns, tail_rows=tail_rows)
            if len(selected) <= 1000:
                frame = frame[frame["security_id"].isin(selected)]
            frame = frame[(frame["date"] >= start_date) & (frame["date"] <= cutoff_date)]
            if not frame.empty:
                parts.append(frame)
        if not parts:
            raise IncrementalBuildError(f"V3_DAILY_SOURCE_SCOPE_EMPTY:{cutoff}")
        return pd.concat(parts, ignore_index=True).sort_values(["security_id", "date"], kind="mergesort").reset_index(drop=True)


def _load_membership(path: Path | None, cutoff: str) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]], tuple[str, ...]]:
    if path is None or not path.is_file():
        return {}, {}, ()
    frame = pd.read_parquet(path)
    column = _date_column(frame)
    required = {column, "sector_id", "security_id"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise IncrementalBuildError("V3_DAILY_MEMBERSHIP_COLUMNS_MISSING:" + ",".join(missing))
    frame = frame.copy()
    frame[column] = pd.to_datetime(frame[column], errors="raise").dt.date.astype(str)
    current = frame[frame[column].eq(cutoff)].copy()
    if current.empty:
        return {}, {}, ()
    current["sector_id"] = current["sector_id"].astype(str)
    current["security_id"] = current["security_id"].astype(str)
    sector_members: dict[str, tuple[str, ...]] = {}
    security_sectors: dict[str, tuple[str, ...]] = {}
    for sector_id, rows in current.groupby("sector_id", sort=True):
        sector_members[f"{cutoff}|{sector_id}"] = tuple(sorted(set(rows["security_id"])))
    for security_id, rows in current.groupby("security_id", sort=True):
        security_sectors[security_id] = tuple(sorted(set(rows["sector_id"])))
    return sector_members, security_sectors, tuple(sorted(current["sector_id"].unique()))


def build_new_day_plan(
    source: pd.DataFrame,
    sessions: Iterable[str],
    *,
    membership_path: Path | None = None,
    target_domains: Iterable[str] = V3_DAILY_TARGET_DOMAINS,
) -> dict[str, Any]:
    """Build the actual daily new-session plan for the V3 entry."""

    ordered_sessions = tuple(sorted(str(value) for value in sessions))
    if len(ordered_sessions) < 2:
        raise IncrementalBuildError("V3_DAILY_PLAN_NEEDS_PREVIOUS_SESSION")
    cutoff = ordered_sessions[-1]
    source_column = _date_column(source)
    current = source[source[source_column].astype(str).str[:10].eq(cutoff)]
    security_ids = tuple(sorted(set(current["security_id"].astype(str))))
    if not security_ids:
        raise IncrementalBuildError("V3_DAILY_CURRENT_UNIVERSE_EMPTY")
    sector_members, security_sectors, sector_ids = _load_membership(membership_path, cutoff)
    previous = DependencySummary(trading_days=ordered_sessions[:-1])
    current_summary = DependencySummary(trading_days=ordered_sessions)
    return build_plan(
        previous,
        current_summary,
        sessions=ordered_sessions,
        security_ids=security_ids,
        sector_ids=sector_ids,
        security_to_sectors=security_sectors,
        sector_members=sector_members,
        cutoff_date=cutoff,
        target_domains=target_domains,
    )


def _bound_snapshot(connection: duckdb.DuckDBPyConnection, publication_id: str) -> str | None:
    row = connection.execute(
        "SELECT snapshot_id FROM publication_analysis_snapshots WHERE publication_id=? AND domain='LOCAL_RECONSTRUCTED'",
        [publication_id],
    ).fetchone()
    return str(row[0]) if row else None


def _reuse_entries(
    connection: duckdb.DuckDBPyConnection,
    plan: Mapping[str, Any],
    source_snapshot_id: str,
) -> list[ReusedBuildObject]:
    tasks = [dict(item) for item in plan.get("tasks", [])]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in tasks:
        if item["domain"] == "technical":
            continue
        grouped.setdefault((str(item["domain"]), str(item["trade_date"])), []).append(item)
    references: list[ReusedBuildObject] = []
    for (domain, trade_date), group in sorted(grouped.items()):
        row = connection.execute(
            """
            SELECT slice_id FROM analysis_snapshot_entries
             WHERE snapshot_id=? AND domain=? AND trade_date=?
            """,
            [source_snapshot_id, domain, date.fromisoformat(trade_date)],
        ).fetchone()
        if not row:
            raise IncrementalBuildError(f"V3_REUSE_SOURCE_ENTRY_MISSING:{domain}:{trade_date}")
        keys = tuple(task_key(item) for item in group)
        references.append(
            ReusedBuildObject(
                task_key=keys[0],
                source_slice_id=str(row[0]),
                covered_task_keys=keys[1:],
                source_snapshot_id=source_snapshot_id,
            )
        )
    return references


def _preserved_entries(
    connection: duckdb.DuckDBPyConnection,
    source_snapshot_id: str,
    target_domains: Iterable[str],
) -> tuple[tuple[str, str, str], ...]:
    target = {str(domain) for domain in target_domains}
    rows = connection.execute(
        """
        SELECT domain, cast(trade_date as varchar), slice_id
          FROM analysis_snapshot_entries
         WHERE snapshot_id=?
         ORDER BY domain, trade_date, slice_id
        """,
        [source_snapshot_id],
    ).fetchall()
    return tuple((str(domain), str(trade_date), str(slice_id)) for domain, trade_date, slice_id in rows if str(domain) not in target)


def _load_bound_technical_rows(
    connection: duckdb.DuckDBPyConnection,
    source_snapshot_id: str,
) -> dict[str, tuple[str, pd.DataFrame]]:
    """Load V3 technical rows available for full-day result reassembly.

    A historical correction can plan only security A while the snapshot entry
    is one logical day slice.  The untouched B/C rows must come from that
    immutable source slice, never from a newly calculated partial frame.
    """

    from workbench_analysis.technical import TECHNICAL_RESULT_COLUMNS

    rows = connection.execute(
        """
        SELECT e.trade_date, e.slice_id, b.result_object_id
          FROM analysis_snapshot_entries e
          JOIN analysis_slice_result_bindings b ON b.slice_id=e.slice_id
         WHERE e.snapshot_id=? AND e.domain='technical'
         ORDER BY e.trade_date, e.slice_id
        """,
        [source_snapshot_id],
    ).fetchall()
    result: dict[str, tuple[str, pd.DataFrame]] = {}
    for trade_date, slice_id, result_object_id in rows:
        raw = connection.execute(
            f"SELECT {','.join(TECHNICAL_RESULT_COLUMNS)} FROM technical_result_rows WHERE result_object_id=? ORDER BY security_id",
            [result_object_id],
        ).fetchall()
        if not raw:
            continue
        frame = pd.DataFrame(raw, columns=list(TECHNICAL_RESULT_COLUMNS))
        frame = frame.rename(columns={"trade_date": "date", "contract_id": "technical_contract_id"})
        frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.date
        for column in ("quality_codes", "basis_json"):
            frame[column] = frame[column].map(
                lambda value: json.loads(value) if isinstance(value, str) else value
            )
        result[str(trade_date)[:10]] = (str(slice_id), frame)
    return result


def _daily_executor_matrix(
    technical_source: Mapping[str, tuple[str, pd.DataFrame]],
) -> dict[str, DomainExecutor]:
    """Build the daily matrix with full-day technical reassembly."""

    matrix = default_executor_matrix()
    base = matrix["technical"]
    if base.calculate is None:
        raise IncrementalBuildError("V3_TECHNICAL_EXECUTOR_MISSING")

    def calculate_technical(frame: Any, task: Mapping[str, Any]) -> Any:
        selected = {str(value) for value in task.get("security_ids", ()) if value}
        if not selected and task.get("security_id") is not None:
            selected = {str(task["security_id"])}
        calculated = base.calculate(frame, task)
        if hasattr(calculated, "columns") and selected:
            calculated = calculated[calculated["security_id"].astype(str).isin(selected)].copy()
        loaded = task.get("_loaded") or {}
        reused = loaded.get("reused_frame") if isinstance(loaded, Mapping) else None
        if reused is not None and not reused.empty:
            calculated = pd.concat([calculated, reused], ignore_index=True, sort=False)
        return calculated.sort_values(["date", "security_id"], kind="mergesort").reset_index(drop=True)

    matrix["technical"] = DomainExecutor(
        "CALCULATE",
        calculate=calculate_technical,
        contract_id=base.contract_id,
        primary_key=base.primary_key,
    )
    return matrix


def run_v3_daily_entry(
    root: str | Path,
    database_path: str | Path,
    *,
    publication_id: str,
    source_path: str | Path,
    membership_path: str | Path | None = None,
    plan: Mapping[str, Any] | None = None,
    source_snapshot_id: str | None = None,
    target_domains: Iterable[str] = V3_DAILY_TARGET_DOMAINS,
    repository: IncrementalWriterRepository | None = None,
) -> dict[str, Any]:
    """Run the V3 daily path from source input through final binding."""
    # MIGRATION_CONTRACT: daily entry remains MIGRATE_TO_PG until its read
    # projections and incremental writer share a rehearsed PG transaction.

    root_path = Path(root).resolve()
    repository = repository or DuckDBIncrementalWriterRepository(database_path)
    source_file = Path(source_path).resolve()
    membership_file = Path(membership_path).resolve() if membership_path else None
    source_reader = _ParquetSourceReader(source_file)
    sessions = source_reader.sessions
    try:
        if plan is not None:
            verified = verify_build_plan(plan)
        else:
            cutoff = sessions[-1]
            # Planning only needs the current universe and calendar. Do not
            # materialize historical prices at this boundary.
            current_ids = source_reader.current_security_ids(cutoff)
            plan_source = pd.DataFrame({
                "security_id": current_ids,
                "date": [cutoff] * len(current_ids),
            })
            verified = build_new_day_plan(
                plan_source,
                sessions,
                membership_path=membership_file,
                target_domains=target_domains,
            )
    except Exception:
        source_reader.close()
        raise
    if str(verified.get("status")) == "NO_WORK":
        try:
            report = IncrementalBuildCoordinator(database_path, repository=repository).execute_daily(
                verified,
                input_provider=lambda _task: None,
            )
            sync = _sync_postgres_if_enabled(root_path, str(verified["input"]["cutoff_date"]))
            return {"entrypoint": "V3_DAILY_INCREMENTAL", **report, **({"postgres_sync": sync} if sync else {})}
        finally:
            source_reader.close()

    with repository.connect() as connection:
        active_source_snapshot = source_snapshot_id or _bound_snapshot(connection, publication_id)
        if not active_source_snapshot:
            raise IncrementalBuildError("V3_REUSE_SOURCE_SNAPSHOT_REQUIRED")
        reused = _reuse_entries(connection, verified, active_source_snapshot)
        preserved = _preserved_entries(
            connection,
            active_source_snapshot,
            verified.get("target_domains") or target_domains,
        )
        technical_source = _load_bound_technical_rows(connection, active_source_snapshot)

    def input_provider(task: Mapping[str, Any]) -> Mapping[str, Any]:
        frame = source_reader.frame_for_task(task)
        source_slice_id, source_rows = technical_source.get(str(task["trade_date"]), (None, pd.DataFrame()))
        selected_ids = {str(value) for value in task.get("security_ids", ()) if value}
        if not selected_ids and task.get("security_id") is not None:
            selected_ids = {str(task["security_id"])}
        source_universe_ids = set(source_reader.current_security_ids(str(task["trade_date"])))
        reused_frame = source_rows[~source_rows["security_id"].astype(str).isin(selected_ids)].copy() if not source_rows.empty else source_rows
        reused_security_ids = sorted(set(reused_frame["security_id"].astype(str))) if not reused_frame.empty else []
        expected_reused_ids = source_universe_ids - selected_ids
        if expected_reused_ids and set(reused_security_ids) != expected_reused_ids:
            raise IncrementalBuildError(
                f"V3_FULL_DAY_SOURCE_REQUIRED:{task['trade_date']}:{','.join(sorted(expected_reused_ids - set(reused_security_ids)))}"
            )
        if not reused_security_ids:
            source_slice_id = None
        return {
            "frame": frame.copy(),
            "reused_frame": reused_frame,
            "basis": {
                "source_parquet": str(source_file),
                "source_sha256": _sha256_file(source_file),
                "entrypoint": "V3_DAILY_INCREMENTAL",
                "source_reader": "PYARROW_PARQUET_ROW_GROUP",
                "reused_security_ids": reused_security_ids,
                "reused_row_count": int(len(reused_frame)),
                "reused_source_slice_id": source_slice_id,
            },
        }

    cutoff = str(verified["input"]["cutoff_date"])
    query_start = sessions[0]
    manifest_hash = _sha256_file(source_file)
    snapshot_id = "v3-daily-" + hashlib.sha256(
        json.dumps({"publication_id": publication_id, "plan_id": verified["plan_id"]}, sort_keys=True).encode("utf-8")
    ).hexdigest()[:24]
    binding = SnapshotBinding(
        snapshot_id=snapshot_id,
        publication_id=publication_id,
        binding_domain="LOCAL_RECONSTRUCTED",
        cutoff_date=cutoff,
        query_start=query_start,
        config_hash=str(verified["input"]["current_digest"]),
        manifest_hash=manifest_hash,
        expected_task_keys=tuple(task_key(item) for item in verified.get("tasks", [])),
        preserved_entries=preserved,
    )
    try:
        report = IncrementalBuildCoordinator(
            database_path,
            executor_matrix=_daily_executor_matrix(technical_source),
            repository=repository,
        ).execute_daily(
            verified,
            input_provider=input_provider,
            reused=reused,
            snapshot=binding,
        )
    finally:
        source_reader.close()
    report = {
        "entrypoint": "V3_DAILY_INCREMENTAL",
        "source_snapshot_id": active_source_snapshot,
        "source_parquet": str(source_file),
        "target_domains": list(verified.get("target_domains") or target_domains),
        "preserved_legacy_entry_count": len(preserved),
        **report,
    }
    sync = _sync_postgres_if_enabled(root_path, cutoff)
    if sync:
        report["postgres_sync"] = sync
    artifact_root = root_path / "reports" / "v3" / "daily"
    plan_path = write_growth_report(artifact_root / f"{cutoff}.plan.json", verified)
    report["plan_artifact"] = str(plan_path)
    report_path = write_growth_report(artifact_root / f"{cutoff}.report.json", report)
    report["report_artifact"] = str(report_path)
    return report


__all__ = [
    "V3_DAILY_TARGET_DOMAINS",
    "build_new_day_plan",
    "run_v3_daily_entry",
]
