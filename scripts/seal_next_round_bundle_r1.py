"""Seal current nine candidates and a reviewable, immutable unified artifact list."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,json,xml.etree.ElementTree as ET
from scripts.next_round_bundle_r1 import ROOT,P,BASELINE,write,read,bind,exact,verify_protected,atomic_bytes
from src.v4.confirmation import detect_confirmation

PACKAGES={
 'V4-11':'reports/v4_11/candidate_r1/V4_11_CANDIDATE_EXTERNAL_REAUDIT_HANDOFF_R2.json',
 'A02':'reports/next_round_r1/A02_CANDIDATE_EXTERNAL_REAUDIT_HANDOFF_R1.json',
 'A03':'reports/audits/A03_R2_1_CANDIDATE_EXTERNAL_REAUDIT_HANDOFF_R1.json',
 'A04':'reports/audits/A04_R2_CANDIDATE_EXTERNAL_REAUDIT_HANDOFF_R1.json',
 'A05':'reports/next_round_r1/A05_CANDIDATE_EXTERNAL_REAUDIT_HANDOFF_R1.json',
 'OWNER':'reports/audits/OWNER_REGISTRY_SCOPED_BOOTSTRAP_CANDIDATE_CLOSURE_R1.json',
 'A06':'reports/audits/A06_R2_CANDIDATE_CLOSURE_R1.json',
 'A07':'reports/audits/A07_R2_CANDIDATE_EXTERNAL_REAUDIT_HANDOFF_R1.json',
 'READER_DI':'reports/audits/HISTORICAL_PUBLICATION_READER_DI_CANDIDATE_CLOSURE_R1.json'}

def task_paths():
    entry=read(P+'BATCH_STAGE_ENTRY_R1.json');old=set(entry['baseline_tracked_paths']);paths=set()
    # Only task-owned additions. Prior FEP artifacts, docs/design and tmp stay untouched.
    for folder in ('config','scripts','src','tests','docs/evidence/next_round_r1'):
        for p in (ROOT/folder).rglob('*'):
            rel=p.relative_to(ROOT).as_posix()
            if folder=='config' and not p.name.startswith(('a02_','a03_','a04_','a05_','a07_','baostock_binding_tolerance_policy_r2','v4_11_confirmation_','v4_11_legacy_','v4_migration_allocation_registry_r2')):continue
            if p.name.startswith('.env') or '.pytest_cache' in rel:continue
            if p.is_file() and rel not in old and '__pycache__' not in rel and p.suffix not in ('.pyc','.tmp','.lock'):paths.add(rel)
    for folder in ('data/v4/confirmation_candidates_r1','data/v4/a02_rps_history_r1','data/v4/a03_forward_pit_r2','data/v4/a05_legacy_exact_r1',
        'data/v4/source_evidence/a04_r2','data/v4/source_evidence/a06_r2','data/v4/source_evidence/a07_r2','data/v4/source_evidence/a03_a04_a07_r2_original_bytes',
        'data/v4/source_evidence/next_round_r1_original_bytes','data/v4/source_evidence/v4_11_candidate_r1_archive','reports/v4_11/candidate_r1','reports/next_round_r1'):
        if (ROOT/folder).exists():
            for p in (ROOT/folder).rglob('*'):
                rel=p.relative_to(ROOT).as_posix()
                if p.is_file() and rel not in old:paths.add(rel)
    prefixes=('A02_','A03_','A04_','A05_','A06_','A07_','OWNER_REGISTRY_SCOPED_BOOTSTRAP_','OWNER_A06_READER_DI_','HISTORICAL_PUBLICATION_READER_DI_')
    for p in (ROOT/'reports/audits').iterdir():
        rel=p.relative_to(ROOT).as_posix()
        if p.is_file() and rel not in old and p.name.startswith(prefixes):paths.add(rel)
    for p in (ROOT/'docs/audits').iterdir():
        rel=p.relative_to(ROOT).as_posix()
        if p.is_file() and rel not in old and p.name.startswith(('A02_','A03_','A05_','NEXT_ROUND_','V4_11_')):paths.add(rel)
    paths.add('data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R4_CANDIDATE.json')
    return sorted(paths)

def main():
    entry=verify_protected();h=read('reports/v4_11/candidate_r1/V4_11_CANDIDATE_EXTERNAL_REAUDIT_HANDOFF_R1.json');summary=read(h['full_market']['path'])
    with gzip.open(exact(summary['input_publication']),'rt',encoding='utf8') as f:inputs=json.load(f)
    with gzip.open(exact(summary['confirmation_publication']),'rt',encoding='utf8') as f:stored=json.load(f)
    if detect_confirmation(inputs)!=stored:raise ValueError('REAL_CONFIRMATION_INDEPENDENT_READBACK_FAILED')
    suites=list(ET.parse(ROOT/'reports/v4_11/candidate_r1/TARGETED_FINAL_R3.xml').getroot().iter('testsuite'))
    total={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    if not suites or total['failures'] or total['errors']:raise ValueError('V4_11_TARGETED_NOT_PASSED')
    review=write('reports/v4_11/candidate_r1/ENGINEERING_REVIEW_REMEDIATION_R1.json',dict(status='PASS_ENGINEERING_REMEDIATION_ONLY',
        reviewer='/root/a03_a04_a07',scope='PEER_CODE_REVIEW_NOT_INDEPENDENT_EXTERNAL_ACCEPTANCE',external_acceptance=False,
        issues=[dict(id='CURRENT_FACT_DATE',remediation='Enforce exact target trade_date for current facts'),
                dict(id='WHOLE_D0_D2_BINDING',remediation='Bind complete canonical D0 row digest plus exact primary scenario'),
                dict(id='FROZEN_WRAPPER_TAMPER',remediation='Rebuild frozen head with all original scope/calendar/row guards'),
                dict(id='D2_PARENT_SPLIT',remediation='Current reducer prior payload must equal the frozen prior-session row'),
                dict(id='PUBLICATION_CUTOFF_FUTURE',remediation='Reject cutoff later than actual current UTC'),
                dict(id='CANDIDATE_DB_BOUNDARY',remediation='Controlled publisher role; exact parent row; commit-time completeness; append-only')],
        regression=bind('reports/v4_11/candidate_r1/TARGETED_FINAL_R3.xml'),old_draft_archives=bind('reports/v4_11/candidate_r1/R1_DRAFT_BINDING_ARCHIVE_R1.json')))
    golden=read(h['golden_expectations']['path']);golden.update(executable_vectors=bind('tests/v4_11/test_confirmation.py'),persistence_vectors=bind('tests/v4_11/test_persistence.py'))
    g=write('reports/v4_11/candidate_r1/INDEPENDENT_GOLDEN_EXPECTATIONS_R2.json',golden)
    h.update(runtime=[bind(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'src/v4').glob('confirmation*.py'))],
        migration=bind('src/workbench_db/migrations/v4_postgres/026_confirmation_events_candidate_r1.sql'),
        golden_expectations=g,targeted_regression=bind('reports/v4_11/candidate_r1/TARGETED_FINAL_R3.xml'),targeted_summary=total,engineering_review=review,
        superseded_draft=bind('reports/v4_11/candidate_r1/V4_11_CANDIDATE_EXTERNAL_REAUDIT_HANDOFF_R1.json'),
        real_full_market_readback='PASS_EXACT_ACCEPTED_SOURCE_PROJECTION_AND_D0_RECOMPUTATION',version='1.1.0')
    write(PACKAGES['V4-11'],h)
    for name,proof,task,runtime,limitation in [
        ('A02','reports/audits/A02_RPS_HISTORY_BOOTSTRAP_EVIDENCE_R3.json','V4_A02_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_TASK_R2_20261001.md',
            ['src/v4/rps_pit_history_a02_v1.py','src/v4/rps_history_reader_a02_v1.py','src/v4/rps_history_producer_a02_r2.py'],'RECONSTRUCTED_CORRECTED_CANDIDATE_PUBLICATIONS_NOT_ACCEPTED'),
        ('A05','reports/audits/A05_EXACT_RECOVERY_EVIDENCE_R2.json','V4_A05_LEGACY_VALID_MEMBER_EXACT_PRODUCER_TASK_R2_20261001.md',
            ['src/sector/legacy_valid_member_a05_v1.py'],'CURRENT_SNAPSHOT_ONLY_LEGACY_BINDING_NOT_EXTERNAL_ACCEPTED')]:
        write(PACKAGES[name],dict(contract_id=name+'_CANDIDATE_HANDOFF_V1',status='CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',baseline_commit=BASELINE,
            proof=bind(proof),stage_contract=bind('docs/evidence/next_round_r1/'+task),runtime_bindings=[bind(p) for p in runtime],
            targeted_regression=bind('reports/audits/A02_A05_TARGETED_TESTS_R3.xml'),independent_source_readback_script=bind('scripts/verify_a02_a05_candidate_readback_r1.py'),
            external_condition_status=limitation,external_acceptance=False,accepted_heads=entry['protected_heads'],permissions=entry['permissions'],
            clean_joint=P+'BATCH_CLEAN_CHECKOUT_R1.json',next_stage='STOP_WAIT_FOR_INDEPENDENT_EXTERNAL_REAUDIT'))
    records={name:dict(status='CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',handoff=bind(path)) for name,path in PACKAGES.items()}
    for name,record in records.items():
        payload=read(record['handoff']['path']);record['execution_result']=payload.get('execution_result',payload.get('technical_candidate','COMPLETE_ENGINEERING_CANDIDATE'))
        record['external_conditions']=payload.get('external_condition_status',payload.get('blockers',[]))
    write('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R11_CANDIDATE.json',dict(contract_id='V4_CROSS_STAGE_CANDIDATE_REGISTRY_R11',
        status='CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',baseline_commit=BASELINE,accepted_parent_registry=bind('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R10.json'),
        active_registry_changed=False,entries=records,permissions=entry['permissions'],stage_head_action='KEEP',data_head_action='KEEP',external_acceptance=False))
    write(P+'BATCH_CANDIDATE_HANDOFF_R1.json',dict(contract_id='V4_NEXT_ROUND_NINE_PACKAGE_HANDOFF_V1',status='CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',
        baseline_commit=BASELINE,master_task=entry['stage_contract'],stage_entry=bind(P+'BATCH_STAGE_ENTRY_R1.json'),task_count=10,work_package_count=9,
        packages=records,candidate_registry=bind('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R11_CANDIDATE.json'),
        protected_heads=entry['protected_heads'],protected_representations=bind(P+'BATCH_PROTECTED_REPRESENTATIONS_R1.json'),
        DataHead='2026-09-30',StageHead='V4_00_TO_V4_10_ACCEPTED',permissions=entry['permissions'],v4_12_implemented=False,
        owner_registry_bulk_accept=False,amount_A_formal_branch='DISABLED',external_acceptance=False,
        engineering_complete=True,real_external_conditions_do_not_block_mainline=True,clean_joint=P+'BATCH_CLEAN_CHECKOUT_R1.json',
        next_stage='STOP_AFTER_UNIFIED_COMMIT_PUSH_WAIT_FOR_INDEPENDENT_EXTERNAL_REAUDIT'))
    paths=task_paths();paths+=['reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R11_CANDIDATE.json']
    paths=sorted(set(paths)-{P+'BATCH_CANDIDATE_ARTIFACT_MANIFEST_R1.json'})
    write(P+'BATCH_CANDIDATE_ARTIFACT_MANIFEST_R1.json',dict(contract_id='V4_NEXT_ROUND_CANDIDATE_ARTIFACT_MANIFEST_V1',baseline_commit=BASELINE,
        artifacts=[bind(p) for p in paths],unrelated_changes_preserved=['artifacts/fep_20260930','artifacts/fep_r2_20260930','docs/audits/FEP_*','docs/design','tmp'],
        accepted_head_action='KEEP',external_acceptance=False))
    verify_protected();print(json.dumps(dict(status='CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',packages=list(PACKAGES),artifacts=len(paths))))
if __name__=='__main__':main()
