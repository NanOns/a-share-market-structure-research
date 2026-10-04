"""Independent R31R2 fail-closed vectors; ephemeral simulated closure authorities."""
from copy import deepcopy
import hashlib,json,os,subprocess
from pathlib import Path
import pytest
from tests.test_v4_22_independent_audit_contract import C,ROOT,ledger,evaluate,future_simulation
from reports.r31.audit_oracle import digest,final_verdict
from reports.r31r2.build_contract import build,build_bytes,BASE,BASE_SHA,CONTRACT

def atomic_json(p,v):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix('.stage'); t.write_text(json.dumps(v,sort_keys=True),encoding='utf8'); os.replace(t,p)
def binding(p,root):
    return dict(path=p.relative_to(root).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),contract_id=json.loads(p.read_bytes())['contract_id'])
def exact_future(root):
    c,items,gates=future_simulation(); closures={}
    evidence=root/'evidence.json'; atomic_json(evidence,dict(contract_id='SIMULATED_CLOSURE_EVIDENCE',scope='CONTRACT_DESIGN_SIMULATION_NOT_REAL_EVIDENCE'))
    refs=[binding(evidence,root)]; entries=[]
    for item in c['open_items']:
        if item['item_id']=='OPEN-09': continue
        entries.append(dict(item_id=item['item_id'],capability_scope=item['capability_scope'],explicit_disposition='INDEPENDENTLY_DISPOSED',exact_evidence=refs,date_source='2026-10-05/SIMULATED_INDEPENDENT_AUTHORITY',independent_recheck=True))
    authority=root/'authority.json'; atomic_json(authority,dict(contract_id='SIMULATED_INDEPENDENT_CLOSURE_AUTHORITY',scope='CONTRACT_DESIGN_SIMULATION_NOT_REAL_AUTHORITY',closure_authorizations=entries))
    owner=binding(authority,root)
    for entry in entries:
        r=dict(entry,authority=owner,closure_authority=owner); key=r['item_id']; closures[key]=r
        c['open_item_closure_bindings'][key]=dict(item_id=key,capability_scope=r['capability_scope'],canonical_sha256=digest(r),closure_authority=owner,exact_evidence=refs)
        c['closure_authority_authorizations'][key]=[owner]
    return c,items,gates,closures

def closure_vector(vector,root):
    c,items,gates,closures=exact_future(root); r=closures['OPEN-01']; b=c['open_item_closure_bindings']['OPEN-01']
    if vector==1: r['exact_evidence'][0]['path']='missing.json'
    if vector==2: r['exact_evidence'][0]['sha256']='0'*64
    if vector==3: r['exact_evidence'][0]['contract_id']='WRONG'
    if vector==4: r['exact_evidence'][:]=[dict(path='SIM_ONLY',sha256='SIM_ONLY')]
    if vector==5:
        opener=c['open_items'][0]['authority']; r.update(authority=opener,closure_authority=opener); b['closure_authority']=opener
    if vector==6: r['closure_authority']['sha256']='0'*64
    if vector==8: c['closure_authority_authorizations'].clear()
    if vector==9: r['independent_recheck']=1
    if vector==10: r['date_source']='OTHER'
    if vector==11: r['explicit_disposition']='SELF_ASSERTED'
    if vector==12: r['exact_evidence'][0]['path']='../outside.json'
    if vector==13: r['exact_evidence'][0].pop('contract_id')
    b['canonical_sha256']=digest(r)  # Rebind to prove canonical digest alone is insufficient.
    result=final_verdict(c,items,gates,dict(status='PASS'),open_item_receipts=closures,evidence_root=root)
    assert result['formula_result']==('V4_22_FINAL_PASS' if vector==7 else 'FINAL_AUDIT_BLOCKED')
    assert result['acceptance_granted'] is False and result['production_grant'] is False
    return dict(vector=f'R31R2-CLOSURE-{vector:02}',receipt=r,binding=b,result=result,simulation_only=True)

@pytest.mark.parametrize('vector',range(1,14),ids=[f'R31R2-CLOSURE-{i:02}' for i in range(1,14)])
def test_closure(vector,tmp_path): closure_vector(vector,tmp_path)

def ledger_vector(vector):
    v=ledger()
    if vector==1: v['events'][0].pop('evidence_lane')
    if vector==2: v['outcomes'][0].pop('evidence_lane')
    if vector==3: v['sessions'][0]['evidence_lane']='UNKNOWN'
    if vector==4: v['events'][0]['evidence_lane']='SHADOW_REAl'
    if vector==5: v['outcomes'][0]['evidence_lane']='TYPO'
    if vector in (6,7,9):
        lane={6:'HISTORICAL_REPLAY',7:'RECONSTRUCTED_ASOF',9:'ACTIVATION_SIMULATION'}[vector]
        ns={'HISTORICAL_REPLAY':'REPLAY','RECONSTRUCTED_ASOF':'RECONSTRUCTED_ASOF','ACTIVATION_SIMULATION':'ACTIVATION_SIMULATION'}[lane]
        for name in ('sessions','events','outcomes'): v[name][0].update(evidence_lane=lane,observation_namespace=ns,evidence_origin=lane,accepted_real_publication=False)
    if vector==10: v['events'][0]['observation_namespace']='REPLAY'
    if vector==11: v['events'][0]['accepted_real_publication']=False
    if vector==12:
        v['events'][0].update(evidence_lane='HISTORICAL_REPLAY',observation_namespace='REPLAY',evidence_origin='HISTORICAL_REPLAY',accepted_real_publication=False); v['events'][0].pop('logical_event_id')
    result=evaluate(v)
    assert result['status']==('PASS_DESIGN_ONLY' if vector in (6,7,8,9) else 'BLOCKED_AFFECTED_SCOPE')
    if vector in (6,7,9): assert result['design_countable_sessions']==0
    return dict(vector=f'R31R2-LEDGER-{vector:02}',input=v,result=result)

@pytest.mark.parametrize('vector',range(1,13),ids=[f'R31R2-LEDGER-{i:02}' for i in range(1,13)])
def test_ledger(vector): ledger_vector(vector)

@pytest.mark.parametrize('vector',range(1,5),ids=[f'R31R2-BUILD-{i:02}' for i in range(1,5)])
def test_build(vector,tmp_path):
    if vector in (1,2):
        subprocess.run(['git','init','-q',str(tmp_path)],check=True)
        common=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip())
        common=common if common.is_absolute() else ROOT/common
        (tmp_path/'.git/objects/info/alternates').write_bytes(((common.resolve()/'objects').as_posix()+'\n').encode('utf8'))
        p=tmp_path/CONTRACT; p.parent.mkdir(parents=True)
        p.write_bytes(subprocess.check_output(['git','show',BASE+':'+CONTRACT],cwd=tmp_path))
        before=build(tmp_path); after=build(tmp_path)
        assert before==after==hashlib.sha256((ROOT/CONTRACT).read_bytes()).hexdigest()
    if vector==3:
        from reports.r31.build_contract import historical_guard
        with pytest.raises(ValueError,match='HISTORICAL_ONLY'): historical_guard()
    if vector==4: assert C['next_stage']=='STOP_WAIT_R31R2_INDEPENDENT_EXTERNAL_AUDIT' and C['version']=='1.0.2'

def test_current_real_closures_remain_empty():
    assert C['closure_authority_authorizations']==C['open_item_closure_bindings']=={}
    assert C['current_state']['REAL_SHADOW_OBSERVATIONS']==0
