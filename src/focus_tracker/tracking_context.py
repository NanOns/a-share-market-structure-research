"""Resolve current or frozen source context for every tracked Focus key."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from psycopg import sql

from .contracts import FocusKey, SOURCE_AUTHORITY_CONTRACT, source_item_digest
from .daily_plan import PlannedDay
from .source_reader import AcceptedSources, SourceRow


CONTRACT_ID = "FOCUS_EPISODE_TRACKING_CONTEXT_V2"


@dataclass(frozen=True)
class TrackingContext:
    key: FocusKey
    episode_id: str
    first_trade_date: date
    source_contract_id: str
    source_facts: dict[str, Any]
    today_source_row: SourceRow | None
    frozen_source_item_digest: str


def resolve_tracking_contexts(*, plan: PlannedDay,
                              sources: AcceptedSources,
                              first_source_rows: Mapping[str, SourceRow]) -> dict[tuple[FocusKey, str], TrackingContext]:
    """Join the union to today's rows or the exact accepted episode origin."""
    today = {row.key: row for row in sources.rows}
    if len(today) != len(sources.rows):
        raise ValueError("duplicate today source key")
    decisions = plan.episode_tracking or plan.decisions
    result: dict[tuple[FocusKey, str], TrackingContext] = {}
    for decision in decisions:
        key = decision.key
        if decision.episode_id is None:
            raise ValueError("tracked key lacks episode decision")
        # A reentered source row starts a new episode. It cannot become the
        # current source evidence for an older episode's follow-up.
        current = (None if decision.reason == "PENDING_EPISODE_FOLLOW_UP"
                   else today.get(key))
        frozen = first_source_rows.get(decision.episode_id)
        if decision.phase not in {"NEW", "REENTERED", "MODEL_BASELINE"} and frozen is None:
            raise ValueError("continuing episode lacks accepted first source")
        if current is None and frozen is None:
            raise ValueError("historical tracking source context unavailable")
        if frozen is not None and frozen.key != key:
            same_entity = (frozen.key.source_family == key.source_family and
                           frozen.key.entity_type == key.entity_type and
                           frozen.key.entity_id == key.entity_id)
            if not same_entity or decision.phase != "SOURCE_MODEL_BOUNDARY":
                raise ValueError("historical source identity differs from episode")
        row = current or frozen
        assert row is not None
        if current is not None and current.trade_date != plan.trade_date:
            raise ValueError("today source date mismatch")
        if source_item_digest(row.source_item_key, row.source_contract_id,
                              row.source_facts) != row.source_item_digest:
            raise ValueError("tracking source digest mismatch")
        first = frozen.trade_date if frozen is not None else plan.trade_date
        if first > plan.trade_date:
            raise ValueError("episode source date after tracking date")
        result[(key, decision.episode_id)] = TrackingContext(
            key, decision.episode_id, first, row.source_contract_id,
            row.source_facts, current,
            frozen.source_item_digest if frozen else row.source_item_digest)
    expected = {(item.key, item.episode_id) for item in decisions}
    if set(result) != expected:
        raise ValueError("tracking context set differs from episode union")
    return result


def read_first_source_rows(repository, *, episode_ids: set[str]) -> dict[str, SourceRow]:
    """Read exact FIRST_FOCUS rows only through valid accepted Focus heads."""
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    if not episode_ids:
        return {}
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL(
            "select e.episode_id,e.source_family,e.entity_type,e.entity_id,"
            "e.selection_contract_family,e.first_trade_date,d.source_membership_state,"
            "d.source_item_key,d.source_item_digest,d.source_contract_id,"
            "d.source_rank,d.source_focus_class,d.source_facts "
            "from {}.focus_episodes e "
            "join {}.focus_trade_date_heads h on h.trade_date=e.first_trade_date "
            "and h.source_authority_contract_id=%s and h.lineage_state='VALID' "
            "join {}.focus_daily_items d on d.focus_run_id=h.accepted_focus_run_id "
            "and d.source_family=e.source_family and d.entity_type=e.entity_type "
            "and d.entity_id=e.entity_id and d.selection_contract_family=e.selection_contract_family "
            "where e.episode_id=any(%s) order by e.episode_id"
        ).format(schema, schema, schema),
            (SOURCE_AUTHORITY_CONTRACT, sorted(episode_ids)))
        rows = cur.fetchall()
    result: dict[str, SourceRow] = {}
    for (episode, family, entity_type, entity_id, selection, first, membership,
         item_key, item_digest, contract, rank, focus_class, facts) in rows:
        episode = str(episode)
        if episode in result:
            raise ValueError("ambiguous accepted first source row")
        key = FocusKey(str(family), str(entity_type), str(entity_id), str(selection))
        row = SourceRow(key, first, str(membership), str(item_key), str(item_digest),
                        str(contract), rank, focus_class, facts)
        if source_item_digest(row.source_item_key, row.source_contract_id,
                              row.source_facts) != row.source_item_digest:
            raise ValueError("accepted first source digest mismatch")
        result[episode] = row
    if set(result) != episode_ids:
        raise ValueError("accepted first source rows incomplete")
    return result
