from decimal import Decimal

from validation.external_qfq import ExternalBar, compare_ohlc, parse_eastmoney_payload, parse_tencent_payload


def test_eastmoney_daily_qfq_field_order() -> None:
    payload = {"data": {"klines": ["2025-06-25,10.01,10.22,10.30,9.99,123"]}}
    bar = parse_eastmoney_payload(payload)[20250625]
    assert (bar.open, bar.high, bar.low, bar.close) == tuple(
        map(Decimal, ("10.01", "10.30", "9.99", "10.22"))
    )


def test_tencent_daily_qfq_field_order_and_tolerance() -> None:
    payload = {"data": {"sh600519": {"qfqday": [["2025-06-25", "10.004", "10.224", "10.304", "9.994", "1"]]}}}
    bar = parse_tencent_payload(payload, "SH.600519")[20250625]
    compared = compare_ohlc(
        {"local_open": 10.01, "local_high": 10.30, "local_low": 9.99, "local_close": 10.22},
        bar,
    )
    assert compared["within_tolerance"] is True
    assert compared["status"] == "LOCAL_MATCHES_EXTERNAL"


def test_unavailable_external_bar_is_explicit() -> None:
    compared = compare_ohlc(
        {"local_open": 1, "local_high": 1, "local_low": 1, "local_close": 1}, None
    )
    assert compared["status"] == "UNVERIFIABLE_EXTERNAL"

