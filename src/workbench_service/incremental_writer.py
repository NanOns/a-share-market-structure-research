"""V3 P04-02 transactional incremental build coordination.

The coordinator is deliberately below the domain algorithms.  It accepts a
verified P04-01 plan, creates only the supplied planned slice identities, and
delegates the actual rows to the existing P02/P03 domain writers.  Snapshot
and publication binding happens only after every supplied object succeeds in
the same transaction.  No TDX input is written here.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from numbers import Real
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import duckdb

from workbench_db.digest import logical_digest

from .build_planner import BuildPlanError, task_key, verify_build_plan


CONTRACT_VERSION = "v3-incremental-writer-v1.0"
METRICS_CONTRACT_VERSION = "v3-build-growth-metrics-v1.0"
STORAGE_KIND = "DUCKDB"
V3_RESULT_DOMAINS = {"technical", "strength", "high", "member_state", "structure", "summary"}
BINDING_DOMAINS = {"LOCAL_OBSERVED", "LOCAL_RECONSTRUCTED"}


class IncrementalBuildError(RuntimeError):
    """Raised when a plan cannot be executed without widening its scope."""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _iso(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise IncrementalBuildError(f"DATE_INVALID:{value}") from exc


def _frame_rows(frame: Any) -> tuple[list[str], list[dict[str, Any]]]:
    if hasattr(frame, "to_dict") and hasattr(frame, "columns"):
        columns = [str(value) for value in frame.columns]
        rows = [dict(row) for row in frame.to_dict("records")]
    else:
        rows = [dict(row) for row in frame]
        columns = sorted({str(column) for row in rows for column in row})
    if not rows:
        raise IncrementalBuildError("BUILD_OBJECT_ROWS_EMPTY")
    normalised = []
    for row in rows:
        normalised.append({column: _digest_value(row.get(column)) for column in columns})
    return columns, normalised


def _digest_value(value: Any) -> Any:
    """Canonicalise NaN/inf as explicit NULL for identity hashing."""

    if isinstance(value, Real) and not isinstance(value, bool):
        try:
            if not math.isfinite(float(value)):
                return None
        except (TypeError, ValueError):
            pass
    return value


def _file_bytes(path: Path) -> int:
    total = path.stat().st_size if path.is_file() else 0
    for suffix in (".wal", ".shm"):
        sidecar = Path(str(path) + suffix)
        if sidecar.is_file():
            total += sidecar.stat().st_size
    return int(total)


def _database_size_bytes(connection: duckdb.DuckDBPyConnection) -> int:
    """Return measured DuckDB block bytes without inventing row-size estimates."""

    columns = [item[0] for item in connection.execute("PRAGMA database_size").description]
    row = connection.execute("PRAGMA database_size").fetchone()
    if not row:
        return 0
    values = dict(zip(columns, row))
    block_size = int(values.get("block_size") or 0)
    used_blocks = int(values.get("used_blocks") or 0)
    return block_size * used_blocks


def _row_count(frame: Any) -> int:
    try:
        return int(len(frame))
    except TypeError as exc:
        raise IncrementalBuildError("BUILD_OBJECT_FRAME_LENGTH_REQUIRED") from exc


def _writer_frame(frame: Any) -> Any:
    """Preserve domain quality semantics while removing pandas object NaN."""

    if not hasattr(frame, "copy") or not hasattr(frame, "columns"):
        return frame
    result = frame.copy()
    for column in result.columns:
        try:
            if str(column) in {"amount_class", "ma_alignment"} or str(result[column].dtype) == "object":
                result[column] = result[column].astype(object).where(result[column].notna(), None)
        except (AttributeError, TypeError, ValueError):
            continue
    return result


@dataclass(frozen=True)
class PreparedBuildObject:
    """One planned slice input ready for an existing domain writer."""

    task_key: str
    domain: str
    trade_date: str
    slice_id: str
    contract_id: str
    input_hash: str
    dependency_hash: str
    basis: Mapping[str, Any]
    row_count: int
    logical_hash: str
    frame: Any = field(compare=False, repr=False)
    covered_task_keys: tuple[str, ...] = ()

    @classmethod
    def from_frame(
        cls,
        task: Mapping[str, Any],
        frame: Any,
        *,
        plan_id: str,
        contract_id: str,
        basis: Mapping[str, Any] | None = None,
        dependency_hash: str | None = None,
        primary_key: Sequence[str] | None = None,
        slice_id: str | None = None,
        covered_task_keys: Sequence[str] = (),
    ) -> "PreparedBuildObject":
        columns, rows = _frame_rows(frame)
        keys = tuple(primary_key or columns[:1])
        if not keys:
            raise IncrementalBuildError("BUILD_OBJECT_PRIMARY_KEY_REQUIRED")
        logical = logical_digest(rows, columns, list(keys))
        canonical_key = task_key(task)
        supplied_key = task.get("task_key")
        if supplied_key is not None and str(supplied_key) != canonical_key:
            raise IncrementalBuildError("BUILD_OBJECT_TASK_KEY_MISMATCH")
        key = canonical_key
        basis_value = dict(basis or {})
        input_hash = _hash({"plan_id": plan_id, "task_key": key, "logical_hash": logical["sha256"], "basis": basis_value})
        dependency = str(dependency_hash or _hash([]))
        object_slice_id = slice_id or "slice-" + _hash({"plan_id": plan_id, "task_key": key, "input_hash": input_hash, "dependency_hash": dependency})[:32]
        return cls(
            task_key=key,
            domain=str(task["domain"]),
            trade_date=_iso(task["trade_date"]),
            slice_id=object_slice_id,
            contract_id=str(contract_id),
            input_hash=input_hash,
            dependency_hash=dependency,
            basis=basis_value,
            row_count=len(rows),
            logical_hash=str(logical["sha256"]),
            frame=frame,
            covered_task_keys=tuple(dict.fromkeys((key, *(str(value) for value in covered_task_keys)))),
        )


@dataclass(frozen=True)
class SnapshotBinding:
    """The immutable snapshot and publication identity committed after build."""

    snapshot_id: str
    publication_id: str
    binding_domain: str
    cutoff_date: str
    query_start: str
    config_hash: str
    manifest_hash: str
    universe_contract: str = "CN_A_LISTED_V2"
    expected_task_keys: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.snapshot_id or not self.publication_id:
            raise IncrementalBuildError("SNAPSHOT_BINDING_ID_REQUIRED")
        if self.binding_domain not in BINDING_DOMAINS:
            raise IncrementalBuildError("SNAPSHOT_BINDING_DOMAIN_INVALID")
        if _iso(self.query_start) > _iso(self.cutoff_date):
            raise IncrementalBuildError("SNAPSHOT_QUERY_START_AFTER_CUTOFF")
        if not self.config_hash or not self.manifest_hash:
            raise IncrementalBuildError("SNAPSHOT_BINDING_HASH_REQUIRED")


def default_writers() -> dict[str, Callable[[Any, str, Any], int]]:
    """Return the existing V3/P02 domain writers without duplicating them."""

    from workbench_analysis.highs import insert_high_result_rows
    from workbench_analysis.history_adapter import insert_sector_base_rows
    from workbench_analysis.mainline import insert_mainline_rows
    from workbench_analysis.member_state import insert_member_state_result_rows
    from workbench_analysis.sector_cycle import insert_sector_cycle_rows
    from workbench_analysis.strength import insert_strength_result_rows
    from workbench_analysis.structures import insert_structure_result_rows, insert_structure_summary_result_rows
    from workbench_analysis.technical import insert_technical_result_rows

    return {
        "technical": insert_technical_result_rows,
        "strength": insert_strength_result_rows,
        "high": insert_high_result_rows,
        "member_state": insert_member_state_result_rows,
        "structure": insert_structure_result_rows,
        "summary": insert_structure_summary_result_rows,
        "sector_base": insert_sector_base_rows,
        "sector_cycle": insert_sector_cycle_rows,
        "mainline": insert_mainline_rows,
    }


class IncrementalBuildCoordinator:
    """Execute only planned objects and commit binding after all writers pass."""

    def __init__(self, database_path: str | Path, *, writers: Mapping[str, Callable[[Any, str, Any], int]] | None = None):
        self.database_path = Path(database_path).resolve()
        self.writers = dict(writers or default_writers())

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.database_path))

    @staticmethod
    def _existing_slice(connection: Any, slice_id: str) -> tuple[Any, ...] | None:
        return connection.execute(
            """
            SELECT domain, cast(trade_date as varchar), contract_id, input_hash,
                   dependency_hash, basis_json, row_count, logical_hash,
                   storage_kind, storage_object_id
            FROM analysis_slices WHERE slice_id=?
            """,
            [slice_id],
        ).fetchone()

    @staticmethod
    def _existing_binding(connection: Any, slice_id: str) -> tuple[Any, ...] | None:
        return connection.execute(
            "SELECT result_object_id, identity_evidence FROM analysis_slice_result_bindings WHERE slice_id=?",
            [slice_id],
        ).fetchone()

    @staticmethod
    def _object_ids(connection: Any) -> set[str]:
        return {str(row[0]) for row in connection.execute("SELECT result_object_id FROM analysis_result_objects").fetchall()}

    @classmethod
    def _ensure_slice(cls, connection: Any, item: PreparedBuildObject) -> bool:
        existing = cls._existing_slice(connection, item.slice_id)
        basis_json = _json(dict(item.basis))
        expected = (
            item.domain,
            item.trade_date,
            item.contract_id,
            item.input_hash,
            item.dependency_hash,
            basis_json,
            item.row_count,
            item.logical_hash,
            STORAGE_KIND,
        )
        if existing:
            actual = (
                str(existing[0]), str(existing[1]), str(existing[2]), str(existing[3]),
                str(existing[4]), _json(json.loads(existing[5]) if isinstance(existing[5], str) else existing[5]),
                int(existing[6]), str(existing[7]), str(existing[8]),
            )
            if actual != expected:
                raise IncrementalBuildError(f"SLICE_IDENTITY_CONFLICT:{item.slice_id}")
            return True
        now = datetime.now(timezone.utc)
        connection.execute(
            "INSERT INTO analysis_slices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [item.slice_id, item.domain, date.fromisoformat(item.trade_date), item.contract_id, item.input_hash, item.dependency_hash, basis_json, item.row_count, item.logical_hash, STORAGE_KIND, None, now],
        )
        return False

    @staticmethod
    def _bind_snapshot(connection: Any, binding: SnapshotBinding, items: Sequence[PreparedBuildObject]) -> None:
        binding.validate()
        expected = tuple(binding.expected_task_keys or tuple(key for item in items for key in (item.covered_task_keys or (item.task_key,))))
        actual = tuple(key for item in items for key in (item.covered_task_keys or (item.task_key,)))
        if set(expected) != set(actual):
            raise IncrementalBuildError("SNAPSHOT_TASK_SCOPE_MISMATCH")
        domain_dates = [(item.domain, item.trade_date) for item in items]
        if len(domain_dates) != len(set(domain_dates)):
            raise IncrementalBuildError("SNAPSHOT_DOMAIN_DATE_DUPLICATE")
        if not connection.execute("SELECT 1 FROM publications WHERE publication_id=?", [binding.publication_id]).fetchone():
            raise IncrementalBuildError("PUBLICATION_NOT_FOUND")
        connection.execute(
            "INSERT INTO analysis_snapshots VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(snapshot_id) DO NOTHING",
            [binding.snapshot_id, date.fromisoformat(_iso(binding.cutoff_date)), date.fromisoformat(_iso(binding.query_start)), binding.universe_contract, binding.config_hash, binding.manifest_hash, "SUCCESS", datetime.now(timezone.utc)],
        )
        stored = connection.execute(
            "SELECT cast(cutoff_date as varchar), cast(query_start as varchar), universe_contract, config_hash, manifest_hash, status FROM analysis_snapshots WHERE snapshot_id=?",
            [binding.snapshot_id],
        ).fetchone()
        expected_snapshot = (_iso(binding.cutoff_date), _iso(binding.query_start), binding.universe_contract, binding.config_hash, binding.manifest_hash, "SUCCESS")
        if not stored or tuple(str(value) for value in stored) != expected_snapshot:
            raise IncrementalBuildError("SNAPSHOT_IDENTITY_CONFLICT")
        for item in items:
            connection.execute(
                "INSERT INTO analysis_snapshot_entries VALUES (?,?,?,?) ON CONFLICT(snapshot_id,domain,trade_date) DO NOTHING",
                [binding.snapshot_id, item.domain, date.fromisoformat(item.trade_date), item.slice_id],
            )
            stored_entry = connection.execute(
                "SELECT slice_id FROM analysis_snapshot_entries WHERE snapshot_id=? AND domain=? AND trade_date=?",
                [binding.snapshot_id, item.domain, date.fromisoformat(item.trade_date)],
            ).fetchone()
            if not stored_entry or stored_entry[0] != item.slice_id:
                raise IncrementalBuildError("SNAPSHOT_ENTRY_IDENTITY_CONFLICT")
        connection.execute(
            "INSERT INTO publication_analysis_snapshots VALUES (?,?,?,?) ON CONFLICT(publication_id,domain) DO UPDATE SET snapshot_id=excluded.snapshot_id, bound_at=excluded.bound_at",
            [binding.publication_id, binding.binding_domain, binding.snapshot_id, datetime.now(timezone.utc)],
        )

    def execute(
        self,
        plan: Mapping[str, Any],
        objects: Iterable[PreparedBuildObject],
        *,
        snapshot: SnapshotBinding | None = None,
    ) -> dict[str, Any]:
        """Execute the selected planned objects atomically.

        A caller may execute a domain/date subset of a larger plan only when it
        does not request a snapshot binding.  Snapshot binding requires an
        explicit matching task scope, so a partial dry run cannot become the
        active publication input by accident.
        """

        try:
            verified = verify_build_plan(plan)
        except BuildPlanError as exc:
            raise IncrementalBuildError(str(exc)) from exc
        object_list = list(objects)
        status = str(verified.get("status") or "")
        if status == "NO_WORK":
            if object_list or snapshot is not None:
                raise IncrementalBuildError("NO_WORK_PLAN_HAS_EXECUTION_INPUT")
            return {
                "contract_version": CONTRACT_VERSION,
                "metrics_contract_version": METRICS_CONTRACT_VERSION,
                "status": "NO_WORK",
                "plan_id": verified["plan_id"],
                "planned_task_count": 0,
                "executed_task_count": 0,
                "executed_object_count": 0,
                "new_relation_edges": 0,
                "closed_relation_edges": 0,
                "relation_rows_reused": 0,
                "new_fact_rows": 0,
                "reused_result_objects": 0,
                "identity_rows_added": 0,
                "cache_bytes_added": 0,
                "db_file_growth_bytes": 0,
                "snapshot_binding": None,
            }
        if status != "PLANNED":
            raise IncrementalBuildError("BUILD_PLAN_STATUS_INVALID")
        tasks = {str(item.get("task_key") or task_key(item)): item for item in verified.get("tasks", [])}
        if not object_list:
            raise IncrementalBuildError("PLANNED_OBJECTS_REQUIRED")
        seen: set[str] = set()
        for item in object_list:
            covered = item.covered_task_keys or (item.task_key,)
            for covered_key in covered:
                if covered_key in seen:
                    raise IncrementalBuildError(f"BUILD_OBJECT_DUPLICATE:{covered_key}")
                seen.add(covered_key)
                task = tasks.get(covered_key)
                if task is None:
                    raise IncrementalBuildError(f"BUILD_OBJECT_NOT_IN_PLAN:{covered_key}")
                if str(task.get("domain")) != item.domain or _iso(task.get("trade_date")) != item.trade_date:
                    raise IncrementalBuildError(f"BUILD_OBJECT_SCOPE_MISMATCH:{covered_key}")
            if item.domain not in self.writers:
                raise IncrementalBuildError(f"WRITER_NOT_REGISTERED:{item.domain}")
            if _row_count(item.frame) != item.row_count:
                raise IncrementalBuildError(f"BUILD_OBJECT_ROW_COUNT_MISMATCH:{item.task_key}")
        if snapshot is not None:
            expected = set(snapshot.expected_task_keys or tuple(key for item in object_list for key in (item.covered_task_keys or (item.task_key,))))
            if expected != seen:
                raise IncrementalBuildError("SNAPSHOT_TASK_SCOPE_MISMATCH")

        database_before = _file_bytes(self.database_path)
        rows_new = 0
        rows_reused = 0
        reused_objects = 0
        identity_rows_added = 0
        task_metrics: list[dict[str, Any]] = []
        connection = self._connect()
        connection_open = True
        try:
            connection.execute("BEGIN TRANSACTION")
            for item in sorted(object_list, key=lambda value: (value.trade_date, value.domain, value.slice_id)):
                slice_reused = self._ensure_slice(connection, item)
                before_binding = self._existing_binding(connection, item.slice_id)
                before_objects = self._object_ids(connection)
                written = self.writers[item.domain](connection, item.slice_id, _writer_frame(item.frame))
                if isinstance(written, Mapping):
                    row_count = int(written.get("row_count", item.row_count))
                else:
                    row_count = int(written)
                if row_count != item.row_count:
                    raise IncrementalBuildError(f"WRITER_ROW_COUNT_MISMATCH:{item.task_key}")
                after_binding = self._existing_binding(connection, item.slice_id)
                after_objects = self._object_ids(connection)
                new_object_ids = after_objects - before_objects
                if before_binding is not None or slice_reused:
                    rows_reused += row_count
                else:
                    rows_new += row_count
                    identity_rows_added += 1
                result_object_reused = bool(after_binding and after_binding[0] in before_objects)
                if result_object_reused:
                    reused_objects += 1
                task_metrics.append({
                    "task_key": item.task_key,
                    "covered_task_keys": list(item.covered_task_keys or (item.task_key,)),
                    "covered_task_count": len(item.covered_task_keys or (item.task_key,)),
                    "domain": item.domain,
                    "trade_date": item.trade_date,
                    "slice_id": item.slice_id,
                    "row_count": row_count,
                    "slice_reused": bool(slice_reused),
                    "result_binding_created": before_binding is None and after_binding is not None,
                    "new_result_object_count": len(new_object_ids),
                })
            if snapshot is not None:
                self._bind_snapshot(connection, snapshot, object_list)
            connection.execute("COMMIT")
        except Exception:
            try:
                connection.execute("ROLLBACK")
            finally:
                connection.close()
                connection_open = False
            raise
        finally:
            if connection_open:
                connection.close()

        database_after = _file_bytes(self.database_path)
        db_growth = max(0, database_after - database_before)
        return {
            "contract_version": CONTRACT_VERSION,
            "metrics_contract_version": METRICS_CONTRACT_VERSION,
            "status": "BUILT",
            "plan_id": verified["plan_id"],
            "planned_task_count": len(tasks),
            "executed_task_count": len(seen),
            "executed_object_count": len(object_list),
            "skipped_task_count": len(tasks) - len(seen),
            "new_relation_edges": 0,
            "closed_relation_edges": 0,
            "relation_rows_reused": 0,
            "new_fact_rows": rows_new,
            "reused_rows": rows_reused,
            "reused_result_objects": reused_objects,
            "identity_rows_added": identity_rows_added,
            "cache_bytes_added": db_growth,
            "db_file_growth_bytes": db_growth,
            "database_bytes_before": database_before,
            "database_bytes_after": database_after,
            "task_metrics": task_metrics,
            "snapshot_binding": {
                "snapshot_id": snapshot.snapshot_id,
                "publication_id": snapshot.publication_id,
                "binding_domain": snapshot.binding_domain,
            } if snapshot else None,
        }


def write_growth_report(path: str | Path, report: Mapping[str, Any]) -> Path:
    """Atomically write an auditable build-growth report outside TDX inputs."""

    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_text(json.dumps(dict(report), ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


__all__ = [
    "CONTRACT_VERSION",
    "METRICS_CONTRACT_VERSION",
    "IncrementalBuildCoordinator",
    "IncrementalBuildError",
    "PreparedBuildObject",
    "SnapshotBinding",
    "default_writers",
    "write_growth_report",
]
