"""Read and enforce ordered Focus historical replay chains."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from psycopg import sql

from .contracts import SOURCE_AUTHORITY_CONTRACT


CONTRACT_ID = "FOCUS_ORDERED_REPLAY_CHAIN_V1"


@dataclass(frozen=True, order=True)
class ReplayItem:
    trade_date: date
    old_focus_run_id: str
    accepted_revision: int


def pending_replay_chain(repository, *, from_date: date | None = None) -> tuple[ReplayItem, ...]:
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        if from_date is None:
            cur.execute(sql.SQL(
                "select trade_date,accepted_focus_run_id,accepted_revision "
                "from {}.focus_trade_date_heads where source_authority_contract_id=%s "
                "and lineage_state='REPLAY_REQUIRED' order by trade_date"
            ).format(schema), (SOURCE_AUTHORITY_CONTRACT,))
        else:
            cur.execute(sql.SQL(
                "select trade_date,accepted_focus_run_id,accepted_revision "
                "from {}.focus_trade_date_heads where source_authority_contract_id=%s "
                "and lineage_state='REPLAY_REQUIRED' and trade_date>=%s "
                "order by trade_date"
            ).format(schema), (SOURCE_AUTHORITY_CONTRACT, from_date))
        return tuple(ReplayItem(row[0], str(row[1]), int(row[2]))
                     for row in cur.fetchall())


def require_replay_clear(repository, *, before_trade_date: date | None = None) -> None:
    """Stop ordinary forward publication while an earlier chain is stale."""
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    schema = sql.Identifier(repository.schema)
    query = sql.SQL(
        "select trade_date from {}.focus_trade_date_heads "
        "where source_authority_contract_id=%s and lineage_state='REPLAY_REQUIRED'").format(schema)
    params: tuple[object, ...] = (SOURCE_AUTHORITY_CONTRACT,)
    if before_trade_date is not None:
        query += sql.SQL(" and trade_date<%s")
        params += (before_trade_date,)
    query += sql.SQL(" order by trade_date limit 1")
    with repository.connection.cursor() as cur:
        cur.execute(query, params)
        pending = cur.fetchone()
    if pending:
        raise ValueError("Focus replay required from " + pending[0].isoformat())
