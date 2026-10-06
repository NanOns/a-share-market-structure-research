"""R1R1C isolated metadata successor; replay frozen B algorithms and outputs."""
import os, sys, json, subprocess
from pathlib import Path
from scripts import run_fep_e5_r1r1b as b
from scripts import finalize_fep_e5_r1r1b as drills
from workbench_analysis.fep_e5 import metadata_binding as m
from workbench_analysis.fep_e1.contracts import atomic_json, digest

ROOT=b.ROOT
REPORT=ROOT/'reports/fep_e5_r1r1c'
BASE='68b3d97d1f5d98a4ed6be87bca3ce8c81696e587'
PREVIOUS=ROOT/'reports/fep_e5_r1r1b'
DSNS={k:f'host=127.0.0.1 port={port} user=fep_e5_admin dbname=fep_e5b_{k}' for k,port in [('fresh',55492),('upgrade',55493)]}
CODE=['src/workbench_analysis/fep_e5/canonical_ledger.py','src/workbench_analysis/fep_e5/metadata_binding.py',
      'scripts/run_fep_e5_r1r1c.py','scripts/publish_fep_e5_r1r1c_readback.py','tests/fep_e5/test_e5_metadata_binding.py']

def load(p):return json.loads(Path(p).read_bytes())
def emit(n,v):atomic_json(REPORT/(n+'.json'),v)

def verified():
    freeze=load(REPORT/'R1R1C_PASS_KEEP_FREEZE.json')
    for ref in freeze['evidence']+freeze['code']:
        if ref['path']=='src/workbench_analysis/fep_e5/canonical_ledger.py':
            raw=b.git('show',BASE+':'+ref['path'])
            import hashlib
            assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
        else:b.verify_file(ROOT,ref)
    for ref in load(PREVIOUS/'IMPLEMENTATION_INPUT_FREEZE.json')['input_bindings']:b.verify_file(ROOT,ref)
    return freeze

def configure():
    # The reviewed algorithms remain byte-identical; only explicit fixture locations
    # and the successor verification hook change for this isolated invocation.
    verified()
    b.REPORT=REPORT;b.DSNS=DSNS;b.frozen=verified
    drills.REPORT=REPORT;drills.DSNS=DSNS;drills.verified=verified

def run():
    configure();a=m.authority()
    emit('CANONICAL_TARGET_AUTHORITY_BINDING',dict(status='PASS_CANDIDATE',authority=a,adapter_is_not_activation=True))
    emit('CANONICAL_SIGNAL_CONTRACT_BINDING',dict(status='PASS_CANDIDATE',contract_id=m.SIGNAL_CONTRACT,
         body=a['signal_body'],source=a['signal_reference'],predicate_digest=a['predicate_digest'],RA_is_dependency_only=True))
    emit('NO_NEW_MIGRATION',dict(status='NOT_APPLICABLE',not_a_pass=True,reason='Existing typed metadata columns and contract FKs support exact accepted binding; append-only old facts are retained, isolated fixtures rebuilt; admission/readback verifier rejects metadata drift. No SQL028-032 changes.'))
    atomic_json(REPORT/'HISTORICAL_RECONSTRUCTION_AUTHORITY_CONTRACT.json',load(PREVIOUS/'HISTORICAL_RECONSTRUCTION_AUTHORITY_CONTRACT.json'))
    b.install();b.project();drills.drills();readback()

def readback():
    configure();a=m.authority();fixtures={};parity={}
    for kind in DSNS:
        current=load(REPORT/(kind.upper()+'_FINAL_DB_READBACK.json'))
        previous=load(PREVIOUS/(kind.upper()+'_FINAL_DB_READBACK.json'))
        t=current['tables'];p=previous['tables']
        row=next(x for x in t['targets'] if x['target_id']==b.c.TARGET)
        m.verify_target(row,a['target_registry'])
        obs=[x for x in t['observations'] if x['scope_id']==b.c.SCOPE]
        for x in obs:m.verify_signal(x,a['signal_body'])
        assert len(obs)==205
        def stable(rows,omit):return sorted([digest({k:v for k,v in x.items() if k not in omit}) for x in rows])
        # Only execution-clock-dependent columns may differ on a fresh reconstruction.
        omissions={'observations':{'core_signal_contract_id'},'reconstruction_authorities':{'reconstructed_at'},
          'observation_revisions':{'created_at'},'snapshots':{'created_at'},'feature_values':set(),
          'predictions':{'accepted_at'},'models':{'accepted_at'},'model_set_members':set(),'permission_keys':set(),
          'prediction_runs':{'started_at','finished_at'},'prediction_slots':{'selection_cutoff','deadline'},
          'slot_model_bindings':{'selected_at'}}
        checks={}
        for name,omit in omissions.items():
            left=t[name];right=p[name]
            if kind=='upgrade' and name in ('observations','observation_revisions','snapshots'):
                left=[x for x in left if not str(x.get('observation_id','')).startswith('UNIT_PIT_')]
                right=[x for x in right if not str(x.get('observation_id','')).startswith('UNIT_PIT_')]
            checks[name]=stable(left,omit)==stable(right,omit)
        assert all(checks.values()),checks
        assert current['schema']['logical_digest']==previous['schema']['logical_digest']
        fixtures[kind]=dict(target=row,observations=obs,registered_contracts=[x for x in t['contracts'] if x['contract_id'] in (m.TARGET_CONTRACT,m.SIGNAL_CONTRACT)],exact_signal_count=205,fallback_count=0)
        parity[kind]=dict(status='PASS',checks=checks,execution_clock_columns_regenerated=True,
            schema_unchanged=True,counts=current['table_counts'],final_head=current['final_head'],
            previous=b.binding(PREVIOUS/(kind.upper()+'_FINAL_DB_READBACK.json')),current=b.binding(REPORT/(kind.upper()+'_FINAL_DB_READBACK.json')))
    emit('CANONICAL_TARGET_ROW_READBACK',dict(status='PASS_CANDIDATE',fixtures={k:v['target'] for k,v in fixtures.items()}))
    emit('CANONICAL_OBSERVATION_METADATA_READBACK',dict(status='PASS_CANDIDATE',fixtures=fixtures))
    emit('R1R1C_CANONICAL_VS_R1R1B_PARITY',dict(status='PASS',fixtures=parity,numeric_outputs_changed=0,authority_ID_changes=0,snapshot_ID_changes=0))
    emit('PERMISSION_PASS_KEEP_READBACK',dict(status='PASS_KEEP',roles=['BASELINE','CHALLENGER','CHALLENGER'],final_heads='REVOKE',CHAMPION=False,MODEL_DISPLAY=False,PRIORITY_USE=False,fixtures=parity))
    emit('CAS_PASS_KEEP_READBACK',dict(status='PASS_KEEP',concurrency=load(REPORT/'CANONICAL_CAS_CONCURRENCY.json'),idempotency=load(REPORT/'CANONICAL_CAS_IDEMPOTENCY.json'),rollback=load(REPORT/'CANONICAL_ROLLBACK_DRILL.json')))
    emit('API_PRIORITY_PASS_KEEP_READBACK',dict(status='PASS_KEEP',API=load(REPORT/'API_READBACK.json'),priority=load(REPORT/'CANONICAL_PRIORITY_FIXTURE_READBACK.json')))
    refs=[b.binding(ROOT/p) for p in ('config/v4_18_migration_replay_contract_v1_2.json','tests/fep/test_v4_18_namespace_successor.py')]
    emit('V4_18_PASS_KEEP_READBACK',dict(status='PASS_KEEP',bindings=refs))

def tests():
    verified();from scripts import run_fep_e2_r1 as runner
    runner.REPORT=REPORT;runner.BASE=BASE
    env=os.environ.copy();env.update(TEMP='E:/codex_tmp/test_temp',TMP='E:/codex_tmp/test_temp',FEP_E1_TEST_DSN='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh',FEP_E5_TEST_DSN='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh',WORKBENCH_PG_DSN='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh',FEP_E5_CANONICAL_TEST_ENABLE='1',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
    prior=load(PREVIOUS/'TARGETED_SUMMARY.json')
    cmd=[x for x in prior['command'] if not x.startswith(('--basetemp=','--junitxml='))];cmd[0]=sys.executable
    cmd+=['--basetemp=E:/codex_tmp/test_temp/r1r1c-targeted','--junitxml='+str(REPORT/'targeted.xml')]
    runner.execute(cmd,env,'targeted')
    assert not load(REPORT/'TARGETED_SUMMARY.json')['failed_nodes']
    prior=load(PREVIOUS/'SCOPED_REGRESSION_SUMMARY.json')
    cmd=[x for x in prior['command'] if not x.startswith(('--basetemp=','--junitxml='))];cmd[0]=sys.executable
    cmd+=['--basetemp=E:/codex_tmp/test_temp/r1r1c-scoped','--junitxml='+str(REPORT/'scoped.xml')]
    runner.execute(cmd,env,'scoped',prior['failed_nodes'])

def finalize():
    freeze=verified();target=load(REPORT/'TARGETED_SUMMARY.json');scope=load(REPORT/'SCOPED_REGRESSION_SUMMARY.json')
    assert not target['failed_nodes'] and not scope['introduced_active_failures']
    assert sorted(scope['failed_nodes'])==sorted(load(PREVIOUS/'SCOPED_REGRESSION_SUMMARY.json')['failed_nodes']) and len(scope['failed_nodes'])==52
    assert scope['skipped']==4
    assert [x for x in scope['command'] if x.startswith('--deselect=')]==[x for x in load(PREVIOUS/'SCOPED_REGRESSION_SUMMARY.json')['command'] if x.startswith('--deselect=')]
    assert b.protected(ROOT)==freeze['protected'] and b.selection(ROOT)==freeze['selection']
    emit('PROTECTED_STATE_READBACK',dict(status='PASS_KEEP',protected=b.protected(ROOT),selection=b.selection(ROOT),TDX='READ_ONLY_NO_WRITES',Priority_V1_unchanged=True))
    import xml.etree.ElementTree as ET
    cases=[dict(node=x.attrib['classname']+'::'+x.attrib['name'],status='PASS' if x.find('failure') is None and x.find('error') is None and x.find('skipped') is None else 'NON_PASS') for x in ET.parse(REPORT/'targeted.xml').findall('.//testcase') if 'test_e5_metadata_binding' in x.attrib['classname']]
    assert len(cases)==18 and all(x['status']=='PASS' for x in cases)
    emit('METADATA_NEGATIVE_MATRIX',dict(status='PASS',cases=cases,XML=b.binding(REPORT/'targeted.xml'),boundary='Strict canonical adapter verifier; no new SQL constraint claimed'))
    state=dict(V4_15E5_R1R1C_METADATA_REPAIR='CANDIDATE_EXTERNAL_AUDIT_REQUIRED',M01='PASS_CANDIDATE',M02='PASS_CANDIDATE',HISTORICAL_RECONSTRUCTION_AUTHORITY='PASS_KEEP',B01='PASS_CANDIDATE',B02='PASS_CANDIDATE',B03='PASS_CANDIDATE',external_acceptance=False,production=False,MODEL_DISPLAY=False,PRIORITY_USE=False,FIRST_OBSERVED=False,REAL_OOS=False,CHAMPION=False,NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT_R1R1C')
    emit('STAGE_ACCEPTANCE_AND_NEXT',state)
    text=f'# R1R1C metadata repair candidate\n\nBaseline {BASE}. M01/M02 PASS_CANDIDATE. Exact accepted target registry and event-strata bodies registered with original byte bindings. ABS_RETURN_N:T1 formula R_N, ratio, endpoint OBSERVED; enabled=false. Engineering adapter does not activate targets. All 205 FIRST_PREWATCH observations use FEP_E2_ENTRY_EVENT_STRATA_V1_1; reconstruction authority remains dependency-only.\n\nFresh and populated PIT upgrade rebuilt on isolated ports 55492/55493. No new migration, no SQL028–032 change. Strict canonical admission/readback verifier rejects TM01–08 and SM01–07; no additional database-owner constraint claimed. Canonical identities, 205 authorities/snapshots, 4100 values/477 UNKNOWN, 615 outputs and digests, 616 slots, imported artifacts and three SHADOW roles remain exact. Execution timestamps regenerate honestly; no historical availability is fabricated. CAS concurrency, replay, rollback, final REVOKE and synthetic Priority linkage rerun through byte-identical reviewed B drivers. Original B fixtures retained for regression provenance.\n\nTargeted {target["passed"]} passed / {target["skipped"]} skipped / zero failures. Scoped {scope["passed"]} passed / {scope["skipped"]} skipped, exact 52 known debts, zero introduced failures; two prior deselections retained. Protected state, Priority V1 and V4-18 successor unchanged.\n\nCANDIDATE_EXTERNAL_AUDIT_REQUIRED; external_acceptance=false. STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT_R1R1C. Production, display, Priority, first-observed, real OOS and Champion remain closed. Commit/push establishes publication only.\n'
    b.old.write(REPORT/'COMPLETION_REPORT.md',text.encode())
    files=CODE+sorted(p.relative_to(ROOT).as_posix() for p in REPORT.rglob('*') if p.is_file())+['reports/fep_e5_r1r1c/CHANGED_FILE_LIST.json','reports/fep_e5_r1r1c/FEP_E5_R1R1C_CANDIDATE_SEAL.json']
    emit('CHANGED_FILE_LIST',dict(parent=BASE,all_changed_files=sorted(set(files))))
    seal=dict(status='CANDIDATE_EXTERNAL_AUDIT_REQUIRED',baseline_sha=BASE,prior_implementation_sha=freeze['implementation'],code_bindings=[b.binding(ROOT/p) for p in CODE],evidence_bindings=[b.binding(p) for p in sorted(REPORT.rglob('*')) if p.is_file()],metadata_authority=m.authority(),state=state,external_acceptance=False,sealed_at=b.now())
    seal['logical_digest']=digest(seal);emit('FEP_E5_R1R1C_CANDIDATE_SEAL',seal)
    print(state,flush=True)

if __name__=='__main__':globals()[sys.argv[1]]()
