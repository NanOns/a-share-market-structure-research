import pandas as pd
import pytest

from workbench_analysis.representative_state import RepresentativeStateError, build_representative_state_daily


def _states(sequence):
    return pd.DataFrame([
        {"sector_id": "INDUSTRY:A", "security_id": security, "trade_date": f"2026-09-{7 + index:02d}", "member_present": True, "strong_state": True, "member_rank": rank, "ret20": 0.2 - rank / 100}
        for index, (security, rank) in enumerate(sequence)
    ])


def test_candidate_is_confirmed_on_second_consecutive_day():
    result = build_representative_state_daily(_states([("SH.A", 1), ("SH.B", 1), ("SH.B", 1)]))
    assert result.iloc[0].candidate_id == "SH.A"
    assert result.iloc[1].candidate_id == "SH.B"
    assert result.iloc[1].candidate_streak == 1
    assert result.iloc[2].confirmed_id == "SH.B"
    assert result.iloc[2].confirmation_event == "INITIAL_CONFIRMATION"


def test_a_b_a_does_not_confirm_b_and_missing_day_makes_confirmed_stale():
    frame = pd.concat([_states([("SH.A", 1)]), _states([("SH.A", 1)]).assign(trade_date="2026-09-08"), _states([("SH.B", 1)]).assign(trade_date="2026-09-09"), _states([("SH.A", 1)]).assign(trade_date="2026-09-10"), _states([("SH.A", 1)]).assign(trade_date="2026-09-11", member_present=False, strong_state=None)], ignore_index=True)
    result = build_representative_state_daily(frame)
    assert result.iloc[2].confirmed_id == "SH.A"
    assert result.iloc[2].candidate_id == "SH.B"
    assert result.iloc[3].confirmed_id == "SH.A"
    assert bool(result.iloc[4].stale) is True
    with pytest.raises(RepresentativeStateError, match="FUTURE_REPRESENTATIVE_INPUT"):
        build_representative_state_daily(frame, cutoff="2026-09-09")
