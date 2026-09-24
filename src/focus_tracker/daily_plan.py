"""FOCUS-02 deterministic daily tracking union before any publication."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping

from .contracts import FocusKey, digest
from .lifecycle import Decision, Previous, plan_day, tracking_union
from .materialize import PathRequest
from .source_reader import AcceptedSources


CONTRACT_ID = "FOCUS_DAILY_TRACKING_PLAN_V1"


@dataclass(frozen=True)
class PlannedDay:
    trade_date: date
    decisions: tuple[Decision, ...]
    tracking_keys: tuple[FocusKey, ...]
    stock_path_requests: tuple[PathRequest, ...]
    sector_ids: tuple[str, ...]
    plan_digest: str


def build_day_plan(*, sources: AcceptedSources,
                   previous: Mapping[FocusKey, Previous],
                   pending_followup: set[FocusKey],
                   due_outcomes: set[FocusKey]) -> PlannedDay:
    current = {row.key: row.membership for row in sources.rows}
    if len(current) != len(sources.rows):
        raise ValueError("duplicate source key in accepted rows")
    if any(key not in previous and key not in current
           for key in pending_followup | due_outcomes):
        raise ValueError("pending entity lacks prior or current identity")
    decisions = tuple(plan_day(trade_date=sources.trade_date, current=current,
                               previous=previous, capabilities=sources.capabilities))
    decisions_by_entity = {(item.key.source_family, item.key.entity_type,
                            item.key.entity_id): item for item in decisions}
    union = tracking_union(set(current), pending_followup, due_outcomes)
    keys = tuple(sorted({decisions_by_entity[(key.source_family, key.entity_type,
                                             key.entity_id)].key for key in union}))
    requests: set[PathRequest] = set()
    sectors: set[str] = set()
    for key in keys:
        decision = decisions_by_entity.get((key.source_family, key.entity_type,
                                            key.entity_id))
        if decision is None:
            raise ValueError("tracking key has no lifecycle decision")
        if key.entity_type == "SECTOR":
            sectors.add(key.entity_id)
            continue
        prior = next((old for old_key, old in previous.items()
                      if (old_key.source_family, old_key.entity_type, old_key.entity_id)
                      == (key.source_family, key.entity_type, key.entity_id)), None)
        start = (prior.first_trade_date if prior and prior.episode_id == decision.episode_id
                 else sources.trade_date)
        if start is None or start > sources.trade_date:
            raise ValueError("invalid stock path anchor")
        requests.add(PathRequest(key.entity_id, start))
    stock_requests = tuple(sorted(requests))
    payload = {"contract": CONTRACT_ID, "trade_date": sources.trade_date,
               "source_identity_digest": sources.source_identity_digest,
               "previous": [(key.source_family, key.entity_type, key.entity_id,
                             old.membership, old.episode_id, old.first_trade_date)
                            for key, old in sorted(previous.items())],
               "pending_followup": [(key.source_family, key.entity_id)
                                    for key in sorted(pending_followup)],
               "due_outcomes": [(key.source_family, key.entity_id)
                                for key in sorted(due_outcomes)],
               "decisions": [(item.key.source_family, item.key.entity_id,
                              item.membership, item.phase, item.episode_id,
                              item.anchors) for item in decisions],
               "stock_paths": [(item.security_id, item.start_trade_date)
                               for item in stock_requests],
               "sectors": sorted(sectors)}
    return PlannedDay(sources.trade_date, decisions, keys, stock_requests,
                      tuple(sorted(sectors)), digest(payload))
