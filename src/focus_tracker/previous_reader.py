"""Read the comparable preceding accepted Focus head, never a draft run."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from psycopg import sql

from .contracts import FocusKey, SOURCE_AUTHORITY_CONTRACT
from .lifecycle import Previous


CONTRACT_ID = "FOCUS_PREDECESSOR_HEAD_READER_V2"


@dataclass(frozen=True)
class PredecessorSnapshot:
    trade_date: date | None
    focus_run_id: str | None
    previous: dict[FocusKey, Previous]


def read_predecessor(repository, trade_date: date) -> PredecessorSnapshot:
    """Reject a replay-required predecessor and retain completed reentry parents."""
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL(
            "select trade_date,accepted_focus_run_id,lineage_state "
            "from {}.focus_trade_date_heads "
            "where trade_date<%s and source_authority_contract_id=%s "
            "order by trade_date desc limit 1").format(schema),
            (trade_date, SOURCE_AUTHORITY_CONTRACT))
        head = cur.fetchone()
        if head is None:
            return PredecessorSnapshot(None, None, {})
        previous_day, run_id, lineage = head
        if lineage != "VALID":
            raise ValueError("predecessor Focus head requires replay")
        cur.execute(sql.SQL(
            "select e.source_family,e.entity_type,e.entity_id,"
            "e.selection_contract_family,e.episode_id,e.first_trade_date,"
            "o.source_membership_state,o.validity_state,"
            "o.first_supported_anchor_id "
            "from {}.focus_episode_observations o "
            "join {}.focus_episodes e using(episode_id) "
            "where o.focus_run_id=%s and o.evaluation_mode='AS_RECORDED' "
            "order by e.source_family,e.entity_type,e.entity_id,"
            "(o.source_membership_state not in ('NONE','UNKNOWN')) desc,"
            "e.first_trade_date desc,e.episode_id desc").format(schema, schema),
            (run_id,))
        observations = cur.fetchall()
        cur.execute(sql.SQL(
            "select distinct on(source_family,entity_type,entity_id) "
            "e.source_family,e.entity_type,e.entity_id,e.selection_contract_family,"
            "e.episode_id,e.first_trade_date "
            "from {}.focus_episodes e "
            "join {}.focus_episode_observations o on o.episode_id=e.episode_id "
            "join {}.focus_trade_date_heads h on h.accepted_focus_run_id=o.focus_run_id "
            "where h.trade_date<=%s and h.source_authority_contract_id=%s "
            "and h.lineage_state='VALID' and o.evaluation_mode='AS_RECORDED' "
            "order by e.source_family,e.entity_type,e.entity_id,"
            "e.first_trade_date desc,e.episode_id desc"
        ).format(schema, schema, schema), (previous_day, SOURCE_AUTHORITY_CONTRACT))
        all_last_episodes = cur.fetchall()
    result: dict[FocusKey, Previous] = {}
    seen: set[tuple[str, str, str]] = set()
    for family, entity_type, entity_id, selection, episode, first, membership, validity, support in observations:
        identity = (str(family), str(entity_type), str(entity_id))
        # A reentry can leave older follow-up episodes beside the current
        # episode in the same accepted run. Lifecycle predecessor is the
        # active/latest episode; older episodes are loaded by the follow-up
        # episode query as independent tracking work.
        if identity in seen:
            continue
        seen.add(identity)
        key = FocusKey(*identity, str(selection))
        result[key] = Previous(key, str(membership), str(episode), first,
                               str(validity), support is not None)
    for family, entity_type, entity_id, selection, episode, first in all_last_episodes:
        identity = (str(family), str(entity_type), str(entity_id))
        if identity in seen:
            continue
        key = FocusKey(*identity, str(selection))
        result[key] = Previous(key, "NONE", str(episode), first)
    return PredecessorSnapshot(previous_day, str(run_id), result)
