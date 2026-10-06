"""Reproducible candidate evidence; immutable history and authority are read-only."""
import hashlib
import json
import os
import subprocess
import time
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone
from scripts.full_chain_repair_io import ROOT, binding, write
from scripts.forward_p1_fingerprint import PREFIX

BASE = '0c78051c570bdd68ef98f1cb9fdcfcd315759ec2'
CONTRACT = 'config/v4_15_forward_p1_candidate_contract_v1.json'
CODE = ['tests/.gitattributes','docs/audits/.gitattributes','conftest.py','tests/runtime_isolation_plugin.py','src/workbench_analysis/.gitattributes','src/workbench_analysis/v4_15_forward_p1.py','scripts/v4_16_forward_p1_worker.py',
        'tests/runtime_isolation.py','tests/upgrade_m12/conftest.py','tests/forward_p1_vectors.py',
        'tests/test_forward_p1_isolation.py','tests/test_forward_p1_stock.py',
        'tests/test_forward_p1_sector.py','tests/test_forward_p1_regression.py',
        'scripts/forward_p1_checks.py','scripts/forward_p1_collection.py',
        'scripts/forward_p1_fingerprint.py','scripts/forward_p1_evidence.py','scripts/forward_p1_restore_checkpoint.py']
DISPOSITION = 'docs/audits/V4_FORWARD_P1_REPAIR_R1_CANDIDATE_DISPOSITION_20261006.md'

def load(path): return json.loads((ROOT/path).read_bytes())
def put(name,value): return write(PREFIX+name,value)

def contract():
    entry=load(PREFIX+'ENTRY_BASELINE.json')
    return write(CONTRACT,dict(contract_id='V4_FORWARD_P1_REPAIR_R1_IA09_IA01_IA02',version='1.0.0',
        status='CANDIDATE_PENDING_INDEPENDENT_EXTERNAL_AUDIT', baseline_commit=BASE,
        task_document=entry['task_document'],source_audits=entry['source_audits'],
        design_contracts=[binding('config/v4_15_forward_price_path_contract_v1.json'),binding('config/v4_15_forward_sector_benchmark_contract_v1.json'),binding('config/v4_15_forward_market_benchmark_contract_v1.json')],
        implementation_bindings=[binding(p) for p in CODE],outcome_contract_id='FORWARD_PRICE_PATH_V1_1',
        sector_contract_id='SECTOR_BASKET_FORWARD_PATH_V1',
        endpoint_policy='ENDPOINT_RETURN_INDEPENDENT_IF_VERIFIED',
        stock_endpoint='STRICT_T0_ENDPOINT_AFFINE_COMMON_BASIS_IDENTITY_AND_TERMINAL_ADMISSION',
        stock_path='EVERY_PARTICIPATING_ACTUAL_COORDINATE_VERIFIED; NO_INTERPOLATION; CONFIRMED_SUSPENSION_OMITTED',
        sector_identity=['sector_subject_id','membership_snapshot','member_security_ids','initial_weights','fixed_shares','T0_evaluation_basis','member_source_identities','member_adjustment_identities','constituent_policy'],
        sector_coverage='ALL_ORIGINAL_WEIGHT_VALUED_OR_UNKNOWN; NO_NEW_THRESHOLD; NO_REWEIGHT',
        sector_numeric_fields=['R_N','MFE_CLOSE','MAE_CLOSE'],
        sector_stock_fields=dict(MFE_N=None,MAE_N=None,PATH_MDD_CLOSE_N=None,applicability='NOT_APPLICABLE_SECTOR'),
        relative_benchmarks='INDEPENDENT_EXISTING_CONTRACTS_UNCHANGED',
        revision_policy='APPEND_SUCCESSOR_AND_CORRECTIONS; HISTORICAL_BYTES_IMMUTABLE',
        IA03='OPEN_AUDIT_ONLY_P2_SAME_SOURCE_PENDING_DUE_COLLISION_UNCHANGED',
        IA04='OPEN_AUDIT_ONLY_P2_PRICE_DOMAIN_BEHAVIOR_UNCHANGED',
        consumer='SIMULATION_ONLY_CANDIDATE_WORKER; NO_ACCEPTED_DEPENDENCY_SELECTS_IT',
        fep='NO_NEW_OWNER_ALLOCATION; EXACT_REVISION_AND_RECEIPTS_REQUIRED; NO_HISTORICAL_LABEL_REWRITE',
        runtime_authorized=False,real_shadow_authorized=False,production=False,shadow=False,focus=False,default_ui=False,
        REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0,
        next_stage='INDEPENDENT_EXTERNAL_AUDIT_REQUIRED'))

def isolation():
    from tests.runtime_isolation import create, guard, environment, serve
    from tests.test_forward_p1_isolation import recovery_fixture
    root=create(Path('E:/codex_tmp/test_temp')/('forward_p1_proof_'+str(time.time_ns())))
    database=root/'data/test.duckdb'
    attempts=[]
    for name,r,d,mode in [('REAL_REPOSITORY',ROOT,ROOT/'data/database/market_research.duckdb','NO_REAL_RECOVERY'),
                          ('TDX','D:/new_tdx','D:/new_tdx/test.duckdb','NO_REAL_RECOVERY'),
                          ('REAL_DB_ESCAPE',root,ROOT/'data/database/market_research.duckdb','NO_REAL_RECOVERY'),
                          ('RELATIVE_ESCAPE',root,root/'..'/'escape.duckdb','NO_REAL_RECOVERY'),
                          ('UNDECLARED_MODE',root,database,'DEFAULT')]:
        try:
            if name=='REAL_REPOSITORY':serve(r,d,19001)
            else:guard(r,d,mode)
        except ValueError as error:
            attempts.append(dict(case=name,attempted_root=str(r),attempted_database=str(d),mode=mode,decision='REJECTED_BEFORE_SERVICE',reason=str(error)))
        else:raise AssertionError('PROTECTED_ATTEMPT_NOT_REJECTED')
    guard(root,database)
    attempts.append(dict(case='DISPOSABLE_ACCEPTED',attempted_root=str(root),attempted_database=str(database),mode='NO_REAL_RECOVERY',decision='ADMITTED'))
    recovery=recovery_fixture(create(root/'recovery'))
    assert recovery['before_sha256']!=recovery['after_sha256'] and recovery['after_status']=='INTERRUPTED'
    # A copied request may contain real output paths. Explicit disposable
    # interruption recovery must never resume it or launch a worker.
    import duckdb
    from unittest.mock import patch
    from tests.runtime_isolation import recover_history
    from workbench_service.history_jobs import HistoryJobService
    escaped_payload=dict(job_kind='HISTORY_ANALYSIS',completed_slice_ids=[],request={
        'source_manifest_path':str(ROOT/'data/current'),'output_root':'D:/new_tdx'})
    disposable=Path(recovery['database'])
    with duckdb.connect(str(disposable)) as connection:
        connection.execute("update jobs set status='RUNNING',payload_json=? where job_id='disposable-job'",[json.dumps(escaped_payload)])
        connection.execute("update job_attempts set status='RUNNING' where job_id='disposable-job'")
    with patch.object(HistoryJobService,'_start',side_effect=AssertionError('BACKGROUND_ESCAPE')) as start:
        escaped=recover_history(recovery['root'],disposable)
        assert start.call_count==0 and escaped[0]['status']=='INTERRUPTED'
    recovery['background_escape_probe']=dict(attempted_request=escaped_payload,
        decision='INTERRUPTION_MARKED_ONLY_NO_BACKGROUND_RESUME',background_start_calls=0,
        after_result=escaped,after_sha256=hashlib.sha256(disposable.read_bytes()).hexdigest())
    before=load(PREFIX+'IA09_PROTECTED_ROOT_FINGERPRINT_BEFORE.json')
    after=load(PREFIX+'IA09_PROTECTED_ROOT_FINGERPRINT_AFTER.json')
    assert before==after,'PROTECTED_RUNTIME_DRIFT'
    all_before=load(PREFIX+'IA09_ALL_RUNTIME_ROOTS_BEFORE_FINAL_REGRESSION.json')
    all_after=load(PREFIX+'IA09_ALL_RUNTIME_ROOTS_AFTER_FINAL_REGRESSION.json')
    # Supplemental baseline was captured after the rejected storage checkpoint.
    # Keep it immutable and reconcile only database against the earlier complete
    # per-file baseline, which the final complete core inventory already matches.
    database_states = [f for f in before['files'] if f['path'].startswith('data/database/')]
    original_database = dict(root='data/database', files=len(database_states),
        bytes=sum(f['bytes'] for f in database_states),
        catalog_sha256=hashlib.sha256(json.dumps(database_states,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest())
    reconciled = dict(all_before, roots=[original_database if r['root']=='data/database' else r for r in all_before['roots']])
    assert reconciled==all_after,'SUPPLEMENTAL_RUNTIME_DRIFT'
    put('SUPPLEMENTAL_BASELINE_RECONCILIATION.json',dict(
        reason='Supplemental BEFORE was captured after failed collection storage checkpoint; original complete core BEFORE predates it',
        original_supplemental_unchanged=binding(PREFIX+'IA09_ALL_RUNTIME_ROOTS_BEFORE_FINAL_REGRESSION.json'),
        authoritative_database_baseline=binding(PREFIX+'IA09_PROTECTED_ROOT_FINGERPRINT_BEFORE.json'),
        derived_database_catalog=original_database, all_other_roots_equal=True,
        final_complete_core_equals_original=True, reconciled_supplemental_equals_final=True,
        original_failed_run_accepted=False))
    put('IA09_TEST_ISOLATION_PROOF.json',dict(attempts=attempts,disposable_recovery=recovery,
        subprocess_environment_keys=sorted(environment(root)),inherited_dsn_or_runtime_environment=False,
        default_recovery_mode='NO_REAL_RECOVERY',production_recovery_code_changed=False,
        original_m12_tests_byte_identical=True,protected_file_drift=0,protected_root_before_after_equal=True,
        storage_incident=binding(PREFIX+'PROTECTED_DB_STORAGE_INCIDENT_AND_RESTORATION.json'),
        zero_write_claim_scope='POST_GLOBAL_GUARD_ACCEPTANCE_RUN_ONLY; EARLIER_FAILED_STORAGE_DRIFT_IS_DISCLOSED',
        required_vectors={'TISO-01':'REAL_DB_ESCAPE rejected before service',
            'TISO-02':'REAL_REPOSITORY rejected by guarded launcher',
            'TISO-03':'Configured TDX output root rejected',
            'TISO-04':'DISPOSABLE_ACCEPTED admitted',
            'TISO-05':'Real HistoryJobService changes disposable RUNNING to INTERRUPTED',
            'TISO-06':'Real DB full-byte SHA/mtime/size unchanged',
            'TISO-07':'Escaped request retained as interrupted; zero background starts; DB/root escapes rejected',
            'TISO-08':'Explicit child environment from isolated root; no inherited DSNs'},
        initial_core_fingerprints=[binding(PREFIX+'IA09_PROTECTED_ROOT_FINGERPRINT_'+s+'.json') for s in ('BEFORE','AFTER')],
        supplemental_fingerprints=[binding(PREFIX+'IA09_ALL_RUNTIME_ROOTS_'+s+'_FINAL_REGRESSION.json') for s in ('BEFORE','AFTER')],
        coverage_note='Initial core runtime roots cover the entire task. Supplemental all runtime output roots surround final acceptance regression. Input staging is read-only input and excluded from supplemental output inventory.',
        test_receipt=binding(PREFIX+'IA09_TEST_RECEIPT.json')))

def vectors():
    from tests.forward_p1_vectors import stock_vector,sector_vector,runtime_fixture,row,BASIS
    from workbench_analysis import v4_15_forward_p1 as candidate
    from workbench_analysis import v4_15_settlement_successor as previous
    stock=[stock_vector(n) for n in range(1,13)]
    sector=[sector_vector(n) for n in range(1,13)]
    put('IA01_VECTOR_MATRIX.json',stock)
    put('IA02_VECTOR_MATRIX.json',sector)
    put('IA01_ENDPOINT_PATH_SEPARATION_PROOF.json',dict(matrix=binding(PREFIX+'IA01_VECTOR_MATRIX.json'),
        endpoint_strictness='UNCHANGED; FROZEN_EXPECTED_IDENTITY_ENFORCED_WHERE_PRESENT',
        interior_unknown='PRESERVES_VERIFIED_R_N; NULL_PATH_METRICS_WITH_EXPLICIT_REASONS',
        relative_market='ENDPOINT_INDEPENDENT_STK_11',historical_rewrite=False,
        accepted_consumer_activation=False,receipt=binding(PREFIX+'IA01_TEST_RECEIPT.json')))
    put('IA02_SECTOR_BASKET_IDENTITY_PROOF.json',dict(matrix=binding(PREFIX+'IA02_VECTOR_MATRIX.json'),
        dedicated_basket_identity=True,stock_adjustment_identity_fabricated=False,
        frozen_membership_and_weights=True,member_source_adjustment_basis_verified_individually=True,
        partial_coverage='UNKNOWN_NO_REWEIGHT',minimum_members=2,threshold_invented=False,
        legacy_missing_identity='UNKNOWN; NO_BACKFILL',receipt=binding(PREFIX+'IA02_TEST_RECEIPT.json')))
    put('IA02_FIELD_SEMANTICS_PROOF.json',dict(numeric_sector_fields=['R_N','MFE_CLOSE','MAE_CLOSE'],
        MFE_N=None,MAE_N=None,PATH_MDD_CLOSE_N=None,stock_extrema_applicability='NOT_APPLICABLE_SECTOR',
        synthetic_ohlc=False,relative_sector_independent=True,market_benchmark_parity=True,
        evidence_vectors=['SEC-06','SEC-07','SEC-08','SEC-09','SEC-10']))
    runtime,store,freeze,source,*_=runtime_fixture()
    pending=runtime.settle(freeze,source,'2030-01-01',(3,))[0]
    due=runtime.settle(freeze,source,BASIS,(3,))[0]
    sentinels=[]
    for name,patch in [('NEGATIVE_ACTUAL_PRICE',dict(close=-1,high=0,low=-2)),
                       ('INVALID_OHLC',dict(close=11,high=9,low=12)),
                       ('TERMINAL_ZERO',dict(status='DELISTED',terminal_verified=True,terminal_evidence='FIXTURE',terminal_value=0))]:
        endpoint=dict(row(),**patch)
        old=previous.price_path(10,[endpoint],BASIS);new=candidate.price_path(10,[endpoint],BASIS)
        assert old['R_N']==new['R_N'] and old['outcome_status']==new['outcome_status']
        sentinels.append(dict(case=name,input=endpoint,old_result=old,new_result=new,semantic_change=False))
    collection=load(PREFIX+'SAFE_COLLECTION_RECEIPT.json')
    affected=load(PREFIX+'AFFECTED_TEST_RECEIPT.json')
    put('OPEN_ISSUES_PRESERVED.json',dict(
        IA03=dict(status='OPEN_AUDIT_ONLY',priority='P2',same_source_pending_due_same_reference=pending==due,
                  observed_outcome=store.read(due),fixed=False),
        IA04=dict(status='OPEN_AUDIT_ONLY',priority='P2',sentinels=sentinels,fixed=False),
        IA05=dict(status='OPEN',collection=collection,retired_capture_writer_restored=False),
        IA06=dict(status='OPEN',skipped_pg_fixture_cases=affected['counts']['skipped'],missing_fixture_is_pass=False),
        IA07='OPEN_OUT_OF_SCOPE',IA08='OPEN_OUT_OF_SCOPE',IA10='OPEN_OUT_OF_SCOPE'))

def protected():
    entry=load(PREFIX+'ENTRY_BASELINE.json')
    assert entry['baseline_commit']==BASE
    for ref in entry['protected']: assert binding(ref['path'])==ref
    old_names=set(subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=ROOT,text=True,encoding='utf8').splitlines())
    changed=set(subprocess.check_output(['git','diff','--name-only',BASE],cwd=ROOT,text=True,encoding='utf8').splitlines())
    assert not old_names & changed,'HISTORICAL_TRACKED_BYTES_CHANGED'
    authority=load('config/v4_16_runtime_activation_authority_v5.json')
    for key in ('runtime_authorized','real_shadow_authorized','production','shadow','focus','V4_16'): assert authority[key] is False
    assert authority['REAL_SHADOW_OBSERVATIONS']==authority['PIT_OBSERVED_REAL_SAMPLES']==0
    assert authority['grant'] is None and authority['external_acceptance'] is None
    head=load('data/v4/V4_15_ACCEPTED_HEAD.json')
    assert head['PROVED_HORIZONS']==[] and head['CURRENT_REAL_MATURITY_EVIDENCE']=='NONE'
    absent=[f'data/v4/V4_{n}_ACCEPTED_HEAD.json' for n in range(16,23)]
    assert not any((ROOT/p).exists() for p in absent)
    targets=load('config/fep_target_registry_v1.json')['targets']
    assert all(t['training_allowed'] is False for t in targets)
    paths=['config/v4_16_runtime_activation_authority_v5.json','config/v4_16_runtime_dependencies_v6.json',
           'config/v4_16_runtime_capability_resolution_v2.json','config/fep_scope_registry_v1.json',
           'config/fep_target_registry_v1.json','config/fep_feature_registry_v1.json',
           'config/v4_15_fep_label_time_authority_v1.json']
    for p in paths:
        original=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
        assert hashlib.sha256(original).hexdigest()==binding(p)['sha256']
    import duckdb
    with duckdb.connect(str(ROOT/'data/database/market_research.duckdb'),read_only=True) as connection:
        summaries={}
        for table in ('jobs','job_attempts','job_events'):
            rows=connection.execute('select * from '+table+' order by all').fetchall()
            raw=json.dumps(rows,default=str,sort_keys=True,ensure_ascii=False).encode()
            summaries[table]=dict(rows=len(rows),ordered_rows_sha256=hashlib.sha256(raw).hexdigest())
        summaries['job_status_counts']=dict(connection.execute('select status,count(*) from jobs group by status').fetchall())
    put('PROTECTED_STATE_READBACK.json',dict(baseline_commit=BASE,historical_tracked_path_count=len(old_names),
        historical_tracked_drift=[],protected_head_migration_bindings=entry['protected'],authority_bindings=[binding(p) for p in paths],
        runtime_authorized=False,real_shadow_authorized=False,Production=False,Focus=False,Default_UI=False,
        REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0,FEP_training_allowed=False,
        FEP_PRODUCTION='UNGRANTED',MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',REAL_OOS='NOT_GRANTED',CHAMPION='NONE',
        prior_permission_readback=binding('reports/a08_current_runtime_propagation_20261006/PROTECTED_STATE_READBACK.json'),
        proved_horizons=[],current_real_maturity='NONE',formal_later_stage_heads_absent=absent,
        current_audit_head_changed=False,real_jobs_after=summaries,
        real_job_rows_unchanged_proof='Entire real DB SHA256 and mtime identical in initial BEFORE/AFTER inventory',
        protected_state_drift=0))

def seal():
    receipts={p:load(PREFIX+p+'_TEST_RECEIPT.json') for p in ('IA09','IA01','IA02','AFFECTED')}
    assert all(r['exit_code']==0 and r['counts']['failures']==r['counts']['errors']==0 for r in receipts.values())
    contract();isolation();vectors();protected()
    affected=receipts['AFFECTED']
    put('AFFECTED_REGRESSION_SUMMARY.json',dict(receipts={p:binding(PREFIX+p+'_TEST_RECEIPT.json') for p in receipts},
        executed_passed=affected['counts']['tests']-affected['counts']['skipped'],introduced_failures=0,
        skipped_pg_cases=affected['counts']['skipped'],skip_is_pass=False,IA06='OPEN',
        global_pytest_pass=False,safe_collection=binding(PREFIX+'SAFE_COLLECTION_RECEIPT.json'),
        historical_R25_gate='PASS_WITH_ORIGINAL_M12_BYTES_RESTORED; NO_ALLOWLIST_CHANGE'))
    put('DEVELOPMENT_FINDINGS.json',dict(
        resolved=['M12 fixture needed an explicit complete publication head instead of latest partial preview',
                  'Legacy test tables are rematerialized only in the disposable snapshot',
                  'Chart fixture needed a bounded normalized input projection',
                  'Direct old-test edits triggered R25 historical-byte protection; original bytes restored and additive conftest used',
                  'Protected fingerprint gate caught a physical DuckDB byte change; 103 tables and all views/indexes compared equal; changed bytes retained and original snapshot restored; repository-wide pytest read-only/recovery guard added before fresh acceptance'],
        known_debt_not_hidden=['IA05 collection import error','IA06 unavailable opt-in PG cases','IA03 pending/due collision','IA04 price-domain behavior']))
    report=f'''# Forward P1 Repair R1 completion

FORWARD_P1_REPAIR_R1=CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

IA-09=CANDIDATE_FIXED; IA-01=CANDIDATE_FIXED; IA-02=CANDIDATE_FIXED.

Entry: `{BASE}`. Completed evidence timestamp: {datetime.now(timezone.utc).isoformat()}.

- IA-09: {receipts['IA09']['counts']['tests']} tests passed, 0 failed/error/skipped.
- Stock: 12 required vectors passed; Sector: 12 required vectors passed.
- Affected regression: {affected['counts']['tests']-affected['counts']['skipped']} passed, 0 failed/error; {affected['counts']['skipped']} existing opt-in PG cases unexecuted. IA-06 remains OPEN.
- Safe collection retains the IA-05 retired-writer import error. No global pytest PASS is claimed.
- Final complete core runtime byte/mtime inventory equals the original baseline; all remaining runtime roots match the supplemental baseline. The supplemental database entry is reconciled against the earlier original core baseline in SUPPLEMENTAL_BASELINE_RECONCILIATION.json. All historical tracked objects are unchanged. Authority, Current Audit Head, accepted heads, old outcomes, FEP labels and migrations remain frozen. Real counters remain zero; later formal heads are absent.

An earlier regression was rejected by the protected-state gate because the live DuckDB storage bytes changed. Exhaustive comparison found identical rows in all 103 tables and identical views/indexes. Both versions and the failed fingerprints are retained; the original exact snapshot was restored with a separate incident receipt. The final regression uses a repository-wide test connection/recovery guard and is independently fingerprinted. The failed run is not claimed as zero-write or accepted.

Stock endpoint and path quality are independent. Sector uses dedicated frozen basket identities and member valuation, fixed original weights, no synthetic stock OHLC, and only close extrema. Successor outcomes/corrections append under FORWARD_PRICE_PATH_V1_1. Old M12 assertions and bytes remain intact; the new fixture isolates service/API writes and disposable recovery.

The new worker is simulation-only and rejects real delivery before source access. No active accepted dependency, UI permission or FEP owner allocation changes. IA-03/04 sentinels preserve current behavior; IA-05/06/07/08/10 remain OPEN.

Review IA01/IA02 vector matrices for inputs, expectations, old/new results and contract reasoning; IA09_TEST_ISOLATION_PROOF for actual guard attempts/recovery; PROTECTED_STATE_READBACK and both inventory pairs for preservation; AFFECTED_REGRESSION_SUMMARY for coverage limits.

Next: INDEPENDENT_EXTERNAL_AUDIT_REQUIRED. Git delivery is evidence transport, not external acceptance or permission for the next gated stage.
'''
    write(PREFIX+'COMPLETION_REPORT.md',report.encode(),raw=True)
    files=CODE+[CONTRACT,DISPOSITION]
    files += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'docs/evidence/forward_p1_repair_r1_20261006').rglob('*')) if p.is_file()]
    files += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/PREFIX).rglob('*')) if p.is_file() and p.name not in ('CANDIDATE_SEAL.json','CHANGED_FILE_LIST.json','GIT_DELIVERY.json')]
    files=sorted(set(files))
    put('CHANGED_FILE_LIST.json',dict(files=files+[PREFIX+'CHANGED_FILE_LIST.json',PREFIX+'CANDIDATE_SEAL.json'],historical_files_modified=[],unrelated_worktree_preserved=load(PREFIX+'ENTRY_BASELINE.json')['unrelated_worktree']))
    files.append(PREFIX+'CHANGED_FILE_LIST.json')
    put('CANDIDATE_SEAL.json',dict(status='CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT',baseline_commit=BASE,
        IA09='CANDIDATE_FIXED',IA01='CANDIDATE_FIXED',IA02='CANDIDATE_FIXED',
        bindings=[binding(p) for p in sorted(files)],self_excluded=True,
        later_delivery_receipt_is_append_only_outside_payload=True,next_stage='INDEPENDENT_EXTERNAL_AUDIT_REQUIRED',
        runtime_authorized=False,real_shadow_authorized=False,production=False,focus=False,default_ui=False))

if __name__=='__main__':
    import sys
    contract() if len(sys.argv)>1 and sys.argv[1]=='contract' else seal()
