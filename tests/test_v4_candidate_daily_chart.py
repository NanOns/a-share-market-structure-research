import json
from pathlib import Path

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


def test_candidate_chart_builds_qfq_from_dated_raw_and_frozen_tdx_gbbq(tmp_path, monkeypatch):
    import tdx.gbbq_reader as gbbq_reader
    import workbench_analysis.r43_owner_replay as owner_replay
    from tdx.gbbq_reader import GbbqRecord

    sid = 'SEC-TEST'
    rows = {
        '2026-10-09': [dict(security_id=sid, trade_date='2026-10-09', open=10, high=10.5, low=9.5, close=10, volume=100, amount=1000)],
        '2026-10-14': [dict(security_id=sid, trade_date='2026-10-14', open=9.8, high=10.1, low=9.7, close=9.9, volume=200, amount=1980)],
    }
    bff = make_bff(rows)
    bff.api.root = tmp_path
    source_path = tmp_path / 'gbbq.bin'
    source_bytes = b'TDX frozen GBBQ test bytes'
    source_path.write_bytes(source_bytes)
    bff.api.candidate['source_registry'] = {'2026-10-14': {'gbbq': {
        'path': 'gbbq.bin', 'sha256': __import__('hashlib').sha256(source_bytes).hexdigest(), 'bytes': len(source_bytes)}}}
    bff.api.candidate['owners']['2026-10-09'] = {'raw': {'path': 'owners/2026-10-09/raw.jsonl.gz', 'sha256': 'raw-09'}}
    bff.api.candidate['owners']['2026-10-14'] = {'raw': {'path': 'owners/2026-10-14/raw.jsonl.gz', 'sha256': 'raw-14'}}
    bff.resolve_dated_object = lambda *_args: {'symbol': 'SH.600000'}
    monkeypatch.setattr(owner_replay, 'checked', lambda root, binding: Path(root) / binding['path'])
    calls={'read_gbbq':0}
    def fake_gbbq(_path):
        calls['read_gbbq']+=1
        return [GbbqRecord(security_id='SH.600000',raw_code='600000',event_date=20261012,category=1,
            c1=1.0,c2=0.0,c3=0.0,c4=0.0,source='fixture',source_record_index=1,market_byte=1)]
    monkeypatch.setattr(gbbq_reader, 'read_gbbq', fake_gbbq)
    (tmp_path / 'config').mkdir()
    (tmp_path / 'config/v4_02_gbbq_price_impact_classification_v1.json').write_text(
        json.dumps({'dispositions': {'1': {'formal_disposition': 'SUPPORTED_XRXD'}}}), encoding='utf-8')

    code, payload = bff.chart('2026-10-14', sid, {'period': 'D', 'price_basis': 'QFQ'})
    assert code == 200
    assert payload['status'] == 'READY'
    assert payload['price_basis'] == 'QFQ'
    assert payload['chart_availability'] == 'READY'
    assert payload['PIT_ELIGIBLE'] is False
    assert payload['items'][0]['close'] == 9.9
    assert payload['items'][1]['close'] == 9.9
    assert payload['exact_transport_count'] == 2
    assert payload['source_bindings'][-1]['role'] == 'T0_GBBQ_ADJUSTMENT_SOURCE'
    assert 'TDX GBBQ' in payload['disclaimer']
    _, repeated = bff.chart('2026-10-14', sid, {'period': 'D', 'price_basis': 'QFQ'})
    assert repeated['chart_cache_hit'] is True
    assert repeated['items'] == payload['items']
    assert calls['read_gbbq'] == 1
