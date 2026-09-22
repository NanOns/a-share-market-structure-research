import json

from workbench_online.base import FetchResult, OnlineFetchPolicy
from workbench_online.eastmoney_quotes import fetch_eastmoney_quotes


def test_eastmoney_quote_batch_normalizes_units_and_observed_time():
    def fake_fetcher(url, policy, referer=None):
        assert referer == "https://quote.eastmoney.com/"
        assert "ut=fa5fd1943c7b386f172d6893dbbd1d0c" in url
        assert "secids=1.600000%2C0.000001" in url or "secids=1.600000,0.000001" in url
        body = json.dumps(
            {"data": {"diff": [{"f2": 12.34, "f3": 123, "f6": 456789, "f12": "600000", "f13": 1, "f14": "浦发银行", "f47": 7890, "f168": 321, "f170": 123}]}}
        ).encode("utf-8")
        return FetchResult("2026-09-11T07:10:00+00:00", "2026-09-11T07:10:01+00:00", 200, "application/json", body, url)

    _, rows = fetch_eastmoney_quotes(["SH.600000", "SZ.000001"], OnlineFetchPolicy(), fetcher=fake_fetcher)
    assert rows[0]["security_id"] == "SH.600000"
    assert rows[0]["price"] == 12.34
    assert rows[0]["ret1"] == 1.23
    assert rows[0]["amount_unit"] == "CNY"
    assert rows[0]["volume"] == 789000
    assert rows[0]["source_volume_unit"] == "LOTS_100_SHARES"
    assert rows[0]["quote_state"] == "UNKNOWN"
    assert rows[0]["time_semantics"] == "OBSERVED_AT_ONLY"


def test_eastmoney_quote_rejects_unmapped_or_oversized_requests():
    try:
        fetch_eastmoney_quotes(["BJ.830001"], OnlineFetchPolicy(), fetcher=lambda *_args: None)
    except ValueError as exc:
        assert str(exc) == "QUOTE_SECURITY_ID_LIMIT" or str(exc) == "QUOTE_SECURITY_ID_UNMAPPED"
    else:
        raise AssertionError("unsupported exchange must fail closed")

    try:
        fetch_eastmoney_quotes([f"SZ.{index:06d}" for index in range(51)], OnlineFetchPolicy(), fetcher=lambda *_args: None)
    except ValueError as exc:
        assert str(exc) == "QUOTE_SECURITY_ID_LIMIT"
    else:
        raise AssertionError("oversized quote request must fail closed")


def test_eastmoney_quote_rejects_non_numeric_source_fields():
    def fake_fetcher(url, policy, referer=None):
        body = json.dumps({"data": {"diff": [{"f2": "bad", "f3": 1, "f6": 2, "f12": "600000", "f13": 1}]}}).encode("utf-8")
        return FetchResult("2026-09-11T07:10:00+00:00", "2026-09-11T07:10:01+00:00", 200, "application/json", body, url)

    try:
        fetch_eastmoney_quotes(["SH.600000"], OnlineFetchPolicy(), fetcher=fake_fetcher)
    except ValueError as exc:
        assert str(exc) == "QUOTE_FIELD_INVALID:price"
    else:
        raise AssertionError("invalid quote field must fail closed")
