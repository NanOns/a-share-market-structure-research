from copy import deepcopy
from types import SimpleNamespace

import pytest

from workbench_service.research_priority_r1 import build_priority


def cell(value, quality='KNOWN'):
    return {'value': value, 'quality': quality}


def stock(**changes):
    entity_id=changes.pop('entity_id', 'SEC-A')
    fields = {
        'core_price_damage': cell(False),
        'close': {**cell(12.0), 'adjustment_basis': 'TDX_NATIVE_AFFINE_QFQ_T0_COORDINATE'},
        'prior_low20': {**cell(10.0), 'adjustment_basis': 'TDX_NATIVE_AFFINE_QFQ_T0_COORDINATE'},
        'rps20': cell(65.0, 'OBSERVED'),
        'rps20_delta3': cell(0.1, 'OBSERVED'),
        'ret5': cell(0.02, 'OBSERVED'),
        'pos60': cell(0.5, 'OBSERVED'),
    }
    fields.update(changes)
    return {'entity_id': entity_id, 'trade_date': '2026-10-14', 'fields': fields}


def result(row):
    return build_priority('2026-10-14', 'token', [row], [], {}, 'core', 'sector', 'p'*64)['stocks']


def test_missing_close_is_not_replaced_by_prior_low20():
    row = stock()
    del row['fields']['close']
    got = result(row)
    assert got['rankable'] == 0
    assert got['not_rankable_rows'][0]['exclusion_reason'] == 'MISSING_INPUT'
    assert got['not_rankable_rows'][0]['unknown_inputs'] == ['close']
    assert got['not_rankable_rows'][0]['score'] is None


@pytest.mark.parametrize('value', [None, float('nan'), float('inf'), float('-inf'), True, 0, -1])
def test_invalid_close_never_receives_a_neutral_or_ranked_score(value):
    got = result(stock(close=cell(value)))
    assert got['rankable'] == 0
    assert got['not_rankable_rows'][0]['score'] is None
    assert 'close' in got['not_rankable_rows'][0]['invalid_inputs']


@pytest.mark.parametrize('value', [float('nan'), float('inf'), float('-inf'), True])
def test_nonfinite_or_boolean_rps_is_not_ranked(value):
    got = result(stock(rps20=cell(value, 'OBSERVED')))
    assert got['rankable'] == 0
    assert got['not_rankable_rows'][0]['invalid_inputs'] == ['rps20']


def test_bad_quality_wrong_date_and_domain_values_are_explainable():
    cases = [
        stock(rps20=cell(50, 'SOURCE_INCOMPLETE')),
        stock(close={'value': 12, 'quality': 'KNOWN', 'as_of': '2026-10-13',
                     'adjustment_basis': 'TDX_NATIVE_AFFINE_QFQ_T0_COORDINATE'}),
        stock(pos60=cell(1.1, 'OBSERVED')),
        stock(rps20=cell(101, 'OBSERVED')),
        stock(rps20_delta3=cell(100.01, 'OBSERVED')),
        stock(ret5=cell(-1, 'OBSERVED')),
    ]
    for row, field in zip(cases, ['rps20', 'close', 'pos60', 'rps20', 'rps20_delta3', 'ret5']):
        item = result(row)['not_rankable_rows'][0]
        assert item['score'] is None
        assert item['invalid_inputs'] == [field]
        assert item['exclusion_reason'] == 'INVALID_INPUT'


def test_mixed_or_missing_price_coordinates_are_not_scored():
    row=stock()
    row['fields']['close']['adjustment_basis']='RAW_UNADJUSTED'
    item=result(row)['not_rankable_rows'][0]
    assert item['score'] is None
    assert 'price_coordinate:close,prior_low20' in item['invalid_inputs']
    assert item['exclusion_reason']=='INVALID_INPUT'


def test_eligible_score_and_sort_contract_remain_unchanged():
    rows = [stock(entity_id='SEC-B'), stock(entity_id='SEC-A')]
    got = build_priority('2026-10-14', 'token', rows, [], {}, 'core', 'sector', 'p'*64)['stocks']
    assert got['rankable'] == 2
    assert [row['entity_id'] for row in got['all_items']] == ['SEC-A', 'SEC-B']
    # delta and return are capped by the existing R1 scoring contract.
    assert [row['score'] for row in got['all_items']] == [10.0, 10.0]


def test_focus_reason_cache_key_changes_when_candidate_binding_changes(monkeypatch, tmp_path):
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    import workbench_analysis.r6_reason_attribution as attribution

    calls = []
    monkeypatch.setattr(attribution, 'candidate_d0_reason_attribution',
                        lambda root, candidate, day, *, focus_security_ids: calls.append(candidate['owners'][day]['focus']['sha256']) or {'status': 'READY'})
    candidate = {'accepted_trade_date': '2026-10-14', 'owners': {'2026-10-14': {'focus': {'sha256': 'a'}}}}
    api = SimpleNamespace(token='same-token', candidate=candidate, cache={}, root=tmp_path)
    bff = object.__new__(CoreProductBFFR1)
    bff.api = api
    first = bff._candidate_focus_reason_attribution('2026-10-14', ['S1'])
    assert bff._candidate_focus_reason_attribution('2026-10-14', ['S1']) is first
    api.candidate = deepcopy(candidate)
    api.candidate['owners']['2026-10-14']['focus']['sha256'] = 'b'
    second = bff._candidate_focus_reason_attribution('2026-10-14', ['S1'])
    assert second is not first
    assert calls == ['a', 'b']


def test_lifecycle_cache_key_changes_for_same_token_candidate_revision(monkeypatch):
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    import sector.candidate_lifecycle_v1 as lifecycle

    calls = []
    monkeypatch.setattr(lifecycle, 'build_candidate_lifecycle',
                        lambda root, candidate, source_root: calls.append(candidate['owners']['2026-10-14']['sector']['sha256']) or {'ready': True})
    candidate = {'accepted_trade_date': '2026-10-14', 'published_sessions': [],
                 'owners': {'2026-10-14': {'sector': {'sha256': 'a'}}}}
    api = SimpleNamespace(token='same-token', candidate=candidate, cache={}, root='candidate')
    bff = object.__new__(CoreProductBFFR1)
    bff.api = api
    bff._candidate_lifecycle()
    bff._candidate_lifecycle()
    api.candidate = deepcopy(candidate)
    api.candidate['owners']['2026-10-14']['sector']['sha256'] = 'b'
    bff._candidate_lifecycle()
    assert calls == ['a', 'b']


def test_s01_cache_namespaces_isolate_token_day_producer_parameters_and_members():
    from workbench_service.core_product_bff_r1 import (
        _candidate_focus_reason_cache_key,_candidate_lifecycle_cache_key)

    candidate={'accepted_trade_date':'2026-10-14','owners':{'2026-10-14':{'sector':{'sha256':'a'}}}}
    base=_candidate_lifecycle_cache_key('token-a',candidate,'producer-a','params-a')
    assert base!=_candidate_lifecycle_cache_key('token-b',candidate,'producer-a','params-a')
    assert base!=_candidate_lifecycle_cache_key('token-a',candidate,'producer-b','params-a')
    assert base!=_candidate_lifecycle_cache_key('token-a',candidate,'producer-a','params-b')
    revised=deepcopy(candidate); revised['owners']['2026-10-14']['sector']['sha256']='b'
    assert base!=_candidate_lifecycle_cache_key('token-a',revised,'producer-a','params-a')

    focus=_candidate_focus_reason_cache_key('token-a',candidate,'2026-10-14',['S2','S1'])
    assert focus==_candidate_focus_reason_cache_key('token-a',candidate,'2026-10-14',['S1','S2'])
    assert focus!=_candidate_focus_reason_cache_key('token-b',candidate,'2026-10-14',['S1','S2'])
    assert focus!=_candidate_focus_reason_cache_key('token-a',candidate,'2026-10-13',['S1','S2'])
    assert focus!=_candidate_focus_reason_cache_key('token-a',candidate,'2026-10-14',['S1','S3'])
    assert focus!=_candidate_focus_reason_cache_key('token-a',revised,'2026-10-14',['S1','S2'])


def test_market_cache_hit_is_diagnostic_not_business_payload(monkeypatch):
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    import workbench_analysis.r6_candidate_market_stress as stress

    monkeypatch.setattr(stress, 'candidate_market_stress_identity', lambda root, candidate: 'same-source')
    monkeypatch.setattr(stress, 'build_candidate_market_stress', lambda root, candidate: {'T0': '2026-10-14', 'risk': 0.2})
    api = SimpleNamespace(token='same-token', candidate={}, cache={}, root='candidate')
    bff = object.__new__(CoreProductBFFR1)
    bff.api = api
    cold, cold_diag = bff._candidate_market_stress()
    hot, hot_diag = bff._candidate_market_stress()
    assert cold == hot == {'T0': '2026-10-14', 'risk': 0.2}
    assert cold_diag['cache_hit'] is False and hot_diag['cache_hit'] is True
    assert 'cache_hit' not in cold and 'cache_hit' not in hot


def test_source_bytes_changed_without_binding_revision_fails_closed(tmp_path):
    import hashlib
    from workbench_analysis.r6_candidate_market_stress import _checked

    path=tmp_path/'owner.jsonl.gz'
    path.write_bytes(b'original owner bytes')
    binding={'path': path.name, 'bytes': path.stat().st_size,
             'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    path.write_bytes(b'changed owner bytes')
    with pytest.raises(ValueError, match='BYTES_OR_SHA_MISMATCH'):
        _checked(tmp_path,binding)


def test_warm_priority_cache_source_integrity_rechecks_current_owner_bytes(tmp_path):
    import hashlib
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1

    owners={}
    for domain in ('core','adjusted','sector'):
        path=tmp_path/f'{domain}.json'
        path.write_bytes((domain+'-bytes').encode())
        raw=path.read_bytes()
        owners[domain]={'path':path.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    bff=object.__new__(CoreProductBFFR1)
    bff.api=SimpleNamespace(root=tmp_path,candidate={'owners':{'2026-10-14':owners}})
    bff._verify_candidate_priority_bindings('2026-10-14')
    (tmp_path/'adjusted.json').write_bytes(b'tampered bytes')
    with pytest.raises(ValueError,match='CORRECTED_INPUT_DIGEST_MISMATCH'):
        bff._verify_candidate_priority_bindings('2026-10-14')
