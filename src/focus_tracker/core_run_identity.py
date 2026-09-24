"""FOCUS-03 exact run/revision idempotency guard under the writer transaction."""
from __future__ import annotations

from datetime import date

from psycopg import sql

from .contracts import SOURCE_AUTHORITY_CONTRACT


CONTRACT_ID = "FOCUS_CORE_RUN_IDEMPOTENCY_V1"


def inspect_run_slot(repository, *, trade_date: date, revision: int,
                     run_id: str, source_identity_digest: str,
                     observation_input_digest: str, state_contract_id: str,
                     parameter_set_id: str, dependency_lock_hash: str) -> str:
    """Return NEW or ALREADY_ACTIVATED; reject every ambiguous collision.

    Call while holding the per-date writer advisory lock and in the same
    transaction as insertion/head activation. A BUILDING/READY orphan is not
    silently reused as an accepted run.
    """
    if revision < 1 or not run_id:
        raise ValueError("invalid Focus run identity")
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL(
            "select focus_run_id,source_identity_digest,observation_input_digest,"
            "state_contract_id,parameter_set_id,dependency_lock_hash,"
            "core_publication_status from {}.focus_runs "
            "where trade_date=%s and source_authority_contract_id=%s "
            "and revision=%s").format(schema),
            (trade_date, SOURCE_AUTHORITY_CONTRACT, revision))
        rows = cur.fetchall()
        if len(rows) > 1:
            raise ValueError("ambiguous Focus run slot")
        if not rows:
            return "NEW"
        existing = rows[0]
        expected = (run_id, source_identity_digest, observation_input_digest,
                    state_contract_id, parameter_set_id, dependency_lock_hash)
        if tuple(str(value) for value in existing[:6]) != expected:
            raise ValueError("immutable Focus run/revision conflict")
        if existing[6] != "ACTIVATED":
            raise ValueError("matching Focus run is not activated")
        cur.execute(sql.SQL(
            "select accepted_focus_run_id,accepted_revision,lineage_state "
            "from {}.focus_trade_date_heads where trade_date=%s "
            "and source_authority_contract_id=%s").format(schema),
            (trade_date, SOURCE_AUTHORITY_CONTRACT))
        head = cur.fetchone()
        if head != (run_id, revision, "VALID"):
            raise ValueError("matching Focus run is not the valid accepted head")
        return "ALREADY_ACTIVATED"
