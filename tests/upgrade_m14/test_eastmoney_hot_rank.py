import json
from datetime import datetime, timezone

from workbench_online.base import FetchResult, OnlineFetchPolicy
from workbench_online.eastmoney_hot_rank import decode_eastmoney_payload, fetch_eastmoney_hot_rank


def _fake_fetcher(_url, _policy, **_kwargs):
    now = datetime.now(timezone.utc).isoformat()
    return FetchResult(now, now, 200, "application/x-javascript", b"var popularityList='fixture';", "https://example.invalid/rank")


def _fake_decoder(_body):
    return [
        {
            "code": "688001",
            "rankNumber": 1,
            "changeNumber": 3,
            "exactTime": "2026-09-11 14:00:00",
            "history": [{"SRCSECURITYCODE": "SH688001", "RANK": 1}],
        },
        {
            "code": "000001",
            "rankNumber": 2,
            "changeNumber": -1,
            "exactTime": "2026-09-11 14:00:00",
            "history": [
                {"SRCSECURITYCODE": "SZ000002", "RANK": 1},
                {"SRCSECURITYCODE": "SZ000001", "RANK": 2},
            ],
        },
    ]


def test_eastmoney_adapter_preserves_platform_rank_and_source_time():
    result, normalized = fetch_eastmoney_hot_rank(
        OnlineFetchPolicy(), fetcher=_fake_fetcher, decoder=_fake_decoder
    )
    assert result.status_code == 200
    assert normalized["source_as_of"] == "2026-09-11 14:00:00"
    assert normalized["decoder_version"] == "EASTMONEY_AES_CBC_NODE_CRYPTO_V1"
    assert [row["platform_rank"] for row in normalized["rows"]] == [1, 2]
    assert [row["security_id"] for row in normalized["rows"]] == ["SH.688001", "SZ.000001"]


def test_eastmoney_decoder_rejects_missing_encoded_variable():
    try:
        decode_eastmoney_payload(b"not-a-popularity-list")
    except ValueError as exc:
        assert str(exc) == "EASTMONEY_DECODE_FAILED"
    else:
        raise AssertionError("decoder must reject a missing popularityList variable")


def test_eastmoney_mapping_rejects_history_without_current_rank_match():
    from workbench_online.eastmoney_hot_rank import _security_id

    assert _security_id({"rankNumber": 1, "history": [{"SRCSECURITYCODE": "SH688001", "RANK": 99}]}) is None
