import pytest

from src.v4.factors.core import Bar, Observation, compute_core, market_reference, rps_midrank
from src.v4.factors.native import historical_market_path, market_axis_primitives, sector_native
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
    assert suspended["ma5"].quality_state == "UNKNOWN"
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
    assert historical_market_path([("a", .1), ("b", .2)])[-1]["level"] == 1.32
    primitive = sector_native(["b", "a", "a"], {"a": {"quality_state": "OBSERVED", "ret1": 1, "amount": 100,
                              "above_ma20": True}})
    assert primitive["member_count"] == 2
    assert primitive["publication_permission"] == "NOT_V4_08_SECTOR_FACTORS"


def test_market_axis_exact_thresholds_and_conflict():
    at = market_axis_primitives(breadth=.05, participation=1.2,
                                limit_coverage=.8, stress_ratio=.05, prior_stress_ratio=.05)
    assert at["breadth_axis"] == "STABLE"
    assert at["participation_axis"] == "EXPANDING"
    assert at["stress_level"] == "HIGH"
    assert at["stress_change"] == "STABLE"
    assert at["trend_axis_blocker"] == "CONTRACT_CONFLICT_MARKET_REGIME_TREND_WEAK_AST"
    below = market_axis_primitives(breadth=-.050001, participation=.79999,
                                   limit_coverage=.79999, stress_ratio=.01, prior_stress_ratio=.02)
    assert below["breadth_axis"] == "DETERIORATING"
    assert below["participation_axis"] == "THIN"
    assert below["stress_level"] is None
    assert below["stress_change"] == "DECLINING"


def test_relative_factors_keep_rps_and_reference_separate():
    returns = {1: {"a": .1, "b": .2}, 3: {"a": .3, "b": .5},
               5: {"a": .4, "b": .6}, 20: {"a": .1, "b": .1}}
    previous = {1: {"rps5": {"a": 10, "b": 90}},
                3: {"rps5": {"a": 20, "b": 80}, "rps20": {"a": 40, "b": 60}}}
    values, refs = relative_factors(current_returns=returns, historical_rps=previous,
                                    asof_universe=["b", "a"],
                                    start_universes={1: ["a", "b"], 3: ["a", "b"], 5: ["a", "b"]})
    assert values["a"]["rps5"] == 0
    assert values["a"]["rps20"] == 50
    assert values["a"]["rps5_delta1"] == -10
    assert values["a"]["rel_market_1"] == pytest.approx(-.05)
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
