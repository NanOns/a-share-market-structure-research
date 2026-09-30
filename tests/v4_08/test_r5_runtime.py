from pathlib import Path
import copy,json,hashlib
import pytest
from sector.native_r5 import common_delta,retention,build_native
from sector.rotation_r5 import resolve_package,evaluate_b0,advance_rotation
from sector.legacy_b2_r5 import evaluate_b2,build_b2_inputs
from sector.machine_ast_r3 import ast_digest,evaluate_ast

ROOT=Path(__file__).resolve().parents[2]
def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))
def package():
    path=ROOT/'config/v4_08_algorithm_parameter_set_r5.json'
    params=read(path.relative_to(ROOT));registry=read('config/v4_08_sector_field_registry_r5.json')
    contract=read('config/v4_08_rotation_core_contract_r5.json')
    values,fields=resolve_package(contract,params,path.read_bytes(),registry)
    return params,registry,contract,values,fields
def fact(value):return {'value':value,'quality':'ACCEPTED','max_source_date':'2026-09-30'}
def record(value,date='2026-09-30'):return {'trade_date':date,'fields':{'ret1':{**fact(value),'max_source_date':date}}}

def test_common_member_does_not_count_membership_changes():
    value,reason,meta=common_delta({'A','B'},{'B','C'},{'A':record(1),'B':record(-1)},{'B':record(1,'2026-09-29'),'C':record(-1,'2026-09-29')},'ret1','2026-09-30','2026-09-29',lambda v:int(v>0))
    assert value==-1 and meta['common_count']==1 and meta['membership_entered_count']==1
    assert meta['endpoint_known_count']==1

def test_missing_history_not_current_membership_replay():
    value,reason,meta=common_delta({'A'},None,{}, {},'ret1','2026-09-30',None,lambda v:int(v>0))
    assert value is None and reason=='NO_PRIOR_ACCEPTED_PIT_HISTORY' and meta['prior_member_count'] is None

def test_absent_target_publication_does_not_create_zero_quote_coverage():
    params,*_=package()
    members=[dict(sector_type='INDUSTRY',sector_id='SYNTHETIC',security_id='MEMBER',snapshot_id='SNAPSHOT',target_trade_date='2026-09-30')]
    row=build_native(members,{},target='2026-09-30',snapshot_id='SNAPSHOT',publication_id='FIXTURE',parameter_set=params,source_bindings={})[0]
    assert row['fields']['sector_quote_coverage']['value'] is None
    assert row['fields']['sector_quote_coverage']['quality']=='UNKNOWN'
    registry={f['field_id']:f for f in read('config/v4_08_sector_field_registry_r5.json')['fields']}
    for field,item in row['fields'].items():
        assert registry[field]['producer']==item['producer']
        assert registry[field]['time_role']==item['time_role']

def test_native_midrank_is_section_10a0_not_legacy_display_percentile():
    params,*_=package();members=[];current={}
    for sector,ret in [('FIRST',.1),('SECOND',.1)]:
        for index in range(5):
            member=f'{sector}_{index}'
            members.append(dict(sector_type='INDUSTRY',sector_id=sector,security_id=member,snapshot_id='SNAPSHOT',target_trade_date='2026-09-30'))
            current[member]={'trade_date':'2026-09-30','fields':{f:fact(v) for f,v in {'ret1':.01,'ret5':ret,'ret20':ret,'ret60':ret,'close_minus_ma20':1,'amount':10,'amount_ratio20':1,'rps20':85}.items()}}
    result=build_native(members,current,target='2026-09-30',snapshot_id='SNAPSHOT',publication_id='FIXTURE',parameter_set=params,source_bindings={})
    assert {r['fields']['sector_rs5_pct']['value'] for r in result}=={50}
    assert result[0]['fields']['sector_rs5']['value']==.1
    assert result[0]['fields']['breadth_ret1']['value']==1
    assert result[0]['fields']['ma20_width']['value']==1
    assert result[0]['fields']['top1_concentration']['value']==.2
    assert result[0]['fields']['participation_proxy']['value']==1
    single=build_native(members[:5],current,target='2026-09-30',snapshot_id='SNAPSHOT',publication_id='FIXTURE',parameter_set=params,source_bindings={})
    assert single[0]['fields']['sector_rs5_pct']['value'] is None

@pytest.mark.parametrize('old,now,expected',[([],{},'NOT_APPLICABLE'),(['A'],{},'UNKNOWN'),(['A','B'],{'A':True,'B':False},'ACCEPTED')])
def test_frozen_denominator(old,now,expected):assert retention(old,now)[1]==expected

def test_parameter_instance_digest_rejects_unbound_mutation():
    params,registry,contract,values,fields=package()
    data=(ROOT/'config/v4_08_algorithm_parameter_set_r5.json').read_bytes()+b' '
    with pytest.raises(ValueError,match='DIGEST'):resolve_package(contract,params,data,registry)

@pytest.mark.parametrize('pid,field,rule',[
    ('V4_08_EARLY_SEED_RETENTION_MIN','base_seed_retention','early_retained'),
    ('V4_08_EARLY_BREADTH_RETENTION_MIN','breadth_retention','early_retained'),
    ('V4_08_EARLY_BREADTH_DELTA_MIN','breadth_delta1','early_retained'),
    ('V4_08_EARLY_TOP1_CONCENTRATION_MAX','top1_concentration','early_retained'),
    ('V4_08_MATURE_STRONG_RETENTION_MIN','strong_member_retention_1','mature_retained')])
def test_all_five_parameters_change_runtime_predicates(pid,field,rule):
    _,_,contract,values,fields=package()
    raw={'basket_cumulative_return':.1,'base_seed_retention':1,'breadth_retention':1,'breadth_delta1':.1,'top1_concentration':.1,'strong_prev':5,'strong_member_retention_1':1}
    if field=='base_seed_retention':raw['breadth_retention']=0
    if field=='breadth_retention':raw['base_seed_retention']=0
    raw[field]=values[pid]
    facts={f:{**fields[f],'value':v,'quality':'ACCEPTED'} for f,v in raw.items()}
    assert evaluate_ast(rule,contract['rules'],facts,values) is True
    changed={**values,pid:values[pid]+(.01 if field!='top1_concentration' else -.01)}
    assert evaluate_ast(rule,contract['rules'],facts,changed) is False

def test_b0_missing_seed_is_unknown_even_when_safety_false():
    c=read('config/v4_08_sector_prewatch_contract_r5.json')
    _,_,_,v,_=package()
    assert evaluate_b0({'fields':{}},c,v)['output_state']=='UNKNOWN'

def test_first_pit_rotation_unknown():
    params,registry,contract,values,_=package()
    result=advance_rotation({'target_trade_date':'2026-09-30','sector_id':'TEST','membership_snapshot_id':'S','member_ids':[],'fields':{}},{},prior_publication=None,prior_members=None,prior_core=None,calendar_sessions=['2026-09-30'],contract=contract,registry=registry,parameters=values)
    assert result['output_state']=='UNKNOWN' and result['episode'] is None
    assert result['reason_codes']==['NO_PRIOR_ACCEPTED_PIT_HISTORY']

def test_pulse_then_in_with_empty_prior_strong_cohort_and_degraded_seed():
    _,registry,contract,values,fields=package()
    target='2026-09-30';old='2026-09-29';members=['A','B','C','D','E']
    raw={'membership_ready':True,'sector_member_count':5,'sector_quote_coverage':1,'dq5':12,'breadth_delta1':.1,'top1_concentration':.2,'net_entered_count':1}
    native={'target_trade_date':target,'sector_id':'TEST','membership_snapshot_id':'S','member_ids':members,'fields':{f:{**fields[f],'value':v,'quality':'ACCEPTED'} for f,v in raw.items()}}
    def core(date,close):return {m:{'trade_date':date,'price_basis_id':'ACCEPTED_SYNTHETIC_COMMON_COORDINATE','fields':{f:{**fact(v),'max_source_date':date} for f,v in {'close':close,'ret1':.1,'rps20':20}.items()}} for m in members}
    prior={'acceptance':'ACCEPTED','target_trade_date':old,'membership_snapshot_id':'PREV','output_state':'NONE','native_fields':{'dq5':{'value':0}},'episode':None}
    pulse=advance_rotation(native,core(target,11),prior_publication=prior,prior_members=members,prior_core=core(old,10),calendar_sessions=[old,target,'2026-10-01'],contract=contract,registry=registry,parameters=values,prior_maturity='NONE')
    assert pulse['output_state']=='ROTATION_PULSE'
    assert pulse['episode']['frozen_basket']==members and pulse['episode']['pulse_baseline']['A']==10
    nxt={**native,'target_trade_date':'2026-10-01'}
    accepted_prior={**pulse,'acceptance':'ACCEPTED','target_trade_date':target,'membership_snapshot_id':'S'}
    result=advance_rotation(nxt,core('2026-10-01',12),prior_publication=accepted_prior,prior_members=members,prior_core=core(target,11),calendar_sessions=[old,target,'2026-10-01'],contract=contract,registry=registry,parameters=values,prior_maturity='NONE')
    assert result['output_state']=='ROTATION_IN'
    assert result['predicates']['mature_retained']['state']=='NOT_APPLICABLE'
    assert result['fields']['base_seed_retention']['quality']=='UNKNOWN'
    assert result['fields']['breadth_retention']['value']==1
    changed=core('2026-10-01',12);changed['A']['price_basis_id']='DIFFERENT_COORDINATE'
    invalid=advance_rotation(nxt,changed,prior_publication=accepted_prior,prior_members=members,prior_core=core(target,11),calendar_sessions=[old,target,'2026-10-01'],contract=contract,registry=registry,parameters=values,prior_maturity='NONE')
    assert invalid['fields']['basket_cumulative_return']['value'] is None

def b2(values):
    ast=read('config/v4_08_b2_machine_ast_r5.json')
    def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    return evaluate_b2({k:fact(v) for k,v in values.items()},ast,source_sha256=sha(ast['source_path']),source_parameter_sha256=sha(ast['source_parameter_path']),parameter_set_sha256=sha('config/v4_08_algorithm_parameter_set_r5.json'))

def positive():return dict(allowed_sector_type=True,normal_rank_eligible=True,total_member_count=10,quote_coverage=1,market_ok=True,type_cross_section_coverage=1,m1=.02,b1=.8,rel1=.01,p1=.9,positive_count=8,top1_positive_share=.2)

@pytest.mark.parametrize('patch,expected',[({},'TRUE'),({'m1':-.01},'FALSE'),({'b1':.6,'p1':.8,'rel1':.003,'positive_count':3,'top1_positive_share':.5},'TRUE'),({'market_ok':False,'m1':-.01},'UNKNOWN'),({'top1_positive_share':.50001},'FALSE')])
def test_independent_b2_golden_current(patch,expected):
    result=b2({**positive(),**patch})
    assert result['confirmed_raw']==expected
    assert result['warm_raw']=='UNKNOWN'

def test_b2_unknown_not_false():
    values=positive();values.pop('b1')
    assert b2(values)['confirmed_raw']=='UNKNOWN'

def test_actual_legacy_current_function_against_pit_adapter():
    import pandas as pd
    from workbench_analysis.sector_attention import build_sector_current
    cfg=read('config/research_attention_v3.yaml');native=[];current={};members=[]
    for sector in range(5):
        ids=[f'MEMBER_{sector}_{member}' for member in range(5)]
        for member in ids:
            value=.01*(sector+1)
            current[member]=record(value)
            members.append(dict(sector_id=f'SECTOR_{sector}',security_id=member,trade_date='2026-09-30',ret1=value,sector_type='INDUSTRY',sector_name='GENERIC INDUSTRY',semantic_bucket='NORMAL_ATTRIBUTE',sector_valid=True))
        native.append(dict(sector_id=f'SECTOR_{sector}',sector_type='INDUSTRY',member_ids=ids,fields={f:{'value':None} for f in ('ma20_width','breadth_delta3','ma20_delta3','dq5','sector_rs20_pct')}))
    inputs=build_b2_inputs(native,current,'2026-09-30',cfg)
    assert all(f['q20']['value'] is None and f['dq5_3']['value'] is None for f in inputs.values())
    source=build_sector_current(pd.DataFrame(members),pd.DataFrame(members)[['security_id','trade_date','ret1']],cfg)
    actual={row['sector_id']:row['current'] for row in source.to_dict('records')}
    assert actual['SECTOR_4'] is True
    for sid,facts in inputs.items():
        values={k:v['value'] for k,v in facts.items()}
        expected='TRUE' if actual[sid] is True else 'FALSE' if actual[sid] is False else 'UNKNOWN'
        assert b2(values)['confirmed_raw']==expected

@pytest.mark.parametrize('amount,expected',[(1.1,'TRUE'),(None,'UNKNOWN'),(.1,'FALSE')])
def test_all_actual_legacy_potential_branches_keep_amount_a_diagnostic(amount,expected):
    import pandas as pd
    from workbench_analysis.sector_attention import build_sector_potential
    values={**positive(), 'sector_id':'SYNTHETIC','current':False,'weak':False,'m1':-.005,'b1':.5,
        'ma20_width':.6,'extended_share':.1,'risk_evaluable_count':10,'risk_coverage':1,
        'dq5_3':.2,'b_delta3':.2,'ma20_delta3':.1,'early_width':.2,'early_count':3,
        'amount_A':amount,'q20':.6,'setup_count':3,'setup_evaluable_count':10,'prior_current_within10':True}
    source=build_sector_potential(pd.DataFrame([values]),read('config/research_attention_v3.yaml')).to_dict('records')[0]
    actual=b2(values)
    for rule,state in source['branch_results'].items():
        source_state='TRUE' if state is True else 'FALSE' if state is False else 'UNKNOWN'
        assert actual['predicates'][rule]['state']==source_state
    assert actual['warm_diagnostic']==expected and actual['warm_raw']=='UNKNOWN'

@pytest.mark.parametrize('feedback',['PREWATCH','Focus','Radar','Support','turnover','future_confirmation','future_outcome'])
def test_b2_feedback_isolation(feedback):
    values=positive()
    assert b2({**values,feedback:True})==b2({**values,feedback:False})

def test_full_market_exact_scoped_membership():
    head=read('data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json')
    assert head['row_count']==50162 and head['does_not_grant_sector_algorithm_acceptance']
    for kind in ('SECTOR_NATIVE','B0','ROTATION','B2'):
        receipt=read(f'reports/v4_08/V4_08_R5_{kind}_FULL_MARKET.json')
        assert receipt['row_count']==378 and receipt['sector_counts']=={'INDUSTRY':110,'THEME':268}
        assert receipt['stale_core_relabelled'] is False
