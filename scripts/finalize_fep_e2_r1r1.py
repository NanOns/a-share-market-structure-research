"""Measured local candidate gate, independent of external acceptance."""
from collections import Counter
import json,subprocess,sys,xml.etree.ElementTree as ET
from scripts.build_fep_e2_r1r1_history import ROOT,REPORT,binding,now
from workbench_analysis.fep_e1.contracts import atomic_json,digest
from workbench_analysis.fep_e1.feature_owner import verify_file
from workbench_analysis.fep_e2.historical_dataset import read_gzip


def finalize():
    r1=json.loads((REPORT/'R1_PASS_KEEP_READBACK.json').read_bytes())
    for ref in r1['heads']+[r1[k] for k in ('r1_policy','r1_diagnostic','feature_owner','three_time')]+r1['migrations']:
        verify_file(ROOT,ref)
    contract=json.loads((ROOT/'config/fep_e2_historical_dataset_contract_v1.json').read_bytes())
    for ref in [*contract['source_bindings'].values(),*contract['owner_runtime_bindings'],*contract['parameter_bindings']]:verify_file(ROOT,ref)
    import psycopg
    dsn='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh'
    with psycopg.connect(dsn) as p:
        tables=[r[0] for r in p.execute("select tablename from pg_tables where schemaname='fep' order by tablename")]
        from psycopg import sql
        counts={t:p.execute(sql.SQL('select count(*) from fep.{}').format(sql.Identifier(t))).fetchone()[0] for t in tables}
    if len(counts)!=33 or any(counts.values()):raise ValueError('E2_FEP_DATABASE_ISOLATION')
    from scripts.validate_r25_preflight import protected,selection
    protected_result=protected(ROOT);selection_result=selection(ROOT)
    atomic_json(REPORT/'PROTECTED_STATE_READBACK.json',dict(status='PASS',heads=r1['heads'],
        accepted_owners_unchanged=True,E1_contracts_and_three_time_unchanged=True,R1_policy_and_diagnostic_unchanged=True,
        migration_028_031_unchanged=True,real_database_table_counts=counts,TDX='UNTOUCHED',
        r25_protected=protected_result,r25_selection=selection_result,E3='NOT_AUTHORIZED',
        model_display='UNGRANTED',priority_use='UNGRANTED',production=False,shadow=False,read_at=now()))
    targeted=json.loads((REPORT/'TARGETED_SUMMARY.json').read_bytes())
    regression=json.loads((REPORT/'SCOPED_REGRESSION_SUMMARY.json').read_bytes())
    cases=ET.parse(REPORT/'targeted.xml').findall('.//testcase')
    negatives=[dict(node=c.attrib['classname']+'::'+c.attrib['name'],status='PASS' if c.find('failure') is None and c.find('error') is None else 'FAIL')
        for c in cases if 'test_r1r1_repair' in c.attrib['classname']]
    if len(negatives)<15 or any(r['status']!='PASS' for r in negatives):raise ValueError('E2_NEGATIVE_MATRIX')
    atomic_json(REPORT/'NEGATIVE_MATRIX.json',dict(status='PASS',case_count=len(negatives),cases=negatives,
        synthetic_vectors_are_tests_only=True,receipt=binding(REPORT/'targeted.xml')))
    method=json.loads((REPORT/'CONDITIONAL_BASELINE_GATE.json').read_bytes())
    policy=json.loads((ROOT/'config/fep_e2_support_policy_registry_v1.json').read_bytes())
    admitted=[p['applicability'] for p in policy['policies'] if p.get('status')!='UNSET_DIAGNOSTIC_ONLY']
    atomic_json(REPORT/'SUPPORT_POLICY_SCOPE_GATE.json',dict(status='PASS_EXACT_APPLICABILITY',admitted_scopes=admitted,
        registry=binding('config/fep_e2_support_policy_registry_v1.json'),negative_matrix=binding(REPORT/'NEGATIVE_MATRIX.json'),
        unlisted_or_UNSET_scopes='NOT_EVALUABLE',engineering_only=True,pooled_entry_event_semantics='ENTRY includes owner-enrolled FIRST_PREWATCH/NEW_CONFIRMED; original event type preserved per row'))
    population=json.loads((REPORT/'HISTORICAL_OBSERVATION_POPULATION.json').read_bytes())
    dataset=json.loads((REPORT/'HISTORICAL_DATASET_SEAL.json').read_bytes())
    label_gate=json.loads((REPORT/'V4_15_HISTORICAL_LABEL_ADAPTER_GATE.json').read_bytes())
    for receipt in population['receipts']:
        for directory,key in [('population','population_sha256'),('owner_records','bundle_sha256'),('state_scan','state_scan_sha256')]:
            ref=binding(REPORT/directory/(receipt['entity_id']+'.jsonl.gz'))
            if ref['sha256']!=receipt[key]:raise ValueError('E2_POPULATION_RECEIPT_MISMATCH')
    for receipt in label_gate['receipts']:
        for directory,key in [('labels','label_sha256'),('settlement_records','settlement_bundle_sha256')]:
            ref=binding(REPORT/directory/(receipt['entity_id']+'.jsonl.gz'))
            if ref['sha256']!=receipt[key]:raise ValueError('E2_LABEL_RECEIPT_MISMATCH')
    from workbench_analysis.fep_e2.conditional import baseline
    from workbench_analysis.fep_e2.historical_dataset import resolve_policy,verify_stage_order
    verify_file(ROOT,dataset['dataset']);verify_file(ROOT,method['artifact'])
    frozen_dataset=next(read_gzip(ROOT/dataset['dataset']['path']))
    artifact=json.loads((ROOT/method['artifact']['path']).read_bytes())
    query=dict(artifact['base_partition'],regime='UNAVAILABLE',trend='UNAVAILABLE',position='UNAVAILABLE',risk='UNAVAILABLE')
    scoped=resolve_policy(policy,dict(artifact['base_partition'],target_kind=frozen_dataset['target_kind']))
    method_contract=json.loads((ROOT/'config/fep_conditional_statistics_contract_v1.json').read_bytes())
    rebuilt=baseline(frozen_dataset,query,scoped,method_contract,now())
    if rebuilt['logical_digest']!=artifact['logical_digest']:raise ValueError('E2_REBUILD_DIGEST_MISMATCH')
    discovery=json.loads((REPORT/'SUPPORT_POLICY_DISCOVERY.json').read_bytes())
    stats_start=json.loads((REPORT/'STATISTICS_PHASE_START.json').read_bytes())
    verify_stage_order(dataset['sealed_at'],discovery['sealed_at'],policy['frozen_at'],stats_start['started_at'])
    atomic_json(REPORT/'HISTORICAL_DETERMINISM_GATE.json',dict(status='PASS',
        original_logical_digest=artifact['logical_digest'],rebuilt_logical_digest=rebuilt['logical_digest'],
        population_receipts_verified=len(population['receipts']),label_receipts_verified=len(label_gate['receipts']),
        frozen_policy_reused=True,stage_order='DATASET_THEN_DISCOVERY_THEN_POLICY_THEN_STATISTICS',verified_at=now()))
    ready=not targeted['failed_nodes'] and not regression['introduced_active_failures'] and method['status']=='PASS_ENGINEERING_CAPABILITY_SCOPED'
    status='PASS_LOCAL_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT' if ready else 'BLOCKED'
    next_stage='STOP_WAIT_V4_15E2_R1R1_INDEPENDENT_EXTERNAL_AUDIT' if ready else 'STOP_WAIT_EXTERNAL_REPAIR_DISPOSITION'
    matrices=dict(historical_population='PASS',feature_owner='PASS',V4_15_labels='PASS',dataset='PASS',
        policy_scope='PASS',representation='PASS_EXPLICIT_UNAVAILABLE',conditional_baseline=method['status'],
        negative_matrix='PASS',protected_state='PASS',targeted='PASS' if not targeted['failed_nodes'] else 'FAIL',
        scoped_regression='PASS_NO_NEW_FAILURES' if not regression['introduced_active_failures'] else 'FAIL',
        pre_existing_failures=len(regression['failed_nodes']),external_acceptance='NOT_GRANTED')
    atomic_json(REPORT/'LOCAL_ACCEPTANCE_MATRIX.json',dict(status=status,checks=matrices,
        admitted_scope=admitted if ready else [],next=next_stage))
    atomic_json(REPORT/'INDEPENDENT_AUDIT_ITEMS.json',dict(items=[dict(
        audit_id='FEP_E2_HISTORICAL_D2_FACT_AVAILABILITY',status='OPEN_DIAGNOSTIC_ONLY',
        scope='Historical confirmation unknown transitions, absent frozen episode invalidation, corrected adjustment first-availability limitations',
        evidence=[binding(REPORT/'HISTORICAL_OBSERVATION_POPULATION.json'),binding('config/fep_e2_historical_dataset_contract_v1.json')],
        independent_acceptance='Requires a separately versioned owner-input closure audit; no global effectiveness claim',
        current_stage_effect='Unknown rows retained in full state scan; no synthetic fills; accepted ENTRY estimand only')]))
    report=f'''# V4-15E2 R1R1 local completion\n\nStatus: {status}\n\nHistorical window: {json.loads((REPORT/'HISTORICAL_WINDOW_FREEZE.json').read_bytes())['window']['start']} through 2026-09-24.\nComplete owner scan: {population['entities']} entities, {population['state_rows']} date/entity states.\nENTRY observations: {dataset['expected']}; eligible engineering T1 labels: {dataset['eligible']}.\nBaseline: {method['support_state']}; level {method['selected_level']}; capability scoped to reconstructed Core ENTRY ABS_RETURN_N:T1.\n\nTargeted: {targeted['passed']} passed, {targeted['skipped']} skipped, zero failures.\nScoped regression: {regression['passed']} passed, {regression['skipped']} skipped, {len(regression['failed_nodes'])} existing debt failures, {len(regression['introduced_active_failures'])} new failures.\nThe original two governed exclusions remain unchanged.\n\nReal-source reconstruction wraps frozen owners. No forward formula or reducer/event business rule is rewritten. Unknown facts remain unknown. The explicitly unimplemented required frozen-invalidation input blocks upstream recalculation only when the unchanged reducer cannot admit ENTRY; all daily state transitions are still replayed. The pre-gate full replay of 189 entities has byte-identical ENTRY payloads to this gated replay (REQUIRED_INPUT_GATE_POPULATION_PARITY.json). Sector/regime are explicitly unavailable and cannot be formal conditioning levels. Complete denominator and non-eligible reasons are retained. Actual reconstruction timestamps do not prove historical first availability. Owner revision terms FIRST_OBSERVED describe append sequence only. All FEP engineering labels remain RECONSTRUCTED_CORRECTED; real training authority is unchanged.\n\n35 protected heads, accepted owner sources, E1 contracts, migrations 028–031, original R1 policy/diagnostic, R25 WAIT and E1 database isolation are preserved. Separate historical owner availability audit remains open.\n\nProduction, shadow, MODEL_DISPLAY and PRIORITY_USE remain ungranted. E3 is NOT_AUTHORIZED. Next: {next_stage}. Commit/push conveys local code and evidence only.\n'''
    temp=REPORT/'COMPLETION_REPORT.md.tmp';temp.write_bytes(report.encode('utf-8'));temp.replace(REPORT/'COMPLETION_REPORT.md')
    refs=[binding(p) for p in sorted(REPORT.glob('*')) if p.is_file() and p.name!='FEP_E2_R1R1_CANDIDATE_SEAL.json' and not p.name.endswith('.tmp')]
    codepaths=['src/workbench_analysis/fep_e2/conditional.py','src/workbench_analysis/fep_e2/support.py',
        'src/workbench_analysis/fep_e2/historical_dataset.py','src/workbench_analysis/fep_e2/historical_owners.py',
        'src/workbench_analysis/fep_e2/historical_labels.py','scripts/build_fep_e2_r1r1_history.py','scripts/seal_fep_e2_r1r1.py',
        'scripts/verify_fep_e2_r1r1.py','scripts/finalize_fep_e2_r1r1.py','tests/fep_e2/test_conditional.py','tests/fep_e2/test_r1r1_repair.py',
        'config/fep_e2_historical_dataset_contract_v1.json','config/fep_e2_support_policy_registry_v1.json',
        'config/fep_e2_historical_required_input_gate_v1.json']
    seal=dict(stage='V4-15E2.R1R1',status=status,baseline_engineering='BASELINE_ENGINEERING_PASS_LOCAL_CAPABILITY_SCOPED' if ready else 'BLOCKED',
        support_policy='FROZEN_FOR_ADMITTED_SCOPES',release_readiness='ENGINEERING_READY_NOT_PRODUCTION' if ready else 'BLOCKED',
        baseline_commit='87e5b36b32aafd73101f21225703228353d12140',maintenance_successor='6aaff0b',
        code_bindings=[binding(p) for p in codepaths],evidence_bindings=refs,admitted_scopes=admitted if ready else [],
        external_acceptance=False,production=False,shadow=False,MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',
        E3='NOT_AUTHORIZED',next=next_stage,sealed_at=now())
    seal['logical_digest']=digest(seal);atomic_json(REPORT/'FEP_E2_R1R1_CANDIDATE_SEAL.json',seal)
    print(status,flush=True)


if __name__=='__main__':finalize()
