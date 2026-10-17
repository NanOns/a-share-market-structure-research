"""Canonical PostgreSQL Head for DM01 V2 accepted data.

The initial row is an explicit, exact-byte bootstrap from an already-ingressed
Head fact. All subsequent selection and CAS operations use PostgreSQL only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .v4_native import connection,current_read_snapshot

CONTRACT = "V4_DM01_DATA_ACCEPTED_HEAD_PG_R1"
TABLE = "dm01_data_accepted_heads"
SOURCE_PATH = "data/v4/V4_DATA_ACCEPTED_HEAD.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _decode(raw: bytes, expected_sha: str) -> dict[str, Any]:
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError("DM01_PG_DATA_HEAD_DIGEST_MISMATCH")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("DM01_PG_DATA_HEAD_JSON_INVALID") from exc
    if not isinstance(payload, dict) or payload.get("contract_id") != "V4_DATA_ACCEPTED_HEAD_V2":
        raise ValueError("DM01_PG_DATA_HEAD_CONTRACT_INVALID")
    return payload


def read_current(root: str | Path) -> dict[str, Any]:
    """Read and verify the current accepted Head from one PG snapshot."""
    def read(pg):
        if pg.execute("SELECT to_regclass('v4.dm01_data_accepted_heads')").fetchone()[0] is None:
            raise ValueError("DM01_PG_DATA_HEAD_REGISTRY_NOT_INSTALLED")
        row = pg.execute(
            "SELECT head_payload::text,head_bytes,head_sha256,generation,updated_at "
            "FROM v4.dm01_data_accepted_heads WHERE singleton=true"
        ).fetchone()
        identity = pg.execute(
            "SELECT current_database(),(SELECT oid FROM pg_database WHERE datname=current_database()),"
            "inet_server_addr()::text,inet_server_port()"
        ).fetchone()
        return row,identity
    active=current_read_snapshot()
    if active is not None:row,identity=read(active)
    else:
        with connection("v4", read_only=True) as pg:row,identity=read(pg)
    if row is None:
        raise ValueError("DM01_PG_DATA_HEAD_BOOTSTRAP_REQUIRED")
    payload_text, raw, expected, generation, updated_at = row
    raw = bytes(raw)
    payload = _decode(raw, str(expected).strip())
    if payload != json.loads(payload_text):
        raise ValueError("DM01_PG_DATA_HEAD_JSONB_BYTES_MISMATCH")
    return dict(contract_id=CONTRACT, candidate=payload,
                head_sha256=str(expected).strip(), head_bytes=len(raw),
                generation=int(generation), updated_at=updated_at,
                database_identity=dict(database=identity[0], database_oid=identity[1],
                                       host=identity[2], port=identity[3]))


def bootstrap_from_ingress(root: str | Path) -> dict[str, Any]:
    """Copy the exact previously ingressed Head into an empty PG Head registry."""
    from .v4_historical_source_ingress_pg_r1 import read_path

    source = read_path(root, SOURCE_PATH)
    raw = source["raw"]
    expected = source["record"]["source_sha256"]
    payload = _decode(raw, expected)
    with connection("v4") as pg:
        pg.execute(
            "INSERT INTO v4.dm01_data_accepted_heads "
            "(singleton,head_payload,head_bytes,head_sha256,generation) "
            "VALUES(true,%s::jsonb,%s,%s,1) ON CONFLICT(singleton) DO NOTHING",
            (raw.decode("utf-8"), raw, expected),
        )
    current = read_current(root)
    if current["candidate"] != payload or current["head_sha256"] != expected:
        raise ValueError("DM01_PG_DATA_HEAD_BOOTSTRAP_READBACK_MISMATCH")
    return current


def compare_and_swap(root: str | Path, candidate: dict[str, Any],
                     expected_sha256: str) -> dict[str, Any]:
    """Append the predecessor and atomically CAS the accepted Head in PG."""
    if candidate.get("contract_id") != "V4_DATA_ACCEPTED_HEAD_V2":
        raise ValueError("DM01_PG_DATA_HEAD_CANDIDATE_CONTRACT_INVALID")
    raw = canonical(candidate)
    candidate_sha = hashlib.sha256(raw).hexdigest()
    with connection("v4") as pg:
        prior_row = pg.execute(
            "SELECT head_payload,head_bytes,head_sha256,generation "
            "FROM v4.dm01_data_accepted_heads WHERE singleton=true FOR UPDATE"
        ).fetchone()
        if prior_row is None:
            raise ValueError("DM01_PG_DATA_HEAD_BOOTSTRAP_REQUIRED")
        prior_payload, prior_raw, prior_sha, generation = prior_row
        prior_raw = bytes(prior_raw)
        prior_sha = str(prior_sha).strip()
        prior = _decode(prior_raw, prior_sha)
        if prior != json.loads(prior_payload):
            raise ValueError("DM01_PG_DATA_HEAD_JSONB_BYTES_MISMATCH")
        if prior_sha != expected_sha256:
            raise ValueError("STALE_DM01_DATA_HEAD_PG_CAS")
        updated = pg.execute(
            "UPDATE v4.dm01_data_accepted_heads SET head_payload=%s::jsonb,head_bytes=%s,"
            "head_sha256=%s,generation=generation+1 WHERE singleton=true "
            "AND head_sha256=%s RETURNING generation,updated_at",
            (raw.decode("utf-8"), raw, candidate_sha, expected_sha256),
        ).fetchone()
        if updated is None:
            raise ValueError("STALE_DM01_DATA_HEAD_PG_CAS")
    return dict(contract_id=CONTRACT, candidate=candidate,
                head_sha256=candidate_sha, head_bytes=len(raw),
                generation=int(updated[0]), updated_at=updated[1],
                predecessor=prior, predecessor_sha256=prior_sha)
