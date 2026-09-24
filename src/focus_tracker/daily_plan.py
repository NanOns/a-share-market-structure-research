"""FOCUS-02 deterministic daily tracking union before any publication."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping

from .contracts import FocusKey, digest
from .lifecycle import (Decision, EpisodeTrackingRef, Previous, plan_day,
                        tracking_union)
from .materialize import PathRequest
from .source_reader import AcceptedSources


CONTRACT_ID = "FOCUS_EPISODE_TRACKING_PLAN_V2"


@dataclass(frozen=True)
class PlannedDay:
    trade_date: date
    decisions: tuple[Decision, ...]
    tracking_keys: tuple[FocusKey, ...]
    stock_path_requests: tuple[PathRequest, ...]
    sector_ids: tuple[str, ...]
    plan_digest: str
    pending_followup_keys: tuple[FocusKey, ...] = ()
    due_outcome_keys: tuple[FocusKey, ...] = ()
    episode_tracking: tuple[Decision, ...] = ()


def _entity_identity(key: FocusKey) -> tuple[str, str, str]:
    return key.source_family, key.entity_type, key.entity_id


def require_tracking_coverage(*, tracking_keys: tuple[FocusKey, ...],
                              source_keys: set[FocusKey],
                              pending_followup: set[FocusKey],
                              due_outcomes: set[FocusKey]) -> None:
    """Require each source, follow-up and due entity in the tracked set.

    A source contract boundary can rekey one entity; episode overlap remains
    a separate audit item and must not be inferred from this entity gate.
    """
    if len(set(tracking_keys)) != len(tracking_keys):
        raise ValueError("duplicate tracking union key")
    covered = {_entity_identity(key) for key in tracking_keys}
    for name, required in (("source", source_keys),
                           ("pending follow-up", pending_followup),
                           ("due outcome", due_outcomes)):
        if not {_entity_identity(key) for key in required} <= covered:
            raise ValueError(name + " entity missing from tracking union")


def build_day_plan(*, sources: AcceptedSources,
                   previous: Mapping[FocusKey, Previous],
                   pending_followup: set[FocusKey],
                   due_outcomes: set[FocusKey],
                   required_episodes: tuple[EpisodeTrackingRef, ...] = ()) -> PlannedDay:
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
    require_tracking_coverage(tracking_keys=keys, source_keys=set(current),
                              pending_followup=pending_followup,
                              due_outcomes=due_outcomes)
    episode_decisions = list(decisions)
    episode_ids = {(item.key, item.episode_id) for item in decisions}
    required_by_identity = {}
    for ref in required_episodes:
        identity = (ref.key.source_family, ref.key.entity_type, ref.key.entity_id)
        decision = decisions_by_entity.get(identity)
        if decision is None:
            raise ValueError("required follow-up episode lacks current entity decision")
        if ref.first_trade_date > sources.trade_date:
            raise ValueError("required follow-up episode begins after tracking date")
        required_by_identity[(ref.key, ref.episode_id)] = ref
    for (key, episode), ref in sorted(
            required_by_identity.items(), key=lambda item: (item[0][0], item[0][1])):
        if (key, episode) in episode_ids:
            continue
        episode_decisions.append(Decision(
            key, "NONE", "POST_EXIT", episode, None, (), "PENDING_EPISODE_FOLLOW_UP"))
        episode_ids.add((key, episode))
    requests: set[PathRequest] = set()
    sectors: set[str] = set()
    ref_by_episode = {(ref.key, ref.episode_id): ref
                      for ref in required_by_identity.values()}
    for decision in episode_decisions:
        key = decision.key
        if key.entity_type == "SECTOR":
            sectors.add(key.entity_id)
            continue
        prior = next((old for old_key, old in previous.items()
                      if (old_key.source_family, old_key.entity_type, old_key.entity_id)
                      == (key.source_family, key.entity_type, key.entity_id)), None)
        ref = ref_by_episode.get((key, decision.episode_id))
        start = (ref.first_trade_date if ref else
                 prior.first_trade_date if prior and prior.episode_id == decision.episode_id
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
               "episode_tracking": [(item.key.source_family, item.key.entity_type,
                                     item.key.entity_id, item.episode_id,
                                     item.membership, item.phase, item.reason)
                                    for item in episode_decisions],
               "stock_paths": [(item.security_id, item.start_trade_date)
                               for item in stock_requests],
               "sectors": sorted(sectors)}
    return PlannedDay(sources.trade_date, decisions, keys, stock_requests,
                      tuple(sorted(sectors)), digest(payload),
                      tuple(sorted(pending_followup)), tuple(sorted(due_outcomes)),
                      tuple(episode_decisions))
