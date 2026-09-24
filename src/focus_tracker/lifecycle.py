"""Deterministic FOCUS-00 membership and follow-up planning.

Invalidation and price path are orthogonal to these source transitions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping

from .contracts import FocusKey, SOURCE_MEMBERSHIPS, anchor_id, episode_id
from .contracts import digest
from .predicates import Tri


CAPABILITIES = frozenset({"COMPLETE", "UNAVAILABLE", "REVISED", "CONTRACT_BOUNDARY"})


@dataclass(frozen=True)
class Previous:
    key: FocusKey
    membership: str
    episode_id: str | None
    first_trade_date: date | None
    validity: str = "UNKNOWN"
    had_sector_support: bool = False

    def __post_init__(self) -> None:
        if self.membership not in SOURCE_MEMBERSHIPS[self.key.source_family] | {"NONE", "UNKNOWN"}:
            raise ValueError("previous membership does not match source")
        if bool(self.episode_id) != bool(self.first_trade_date):
            raise ValueError("previous episode identity incomplete")


@dataclass(frozen=True)
class EpisodeTrackingRef:
    """Exact episode that still requires a daily follow-up observation."""
    key: FocusKey
    episode_id: str
    first_trade_date: date

    def __post_init__(self) -> None:
        if not self.episode_id:
            raise ValueError("follow-up episode identity missing")


@dataclass(frozen=True)
class Decision:
    key: FocusKey
    membership: str
    phase: str
    episode_id: str | None
    parent_episode_id: str | None
    anchors: tuple[tuple[str, str], ...]
    reason: str


def tracking_union(today: set[FocusKey], pending_followup: set[FocusKey],
                   due_outcomes: set[FocusKey]) -> set[FocusKey]:
    """The shared fact materializer computes this union once per entity/date."""
    return today | pending_followup | due_outcomes


def segment_id(episode: str, segment_type: str, start_trade_date: date,
               source_model_contract_id: str, state_contract_id: str,
               source_revision: int = 1) -> str:
    if segment_type not in {"SOURCE_MODEL", "INTERPRETATION"}:
        raise ValueError("unknown focus segment type")
    if not episode or not source_model_contract_id or not state_contract_id or source_revision < 1:
        raise ValueError("incomplete focus segment identity")
    return "segment-" + digest({"contract": "FOCUS_MODEL_SEGMENT_V1",
                                "episode_id": episode, "segment_type": segment_type,
                                "start_trade_date": start_trade_date,
                                "source_model_contract_id": source_model_contract_id,
                                "state_contract_id": state_contract_id,
                                "source_revision": source_revision})[:32]


def source_attribute_transition(previous_scenario: str | None,
                                current_scenario: str | None) -> str | None:
    return "SCENARIO_CHANGED" if previous_scenario != current_scenario else None


def auxiliary_anchors(*, previous: Previous, trade_date: date,
                      invalidation: Tri, current_sector_support: bool | None) -> tuple[tuple[str, str], ...]:
    """Validity and support transitions do not change source membership."""
    if not previous.episode_id:
        raise ValueError("auxiliary anchor requires an existing episode")
    result = []
    if invalidation == Tri.TRUE and previous.validity != "INVALIDATED":
        result.append(("INVALIDATION", anchor_id(previous.episode_id, "INVALIDATION", trade_date)))
    if previous.key.entity_type == "STOCK" and not previous.had_sector_support and current_sector_support is True:
        result.append(("FIRST_SUPPORTED", anchor_id(previous.episode_id, "FIRST_SUPPORTED", trade_date)))
    return tuple(result)


def plan_day(*, trade_date: date, current: Mapping[FocusKey, str],
             previous: Mapping[FocusKey, Previous],
             capabilities: Mapping[str, str]) -> list[Decision]:
    """Plan a core day's source transitions from the prior accepted head.

    A missing current row means NONE only for a COMPLETE source family. It is
    UNKNOWN otherwise.  Old completed episodes may be supplied in ``previous``
    for reentry parent lookup; the caller decides the daily follow-up union.
    """
    for family, capability in capabilities.items():
        if family not in SOURCE_MEMBERSHIPS or capability not in CAPABILITIES:
            raise ValueError("invalid source capability")
    if set(SOURCE_MEMBERSHIPS) - set(capabilities):
        raise ValueError("all source family capabilities must be explicit")
    for key, membership in current.items():
        if membership not in SOURCE_MEMBERSHIPS[key.source_family]:
            raise ValueError("current membership does not match source")
        if capabilities[key.source_family] not in {"COMPLETE", "CONTRACT_BOUNDARY"}:
            raise ValueError("rows supplied for unavailable source")
    by_entity: dict[tuple[str, str, str], Previous] = {}
    for key, old in previous.items():
        if key != old.key:
            raise ValueError("previous key mismatch")
        identity = (key.source_family, key.entity_type, key.entity_id)
        if identity in by_entity:
            raise ValueError("duplicate prior source entity")
        by_entity[identity] = old
    today_by_entity: dict[tuple[str, str, str], tuple[FocusKey, str]] = {}
    for key, membership in current.items():
        identity = (key.source_family, key.entity_type, key.entity_id)
        if identity in today_by_entity:
            raise ValueError("duplicate current source entity")
        today_by_entity[identity] = (key, membership)
    decisions = []
    for identity in sorted(set(by_entity) | set(today_by_entity)):
        old = by_entity.get(identity)
        today = today_by_entity.get(identity)
        key = today[0] if today else old.key
        capability = capabilities[key.source_family]
        membership = today[1] if today else ("NONE" if capability == "COMPLETE" else "UNKNOWN")
        prior_membership = old.membership if old else "NONE"
        prior_episode = old.episode_id if old else None
        phase: str
        reason = "SOURCE_MEMBERSHIP"
        parent = None
        anchors: list[tuple[str, str]] = []
        eid = prior_episode
        if capability == "REVISED":
            phase, reason = "SOURCE_REVISED", "SOURCE_REVISION_NOT_ACCEPTED"
        elif capability == "UNAVAILABLE":
            phase, reason = "DATA_UNAVAILABLE", "SOURCE_UNAVAILABLE"
        elif capability == "CONTRACT_BOUNDARY" or (old and old.key.selection_contract_family != key.selection_contract_family):
            phase, reason = "SOURCE_MODEL_BOUNDARY", "SELECTION_CONTRACT_BOUNDARY"
            if today and (old is None or old.membership == "NONE"):
                eid = episode_id(key, trade_date)
                parent = prior_episode
                phase = "MODEL_BASELINE"
                anchors.append(("FIRST_FOCUS", anchor_id(eid, "FIRST_FOCUS", trade_date)))
            elif old and today is None:
                phase = "BOUNDARY_UNKNOWN"
        elif prior_membership == "UNKNOWN":
            phase, reason = "CONTINUITY_UNKNOWN", "PRIOR_MEMBERSHIP_UNKNOWN"
        elif prior_membership == "NONE" and membership != "NONE":
            phase = "REENTERED" if prior_episode else "NEW"
            parent = prior_episode
            eid = episode_id(key, trade_date)
            anchors.append(("FIRST_FOCUS", anchor_id(eid, "FIRST_FOCUS", trade_date)))
        elif prior_membership != "NONE" and membership == "NONE":
            phase = "EXITED"
            if not eid:
                raise ValueError("cannot exit without prior episode")
            anchors.append(("EXIT_EFFECTIVE", anchor_id(eid, "EXIT_EFFECTIVE", trade_date)))
        elif prior_membership == "EARLY" and membership == "CURRENT":
            phase = "UPGRADED"
            anchors.append(("CURRENT_UPGRADE", anchor_id(eid, "CURRENT_UPGRADE", trade_date)))
        elif prior_membership == "CURRENT" and membership == "EARLY":
            phase = "DOWNGRADED"
        elif prior_membership == "NONE" and membership == "NONE":
            phase = "POST_EXIT" if eid else "NONE"
        else:
            phase = "PERSISTENT"
        decisions.append(Decision(key, membership, phase, eid, parent,
                                  tuple(anchors), reason))
    return decisions
