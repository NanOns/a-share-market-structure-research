"""Narrow atomic repair; baseline PASS_KEEP sections and historical reports frozen."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
BASE='3f0663804bf104dd3e61e65d9927cb7f2081fa3b'
CONTRACT='config/v4_21_continued_forward_observation_contract_v1.json'
ALLOWED=(CONTRACT,'reports/r30/design_ledger.py','tests/test_v4_21_forward_observation_contract.py')
PASS_KEEP=('evidence_lanes','event_cohort_ledger','due_outcome_ledger','right_censor','stratification','continuity','gate_readback','recovery','prohibited','daily_operation','current_state','implementation_entry')


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def write(path,value):
    assert path==CONTRACT or path.startswith(('reports/r30r1/','docs/evidence/r30r1/'))
    target=ROOT/path; target.parent.mkdir(parents=True,exist_ok=True)
    data=value if isinstance(value,str) else json.dumps(value,indent=2,ensure_ascii=False,sort_keys=True)+'\n'
    staging=target.with_name(target.name+'.r30r1-staging')
    with staging.open('wb') as stream:
        stream.write(data.replace('\r\n','\n').encode()); stream.flush(); os.fsync(stream.fileno())
    os.replace(staging,target)


def baseline_contract():
    return json.loads(subprocess.check_output(['git','show',BASE+':'+CONTRACT],cwd=ROOT))


def build():
    from reports.r30r1.session_authority import OWNER,OWNER_PATH,OWNER_SHA
    docs=[]
    for name in ('V4_NEXT_ROUND_EXECUTION_MASTER_R30R1_20261004.md','V4_21_R30R1_NATIVE_SESSION_STATUS_AND_OWNER_BINDING_REPAIR_TASK_20261004.md','V4_R30_V4_21_CONTINUED_FORWARD_OBSERVATION_CONTRACT_DESIGN_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'):
        source=Path('D:/Users/lps/Desktop/阶段任务')/name; target='docs/evidence/r30r1/'+name
        docs.append(dict(source=str(source),sha256=sha(source),copy=target)); write(target,source.read_text(encoding='utf8'))
    write('reports/r30r1/STAGE_CONTRACT.json',dict(stage='V4-21/R30R1',mode='NARROW_CONTRACT_DESIGN_REPAIR',baseline=BASE,documents=docs,allowed=list(ALLOWED)+['reports/r30r1/*','docs/evidence/r30r1/*'],upgrade=dict(path='docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md',sections=['51A','52A','78/V4-21','81.4']),acceptance='PENDING_LOCAL_REPAIR_VALIDATION',next='STOP_WAIT_R30R1_INDEPENDENT_EXTERNAL_AUDIT',temporary_checkouts='F:/codex_tmp',test_temp='E:/codex_tmp/test_temp'))
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=ROOT,text=True,encoding='utf8').splitlines()
    # Read historical blobs for the three authorized mutable text files; others hash current protected bytes.
    original={n:(hashlib.sha256(subprocess.check_output(['git','show',BASE+':'+n],cwd=ROOT)).hexdigest() if n in ALLOWED else sha(ROOT/n)) for n in names if (ROOT/n).is_file()}
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT).decode('utf8').split('\0')
    write('reports/r30r1/PROTECTED_BASELINE.json',dict(baseline=BASE,allowed_changes=list(ALLOWED),tracked=original,unrelated={n:sha(ROOT/n) for n in untracked if n and not n.startswith(('reports/r30r1/','docs/evidence/r30r1/','tests/test_v4_21_native_session_repair.py'))}))
    c=baseline_contract(); c.update(version='1.0.1',baseline=BASE,status='LOCAL_NATIVE_SESSION_REPAIR_PENDING_EXTERNAL_AUDIT',next_stage='STOP_WAIT_R30R1_INDEPENDENT_EXTERNAL_AUDIT')
    binding=dict(contract_id=OWNER['contract_id'],path=OWNER_PATH,sha256=OWNER_SHA,native_slot_states=OWNER['slot_states'])
    c['owner_bindings'].append(binding)
    c['native_session_policy']=dict(shadow_owner=binding,shadow_authority_id=OWNER['contract_id'],shadow_allowed_statuses=OWNER['slot_states'],fields=['native_session_authority_id','native_session_authority_sha256','native_session_status','projection_evaluable','projection_evaluable_reason'],compatibility_slot_status='IF_PRESENT_EXACT_NATIVE_STATUS_ONLY_NO_ALIAS',accepted_rule='PIT_OBSERVED AND ACCEPTED_REAL_PUBLICATION AND SHADOW AND NATIVE_ACCEPTED_ON_TIME AND PROJECTION_EVALUABLE_TRUE',missed='NATIVE_MISSED_OBSERVATION_SLOT_RETAIN_DENOMINATOR_PROJECTION_FALSE_AND_STREAK_ZERO',accepted_non_evaluable='NATIVE_ACCEPTED_ON_TIME_RETAIN_DENOMINATOR_WITH_DISTINCT_PROJECTION_REASON_COUNT_ZERO_STREAK_ZERO_NEVER_MISSED',projection_type='STRICT_BOOLEAN; FALSE_REQUIRES_EXPLICIT_REASON',production_native_session_authority='FUTURE_ACCEPTED_BINDING_REQUIRED',production_accepted_binding=None,production_current_real_gate_count='NOT_COUNTABLE_FOR_REAL_GATE',production_design_fixture='ONLY_EXPLICIT_CONTRACT_DESIGN_SIMULATION_WITH_SIMULATED_AUTHORITY_ID_STATES_AND_EXACT_DIGEST; NEVER_CURRENT_AUTHORITY')
    required=c['session_ledger']['required']; required.remove('slot_status'); required.remove('evaluable'); required.extend(c['native_session_policy']['fields'])
    c['session_ledger']['owner']='EXACT_V4_16_OBSERVATION_SLOT_CONTRACT_V2_FOR_SHADOW; FUTURE_ACCEPTED_BINDING_REQUIRED_FOR_PRODUCTION'
    c['session_ledger']['native_owner_binding']=binding
    c['ledger_rules']['session_order']='EXACT_ACCEPTED_CALENDAR_ORDER; MISSED_OBSERVATION_SLOT_OR_PROJECTION_EVALUABLE_FALSE_RESETS_STREAK; NATIVE_STATUS_AND_PROJECTION_DISTINCT'
    c['receipt_schema']['additional'].extend(c['native_session_policy']['fields'])
    c['receipt_schema']['required'].extend(c['native_session_policy']['fields'])
    c['receipt_schema']['accepted_session_status_derivation']='SHADOW: EXACT_NATIVE_V4_16_SLOT_STATUS; RETAIN_NATIVE_AUTHORITY_ID_SHA_AND_SEPARATE_PROJECTION_EVALUABLE_REASON. PRODUCTION: FUTURE_ACCEPTED_BINDING_REQUIRED; NO_REAL_R30R1_RECEIPT'
    for index,desc in {0:'ACCEPTED_ON_TIME and projection evaluable true counts one',4:'MISSED_OBSERVATION_SLOT retained denominator count zero streak breaks',5:'ACCEPTED_ON_TIME and projection evaluable false retained denominator count zero streak breaks not missed'}.items(): c['vectors'][index]['description']=desc
    write(CONTRACT,c)
    mapping={'NATIVE_SESSION_OWNER_BINDING':binding,'SHADOW_SLOT_STATUS_GATE':c['native_session_policy'],'SESSION_EVALUABILITY_GATE':c['session_ledger'],'PRODUCTION_SESSION_AUTHORITY_GATE':dict(status='FUTURE_ACCEPTED_BINDING_REQUIRED',accepted_binding=None,current_real_gate_count='NOT_COUNTABLE_FOR_REAL_GATE'),'OBSERVATION_RECEIPT_STATUS_GATE':c['receipt_schema']}
    for name,value in mapping.items(): write('reports/r30r1/'+name+'.json',dict(contract=CONTRACT,contract_sha256=sha(ROOT/CONTRACT),definition=value,scope='CONTRACT_DESIGN_REPAIR_ONLY'))


if __name__=='__main__':
    import sys
    sys.path.insert(0,str(ROOT)); build()
