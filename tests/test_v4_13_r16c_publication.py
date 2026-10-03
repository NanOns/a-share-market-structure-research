"""Fresh processes, immutable revisions and independent end-to-end witnesses."""
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
import pytest
from workbench_analysis.v4_13_io import digest,envelope
from workbench_analysis.v4_13_accepted_contract_package import current_contracts as FrozenContracts
from workbench_analysis.v4_13_publication import publish,readback
from workbench_analysis.v4_13_loo_runtime import LOOContextRuntime
from workbench_analysis.v4_13_profile_runtime import ProfileRuntime
from test_v4_13_r16a_runtime import fixture_binder
ROOT=Path(__file__).resolve().parents[1]

def metadata():
    return dict(source_refs=[],diagnostics={},scope='SYNTHETIC_INDEPENDENT_ORACLE',prior_session_ref={'trade_date':'2026-09-29'},contract_digest='fixture',available_at='2026-10-02T15:00:00+08:00')

def row(revision,concepts=None):
    return dict(security_id='S',trade_date='2026-09-30',revision=revision,primary_industry='I',supporting_concepts=['A','Z'] if concepts is None else concepts)

def test_append_only_correction_and_prior_isolation(tmp_path):
    refs=[]
    for rev,concepts in [('r1',['A','Z']),('r2',['A','B','Z']),('r3',['A','B','Z'])]:
        refs.append(publish(tmp_path,'synthetic','2026-09-30',rev,[row(rev,concepts)],[],metadata()))
    assert readback(tmp_path,refs[0])['profile_advanced'][0]['supporting_concepts']==['A','Z']
    assert [readback(tmp_path,r)['manifest']['prior_session_ref']['trade_date'] for r in refs]==['2026-09-29']*3
    with pytest.raises(ValueError,match='APPEND_ONLY'):publish(tmp_path,'synthetic','2026-09-30','r1',[row('r1',['Q'])],[],metadata())

def test_fresh_process_exact_readback(tmp_path):
    ref=publish(tmp_path,'synthetic','2026-09-30','r1',[row('r1')],[],metadata())
    code='from workbench_analysis.v4_13_publication import readback; import json,sys; r=readback(sys.argv[1],json.loads(sys.argv[2])); print(json.dumps(r["profile_advanced"]))'
    p=subprocess.run([sys.executable,'-c',code,str(tmp_path),json.dumps(ref)],capture_output=True,text=True,env=dict(os.environ,PYTHONPATH=str(ROOT/'src')))
    assert p.returncode==0,p.stderr;assert json.loads(p.stdout)==[row('r1')]

def test_deterministic_publication_and_tamper_rejection(tmp_path):
    ref=publish(tmp_path,'synthetic','2026-09-30','r1',[row('r1')],[],metadata())
    assert ref==publish(tmp_path,'synthetic','2026-09-30','r1',[row('r1')],[],metadata())
    p=tmp_path/ref['path'];p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError,match='DIGEST_MISMATCH'):readback(tmp_path,ref)

@pytest.mark.parametrize('perturb',['membership','context','D1','sector_order','concept_order','display_cap'])
def test_actual_profile_pipeline_perturbation_raw_freeze(perturb):
    contracts=FrozenContracts(ROOT);b=fixture_binder(contracts)
    b.structure={};b.structure_ref=None;b.prior_session_ref={'trade_date':'2026-09-29'}
    engine=LOOContextRuntime(contracts);projector=ProfileRuntime(contracts)
    before=deepcopy((b.stock,b.seed,b.current));a=engine.compute(b,'target','r1');p=projector.compute(b,'target','r1',a)
    if perturb=='sector_order':b.memberships.reverse()
    elif perturb=='context':a['relative_sector_state']=envelope('NEUTRAL','KNOWN',None)
    elif perturb=='D1':b.structure={'target':dict(active_selection={'active_anchor_id':'CHANGED','quality':'KNOWN'},active_projection={'support_state':'HELD'},anchor_states=[],basic_breakout_state='BREAKOUT_TENTATIVE',events=[])}
    elif perturb in ['membership','concept_order']:b.by_security['target']=list(reversed(b.by_security['target']))
    elif perturb=='display_cap':contracts.config['parameter_set']['parameters'][0]['value']=0
    changed=engine.compute(b,'target','r1') if perturb!='context' else a
    q=projector.compute(b,'target','r1',changed)
    assert (b.stock,b.seed,b.current)==before
    if perturb=='D1':assert digest(changed['contexts'])==digest(a['contexts'])
    assert p['raw_qualification_before']==p['raw_qualification_after']==q['raw_qualification_after']
    if perturb in ['sector_order','concept_order','display_cap']:assert digest(p)==digest(q)

def test_real_persisted_capability_scope_if_available():
    path=ROOT/'reports/v4_13_runtime_r16/real/2026-09-30/r5/manifest.json'
    if not path.exists():pytest.skip('Real replay is sequentially run after local unit gate')
    from workbench_analysis.v4_13_io import file_ref
    result=readback(ROOT,file_ref(ROOT,path.relative_to(ROOT).as_posix()),collect=False)
    assert result['profile_advanced']==5224
    from workbench_analysis.v4_13_io import rows
    artifact=next(r for r in result['manifest']['artifacts'] if 'profile_advanced' in r['path'])
    for r in rows(ROOT,artifact):
        assert r['fields']['primary_industry']['quality'] in ['KNOWN','NOT_APPLICABLE']
        assert r['fields']['supporting_concepts']['quality'] in ['KNOWN','NOT_APPLICABLE']
        assert r['fields']['algorithmic_support_sector']['quality']=='UNKNOWN'
        assert r['prior_session_ref']['trade_date']=='2026-09-29'
    assert set(result['diagnostics']['authority_counters'].values())=={0}

def test_fresh_process_membership_correction_uses_same_market_predecessor(tmp_path):
    first=publish(tmp_path,'synthetic','2026-09-30','r1',[row('r1')],[],metadata())
    code="""import json,sys
from workbench_analysis.v4_13_publication import readback,publish
root=sys.argv[1];old=readback(root,json.loads(sys.argv[2]))
assert old['profile_advanced'][0]['supporting_concepts']==['A','Z']
new=dict(old['profile_advanced'][0],revision='r2',supporting_concepts=['A','B','Z'])
meta=dict(source_refs=[],diagnostics={},scope='SYNTHETIC_INDEPENDENT_ORACLE',prior_session_ref=old['manifest']['prior_session_ref'],contract_digest='fixture',available_at='2026-10-02T15:00:00+08:00')
ref=publish(root,'synthetic','2026-09-30','r2',[new],[],meta)
print(json.dumps(ref))
"""
    process=subprocess.run([sys.executable,'-c',code,str(tmp_path),json.dumps(first)],capture_output=True,text=True,env=dict(os.environ,PYTHONPATH=str(ROOT/'src')))
    assert process.returncode==0,process.stderr
    second=json.loads(process.stdout);result=readback(tmp_path,second)
    assert result['profile_advanced'][0]['supporting_concepts']==['A','B','Z']
    assert result['manifest']['prior_session_ref']=={'trade_date':'2026-09-29'}
    assert readback(tmp_path,first)['profile_advanced'][0]['supporting_concepts']==['A','Z']
