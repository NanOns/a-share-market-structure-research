"""Independent read-only R10A entry/authority exact-byte gate."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT,bind,PERMISSIONS
from scripts.prepare_v4_12_runtime_entry_r1 import BASELINE,ACCEPTANCE,ENTRY,DOC,NAMES,EVIDENCE,OUT
from scripts.record_r7_stage_contract import put
from src.workbench_analysis.historical_stage_governance_r17 import protected_bytes,resolve,current_state,STAGE

def exact(ref):
    path=resolve(ROOT,ref) if ref['path']==STAGE else (ROOT/ref['path']).resolve();assert path.is_relative_to(ROOT)
    raw=path.read_bytes();assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],ref['path']
    return json.loads(raw)

def validate(emit=False):
    accepted=json.loads((ROOT/ACCEPTANCE).read_bytes());entry=json.loads((ROOT/ENTRY).read_bytes())
    assert entry['contract_freeze_acceptance']==bind(ACCEPTANCE)
    assert accepted['external_audit_status']=='PASS_V4_12_CONTRACT_FREEZE' and accepted['audited_remote_head']==BASELINE
    assert accepted['tested_source_sha']=='11d8015d608670572bd57fc50fb6327e2b693a73'
    assert accepted['external_authority']==bind(DOC+NAMES[3])
    assert 'PASS_V4_12_CONTRACT_FREEZE' in (ROOT/(DOC+NAMES[3])).read_text(encoding='utf-8')
    assert set(r['path'] for r in accepted['evidence'])==set(EVIDENCE)
    for ref in accepted['evidence']+[accepted['accepted_parent'],accepted['stage_entry']]:exact(ref)
    expected=sorted(p for p in subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,'config'],cwd=ROOT,text=True,encoding='utf8').splitlines() if p.startswith('config/v4_12_') and p.endswith('.json'))
    assert [r['path'] for r in accepted['frozen_contracts']]==expected and entry['frozen_contracts']==accepted['frozen_contracts']
    for ref in accepted['frozen_contracts']:exact(ref)
    for key in ['stage_head','data_head']:exact(entry[key])
    assert entry['scope']=='V4_12_D1_ENGINEERING_RUNTIME_R1' and entry['scoped_engineering_implementation_permission'] is True
    assert entry['allowed_namespaces']==['F0[t]','Frozen D1[t-1]','frozen calendar','frozen contract/parameter']
    assert entry['forbidden_namespaces']==['D2','Final State','state_events','Radar','Focus','UI','Forward outcomes','Validation Cohort']
    fields=json.loads((ROOT/'config/v4_12_field_registry_v1.json').read_bytes())['fields']
    assert entry['blocked_fields']==[dict(field=r['field'],reason=r['blocked_reason'],producer=r['producer_contract_id']) for r in fields if r['field_role'] in ['BLOCKED_CAPABILITY','FROZEN_PRIOR_D1']]
    for obj in [accepted,entry]:
        assert all(obj[k] is False for k in PERMISSIONS) and obj['stage_accepted'] is False
    assert all(entry[k] is False for k in ['formal_V4_12_head_permission','DB_migration_permission','D2_integration_permission','V4_13_permission'])
    protected=['AGENTS.md','data/v4/V4_11_ACCEPTED_HEAD.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json',
        'reports/v4_12/V4_12_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY_R1.json']
    protected+=subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,'reports/v4_12_r2','reports/v4_12_r2_1'],cwd=ROOT,text=True).splitlines()
    proof=[]
    for path in protected:
        before=subprocess.check_output(['git','show',BASELINE+':'+path],cwd=ROOT);after=protected_bytes(ROOT,path,hashlib.sha256(before).hexdigest());assert before==after,path
        proof.append(dict(path=path,before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(after).hexdigest(),byte_identical=True))
    assert subprocess.run(['git','cat-file','-e',BASELINE+':data/v4/V4_12_ACCEPTED_HEAD.json'],cwd=ROOT,capture_output=True).returncode!=0
    assert exact(entry['stage_head'])['accepted_stage_range']=='V4_00_TO_V4_11_ACCEPTED'
    current=current_state(ROOT)
    result=dict(status='PASS',current_accepted_state=current,historical_stage_head=exact(entry['stage_head'])['accepted_stage_range'],entry_status=entry['status'],frozen_contract_count=len(expected),protected_artifacts=proof,
        stage_head=json.loads((ROOT/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_bytes())['accepted_stage_range'],
        data_head=json.loads((ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes())['accepted_trade_date'],permissions=PERMISSIONS,
        scoped_engineering_implementation_permission=True,entry=bind(ENTRY))
    if emit:put(OUT+'R10A_LOCAL_READBACK.json',result)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--emit',action='store_true');r=validate(p.parse_args().emit);print(json.dumps(dict(status=r['status'],entry_status=r['entry_status'],frozen_contract_count=r['frozen_contract_count'])))
