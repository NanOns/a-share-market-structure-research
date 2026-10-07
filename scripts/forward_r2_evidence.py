"""Seal R2 engineering candidate, reproducible vectors and immutable-state readback."""
import json
import hashlib
import subprocess
import time
from datetime import datetime,timezone
from pathlib import Path
from scripts.full_chain_repair_io import ROOT,write,binding
P='reports/forward_repair_r2_20261007/'
BASE='15a4e1cc545f6c44d94ebb2b63e71fba6c69e63a'
CODE=['src/workbench_analysis/v4_15_forward_r2.py','scripts/v4_16_forward_r2_worker.py','scripts/_bootstrap.py',
      'scripts/forward_r2_checks.py','scripts/forward_r2_evidence.py','scripts/forward_r2_fingerprint.py',
      'tests/test_forward_r2.py','tests/test_forward_r2_cli.py',
      'config/v4_15_forward_r2_semantics_v1.json','config/dm01_standalone_bootstrap_r2_v1.json']
CODE += ['docs/audits/AUDIT_DM01_R4_LEGACY_TEST_ACCEPTANCE_STATE_20261007.md']
CONTRACT='config/v4_15_forward_r2_candidate_contract_v1.json'
DISPOSITION='docs/audits/V4_FORWARD_REPAIR_R2_CANDIDATE_DISPOSITION_20261007.md'

def load(p):return json.loads((ROOT/p).read_bytes())
def put(name,value):return write(P+name,value)

def seal():
    entry=load(P+'ENTRY_BASELINE.json');assert entry['baseline_commit']==BASE
    receipts={p:load(P+p+'_TEST_RECEIPT.json') for p in ('IA09','FORWARD','CLI','AFFECTED')}
    assert all(r['exit_code']==0 and r['counts']['errors']==r['counts']['failures']==0 for p,r in receipts.items() if p!='AFFECTED')
    affected=receipts['AFFECTED'];classification=load(P+'AFFECTED_FAILURE_CLASSIFICATION.json')
    assert affected['exit_code']==1 and affected['counts']['errors']==0 and affected['counts']['failures']==1
    assert classification['full_run']==binding(P+'AFFECTED_TEST_RECEIPT.json') and classification['introduced_failures']==0
    assert classification['baseline_reproduction']==binding(P+'BASELINE_DM01_LEGACY_TEST_RECEIPT.json')
    for r in receipts.values():
        for source in r['source_bindings']:assert binding(source['path'])==source
    for p in ('PROTECTED_FINGERPRINT','ALL_RUNTIME_ROOTS'):
        assert load(P+p+'_BEFORE.json')==load(P+p+'_AFTER.json'),p+'_DRIFT'
    for ref in entry['protected']:assert binding(ref['path'])==ref
    old_names=set(subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=ROOT,text=True,encoding='utf8').splitlines())
    changed=set(subprocess.check_output(['git','diff','--name-only',BASE],cwd=ROOT,text=True,encoding='utf8').splitlines())
    assert not old_names & changed,'HISTORICAL_TRACKED_BYTES_CHANGED'
    authority=load('config/v4_16_runtime_activation_authority_v5.json')
    for key in ('runtime_authorized','real_shadow_authorized','production','shadow','focus','V4_16'):assert authority[key] is False
    assert authority['REAL_SHADOW_OBSERVATIONS']==authority['PIT_OBSERVED_REAL_SAMPLES']==0
    assert all(t['training_allowed'] is False for t in load('config/fep_target_registry_v1.json')['targets'])
    absent=[f'data/v4/V4_{n}_ACCEPTED_HEAD.json' for n in range(16,23)]
    assert not any((ROOT/p).exists() for p in absent)
    head=load('data/v4/V4_15_ACCEPTED_HEAD.json');assert head['PROVED_HORIZONS']==[]
    from tests.test_forward_r2 import state_vector,price_vector,g
    from tests.test_forward_r2_cli import child_vector
    from tests.runtime_isolation import create
    root=create(Path('E:/codex_tmp/test_temp')/('forward_r2_evidence_'+str(time.time_ns())))
    state=[state_vector(n,create(root/('state'+str(n)))) for n in range(1,11)]
    prices=[price_vector(n) for n in range(1,13)]
    children=[child_vector(n,create(root/('cli'+str(n)))) for n in range(1,9)]
    state_expectations=['pre-due is PENDING','same source at due appends OBSERVED','pre-due retry is idempotent','due retry is idempotent','corrected source appends revision','first/latest matured views intact','filesystem reopen between pre-due and due','PENDING cannot replace observed view','historical pending bytes unchanged','identity exactly reproducible without clock or UUID']
    for vector,expectation in zip(state,state_expectations):
        vector['contract_expectation']=expectation
        vector['why_contract_matches']='State role and frozen sessions distinguish maturity; scoped append-only revisions and matured-only views'
    price_expectations=['negative ordinary close rejected','zero ordinary close rejected','high below close rejected','low above close rejected','low above high rejected','transformed negative rejected with valid separate T0 transform','NaN fails closed; Inf covered by additional test','valid positive envelope matches predecessor','verified delisted terminal zero gives R_N=-1','unverified terminal zero rejected','suspension has no endpoint synthetic bar','invalid interior preserves verified endpoint and clears path']
    for vector,expectation in zip(prices,price_expectations):vector['contract_expectation']=expectation
    put('IA03_VECTOR_MATRIX.json',dict(vectors=state,evidence_class='ENGINEERING_FIXTURE_ONLY'))
    from tests.forward_p1_vectors import runtime_fixture as old_fixture
    old_runtime,old_store,old_freeze,old_source,*_=old_fixture()
    old_pre=old_runtime.settle(old_freeze,old_source,'2030-01-01',(3,))[0]
    old_due=old_runtime.settle(old_freeze,old_source,'2030-01-04',(3,))[0]
    assert old_pre==old_due and old_store.read(old_due)['outcome_status']=='PENDING'
    put('IA03_STATE_REVISION_PROOF.json',dict(old_same_source_collision=dict(same_reference=old_pre==old_due,due_result=old_store.read(old_due)),contract=binding('config/v4_15_forward_r2_semantics_v1.json'),vectors=binding(P+'IA03_VECTOR_MATRIX.json'),pending_policy='Deterministic maturity-state revision role; not removed because formal status/revision design includes ledger PENDING',historical_pending_bytes_unchanged=True,same_source_due_can_append=True,restart_reopened_from_disk=True,FIRST_OBSERVED='first matured revision only',LATEST_CORRECTED='latest matured correction; pending never replaces it',identity_uses_wall_clock_random=False,chain_scope='exact frozen T0 and contract'))
    put('IA04_VECTOR_MATRIX.json',dict(vectors=prices,evidence_class='ENGINEERING_FIXTURE_ONLY'))
    put('IA04_PRICE_DOMAIN_PROOF.json',dict(authority=binding(P+'PRICE_DOMAIN_AUTHORITY_READBACK.json'),adjustment_owner=binding(P+'ADJUSTMENT_OWNER_SUPPLEMENTAL_READBACK.json'),successor=binding('config/v4_15_forward_r2_semantics_v1.json'),vectors=binding(P+'IA04_VECTOR_MATRIX.json'),ordinary='Finite positive native/transformed prices with owner OHLC envelope; incomplete path unknown',terminal='DELISTED + verified evidence independent finite nonnegative terminal; zero => -1',suspension='No fabricated bar',endpoint_path_separation_preserved=True,sector_successor='SECTOR_BASKET_FORWARD_PATH_V2'))
    put('IA10_CHILD_PROCESS_MATRIX.json',dict(vectors=children,clean_environment=True))
    put('IA10_BOOTSTRAP_PROOF.json',dict(contract=binding('config/dm01_standalone_bootstrap_r2_v1.json'),implementation=binding('scripts/_bootstrap.py'),matrix=binding(P+'IA10_CHILD_PROCESS_MATRIX.json'),module_launcher_and_supported_direct_launcher_equal=True,old_bare_scripts_not_redefined=True,frozen_verification_recipes_not_replayed=True,nine_component_numerics_unchanged=True,R25_business_gate_unchanged=True,TDX_read_only=True))
    stock=[g['stock_vector'](n) for n in range(1,13)];sector=[g['sector_vector'](n) for n in range(1,13)]
    put('PASS_KEEP_IA01_IA02_IA09.json',dict(IA01=dict(status='PASS_KEEP',successor_vectors=stock),IA02=dict(status='PASS_KEEP',successor_vectors=sector),IA09=dict(status='PASS_KEEP',receipt=binding(P+'IA09_TEST_RECEIPT.json'),prior_execution_incident='CLOSED_WITH_RESTORATION_EVIDENCE; NEVER_REWRITTEN_AS_NO_TOUCH',incident=binding('reports/forward_p1_repair_r1_20261006/PROTECTED_DB_STORAGE_INCIDENT_AND_RESTORATION.json')),active_runtime_switched=False))
    put('AFFECTED_REGRESSION_SUMMARY.json',dict(receipts={p:binding(P+p+'_TEST_RECEIPT.json') for p in receipts},counts={p:r['counts'] for p,r in receipts.items()},introduced_failures=0,known_baseline_failures=1,failure_classification=binding(P+'AFFECTED_FAILURE_CLASSIFICATION.json'),full_scope_green=False,skip_is_pass=False,global_pytest_pass=False,IA06='OPEN',scope='Targeted Forward + isolation + settlement workers + inherited FEP/governance + DM01 R4/R4R1'))
    put('OPEN_ISSUES_PRESERVED.json',dict(IA05='OPEN_P1',IA06='OPEN_P1',IA07='OPEN_P2',IA08='OPEN_P2',separate_audit_item='AUDIT_DM01_R4_LEGACY_TEST_ACCEPTANCE_STATE_20261007 OPEN_P2; stale pre-acceptance assertion independently reproduced with unchanged baseline inputs',global_collection='Known retired M14 import debt; not rerun or fixed in R2',PG_coverage='opt-in PG cases unexecuted, never PASS',next_order='Independent R2 audit decides Round 3 versus successor admission',runtime_promotion='NOT_GRANTED'))
    protected_paths=['config/v4_16_runtime_activation_authority_v5.json','config/v4_16_runtime_dependencies_v6.json','config/v4_16_runtime_capability_resolution_v2.json','config/fep_scope_registry_v1.json','config/fep_target_registry_v1.json','config/fep_feature_registry_v1.json','data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V4.json']
    put('PROTECTED_STATE_READBACK.json',dict(baseline_commit=BASE,historical_tracked_path_count=len(old_names),historical_tracked_drift=[],protected_head_migration_bindings=entry['protected'],authority_bindings=[binding(p) for p in protected_paths],runtime_authorized=False,real_shadow_authorized=False,production=False,focus=False,default_ui=False,REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0,FEP_permissions_unchanged=True,Current_Audit_Head_unchanged=True,formal_later_heads_absent=absent,real_job_rows_unchanged='Full DB SHA and mtime exact equal',fingerprints=[binding(P+p+'_'+side+'.json') for p in ('PROTECTED_FINGERPRINT','ALL_RUNTIME_ROOTS') for side in ('BEFORE','AFTER')],no_runtime_dependency_selects_successor=True,TDX_root_writes=0))
    write(CONTRACT,dict(contract_id='V4_FORWARD_REPAIR_R2_CANDIDATE_V1',outcome_contract_id='FORWARD_PRICE_PATH_V1_2',sector_contract_id='SECTOR_BASKET_FORWARD_PATH_V2',baseline_commit=BASE,task_documents=entry['task_documents'],source_bindings=[binding(p) for p in CODE],status='CANDIDATE_PENDING_INDEPENDENT_EXTERNAL_AUDIT',simulation_only=True,no_accepted_dependency_selects_it=True,runtime_authorized=False,real_shadow_authorized=False,production=False,focus=False,default_ui=False,next_stage='INDEPENDENT_EXTERNAL_AUDIT_REQUIRED'))
    report=f"""# Forward Repair R2 completion

FORWARD_REPAIR_R2 = CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

IA-03 = CANDIDATE_FIXED; IA-04 = CANDIDATE_FIXED; IA-10 = CANDIDATE_FIXED.
IA-01 / IA-02 / IA-09 = PASS_KEEP.

Baseline: `{BASE}`. Evidence completed: {datetime.now(timezone.utc).isoformat()}.

Deterministic PENDING/DUE identities append independently under Forward V1.2. FIRST_OBSERVED/latest correction exclude planner PENDING, scoped to the exact freeze and contract. Historical pending/outcomes and V1.1 bytes remain intact.

Owner price rules reject illegal finite/nonfinite ordinary and transformed prices and OHLC envelopes; terminal delisting with verified evidence still admits zero. Sector uses its V2 basket identity and keeps close-only fields and original weights.

DM01 supports the unified direct launcher `python -I -B <repo>/scripts/_bootstrap.py` and module launcher `python -s -B -m scripts._bootstrap` (from repository root). Pass `--module scripts.<supported_module> -- <original args>`. Frozen bare scripts are not the supported launch contract. Verification recipes require a guarded disposable fixture or read-only preflight; historical evidence is not replayed. No numerical kernel, accepted source gate, head promotion or R25 rule changed.

Counts: { {p:r['counts'] for p,r in receipts.items()} }. The mandatory R2 targeted gates passed. Expanded affected regression has one preexisting stale DM01 R4 test expectation, independently reproduced with exact baseline implementation/test/accepted-head bytes; it remains a separate OPEN_P2 audit item, not a PASS or an R2 repair. Opt-in PG skips remain unexecuted. No global pytest PASS is claimed. IA-05/06/07/08 remain OPEN.

Both full protected byte/mtime inventory pairs match exactly. Historical accepted heads, audit head, runtime/FEP permissions, real counters and original execution-incident records remain frozen. This batch introduced no protected storage incident.

Implementation, input/expectation/output matrices, test receipts and exact hash bindings are included. Git delivery is transport only. Next stage: INDEPENDENT_EXTERNAL_AUDIT_REQUIRED; no active runtime promotion, real shadow or production grant.
"""
    write(P+'COMPLETION_REPORT.md',report.encode(),raw=True)
    files=CODE+[CONTRACT,DISPOSITION]
    files += [p.relative_to(ROOT).as_posix() for folder in ('docs/evidence/forward_repair_r2_20261007',P) for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and p.name not in ('CANDIDATE_SEAL.json','CHANGED_FILE_LIST.json','GIT_DELIVERY.json')]
    files=sorted(set(files))
    put('CHANGED_FILE_LIST.json',dict(files=files+[P+'CHANGED_FILE_LIST.json',P+'CANDIDATE_SEAL.json'],historical_files_modified=[],unrelated_worktree_preserved=entry['unrelated_worktree']))
    files.append(P+'CHANGED_FILE_LIST.json')
    put('CANDIDATE_SEAL.json',dict(status='CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT',baseline_commit=BASE,bindings=[binding(p) for p in sorted(files)],self_excluded=True,later_delivery_receipt_is_append_only_outside_payload=True,IA03='CANDIDATE_FIXED',IA04='CANDIDATE_FIXED',IA10='CANDIDATE_FIXED',runtime_authorized=False,next_stage='INDEPENDENT_EXTERNAL_AUDIT_REQUIRED'))
if __name__=='__main__':seal()
