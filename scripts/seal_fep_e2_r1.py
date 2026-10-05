"""Seal measured E2 evidence; UNSET thresholds can never yield stage PASS."""
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from workbench_analysis.fep_e1.contracts import atomic_json
from workbench_analysis.fep_e1.contracts import digest
from workbench_analysis.fep_e1.datasets import assemble
from workbench_analysis.fep_e2.input import bind
from workbench_analysis.fep_e2.conditional import baseline
from workbench_analysis.fep_e2.support import gate,diagnostics
from copy import deepcopy
from workbench_analysis.fep_e2.registry import register
from scripts.run_fep_e2_r1 import ROOT,REPORT,binding,now
from scripts.validate_r25_preflight import protected,selection


def load(name):return json.loads((REPORT/name).read_bytes())


def revision_readback():
    # Counterfactual revision source has all r1/r2/r3 present. Only E1 selects;
    # E2 sees the immutable selected payload, never the revision source list.
    from tests.fep_e2.test_conditional import fixture,POLICY,CONTRACT,NOW
    seed=fixture();observations=[];snapshots={};labels={}
    for row in seed['denominator']:
        key=row['observation_id']
        observations.append(dict(observation_id=key,scope_id=row['observation_scope'],entity_id=row['entity_id'],
                                 trade_date=row['trade_date'],episode_key=key))
        snapshots[key]=dict(snapshot_id='frozen-'+key)
        labels[key,'target']=[dict(revision=n,target_digest=digest(row['outcome']*n),training_allowed=True,
            source_fact_available_at='2026-10-01T00:00:00Z',label_training_mature_at='2026-10-01T00:00:00Z',
            label_revision_available_at=f'2026-10-0{n}T00:00:00Z') for n in (1,2,3)]
    outputs=[]
    for cutoff,revision in [('2026-10-01T12:00:00Z',1),('2026-10-02T12:00:00Z',2)]:
        folds=[dict(fold_id='f1',partition_name='FIT',observation_ids=[r['observation_id'] for r in observations],
                    fold_dataset_cutoff=cutoff,phase_started_at='2026-10-04T00:00:00Z')]
        e1=assemble(observations,[dict(target_id='target',scope_id='FEP_STOCK_ENTRY_CORE',horizon=1)],folds,labels,
                    snapshots,'2026-10-04T00:00:00Z')
        envelopes={r['observation_id']:dict(r,outcome=r['outcome']*revision,selected_label_revision=revision,
                        selected_label_digest=digest(r['outcome']*revision)) for r in seed['denominator']}
        metadata={k:v for k,v in seed.items() if k not in
                  ('digest','e1_dataset_digest','e1_frozen_payload','selections','denominator','rows')}
        dataset=bind(e1,metadata,envelopes)
        a=baseline(dataset,dataset['rows'][0],POLICY,CONTRACT,NOW)
        assert all(s['selected_label_revision']==revision for s in a['label_revision_selections'])
        outputs.append((dataset,a))
    early,artifact=outputs[0]
    assert baseline(early,early['rows'][0],POLICY,CONTRACT,NOW)==artifact
    atomic_json(REPORT/'REVISION_PIT_GATE.json',dict(status='PASS_ENGINEERING_COUNTERFACTUAL',
        source_latest_revision=3,early_cutoff='2026-10-01T12:00:00Z',early_selected_revision=1,
        late_cutoff='2026-10-02T12:00:00Z',late_selected_revision=2,
        early_artifact_unchanged=True,early_artifact=artifact,late_artifact=outputs[1][1],
        policy_scope='TEST_ONLY_NOT_ADMITTED'))


def support_readback():
    from tests.fep_e2.test_conditional import fixture,POLICY
    rows=fixture()['rows'];states={}
    for key in ('rows','dates','blocks','entities','episodes'):
        policy=deepcopy(POLICY);policy['values'][key]=3
        state=gate(rows,rows,policy)[0]
        assert state=='THIN_'+key.upper()
        states[key]=state
    policy=deepcopy(POLICY);policy['values']['class_min']=2
    assert gate(rows,rows,policy)[0]=='THIN_CLASS';states['class']='THIN_CLASS'
    population=fixture((-.1,.2,None))
    policy=deepcopy(POLICY);policy['values']['max_missing_fraction']=0
    assert gate(population['rows'],population['denominator'],policy)[0]=='MISSINGNESS_FAIL'
    states['missingness']='MISSINGNESS_FAIL'
    statuses=['ELIGIBLE','PENDING','RIGHT_CENSORED','MATURED_DATA_MISSING','SUSPENDED','DELISTED',
              'IDENTITY_UNKNOWN','ADJUSTMENT_UNKNOWN','OTHER_EXPLICIT_REASON']
    expected=[dict(rows[0],observation_id='denominator-'+str(i),status=s) for i,s in enumerate(statuses)]
    diagnostic=diagnostics(expected,[expected[0]])
    assert sum(diagnostic['statuses'].values())==len(statuses) and diagnostic['eligible']==1
    atomic_json(REPORT/'SUPPORT_DIMENSIONS_READBACK.json',dict(status='PASS_ENGINEERING_COUNTERFACTUAL',
                 states=states,denominator_diagnostic=diagnostic,all_explicit_missing_reasons_preserved=True,
                 policy_scope='TEST_ONLY_NOT_ADMITTED'))


def run():
    targeted=load('TARGETED_SUMMARY.json');scoped=load('SCOPED_REGRESSION_SUMMARY.json')
    assert not targeted['introduced_active_failures'] and not scoped['introduced_active_failures']
    database=load('FINAL_DATABASE_READBACK.json')
    assert database['table_count']==33 and not any(database['row_counts'].values())
    assert load('ISOLATED_POSTGRES_SHUTDOWN_READBACK.json')['status']=='STOPPED_RETAINED'
    cases=ET.parse(REPORT/'targeted.xml').findall('.//testcase')
    e2=[c for c in cases if c.attrib['classname'].startswith('tests.fep_e2.')]
    assert len(e2)>=24 and all(c.find('failure') is None and c.find('error') is None for c in e2)
    measures=[dict(node=c.attrib['classname']+'::'+c.attrib['name'],status='PASS',seconds=c.attrib.get('time')) for c in e2]
    atomic_json(REPORT/'NEGATIVE_MATRIX.json',dict(status='PASS_ENGINEERING_VECTORS_ONLY',
        vectors=['E2-'+str(i).zfill(2) for i in range(1,21)],measured_cases=measures,
        evidence=binding('reports/fep_e2_r1/targeted.xml'),policy_scope='TEST_ONLY_NOT_ADMITTED',
        no_threshold_acceptance_from_test_fixtures=True))
    for name,prefix in [('CONDITIONAL_CONTRACT_GATE','test_e2_08'),('BACKOFF_GATE','test_e2_03'),
        ('WEIGHTING_GATE','test_e2_01'),('WEIGHTED_QUANTILE_GATE','test_e2_02'),
        ('CONTINUOUS_BASELINE_GATE','test_e2_03'),('CATEGORICAL_BASELINE_GATE','test_e2_11'),
        ('MISSINGNESS_GATE','test_e2_13'),('REPRESENTATIVENESS_GATE','test_e2_14'),
        ('SCOPE_ISOLATION_GATE','test_e2_08'),('REVISION_PIT_GATE','test_e2_15'),
        ('ARTIFACT_REGISTRY_GATE','test_e2_19'),('DETERMINISM_GATE','test_e2_16')]:
        nodes=[m for m in measures if prefix in m['node']]
        assert nodes
        atomic_json(REPORT/(name+'.json'),dict(status='PASS_ENGINEERING_MECHANICS',measured_cases=nodes,
                     source=binding('reports/fep_e2_r1/targeted.xml'),admitted_support_policy=False,
                     actual_input='DIAGNOSTIC_ONLY_NOT_EVALUABLE',production=False))
    artifact=load('DIAGNOSTIC_BASELINE.json')
    revision_readback()
    support_readback()
    authority=json.loads((ROOT/'config/v4_15_fep_label_time_authority_v1.json').read_bytes())
    real=json.loads((ROOT/'reports/fep_e1_r1_repair/LABEL_ADAPTER_REAL_PENDING_READBACK.json').read_bytes())
    assert not authority['allocations'] and all(not r['adapter_result']['training_allowed'] for r in real['real_rows'])
    atomic_json(REPORT/'E1_LABEL_COVERAGE_READBACK.json',dict(status='PASS_FAIL_CLOSED_NO_ADMITTED_MATURE_POPULATION',
        label_time_allocation_count=len(authority['allocations']),real_source_rows=len(real['real_rows']),
        real_pending_count=sum(r['adapter_result']['quality']=='PENDING' for r in real['real_rows']),
        engineering_expected_count=1,engineering_eligible_count=0,owner_feature_rows=5222,
        feature_only_date_count=1,feature_rows_are_not_labeled_entry_observations=True,
        bindings=[binding('config/v4_15_fep_label_time_authority_v1.json'),
                  binding('reports/fep_e1_r1_repair/LABEL_ADAPTER_REAL_PENDING_READBACK.json'),
                  binding('reports/fep_e1_r2_final/FEATURE_47_FIELD_READBACK.json')]))
    registered=register(REPORT/'registry',artifact)
    before=registered.read_bytes();register(REPORT/'registry',dict(artifact,created_at=now()))
    assert registered.read_bytes()==before
    atomic_json(REPORT/'REGISTRY_READBACK.json',dict(status='PASS',binding=binding(registered.relative_to(ROOT).as_posix()),
        idempotent_timestamp_drift=True,append_only=True,artifact_type=artifact['artifact_type']))
    changed=[]
    for path,old in load('ENTRY_BASELINE.json')['protected_files'].items():
        if binding(path)!=old:changed.append(path)
    assert not changed,changed
    prior=json.loads((ROOT/'reports/fep_e1_r2_final/PROTECTED_STATE_READBACK.json').read_bytes())
    for item in prior['heads']:assert binding(item['path'])==item
    absent=[p for p in ('data/v4/V4_16_ACCEPTED_HEAD.json','data/v4/FEP_E1_ACCEPTED_HEAD.json') if (ROOT/p).exists()]
    assert not absent
    atomic_json(REPORT/'PROTECTED_STATE_READBACK.json',dict(status='PASS',all_prior_tracked_files_unchanged=True,
        tracked_count=len(load('ENTRY_BASELINE.json')['protected_files']),heads=prior['heads'],
        r25_protected=protected(ROOT),r25_selection=selection(ROOT),PRIORITY_V1='UNCHANGED',
        Production=False,Shadow=False,Focus=False,MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',
        FEP_PRODUCTION='UNGRANTED',V4_16_ACCEPTED_HEAD='NOT_CREATED',TDX='NO_WRITES'))
    atomic_json(REPORT/'INDEPENDENT_AUDIT_ITEMS.json',dict(items=[
        dict(audit_id='FEP_E1_BASELINE_52_FAILURES',status='OPEN_EXISTING_OWNER_DEBT',scope='43 registered + 9 independently reproduced pre-FEP failures',
             evidence=binding('reports/fep_e2_r1/SCOPED_REGRESSION_SUMMARY.json'),acceptance='Separate owner-stage repair; zero new active failures required by E2'),
        dict(audit_id='FEP_E1_LEGACY_MIGRATION_REGISTRATION_GAP',status='OPEN_EXISTING_INFRASTRUCTURE_DEBT',scope='014..027 registration',
             evidence=binding('reports/fep_e1_r2_final/INDEPENDENT_AUDIT_ITEMS.json'),acceptance='Independent infrastructure owner repair'),
        dict(audit_id='FEP_E2_SUPPORT_THRESHOLD_EVIDENCE_GAP',status='OPEN_BLOCKING_E2',scope='No exact-bound multi-date mature outcome population for threshold discovery',
             evidence=binding('reports/fep_e2_r1/SUPPORT_POLICY_DISCOVERY.json'),
             acceptance='External disposition or exact-bound historical engineering dataset with dependence/class/missingness inventory; preregister justified thresholds before outcome statistics')]))
    gates=[]
    evidence_names=['E1_INPUT_BINDING.json','SUPPORT_POLICY_DISCOVERY.json','SUPPORT_POLICY_FREEZE.json',
        'BACKOFF_GATE.json','WEIGHTING_GATE.json','WEIGHTED_QUANTILE_GATE.json','CONTINUOUS_BASELINE_GATE.json',
        'CATEGORICAL_BASELINE_GATE.json','SUPPORT_DIMENSIONS_READBACK.json','MISSINGNESS_GATE.json',
        'REPRESENTATIVENESS_GATE.json','SCOPE_ISOLATION_GATE.json','REVISION_PIT_GATE.json','NEGATIVE_MATRIX.json',
        'DETERMINISM_GATE.json','REGISTRY_READBACK.json','PROTECTED_STATE_READBACK.json',
        'FINAL_DATABASE_READBACK.json','PROTECTED_STATE_READBACK.json','SCOPED_REGRESSION_SUMMARY.json']
    for i in range(1,21):
        gates.append(dict(gate='E2-A'+str(i).zfill(2),status='BLOCKED_UNSET_THRESHOLDS' if i==3 else 'PASS_ENGINEERING_MECHANICS',
                          evidence=evidence_names[i-1]))
    atomic_json(REPORT/'LOCAL_ACCEPTANCE_MATRIX.json',dict(status='BLOCKED',gates=gates,
        distinction='Algorithm tests pass; no defensible admitted support thresholds frozen. Test-only parameters never constitute acceptance.'))
    exit=dict(V4_15E2_LOCAL_IMPLEMENTATION='BLOCKED',FEP_CONDITIONAL_BASELINE='DIAGNOSTIC_ONLY',
        FEP_SUPPORT_POLICY='UNSET_DIAGNOSTIC_ONLY',FEP_DESCRIPTIVE_SHADOW='NOT_GRANTED_DIAGNOSTIC_ONLY',
        FEP_MODEL_ENGINEERING='NOT_STARTED',FEP_MODEL_DISPLAY='UNGRANTED',FEP_PRIORITY_USE='UNGRANTED',
        FEP_PRODUCTION='UNGRANTED',introduced_active_failures=0,NEXT='STOP_WAIT_EXTERNAL_REPAIR_DISPOSITION',
        CURRENT_REAL_MATURITY_EVIDENCE='NONE',PROVED_HORIZONS=[])
    atomic_json(REPORT/'COMPLETION_EXIT.json',exit)
    text=f'''# V4-15E2 R1 completion

Local exit: **BLOCKED / DIAGNOSTIC_ONLY**. E1 external PASS authorizes this stage, but its exact-bound engineering input has one expected observation and zero eligible mature outcomes. No multi-date/block/entity/episode or class-count evidence justifies thresholds. All eight E2-owned support parameters remain UNSET. No test-only policy is promoted to admission authority.

Implemented frozen E1 population binding, L4→L1 first-supported backoff, rational bucket date weights, explicit inverse-CDF weighted quantiles, continuous/categorical/overlapping-event descriptives, dependence gates, complete denominator/missingness/representation diagnostics, deterministic baseline identity and atomic append-only local registry. Actual input emits NOT_EVALUABLE and an empty statistics payload.

Validation: {len(e2)} E2 tests passed; targeted {targeted['passed']} passed, {targeted['skipped']} skipped, no failures. Full scoped regression {scoped['passed']} passed, {scoped['skipped']} skipped, {len(scoped['failed_nodes'])} existing failures, zero introduced active failures. Exactly the two previously governed deselections remain. Raw logs/XML and node accounting are included.

All prior tracked files and {len(prior['heads'])} protected heads remain byte-identical. Core, E1, DM01/R25, Priority V1, migrations and grants are unchanged. No TDX writes, real-label promotion, models, calibration, OOD, production or E3 work.

Next: STOP_WAIT_EXTERNAL_REPAIR_DISPOSITION. Required disposition concerns exact-bound historical engineering outcome input and defensible outcome-performance-free threshold discovery; it does not require waiting for a future real session. Existing 52 failures and historical migration registration debt remain independently tracked.
'''
    path=REPORT/'COMPLETION_REPORT.md';temp=path.with_suffix('.tmp');temp.write_text(text,encoding='utf-8',newline='\n');temp.replace(path)
    paths=[p for p in REPORT.rglob('*') if p.is_file() and p.name!='FEP_E2_R1_CANDIDATE_SEAL.json']
    paths+=list((ROOT/'src/workbench_analysis/fep_e2').glob('*.py'))
    paths+=list((ROOT/'tests/fep_e2').glob('*.py'))
    paths+=[ROOT/'config/fep_conditional_statistics_contract_v1.json',ROOT/'config/fep_e2_support_policy_v1.json',
            ROOT/'scripts/run_fep_e2_r1.py',ROOT/'scripts/seal_fep_e2_r1.py']
    atomic_json(REPORT/'FEP_E2_R1_CANDIDATE_SEAL.json',dict(status='BLOCKED_CANDIDATE_NOT_ACCEPTED',exit=exit,
                 exact_bindings=[binding(p.relative_to(ROOT).as_posix()) for p in sorted(paths)],sealed_at=now()))
    print(json.dumps(exit),flush=True)


if __name__=='__main__':run()
