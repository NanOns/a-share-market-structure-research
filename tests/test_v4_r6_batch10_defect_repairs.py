from __future__ import annotations

import hashlib
import json
import gzip
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_corrected_owner_pipeline_requires_explicit_dynamic_target_date(tmp_path):
    from workbench_analysis.corrected_owner_pipeline import run_corrected_owner_pipeline

    with pytest.raises(ValueError, match='CORRECTED_TARGET_DATE_REQUIRED'):
        run_corrected_owner_pipeline(tmp_path)


def test_corrected_owner_pipeline_keeps_contract_sessions_and_rejects_others(tmp_path, monkeypatch):
    from workbench_analysis import corrected_owner_pipeline as pipeline

    day = '2026-10-08'
    monkeypatch.setattr(pipeline, 'load', lambda path: {'target_sessions': [day]})
    monkeypatch.setattr(pipeline, 'official_sessions', lambda root: [day])
    monkeypatch.setattr(pipeline, 'materialize_core', lambda *args, **kwargs: None)
    assert pipeline.run_corrected_owner_pipeline(tmp_path, target_date=day, stage='core')['status'] == 'CORRECTED_CORE_READY'
    with pytest.raises(ValueError, match='CORRECTED_SESSION_OUTSIDE_VERSIONED_CONTRACT'):
        pipeline.run_corrected_owner_pipeline(tmp_path, target_date='2026-10-09', stage='core')


def test_priority_legacy_route_uses_same_dated_pg_owner_consumer():
    from workbench_service.core_product_bff_r1 import _normalize_priority_route

    assert _normalize_priority_route('/api/v4/priority') == '/api/v4/radar/priority'
    assert _normalize_priority_route('/api/v4/radar/priority') == '/api/v4/radar/priority'
    assert _normalize_priority_route('/api/v4/focus/priority') == '/api/v4/focus/priority'


def test_focus_priority_is_explicitly_blocked_until_rule_is_adjudicated():
    from workbench_service.core_product_bff_r1 import _focus_priority_contract_block

    payload = _focus_priority_contract_block('2026-10-23')
    assert payload['status'] == 'CONTRACT_BLOCKED'
    assert payload['selected_rule'] is None
    assert payload['ranked'] is False
    assert payload['items'] == []
    assert [row['contract_id'] for row in payload['rule_options']] == [
        'FOCUS_PRIORITY_D0_STATE_BUCKETS_R1',
        'FOCUS_PRIORITY_EVIDENCE_RECENCY_R1',
    ]


def test_focus_priority_route_returns_block_without_ranking(monkeypatch):
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    from workbench_db import v4_read_index_r2

    day = '2026-10-23'
    monkeypatch.setattr(v4_read_index_r2, 'validate_query',
                        lambda query, token, dates, default_day, path: day)
    bff = object.__new__(CoreProductBFFR1)
    bff.api = SimpleNamespace(token='candidate-token', candidate={
        'published_sessions': [day], 'accepted_trade_date': day})
    bff.envelope = lambda target_day, **payload: dict(payload)
    code, payload = bff._get_dated_product('/api/v4/focus/priority', {
        'context_token': 'candidate-token', 'limit': 10})
    assert code == 200
    assert payload['status'] == 'CONTRACT_BLOCKED'
    assert payload['ranked'] is False
    assert payload['items'] == []


def test_priority_exact_coordinate_accepts_both_versioned_native_coordinate_families():
    from workbench_service.core_product_bff_r1 import _exact_price_coordinate

    revision = 'a' * 64
    for base in ('TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE',
                 'TDX_NATIVE_AFFINE_QFQ_V0_3_EXACT_TARGET_COORDINATE'):
        core = {'price_basis_id': base + ':' + revision}
        adjusted = {'price_basis': base, 'adjustment_source_revision': revision,
                    'adjustment_readiness': 'READY'}
        assert _exact_price_coordinate(core, adjusted) == core['price_basis_id']
        assert _exact_price_coordinate(core, {**adjusted,
            'adjustment_source_revision': 'b' * 64}) is None


def test_pg_lifecycle_projection_preserves_parameter_and_dated_source_bindings():
    from workbench_service.core_product_bff_r1 import _pg_lifecycle_source

    day = '2026-10-21'
    binding = {'contract_id': 'SECTOR_LIFECYCLE_PG_R1', 'schema': 'dev_sector',
               'digest': 'a' * 64, 'producer_sha256': 'b' * 64,
               'parameter_digest': 'c' * 64}
    lifecycle = {'input_digest': 'd' * 64,
                 'source_bindings': {day: {'sector': {'sha256': 'e' * 64}}}}
    got = _pg_lifecycle_source(binding, lifecycle, day)
    assert got['parameter_sha256'] == binding['parameter_digest']
    assert got['source_bindings'] == lifecycle['source_bindings']
    assert got['input_digest'] == lifecycle['input_digest']


def test_market_stress_window_is_relative_to_each_bound_candidate_t0():
    from workbench_analysis.r6_candidate_market_stress import _stress_window_days

    sessions = [f'2026-10-{day:02d}' for day in range(1, 22)]
    assert _stress_window_days({'accepted_trade_date': '2026-10-21',
                                'published_sessions': sessions}) == sessions[-3:]
    with pytest.raises(ValueError, match='R7_MARKET_STRESS_T0_NOT_IN_PUBLISHED_SESSIONS'):
        _stress_window_days({'accepted_trade_date': '2026-10-22',
                             'published_sessions': sessions})


def test_market_trend_requires_verified_permission_and_same_t0():
    from workbench_analysis import r6_candidate_market_stress as stress

    reference = {
        'trade_date': '2026-10-21', 'series_id': 'SERIES:V1', 'price_basis_id': 'QFQ:REV',
        'source_sha256': 'a' * 64, 'market_calendar_id': 'CAL', 'index_close': 101,
        'index_ma20': 100, 'index_ma20_t_minus_5': 99,
        'source_available_at': '2026-10-21T08:00:00+00:00',
        'knowledge_cutoff': '2026-10-21T08:00:00+00:00',
        'permission_chain': {'candidate_root': 'fixture', 'trade_date': '2026-10-21'},
        'input_publication_id': 'b' * 64, 'time_role': 'KNOWN_BY_CUTOFF',
    }
    monkey = pytest.MonkeyPatch()
    try:
        monkey.setattr(stress, '_permission_chain_proven', lambda *args: True)
        allowed = stress.adapt_candidate_trend_reference(
            reference, t0='2026-10-21', knowledge_cutoff='2026-10-21T08:00:00+00:00')
        assert allowed['quality'] == 'OBSERVED'
        assert allowed['permission_chain_proven'] is True
        monkey.setattr(stress, '_permission_chain_proven', lambda *args: False)
        denied = stress.adapt_candidate_trend_reference(
            reference, t0='2026-10-21', knowledge_cutoff='2026-10-21T08:00:00+00:00')
        assert denied['quality'] == 'SOURCE_INCOMPLETE'
        assert denied['reason'] == 'TREND_REFERENCE_PERMISSION_NOT_PROVEN'
        wrong_role = stress.adapt_candidate_trend_reference(
            {**reference, 'time_role': 'RECONSTRUCTED'},
            t0='2026-10-21', knowledge_cutoff='2026-10-21T08:00:00+00:00')
        assert wrong_role['reason'] == 'TREND_REFERENCE_TIME_ROLE_NOT_ADMISSIBLE'
    finally:
        monkey.undo()


def test_market_trend_real_permission_verifier_accepts_only_bound_r8_pg_chain(tmp_path, monkeypatch):
    from workbench_analysis import market_source_acquisition
    from workbench_analysis import r6_candidate_market_stress as stress
    from workbench_db import v4_native
    from workbench_db.v4_forward_pg_r1 import ForwardFactStore

    day = '2026-10-22'
    sessions = []
    cursor = __import__('datetime').date.fromisoformat(day)
    while len(sessions) < 25:
        if cursor.weekday() < 5:
            sessions.append(cursor.isoformat())
        cursor = cursor.fromordinal(cursor.toordinal() - 1)
    sessions.sort()
    monkeypatch.setattr(market_source_acquisition, 'official_sessions', lambda root: sessions)

    def bind(path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = payload if isinstance(payload, bytes) else json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
        path.write_bytes(raw)
        return {'path': path.relative_to(tmp_path).as_posix(), 'bytes': len(raw),
                'sha256': hashlib.sha256(raw).hexdigest()}

    source_path = tmp_path / 'data/v4/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R3.jsonl.gz'
    raw_rows = [json.dumps({'trade_date': session, 'series_version': 'V1',
                            'path_identity': 'INDEX-X', 'market_calendar_id': 'CAL-X',
                            'adjustment_basis_id': 'QFQ-X', 'quality_state': 'OBSERVED',
                            'level': float(index + 1)}, sort_keys=True).encode() + b'\n'
                for index, session in enumerate(sessions)]
    source_binding = bind(source_path, gzip.compress(b''.join(raw_rows)))
    market_payload = {'trade_date': day, 'input_bindings': [source_binding]}
    market_binding = bind(tmp_path / 'data/v4/market-owner.json', market_payload)
    head = {'accepted_trade_date': day, 'published_sessions': sessions,
            'owners': {day: {'market': market_binding}}}
    head_raw = json.dumps(head, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':')).encode('utf-8')
    head_path = tmp_path / 'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    head_binding = bind(head_path, head_raw)
    token = head_binding['sha256']
    schema = 'v4_synthetic_r8'
    database_identity = {'database': 'market_research', 'port': 5432}
    readback = {'status': 'PENDING', 'context_token': token,
                'accepted_trade_date': day, 'production_accepted': False,
                'read_scope': 'DEVELOPMENT_CANDIDATE_PREVIEW'}
    owner_authority = bind(tmp_path / 'data/v4/owner-authority.json', {'scope': 'test'})
    source_freeze = bind(tmp_path / 'data/v4/source-freeze.json', {'scope': 'test'})
    transaction = bind(tmp_path / 'data/v4/publication-transaction.json',
                       {'state': 'COMMITTED', 'candidate_token': token})
    pg_row = (token, day, '1' * 64, token, owner_authority['sha256'],
              source_freeze['sha256'], readback, '2026-10-22T08:00:00+00:00')
    row_sha = hashlib.sha256(stress._canonical([*pg_row[:6], pg_row[6]])).hexdigest()
    pg_event = ['FINALIZED', row_sha,
                {'transaction_sha256': transaction['sha256'], 'readback': readback},
                '2026-10-22T08:00:00+00:00']
    receipt = {'contract_id': 'V4_R8_REAL_APPEND_PG_RECEIPT_R2', 'status': 'PASS',
               'candidate_token': token, 'trade_date': day, 'production_accepted': False,
               'formal_head_modified': False, 'candidate_head_sha256': token,
               'predecessor_head_sha256': pg_row[2], 'owner_authority': owner_authority,
               'source_freeze': source_freeze, 'publication_transaction': transaction,
               'pg_schema': schema, 'pg_database_identity': database_identity,
               'pg_row_sha256': row_sha, 'readback': readback}
    bind(tmp_path / 'data/v4/r8_publication_bridge_v1/receipts' / f'{token}.json', receipt)

    class QueryResult:
        def __init__(self, row):
            self.row = row

        def fetchone(self):
            return self.row

    class FakePG:
        def execute(self, statement, params=None):
            return QueryResult(pg_row if 'FROM r8_publications' in statement else pg_event)

    class FakeConnection:
        def __enter__(self):
            return FakePG()

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(v4_native, 'connection', lambda requested_schema, read_only=False: FakeConnection())
    monkeypatch.setattr(v4_native, 'workspace_schema', lambda *args, **kwargs: schema)
    monkeypatch.setattr(ForwardFactStore, '_database_identity', staticmethod(lambda pg: database_identity))

    values = [float(index + 1) for index in range(25)]
    reference = {
        'trade_date': day, 'series_id': 'INDEX-X:V1', 'price_basis_id': 'QFQ-X',
        'source_sha256': source_binding['sha256'], 'market_calendar_id': 'CAL-X',
        'index_close': values[-1], 'index_ma20': sum(values[-20:]) / 20,
        'index_ma20_t_minus_5': sum(values[:20]) / 20,
        'source_available_at': '2026-10-22T08:00:00+00:00',
        'knowledge_cutoff': '2026-10-22T08:00:00+00:00',
        'permission_chain': {'candidate_root': str(tmp_path), 'trade_date': day},
        'input_publication_id': token, 'time_role': 'KNOWN_BY_CUTOFF',
    }
    allowed = stress.adapt_candidate_trend_reference(
        reference, t0=day, knowledge_cutoff='2026-10-22T08:00:00+00:00')
    assert allowed['quality'] == 'OBSERVED'
    assert allowed['permission_chain_proven'] is True

    pg_event[0] = 'ABORTED'
    denied = stress.adapt_candidate_trend_reference(
        reference, t0=day, knowledge_cutoff='2026-10-22T08:00:00+00:00')
    assert denied['quality'] == 'SOURCE_INCOMPLETE'
    assert denied['reason'] == 'TREND_REFERENCE_PERMISSION_NOT_PROVEN'


def test_frozen_invalidation_successor_is_unknown_when_contract_is_not_proven():
    from workbench_analysis.r7_frozen_invalidation_v2 import evaluate_frozen_invalidation

    got = evaluate_frozen_invalidation(
        prior_episode={'episode_id': 'EP-1', 'invalidation_contract_id': 'FROZEN_INVALIDATION_CONTRACT_R2'},
        current_close=10, frozen_invalidation_level=9,
        current_price_basis_id='QFQ-1', frozen_price_basis_id='QFQ-1',
        current_bar_status='ACTUAL', current_source_sha256='a' * 64,
        trade_date='2026-10-21', source_trade_date='2026-10-21')
    assert got['value'] == 'UNKNOWN'
    assert got['reason'] == 'FROZEN_LEVEL_OR_PRODUCER_CONTRACT_NOT_PROVEN'


def test_baostock_factor_alias_requires_exact_pinned_adapter():
    from workbench_analysis.baostock_daily_update_source import (
        BaoStockDailyUpdateError, _normalize_factor_schema)

    adapter = json.loads((Path(__file__).resolve().parents[1] /
                          'config/baostock_dm01_sdk_schema_adapter_v2.json').read_text(encoding='utf-8'))
    sdk = {'version': adapter['sdk_version'],
           'installed_python_sources_sha256': adapter['sdk_python_sources_sha256']}
    raw_fields = adapter['factor_raw_schema']
    rows = [{'code': 'sh.999999', 'dividOperateDate': '2026-10-22',
             'foreAdjustFactor': '1', 'backAdjustFactor': '1', 'adjustFacto': '1'}]
    normalized, evidence = _normalize_factor_schema(rows, raw_fields, sdk=sdk)
    assert normalized[0]['adjustFactor'] == '1'
    assert 'adjustFacto' not in normalized[0]
    assert evidence['adapter_sha256'] == hashlib.sha256(
        (Path(__file__).resolve().parents[1] / 'config/baostock_dm01_sdk_schema_adapter_v2.json').read_bytes()
    ).hexdigest()
    with pytest.raises(BaoStockDailyUpdateError, match='BAOSTOCK_FACTOR_SCHEMA_ADAPTER_BINDING_MISMATCH'):
        _normalize_factor_schema(rows, raw_fields,
                                 sdk={**sdk, 'installed_python_sources_sha256': '0' * 64})
    with pytest.raises(BaoStockDailyUpdateError, match='BAOSTOCK_FACTOR_SCHEMA_ADAPTER_BINDING_MISMATCH'):
        _normalize_factor_schema(rows, [*raw_fields[:-1], 'unknownField'], sdk=sdk)


def test_baostock_capture_binds_raw_and_normalized_factor_responses(monkeypatch, tmp_path):
    from workbench_analysis import baostock_daily_update_source as source

    day = '2026-10-22'
    daily = [{'date': day, 'code': 'sh.999999', 'open': '10', 'high': '11', 'low': '9',
              'close': '10.5', 'volume': '100', 'amount': '1050', 'tradestatus': '1', 'isST': '0'}]
    factor = [{'code': 'sh.999999', 'dividOperateDate': day,
               'foreAdjustFactor': '1', 'backAdjustFactor': '1', 'adjustFacto': '1'}]
    factor_fields = json.loads((Path(__file__).resolve().parents[1] /
                                'config/baostock_dm01_sdk_schema_adapter_v2.json').read_text(encoding='utf-8'))['factor_raw_schema']

    class FakeSDK:
        query_daily_history_k_AStock = staticmethod(lambda **kwargs: None)
        query_daily_adjust_factor = staticmethod(lambda **kwargs: None)

    class FakeClient:
        logged_in = True
        sdk = FakeSDK()
        auth_mode = 'PUBLIC_ANONYMOUS'

        def query_rows(self, operation, method, **kwargs):
            if method == source.DAILY_METHOD:
                return daily, {'page_count': 1, 'provider_date': day,
                               'fields': list(source.DAILY_REQUIRED_FIELDS)}
            return factor, {'page_count': 1, 'provider_date': day, 'fields': factor_fields}

    sdk = {'package': 'baostock', 'version': '0.9.3',
           'installed_python_sources_sha256': '32bd19deb872561c8f9c40063de38df4fe4ab0f1073685538f627a9238686bfe'}
    monkeypatch.setattr(source, 'package_metadata', lambda: sdk)
    monkeypatch.setattr(source, 'runtime_acceptance_error', lambda *args, **kwargs: None)
    out = source.capture_baostock_daily_update(
        trade_date=day, client=FakeClient(), snapshot_root=tmp_path / 'snapshots',
        tdx_root=tmp_path / 'tdx', observed_at='2026-10-23T00:00:00+00:00',
        runtime_acceptance_manifest={'live_smoke': {'target_date': day}})
    assert out['status'] == 'BAOSTOCK_DAILY_SNAPSHOT_READY'
    assert out['schema_adaptations']['adjustment_factor']['field_map'] == {'adjustFacto': 'adjustFactor'}
    factor_op = out['query_operations'][1]
    assert set(factor_op['metadata']['fields']) == source.FACTOR_REQUIRED_FIELDS
    assert factor_op['metadata']['raw_fields'] == factor_fields
    assert factor_op['response_sha256'] != factor_op['normalized_rows_sha256']
    written = json.loads((tmp_path / 'snapshots/baostock/20261022' / out['snapshot_id'] /
                          'daily_update.json').read_text(encoding='utf-8'))
    assert written['adjustment_factor_rows'][0]['adjustFactor'] == '1'
    assert written['raw_daily_ohlc_authority'] == 'TDX_ONLY'
