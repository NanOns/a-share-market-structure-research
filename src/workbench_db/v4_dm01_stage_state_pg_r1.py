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
DATA_HEAD_IMPORT_CONTRACT = "V4_DM01_DATA_HEAD_IMPORT_R1"
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
    "data_head",
    "stage_head",
    "dev_baseline_head",
    "bootstrap_manifest",
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
    payload_day = payload.get("trade_date", payload.get("target_date", payload.get("accepted_trade_date")))
    if payload_day != day:
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


def build_data_head_import_payload(root, binding: dict) -> dict:
    """Prepare the exact accepted V2 Data Head for a one-time PG import.

    This is an explicit source-ingress operation. The input path is fixed to
    the current V4 Data Head namespace, and both its raw bytes and validated
    decoded object are retained so PG readback can prove byte identity.
    """
    project_root = Path(root).resolve()
    expected_path = "data/v4/V4_DATA_ACCEPTED_HEAD.json"
    if project_root.drive.upper() != "G:":
        raise ValueError("DM01_DATA_HEAD_IMPORT_G_ROOT_REQUIRED")
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256", "bytes"}:
        raise ValueError("DM01_DATA_HEAD_IMPORT_BINDING_REQUIRED")
    if binding.get("path") != expected_path:
        raise ValueError("DM01_DATA_HEAD_IMPORT_SOURCE_PATH_INVALID")
    source = (project_root / expected_path).resolve()
    if not source.is_relative_to(project_root) or not source.is_file():
        raise ValueError("DM01_DATA_HEAD_IMPORT_SOURCE_MISSING")
    raw = source.read_bytes()
    if len(raw) != binding["bytes"] or digest(raw) != binding["sha256"]:
        raise ValueError("DM01_DATA_HEAD_IMPORT_SOURCE_DIGEST_MISMATCH")
    try:
        head = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("DM01_DATA_HEAD_IMPORT_SOURCE_JSON_INVALID") from exc
    if (not isinstance(head, dict) or head.get("contract_id") != "V4_DATA_ACCEPTED_HEAD_V2"
            or head.get("version") != "2.0.0" or not isinstance(head.get("accepted_trade_date"), str)):
        raise ValueError("DM01_DATA_HEAD_IMPORT_V2_REQUIRED")
    try:
        from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
        authority = CurrentStageAuthority(project_root)
        if authority.data_ref != binding or authority.data != head:
            raise ValueError("DM01_DATA_HEAD_IMPORT_NOT_CURRENTLY_ACCEPTED")
        authority_bindings = authority.bindings()
    except (AssertionError, KeyError, TypeError, ValueError, OSError) as exc:
        raise ValueError("DM01_DATA_HEAD_IMPORT_ACCEPTED_HEAD_INVALID") from exc
    return {
        "contract_id": DATA_HEAD_IMPORT_CONTRACT,
        "contract_version": VERSION,
        "trade_date": head["accepted_trade_date"],
        "accepted_trade_date": head["accepted_trade_date"],
        "source_binding": dict(binding),
        "source_raw_utf8": raw.decode("utf-8"),
        "source_raw_sha256": digest(raw),
        "source_raw_bytes": len(raw),
        "accepted_authority_bindings": authority_bindings,
        "head": head,
    }


def decode_data_head_import_payload(payload: dict) -> tuple[dict, dict]:
    """Recover a byte-verified V2 Head and its source binding from PG state."""
    if (not isinstance(payload, dict) or payload.get("contract_id") != DATA_HEAD_IMPORT_CONTRACT
            or payload.get("contract_version") != VERSION):
        raise ValueError("DM01_DATA_HEAD_IMPORT_ENVELOPE_REQUIRED")
    binding = payload.get("source_binding")
    if (not isinstance(binding, dict) or binding.get("path") != "data/v4/V4_DATA_ACCEPTED_HEAD.json"
            or not isinstance(binding.get("sha256"), str)
            or isinstance(binding.get("bytes"), bool) or not isinstance(binding.get("bytes"), int)):
        raise ValueError("DM01_DATA_HEAD_IMPORT_BINDING_INVALID")
    authority_bindings = payload.get("accepted_authority_bindings")
    if (not isinstance(authority_bindings, dict) or authority_bindings.get("data") != binding
            or not isinstance(authority_bindings.get("stage"), dict)
            or not isinstance(authority_bindings.get("current_stage_head"), dict)
            or not isinstance(authority_bindings.get("current_authority_contract"), dict)):
        raise ValueError("DM01_DATA_HEAD_IMPORT_ACCEPTED_AUTHORITY_BINDING_REQUIRED")
    raw_text = payload.get("source_raw_utf8")
    if not isinstance(raw_text, str):
        raise ValueError("DM01_DATA_HEAD_IMPORT_RAW_BYTES_REQUIRED")
    raw = raw_text.encode("utf-8")
    if (len(raw) != binding["bytes"] or len(raw) != payload.get("source_raw_bytes")
            or digest(raw) != binding["sha256"] or digest(raw) != payload.get("source_raw_sha256")):
        raise ValueError("DM01_DATA_HEAD_IMPORT_SOURCE_DIGEST_MISMATCH")
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except ValueError as exc:
        raise ValueError("DM01_DATA_HEAD_IMPORT_SOURCE_JSON_INVALID") from exc
    if (not isinstance(decoded, dict) or decoded != payload.get("head")
            or decoded.get("contract_id") != "V4_DATA_ACCEPTED_HEAD_V2"
            or decoded.get("version") != "2.0.0"
            or decoded.get("accepted_trade_date") != payload.get("accepted_trade_date")
            or payload.get("trade_date") != payload.get("accepted_trade_date")):
        raise ValueError("DM01_DATA_HEAD_IMPORT_PAYLOAD_MISMATCH")
    return decoded, dict(binding)


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


def read_latest_stage(root, *, stage: str) -> dict:
    """Read the unique fact at the latest dated stage; no local Head fallback."""
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
                 WHERE kind=%s AND payload::jsonb->>'stage'=%s
                 ORDER BY payload::jsonb->>'trade_date' DESC, fact_key COLLATE \"C\"
                 LIMIT 2""",
            (KIND, stage),
        ).fetchall()
    if not rows:
        raise ValueError("DM01_STAGE_STATE_NOT_FOUND")
    if len(rows) > 1:
        first = json.loads(rows[0][0])
        second = json.loads(rows[1][0])
        if first.get("trade_date") == second.get("trade_date"):
            raise ValueError("DM01_STAGE_STATE_NOT_UNIQUE")
    raw, expected_sha = rows[0]
    if digest(raw.encode("utf-8")) != expected_sha:
        raise ValueError("DM01_STAGE_STATE_PG_PAYLOAD_DIGEST_MISMATCH")
    record = json.loads(raw)
    payload = record.get("payload") if isinstance(record, dict) else None
    day = record.get("trade_date") if isinstance(record, dict) else None
    payload_day = (payload.get("trade_date", payload.get("target_date", payload.get("accepted_trade_date")))
                   if isinstance(payload, dict) else None)
    if (not isinstance(record, dict) or record.get("contract_id") != CONTRACT or record.get("contract_version") != VERSION
            or record.get("stage") != stage or not isinstance(payload, dict)
            or _day(day) != day or payload_day != day or digest(canonical(payload)) != record.get("payload_sha256")):
        raise ValueError("DM01_STAGE_STATE_BINDING_MISMATCH")
    return payload
