"""Date-bound PG authority for DM-01 inter-stage orchestration state."""
from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path

from . import v4_native
from .v4_forward_pg_r1 import ForwardFactStore, canonical, digest

CONTRACT = "V4_DM01_STAGE_STATE_PG_R1"
VERSION = "1.0.0"
FOLDER = "data/v4/dm01_stage_state_pg_r1"
KIND = "stage_state"
STAGES = frozenset({
    "phase0_acceptance",
    "v401_acceptance",
    "v401_postcheck",
    "v402_acceptance",
    "gbbq_revision_probe",
    "lifecycle_snapshot",
    "special_phase_manifest",
    "daily_source_freeze",
    "source_readiness",
    "v402_acceptance",
})


def _day(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError("DM01_STAGE_TRADE_DATE_INVALID") from exc


def _expected_identity() -> dict:
    try:
        identity = json.loads(os.environ.get("V4_PG_EXPECTED_DATABASE_IDENTITY_JSON", "{}"))
    except ValueError as exc:
        raise ValueError("PG_DATABASE_IDENTITY_CONFIGURATION_INVALID") from exc
    if not isinstance(identity, dict) or not {
        "database", "database_oid", "host", "port"
    }.issubset(identity):
        raise ValueError("PG_EXPECTED_DATABASE_IDENTITY_REQUIRED")
    return identity


def _store(root) -> ForwardFactStore:
    project_root = Path(root).resolve()
    if project_root.drive.upper() != "G:":
        raise ValueError("DM01_STAGE_STATE_G_ROOT_REQUIRED")
    folder = (project_root / FOLDER).resolve()
    if not folder.is_relative_to(project_root):
        raise ValueError("DM01_STAGE_STATE_G_ROOT_REQUIRED")
    # Do not construct ForwardFactStore here: its constructor creates schemas,
    # installs DDL, and imports local JSON. Stage-state calls may only use the
    # separately provisioned relation and the explicitly configured writer.
    store = ForwardFactStore.__new__(ForwardFactStore)
    store.root = project_root
    store.folder = folder
    store.schema = v4_native.workspace_schema(folder, "forward")
    store.dsn = v4_native.configured_dsn()
    with v4_native.connection(store.schema, dsn=store.dsn) as pg:
        relation = pg.execute("SELECT to_regclass('forward_facts')").fetchone()
        if not relation or relation[0] is None:
            raise ValueError("DM01_STAGE_STATE_SCHEMA_NOT_PROVISIONED")
        store.database_identity = ForwardFactStore._database_identity(pg)
    if store.database_identity != _expected_identity():
        raise ValueError("DM01_STAGE_STATE_DATABASE_IDENTITY_MISMATCH")
    return store


def _read_fact(root, binding: dict) -> dict:
    """Read a descriptor without constructing the write-capable Forward store."""
    project_root = Path(root).resolve()
    folder = (project_root / FOLDER).resolve()
    if project_root.drive.upper() != "G:" or not folder.is_relative_to(project_root):
        raise ValueError("DM01_STAGE_STATE_G_ROOT_REQUIRED")
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256", "bytes"}:
        raise ValueError("DM01_STAGE_STATE_BINDING_REQUIRED")
    descriptor_path = (project_root / binding["path"]).resolve()
    if not descriptor_path.is_relative_to(folder) or not descriptor_path.name.endswith(".pg.json"):
        raise ValueError("DM01_STAGE_STATE_DESCRIPTOR_PATH_INVALID")
    raw = descriptor_path.read_bytes()
    if len(raw) != binding["bytes"] or digest(raw) != binding["sha256"]:
        raise ValueError("DM01_STAGE_STATE_DESCRIPTOR_DIGEST_MISMATCH")
    descriptor = json.loads(raw)
    schema = v4_native.workspace_schema(folder, "forward")
    if (descriptor.get("contract_id") != "V4_FORWARD_PG_FACT_STORE_R1"
            or descriptor.get("engine") != "postgresql"
            or descriptor.get("schema") != schema
            or descriptor.get("kind") != KIND
            or descriptor.get("database_identity") != _expected_identity()):
        raise ValueError("DM01_STAGE_STATE_DESCRIPTOR_IDENTITY_MISMATCH")
    dsn = v4_native.configured_reader_dsn()
    with v4_native.connection(schema, read_only=True, dsn=dsn) as pg:
        if ForwardFactStore._database_identity(pg) != descriptor["database_identity"]:
            raise ValueError("DM01_STAGE_STATE_DATABASE_IDENTITY_MISMATCH")
        row = pg.execute(
            "SELECT payload,payload_sha256 FROM forward_facts WHERE kind=%s AND fact_key=%s",
            (descriptor["kind"], descriptor["fact_key"]),
        ).fetchone()
    if (row is None or row[1] != descriptor.get("payload_sha256")
            or digest(row[0].encode("utf-8")) != descriptor["payload_sha256"]):
        raise ValueError("DM01_STAGE_STATE_PG_PAYLOAD_DIGEST_MISMATCH")
    return json.loads(row[0])


def append_stage(root, trade_date: str, stage: str, payload: dict) -> dict:
    """Append one immutable stage result to the explicitly configured PG writer."""
    day = _day(trade_date)
    if stage not in STAGES:
        raise ValueError("DM01_STAGE_STATE_STAGE_INVALID")
    if not isinstance(payload, dict) or not isinstance(payload.get("contract_id"), str):
        raise ValueError("DM01_STAGE_STATE_PAYLOAD_CONTRACT_REQUIRED")
    if payload.get("trade_date", payload.get("target_date")) != day:
        raise ValueError("DM01_STAGE_STATE_PAYLOAD_DATE_MISMATCH")
    record = {
        "contract_id": CONTRACT,
        "contract_version": VERSION,
        "trade_date": day,
        "stage": stage,
        "payload_sha256": digest(canonical(payload)),
        "payload": payload,
    }
    fact_key = digest(canonical(record))
    store = _store(root)
    if store.database_identity != _expected_identity():
        raise ValueError("DM01_STAGE_STATE_DATABASE_IDENTITY_MISMATCH")
    binding = store.append(KIND, fact_key, record, migration_timeout_seconds=120)
    return {
        "contract_id": CONTRACT,
        "contract_version": VERSION,
        "trade_date": day,
        "stage": stage,
        "fact_key": fact_key,
        "payload_sha256": record["payload_sha256"],
        "binding": binding,
    }


def read_stage(root, binding: dict, *, trade_date: str, stage: str) -> dict:
    """Read the exact immutable stage fact; no report-file or latest-row fallback."""
    day = _day(trade_date)
    if stage not in STAGES:
        raise ValueError("DM01_STAGE_STATE_STAGE_INVALID")
    if not isinstance(binding, dict):
        raise ValueError("DM01_STAGE_STATE_BINDING_REQUIRED")
    record = _read_fact(root, binding)
    if not isinstance(record, dict):
        raise ValueError("DM01_STAGE_STATE_BINDING_MISMATCH")
    payload = record.get("payload") if isinstance(record, dict) else None
    if (record.get("contract_id") != CONTRACT
            or record.get("contract_version") != VERSION
            or record.get("trade_date") != day
            or record.get("stage") != stage
            or not isinstance(payload, dict)
            or digest(canonical(payload)) != record.get("payload_sha256")):
        raise ValueError("DM01_STAGE_STATE_BINDING_MISMATCH")
    return payload


def read_unique_stage(root, *, trade_date: str, stage: str) -> dict:
    """Resolve one date/stage fact directly in PG; duplicate revisions fail closed."""
    day = _day(trade_date)
    if stage not in STAGES:
        raise ValueError("DM01_STAGE_STATE_STAGE_INVALID")
    project_root = Path(root).resolve()
    folder = (project_root / FOLDER).resolve()
    if project_root.drive.upper() != "G:" or not folder.is_relative_to(project_root):
        raise ValueError("DM01_STAGE_STATE_G_ROOT_REQUIRED")
    schema = v4_native.workspace_schema(folder, "forward")
    expected = _expected_identity()
    with v4_native.connection(schema, read_only=True, dsn=v4_native.configured_reader_dsn()) as pg:
        if ForwardFactStore._database_identity(pg) != expected:
            raise ValueError("DM01_STAGE_STATE_DATABASE_IDENTITY_MISMATCH")
        rows = pg.execute(
            """SELECT payload,payload_sha256 FROM forward_facts
                 WHERE kind=%s
                   AND payload::jsonb->>'trade_date'=%s
                   AND payload::jsonb->>'stage'=%s
                 ORDER BY fact_key COLLATE \"C\" LIMIT 2""",
            (KIND, day, stage),
        ).fetchall()
    if len(rows) != 1:
        raise ValueError("DM01_STAGE_STATE_NOT_UNIQUE")
    raw, expected_sha = rows[0]
    if digest(raw.encode("utf-8")) != expected_sha:
        raise ValueError("DM01_STAGE_STATE_PG_PAYLOAD_DIGEST_MISMATCH")
    record = json.loads(raw)
    payload = record.get("payload") if isinstance(record, dict) else None
    if (record.get("contract_id") != CONTRACT or record.get("contract_version") != VERSION
            or record.get("trade_date") != day or record.get("stage") != stage
            or not isinstance(payload, dict) or digest(canonical(payload)) != record.get("payload_sha256")):
        raise ValueError("DM01_STAGE_STATE_BINDING_MISMATCH")
    return payload
