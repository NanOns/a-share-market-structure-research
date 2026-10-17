"""Read the active Operational Successor Head from the canonical PG registry.

The legacy workspace JSON remains an ingress artifact only. This module never
uses it to choose an operational candidate or recover a Head.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .v4_native import connection

CONTRACT = "V4_OPERATIONAL_RESEARCH_LIVE_HEAD_PG_R1"
TABLE = "operational_research_heads"


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def read_current(root: str | Path) -> dict:
    """Return the one current PG Head and verify its immutable candidate digest."""
    root = Path(root).resolve()
    with connection("v4", read_only=True) as pg:
        found = pg.execute(
            "SELECT to_regclass('v4.operational_research_heads')"
        ).fetchone()
        if not found or found[0] is None:
            raise ValueError("PG_OPERATIONAL_HEAD_REGISTRY_NOT_INSTALLED")
        row = pg.execute(
            "SELECT head_payload::text, head_bytes, head_sha256, generation, updated_at "
            "FROM operational_research_heads WHERE singleton=true"
        ).fetchone()
        identity = pg.execute(
            "SELECT current_database(), (SELECT oid FROM pg_database WHERE datname=current_database()), "
            "inet_server_addr()::text, inet_server_port()"
        ).fetchone()
    if row is None:
        raise ValueError("PG_ACCEPTED_OPERATIONAL_HEAD_REQUIRED_NO_FILE_FALLBACK")
    payload_text, raw_bytes, expected, generation, updated_at = row
    try:
        payload = json.loads(raw_bytes)
    except (TypeError, ValueError) as exc:
        raise ValueError("PG_OPERATIONAL_HEAD_PAYLOAD_INVALID") from exc
    if payload != json.loads(payload_text):
        raise ValueError("PG_OPERATIONAL_HEAD_JSONB_BYTES_MISMATCH")
    actual = hashlib.sha256(raw_bytes).hexdigest()
    if actual != expected:
        raise ValueError("PG_OPERATIONAL_HEAD_DIGEST_MISMATCH")
    if payload.get("contract_id") != "V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1":
        raise ValueError("PG_OPERATIONAL_HEAD_CONTRACT_INVALID")
    return dict(contract_id=CONTRACT, candidate=payload, head_sha256=actual,
                generation=generation, head_bytes=len(raw_bytes), updated_at=updated_at,
                database_identity=dict(database=identity[0], database_oid=identity[1],
                                       host=identity[2], port=identity[3]))


def compare_and_swap(root: str | Path, candidate: dict, expected_sha256: str) -> dict:
    """Atomically replace the current Head, requiring its exact prior digest.

    The table is pre-provisioned by migration 044. This operation never seeds
    an empty registry from a local file.
    """
    raw = canonical(candidate)
    candidate_sha = hashlib.sha256(raw).hexdigest()
    with connection("v4") as pg:
        row = pg.execute(
            "SELECT head_payload, head_bytes, head_sha256, generation FROM operational_research_heads "
            "WHERE singleton=true FOR UPDATE"
        ).fetchone()
        if row is None:
            raise ValueError("PG_OPERATIONAL_HEAD_BOOTSTRAP_REQUIRED_NO_FILE_IMPORT")
        prior_payload, prior_raw, prior_sha, generation = row
        prior = json.loads(prior_raw) if isinstance(prior_raw, str) else prior_raw
        if prior != (json.loads(prior_payload) if isinstance(prior_payload, str) else prior_payload):
            raise ValueError("PG_OPERATIONAL_HEAD_JSONB_BYTES_MISMATCH")
        actual_prior = hashlib.sha256(prior_raw).hexdigest()
        if actual_prior != prior_sha or prior_sha != expected_sha256:
            raise ValueError("STALE_OPERATIONAL_HEAD_PG_CAS")
        updated = pg.execute(
            "UPDATE operational_research_heads SET head_payload=%s::jsonb, head_bytes=%s, head_sha256=%s, "
            "generation=generation+1 WHERE singleton=true AND head_sha256=%s "
            "RETURNING generation, updated_at",
            (raw.decode("utf-8"), raw, candidate_sha, expected_sha256),
        ).fetchone()
        if updated is None:
            raise ValueError("STALE_OPERATIONAL_HEAD_PG_CAS")
    return dict(candidate=candidate, head_sha256=candidate_sha,
                generation=updated[0], updated_at=updated[1],
                predecessor=prior, predecessor_sha256=prior_sha)
