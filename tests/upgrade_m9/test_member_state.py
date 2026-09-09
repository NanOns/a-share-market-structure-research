import pandas as pd
import pytest

from workbench_analysis.member_state import MemberStateError, build_membership_changes, build_sector_member_state_daily


def _inputs():
    technical = pd.DataFrame([
        {"security_id": "SH.1", "trade_date": "2026-09-07", "ret20": .20, "rps20": .90},
        {"security_id": "SH.2", "trade_date": "2026-09-07", "ret20": .10, "rps20": .90},
        {"security_id": "SH.1", "trade_date": "2026-09-08", "ret20": .40, "rps20": .90},
        {"security_id": "SH.3", "trade_date": "2026-09-08", "ret20": .30, "rps20": .95},
    ])
    memberships = pd.DataFrame([
        {"sector_id": "INDUSTRY:A", "security_id": "SH.1", "trade_date": "2026-09-07"},
        {"sector_id": "INDUSTRY:A", "security_id": "SH.2", "trade_date": "2026-09-07"},
        {"sector_id": "INDUSTRY:A", "security_id": "SH.1", "trade_date": "2026-09-08"},
        {"sector_id": "INDUSTRY:A", "security_id": "SH.3", "trade_date": "2026-09-08"},
    ])
    structures = pd.DataFrame([
        {"security_id": "SH.1", "trade_date": "2026-09-07", "hit": True},
        {"security_id": "SH.2", "trade_date": "2026-09-07", "hit": False},
        {"security_id": "SH.1", "trade_date": "2026-09-08", "hit": True},
        {"security_id": "SH.3", "trade_date": "2026-09-08", "hit": True},
    ])
    return technical, memberships, structures


def test_strong_state_uses_three_state_predicates_and_separates_membership_changes():
    technical, memberships, structures = _inputs()
    states = build_sector_member_state_daily(technical, memberships, structures=structures, cutoff="2026-09-08")
    first = states[(states.security_id == "SH.1") & (states.trade_date.astype(str) == "2026-09-07")].iloc[0]
    assert first.strong_state is True
    assert first.member_change_kind == "UNKNOWN"
    current = states[(states.security_id == "SH.1") & (states.trade_date.astype(str) == "2026-09-08")].iloc[0]
    assert current.member_change_kind == "RETAINED"
    added = states[(states.security_id == "SH.3") & (states.trade_date.astype(str) == "2026-09-08")].iloc[0]
    assert added.member_change_kind == "ADDED"
    changes = build_membership_changes(states)
    assert set(changes.change_type) == {"ADDED", "REMOVED"}


def test_unknown_is_not_false_and_future_duplicate_inputs_are_rejected():
    technical, memberships, structures = _inputs()
    unknown = build_sector_member_state_daily(technical.assign(rps20=None), memberships, structures=structures)
    assert unknown.strong_state.isna().all()
    with pytest.raises(MemberStateError, match="FUTURE_MEMBER_STATE_INPUT"):
        build_sector_member_state_daily(technical.assign(trade_date="2026-09-09"), memberships, cutoff="2026-09-08")
    duplicate = pd.concat([memberships, memberships.iloc[[0]]], ignore_index=True)
    with pytest.raises(MemberStateError, match="MEMBERSHIP_DUPLICATE_CONFLICT"):
        build_sector_member_state_daily(technical, duplicate, structures=structures)
