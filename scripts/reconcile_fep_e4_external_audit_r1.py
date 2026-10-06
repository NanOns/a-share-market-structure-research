"""Archive the supplied E4 external verdict without altering its frozen experiment."""
import hashlib,json,os,re,subprocess
from pathlib import Path
from scripts.build_fep_e2_r1r1_history import ROOT,binding,now
from scripts.validate_r25_preflight import protected,selection
from workbench_analysis.fep_e1.contracts import atomic_json,digest
from workbench_analysis.fep_e1.feature_owner import verify_file

AUDITED='848db27bfd2ede74ef1eac508f5454044d2211ce'
PARENT='77c7c2c85a5ff0bbd27bb664900673de7a3bff5a'
NAME='V4_15E4_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261006.md'
SOURCE=Path('D:/Users/lps/Desktop/阶段任务')/NAME
REPORT=ROOT/'reports/fep_e4_external_acceptance_r1'
E4=ROOT/'reports/fep_e4_r1'
NEXT='ISSUE_V4_15E5_EXPECTANCY_AWARE_PRIORITY_PROJECTION_TASK'

def load(path):return json.loads(Path(path).read_bytes())
def emit(name,payload):atomic_json(REPORT/(name+'.json'),payload)
def write(path,raw):
    tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    os.replace(tmp,path)
def require(condition,reason):
    if not condition:raise ValueError(reason)
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)

def main():
    require(not (REPORT/'EXTERNAL_ACCEPTANCE_SEAL.json').exists(),'AUDIT_RECEIPT_ALREADY_SEALED')
    require(git('rev-parse','HEAD').decode().strip()==AUDITED,'AUDITED_HEAD_REQUIRED')
    require(git('rev-parse',AUDITED+'^').decode().strip()==PARENT,'AUDITED_PARENT_MISMATCH')
    raw=SOURCE.read_bytes();text=raw.decode('utf-8-sig')
    decisions=dict(V4_15E4_FINAL_EXTERNAL_AUDIT='PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED',
        FEP_TREE_CHALLENGER_ENGINEERING='PASS_EXTERNAL_FIRST_PREWATCH_T1',CHALLENGER_EFFECTIVENESS='MIXED',
        PRIMARY_EFFECTIVENESS_VS_E2='NO_INCREMENT',DIAGNOSTIC_EFFECTIVENESS_VS_E3='IMPROVED',
        E3_MODEL_EFFECTIVENESS='NO_INCREMENT',REAL_OOS='NOT_GRANTED',FIRST_OBSERVED='NOT_GRANTED',
        MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',FEP_PRODUCTION='UNGRANTED')
    require(AUDITED in text and PARENT in text,'AUDIT_COMMIT_IDENTITY_MISMATCH')
    for key,value in decisions.items():
        values=re.findall(r'(?m)^'+re.escape(key)+r'\s*=\s*\n([^\r\n]+)',text)
        require(values and all(v.strip()==value for v in values),'AUDIT_DECISION_MISMATCH:'+key)
    require('E5 的正式实施必须另发独立任务卡' in text,'E5_SEPARATE_TASK_BOUNDARY_REQUIRED')
    # Confirm all audited E4 tracked bytes, including registry and receipts, against the audited Git object.
    paths=git('ls-tree','-r','--name-only',AUDITED,'--','reports/fep_e4_r1').decode().splitlines()
    old=load(E4/'FEP_E4_R1_CANDIDATE_SEAL.json');refs=old['code_bindings']+old['evidence_bindings']
    refs+=[binding(ROOT/path) for path in paths]
    refs+=load(ROOT/'config/fep_e4_challenger_protocol_v1.json')['input_bindings']
    refs=list({ref['path']:ref for ref in refs}.values())
    git_readback=[]
    for ref in refs:
        verify_file(ROOT,ref)
        raw_git=git('show',AUDITED+':'+ref['path'])
        blob=git('rev-parse',AUDITED+':'+ref['path']).decode().strip()
        filtered=git('hash-object','--path='+ref['path'],ref['path']).decode().strip()
        require(blob==filtered,'AUDITED_GIT_CONTENT_MISMATCH:'+ref['path'])
        git_readback.append(dict(path=ref['path'],audited_git_blob=blob,filtered_worktree_blob=filtered,
            raw_git_sha256=hashlib.sha256(raw_git).hexdigest(),sealed_worktree_sha256=ref['sha256'],
            exact_raw_git_bytes=hashlib.sha256(raw_git).hexdigest()==ref['sha256']))
    result=load(E4/'BASELINE_E3_E4_COMPARISON.json')['result']
    require(result['CHALLENGER_EFFECTIVENESS']=='MIXED' and result['E3_MODEL_EFFECTIVENESS']=='NO_INCREMENT','EFFECTIVENESS_REWRITE')
    mae={key:value['DATE_BALANCED_MAE'] for key,value in result['metrics'].items()}
    require(mae['E2']<mae['E4']<mae['E3'],'EXTERNAL_METRIC_ORDER_MISMATCH')
    require((result['rows'],result['outer_total'],result['dates'],result['blocks'])==(46,205,35,24),'POPULATION_MISMATCH')
    require(result['SEEN_OUTER_DIAGNOSTIC_ONLY'] is True and result['REAL_OOS'] is False and result['PROMOTION_EVIDENCE'] is False,'SEEN_OUTER_BOUNDARY')
    targeted=load(E4/'TARGETED_SUMMARY.json');scoped=load(E4/'SCOPED_REGRESSION_SUMMARY.json')
    require((targeted['passed'],targeted['skipped'],len(targeted['failed_nodes']))==(256,1,0),'TARGETED_RECEIPT_MISMATCH')
    require((scoped['passed'],scoped['skipped'],len(scoped['failed_nodes']))==(2615,4,52) and not scoped['introduced_active_failures'],'SCOPED_RECEIPT_MISMATCH')
    previous=load(ROOT/'reports/fep_e3_r1/SCOPED_REGRESSION_SUMMARY.json')
    require(sorted(scoped['failed_nodes'])==sorted(previous['failed_nodes']),'KNOWN_DEBT_IDENTITY_MISMATCH')
    exclusions=[v for v in scoped['command'] if v.startswith('--deselect=')]
    require(exclusions==[v for v in previous['command'] if v.startswith('--deselect=')],'EXCLUSION_MISMATCH')
    guard=protected(ROOT);wait=selection(ROOT)
    require((guard['Stage'],guard['Data'],guard['V4_16_ACCEPTED_HEAD'])==('V4_00_TO_V4_15_ACCEPTED','2026-09-30','NOT_CREATED'),'PROTECTED_HEAD_STATE')
    require(not guard['historical_git_diff'] and wait['status']=='WAIT_ACCEPTED_DAILY_INPUT','R25_BOUNDARY')
    REPORT.mkdir(parents=True,exist_ok=True);write(REPORT/'.gitattributes',b'* -text\n');write(REPORT/NAME,raw)
    authority=binding(REPORT/NAME)
    emit('ENTRY_BASELINE',dict(stage='V4-15E4.EXTERNAL_ACCEPTANCE.R1',baseline=AUDITED,parent=PARENT,
        source_path=str(SOURCE),source_sha256=hashlib.sha256(raw).hexdigest(),authority=authority,entered_at=now(),
        scope='External audit archival and governance reconciliation only; no model or next-stage execution'))
    boundary=dict(SEEN_OUTER_DIAGNOSTIC_ONLY=True,NEW_INDEPENDENT_OOS_EVIDENCE=False,CHAMPION=False,
        PROMOTION_EVIDENCE=False,production=False,shadow=False,focus=False)
    emit('EXTERNAL_ACCEPTANCE_RECONCILIATION',dict(status='PASS_EXACT_EXTERNAL_VERDICT_RECONCILED',authority=authority,
        audited_commit=AUDITED,audited_parent=PARENT,decisions=decisions,exact_audited_bindings=refs,git_blob_readback=git_readback,
        git_readback_semantics='Exact sealed working bytes plus equality with audited Git blob after configured clean filters; raw Git hashes retained separately',
        MAE=mae,predictable_rows=46,original_population=205,coverage=46/205,
        regression=dict(targeted_passed=256,targeted_skipped=1,scoped_passed=2615,scoped_skipped=4,
            existing_debt_nodes=scoped['failed_nodes'],exclusions=exclusions,introduced_active_failures=0,repository_all_green=False,
            new_test_run=False,CI_evidence='NO_RUN_NO_STATUS_REPORTED_BY_SUPPLIED_EXTERNAL_AUDIT'),**boundary))
    emit('INDEPENDENT_AUDIT_ITEMS',dict(items=[dict(audit_id='AUDIT_NOTE_E4_01',
        external_disposition='PASS_NONBLOCKING_GOVERNANCE_HARDENING_REQUIRED',status='OPEN_FOR_NEXT_EFFECTIVENESS_PROTOCOL',
        scope='Pre-register effectiveness disposition mapping with primary metric, tie-break and promotion boundary before evaluation opens',
        historical_E4='Mapping existed in frozen evaluator source but not an explicit protocol field; accepted nonblocking by external auditor',
        evidence=[authority,binding(ROOT/'config/fep_e4_challenger_protocol_v1.json'),binding(ROOT/'scripts/run_fep_e4_r1.py')],
        acceptance='Next E5/new effectiveness task must freeze the required explicit fields before its evaluation; no retroactive E4 protocol edit'),
        dict(audit_id='FEP_E4_MODEL_EVIDENCE_LIMITATIONS',status='OPEN_NO_PROMOTION',
        scope=['Seen historical Outer','46/205 predictable coverage','JOINT_OOD UNSET','No MAE increment over E2','Weak quantile calibration'],
        evidence=[authority,binding(E4/'INDEPENDENT_AUDIT_ITEMS.json')],acceptance='Separate future authorized evidence audit; E4 engineering acceptance does not close limitations')]))
    emit('E5_ENTRY_BOUNDARY',dict(status='AUTHORIZED_ENTRY_REQUIRES_SEPARATE_TASK_CARD',E5_ENTRY='AUTHORIZED_NOT_BLOCKED_BY_E4',
        E5_started=False,formal_task_card_received=False,required_pre_run_frozen_fields=['effectiveness disposition rule','primary metric',
        'tie-break','promotion boundary','priority projection boundary','shadow-only boundary','model evidence class'],
        prohibition=['promotion from seen Outer','MODEL_DISPLAY from E4','PRIORITY_USE from E4','production grant from E4','retroactive PRIORITY_V1 rewrite'],NEXT=NEXT))
    emit('PROTECTED_STATE_READBACK',dict(status='PASS_READ_ONLY_GOVERNANCE_RECONCILIATION',R25_protected=guard,R25_selection=wait,
        accepted_experiment_unchanged=True,E3_MODEL_EFFECTIVENESS='NO_INCREMENT',TDX='UNTOUCHED',
        new_model_fits=0,new_model_scoring=0,new_database_run=False,
        previous_database_evidence=binding(E4/'FINAL_EXIT_READBACK.json'),decisions=decisions,**boundary))
    summary='''# E4 final external audit reconciliation — 2026-10-06

E4 external verdict: PASS_FINAL_ENGINEERING_CAPABILITY_SCOPED / PASS_EXTERNAL_FIRST_PREWATCH_T1.
Challenger effectiveness stays MIXED: improves on E3, no primary MAE increment over E2. E3 stays NO_INCREMENT.

The supplied independent audit is archived byte-for-byte and bound to audited HEAD 848db27bfd2ede74ef1eac508f5454044d2211ce and its exact parent. All sealed working bytes were verified against their original SHA256 bindings, and Git blob identity was verified after configured clean filters. Raw Git and working-byte hashes are recorded separately for upstream Windows newline normalization. Frozen E4 protocol, trials, model artifacts and original candidate seal remain unchanged.

Seen Outer remains diagnostic only, with 46/205 predictable observations. No new independent OOS, first-observed, CHAMPION, model display, priority-use or production permission. Quantile calibration is weak; JOINT_OOD remains UNSET.

AUDIT_NOTE_E4_01 is tracked separately as nonblocking governance hardening required for the next effectiveness protocol. Disposition mapping must be explicit alongside the primary metric, tie-break and promotion boundary before evaluation. This receipt does not retroactively pre-register E4 or claim that the future requirement has been implemented.

Verification: exact file/Git hashes, audit decisions, metric ordering, scope/population, preserved 256/1 targeted and 2615/4/52 scoped receipts, exact known debt identities and two exclusions, accepted heads and live R25 WAIT readback. No fits, scoring, new test run or database run. Existing test debt remains visible.

E5 entry is authorized but formal implementation requires a separate task card. E5 was not started. Next: ISSUE_V4_15E5_EXPECTANCY_AWARE_PRIORITY_PROJECTION_TASK.
'''
    write(REPORT/'COMPLETION_REPORT.md',summary.encode())
    seal=dict(stage='V4-15E4.EXTERNAL_ACCEPTANCE.R1',status='PASS_EXTERNAL_AUDIT_RECONCILED',baseline=AUDITED,
        authority=authority,decisions=decisions,code_binding=binding(ROOT/'scripts/reconcile_fep_e4_external_audit_r1.py'),
        evidence_bindings=[binding(path) for path in sorted(REPORT.iterdir()) if path.is_file()],
        accepted_E4_candidate_seal=binding(E4/'FEP_E4_R1_CANDIDATE_SEAL.json'),E5_started=False,NEXT=NEXT,sealed_at=now(),**boundary)
    seal['logical_digest']=digest(seal);emit('EXTERNAL_ACCEPTANCE_SEAL',seal)
    print('PASS_EXTERNAL_AUDIT_RECONCILED; exact audited bindings='+str(len(refs))+'; E5 not started',flush=True)

if __name__=='__main__':main()
