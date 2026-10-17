"""Append-only PG startup attestations; runtime JSON files are not authoritative."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import v4_native
from .v4_forward_pg_r1 import ForwardFactStore, canonical, digest

CONTRACT = "V4_PRODUCT_STARTUP_ATTESTATION_PG_R1"
FOLDER = "data/v4/historical_source_ingress_pg_r1"
KIND = "startup_attestation"


def append(root: str | Path, attestation: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(attestation, dict) or attestation.get("contract_id") != "R4_PRODUCT_STARTUP_ATTESTATION_V1":
        raise ValueError("STARTUP_ATTESTATION_CONTRACT_INVALID")
    store = ForwardFactStore(Path(root), FOLDER)
    attestation = dict(attestation, pg_database_identity=store.database_identity)
    key = digest(canonical({"contract_id": CONTRACT, "pid": attestation.get("pid"),
                           "startup_time": attestation.get("startup_time"),
                           "exact_HEAD": attestation.get("exact_HEAD")}))
    record = {"contract_id": CONTRACT, "contract_version": "1.0.0",
              "attestation": attestation, "attestation_sha256": digest(canonical(attestation)),
              "accepted_head_mutation": False}
    binding = store.append(KIND, key, record)
    readback = read(root, binding)
    if readback != record:
        raise ValueError("STARTUP_ATTESTATION_PG_READBACK_MISMATCH")
    return binding


def read(root: str | Path, binding: dict[str, Any]) -> dict[str, Any]:
    record = ForwardFactStore(Path(root), FOLDER).read(binding)
    if (record.get("contract_id") != CONTRACT
            or record.get("attestation_sha256") != digest(canonical(record.get("attestation")))
            or record.get("accepted_head_mutation") is not False):
        raise ValueError("STARTUP_ATTESTATION_PG_IDENTITY_INVALID")
    return record


def read_latest(root: str | Path) -> dict[str, Any]:
    project = Path(root).resolve()
    folder = (project / FOLDER).resolve()
    schema = v4_native.workspace_schema(folder, "forward")
    dsn = v4_native.configured_reader_dsn()
    with v4_native.connection(schema, dsn=dsn, read_only=True) as pg:
        rows = pg.execute("SELECT payload,payload_sha256 FROM forward_facts WHERE kind=%s ORDER BY ordinal DESC LIMIT 1",
                          (KIND,)).fetchall()
        identity = ForwardFactStore._database_identity(pg)
    if len(rows) != 1:
        raise ValueError("STARTUP_ATTESTATION_PG_NOT_FOUND")
    payload, payload_sha = rows[0]
    if digest(payload.encode("utf-8")) != payload_sha:
        raise ValueError("STARTUP_ATTESTATION_PG_DIGEST_MISMATCH")
    record = json.loads(payload)
    if (record.get("contract_id") != CONTRACT
            or record.get("attestation_sha256") != digest(canonical(record.get("attestation")))
            or record.get("attestation", {}).get("pg_database_identity") != identity
            or record.get("accepted_head_mutation") is not False):
        raise ValueError("STARTUP_ATTESTATION_PG_IDENTITY_INVALID")
    return record
