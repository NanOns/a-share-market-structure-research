"""Content-addressed historical slice coordination for M7B-04.

The coordinator deliberately stays below the factor layer.  It accepts an
already frozen, explainable batch of rows, writes a temporary Parquet object,
verifies the read-back digest, and only then seals the slice and its
dependencies in DuckDB.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

import duckdb
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from workbench_db.digest import logical_digest
from .source_freezer import sha256_file


CONTRACT_VERSION = "history-slice-coordination-v1.0"
STORAGE_KIND = "PARQUET"


class SliceCoordinationError(RuntimeError):
    """Raised when a slice cannot be safely prepared or sealed."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _normalise_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    if not rows:
        raise SliceCoordinationError("SLICE_ROWS_EMPTY")
    columns = sorted({str(column) for row in rows for column in row})
    normalised = [{column: row.get(column) for column in columns} for row in rows]
    return columns, normalised


def _dependencies(value: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    result = []
    for item in value:
        required = ("input_domain", "input_date", "input_slice_id")
        if any(key not in item for key in required):
            raise SliceCoordinationError("SLICE_DEPENDENCY_FIELD_MISSING")
        result.append({key: str(item[key]) for key in required})
    return sorted(result, key=lambda item: (item["input_domain"], item["input_date"], item["input_slice_id"]))


def iter_security_batches(
    parquet_path: str | Path,
    *,
    trade_date: str,
    security_ids: Sequence[str],
    columns: Sequence[str] | None = None,
    batch_size: int = 4096,
) -> Iterator[dict[str, Any]]:
    """Read only selected securities for one observed date in record batches."""
    if not security_ids:
        raise SliceCoordinationError("SECURITY_IDS_REQUIRED")
    path = Path(parquet_path).resolve()
    if not path.is_file():
        raise SliceCoordinationError("SLICE_INPUT_FILE_MISSING")
    requested = list(dict.fromkeys(str(value) for value in security_ids))
    dataset = ds.dataset(path, format="parquet")
    available = set(dataset.schema.names)
    if "security_id" not in available or "date" not in available:
        raise SliceCoordinationError("SLICE_INPUT_SCHEMA_MISSING")
    selected_columns = list(columns) if columns else list(dataset.schema.names)
    missing = sorted(set(selected_columns) - available)
    if missing:
        raise SliceCoordinationError(f"SLICE_INPUT_COLUMNS_MISSING:{','.join(missing)}")
    filter_expr = (ds.field("date") == date.fromisoformat(str(trade_date))) & ds.field("security_id").isin(requested)
    grouped: dict[str, list[dict[str, Any]]] = {security_id: [] for security_id in requested}
    scanner = dataset.scanner(columns=selected_columns, filter=filter_expr, batch_size=int(batch_size))
    for batch in scanner.to_batches():
        for row in batch.to_pylist():
            grouped[str(row["security_id"])].append(row)
    for security_id in requested:
        rows = grouped[security_id]
        if rows:
            yield {"security_id": security_id, "trade_date": str(trade_date), "rows": rows}


class SliceCoordinator:
    """Prepare, validate, and seal content-addressed analysis slices."""

    def __init__(self, root: str | Path, database_path: str | Path | None = None):
        self.root = Path(root).resolve()
        self.database_path = Path(database_path).resolve() if database_path else self.root / "data/database/market_research.duckdb"
        self.object_root = self.root / "data/analysis_objects"

    def _object_path(self, object_id: str) -> Path:
        return self.object_root / f"{object_id}.parquet"

    def _input_hash(self, logical_hash: str, row_count: int, basis: Mapping[str, Any]) -> str:
        return _sha({
            "contract_version": CONTRACT_VERSION,
            "logical_hash": logical_hash,
            "row_count": row_count,
            "source_manifest_sha256": basis.get("source_manifest_sha256"),
            "source_bundle_id": basis.get("source_bundle_id"),
        })

    def _slice_identity(
        self,
        *,
        domain: str,
        trade_date: str,
        contract_id: str,
        input_hash: str,
        dependency_hash: str,
        basis: Mapping[str, Any],
    ) -> str:
        return "slice-" + _sha({
            "contract_id": contract_id,
            "domain": domain,
            "trade_date": str(trade_date),
            "input_hash": input_hash,
            "dependency_hash": dependency_hash,
            "basis": dict(basis),
        })

    def _write_object(self, path: Path, columns: list[str], rows: list[dict[str, Any]], expected_logical_hash: str) -> tuple[str, int]:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return self._verify_object(path, expected_logical_hash)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            table = pa.Table.from_pylist(rows, schema=None)
            pq.write_table(table, temporary, compression="zstd")
            actual_hash, row_count = self._verify_object(temporary, expected_logical_hash)
            os.replace(temporary, path)
            return actual_hash, row_count
        finally:
            temporary.unlink(missing_ok=True)

    def _verify_object(self, path: Path, expected_logical_hash: str) -> tuple[str, int]:
        if not path.is_file():
            raise SliceCoordinationError("ANALYSIS_OBJECT_MISSING")
        table = pq.read_table(path)
        rows = table.to_pylist()
        digest = logical_digest(rows, list(table.column_names), list(table.column_names[:1]))
        if digest["sha256"] != expected_logical_hash:
            raise SliceCoordinationError("ANALYSIS_OBJECT_LOGICAL_HASH_MISMATCH")
        return sha256_file(path), digest["row_count"]

    def _existing(self, connection: duckdb.DuckDBPyConnection, slice_id: str) -> tuple[Any, ...] | None:
        return connection.execute(
            "select slice_id,domain,cast(trade_date as varchar),contract_id,input_hash,dependency_hash,basis_json,row_count,logical_hash,storage_kind,storage_object_id from analysis_slices where slice_id=?",
            [slice_id],
        ).fetchone()

    def _check_existing(
        self,
        connection: duckdb.DuckDBPyConnection,
        existing: tuple[Any, ...],
        *,
        domain: str,
        trade_date: str,
        contract_id: str,
        input_hash: str,
        dependency_hash: str,
        basis: Mapping[str, Any],
        logical_hash: str,
        row_count: int,
    ) -> dict[str, Any]:
        expected = (domain, str(trade_date), contract_id, input_hash, dependency_hash, row_count, logical_hash, STORAGE_KIND)
        actual = (existing[1], existing[2], existing[3], existing[4], existing[5], int(existing[7]), existing[8], existing[9])
        if actual != expected or json.loads(existing[6]) != dict(basis):
            raise SliceCoordinationError("SLICE_IDENTITY_CONFLICT")
        object_id = str(existing[10]) if existing[10] else ""
        if not object_id:
            raise SliceCoordinationError("SEALED_SLICE_OBJECT_MISSING")
        object_path = self._object_path(object_id)
        self._verify_object(object_path, logical_hash)
        return {"slice_id": existing[0], "storage_object_id": object_id, "logical_hash": logical_hash, "row_count": row_count, "reused": True}

    def coordinate(
        self,
        *,
        domain: str,
        trade_date: str,
        contract_id: str,
        rows: Iterable[Mapping[str, Any]],
        dependencies: Iterable[Mapping[str, Any]] = (),
        basis: Mapping[str, Any],
    ) -> dict[str, Any]:
        trade_date = date.fromisoformat(str(trade_date)).isoformat()
        columns, normalised_rows = _normalise_rows(list(rows))
        logical = logical_digest(normalised_rows, columns, columns[:1])
        dependency_rows = _dependencies(dependencies)
        dependency_hash = _sha(dependency_rows)
        basis_value = dict(basis)
        input_hash = self._input_hash(logical["sha256"], logical["row_count"], basis_value)
        slice_id = self._slice_identity(domain=domain, trade_date=trade_date, contract_id=contract_id, input_hash=input_hash, dependency_hash=dependency_hash, basis=basis_value)
        object_id = "analysis-obj-" + logical["sha256"]
        object_path = self._object_path(object_id)

        with duckdb.connect(str(self.database_path)) as connection:
            existing = self._existing(connection, slice_id)
            if existing:
                return self._check_existing(connection, existing, domain=domain, trade_date=trade_date, contract_id=contract_id, input_hash=input_hash, dependency_hash=dependency_hash, basis=basis_value, logical_hash=logical["sha256"], row_count=logical["row_count"])
            for dependency in dependency_rows:
                found = connection.execute("select 1 from analysis_slices where slice_id=?", [dependency["input_slice_id"]]).fetchone()
                if not found:
                    raise SliceCoordinationError(f"SLICE_DEPENDENCY_NOT_FOUND:{dependency['input_slice_id']}")

        _, row_count = self._write_object(object_path, columns, normalised_rows, logical["sha256"])
        physical_hash = sha256_file(object_path)
        created_at = datetime.now(timezone.utc)
        object_payload = {
            "storage_object_id": object_id,
            "path": str(object_path),
            "relative_path": object_path.relative_to(self.root).as_posix(),
            "kind": "ANALYSIS_SLICE",
            "storage_kind": STORAGE_KIND,
            "logical_hash": logical["sha256"],
            "physical_sha256": physical_hash,
            "row_count": row_count,
            "contract_version": CONTRACT_VERSION,
            "state": "ACTIVE",
            "referenced": False,
            "successful_date": trade_date,
            "registered_at_utc": created_at.isoformat(),
        }
        try:
            with duckdb.connect(str(self.database_path)) as connection:
                connection.execute("BEGIN TRANSACTION")
                try:
                    for dependency in dependency_rows:
                        if not connection.execute("select 1 from analysis_slices where slice_id=?", [dependency["input_slice_id"]]).fetchone():
                            raise SliceCoordinationError(f"SLICE_DEPENDENCY_NOT_FOUND:{dependency['input_slice_id']}")
                    connection.execute("insert into storage_objects(storage_object_id,payload_json) values (?,?) on conflict(storage_object_id) do nothing", [object_id, _json(object_payload)])
                    stored = connection.execute("select payload_json from storage_objects where storage_object_id=?", [object_id]).fetchone()
                    if not stored or json.loads(stored[0]).get("logical_hash") != logical["sha256"]:
                        raise SliceCoordinationError("ANALYSIS_OBJECT_IDENTITY_CONFLICT")
                    connection.execute(
                        "insert into analysis_slices values (?,?,?,?,?,?,?,?,?,?,?,?)",
                        [slice_id, domain, date.fromisoformat(trade_date), contract_id, input_hash, dependency_hash, _json(basis_value), row_count, logical["sha256"], STORAGE_KIND, object_id, created_at],
                    )
                    for dependency in dependency_rows:
                        connection.execute("insert into analysis_slice_dependencies values (?,?,?,?)", [slice_id, dependency["input_domain"], date.fromisoformat(dependency["input_date"]), dependency["input_slice_id"]])
                    daily_basis = basis_value.get("daily_basis")
                    if isinstance(daily_basis, Mapping):
                        required = ("universe_basis", "price_basis", "capabilities_json")
                        if any(key not in daily_basis for key in required):
                            raise SliceCoordinationError("SLICE_DAILY_BASIS_FIELD_MISSING")
                        connection.execute(
                            "insert into analysis_daily_basis values (?,?,?,?,?,?,?,?)",
                            [slice_id, daily_basis["universe_basis"], daily_basis.get("membership_snapshot_id"), daily_basis["price_basis"], daily_basis.get("adjustment_as_of"), daily_basis.get("source_observed_at"), daily_basis.get("coverage"), _json(daily_basis["capabilities_json"])],
                        )
                    connection.execute("COMMIT")
                except Exception:
                    connection.execute("ROLLBACK")
                    raise
        except Exception:
            # A newly prepared but unsealed object is not an advertised slice.
            # Keep an existing content-addressed object available for a retry.
            raise
        return {"slice_id": slice_id, "storage_object_id": object_id, "logical_hash": logical["sha256"], "row_count": row_count, "reused": False}
