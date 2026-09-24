"""Atomic accepted-head activation and downstream replay invalidation."""
from __future__ import annotations

from datetime import date

from psycopg import sql

from .contracts import SOURCE_AUTHORITY_CONTRACT


CONTRACT_ID = "FOCUS_CORE_HEAD_ACTIVATION_V2"


def activate_core_head(repository, *, focus_run_id: str, trade_date: date,
                       revision: int) -> str | None:
    """Activate a READY immutable run and invalidate all later accepted heads.

    Must run in the core publication transaction while the caller holds the
    per-date advisory lock. Same-day revisions point at the prior trade-date
    head, never the older same-day revision.
    """
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    if revision < 1:
        raise ValueError("invalid Focus revision")
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL(
            "select trade_date,revision,core_publication_status "
            "from {}.focus_runs where focus_run_id=%s "
            "and source_authority_contract_id=%s for update").format(schema, schema),
            (focus_run_id, SOURCE_AUTHORITY_CONTRACT))
        run = cur.fetchone()
        if run != (trade_date, revision, "READY"):
            raise ValueError("only the exact READY Focus run can activate")
        # Replay is strictly chronological. Checking only the immediately
        # preceding head is insufficient if a trade date is missing from the
        # head table: a later valid head could otherwise hide an older stale
        # lineage row.
        cur.execute(sql.SQL(
            "select trade_date from {}.focus_trade_date_heads "
            "where source_authority_contract_id=%s "
            "and lineage_state='REPLAY_REQUIRED' "
            "order by trade_date limit 1").format(schema),
            (SOURCE_AUTHORITY_CONTRACT,))
        oldest_pending = cur.fetchone()
        if oldest_pending and oldest_pending[0] < trade_date:
            raise ValueError("Focus replay must proceed in trade-date order from "
                             + oldest_pending[0].isoformat())
        cur.execute(sql.SQL(
            "select trade_date,accepted_focus_run_id,lineage_state "
            "from {}.focus_trade_date_heads where trade_date<%s "
            "and source_authority_contract_id=%s order by trade_date desc limit 1"
        ).format(schema), (trade_date, SOURCE_AUTHORITY_CONTRACT))
        prior = cur.fetchone()
        if prior and prior[2] != "VALID":
            raise ValueError("prior Focus head requires replay")
        predecessor_run_id = str(prior[1]) if prior else None
        cur.execute(sql.SQL(
            "select accepted_revision from {}.focus_trade_date_heads "
            "where trade_date=%s and source_authority_contract_id=%s for update"
        ).format(schema), (trade_date, SOURCE_AUTHORITY_CONTRACT))
        existing = cur.fetchone()
        if existing is None:
            if revision != 1:
                raise ValueError("first Focus day revision must be 1")
            cur.execute(sql.SQL(
                "insert into {}.focus_trade_date_heads "
                "(trade_date,source_authority_contract_id,accepted_focus_run_id,"
                "accepted_revision,predecessor_focus_run_id,lineage_state,activated_at_utc) "
                "values (%s,%s,%s,%s,%s,'VALID',now())").format(schema),
                (trade_date, SOURCE_AUTHORITY_CONTRACT, focus_run_id,
                 revision, predecessor_run_id))
        else:
            if revision != int(existing[0]) + 1:
                raise ValueError("Focus revision must increment by one")
            cur.execute(sql.SQL(
                "update {}.focus_trade_date_heads set accepted_focus_run_id=%s,"
                "accepted_revision=%s,predecessor_focus_run_id=%s,"
                "lineage_state='VALID',activated_at_utc=now() "
                "where trade_date=%s and source_authority_contract_id=%s"
            ).format(schema),
                (focus_run_id, revision, predecessor_run_id, trade_date,
                 SOURCE_AUTHORITY_CONTRACT))
        cur.execute(sql.SQL(
            "update {}.focus_runs set core_publication_status='ACTIVATED',"
            "activated_at_utc=now() where focus_run_id=%s "
            "and core_publication_status='READY'").format(schema), (focus_run_id,))
        if cur.rowcount != 1:
            raise ValueError("Focus run activation state changed")
        cur.execute(sql.SQL(
            "update {}.focus_trade_date_heads set lineage_state='REPLAY_REQUIRED' "
            "where trade_date>%s and source_authority_contract_id=%s "
            "and lineage_state='VALID'").format(schema),
            (trade_date, SOURCE_AUTHORITY_CONTRACT))
    return predecessor_run_id
