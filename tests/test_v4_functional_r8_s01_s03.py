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


def test_distinct_exact_affine_basis_ids_are_not_collapsed_to_display_aliases():
    row=stock()
    row['fields']['close']['adjustment_basis']='TDX_NATIVE_AFFINE_QFQ_V0_3_EXACT_TARGET_COORDINATE:SERIES-A'
    row['fields']['prior_low20']['adjustment_basis']='TDX_NATIVE_AFFINE_QFQ_V0_3_EXACT_TARGET_COORDINATE:SERIES-B'
    item=result(row)['not_rankable_rows'][0]
    assert item['score'] is None
    assert 'price_coordinate:close,prior_low20' in item['invalid_inputs']


def test_exact_price_coordinate_requires_adjusted_revision_to_match_core_basis():
    from workbench_service.core_product_bff_r1 import _exact_price_coordinate
    revision='a'*64;base='TDX_NATIVE_AFFINE_QFQ_V0_3_EXACT_TARGET_COORDINATE'
    core={'price_basis_id':base+':'+revision}
    adjusted={'price_basis':base,'adjustment_source_revision':revision,'adjustment_readiness':'READY'}
    assert _exact_price_coordinate(core,adjusted)==core['price_basis_id']
    assert _exact_price_coordinate(core,{**adjusted,'adjustment_source_revision':'b'*64}) is None
    assert _exact_price_coordinate(core,{**adjusted,'price_basis':'TDX_NATIVE_AFFINE_QFQ_T0_COORDINATE'}) is None


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
    import hashlib
    refs={}
    for domain in ('focus','prewatch','forward'):
        path=tmp_path/f'{domain}.json';path.write_bytes(domain.encode())
        refs[domain]={'path':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    candidate = {'accepted_trade_date': '2026-10-14','published_sessions':['2026-10-13','2026-10-14'],
                 'owners': {'2026-10-13': {'focus':dict(refs['focus'])},
                            '2026-10-14': {k:dict(v) for k,v in refs.items()}}}
    api = SimpleNamespace(token='same-token', candidate=candidate, cache={}, root=tmp_path)
    bff = object.__new__(CoreProductBFFR1)
    bff.api = api
    first = bff._candidate_focus_reason_attribution('2026-10-14', ['S1'])
    assert bff._candidate_focus_reason_attribution('2026-10-14', ['S1']) is first
    api.candidate = deepcopy(candidate)
    api.candidate['revision'] = 'revised-candidate-metadata'
    second = bff._candidate_focus_reason_attribution('2026-10-14', ['S1'])
    assert second is not first
    assert calls == [refs['focus']['sha256'],refs['focus']['sha256']]


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
    api.candidate['revision'] = 'revised-candidate-metadata'
    bff._candidate_lifecycle()
    assert calls == ['a', 'a'] and len(calls)==2


@pytest.mark.parametrize('domain',['prewatch','focus','forward','prior_focus'])
def test_warm_focus_reason_cache_rechecks_every_current_source(domain,tmp_path,monkeypatch):
    import hashlib
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    import workbench_analysis.r6_reason_attribution as attribution
    refs={}
    for name in ('prewatch','focus','forward'):
        path=tmp_path/f'{name}.gz';path.write_bytes((name+' bytes').encode())
        raw=path.read_bytes();refs[name]={'path':path.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    prior=tmp_path/'prior-focus.gz';prior.write_bytes(b'prior focus');raw=prior.read_bytes()
    prior_ref={'path':prior.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    monkeypatch.setattr(attribution,'candidate_d0_reason_attribution',lambda *a,**k:{'status':'READY'})
    candidate={'accepted_trade_date':'2026-10-14','published_sessions':['2026-10-13','2026-10-14'],
        'owners':{'2026-10-13':{'focus':prior_ref},'2026-10-14':refs}}
    bff=object.__new__(CoreProductBFFR1);bff.api=SimpleNamespace(root=tmp_path,token='t',candidate=candidate,cache={})
    bff._candidate_focus_reason_attribution('2026-10-14',['S1'])
    ref=prior_ref if domain=='prior_focus' else refs[domain]
    path=tmp_path/ref['path'];path.write_bytes(b'tampered '+domain.encode())
    with pytest.raises(ValueError,match='CORRECTED_INPUT_DIGEST_MISMATCH'):
        bff._candidate_focus_reason_attribution('2026-10-14',['S1'])


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
    for domain in ('core','adjusted','sector','rotation','focus','prewatch','forward'):
        path=tmp_path/f'{domain}.json'
        path.write_bytes((domain+'-bytes').encode())
        raw=path.read_bytes()
        owners[domain]={'path':path.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    bff=object.__new__(CoreProductBFFR1)
    bff.api=SimpleNamespace(root=tmp_path,candidate={'published_sessions':['2026-10-14'],'owners':{'2026-10-14':owners}})
    bff._verify_candidate_priority_bindings('2026-10-14')
    (tmp_path/'adjusted.json').write_bytes(b'tampered bytes')
    with pytest.raises(ValueError,match='CORRECTED_INPUT_DIGEST_MISMATCH'):
        bff._verify_candidate_priority_bindings('2026-10-14')


def test_project_cache_key_binds_candidate_revision_and_rechecks_warm_owner_bytes(tmp_path):
    import hashlib,json
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1,_candidate_revision_digest
    owners={}
    for domain in ('raw','core','adjusted','focus','profile'):
        path=tmp_path/f'{domain}.json';path.write_bytes(domain.encode())
        raw=path.read_bytes();owners[domain]={'path':path.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    config=tmp_path/'config';config.mkdir();(config/'v4_03_field_registry_v1.json').write_text('{}')
    (config/'v4_04_field_registry_v2.json').write_text('{}');(config/'v4_08_sector_field_registry_r5.json').write_text('{}')
    names=tmp_path/'names.json';names.write_text('{}');raw=names.read_bytes()
    names_ref={'path':names.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    (config/'v4_display_names_authority_v1.json').write_text(json.dumps({'source':names_ref}))
    day='2026-10-14';candidate={'accepted_trade_date':day,'owners':{day:owners}}
    api=SimpleNamespace(root=tmp_path,token='same-token',candidate=candidate,cache={})
    bff=object.__new__(CoreProductBFFR1);bff.api=api
    from workbench_service.core_product_bff_r1 import _product_projection_config_digest
    key=('product-project-v3',api.token,_candidate_revision_digest(candidate),day,'stocks',_product_projection_config_digest(tmp_path))
    api.cache[key]=[{'cached':True}]
    assert bff.project('stocks',day)==[{'cached':True}]
    revised=deepcopy(candidate);revised['revision']='valid-new-candidate-metadata'
    revised_key=('product-project-v3',api.token,_candidate_revision_digest(revised),day,'stocks',_product_projection_config_digest(tmp_path))
    assert revised_key!=key
    (tmp_path/'adjusted.json').write_bytes(b'tampered')
    with pytest.raises(ValueError,match='CORRECTED_INPUT_DIGEST_MISMATCH'):
        bff.project('stocks',day)


@pytest.mark.parametrize('domain',['sector','rotation'])
def test_warm_priority_cache_rechecks_prior_lifecycle_owners(domain,tmp_path):
    import hashlib
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    owners={}
    for day in ('2026-10-13','2026-10-14'):
        owners[day]={}
        for name in ('core','adjusted','sector','rotation','focus','prewatch','forward'):
            path=tmp_path/f'{day}-{name}.json';path.write_bytes((day+name).encode())
            raw=path.read_bytes();owners[day][name]={'path':path.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    bff=object.__new__(CoreProductBFFR1)
    bff.api=SimpleNamespace(root=tmp_path,candidate={'published_sessions':['2026-10-13','2026-10-14'],'owners':owners})
    bff._verify_candidate_priority_bindings('2026-10-14')
    ref=owners['2026-10-13'][domain];(tmp_path/ref['path']).write_bytes(b'tampered prior lifecycle owner')
    with pytest.raises(ValueError,match='CORRECTED_INPUT_DIGEST_MISMATCH'):
        bff._verify_candidate_priority_bindings('2026-10-14')


def test_sector_lifecycle_requires_dated_quality_and_producer_provenance():
    from workbench_service.research_priority_r1 import build_priority
    day='2026-10-14';source={'input_digest':'a'*64,'producer_sha256':'b'*64,
        'parameter_sha256':'c'*64,'source_bindings':{'2026-10-14':{'sector':{'sha256':'d'*64}}}}
    sector={'entity_id':'SEC-A','trade_date':day,'fields':{
        'maturity':{'value':'MATURE','quality':'KNOWN','as_of':day,'source':source},
        'health':{'value':'NONE','quality':'KNOWN','as_of':day,'source':source},
        'sector_rs5':{'value':1.0,'quality':'OBSERVED','as_of':day},
        'sector_rs20':{'value':1.0,'quality':'OBSERVED','as_of':day},
        'output_state':{'value':'ROTATION_IN','quality':'KNOWN','as_of':day}}}
    def run(item):return build_priority(day,'t',[],[item],{},'s','s','p'*64)['sectors']
    assert run(sector)['rankable']==1
    tampered=deepcopy(sector);tampered['fields']['health']['as_of']='2026-10-13'
    result=run(tampered)
    assert result['rankable']==0 and result['not_rankable_rows'][0]['invalid_inputs']==['health']
    missing=deepcopy(sector);missing['fields']['maturity'].pop('source')
    result=run(missing)
    assert result['rankable']==0 and result['not_rankable_rows'][0]['invalid_inputs']==['maturity']


def test_s04_d0_candidate_predicate_digest_does_not_claim_source_seal(tmp_path):
    import gzip,hashlib,json
    from workbench_analysis.r6_reason_attribution import candidate_d0_reason_attribution
    row={'trade_date':'2026-10-14','confirmation':{'confirmation_status':'FALSE',
        'source_sha256':'a'*64,'scenario_evidence':[{'scenario':'LAUNCH_CONFIRM','status':'FALSE','checks':{},'unknown_reasons':[]},
        {'scenario':'RECOVERY_TURN','status':'TRUE','checks':{},'unknown_reasons':[]},
        {'scenario':'STRONG_PULLBACK','status':'UNKNOWN','checks':{},'unknown_reasons':['PRIOR_EPISODE_UNKNOWN']},
        {'scenario':'TREND_CONTINUE','status':'UNKNOWN','checks':{},'unknown_reasons':['SAME_DAY_DIAGNOSTIC_ONLY']}]}}
    raw=gzip.compress(json.dumps([row]).encode());p=tmp_path/'prewatch.gz';p.write_bytes(raw)
    ref={'path':p.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    got=candidate_d0_reason_attribution(tmp_path,{'accepted_trade_date':'2026-10-14','published_sessions':['2026-10-14'],
        'owners':{'2026-10-14':{'prewatch':ref}}},'2026-10-14')
    governance=got['scenario_governance']['scenarios']
    assert got['status']=='READY'
    assert governance['LAUNCH_CONFIRM']['status']=='OPEN_SOURCE_SEAL_METADATA_MISSING'
    assert governance['RECOVERY_TURN']['availability_time_proven'] is False
    assert governance['STRONG_PULLBACK']['role']=='NOT_IN_FORMAL_D0_AGGREGATION'
    assert governance['TREND_CONTINUE']['role']=='NOT_IN_FORMAL_D0_AGGREGATION'
    assert got['D0_status_values_unchanged'] if 'D0_status_values_unchanged' in got else got['scenario_governance']['D0_status_values_unchanged']


def test_s02_breadth_formula_comparison_preserves_zero_and_shared_denominator():
    from workbench_analysis.r6_candidate_market_stress import candidate_breadth_formula_comparison
    values=candidate_breadth_formula_comparison([(0.1,0.0),(0.0,0.0),(-0.1,0.1)],boundary=0.05)
    assert values['evaluable']==3 and values['zero_current']==1 and values['zero_comparison']==2
    assert values['positive_indicator']['value']==pytest.approx(0.0)
    assert values['signed']['value']==pytest.approx(-1/3)
    assert values['positive_indicator']['classification']=='STABLE'
    assert values['signed']['classification']=='DETERIORATING'
    empty=candidate_breadth_formula_comparison([],boundary=0.05)
    assert empty['evaluable']==0 and empty['signed']['classification']=='UNKNOWN'
