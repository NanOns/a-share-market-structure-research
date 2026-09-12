"""P03-01 content-addressed analysis result objects.

Result values are immutable and content-addressed independently from slice
identity.  A slice keeps its own date, dependency and source identity while
the binding points at one verified physical result object.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from workbench_db.digest import logical_digest


STORAGE_KIND = "PARQUET"
CONTRACT_VERSION = "analysis-result-object-v3-v1"


class ResultObjectError(ValueError):
    pass


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _normalise_rows(rows: Iterable[Mapping[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    values = [dict(row) for row in rows]
    if not values:
        raise ResultObjectError("RESULT_ROWS_EMPTY")
    columns = sorted({str(column) for row in values for column in row})
    return columns, [{column: row.get(column) for column in columns} for row in values]


def _validate_primary_key(columns: Sequence[str], primary_key: Sequence[str]) -> tuple[str, ...]:
    keys = tuple(str(value) for value in primary_key)
    if not keys or any(key not in columns for key in keys):
        raise ResultObjectError("RESULT_PRIMARY_KEY_INVALID")
    return keys


def result_value_hash(
    *,
    domain: str,
    schema_version: str,
    semantic_contract: str,
    columns: Sequence[str],
    primary_key: Sequence[str],
    rows: Sequence[Mapping[str, Any]],
    value_semantics: Mapping[str, Any] | None = None,
) -> tuple[str, str, int]:
    """Return value hash, row logical hash and row count.

    The value hash includes schema/units/NULL and quality semantics in
    addition to sorted row content. Slice IDs and source task IDs are absent.
    """
    normalised_columns = tuple(str(column) for column in columns)
    key_columns = _validate_primary_key(normalised_columns, primary_key)
    logical = logical_digest(list(rows), list(normalised_columns), list(key_columns))
    payload = {
        "contract_version": CONTRACT_VERSION,
        "domain": str(domain),
        "schema_version": str(schema_version),
        "semantic_contract": str(semantic_contract),
        "columns": list(normalised_columns),
        "primary_key": list(key_columns),
        "row_count": int(logical["row_count"]),
        "logical_hash": logical["sha256"],
        "value_semantics": dict(value_semantics or {}),
    }
    return _hash(payload), logical["sha256"], int(logical["row_count"])


class ResultObjectCoordinator:
    """Create immutable result objects and preserve independent slice bindings."""

    def __init__(self, root: str | Path, database_path: str | Path | None = None):
        self.root = Path(root).resolve()
        self.database_path = Path(database_path).resolve() if database_path else self.root / "data/database/market_research.duckdb"
        self.object_root = self.root / "data/analysis_objects"

    def _object_path(self, result_object_id: str) -> Path:
        return self.object_root / f"{result_object_id}.parquet"

    def _slice_id(self, domain: str, trade_date: str, contract_id: str, input_hash: str, dependency_hash: str, basis: Mapping[str, Any]) -> str:
        return "slice-" + _hash(
            {
                "domain": domain,
                "trade_date": str(trade_date),
                "contract_id": contract_id,
                "input_hash": input_hash,
                "dependency_hash": dependency_hash,
                "basis": dict(basis),
            }
        )

    @staticmethod
    def _dependency_hash(dependencies: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, str]], str]:
        values = []
        for item in dependencies:
            required = ("input_domain", "input_date", "input_slice_id")
            if any(key not in item for key in required):
                raise ResultObjectError("RESULT_DEPENDENCY_FIELD_MISSING")
            values.append({key: str(item[key]) for key in required})
        values.sort(key=lambda item: (item["input_domain"], item["input_date"], item["input_slice_id"]))
        return values, _hash(values)

    @staticmethod
    def _write_verified(path: Path, columns: list[str], rows: list[dict[str, Any]], expected_value_hash: str, *, domain: str, schema_version: str, semantic_contract: str, primary_key: Sequence[str], value_semantics: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            ResultObjectCoordinator._verify(path, expected_value_hash, domain=domain, schema_version=schema_version, semantic_contract=semantic_contract, primary_key=primary_key, value_semantics=value_semantics)
            return
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            pq.write_table(pa.Table.from_pylist(rows), temporary, compression="zstd")
            ResultObjectCoordinator._verify(temporary, expected_value_hash, domain=domain, schema_version=schema_version, semantic_contract=semantic_contract, primary_key=primary_key, value_semantics=value_semantics)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _verify(path: Path, expected_value_hash: str, *, domain: str, schema_version: str, semantic_contract: str, primary_key: Sequence[str], value_semantics: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
        if not path.is_file():
            raise ResultObjectError("RESULT_OBJECT_MISSING")
        table = pq.read_table(path)
        rows = table.to_pylist()
        columns = list(table.column_names)
        actual, _, _ = result_value_hash(
            domain=domain,
            schema_version=schema_version,
            semantic_contract=semantic_contract,
            columns=columns,
            primary_key=primary_key,
            rows=rows,
            value_semantics=value_semantics,
        )
        if actual != expected_value_hash:
            raise ResultObjectError("RESULT_OBJECT_VALUE_HASH_MISMATCH")
        return rows, columns

    def coordinate(
        self,
        *,
        domain: str,
        trade_date: str,
        contract_id: str,
        schema_version: str,
        semantic_contract: str,
        rows: Iterable[Mapping[str, Any]],
        primary_key: Sequence[str],
        value_semantics: Mapping[str, Any] | None = None,
        dependencies: Iterable[Mapping[str, Any]] = (),
        basis: Mapping[str, Any],
    ) -> dict[str, Any]:
        trade_date = date.fromisoformat(str(trade_date)).isoformat()
        columns, normalised_rows = _normalise_rows(rows)
        keys = _validate_primary_key(columns, primary_key)
        semantics = dict(value_semantics or {})
        value_hash, logical_hash, row_count = result_value_hash(
            domain=domain,
            schema_version=schema_version,
            semantic_contract=semantic_contract,
            columns=columns,
            primary_key=keys,
            rows=normalised_rows,
            value_semantics=semantics,
        )
        dependency_rows, dependency_hash = self._dependency_hash(dependencies)
        input_hash = _hash({"value_hash": value_hash, "source_manifest_sha256": basis.get("source_manifest_sha256"), "source_bundle_id": basis.get("source_bundle_id")})
        slice_id = self._slice_id(domain, trade_date, contract_id, input_hash, dependency_hash, basis)
        result_object_id = "result-obj-" + value_hash[:32]
        object_path = self._object_path(result_object_id)
        self._write_verified(object_path, columns, normalised_rows, value_hash, domain=domain, schema_version=schema_version, semantic_contract=semantic_contract, primary_key=keys, value_semantics=semantics)
        identity_evidence = {
            "contract_version": CONTRACT_VERSION,
            "slice_id": slice_id,
            "domain": domain,
            "trade_date": trade_date,
            "contract_id": contract_id,
            "input_hash": input_hash,
            "dependency_hash": dependency_hash,
            "basis": dict(basis),
            "value_hash": value_hash,
            "schema_version": schema_version,
            "semantic_contract": semantic_contract,
            "value_semantics": semantics,
        }
        created_at = datetime.now(timezone.utc)
        with duckdb.connect(str(self.database_path)) as connection:
            existing = connection.execute("SELECT domain, contract_id, input_hash, dependency_hash, basis_json, row_count, logical_hash, storage_kind, storage_object_id FROM analysis_slices WHERE slice_id=?", [slice_id]).fetchone()
            if existing:
                if existing[0] != domain or existing[2] != input_hash or existing[3] != dependency_hash or json.loads(existing[4]) != dict(basis) or int(existing[5]) != row_count or existing[6] != logical_hash or existing[7] != STORAGE_KIND or existing[8] != result_object_id:
                    raise ResultObjectError("SLICE_IDENTITY_CONFLICT")
                self._verify(object_path, value_hash, domain=domain, schema_version=schema_version, semantic_contract=semantic_contract, primary_key=keys, value_semantics=semantics)
                return {"slice_id": slice_id, "result_object_id": result_object_id, "value_hash": value_hash, "row_count": row_count, "reused": True}
            connection.execute("BEGIN TRANSACTION")
            try:
                connection.execute(
                    "INSERT INTO analysis_result_objects VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(result_object_id) DO NOTHING",
                    [result_object_id, domain, schema_version, semantic_contract, value_hash, row_count, STORAGE_KIND, created_at],
                )
                stored_object = connection.execute(
                    "SELECT domain, schema_version, semantic_contract, value_hash, row_count, storage_kind FROM analysis_result_objects WHERE result_object_id=?",
                    [result_object_id],
                ).fetchone()
                if not stored_object or tuple(stored_object) != (domain, schema_version, semantic_contract, value_hash, row_count, STORAGE_KIND):
                    raise ResultObjectError("RESULT_OBJECT_IDENTITY_CONFLICT")
                storage_payload = {
                    "storage_object_id": result_object_id,
                    "result_object_id": result_object_id,
                    "path": str(object_path),
                    "relative_path": object_path.relative_to(self.root).as_posix(),
                    "kind": "ANALYSIS_RESULT_OBJECT",
                    "storage_kind": STORAGE_KIND,
                    "domain": domain,
                    "schema_version": schema_version,
                    "semantic_contract": semantic_contract,
                    "value_hash": value_hash,
                    "logical_hash": logical_hash,
                    "columns": columns,
                    "primary_key": list(keys),
                    "value_semantics": semantics,
                    "row_count": row_count,
                    "state": "ACTIVE",
                    "referenced": True,
                    "registered_at_utc": created_at.isoformat(),
                }
                connection.execute("INSERT INTO storage_objects(storage_object_id,payload_json) VALUES (?, ?) ON CONFLICT(storage_object_id) DO NOTHING", [result_object_id, _json(storage_payload)])
                stored = connection.execute("SELECT payload_json FROM storage_objects WHERE storage_object_id=?", [result_object_id]).fetchone()
                if not stored or json.loads(stored[0]).get("value_hash") != value_hash:
                    raise ResultObjectError("RESULT_OBJECT_IDENTITY_CONFLICT")
                for dependency in dependency_rows:
                    if not connection.execute("SELECT 1 FROM analysis_slices WHERE slice_id=?", [dependency["input_slice_id"]]).fetchone():
                        raise ResultObjectError(f"RESULT_DEPENDENCY_NOT_FOUND:{dependency['input_slice_id']}")
                connection.execute(
                    "INSERT INTO analysis_slices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [slice_id, domain, date.fromisoformat(trade_date), contract_id, input_hash, dependency_hash, _json(dict(basis)), row_count, logical_hash, STORAGE_KIND, result_object_id, created_at],
                )
                for dependency in dependency_rows:
                    connection.execute("INSERT INTO analysis_slice_dependencies VALUES (?, ?, ?, ?)", [slice_id, dependency["input_domain"], date.fromisoformat(dependency["input_date"]), dependency["input_slice_id"]])
                daily_basis = basis.get("daily_basis")
                if isinstance(daily_basis, Mapping):
                    required = ("universe_basis", "price_basis", "capabilities_json")
                    if any(key not in daily_basis for key in required):
                        raise ResultObjectError("RESULT_DAILY_BASIS_FIELD_MISSING")
                    connection.execute("INSERT INTO analysis_daily_basis VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [slice_id, daily_basis["universe_basis"], daily_basis.get("membership_snapshot_id"), daily_basis["price_basis"], daily_basis.get("adjustment_as_of"), daily_basis.get("source_observed_at"), daily_basis.get("coverage"), _json(daily_basis["capabilities_json"])])
                connection.execute("INSERT INTO analysis_slice_result_bindings VALUES (?, ?, ?)", [slice_id, result_object_id, _json(identity_evidence)])
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
        return {"slice_id": slice_id, "result_object_id": result_object_id, "value_hash": value_hash, "row_count": row_count, "reused": False}


def read_result_rows(connection: duckdb.DuckDBPyConnection, root: str | Path, slice_id: str) -> list[dict[str, Any]]:
    """Read a bound result and verify its value hash, schema, and row count."""
    row = connection.execute(
        """
        SELECT o.domain, o.schema_version, o.semantic_contract, o.value_hash,
               o.row_count, b.identity_evidence, s.payload_json
        FROM analysis_slice_result_bindings b
        JOIN analysis_result_objects o USING (result_object_id)
        JOIN storage_objects s ON s.storage_object_id=b.result_object_id
        WHERE b.slice_id=?
        """,
        [slice_id],
    ).fetchone()
    if not row:
        raise ResultObjectError("RESULT_BINDING_NOT_FOUND")
    evidence = row[5] if isinstance(row[5], dict) else json.loads(row[5])
    payload = row[6] if isinstance(row[6], dict) else json.loads(row[6])
    path = Path(payload["path"])
    if not path.is_absolute():
        path = Path(root).resolve() / path
    rows, columns = ResultObjectCoordinator._verify(
        path,
        str(row[3]),
        domain=str(row[0]),
        schema_version=str(row[1]),
        semantic_contract=str(row[2]),
        primary_key=payload["primary_key"],
        value_semantics=payload.get("value_semantics") or {},
    )
    if len(rows) != int(row[4]) or evidence.get("value_hash") != row[3]:
        raise ResultObjectError("RESULT_BINDING_EVIDENCE_MISMATCH")
    return rows
