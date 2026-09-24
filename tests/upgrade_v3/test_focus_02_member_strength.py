from decimal import Decimal

from src.focus_tracker.member_strength import SectorStrength, strength_retention
from src.focus_tracker.sector_basket import SectorBasket


def _strength(strong, evaluable, quality="READY"):
    return SectorStrength("sector", "snapshot", "result", "value", "member-contract",
                          10, len(evaluable), len(strong), Decimal("0.5"),
                          tuple(strong), tuple(evaluable), quality, "digest")


def _basket(members):
    return SectorBasket("sector", tuple(members), "BOUND_RELATION_REVISION",
                        "scope:1", "digest")


def test_retention_uses_previously_strong_members_only():
    members = tuple(str(i) for i in range(10))
    prior = _strength(("1", "2"), members)
    today = _strength(("2", "3"), members)
    assert strength_retention(previous=prior, current=today,
                              previous_basket=_basket(members),
                              current_basket=_basket(members)) == Decimal("0.5")


def test_retention_unknown_for_membership_drift_or_missing_strong_member():
    members = tuple(str(i) for i in range(10))
    prior = _strength(("1", "2"), members)
    drifted = ("1", "2", "3", "4", "5", "6", "7", "8", "x", "y")
    today = _strength(("2",), drifted)
    assert strength_retention(previous=prior, current=today,
                              previous_basket=_basket(members),
                              current_basket=_basket(drifted)) is None
    today = _strength(("2",), tuple(x for x in members if x != "1"))
    assert strength_retention(previous=prior, current=today,
                              previous_basket=_basket(members),
                              current_basket=_basket(members)) is None
