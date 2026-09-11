from datetime import date

import pandas as pd
import pytest

from workbench_analysis.sector_amount import (
    OBSERVED,
    RECONSTRUCTED,
    SectorAmountError,
    build_sector_amount_daily,
    plan_sector_amount_window,
)


def _calendar(size=24):
    return tuple(pd.date_range("2026-08-03", periods=size, freq="B").date)


def _members(calendar, ids=("SH.1", "SH.2", "SH.3", "SH.4", "SH.5"), *, sector="THEME:X"):
    return pd.DataFrame([
        {"sector_id": sector, "security_id": security_id, "trade_date": trade_date}
        for trade_date in calendar
        for security_id in ids
    ])


def _amounts(calendar, ids=("SH.1", "SH.2", "SH.3", "SH.4", "SH.5"), current=None, *, sector_date_index=None):
    current = current or {security_id: 100.0 for security_id in ids}
    rows = []
    current_index = len(calendar) - 1 if sector_date_index is None else sector_date_index
    for index, trade_date in enumerate(calendar[: current_index + 1]):
        for security_id in ids:
            rows.append({
                "security_id": security_id,
                "trade_date": trade_date,
                "raw_amount": current[security_id] if index == current_index else 100.0,
            })
    return pd.DataFrame(rows)


def test_plan_uses_master_calendar_positions_and_exact_24_session_union():
    calendar = _calendar(24)

    plan = plan_sector_amount_window(calendar, calendar[-1])

    assert plan.prior_dates == calendar[3:23]
    assert len(plan.history_dates) == 21
    assert plan.comparison_date == calendar[20]
    assert plan.comparison_union_dates == calendar


def test_formal_a_is_common_member_aggregate_not_member_median():
    calendar = _calendar(21)
    ids = ("SH.1", "SH.2", "SH.3", "SH.4", "SH.5")
    amounts = _amounts(calendar, ids, current={ids[0]: 500.0, **{security_id: 100.0 for security_id in ids[1:]}})
    result = build_sector_amount_daily(amounts, _members(calendar, ids), calendar)
    row = result[result.trade_date == calendar[-1]].iloc[0]

    assert row.sector_amount_vs_prior20 == pytest.approx(1.8)
    assert row.sector_amount_comparable_sum == pytest.approx(900.0)
    assert row.sector_amount_prior20_mean == pytest.approx(500.0)
    assert row.amount_comparable_member_count == 5
    assert row.amount_comparable_coverage == pytest.approx(1.0)
    assert row.amount_quality_codes == []


def test_three_members_are_not_formal_even_when_the_ratio_is_calculable():
    calendar = _calendar(21)
    ids = ("SH.1", "SH.2", "SH.3")
    result = build_sector_amount_daily(
        _amounts(calendar, ids, current={"SH.1": 300.0, "SH.2": 100.0, "SH.3": 100.0}),
        _members(calendar, ids),
        calendar,
    )
    row = result[result.trade_date == calendar[-1]].iloc[0]

    assert row.sector_amount_vs_prior20 is None
    assert "LOW_MEMBER_COUNT" in row.amount_quality_codes
    assert row.member_amount_sum == pytest.approx(500.0)


def test_observed_new_member_is_excluded_from_common_formal_a_but_stays_in_target_denominator():
    calendar = _calendar(21)
    old_ids = ("SH.1", "SH.2", "SH.3", "SH.4", "SH.5")
    new_id = "SH.6"
    memberships = _members(calendar[:-1], old_ids)
    memberships = pd.concat([
        memberships,
        _members((calendar[-1],), old_ids + (new_id,)),
    ], ignore_index=True)
    amounts = _amounts(calendar, old_ids + (new_id,), current={security_id: 100.0 for security_id in old_ids + (new_id,)})
    row = build_sector_amount_daily(amounts, memberships, calendar).iloc[-1]

    assert row.member_amount_sum == pytest.approx(600.0)
    assert row.sector_amount_comparable_sum == pytest.approx(500.0)
    assert row.sector_amount_vs_prior20 == pytest.approx(1.0)
    assert row.amount_target_member_count == 6
    assert row.amount_comparable_member_count == 5
    assert row.amount_excluded_member_ids == [new_id]


def test_missing_amount_in_fixed_calendar_window_is_not_replaced_by_an_earlier_observation():
    calendar = _calendar(22)
    ids = ("SH.1", "SH.2", "SH.3", "SH.4", "SH.5")
    amounts = _amounts(calendar, ids, sector_date_index=21)
    missing_date = calendar[10]
    amounts = amounts[amounts.trade_date != missing_date]
    result = build_sector_amount_daily(amounts, _members(calendar, ids), calendar)
    row = result[result.trade_date == calendar[-1]].iloc[0]

    assert row.sector_amount_vs_prior20 is None
    assert "INVALID_AMOUNT" in row.amount_quality_codes
    assert row.amount_window_start == calendar[1]


def test_confirmed_zero_numerator_is_valid_zero_but_unknown_zero_is_not_filled():
    calendar = _calendar(21)
    ids = ("SH.1", "SH.2", "SH.3", "SH.4", "SH.5")
    amounts = _amounts(calendar, ids, current={security_id: 0.0 for security_id in ids})
    amounts["amount_status"] = "CONFIRMED_ZERO"
    row = build_sector_amount_daily(amounts, _members(calendar, ids), calendar).iloc[-1]
    assert row.sector_amount_vs_prior20 == pytest.approx(0.0)
    assert row.amount_quality_codes == []

    unknown = amounts.copy()
    unknown["amount_status"] = None
    row = build_sector_amount_daily(unknown, _members(calendar, ids), calendar).iloc[-1]
    assert row.sector_amount_vs_prior20 is None
    assert "INVALID_AMOUNT" in row.amount_quality_codes


def test_comparison_delta_uses_fixed_common_members_over_24_sessions():
    calendar = _calendar(24)
    ids = ("SH.1", "SH.2", "SH.3", "SH.4", "SH.5")
    current = {ids[0]: 500.0, **{security_id: 100.0 for security_id in ids[1:]}}
    row = build_sector_amount_daily(_amounts(calendar, ids, current=current), _members(calendar, ids), calendar).iloc[-1]

    assert row.amount_comparison_date == calendar[-4]
    assert row.amount_comparison_quality_codes == []
    assert row.amount_comparison_current_a == pytest.approx(1.8)
    assert row.amount_comparison_prior_a == pytest.approx(1.0)
    assert row.sector_amount_ratio_delta_3sessions_common == pytest.approx(0.8)
    assert row.amount_comparison_current_coverage == pytest.approx(1.0)
    assert row.amount_comparison_window_coverage == pytest.approx(1.0)
    assert row.amount_comparison_evidence["comparison_date"] == calendar[-4]


def test_reconstructed_uses_one_fixed_snapshot_for_all_h21_dates():
    calendar = _calendar(21)
    ids = ("SH.1", "SH.2", "SH.3", "SH.4", "SH.5")
    snapshot = pd.DataFrame([{"sector_id": "THEME:X", "security_id": security_id} for security_id in ids])
    amounts = _amounts(calendar, ids, current={ids[0]: 500.0, **{security_id: 100.0 for security_id in ids[1:]}})
    result = build_sector_amount_daily(
        amounts,
        memberships=pd.DataFrame(columns=["sector_id", "security_id"]),
        calendar=calendar,
        mode=RECONSTRUCTED,
        membership_snapshot=snapshot,
    )
    row = result[result.trade_date == calendar[-1]].iloc[0]

    assert row.amount_basis == "RECONSTRUCTED_FIXED_SNAPSHOT_COMMON_MEMBER_AGGREGATE"
    assert row.sector_amount_vs_prior20 == pytest.approx(1.8)


def test_reconstructed_target_path_preserves_formula_and_snapshot_identity():
    calendar = _calendar(24)
    ids = ("SH.1", "SH.2", "SH.3", "SH.4", "SH.5")
    snapshot = pd.DataFrame([{"sector_id": "THEME:X", "security_id": security_id} for security_id in ids])
    amounts = _amounts(calendar, ids, current={ids[0]: 500.0, **{security_id: 100.0 for security_id in ids[1:]}})

    result = build_sector_amount_daily(
        amounts,
        memberships=pd.DataFrame(columns=["sector_id", "security_id"]),
        calendar=calendar,
        mode=RECONSTRUCTED,
        membership_snapshot=snapshot,
        membership_snapshot_id="snapshot-v1",
        target_dates=[calendar[-1]],
    )
    row = result.iloc[0]

    assert row.sector_amount_vs_prior20 == pytest.approx(1.8)
    assert row.amount_membership_snapshot_id == "snapshot-v1"
    assert row.amount_comparison_evidence["membership_snapshot_id"] == "snapshot-v1"


def test_quality_gates_keep_current_and_window_denominators_separate():
    calendar = _calendar(21)
    ids = ("SH.1", "SH.2", "SH.3", "SH.4", "SH.5", "SH.6", "SH.7")
    memberships = _members(calendar, ids)
    amounts = _amounts(calendar, ids[:5], current={security_id: 100.0 for security_id in ids[:5]})
    row = build_sector_amount_daily(amounts, memberships, calendar).iloc[-1]

    assert row.amount_target_member_count == 7
    assert row.amount_comparable_member_count == 5
    assert row.amount_comparable_coverage == pytest.approx(5 / 7)
    assert row.amount_window_coverage == pytest.approx(5 / 7)
    assert "LOW_COVERAGE" in row.amount_quality_codes


def test_structural_calendar_and_duplicate_inputs_are_rejected():
    calendar = _calendar(21)
    ids = ("SH.1", "SH.2", "SH.3", "SH.4", "SH.5")
    amounts = _amounts(calendar, ids)
    with pytest.raises(SectorAmountError, match="NO_CALENDAR:UNSORTED_OR_DUPLICATE"):
        plan_sector_amount_window((calendar[1], calendar[0]), calendar[0])
    with pytest.raises(SectorAmountError, match="AMOUNT_DUPLICATE_SECURITY_DATE"):
        build_sector_amount_daily(pd.concat([amounts, amounts.iloc[[0]]]), _members(calendar, ids), calendar)
