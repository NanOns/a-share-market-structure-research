"""Temporal attack fixtures are isolated; never production history."""
import copy
import pytest
from workbench_service.replay_views import temporal_projection,cutoff,timestamp,selected,replay
from workbench_service.current_v4_context import canonical,digest,SourceInvalid
from tests.test_fp02_research_snapshot import reader

def frozen():
    return dict(AS_RECORDED=True,first_available_proven=True,model_known_at='2026-09-28T10:00:00+08:00',items=[dict(entity_id='A',symbol='SH.A',fields={'close':dict(value=10,effective_date='2026-09-28',known_at='2026-09-28T15:05:00+08:00',publication_date='2026-09-28T15:01:00+08:00',model_namespace='TEST_ONLY_V1')})])

@pytest.mark.parametrize('field,future',[('known_at','2026-09-29T00:00:00+08:00'),('publication_date','2026-09-29T00:00:00+08:00'),('effective_date','2026-09-29'),('known_at',None),('known_at','2026-09-28T15:00:00')])
def test_future_and_unproven_cell_fail_closed(field,future):
    x=frozen();x['items'][0]['fields']['close'][field]=future
    assert temporal_projection(x,'2026-09-28')==[]

def test_future_outcome_membership_and_state_do_not_change_t0_hash():
    base=frozen();expected=digest(canonical(temporal_projection(base,'2026-09-28')))
    attacked=copy.deepcopy(base)
    for name in ('outcome','membership','maturity'):
        attacked['items'][0]['fields'][name]=dict(value='FUTURE_SENTINEL',effective_date='2026-09-29',known_at='2026-09-29T09:00:00+08:00',publication_date='2026-09-29T09:00:00+08:00',model_namespace='TEST_ONLY_V1')
    attacked['items'].append(dict(entity_id='FUTURE',fields=copy.deepcopy(attacked['items'][0]['fields'])))
    attacked['items'][-1]['fields'].pop('close')
    actual=temporal_projection(attacked,'2026-09-28')
    assert digest(canonical(actual))==expected
    assert 'FUTURE_SENTINEL' not in str(actual)

@pytest.mark.parametrize('changes',[{'AS_RECORDED':False},{'first_available_proven':False},{'model_known_at':'2026-09-29T00:00:00+08:00'},{'model_known_at':None}])
def test_reconstruction_or_future_model_never_admitted(changes):
    x=frozen();x.update(changes)
    assert temporal_projection(x,'2026-09-28')==[]

def test_timezone_boundary_is_shanghai():
    x=frozen();c=x['items'][0]['fields']['close'];c['known_at']='2026-09-28T15:59:59Z'
    assert temporal_projection(x,'2026-09-28')
    c['known_at']='2026-09-28T16:00:00Z'
    assert not temporal_projection(x,'2026-09-28')

def test_missing_history_and_context_lock(reader):
    assert replay(reader,{'as_of':'2026-09-18'})['status']=='PIT_NOT_AVAILABLE'
    reader.manifest['domain_features']={'replay':dict(catalog=[dict(as_of='2026-09-29',snapshot={'sha256':'a'*64})])}
    with pytest.raises(SourceInvalid,match='SNAPSHOT_DATE_OR_VERSION'):selected(reader,{'as_of':'2026-09-29','snapshot_token':'fp12-'+'b'*64})
    with pytest.raises(ValueError,match='FUTURE_AS_OF'):selected(reader,{'as_of':'2026-10-01'})

def test_later_series_identity_and_bars_do_not_change_selected_values_hash(reader,monkeypatch):
    import workbench_service.replay_views as module
    authority=dict(catalog=[dict(as_of='2026-09-28',snapshot={'sha256':'a'*64})],sources={'series':{'sha256':'b'*64}})
    reader.manifest['domain_features']={'replay':authority}
    snapshot=frozen();snapshot['knowledge_lineage']='TEST_ONLY';snapshot['sources']={}
    monkeypatch.setattr(module,'read_snapshot',lambda *_:snapshot)
    bars=[dict(trade_date='2026-09-28',close=10)]
    monkeypatch.setattr(module,'chart',lambda *_:{'items':bars})
    query={'as_of':'2026-09-28','view':'corrected','left':'A'}
    before=replay(reader,query)
    authority['sources']['series']={'sha256':'c'*64}
    bars.append(dict(trade_date='2026-09-29',close=999))
    after=replay(reader,query)
    assert before['result_hash']==after['result_hash']
    assert after['history']['items']==[dict(trade_date='2026-09-28',close=10)]
