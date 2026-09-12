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
PLANNER_DOMAINS = {
    "quote", "technical", "strength", "high", "structure", "summary",
    "member_state", "sector_base", "sector_cycle", "mainline", "market",
}
EXECUTION_MODES = {"CALCULATE", "REUSE", "UNSUPPORTED"}


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
class DomainExecutor:
    """Explicit execution contract for one planner domain."""

    mode: str
    calculate: Callable[[Any, Mapping[str, Any]], Any] | None = None
    contract_id: str | None = None
    primary_key: tuple[str, ...] = ()

    def validate(self, domain: str) -> None:
        if self.mode not in EXECUTION_MODES:
            raise IncrementalBuildError(f"EXECUTOR_MODE_INVALID:{domain}:{self.mode}")
        if self.mode == "CALCULATE" and self.calculate is None:
            raise IncrementalBuildError(f"EXECUTOR_CALCULATOR_MISSING:{domain}")
        if self.mode == "CALCULATE" and (not self.contract_id or not self.primary_key):
            raise IncrementalBuildError(f"EXECUTOR_OUTPUT_CONTRACT_MISSING:{domain}")


def _same_trade_date(frame: Any, trade_date: str) -> Any:
    """Keep only the requested output date after a rolling calculation."""

    if not hasattr(frame, "columns") or not hasattr(frame, "loc"):
        raise IncrementalBuildError("CALCULATOR_DATAFRAME_REQUIRED")
    date_column = "date" if "date" in frame.columns else "trade_date" if "trade_date" in frame.columns else None
    if date_column is None:
        raise IncrementalBuildError("CALCULATOR_TRADE_DATE_COLUMN_REQUIRED")
    selected = frame.loc[frame[date_column].astype(str).eq(trade_date)].copy()
    if selected.empty:
        raise IncrementalBuildError(f"CALCULATOR_OUTPUT_DATE_MISSING:{trade_date}")
    return selected


def default_executor_matrix() -> dict[str, DomainExecutor]:
    """Return an explicit matrix; unsupported domains fail closed."""

    from workbench_analysis.technical import (
        TECHNICAL_RESULT_SEMANTIC_CONTRACT,
        calculate_technical_daily,
    )

    def calculate_technical(frame: Any, task: Mapping[str, Any]) -> Any:
        return _same_trade_date(calculate_technical_daily(frame, cutoff=task["trade_date"]), str(task["trade_date"]))

    matrix = {
        domain: DomainExecutor("UNSUPPORTED") for domain in sorted(PLANNER_DOMAINS)
    }
    matrix["technical"] = DomainExecutor(
        "CALCULATE",
        calculate=calculate_technical,
        contract_id=TECHNICAL_RESULT_SEMANTIC_CONTRACT,
        primary_key=("security_id", "date"),
    )
    for domain in {"strength", "high", "member_state", "structure", "summary", "sector_base", "sector_cycle", "mainline"}:
        matrix[domain] = DomainExecutor("REUSE")
    return matrix


@dataclass(frozen=True)
class ReusedBuildObject:
    """A planned task explicitly reusing an existing immutable slice."""

    task_key: str
    source_slice_id: str
    covered_task_keys: tuple[str, ...] = ()
    source_snapshot_id: str | None = None

    def keys(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((self.task_key, *self.covered_task_keys)))


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
        frame_scope: dict[str, list[str]] = {}
        for field_name in ("security_id", "sector_id"):
            values = sorted({str(row[field_name]) for row in rows if row.get(field_name) is not None})
            if values:
                frame_scope[field_name] = values
        date_values = sorted({str(row["date"])[:10] for row in rows if row.get("date") is not None})
        if not date_values:
            date_values = sorted({str(row["trade_date"])[:10] for row in rows if row.get("trade_date") is not None})
        if date_values:
            frame_scope["dates"] = date_values
        basis_value["frame_scope"] = frame_scope
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
    # Compatibility entries copied from the explicitly selected source
    # snapshot.  They are outside the V3 target plan, so they never satisfy
    # the target completeness gate; they only keep legacy readers available
    # while V3 domains are activated.
    preserved_entries: tuple[tuple[str, str, str], ...] = ()

    def validate(self) -> None:
        if not self.snapshot_id or not self.publication_id:
            raise IncrementalBuildError("SNAPSHOT_BINDING_ID_REQUIRED")
        if self.binding_domain not in BINDING_DOMAINS:
            raise IncrementalBuildError("SNAPSHOT_BINDING_DOMAIN_INVALID")
        if _iso(self.query_start) > _iso(self.cutoff_date):
            raise IncrementalBuildError("SNAPSHOT_QUERY_START_AFTER_CUTOFF")
        if not self.config_hash or not self.manifest_hash:
            raise IncrementalBuildError("SNAPSHOT_BINDING_HASH_REQUIRED")
        if not self.expected_task_keys or len(set(self.expected_task_keys)) != len(self.expected_task_keys):
            raise IncrementalBuildError("SNAPSHOT_TARGET_TASKS_REQUIRED")


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

    def __init__(
        self,
        database_path: str | Path,
        *,
        writers: Mapping[str, Callable[[Any, str, Any], int]] | None = None,
        executor_matrix: Mapping[str, DomainExecutor] | None = None,
    ):
        self.database_path = Path(database_path).resolve()
        self.writers = dict(writers or default_writers())
        self.executor_matrix = dict(executor_matrix or default_executor_matrix())
        unknown = set(self.executor_matrix) - PLANNER_DOMAINS
        if unknown:
            raise IncrementalBuildError("EXECUTOR_DOMAIN_UNKNOWN:" + ",".join(sorted(unknown)))
        for domain, executor in self.executor_matrix.items():
            executor.validate(domain)

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

    @staticmethod
    def _validate_frame_scope(item: PreparedBuildObject, covered_tasks: Sequence[Mapping[str, Any]]) -> None:
        if not hasattr(item.frame, "columns"):
            raise IncrementalBuildError(f"BUILD_OBJECT_FRAME_COLUMNS_REQUIRED:{item.task_key}")
        columns = {str(column) for column in item.frame.columns}
        for field_name in ("security_id", "sector_id"):
            expected = {str(task[field_name]) for task in covered_tasks if task.get(field_name) is not None}
            if not expected:
                continue
            if field_name not in columns:
                raise IncrementalBuildError(f"BUILD_OBJECT_FRAME_{field_name.upper()}_REQUIRED:{item.task_key}")
            actual = {str(value) for value in item.frame[field_name].dropna().tolist()}
            if actual != expected:
                raise IncrementalBuildError(
                    f"BUILD_OBJECT_FRAME_{field_name.upper()}_SCOPE_MISMATCH:{item.task_key}"
                )
        date_column = "date" if "date" in columns else "trade_date" if "trade_date" in columns else None
        if date_column is not None:
            actual_dates = {str(value)[:10] for value in item.frame[date_column].dropna().tolist()}
            if actual_dates != {item.trade_date}:
                raise IncrementalBuildError(f"BUILD_OBJECT_FRAME_DATE_SCOPE_MISMATCH:{item.task_key}")

    @staticmethod
    def _reuse_source(connection: Any, reference: ReusedBuildObject, covered_tasks: Sequence[Mapping[str, Any]]) -> tuple[int, str, str]:
        source = connection.execute(
            """
            SELECT s.domain, cast(s.trade_date as varchar), s.basis_json, s.row_count,
                   b.result_object_id
            FROM analysis_slices s
            LEFT JOIN analysis_slice_result_bindings b ON b.slice_id=s.slice_id
            WHERE s.slice_id=?
            """,
            [reference.source_slice_id],
        ).fetchone()
        if not source:
            raise IncrementalBuildError(f"REUSE_SOURCE_SLICE_NOT_FOUND:{reference.source_slice_id}")
        if source[4] is None:
            raise IncrementalBuildError(f"REUSE_SOURCE_RESULT_NOT_BOUND:{reference.source_slice_id}")
        expected_domain = str(covered_tasks[0]["domain"])
        expected_date = _iso(covered_tasks[0]["trade_date"])
        if str(source[0]) != expected_domain or str(source[1]) != expected_date:
            raise IncrementalBuildError(f"REUSE_SOURCE_SCOPE_MISMATCH:{reference.task_key}")
        if any(str(task["domain"]) != expected_domain or _iso(task["trade_date"]) != expected_date for task in covered_tasks):
            raise IncrementalBuildError(f"REUSE_TASK_SCOPE_MISMATCH:{reference.task_key}")
        try:
            basis = json.loads(source[2]) if isinstance(source[2], str) else dict(source[2] or {})
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise IncrementalBuildError(f"REUSE_SOURCE_SCOPE_EVIDENCE_INVALID:{reference.source_slice_id}") from exc
        frame_scope = basis.get("frame_scope")
        if not isinstance(frame_scope, Mapping):
            if not reference.source_snapshot_id:
                raise IncrementalBuildError(f"REUSE_SOURCE_SCOPE_EVIDENCE_MISSING:{reference.source_slice_id}")
            bound = connection.execute(
                """
                SELECT 1 FROM analysis_snapshot_entries
                 WHERE snapshot_id=? AND domain=? AND trade_date=? AND slice_id=?
                """,
                [reference.source_snapshot_id, expected_domain, date.fromisoformat(expected_date), reference.source_slice_id],
            ).fetchone()
            if not bound:
                raise IncrementalBuildError(f"REUSE_SOURCE_SNAPSHOT_BINDING_MISSING:{reference.source_slice_id}")
            return int(source[3]), str(source[4]), reference.source_slice_id
        expected_security = {str(task["security_id"]) for task in covered_tasks if task.get("security_id") is not None}
        if expected_security and set(map(str, frame_scope.get("security_id", []))) != expected_security:
            raise IncrementalBuildError(f"REUSE_SOURCE_SECURITY_SCOPE_MISMATCH:{reference.task_key}")
        expected_sector = {str(task["sector_id"]) for task in covered_tasks if task.get("sector_id") is not None}
        if expected_sector and set(map(str, frame_scope.get("sector_id", []))) != expected_sector:
            raise IncrementalBuildError(f"REUSE_SOURCE_SECTOR_SCOPE_MISMATCH:{reference.task_key}")
        if set(map(str, frame_scope.get("dates", []))) != {expected_date}:
            raise IncrementalBuildError(f"REUSE_SOURCE_DATE_SCOPE_MISMATCH:{reference.task_key}")
        return int(source[3]), str(source[4]), reference.source_slice_id

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
    def _bind_snapshot(connection: Any, binding: SnapshotBinding, entries: Sequence[tuple[tuple[str, ...], str, str, str]]) -> None:
        binding.validate()
        actual = {key for covered, _domain, _trade_date, _slice_id in entries for key in covered}
        expected = set(binding.expected_task_keys)
        if expected != actual:
            raise IncrementalBuildError("SNAPSHOT_TASK_SCOPE_MISMATCH")
        domain_dates: dict[tuple[str, str], str] = {}
        for covered, domain, trade_date, slice_id in entries:
            identity = (domain, trade_date)
            previous_slice = domain_dates.get(identity)
            if previous_slice is not None and previous_slice != slice_id:
                raise IncrementalBuildError("SNAPSHOT_DOMAIN_DATE_SLICE_CONFLICT")
            domain_dates[identity] = slice_id
        for domain, trade_date, slice_id in binding.preserved_entries:
            identity = (str(domain), _iso(trade_date))
            previous_slice = domain_dates.get(identity)
            if previous_slice is not None and previous_slice != str(slice_id):
                raise IncrementalBuildError("SNAPSHOT_PRESERVED_ENTRY_CONFLICT")
            domain_dates[identity] = str(slice_id)
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
        for (domain, trade_date), slice_id in sorted(domain_dates.items()):
            connection.execute(
                "INSERT INTO analysis_snapshot_entries VALUES (?,?,?,?) ON CONFLICT(snapshot_id,domain,trade_date) DO NOTHING",
                [binding.snapshot_id, domain, date.fromisoformat(trade_date), slice_id],
            )
            stored_entry = connection.execute(
                "SELECT slice_id FROM analysis_snapshot_entries WHERE snapshot_id=? AND domain=? AND trade_date=?",
                [binding.snapshot_id, domain, date.fromisoformat(trade_date)],
            ).fetchone()
            if not stored_entry or stored_entry[0] != slice_id:
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
        reused: Iterable[ReusedBuildObject] = (),
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
        reused_list = list(reused)
        status = str(verified.get("status") or "")
        if status == "NO_WORK":
            if object_list or reused_list or snapshot is not None:
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
                "execution_matrix": {domain: executor.mode for domain, executor in sorted(self.executor_matrix.items())},
                "snapshot_binding": None,
            }
        if status != "PLANNED":
            raise IncrementalBuildError("BUILD_PLAN_STATUS_INVALID")
        tasks = {str(item.get("task_key") or task_key(item)): item for item in verified.get("tasks", [])}
        if not object_list and not reused_list:
            raise IncrementalBuildError("PLANNED_OBJECTS_REQUIRED")
        seen: set[str] = set()
        binding_entries: list[tuple[tuple[str, ...], str, str, str]] = []
        for item in object_list:
            covered = item.covered_task_keys or (item.task_key,)
            covered_tasks: list[Mapping[str, Any]] = []
            for covered_key in covered:
                if covered_key in seen:
                    raise IncrementalBuildError(f"BUILD_OBJECT_DUPLICATE:{covered_key}")
                seen.add(covered_key)
                task = tasks.get(covered_key)
                if task is None:
                    raise IncrementalBuildError(f"BUILD_OBJECT_NOT_IN_PLAN:{covered_key}")
                if str(task.get("domain")) != item.domain or _iso(task.get("trade_date")) != item.trade_date:
                    raise IncrementalBuildError(f"BUILD_OBJECT_SCOPE_MISMATCH:{covered_key}")
                covered_tasks.append(task)
            if item.domain not in self.writers:
                raise IncrementalBuildError(f"WRITER_NOT_REGISTERED:{item.domain}")
            if _row_count(item.frame) != item.row_count:
                raise IncrementalBuildError(f"BUILD_OBJECT_ROW_COUNT_MISMATCH:{item.task_key}")
            self._validate_frame_scope(item, covered_tasks)
            binding_entries.append((tuple(covered), item.domain, item.trade_date, item.slice_id))
        for reference in reused_list:
            covered = reference.keys()
            if not covered:
                raise IncrementalBuildError("REUSE_TASK_REQUIRED")
            covered_tasks: list[Mapping[str, Any]] = []
            for covered_key in covered:
                if covered_key in seen:
                    raise IncrementalBuildError(f"BUILD_OBJECT_DUPLICATE:{covered_key}")
                seen.add(covered_key)
                task = tasks.get(covered_key)
                if task is None:
                    raise IncrementalBuildError(f"REUSE_TASK_NOT_IN_PLAN:{covered_key}")
                covered_tasks.append(task)
            domain = str(covered_tasks[0]["domain"])
            trade_date = _iso(covered_tasks[0]["trade_date"])
            if any(str(task["domain"]) != domain or _iso(task["trade_date"]) != trade_date for task in covered_tasks):
                raise IncrementalBuildError(f"REUSE_TASK_SCOPE_MISMATCH:{reference.task_key}")
            binding_entries.append((tuple(covered), domain, trade_date, reference.source_slice_id))
        if snapshot is not None:
            expected = set(snapshot.expected_task_keys)
            if expected != set(tasks):
                raise IncrementalBuildError("SNAPSHOT_TARGET_SCOPE_MISMATCH")
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
                    "execution_mode": "CALCULATE",
                    "row_count": row_count,
                    "slice_reused": bool(slice_reused),
                    "result_binding_created": before_binding is None and after_binding is not None,
                    "new_result_object_count": len(new_object_ids),
                })
            for reference in reused_list:
                covered_tasks = [tasks[key] for key in reference.keys()]
                row_count, result_object_id, source_slice_id = self._reuse_source(connection, reference, covered_tasks)
                rows_reused += row_count
                reused_objects += 1
                task_metrics.append({
                    "task_key": reference.task_key,
                    "covered_task_keys": list(reference.keys()),
                    "covered_task_count": len(reference.keys()),
                    "domain": str(covered_tasks[0]["domain"]),
                    "trade_date": _iso(covered_tasks[0]["trade_date"]),
                    "slice_id": source_slice_id,
                    "execution_mode": "REUSE",
                    "row_count": row_count,
                    "result_object_id": result_object_id,
                })
            if snapshot is not None:
                self._bind_snapshot(connection, snapshot, binding_entries)
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
            "executed_object_count": len(object_list) + len(reused_list),
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
            "execution_matrix": {domain: executor.mode for domain, executor in sorted(self.executor_matrix.items())},
            "snapshot_binding": {
                "snapshot_id": snapshot.snapshot_id,
                "publication_id": snapshot.publication_id,
                "binding_domain": snapshot.binding_domain,
            } if snapshot else None,
        }

    def execute_daily(
        self,
        plan: Mapping[str, Any],
        *,
        input_provider: Callable[[Mapping[str, Any]], Any],
        reused: Iterable[ReusedBuildObject] = (),
        snapshot: SnapshotBinding | None = None,
    ) -> dict[str, Any]:
        """Run the explicit domain matrix from raw daily input to binding.

        A plan is executable only when every target task is either calculated
        by a registered calculator or backed by an explicit immutable reuse
        reference.  Unsupported domains fail before opening a write
        transaction, so a partial daily build cannot become visible.
        """

        try:
            verified = verify_build_plan(plan)
        except BuildPlanError as exc:
            raise IncrementalBuildError(str(exc)) from exc
        if str(verified.get("status") or "") == "NO_WORK":
            return self.execute(plan, (), reused=tuple(reused), snapshot=snapshot)
        tasks = {str(item.get("task_key") or task_key(item)): item for item in verified.get("tasks", [])}
        reuse_list = list(reused)
        reuse_keys = {key for reference in reuse_list for key in reference.keys()}
        if len(reuse_keys) != sum(len(reference.keys()) for reference in reuse_list):
            raise IncrementalBuildError("REUSE_TASK_DUPLICATE")
        objects: list[PreparedBuildObject] = []
        calculate_groups: dict[tuple[str, str], list[tuple[str, Mapping[str, Any]]]] = {}
        for key, task in tasks.items():
            executor = self.executor_matrix.get(str(task.get("domain")))
            if executor is None:
                raise IncrementalBuildError(f"EXECUTOR_NOT_REGISTERED:{task.get('domain')}")
            if key in reuse_keys:
                continue
            if executor.mode == "UNSUPPORTED":
                raise IncrementalBuildError(f"EXECUTOR_UNSUPPORTED:{task.get('domain')}")
            if executor.mode == "REUSE":
                raise IncrementalBuildError(f"REUSE_SOURCE_REQUIRED:{key}")
            calculate_groups.setdefault((str(task.get("domain")), _iso(task["trade_date"])), []).append((key, task))
        for (_domain, _trade_date), group in sorted(calculate_groups.items()):
            key, task = group[0]
            executor = self.executor_matrix[str(task.get("domain"))]
            batch_task_keys = [item_key for item_key, _item in group]
            batch_task = dict(task)
            batch_task["batch_task_keys"] = batch_task_keys
            batch_security_ids = sorted({str(item.get("security_id")) for _item_key, item in group if item.get("security_id") is not None})
            if batch_security_ids:
                batch_task["security_ids"] = batch_security_ids
            # Always pass the representative batch task.  The provider is the
            # entrypoint's source-of-truth boundary and must see the complete
            # security set when several same-domain tasks are calculated in
            # one write object.
            loaded = input_provider(batch_task)
            basis: Mapping[str, Any] = {}
            frame = loaded
            if isinstance(loaded, Mapping) and "frame" in loaded:
                frame = loaded["frame"]
                basis = dict(loaded.get("basis") or {})
            calculated = executor.calculate(frame, task) if executor.calculate else None
            if calculated is None:
                raise IncrementalBuildError(f"EXECUTOR_CALCULATION_EMPTY:{task.get('domain')}")
            objects.append(
                PreparedBuildObject.from_frame(
                    task,
                    calculated,
                    plan_id=str(verified["plan_id"]),
                    contract_id=str(executor.contract_id),
                    basis={
                        **basis,
                        "executor_mode": "CALCULATE",
                        "executor_contract_id": executor.contract_id,
                    },
                    primary_key=executor.primary_key,
                    covered_task_keys=batch_task_keys[1:],
                )
            )
        return self.execute(plan, objects, reused=reuse_list, snapshot=snapshot)


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
    "DomainExecutor",
    "EXECUTION_MODES",
    "METRICS_CONTRACT_VERSION",
    "IncrementalBuildCoordinator",
    "IncrementalBuildError",
    "ReusedBuildObject",
    "PreparedBuildObject",
    "SnapshotBinding",
    "default_executor_matrix",
    "default_writers",
    "write_growth_report",
]
