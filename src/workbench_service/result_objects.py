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

import pyarrow as pa
import pyarrow.parquet as pq

from workbench_db.digest import logical_digest
from workbench_db.result_object_repository import DuckDBResultObjectRepository, ResultObjectRepository


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

    def __init__(self, root: str | Path, database_path: str | Path | None = None, *, repository: ResultObjectRepository | None = None):
        self.root = Path(root).resolve()
        self.object_root = self.root / "data/analysis_objects"
        self.repository = repository or DuckDBResultObjectRepository(self.root, database_path)

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
        try:
            reused = self.repository.persist(
                slice_id=slice_id,
                result_object_id=result_object_id,
                domain=domain,
                schema_version=schema_version,
                semantic_contract=semantic_contract,
                value_hash=value_hash,
                logical_hash=logical_hash,
                row_count=row_count,
                storage_kind=STORAGE_KIND,
                created_at=created_at,
                object_path=str(object_path),
                relative_path=object_path.relative_to(self.root).as_posix(),
                columns=columns,
                primary_key=keys,
                value_semantics=semantics,
                basis=basis,
                identity_evidence=identity_evidence,
                dependencies=dependency_rows,
                trade_date=trade_date,
                contract_id=contract_id,
                input_hash=input_hash,
                dependency_hash=dependency_hash,
                daily_basis=basis.get("daily_basis"),
            )
        except ValueError as exc:
            raise ResultObjectError(str(exc)) from exc
        if reused:
            self._verify(object_path, value_hash, domain=domain, schema_version=schema_version, semantic_contract=semantic_contract, primary_key=keys, value_semantics=semantics)
        return {"slice_id": slice_id, "result_object_id": result_object_id, "value_hash": value_hash, "row_count": row_count, "reused": reused}


def read_result_rows(connection: Any, root: str | Path, slice_id: str) -> list[dict[str, Any]]:
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
