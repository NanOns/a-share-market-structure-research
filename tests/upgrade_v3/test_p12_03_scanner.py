from workbench_analysis.today_research_scanner_v3_3 import scan_today_research


def base():
    return dict(normal_universe=True, actual_bar=True, window_valid=True, liq20=True,
                input_identity_compatible=True, structure_break_v3=False, extended_v3=False,
                first_day_damage=False, severe_drop=False, breakout_v3=False,
                break_margin_close20=-.01, ret1_adj=.01, clv=.7, amr20_mean_prior=1.3,
                intraday_reject_high20=False, pullback_episode_confirmed=False,
                recovery_v3=False, reclaim_ma5=False, reclaim_ma20=False,
                prior5_below_ma20_count=0, ma20_nondeclining_3=True, rps5_delta3=.1,
                close_to_ma20=1, trend_background_v3=False, close_to_ma5=1,
                ma5_to_ma20=1, slope20=.01, rps20=.8, close_above_prior_high=True,
                current_with_loo_breadth_support=False, setup_v3=False, break_high20=False)


def test_launch_preserves_platform_type_and_independent_support():
    row = base() | {"breakout_v3": True, "break_margin_close20": .01, "break_high20": False}
    out = scan_today_research(row)
    assert out["launch"]["eligible"] is True
    assert out["launch"]["type"] == "CLOSE_PLATFORM_BREAK"


def test_known_failure_and_unknown_are_both_explained():
    row = base() | {"normal_universe": False, "clv": None}
    out = scan_today_research(row)["launch"]
    assert out["eligible"] is False
    assert "NORMAL_UNIVERSE" in out["known_failed_checks"]
    assert "CLV_GTE_060" in out["unknown_checks"]


def test_safety_unknown_never_admits_scenario():
    row = base() | {"breakout_v3": True, "break_margin_close20": .01, "severe_drop": None}
    out = scan_today_research(row)["launch"]
    assert out["eligible"] is None
    assert "NOT_SEVERE_DROP" in out["unknown_checks"]


def test_absolute_safety_vetoes_all_four_scenarios():
    row = base() | {"severe_drop": True, "breakout_v3": True, "break_margin_close20": .01,
                    "pullback_episode_confirmed": True, "recovery_v3": True,
                    "reclaim_ma5": True, "trend_background_v3": True,
                    "current_with_loo_breadth_support": True}
    out = scan_today_research(row)
    assert all(out[key]["eligible"] is False for key in
               ("launch", "pullback", "recovery_turn", "trend_continue"))


def test_recovery_r20_is_independent_of_legacy_recovery():
    row = base() | {"reclaim_ma20": True, "prior5_below_ma20_count": 2,
                    "recovery_v3": False, "reclaim_ma5": False}
    out = scan_today_research(row)["recovery_turn"]
    assert out["r5"] is False and out["r20"] is True and out["eligible"] is True


def test_continue_keeps_stock_only_shadow_but_requires_current_loo():
    row = base() | {"trend_background_v3": True, "current_with_loo_breadth_support": None}
    out = scan_today_research(row)
    assert out["trend_continue_stock_only"]["eligible"] is True
    assert out["trend_continue"]["eligible"] is None


def test_setup_watch_only_when_no_confirmed_scenario_and_lists_waiting():
    row = base() | {"setup_v3": True, "amr20_mean_prior": 1.1, "clv": .58}
    out = scan_today_research(row)
    assert out["setup_watch"]["eligible"] is True
    assert out["setup_watch"]["waiting_for"] == ["CLOSE_ABOVE_FROZEN_PHC20", "AMR20_GTE_120", "CLV_GTE_060"]
    row.update(breakout_v3=True, break_margin_close20=.01, amr20_mean_prior=1.3, clv=.7)
    assert scan_today_research(row)["setup_watch"]["eligible"] is False


def test_setup_watch_survives_unavailable_pullback_and_loo_as_observation_only():
    row = base() | {"setup_v3": True, "pullback_episode_confirmed": None,
                    "current_with_loo_breadth_support": None,
                    "amr20_mean_prior": 1.1, "clv": .58}
    out = scan_today_research(row)
    assert out["confirmed_any"] is None
    assert out["setup_watch"]["eligible"] is True


def test_one_price_bar_cannot_pass_launch_clv():
    row = base() | {"breakout_v3": True, "break_margin_close20": .01, "clv": None}
    assert scan_today_research(row)["launch"]["eligible"] is None


def test_legacy_signal_or_grade_cannot_bypass_common_and_safety_gates():
    row = base() | {"legacy_grade": "A+", "breakout_v3": True,
                    "break_margin_close20": .01, "normal_universe": False}
    out = scan_today_research(row)
    assert out["launch"]["eligible"] is False
    assert out["launch"]["type"] is None


def test_failed_launch_never_gets_platform_type_even_if_high_break_fact_true():
    row = base() | {"break_high20": True, "breakout_v3": False}
    assert scan_today_research(row)["launch"]["type"] is None
