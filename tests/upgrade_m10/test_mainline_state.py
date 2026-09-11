from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from workbench_analysis.mainline import _window_metrics, apply_mainline_transitions, build_mainline_state_daily, classify_mainline_row


FORMAL_CONFIG = Path(__file__).parents[2] / "config/mainline-v2.4-preview.yaml"


def _cycle(percentiles, breadths=None, amounts=None, coverage=0.9):
    breadths = breadths or [0.6] * len(percentiles)
    amounts = amounts or [1.2] * len(percentiles)
    start = date(2026, 8, 1)
    def _delta(current, previous):
        return None if current is None or previous is None else current - previous

    breadth_change_1d = [None] + [_delta(breadths[index], breadths[index - 1]) for index in range(1, len(breadths))]
    breadth_change_3d = [None] * min(3, len(breadths)) + [_delta(breadths[index], breadths[index - 3]) for index in range(3, len(breadths))]
    return pd.DataFrame(
        {
            "sector_id": ["THEME:X"] * len(percentiles),
            "sector_name": ["示例概念"] * len(percentiles),
            "sector_type": ["THEME"] * len(percentiles),
            "trade_date": [start + timedelta(days=index) for index in range(len(percentiles))],
            "sector_rs20_pct": percentiles,
            "breadth_ret1": breadths,
            "breadth_ret1_common": breadths,
            "breadth_ret1_common_change_1d": breadth_change_1d,
            "breadth_ret1_common_change_3d": breadth_change_3d,
            "amount_vs_prior20": amounts,
            "coverage": [coverage] * len(percentiles),
        }
    )


def _members(dates, *, entered=False):
    rows = []
    for index, trade_date in enumerate(dates):
        rows.append(
            {
                "sector_id": "THEME:X",
                "security_id": "SH.1",
                "trade_date": trade_date,
                "strong_state": True if not entered or index == len(dates) - 1 else False,
                "member_change_kind": "ENTERED" if entered and index == len(dates) - 1 else "RETAINED",
            }
        )
        if entered:
            rows.append(
                {
                    "sector_id": "THEME:X",
                    "security_id": "SH.2",
                    "trade_date": trade_date,
                    "strong_state": True,
                    "member_change_kind": "RETAINED",
                }
            )
    return pd.DataFrame(rows)


def test_three_valid_days_enter_observation_pool_and_never_fading():
    result = classify_mainline_row(_cycle([0.95, 0.4, 0.3]))

    assert result["mainline_class"] == "OBSERVING"
    assert result["conflict_resolution"] == "FAST_HISTORY_NOT_REACHED"
    assert "sector_rs20_pct_5_observations" in result["missing_fields"]
    assert result["on_list_days"] == {"5": None, "10": None, "20": None, "30": None}


def test_window_counts_are_null_until_the_full_window_exists():
    short = _window_metrics([0.90, 0.90, 0.90], 0.80)[0]
    full_five = _window_metrics([0.90] * 5, 0.80)[0]

    assert short == {"5": None, "10": None, "20": None, "30": None}
    assert full_five["5"] == 5
    assert full_five["10"] is None
    assert full_five["20"] is None
    assert full_five["30"] is None


def test_fewer_than_three_valid_days_are_data_insufficient():
    result = classify_mainline_row(_cycle([0.95, None, 0.3]))

    assert result["mainline_class"] == "DATA_INSUFFICIENT"
    assert result["conflict_resolution"] == "OBSERVATION_HISTORY_NOT_REACHED"
    assert result["valid_observation_days"] == 2
    assert "sector_rs20_pct_3_observations" in result["missing_fields"]


def test_five_valid_days_can_enter_fast_observation_state():
    cycle = _cycle([0.4, 0.4, 0.4, 0.4, 0.85], breadths=[0.4, 0.4, 0.4, 0.4, 0.60], amounts=[1.0, 1.0, 1.0, 1.0, 1.20])
    result = classify_mainline_row(cycle, member_states=_members(cycle.trade_date, entered=True))

    assert result["mainline_class"] == "NEW"
    assert result["predicates"]["history_minimum_5_observations"] is True


def test_high_level_contraction_has_priority_when_strength_remains_high():
    percentiles = [0.85] * 21 + [0.95, 0.94, 0.84, 0.83]
    breadths = [0.6] * 22 + [0.55, 0.40, 0.35]
    result = classify_mainline_row(_cycle(percentiles, breadths), member_states=_members(_cycle(percentiles).trade_date))

    assert result["mainline_class"] == "HIGH_LEVEL_CONTRACTION"
    assert result["predicates"]["high_level_contraction"] is True


def test_fading_is_selected_when_a_previously_strong_sector_breaks_down():
    percentiles = [0.85] * 7 + [0.70, 0.55, 0.40]
    breadths = [0.60] * 9 + [0.30]
    amounts = [1.10] * 9 + [0.80]
    result = classify_mainline_row(_cycle(percentiles, breadths, amounts))

    assert result["mainline_class"] == "FADING"
    assert result["predicates"]["fading"] is True


def test_fading_does_not_treat_flat_breadth_or_amount_as_decline():
    percentiles = [0.85] * 7 + [0.70, 0.55, 0.40]
    result = classify_mainline_row(_cycle(percentiles, [0.60] * 10, [1.10] * 9 + [0.80]))

    assert result["breadth_change_3d"] == 0
    assert result["predicates"]["fading_breadth_declined"] is False
    assert result["mainline_class"] == "OBSERVING"


def test_coverage_unknown_is_data_insufficient_even_with_three_valid_days():
    result = classify_mainline_row(_cycle([0.40, 0.45, 0.50], coverage=None))

    assert result["valid_observation_days"] == 3
    assert result["mainline_class"] == "DATA_INSUFFICIENT"
    assert result["conflict_resolution"] == "BASE_INPUT_UNKNOWN"
    assert "coverage" in result["missing_fields"]


def test_reaccelerating_is_available_after_ten_valid_days():
    percentiles = [0.40] * 6 + [0.85, 0.85, 0.85, 0.95]
    breadths = [0.40] * 9 + [0.65]
    amounts = [1.00] * 9 + [1.20]
    result = classify_mainline_row(_cycle(percentiles, breadths, amounts), member_states=_members(_cycle(percentiles).trade_date))

    assert result["mainline_class"] == "REACCELERATING"
    assert result["predicates"]["reaccelerating"] is True


def test_new_counts_prior_high_percentiles_instead_of_boolean_identity():
    percentiles = [0.85, 0.85, 0.40, 0.40, 0.40, 0.85]
    breadths = [0.40] * 5 + [0.60]
    amounts = [1.00] * 5 + [1.20]
    cycle = _cycle(percentiles, breadths, amounts)
    result = classify_mainline_row(cycle, member_states=_members(cycle.trade_date, entered=True))

    assert result["predicates"]["new_prior_on_list_5_le_1"] is False
    assert result["predicates"]["new"] is False
    assert result["mainline_class"] == "BROADENING"


def test_fading_uses_only_the_available_recent_twenty_day_history():
    percentiles = [0.90] + [0.40] * 23 + [0.20]
    breadths = [0.60] * 24 + [0.30]
    amounts = [1.10] * 24 + [0.80]
    result = classify_mainline_row(_cycle(percentiles, breadths, amounts))

    assert result["predicates"]["fading_was_listed"] is False
    assert result["predicates"]["fading"] is False


def test_sustained_requires_stable_history_and_member_retention():
    percentiles = [0.40] * 5 + [0.85] * 5
    result = classify_mainline_row(_cycle(percentiles, [0.60] * 10, [1.10] * 10), member_states=_members(_cycle(percentiles).trade_date))

    assert result["mainline_class"] == "SUSTAINED"
    assert result["predicates"]["sustained"] is True


def test_retention_denominator_is_previous_strong_members_in_common_set():
    cycle = _cycle([0.40, 0.40])
    members = pd.DataFrame(
        [
            {"sector_id": "THEME:X", "security_id": "SH.1", "trade_date": cycle.trade_date.iloc[0], "member_present": True, "strong_state": True, "member_change_kind": "RETAINED"},
            {"sector_id": "THEME:X", "security_id": "SH.2", "trade_date": cycle.trade_date.iloc[0], "member_present": True, "strong_state": True, "member_change_kind": "RETAINED"},
            {"sector_id": "THEME:X", "security_id": "SH.1", "trade_date": cycle.trade_date.iloc[1], "member_present": True, "strong_state": True, "member_change_kind": "RETAINED"},
            {"sector_id": "THEME:X", "security_id": "SH.2", "trade_date": cycle.trade_date.iloc[1], "member_present": False, "strong_state": None, "member_change_kind": "REMOVED"},
        ]
    )

    result = classify_mainline_row(cycle, member_states=members)

    assert result["retention_rate"] == 1.0


def test_retention_uses_both_known_states_and_returns_null_for_zero_comparable_denominator():
    cycle = _cycle([0.40, 0.40])
    members = pd.DataFrame(
        [
            {"sector_id": "THEME:X", "security_id": "SH.1", "trade_date": cycle.trade_date.iloc[0], "strong_state": None, "member_change_kind": "RETAINED"},
            {"sector_id": "THEME:X", "security_id": "SH.1", "trade_date": cycle.trade_date.iloc[1], "strong_state": True, "member_change_kind": "UNKNOWN"},
        ]
    )

    result = classify_mainline_row(cycle, member_states=members)

    assert result["retention_rate"] is None


def test_mainline_breadth_uses_common_breadth_fields_not_all_member_breadth():
    cycle = _cycle([0.40, 0.40, 0.40, 0.75], breadths=[0.40, 0.40, 0.40, 0.40])
    cycle["breadth_ret1_common"] = [0.40, 0.40, 0.40, 0.60]
    cycle["breadth_ret1_common_change_1d"] = [None, 0.0, 0.0, 0.20]
    cycle["breadth_ret1_common_change_3d"] = [None, None, None, 0.20]

    result = classify_mainline_row(cycle)

    assert result["current_breadth"] == pytest.approx(0.60)
    assert result["breadth_change_3d"] == pytest.approx(0.20)
    assert result["predicates"]["broadening_breadth_improved"] is True


def test_broadening_is_selected_when_strength_and_width_expand():
    percentiles = [0.40] * 9 + [0.75]
    breadths = [0.40] * 9 + [0.55]
    result = classify_mainline_row(_cycle(percentiles, breadths), member_states=_members(_cycle(percentiles).trade_date, entered=True))

    assert result["mainline_class"] == "BROADENING"
    assert result["predicates"]["broadening"] is True


def test_new_mainline_precedes_broadening_when_all_new_conditions_pass():
    percentiles = [0.4] * 24 + [0.85]
    breadths = [0.4] * 24 + [0.60]
    amounts = [1.0] * 24 + [1.20]
    cycle = _cycle(percentiles, breadths, amounts)
    result = classify_mainline_row(cycle, member_states=_members(cycle.trade_date, entered=True))

    assert result["mainline_class"] == "NEW"
    assert result["predicates"]["new"] is True
    assert result["predicates"]["broadening"] is True


def test_unknown_higher_priority_blocks_a_lower_priority_class():
    percentiles = [0.40] * 9 + [0.85]
    breadths = [0.40] * 9 + [0.60]
    members = []
    dates = _cycle(percentiles).trade_date
    for index, trade_date in enumerate(dates):
        members.append(
            {
                "sector_id": "THEME:X",
                "security_id": "SH.1",
                "trade_date": trade_date,
                "strong_state": index == len(dates) - 1,
                "member_change_kind": "ENTERED" if index == len(dates) - 1 else "RETAINED",
            }
        )
    result = classify_mainline_row(_cycle(percentiles, breadths), member_states=pd.DataFrame(members))

    assert result["predicates"]["high_level_contraction"] is None
    assert result["predicates"]["new"] is True
    assert result["mainline_class"] == "DATA_INSUFFICIENT"
    assert result["conflict_resolution"] == "UNKNOWN_HIGHER_PRIORITY"


def test_unknown_predicate_is_not_treated_as_false():
    result = classify_mainline_row(_cycle([0.40] * 9 + [0.75], breadths=[None] * 10))

    assert result["predicates"]["broadening_breadth_improved"] is None
    assert result["mainline_class"] == "DATA_INSUFFICIENT"
    assert result["conflict_resolution"] == "UNKNOWN_HIGHER_PRIORITY"
    assert "breadth_ret1_comparison_3d" in result["missing_fields"]
    assert "member_change_counts" in result["missing_fields"]


def test_same_identity_produces_unchanged_or_class_transition():
    cycle = _cycle([0.40, 0.45, 0.50, 0.55])
    frame = build_mainline_state_daily(cycle)

    assert frame.iloc[0]["transition"] is None
    assert list(frame["transition"]) == [None, "UNCHANGED", "OBSERVING", "UNCHANGED"]


def test_contract_or_config_change_is_model_change():
    cycle = _cycle([0.40, 0.45, 0.50, 0.55])
    frame = build_mainline_state_daily(cycle)
    frame.loc[1, "config_hash"] = "changed-config"

    transitioned = apply_mainline_transitions(frame)

    assert transitioned.iloc[1]["transition"] == "MODEL_CHANGE"


def test_history_basis_change_is_not_a_market_transition():
    cycle = _cycle([0.40, 0.45, 0.50, 0.55])
    frame = build_mainline_state_daily(cycle)
    frame.loc[1, "history_basis"] = "OBSERVED"

    transitioned = apply_mainline_transitions(frame)

    assert transitioned.iloc[1]["transition"] == "BASIS_CHANGE"


def test_model_change_takes_precedence_when_contract_and_basis_both_change():
    cycle = _cycle([0.40, 0.45, 0.50, 0.55])
    frame = build_mainline_state_daily(cycle)
    frame.loc[1, "config_hash"] = "changed-config"
    frame.loc[1, "history_basis"] = "OBSERVED"

    transitioned = apply_mainline_transitions(frame)

    assert transitioned.iloc[1]["transition"] == "MODEL_CHANGE"


def test_new_publication_compares_current_cutoff_with_previous_snapshot():
    cycle = _cycle([0.40, 0.45, 0.50, 0.55])
    current = build_mainline_state_daily(cycle)
    previous = current.copy()
    previous.loc[previous.index[-1], "config_hash"] = "old-config"

    transitioned = apply_mainline_transitions(current, previous_frame=previous)

    assert transitioned.iloc[-1]["previous_class"] == previous.iloc[-1]["mainline_class"]
    assert transitioned.iloc[-1]["transition"] == "MODEL_CHANGE"


def test_formal_v24_uses_common_amount_a_delta_for_fading_not_legacy_proxy():
    percentiles = [0.85] * 7 + [0.70, 0.55, 0.40]
    cycle = _cycle(percentiles, [0.60] * 9 + [0.30], [9.0] * 10)
    cycle["sector_amount_vs_prior20"] = [1.20] * 9 + [1.10]
    cycle["sector_amount_ratio_delta_3sessions_common"] = [None] * 9 + [-0.20]

    result = classify_mainline_row(cycle, config=FORMAL_CONFIG)

    assert result["mainline_class"] == "FADING"
    assert result["current_amount_vs_prior20"] is None
    assert result["current_sector_amount_vs_prior20"] == pytest.approx(1.10)
    assert result["amount_change_3d"] == pytest.approx(-0.20)
    assert result["predicates"]["fading_amount_declined"] is True


def test_formal_v24_does_not_fallback_to_legacy_amount_proxy():
    cycle = _cycle([0.40] * 9 + [0.85], [0.40] * 9 + [0.60], [99.0] * 10)
    result = classify_mainline_row(cycle, config=FORMAL_CONFIG)

    assert result["current_sector_amount_vs_prior20"] is None
    assert result["current_amount_vs_prior20"] is None
    assert result["predicates"]["new_amount_ge_110"] is None
