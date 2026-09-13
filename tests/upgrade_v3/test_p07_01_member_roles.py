import json
from pathlib import Path

import pandas as pd

from workbench_analysis.sector_attention import build_sector_member_roles


ROOT = Path(__file__).parents[2]
CONFIG = json.loads((ROOT / "config/research_attention_v3.yaml").read_text(encoding="utf-8"))


def _member(sector, security, ret1, **updates):
    row = {
        "sector_id": sector, "security_id": security, "ret1": ret1,
        "amount_vs_prior20": 1.2, "rps5_delta3": .1, "bias20": .03,
        "extended": False, "structure_break": False, "position_complete": True,
        "liquidity20": True, "breakout": False, "recovery": False, "setup": False,
    }
    row.update(updates)
    return row


def test_today_leader_uses_same_day_rank_not_ret20_and_keeps_extended_fact():
    rows = [_member("A", f"S{index}", ret, ret20=ret20) for index, (ret, ret20) in enumerate([(0.04, .9), (.03, .1), (.02, .8), (.01, .7), (0.0, .99), (-.01, .95)])]
    rows[0]["extended"] = True
    rows[2]["breakout"] = True
    output = build_sector_member_roles(pd.DataFrame(rows), pd.DataFrame([{"sector_id": "A", "current": True, "potential_eligible": False}]), CONFIG)
    leaders = output[output.role.eq("TODAY_LEADER")]
    assert list(leaders.security_id) == ["S0", "S1"]
    assert "S0" in set(output.loc[output.role.eq("ALL_MEMBERS"), "security_id"])
    assert "S0" not in set(output.loc[output.role.eq("CURRENT_RESEARCH"), "security_id"])
    assert "S2" in set(output.loc[output.role.eq("CURRENT_RESEARCH"), "security_id"])


def test_early_watch_is_independent_and_does_not_fill_from_current_or_old_leader():
    rows = [_member("B", "B0", .01, setup=True), _member("B", "B1", .02, ret20=.99), _member("B", "B2", None)]
    output = build_sector_member_roles(pd.DataFrame(rows), pd.DataFrame([{"sector_id": "B", "current": False, "potential_eligible": True}]), CONFIG)
    early = output[output.role.eq("EARLY_WATCH")]
    assert list(early.security_id) == ["B0"]
    assert len(output[output.role.eq("ALL_MEMBERS")]) == 3
    assert len(output[output.role.eq("CURRENT_RESEARCH")]) == 0


def test_role_preview_cap_and_missing_quote_are_explainable():
    rows = [_member("C", f"C{index}", .02 - index / 1000, breakout=True) for index in range(8)]
    rows[-1]["ret1"] = None
    output = build_sector_member_roles(pd.DataFrame(rows), pd.DataFrame([{"sector_id": "C", "current": True, "potential_eligible": False}]), CONFIG)
    assert len(output[output.role.eq("CURRENT_RESEARCH")]) == 5
    missing = output[(output.role.eq("ALL_MEMBERS")) & (output.security_id.eq("C7"))].iloc[0]
    assert "QUOTE_UNKNOWN" in missing.role_reason_codes
