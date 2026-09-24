from dataclasses import replace
from datetime import date, timedelta

from src.focus_tracker.materialize import VerifiedNormalizedSlice
from src.focus_tracker.pit_rps import (CONTRACT_ID, PITUniverse,
                                       calculate_pit_rps20_deltas)


def fixture(count=101):
    calendar = tuple(date(2026, 1, 1) + timedelta(days=i) for i in range(140))
    target = calendar[-1]
    previous = calendar[-4]
    securities = {f"SH.{i:06d}" for i in range(count)}
    by_security = {}
    for index, sid in enumerate(sorted(securities)):
        rows = {}
        base = 500 if sid == "SH.000000" else 100 + index
        for position, day in enumerate(calendar):
            # Make 20-session return rankings distinct. SH.000000 has a
            # point-in-time relative-strength jump over the final 3 sessions.
            close = base + position
            if sid == "SH.000000" and position > len(calendar) - 4:
                close += 100
            rows[day] = {
                "date": day, "has_actual_bar": True,
                "adjustment_status": "VERIFIED_REPRODUCIBLE_TDX_NATIVE",
                "adjustment_version": "qfq-v1", "raw_close": str(close),
                "qfq_mul": "1", "qfq_add": "0",
            }
        by_security[sid] = rows
    normalized = VerifiedNormalizedSlice("a" * 64, calendar, by_security)
    universes = {
        day: PITUniverse(day, "pub-" + day.isoformat(), "bundle-" + day.isoformat(),
                         "b" * 64, "c" * 64, "meta-" + day.isoformat(),
                         frozenset(securities), "POSTGRES_PACKAGE_SHA256")
        for day in (target, previous)
    }
    return normalized, target, previous, securities, universes


def test_pit_rps20_delta_uses_accepted_date_universes_and_t_minus_3():
    normalized, target, previous, securities, universes = fixture()
    deltas, evidence = calculate_pit_rps20_deltas(
        normalized=normalized, universes=universes, evaluation_sessions=(target,))

    assert evidence["contract_id"] == CONTRACT_ID
    assert evidence["delta_quality"][target.isoformat()]["status"] == "READY"
    assert len(deltas[target]) == len(securities)
    assert deltas[target]["SH.000000"] == "0.9900990099009900990099009901"
    assert evidence["rps_date_quality"][previous.isoformat()]["source_bundle_id"] == \
        universes[previous].source_bundle_id


def test_pit_rps20_excludes_security_outside_t_minus_3_universe():
    normalized, target, previous, securities, universes = fixture()
    prior = universes[previous]
    universes[previous] = replace(prior, security_ids=frozenset(securities - {"SH.000000"}))

    deltas, evidence = calculate_pit_rps20_deltas(
        normalized=normalized, universes=universes, evaluation_sessions=(target,))

    assert evidence["delta_quality"][target.isoformat()]["status"] == "READY"
    assert "SH.000000" not in deltas[target]
    assert len(deltas[target]) == len(securities) - 1


def test_pit_rps20_fails_closed_below_minimum_cross_section():
    normalized, target, previous, _, universes = fixture(count=99)

    deltas, evidence = calculate_pit_rps20_deltas(
        normalized=normalized, universes=universes, evaluation_sessions=(target,))

    assert deltas[target] == {}
    assert evidence["delta_quality"][target.isoformat()]["status"] == "UNAVAILABLE"


def test_pit_rps20_requires_120_actual_bars_within_bounded_history():
    normalized, target, _, securities, universes = fixture()
    sid = sorted(securities)[0]
    rows = normalized.by_security[sid]
    for day in normalized.calendar[:21]:
        rows[day]["has_actual_bar"] = False

    deltas, evidence = calculate_pit_rps20_deltas(
        normalized=normalized, universes=universes, evaluation_sessions=(target,))

    assert sid not in deltas[target]
    assert evidence["rps_date_quality"][target.isoformat()]["finite_return_count"] == \
        len(securities) - 1
