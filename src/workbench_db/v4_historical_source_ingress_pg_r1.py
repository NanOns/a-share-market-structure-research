"""Versioned first-ingress and PG-only reads for bounded historical V4 inputs."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any
from datetime import datetime, timezone
from contextlib import contextmanager

import psycopg
from psycopg import sql

from . import v4_native
from .v4_forward_pg_r1 import ForwardFactStore, canonical, digest

CONTRACT = "V4_HISTORICAL_SOURCE_INGRESS_PG_R1"
VERSION = "1.0.0"
KIND = "historical_source_ingress"
FOLDER = "data/v4/historical_source_ingress_pg_r1"


def source_id_for_path(source_path: str) -> str:
    normalized = Path(source_path).as_posix()
    if not normalized or normalized.startswith("/") or ".." in Path(normalized).parts:
        raise ValueError("HISTORICAL_SOURCE_ID_PATH_INVALID")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _root(root: str | Path) -> Path:
    project = Path(root).resolve()
    folder = (project / FOLDER).resolve()
    if project.drive.upper() != "G:" or not folder.is_relative_to(project):
        raise ValueError("HISTORICAL_SOURCE_INGRESS_G_ROOT_REQUIRED")
    return project


@contextmanager
def _same_instance_read(schema: str):
    """Read on the shared configured PG role inside an explicit read-only transaction."""
    dsn = v4_native.configured_reader_dsn()
    with psycopg.connect(dsn, connect_timeout=5) as pg:
        pg.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        pg.execute("SET LOCAL statement_timeout='30s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        pg.execute(sql.SQL("SET LOCAL search_path TO {}, pg_catalog").format(sql.Identifier(schema)))
        v4_native.attest_read_role(pg, schema)
        yield pg


def ingest_file(root: str | Path, source_id: str, source_path: str | Path, *,
                expected_sha256: str | None = None, store: ForwardFactStore | None = None) -> dict[str, Any]:
    """Import one explicitly selected historical/source input as immutable PG fact."""
    project = _root(root)
    path = Path(source_path).resolve()
    if not path.is_relative_to(project) or not path.is_file():
        raise ValueError("HISTORICAL_SOURCE_INGRESS_PATH_INVALID")
    relative = path.relative_to(project).as_posix()
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and sha != expected_sha256:
        raise ValueError("HISTORICAL_SOURCE_INGRESS_DIGEST_MISMATCH")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    if text is not None:
        try:
            decoded: Any = json.loads(text)
        except ValueError:
            decoded = None
    else:
        decoded = None
    record = {
        "contract_id": CONTRACT,
        "contract_version": VERSION,
        "source_id": source_id,
        "source_path": relative,
        "source_sha256": sha,
        "source_bytes": len(raw),
        "source_raw_base64": base64.b64encode(raw).decode("ascii"),
        "source_text_utf8": text,
        "source_json": decoded,
        "first_ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    key = digest(canonical({"contract_id": CONTRACT, "source_id": source_id, "source_sha256": sha}))
    target = store or ForwardFactStore(project, FOLDER)
    try:
        existing = read_bound(project, relative, sha)
    except ValueError as exc:
        if str(exc) != "HISTORICAL_SOURCE_INGRESS_NOT_FOUND":
            raise
    else:
        if existing["raw"] != raw or existing["record"].get("source_id") != source_id:
            raise ValueError("HISTORICAL_SOURCE_INGRESS_IDENTITY_CONFLICT")
        return {"status": "ALREADY_PRESENT", "source_id": source_id,
                "source_path": relative, "source_sha256": sha,
                "source_bytes": len(raw), "binding": None}
    binding = target.append(KIND, key, record, migration_timeout_seconds=120)
    actual = read_bound(project, relative, sha)
    if actual["raw"] != raw:
        raise ValueError("HISTORICAL_SOURCE_INGRESS_READBACK_MISMATCH")
    return {"status": "INGESTED_OR_ALREADY_PRESENT", "source_id": source_id,
            "source_path": relative, "source_sha256": sha, "source_bytes": len(raw),
            "binding": binding}


def _query(root: str | Path, *, source_id: str | None = None,
           source_path: str | None = None, expected_sha256: str | None = None,
           pg: Any | None = None) -> tuple[dict[str, Any], bytes]:
    project = _root(root)
    if (source_id is None) == (source_path is None):
        raise ValueError("HISTORICAL_SOURCE_SELECTOR_REQUIRED")
    folder = (project / FOLDER).resolve()
    schema = v4_native.workspace_schema(folder, "forward")
    expected = {}
    try:
        expected = json.loads(os.environ.get("V4_PG_EXPECTED_DATABASE_IDENTITY_JSON", "{}"))
    except ValueError as exc:
        raise ValueError("PG_DATABASE_IDENTITY_CONFIGURATION_INVALID") from exc
    def query(connection):
        identity = ForwardFactStore._database_identity(connection)
        if expected and identity != expected:
            raise ValueError("HISTORICAL_SOURCE_INGRESS_DATABASE_IDENTITY_MISMATCH")
        return connection.execute(
            "SELECT payload,payload_sha256 FROM forward_facts WHERE kind=%s "
            "AND (%s::text IS NULL OR payload::jsonb->>'source_id'=%s) "
            "AND (%s::text IS NULL OR payload::jsonb->>'source_path'=%s) "
            "AND (%s::text IS NULL OR payload::jsonb->>'source_sha256'=%s) "
            "ORDER BY fact_key COLLATE \"C\" LIMIT 2",
            (KIND,source_id,source_id,source_path,source_path,expected_sha256,expected_sha256),
        ).fetchall()
    if pg is None:
        with _same_instance_read(schema) as connection:
            rows = query(connection)
    else:
        rows = query(pg)
    if len(rows) != 1:
        raise ValueError("HISTORICAL_SOURCE_INGRESS_NOT_UNIQUE" if rows else "HISTORICAL_SOURCE_INGRESS_NOT_FOUND")
    payload_raw, payload_sha = rows[0]
    encoded = payload_raw.encode("utf-8")
    if digest(encoded) != payload_sha:
        raise ValueError("HISTORICAL_SOURCE_INGRESS_PG_DIGEST_MISMATCH")
    record = json.loads(payload_raw)
    if (record.get("contract_id"), record.get("contract_version")) != (CONTRACT, VERSION):
        raise ValueError("HISTORICAL_SOURCE_INGRESS_CONTRACT_MISMATCH")
    raw = base64.b64decode(record.get("source_raw_base64", ""), validate=True)
    if (len(raw) != record.get("source_bytes")
            or hashlib.sha256(raw).hexdigest() != record.get("source_sha256")
            or record.get("source_path") != source_path and source_path is not None
            or record.get("source_id") != source_id and source_id is not None
            or record.get("source_sha256") != expected_sha256 and expected_sha256 is not None):
        raise ValueError("HISTORICAL_SOURCE_INGRESS_SOURCE_IDENTITY_MISMATCH")
    return record, raw


def read_source(root: str | Path, source_id: str) -> dict[str, Any]:
    """Resolve a uniquely imported historical source by stable source ID; no disk fallback."""
    record, raw = _query(root, source_id=source_id)
    text = record.get("source_text_utf8")
    if text is None:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            pass
    return {"record": record, "raw": raw, "value": record.get("source_json"),
            "text": text}


def materialize_bound(root: str | Path, binding: dict[str, Any]) -> Path:
    """Materialize an exact PG-ingressed source into the G-drive temp area for parsers."""
    source = read_bound(root, str(binding.get("path") or ""), str(binding.get("sha256") or ""))
    return _materialize_pg_source(root, source)


def _materialize_pg_source(root: str | Path, source: dict[str, Any]) -> Path:
    project = _root(root)
    from common.paths import resolve_ingest_temp_root
    temp_root = resolve_ingest_temp_root(project)
    path = (temp_root / "v4_historical_source_ingress" / source["record"]["source_sha256"] /
            Path(source["record"]["source_path"]).name)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        existing = path.read_bytes()
        if existing != source["raw"]:
            raise ValueError("HISTORICAL_SOURCE_TEMP_MATERIALIZATION_CONFLICT")
    else:
        temp = path.with_name(path.name + ".tmp")
        temp.write_bytes(source["raw"])
        temp.replace(path)
    return path


def read_bound(root: str | Path, source_path: str, expected_sha256: str) -> dict[str, Any]:
    """Resolve exact historical bytes from PG using the original path and digest binding."""
    record, raw = _query(root, source_path=source_path, expected_sha256=expected_sha256)
    text = record.get("source_text_utf8")
    if text is None:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            pass
    return {"record": record, "raw": raw, "value": record.get("source_json"),
            "text": text}


def admit_bound(root: str | Path, binding: dict[str, Any]) -> dict[str, Any]:
    """Admit one explicitly bound project source once, then return PG bytes.

    This is an ingress operation, not a read fallback: path and SHA-256 come
    from the caller's frozen source binding, the first append is immutable,
    and every returned value is read back from the shared PostgreSQL store.
    """
    project = _root(root)
    relative = binding.get("path")
    expected = binding.get("sha256")
    if (not isinstance(relative, str) or not relative
            or not isinstance(expected, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected)):
        raise ValueError("HISTORICAL_SOURCE_INGRESS_EXACT_BINDING_REQUIRED")
    try:
        admitted = read_bound(project, relative, expected)
    except ValueError as exc:
        if str(exc) != "HISTORICAL_SOURCE_INGRESS_NOT_FOUND":
            raise
        admitted = None
    if admitted is None:
        path = (project / relative).resolve()
        if not path.is_relative_to(project) or not path.is_file():
            raise ValueError("HISTORICAL_SOURCE_INGRESS_PATH_UNAVAILABLE")
        result = ingest_file(project, source_id_for_path(relative), path,
                             expected_sha256=expected)
        admitted = read_bound(project, relative, expected)
        if len(admitted["raw"]) != result["source_bytes"]:
            raise ValueError("HISTORICAL_SOURCE_INGRESS_SIZE_MISMATCH")
    declared_bytes = binding.get("bytes")
    if declared_bytes is not None and len(admitted["raw"]) != declared_bytes:
        raise ValueError("HISTORICAL_SOURCE_INGRESS_BOUND_SIZE_MISMATCH")
    return admitted


def read_bound_many(root: str | Path, bindings: list[dict[str, Any]]) -> list[dict[str, Any] | None]:
    """Resolve exact bindings under one read-only repeatable-read PG snapshot."""
    project = _root(root)
    folder = (project / FOLDER).resolve()
    schema = v4_native.workspace_schema(folder, "forward")
    results: list[dict[str, Any] | None] = []
    with _same_instance_read(schema) as pg:
        for binding in bindings:
            if not isinstance(binding, dict):
                results.append(None)
                continue
            source_path = binding.get("path")
            expected_sha256 = binding.get("sha256")
            if (not isinstance(source_path, str) or not source_path
                    or not isinstance(expected_sha256, str)
                    or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)):
                results.append(None)
                continue
            try:
                record, raw = _query(project, source_path=source_path,
                                     expected_sha256=expected_sha256, pg=pg)
            except ValueError:
                results.append(None)
                continue
            text = record.get("source_text_utf8")
            if text is None:
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    pass
            results.append({"record": record, "raw": raw,
                            "value": record.get("source_json"), "text": text})
    return results


def read_path(root: str | Path, source_path: str) -> dict[str, Any]:
    """Resolve one immutable imported revision by relative source path; no disk fallback."""
    record, raw = _query(root, source_path=source_path)
    text = record.get("source_text_utf8")
    if text is None:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            pass
    return {"record": record, "raw": raw, "value": record.get("source_json"),
            "text": text}


def ingress_path(root: str | Path, source_path: str, *, expected_sha256: str | None = None) -> dict[str, Any]:
    """Resolve a PG source fact, admitting the exact project input once when absent."""
    project = _root(root)
    relative = Path(source_path).as_posix()
    try:
        if expected_sha256:
            return read_bound(project, relative, expected_sha256)
        return read_path(project, relative)
    except ValueError as exc:
        if str(exc) not in {"HISTORICAL_SOURCE_INGRESS_NOT_FOUND", "HISTORICAL_SOURCE_INGRESS_NOT_UNIQUE"}:
            raise
    path = (project / relative).resolve()
    if not path.is_relative_to(project) or not path.is_file():
        raise ValueError("HISTORICAL_SOURCE_INGRESS_PATH_UNAVAILABLE")
    result = ingest_file(project, source_id_for_path(relative), path, expected_sha256=expected_sha256)
    return read_bound(project, relative, result["source_sha256"])


def materialize_path(root: str | Path, source_path: str, *, expected_sha256: str | None = None) -> Path:
    """Materialize only an existing PG-ingressed revision; never auto-ingest on read."""
    project = _root(root)
    source = (read_bound(project, source_path, expected_sha256)
              if expected_sha256 is not None else read_path(project, source_path))
    return _materialize_pg_source(project, source)
