from workbench_service.core_product_bff_r1 import CoreProductBFFR1


class CandidateApi:
    def __init__(self, rows_by_day):
        self.token = 'candidate-token'
        self.candidate = {
            'accepted_trade_date': '2026-10-14',
            'data_cutoff_date': '2026-10-14',
            'observed_at': '2026-10-20T12:00:00+08:00',
            'membership_observed_at': '2026-10-09T09:44:01+08:00',
            'published_sessions': list(rows_by_day),
            'owners': {day: {'raw': {'path': f'owners/{day}/raw.jsonl.gz', 'sha256': day}} for day in rows_by_day},
        }
        self.rows_by_day = rows_by_day

    def context(self):
        return {'read_scope': 'DEVELOPMENT_CANDIDATE_PREVIEW', 'production_accepted': False}

    def read(self, domain, day, token):
        assert domain == 'raw'
        assert token == self.token
        return {'rows': self.rows_by_day[day]}


def make_bff(rows_by_day):
    api = CandidateApi(rows_by_day)
    bff = CoreProductBFFR1.__new__(CoreProductBFFR1)
    bff.api = api
    bff.legacy = None
    bff.isolated_history = None
    bff.chart_history_pack = lambda _day: (_ for _ in ()).throw(
        ValueError('EMBEDDED_PRODUCT_CATALOG_REQUIRED_NO_FALLBACK'))
    return bff


def test_candidate_chart_reads_exact_dated_raw_owners_only():
    sid = 'SEC-TEST'
    rows = {
        '2026-10-13': [dict(security_id=sid, trade_date='2026-10-13', open=10, high=12, low=9, close=11, volume=100, amount=1100)],
        '2026-10-14': [dict(security_id=sid, trade_date='2026-10-14', open=11, high=13, low=10, close=12, volume=200, amount=2400)],
    }
    code, payload = make_bff(rows).chart('2026-10-14', sid, {'period': 'D', 'price_basis': 'RAW'})
    assert code == 200
    assert payload['status'] == 'READY'
    assert payload['candidate_chart_scope'] == 'CANDIDATE_DAILY_OWNER_WINDOW_ONLY'
    assert payload['PIT_ELIGIBLE'] is False
    assert [item['trade_date'] for item in payload['items']] == list(rows)
    assert payload['items'][-1]['close'] == 12
    assert [binding['trade_date'] for binding in payload['source_bindings']] == list(rows)


def test_candidate_chart_does_not_fabricate_a_qfq_series():
    sid = 'SEC-TEST'
    rows = {'2026-10-14': [dict(security_id=sid, trade_date='2026-10-14', open=11, high=13, low=10, close=12, volume=200, amount=2400)]}
    code, payload = make_bff(rows).chart('2026-10-14', sid, {'period': 'D', 'price_basis': 'QFQ'})
    assert code == 200
    assert payload['status'] == 'EMPTY_VALID'
    assert payload['chart_availability'] == 'SOURCE_INCOMPLETE'
    assert payload['reason'] == 'CANDIDATE_QFQ_HISTORY_INDEX_NOT_BOUND'
    assert payload['items'] == []
