"""Narrow repair negatives and perturbations; expected outputs are literal."""
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import pytest
from workbench_analysis.v4_13_io import revision_ordinal,atomic,canonical,file_ref,exact
from workbench_analysis.v4_13_accepted_contract_package import current_contracts as FrozenContracts
from workbench_analysis.v4_13_input_binder import AcceptedInputBinder
from workbench_analysis.v4_13_profile_runtime import copy_structure
from workbench_analysis.v4_13_publication import publish,publish_stream
ROOT=Path(__file__).resolve().parents[1]

def source_row():
    return dict(identity={'security_id':'S','trade_date':'2026-09-30','revision':'r1'},
        active_selection={'active_anchor_id':'A','quality':'KNOWN','reason':'SELECTOR'},
        active_projection={'support_state':'HELD','acceptance_state':'PENDING','basic_pullback_state':'NOT_PULLBACK','basic_recovery_state':'NONE','retest_count':3},
        anchor_states=[dict(anchor_id='A',state_observations={n:{'value':v,'state':v,'quality':'KNOWN','reason':[n+'_REASON']} for n,v in [('support','HELD'),('acceptance','PENDING'),('pullback','NOT_PULLBACK'),('recovery','NONE')]},
            facts={'prior_test_count':{'value':3,'quality':'KNOWN','reason':['COUNTER']}},
            output_envelope={'anchor_view_asof_t':{'lower':'100','upper':'101','quality':'UNKNOWN','reason':'VIEW_UNAVAILABLE'},'structure_health':{'value':'HEALTHY','quality':'DEGRADED','reason':'HEALTH'}})],
        basic_breakout_state='BREAKOUT_TENTATIVE',breakout_projection_quality='KNOWN',breakout_projection_reason=['BREAKOUT'],events=[])

@pytest.fixture(scope='module')
def contracts():return FrozenContracts(ROOT)

@pytest.mark.parametrize('machine,field',[('support','support_state'),('acceptance','acceptance_state'),('pullback','basic_pullback_state'),('recovery','basic_recovery_state')])
def test_machine_quality_and_reason_exact(contracts,machine,field):
    row=source_row();a=copy_structure(row,contracts)
    row['anchor_states'][0]['state_observations'][machine].update(quality='UNKNOWN',reason=['PERTURBED'])
    b=copy_structure(row,contracts)
    assert a[field]['value']==b[field]['value']
    assert b[field]['quality']=='UNKNOWN' and b[field]['reason']==['PERTURBED']
    row['active_selection']['reason']='CHANGED_SELECTOR';row['active_projection']['reason']='CHANGED_SELECTOR'
    assert copy_structure(row,contracts)[field]['reason']==['PERTURBED']

def test_nested_unknown_and_missing_metadata(contracts):
    r=copy_structure(source_row(),contracts)
    assert r['anchor_view_asof_t']['quality']=='UNKNOWN' and r['anchor_view_asof_t']['value']['quality']=='UNKNOWN'
    assert r['structure_events']['value']==[] and r['structure_events']['quality']=='UNKNOWN'
    assert r['retest_count']['quality']=='KNOWN' and r['retest_count']['reason']==['COUNTER']

def test_producer_mismatch_rejected(contracts):
    with pytest.raises(ValueError,match='PRODUCER'):copy_structure(source_row(),contracts,{'producer_contract_id':'WRONG'})

@pytest.mark.parametrize('bad',['r0','r01','r-1','r1/../r2','rX','R1','r1\n',None])
def test_invalid_revision(bad):
    with pytest.raises(ValueError):revision_ordinal(bad)

def test_numeric_revision_and_binder_selection(tmp_path,contracts):
    assert revision_ordinal('r9')<revision_ordinal('r10')<revision_ordinal('r11')
    refs=[]
    for rev in ['r9','r10','r11']:
        row=source_row();row['identity']['revision']=rev
        import gzip
        a=atomic(tmp_path,rev+'.jsonl.gz',gzip.compress(canonical(row)+b'\n',mtime=0))
        refs.append(atomic(tmp_path,rev+'.json',canonical(dict(trade_date='2026-09-30',revision=rev,scope='REAL_ACCEPTED_SOURCE_CANDIDATE',available_at='2026-10-02T06:00:00+00:00',contract_id=contracts.config['projection']['source_publication_contract'],artifacts=[dict(a,path=a['path'].replace(rev+'.jsonl.gz',rev+'/runtime_security.jsonl.gz'))]))))
        atomic(tmp_path,rev+'/runtime_security.jsonl.gz',(tmp_path/a['path']).read_bytes())
    c=SimpleNamespace(owners={'V4_12':{'publication_authority':{'authorized_manifests':refs}}},config=contracts.config)
    b=SimpleNamespace(contracts=c,root=tmp_path,date='2026-09-30',cutoff='2026-10-03T00:00:00+08:00',structure={},refs=[])
    AcceptedInputBinder.load_structure(b)
    assert b.structure_manifest['revision']=='r11'
    c.owners['V4_12']['publication_authority']['authorized_manifests']=refs[:2]
    AcceptedInputBinder.load_structure(b);assert b.structure_manifest['revision']=='r10'

@pytest.mark.parametrize('method',[publish,publish_stream])
@pytest.mark.parametrize('namespace,date,revision',[('../escape','2026-09-30','r1'),('good','../../escape','r1'),('good','2026-02-30','r1'),('good','2026-9-30','r1'),('good','2026-09-30','../r1'),('good','2026-09-30','r01')])
def test_boundary_before_write(tmp_path,method,namespace,date,revision):
    with pytest.raises(ValueError):
        if method==publish:method(tmp_path,namespace,date,revision,[],[],{})
        else:method(tmp_path,namespace,date,revision,[],{})
    assert list(tmp_path.iterdir())==[]

def test_atomic_escape_and_hash_path_mismatch(tmp_path):
    with pytest.raises(ValueError,match='OUTSIDE'):atomic(tmp_path,'../escape',b'')
    r=atomic(tmp_path,'one',b'one');atomic(tmp_path,'two',b'two')
    for bad in [dict(r,sha256='0'*64),dict(r,path='two'),dict(r,path='../outside')]:
        with pytest.raises(ValueError):exact(tmp_path,bad)

@pytest.mark.parametrize('method',[publish,publish_stream])
def test_append_only_changed_bytes(method,tmp_path):
    meta=dict(source_refs=[],diagnostics={},prior_session_ref={'trade_date':'2026-09-29'})
    row=dict(security_id='S',trade_date='2026-09-30',revision='r1',value=1)
    def emit(r):
        return method(tmp_path,'witness','2026-09-30','r1',[r],[],meta) if method==publish else method(tmp_path,'witness','2026-09-30','r1',[(r,[])],meta)
    ref=emit(row);before=(tmp_path/ref['path']).read_bytes();assert emit(row)==ref
    with pytest.raises(ValueError,match='APPEND_ONLY'):emit(dict(row,value=2))
    assert (tmp_path/ref['path']).read_bytes()==before

def test_component_provenance_owner_dates(contracts):
    b=AcceptedInputBinder(contracts,'2026-09-30','2026-10-03T00:00:00+08:00')
    refs=b.component_sources('S',{'value':None},'LOO')
    assert refs['loo_b0_raw'][0]['producer_contract_id']=='V4_08_SECTOR_PREWATCH_B0_V2'
    assert refs['rotation_core_state'][0]['producer_contract_id']=='ROTATION_CORE_V1_R3'
    assert refs['relative_sector_state'][0]['producer_contract_id']=='RELATIVE_STATE_V1'
    for rs in refs.values():
        assert all(r['available_at']!=b.cutoff for r in rs)
        assert next(r for r in rs if 'V4_05_R4_1_FULL_SCOPE' in r['path'])['trade_date']=='2026-09-28'
        for r in rs:exact(ROOT,r)

def test_v1_2_minimal_same_family(contracts):
    from scripts.validate_v4_13_r1_1 import validate_lineage
    current=contracts.config['projection'];assert validate_lineage(current)
    old=json.loads(exact(ROOT,current['supersedes']))
    for key,value in old.items():
        if key not in ['version','supersedes','reason']:assert current[key]==value

@pytest.mark.parametrize('category',list(range(1,11)))
def test_independent_oracle_rejects_each_category_mutation(category):
    from scripts.validate_v4_13_r16 import validate_witnesses
    w=json.loads((ROOT/'reports/v4_13_runtime_r16r1/runtime_witnesses.json').read_bytes())
    if category==1:w['context_cases'][0]['actual']['primary_industry']['value']='WRONG'
    elif category==2:w['context_cases'][0]['actual']['contexts'][0]['member_ids'].append('target')
    elif category==3:w['context_cases'][2]['actual']['contexts'][0]['native_fields']['sector_quote_coverage']['value']=1
    elif category==4:w['selector_cases'][0]['actual']['value']='Z'
    elif category==5:w['context_cases'][0]['actual']['relative_sector_state']['relative_substitutions']['rel_market_1']=0
    elif category==6:w['quality_cases'][0]['actual']='UNKNOWN'
    elif category==7:w['structure_cases'][0]['actual']['support_state']['reason']='SELECTOR'
    elif category==8:w['dual_cases'][0]['actual']['rotation_core_state']=None
    elif category==9:w['publish_append_only']['manifest']['prior_session_ref']['trade_date']='2026-09-30'
    else:w['publish_append_only']['after']['changed']={}
    with pytest.raises(AssertionError):validate_witnesses(w)

@pytest.mark.parametrize('key,value',[('producer_contract_id','WRONG'),('sha256','0'*64),('path','config/v4_13_projection_v1_1.json')])
def test_independent_provenance_mismatch_rejected(key,value):
    from scripts.validate_v4_13_r16 import validate_provenance
    w=json.loads((ROOT/'reports/v4_13_runtime_r16r1/runtime_witnesses.json').read_bytes())
    refs=w['provenance_cases'];refs['loo_b0_raw'][0][key]=value
    with pytest.raises(AssertionError):validate_provenance(refs,'S','I','WITNESS_LOO')
