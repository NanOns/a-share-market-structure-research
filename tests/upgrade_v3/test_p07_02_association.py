import json
from pathlib import Path

import pandas as pd

from workbench_service.research_association import select_associations_and_shortlists


ROOT = Path(__file__).parents[2]
CONFIG = json.loads((ROOT / "config/research_attention_v3.yaml").read_text(encoding="utf-8"))


def _member(sector, security, ret1, setup=False, recovery=False):
    return {"sector_id": sector, "security_id": security, "ret1": ret1, "setup": setup, "recovery": recovery}


def _role(sector, security, role, rank=1):
    return {"sector_id": sector, "security_id": security, "role": role, "role_rank": rank, "role_reason_codes": ["ROLE_ELIGIBLE"]}


def test_primary_is_not_fixed_to_first_sector_and_loo_failure_keeps_alternative():
    members = pd.DataFrame([_member("A", f"A{n}", .01) for n in range(6)] + [_member("B", f"B{n}", .01) for n in range(6)] + [_member("A", "X", .02), _member("B", "X", .03)])
    roles = pd.DataFrame([_role("A", "X", "CURRENT_RESEARCH"), _role("B", "X", "CURRENT_RESEARCH", 2)])
    states = pd.DataFrame([{"sector_id": "A", "current": True, "current_rank": 1}, {"sector_id": "B", "current": True, "current_rank": 2}])
    associations, _ = select_associations_and_shortlists(members, roles, states, CONFIG)
    x = associations[associations.security_id.eq("X")]
    assert x.iloc[0].sector_id == "A"
    assert x.iloc[0].association_role == "PRIMARY"
    assert "LOO_SINGLE_OR_WEAK_SUPPORT" not in x.iloc[0].reason_codes
    assert len(x) == 2


def test_current_and_early_lists_are_independent_but_dual_hit_stays_out_of_early_focus():
    members = pd.DataFrame([_member("A", f"A{n}", .02, setup=True) for n in range(6)] + [_member("A", "X", .03, recovery=True)])
    roles = pd.DataFrame([_role("A", "X", "CURRENT_RESEARCH"), _role("A", "X", "EARLY_WATCH")])
    states = pd.DataFrame([{"sector_id": "A", "current": True, "potential_eligible": True, "current_rank": 1, "potential_rank": 1, "b_delta3": .1}])
    _, shortlist = select_associations_and_shortlists(members, roles, states, CONFIG)
    assert "X" in set(shortlist.loc[shortlist.list_type.eq("CURRENT_FOCUS"), "security_id"])
    assert "X" not in set(shortlist.loc[shortlist.list_type.eq("EARLY_FOCUS"), "security_id"])


def test_early_loo_requires_two_other_early_members_and_preserves_waiting_reason():
    members = pd.DataFrame([_member("P", "P0", .01, setup=True), _member("P", "P1", .01, setup=True), _member("P", "P2", .01), _member("P", "P3", .01), _member("P", "P4", .01), _member("P", "X", .01, recovery=True)])
    roles = pd.DataFrame([_role("P", "X", "EARLY_WATCH")])
    states = pd.DataFrame([{"sector_id": "P", "potential_eligible": True, "potential_rank": 1, "b_delta3": .06}])
    associations, shortlist = select_associations_and_shortlists(members, roles, states, CONFIG)
    assert bool(associations.iloc[0].loo_support) is True
    assert shortlist.iloc[0].waiting_for == "板块当前强势确认"
