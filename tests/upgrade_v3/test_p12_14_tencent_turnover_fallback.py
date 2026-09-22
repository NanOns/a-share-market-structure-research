from workbench_online.base import FetchResult, OnlineFetchPolicy
from workbench_online.tencent_quotes import fetch_tencent_quotes


def test_tencent_fallback_normalizes_turnover_amount_and_lot_volume():
    fields = [""] * 39
    fields[1] = "通鼎互联"
    fields[2] = "002491"
    fields[3] = "22.23"
    fields[30] = "20260915161415"
    fields[35] = "22.23/2670494/5840461313"
    fields[36] = "2670494"
    fields[38] = "22.70"
    body = ('v_sz002491="' + "~".join(fields) + '";').encode("gb18030")
    captured = {}
    def fetcher(url, policy, referer=None):
        captured.update(url=url, referer=referer)
        return FetchResult("a", "b", 200, "text/plain", body, url)
    _, rows = fetch_tencent_quotes(["SZ.002491"], OnlineFetchPolicy(), fetcher=fetcher)
    assert captured["referer"] == "https://gu.qq.com/"
    assert rows[0]["security_id"] == "SZ.002491"
    assert rows[0]["source_id"] == "TENCENT_QUOTES_LATEST"
    assert rows[0]["price"] == 22.23
    assert rows[0]["amount"] == 5_840_461_313.0
    assert rows[0]["volume"] == 267_049_400.0
    assert abs(rows[0]["turnover_rate"] - .227) < 1e-12


def test_tencent_fallback_rejects_more_than_one_bounded_batch():
    try:
        fetch_tencent_quotes([f"SZ.{index:06d}" for index in range(51)])
    except ValueError as exc:
        assert str(exc) == "TENCENT_QUOTE_SECURITY_ID_LIMIT"
    else:
        raise AssertionError("batch limit was not enforced")
