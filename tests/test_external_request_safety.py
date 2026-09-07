import urllib.error
from decimal import Decimal

from validation.external_qfq import PublicQfqClients, parse_tencent_payload, compare_ohlc, ExternalBar


def test_501_opens_circuit_and_skips_later_queries():
    clients = PublicQfqClients()
    calls = []
    def fail():
        calls.append(1)
        clients.tencent.attempt()
        raise urllib.error.HTTPError('https://example.invalid', 501, 'Not Implemented', {}, None)
    assert clients._retry(fail, clients.tencent) is None
    assert clients._retry(fail, clients.tencent) is None
    assert len(calls) == 1


def test_raw_and_qfq_share_provider_request_budget():
    clients = PublicQfqClients()
    clients.tencent.value['request_count'] = 199
    clients.tencent_raw.value['request_count'] = 1
    def forbidden():
        raise AssertionError('network must not be attempted')
    assert clients._retry(forbidden, clients.tencent) is None
    assert clients._retry(forbidden, clients.tencent_raw) is None


def test_raw_payload_does_not_silently_satisfy_qfq():
    payload = {'data': {'sh600519': {'day': [['2025-06-25', '100', '101', '102', '99']]}}}
    assert parse_tencent_payload(payload, 'SH.600519') == {}
    assert len(parse_tencent_payload(payload, 'SH.600519', raw_diagnostic=True)) == 1


def test_wrong_date_is_unverifiable():
    local = {'date': 20250625, **{f'local_{f}': 1 for f in ('open', 'high', 'low', 'close')}}
    bar = ExternalBar(20250626, *[Decimal('1')] * 4)
    assert compare_ohlc(local, bar)['status'] == 'UNVERIFIABLE_EXTERNAL'
