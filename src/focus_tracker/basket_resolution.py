"""Choose entry-frozen and contemporary sector baskets separately."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .basket_store import read_accepted_entry_basket
from .daily_plan import PlannedDay
from .sector_basket import SectorBasket


CONTRACT_ID = "FOCUS_BASKET_RESOLUTION_V1"
NEW_EPISODE_PHASES = frozenset({"NEW", "REENTERED", "MODEL_BASELINE"})


@dataclass(frozen=True)
class ResolvedBaskets:
    entry_frozen_by_episode: dict[str, SectorBasket]
    contemporary_by_sector: dict[str, SectorBasket]


def resolve_baskets(*, repository, plan: PlannedDay,
                    contemporary: Mapping[str, SectorBasket]) -> ResolvedBaskets:
    """An old episode keeps its first accepted basket across later revisions."""
    decisions = {(item.key.source_family, item.key.entity_type, item.key.entity_id): item
                 for item in plan.decisions}
    frozen: dict[str, SectorBasket] = {}
    current: dict[str, SectorBasket] = {}
    for key in plan.tracking_keys:
        if key.entity_type != "SECTOR":
            continue
        decision = decisions[(key.source_family, key.entity_type, key.entity_id)]
        if decision.episode_id is None:
            raise ValueError("tracked sector has no episode")
        if decision.phase in NEW_EPISODE_PHASES:
            basket = contemporary.get(key.entity_id)
            if basket is None:
                raise ValueError("new sector episode lacks entry basket")
        else:
            basket = read_accepted_entry_basket(repository, decision.episode_id)
        if basket.sector_id != key.entity_id:
            raise ValueError("frozen basket sector identity mismatch")
        old = frozen.get(decision.episode_id)
        if old is not None and old != basket:
            raise ValueError("conflicting entry baskets for one episode")
        frozen[decision.episode_id] = basket
        latest = contemporary.get(key.entity_id)
        if latest is not None:
            current[key.entity_id] = latest
    return ResolvedBaskets(frozen, current)
