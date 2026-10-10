"""Isolated future-interface fixtures; no historical or production episodes."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import pytest
from sector.episode_genesis_candidate_v2 import create, observe
from workbench_analysis.v4_14_replay_io import publish


@pytest.fixture
def genesis(tmp_path):
    now = datetime.now(timezone.utc)
    cutoff = now.isoformat()
    clock = (now-timedelta(seconds=2)).isoformat()
    day = now.astimezone(timezone(timedelta(hours=8))).date()
    sessions = [(day+timedelta(days=i)).isoformat() for i in range(6)]
    # Deliberately synthetic calendar including weekends, never a market sample.
    base = dict(version='test-v1', first_available=clock)
    documents = dict(
        membership=dict(T0=sessions[0], sector_id='B1', first_available=clock,
                        member_ids=['S1','S2'], member_set_asof='TEST_MEMBERS_V1', AS_RECORDED=True),
        conditions=dict(base, contract_id='TEST_INVALIDATION_V1', conditions=['PRICE_LT_1'], rule_id='invalid',
            rules={'invalid':dict(operator='LT', field_id='price',constant=1,producer='PRICE',
                time_role='TARGET_CUTOFF',quality_requirement=['ACCEPTED'],unknown_behavior='UNKNOWN')}),
        priority=dict(base,contract_id='TEST_PRIORITY_V1',scenario_priority=['BASE_BUILD','BREADTH_BUILD']),
        calendar=dict(base,contract_id='TEST_CALENDAR_V1',session_dates=sessions))
    refs = {key:publish(tmp_path,'inputs/'+key+'.json',doc) for key,doc in documents.items()}
    documents['capture']=dict(T0=sessions[0], sector_id='B1', first_available=clock,
        received_at=clock,captured_at=clock,evidence_class='SYNTHETIC_ISOLATED_TEST_ONLY',gaps=[],
        member_ids=['S1','S2'],membership=refs['membership'],matched_scenarios=['BREADTH_BUILD','BASE_BUILD'])
    refs['capture']=publish(tmp_path,'inputs/capture.json',documents['capture'])
    documents['price']=dict(T0=sessions[0],sector_id='B1',first_available=clock,price=2,source_capture=refs['capture'])
    refs['price']=publish(tmp_path,'inputs/price.json',documents['price'])
    kwargs={key+'_binding':ref for key,ref in refs.items()}
    kwargs.update(sector_id='B1',cutoff=cutoff)
    return tmp_path, documents, refs, kwargs, sessions


def test_creation_bound_e2e_and_missing_settlement(genesis):
    root,docs,refs,kwargs,sessions=genesis
    ep=create(root,**kwargs)
    assert create(root,**kwargs)==ep
    item=json.loads((root/ep['path']).read_bytes())
    assert item['scenario']=='BASE_BUILD' and item['member_ids']==['S1','S2']
    assert item['due_plan'][0]['due_date']==sessions[1]
    assert item['formal_D2']=='NOT_GRANTED' and item['evidence_class']=='SYNTHETIC_ISOLATED_TEST_ONLY'
    facts=dict(price=dict(value=.5,quality='ACCEPTED',producer='PRICE',time_role='TARGET_CUTOFF',max_source_date=sessions[0]))
    first=observe(root,episode_binding=ep,facts=facts,trade_date=sessions[0],calendar_binding=refs['calendar'])
    assert first['frozen_invalidation']['value']=='TRUE'
    assert all(item['status']=='PENDING' for item in first['followup'].values())
    due=observe(root,episode_binding=ep,trade_date=sessions[1],calendar_binding=refs['calendar'])
    assert due['frozen_invalidation']['value']=='UNKNOWN'
    assert due['followup']['1']['status']=='UNKNOWN' and due['followup']['3']['status']=='PENDING'
    assert observe(root,trade_date=sessions[0],calendar_binding=refs['calendar'])['status']=='NO_PRIOR_EPISODE'


@pytest.mark.parametrize('key,field,value,error',[
    ('membership','AS_RECORDED',False,'MEMBERSHIP'),
    ('membership','member_ids',['S1'],'MEMBERSHIP'),
    ('membership','member_ids',['S1','S1'],'MEMBERSHIP'),
    ('capture','evidence_class','RECONSTRUCTED_RESEARCH_ONLY','CURRENT_SOURCE'),
    ('capture','first_available','2999-01-01T00:00:00Z','FIRST_CLOCK'),
    ('capture','received_at','2999-01-01T00:00:00Z','CLOCK'),
    ('capture','matched_scenarios',['MADE_UP'],'SCENARIO'),
    ('conditions','version',None,'VERSIONED'),
    ('conditions','rules',{},'INVALIDATION_AST'),
    ('priority','scenario_priority',['BASE_BUILD','BASE_BUILD'],'SCENARIO'),
    ('calendar','session_dates',[],'CALENDAR'),
    ('price','price',True,'FINITE_PRICE'),
    ('price','source_capture',{},'MEMBERSHIP'),
])
def test_genesis_fail_closed(genesis,key,field,value,error):
    root,docs,refs,kwargs,sessions=genesis
    docs[key][field]=value
    kwargs[key+'_binding']=publish(root,'inputs/negative-'+key+'.json',docs[key])
    if key=='capture':
        docs['price']['source_capture']=kwargs['capture_binding']
        kwargs['price_binding']=publish(root,'inputs/negative-linked-price.json',docs['price'])
    with pytest.raises(ValueError,match=error):create(root,**kwargs)


def test_no_backfill_future_and_wrong_sha(genesis):
    root,docs,refs,kwargs,sessions=genesis
    with pytest.raises(ValueError,match='NO_BACKFILL'):create(root,**dict(kwargs,cutoff='2026-09-24T18:35:00+08:00'))
    with pytest.raises(ValueError,match='NO_BACKFILL'):create(root,**dict(kwargs,cutoff='2999-01-01T18:35:00+08:00'))
    kwargs['membership_binding']=dict(refs['membership'],sha256='0'*64)
    with pytest.raises(ValueError,match='REF_MISMATCH'):create(root,**kwargs)


def test_settlement_exact_bytes_and_episode_identity(genesis):
    root,docs,refs,kwargs,sessions=genesis
    eb=create(root,**kwargs);episode=json.loads((root/eb['path']).read_bytes())
    raw=publish(root,'inputs/settlement-original.json',dict(trade_date=sessions[1],value=.01))
    details=dict(first_available=kwargs['cutoff'],member_ids=episode['member_ids'])
    sb=publish(root,'inputs/settlement.json',dict(details,trade_date=sessions[1],episode_id=episode['episode_id'],source_binding=raw,value=.01))
    result=observe(root,episode_binding=eb,trade_date=sessions[1],calendar_binding=refs['calendar'],settlement={'1':sb})
    assert result['followup']['1']['status']=='COMPLETE' and result['followup_complete']=='UNKNOWN'
    wrong=publish(root,'inputs/settlement-wrong.json',dict(details,trade_date=sessions[1],episode_id='WRONG',source_binding=raw))
    assert observe(root,episode_binding=eb,trade_date=sessions[1],calendar_binding=refs['calendar'],settlement={'1':wrong})['followup']['1']['status']=='UNKNOWN'
    bad=dict(sb,sha256='0'*64)
    with pytest.raises(ValueError):observe(root,episode_binding=eb,trade_date=sessions[1],calendar_binding=refs['calendar'],settlement={'1':bad})
    with pytest.raises(ValueError,match='SETTLEMENT_CLOCK'):observe(root,episode_binding=eb,trade_date=sessions[0],calendar_binding=refs['calendar'],settlement={'1':sb})


def test_independent_average_rank_oracle_with_ties_and_unstable_delta():
    import pandas as pd
    from workbench_analysis.sector_cycle import _percentile, CONTRACT_VERSION
    from workbench_service.research_builder import _exact_cycle_delta
    values=[1,3,3,7,None]
    actual=_percentile(pd.Series(values)).tolist()
    known=[x for x in values if x is not None]
    expected=[(sum(x<v for x in known)+(sum(x==v for x in known)+1)/2)/len(known) if v is not None else None for v in values]
    assert actual[:4]==expected[:4] and pd.isna(actual[4])
    cfg={'thresholds':{'coverage':{'max_rank_universe_change':.1,'min_rank_intersection_union':.9}}}
    rows=[dict(trade_date=pd.Timestamp(day).date(),sector_id=sid,sector_type=typ,q5=q,contract_id=CONTRACT_VERSION)
        for day,sid,typ,q in [('2026-10-09','A','THEME',.25),('2026-10-09','B','THEME',1),
                             ('2026-10-14','A','THEME',1),('2026-10-14','B','THEME',.5),
                             ('2026-10-09','I','INDUSTRY',1),('2026-10-14','I','INDUSTRY',1),
                             ('2026-10-14','NEW','INDUSTRY',.5)]]
    result=_exact_cycle_delta(pd.DataFrame(rows),'2026-10-14','2026-10-09',cfg).set_index('sector_id')
    assert result.loc['A','dq5_3']==.75 and result.loc['B','dq5_3']==-.5
    assert pd.isna(result.loc['I','dq5_3']) and pd.isna(result.loc['NEW','dq5_3'])


@pytest.mark.parametrize('eligible,expected',[(True,'TRUE'),(None,'UNKNOWN')])
def test_non_amount_confirmation_remains_independent(eligible,expected):
    from sector.legacy_b2_r5 import evaluate_b2
    root=Path(__file__).resolve().parents[1]
    ast=json.loads((root/'config/v4_08_b2_machine_ast_r5.json').read_bytes())
    # Independent hand-calculated boundary vector from frozen phase2 current:
    # 5 members, 70% quote/cross coverage, positive median, 60% breadth,
    # excess >= .003, rank >= .8, >= 3 positive, max contribution <= .5.
    raw=dict(allowed_sector_type=True,normal_rank_eligible=eligible,total_member_count=5,
        quote_coverage=.7,market_ok=True,type_cross_section_coverage=.7,m1=.01,
        b1=.6,rel1=.003,p1=.8,positive_count=3,top1_positive_share=.5,amount_A=None)
    values={key:dict(value=value,quality='ACCEPTED' if value is not None else 'UNKNOWN') for key,value in raw.items()}
    result=evaluate_b2(values,ast,source_sha256=ast['source_sha256'],
        source_parameter_sha256=ast['source_parameter_sha256'],parameter_set_sha256=ast['parameter_set_sha256'])
    assert result['confirmed_diagnostic']==expected
    assert result['confirmed_raw']=='UNKNOWN' and result['warm_raw']=='UNKNOWN'
