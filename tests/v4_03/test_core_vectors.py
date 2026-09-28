import pytest

from src.v4.factors.core import Bar, Observation, compute_core, market_reference, rps_midrank
from src.v4.factors.native import historical_market_path, market_axis_primitives, market_trend_axis, sector_native
from src.v4.factors.relative import relative_factors


def rows(n=100, *, suspension=(), gap=(), flat=False):
    out = []
    for i in range(n):
        date = f"2026-01-{i:03d}"
        state = "CONFIRMED_SUSPENSION" if i in suspension else "UNKNOWN" if i in gap else "ACTUAL"
        close = 10.0 if flat else 10.0 + i * 0.1
        bar = Bar(close, close + (0 if flat else 1), close - (0 if flat else 1), close,
                  100.0 + i, 1000.0 + i, "QFQ_R1", f"source-{i}") if state == "ACTUAL" else None
        out.append(Observation(date, state, bar))
    return out


def test_core_exact_windows_and_ddof_zero():
    out = compute_core(rows(), "SH_600000")
    assert out["ma20"].value == sum(10 + i * .1 for i in range(80, 100)) / 20
    assert out["ret5"].value == (10 + 99 * .1) / (10 + 94 * .1) - 1
    assert out["vol20"].quality_state == "OBSERVED"
    assert out["atr20"].value == 2.0
    assert out["prior_high20"].value < out["hhv20"].value
    assert out["amount_ratio5"].value == 199 / 196
    assert out["slope20"].quality_state == "OBSERVED"
    assert out["pos60"].window_start_trade_date == out["hhv60"].window_start_trade_date
    assert out["pos60"].window_end_trade_date == out["hhv60"].window_end_trade_date
    assert out["amount_ratio5"].actual_count == 6


def test_suspension_crosses_technical_but_blocks_vol():
    out = compute_core(rows(suspension=(96,)), "SH_600000")
    assert out["ma5"].quality_state == "OBSERVED"
    assert out["ma5"].suspended_count == 1
    assert out["ret5"].quality_state == "OBSERVED"
    assert out["vol5"].quality_state == "UNKNOWN"
    prior_day = compute_core(rows(suspension=(98,)), "SH_600000")
    assert prior_day["amount_ratio5"].quality_state == "OBSERVED"
    assert prior_day["amount_ratio5"].suspended_count == 1


def test_endpoint_and_unexplained_gap_fail_closed():
    suspended = compute_core(rows(suspension=(99,)), "SH_600000")
    assert suspended["ma5"].quality_state == "OBSERVED"
    assert suspended["ret5"].quality_state == "UNKNOWN"
    gap = compute_core(rows(gap=(96,)), "SH_600000")
    assert gap["ma5"].unknown_reason == "UNEXPLAINED_DATA_GAP"
    assert gap["ret5"].unknown_reason == "UNEXPLAINED_DATA_GAP"
    adjustment = rows()
    adjustment[-1] = Observation(adjustment[-1].trade_date, "ADJUSTMENT_UNKNOWN")
    assert compute_core(adjustment, "SH_600000")["ma5"].unknown_reason == "ADJUSTMENT_UNKNOWN"
    assert compute_core(adjustment, "SH_600000")["ret5"].unknown_reason == "ADJUSTMENT_UNKNOWN"


def test_short_history_zero_denominator_and_coordinate():
    short = compute_core(rows(19), "SH_600000")
    assert short["ma20"].quality_state == "UNKNOWN"
    flat = compute_core(rows(flat=True), "SH_600000")
    assert flat["clv"].unknown_reason == "ZERO_DENOMINATOR"
    assert flat["range_ratio"].unknown_reason == "ZERO_DENOMINATOR"
    mixed = rows()
    b = mixed[-1].bar
    mixed[-1] = Observation(mixed[-1].trade_date, "ACTUAL", Bar(b.open, b.high, b.low, b.close,
                         b.amount, b.volume, "QFQ_R2", b.source_digest))
    assert compute_core(mixed, "SH_600000")["ma20"].unknown_reason == "MIXED_ADJUSTMENT_IDENTITY"


def test_five_session_suspension_and_zero_amount_volume_denominators():
    long_pause = compute_core(rows(suspension=tuple(range(90, 95))), "SH_600000")
    assert long_pause["ma20"].quality_state == "OBSERVED"
    assert long_pause["ma20"].suspended_count == 5
    assert long_pause["vol20"].quality_state == "UNKNOWN"
    zero = rows()
    for i in range(94, 99):
        b = zero[i].bar
        zero[i] = Observation(zero[i].trade_date, "ACTUAL", Bar(b.open, b.high, b.low, b.close,
                              0.0, 0.0, b.adjustment_basis_id, b.source_digest))
    values = compute_core(zero, "SH_600000")
    assert values["amount_ratio5"].unknown_reason == "ZERO_DENOMINATOR"
    assert values["volume_ratio5"].unknown_reason == "ZERO_DENOMINATOR"


def test_prior_extrema_and_technical_windows_at_suspended_asof():
    data = rows(suspension=(99,))
    result = compute_core(data, "SH_600000")
    assert result["prior_high20"].quality_state == "OBSERVED"
    assert result["prior_low20"].quality_state == "OBSERVED"
    assert result["prior_high20"].window_end_trade_date == data[-2].trade_date
    assert result["ma20"].quality_state == "OBSERVED"
    assert result["ma20"].suspended_count == 1
    assert result["amount_ratio20"].unknown_reason == "CURRENT_BAR_UNAVAILABLE"
    assert result["ret5"].unknown_reason == "MISSING_OR_SUSPENDED_ENDPOINT"
    assert result["pos60"].unknown_reason == "CURRENT_BAR_UNAVAILABLE"
    assert result["clv"].unknown_reason == "CURRENT_BAR_UNAVAILABLE"


def test_nonpositive_price_invalidates_required_window():
    bad = rows()
    b = bad[-2].bar
    bad[-2] = Observation(bad[-2].trade_date, "ACTUAL", Bar(b.open, b.high, b.low, 0.0,
                          b.amount, b.volume, b.adjustment_basis_id, b.source_digest))
    result = compute_core(bad, "SH_600000")
    assert result["ma5"].unknown_reason == "INVALID_PRICE"
    assert result["vol5"].unknown_reason == "INVALID_PRICE"


def test_rps_and_market_reference_boundaries():
    assert rps_midrank({"a": 1}, ["a"])[0]["a"] is None
    assert rps_midrank({"a": 1, "b": 2}, ["b", "a"])[0] == {"a": 0, "b": 100}
    assert set(rps_midrank({"a": 1, "b": 1, "c": 1}, ["a", "b", "c"])[0].values()) == {50}
    assert rps_midrank({"a": 1, "b": 1, "c": 2}, ["a", "b", "c"])[0]["a"] == 25
    scores, coverage = rps_midrank({"a": 1, "b": 2, "c": None}, ["a", "b", "c"])
    assert scores["c"] is None
    assert coverage["universe_count"] == 3 and coverage["evaluable_count"] == 2
    assert market_reference({"a": 1, "b": None, "c": 3, "d": 5, "e": 7}, list("abcde"))[0] == 4
    assert market_reference({"a": 1, "b": None, "c": None, "d": 5, "e": 7}, list("abcde"))[0] is None


def test_native_boundaries():
    source = "a" * 64
    assert historical_market_path([("a", .1), ("b", .2)], start_sessions=["0", "a"],
                                  start_universe_snapshot_ids=["U0", "Ua"],
                                  market_calendar_id="CAL-1", input_source_digest=source)[-1]["level"] == 1.32
    primitive = sector_native(["b", "a", "a"], {"a": {"quote_quality_state": "OBSERVED",
                              "ret1_quality_state": "OBSERVED", "ret1": 1,
                              "amount_quality_state": "UNKNOWN", "amount": None,
                              "ma20_quality_state": "OBSERVED", "above_ma20": True}},
                              trade_date="2026-09-24", market_calendar_id="CAL-1",
                              sector_membership_snapshot_id="SECTOR-U-1", adjustment_basis_id="QFQ-SET-1",
                              input_source_digest=source)
    assert primitive["member_count"] == 2
    assert primitive["positive_breadth_denominator"] == 1
    assert primitive["ma20_width_denominator"] == 1
    assert primitive["amount_evaluable_count"] == 0
    assert primitive["publication_permission"] == "NOT_V4_08_SECTOR_FACTORS"
    second = sector_native(["a"], {"a": {"quote_quality_state": "UNKNOWN",
                              "ret1_quality_state": "OBSERVED", "ret1": -1,
                              "amount_quality_state": "OBSERVED", "amount": 50,
                              "ma20_quality_state": "UNKNOWN", "above_ma20": None}},
                              trade_date="2026-09-24", market_calendar_id="CAL-1",
                              sector_membership_snapshot_id="SECTOR-U-2", adjustment_basis_id="QFQ-SET-1",
                              input_source_digest="b" * 64)
    assert second["raw_quote_coverage"] == 0
    assert second["positive_breadth_denominator"] == 1
    assert second["ma20_width_denominator"] == 0
    assert second["amount_median_primitive"] == 50
    assert primitive["output_digest"] != second["output_digest"]
    assert second["field_quality"]["amount_median_primitive"]["quality_state"] == "OBSERVED"
    assert second["downstream_scope"]["sector_ranking_permitted"] is False
    reordered = sector_native(["a", "b"], {"a": {"quote_quality_state": "OBSERVED",
                               "ret1_quality_state": "OBSERVED", "ret1": 1,
                               "amount_quality_state": "UNKNOWN", "amount": None,
                               "ma20_quality_state": "OBSERVED", "above_ma20": True}},
                               trade_date="2026-09-24", market_calendar_id="CAL-1",
                               sector_membership_snapshot_id="SECTOR-U-1", adjustment_basis_id="QFQ-SET-1",
                               input_source_digest=source)
    assert reordered["input_digest"] == primitive["input_digest"]
    assert reordered["output_digest"] == primitive["output_digest"]
    with pytest.raises(ValueError, match="complete time/source/PIT identity"):
        sector_native(["a"], {}, trade_date="2026-09-24", market_calendar_id="CAL-1",
                      sector_membership_snapshot_id="", adjustment_basis_id="QFQ", input_source_digest=source)


def test_market_axis_exact_thresholds_and_conflict():
    identity = {"trade_date": "2026-09-24", "market_calendar_id": "CAL-1", "market_snapshot_id": "M-1",
                "adjustment_basis_id": "QFQ-MKT-1", "input_source_digest": "c" * 64}
    at = market_axis_primitives(breadth=.05, participation=1.2,
                                limit_coverage=.8, stress_ratio=.05, prior_stress_ratio=.05, **identity)
    assert at["breadth_axis"] == "STABLE"
    assert at["participation_axis"] == "EXPANDING"
    assert at["stress_level"] == "HIGH"
    assert at["stress_change"] == "STABLE"
    assert at["trend_axis"] == "PRODUCED_BY_MARKET_REGIME_TREND_WEAK_ERRATUM_V1"
    below = market_axis_primitives(breadth=-.050001, participation=.79999,
                                   limit_coverage=.79999, stress_ratio=.01, prior_stress_ratio=.02, **identity)
    assert below["breadth_axis"] == "DETERIORATING"
    assert below["participation_axis"] == "THIN"
    assert below["stress_level"] is None
    assert below["stress_change"] == "DECLINING"
    nonfinite = market_axis_primitives(breadth=float("nan"), participation=None,
                                       limit_coverage=.9, stress_ratio=float("inf"),
                                       prior_stress_ratio=.01, **identity)
    assert nonfinite["breadth_axis"] is None
    assert nonfinite["stress_level"] is None
    assert nonfinite["field_quality"]["breadth_axis"]["quality_state"] == "UNKNOWN"


def test_market_trend_weak_erratum_and_mixed_neutral_states():
    identity = {"trade_date": "2026-09-24", "market_calendar_id": "CAL-1", "market_snapshot_id": "M-1",
                "adjustment_basis_id": "QFQ-MKT-1", "input_source_digest": "d" * 64}
    assert market_trend_axis(index_close=12, index_ma20=11, index_ma20_t_minus_5=10, **identity)["trend_axis"] == "STRONG"
    assert market_trend_axis(index_close=9, index_ma20=10, index_ma20_t_minus_5=11, **identity)["trend_axis"] == "WEAK"
    assert market_trend_axis(index_close=9, index_ma20=10, index_ma20_t_minus_5=9, **identity)["trend_axis"] == "NEUTRAL"
    assert market_trend_axis(index_close=10, index_ma20=10, index_ma20_t_minus_5=11, **identity)["trend_axis"] == "NEUTRAL"
    unknown = market_trend_axis(index_close=10, index_ma20=None, index_ma20_t_minus_5=9, **identity)
    assert unknown["trend_axis"] == "UNKNOWN"
    assert unknown["quality_state"] == "UNKNOWN"


def test_relative_factors_keep_rps_and_reference_separate():
    returns = {1: {"a": .1, "b": .2}, 3: {"a": .3, "b": .5},
               5: {"a": .4, "b": .6}, 20: {"a": .1, "b": .1}}
    previous = {1: {"rps5": {"a": 10, "b": 90}},
                3: {"rps5": {"a": 20, "b": 80}, "rps20": {"a": 40, "b": 60}}}
    values, refs = relative_factors(current_returns=returns, historical_rps=previous,
                                    asof_universe=["b", "a"],
                                    start_universes={1: ["a", "b"], 3: ["a", "b"], 5: ["a", "b"]},
                                    asof_trade_date="2026-09-24",
                                    session_dates={"2026-09-24": {1: "2026-09-23", 3: "2026-09-21", 5: "2026-09-17", 20: "2026-08-27", -1: "2026-09-23", -3: "2026-09-21"}},
                                    market_calendar_id="SSE_2026_V1", universe_snapshot_id="U-T",
                                    start_universe_snapshot_ids={1: "U-T1", 3: "U-T3", 5: "U-T5"},
                                    adjustment_basis_id="QFQ-R1", input_source_digest="a" * 64,
                                    prior_rps_artifact_digests={1: {"rps5": "b" * 64},
                                                                3: {"rps5": "c" * 64, "rps20": "d" * 64}},
                                    prior_rps_universe_snapshot_ids={1: {"rps5": "U-T1"},
                                                                     3: {"rps5": "U-T3", "rps20": "U-T3"}})
    assert values["a"]["rps5"].value == 0
    assert values["a"]["rps20"].value == 50
    assert values["a"]["rps5_delta1"].value == -10
    assert values["a"]["rps5"].quality_state == "OBSERVED"
    assert values["a"]["rps5"].universe_snapshot_id == "U-T"
    assert values["a"]["rps5"].input_digest
    assert values["a"]["rps5"].start_universe_snapshot_id == "U-T"
    assert values["a"]["rps5_delta1"].start_universe_snapshot_id == "U-T1"
    assert values["a"]["rel_market_1"].value == pytest.approx(-.05)
    assert refs[1]["reference_return"] == pytest.approx(.15)
    assert refs[1]["path_identity"] == "HISTORICAL_ENDPOINT_EQUAL_WEIGHT_REFERENCE"


def test_temporal_prefix_and_cross_section_order_determinism():
    history = rows(110)
    prefix = compute_core(history[:100], "SH_600000")
    full_at_t = compute_core(history, "SH_600000", asof=history[99].trade_date)
    for field in prefix:
        assert prefix[field] == full_at_t[field]
    values = {"c": .2, "a": .1, "b": .1}
    left = rps_midrank(values, ["a", "b", "c"])
    right = rps_midrank(dict(reversed(list(values.items()))), ["c", "b", "a"])
    assert left == right


def test_market_path_unknown_suffix_requires_new_version_to_rebase():
    path = historical_market_path([("a", .1), ("b", None), ("c", .2)], start_sessions=["0", "a", "b"],
                                  start_universe_snapshot_ids=["U0", "Ua", "Ub"],
                                  market_calendar_id="CAL-1", input_source_digest="e" * 64)
    assert path[0]["level"] == pytest.approx(1.1)
    assert path[1]["quality_state"] == "UNKNOWN"
    assert path[2]["quality_state"] == "UNKNOWN"
    assert path[2]["rebase_policy"] == "UNKNOWN_SUFFIX_UNTIL_NEW_SERIES_VERSION"
    new_series = historical_market_path([("c", .2)], start_sessions=["b"], start_universe_snapshot_ids=["Ub"],
                                        market_calendar_id="CAL-1", input_source_digest="e" * 64,
                                        series_version="DAILY_REBALANCED_RESEARCH_INDEX_V2")
    assert new_series[0]["level"] == pytest.approx(1.2)
