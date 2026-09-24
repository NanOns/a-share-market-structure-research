from datetime import date
from types import SimpleNamespace

from src.focus_tracker.frozen_invalidation_facts import derive_frozen_facts


def source(category, factor=None, recovery=None):
    return SimpleNamespace(
        key=SimpleNamespace(source_family="V3_3_TODAY_CANDIDATE"),
        source_item_digest="d" * 64, trade_date=date(2026, 9, 23),
        source_facts={"primary_category": category,
                      "factor_evidence": factor or {},
                      "scanner_evidence": {"recovery_turn": recovery or {}}})


def test_only_explicit_launch_threshold_is_frozen():
    facts = {f.key: f for f in derive_frozen_facts(
        source("LAUNCH_CONFIRM", {"phh20": 12.5, "ma20": 11}))}
    assert facts["frozen_phh20"].value == "12.5"
    assert facts["frozen_trend_key_low"].value is None
    assert facts["frozen_trend_key_low"].reason == "SOURCE_OPERAND_UNAVAILABLE"
    pg_fact = {f.key: f for f in derive_frozen_facts(
        source("LAUNCH_CONFIRM", {"phh20": {"$binary64": "4029000000000000"}}))}
    assert pg_fact["frozen_phh20"].value == "12.5"


def test_missing_threshold_does_not_fall_back_to_unrelated_low():
    facts = {f.key: f for f in derive_frozen_facts(
        source("STRONG_PULLBACK", {"ma20": 10, "phh20": 12}))}
    assert facts["frozen_pullback_invalid_low"].value is None


def test_recovery_ma_identity_requires_unique_true_branch():
    unique = {f.key: f for f in derive_frozen_facts(
        source("RECOVERY_TURN", recovery={"r5": True, "r20": False}))}
    ambiguous = {f.key: f for f in derive_frozen_facts(
        source("RECOVERY_TURN", recovery={"r5": True, "r20": True}))}
    assert unique["reclaimed_ma_kind"].value == "MA5"
    assert ambiguous["reclaimed_ma_kind"].value is None
