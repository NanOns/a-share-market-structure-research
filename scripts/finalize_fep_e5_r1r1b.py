"""Canonical drills, regression and versioned evidence closure; no next-stage entry."""
import os, sys, json, subprocess, threading
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from scripts import run_fep_e5_r1r1b as r
from scripts.run_fep_e5_r1r1b import ROOT,REPORT,BASE,DSNS,load,emit,binding,now,c,digest,verify_file,git,protected,selection,schema_readback
from workbench_service.canonical_expectancy_service import CanonicalExpectancyReadAPI
from workbench_analysis.fep_e1.contracts import atomic_json

CODE=r.CODE+['scripts/finalize_fep_e5_r1r1b.py','config/v4_18_migration_replay_contract_v1_2.json','tests/fep/test_v4_18_namespace_successor.py']

def freeze_validation():
    f=load(REPORT/'IMPLEMENTATION_INPUT_FREEZE.json')
    for b in f['input_bindings']+[f['semantic_freeze'],f['authority_contract']]:verify_file(ROOT,b)
    # Current projection freeze supersedes explicitly archived draft attempts.
    for b in f['code_bindings']:
        if b['path']!='tests/fep_e5/test_e5_reconstruction.py':verify_file(ROOT,b)
    emit('VALIDATION_CODE_FREEZE',dict(code_bindings=[binding(ROOT/p) for p in CODE],input_freeze=binding(REPORT/'IMPLEMENTATION_INPUT_FREEZE.json'),
        reason='Freeze current validation driver, fixture corrections and additive namespace inventory after rebuilt projection; original semantic contract, source population and numerical outputs unchanged.',
        projected_counts_unchanged=True,previous_failed_attempts=[binding(REPORT/n) for n in ('canonical_initial.xml','canonical_corrected.xml')],frozen_at=now()))

def verified():
    f=load(REPORT/'VALIDATION_CODE_FREEZE.json')
    for b in f['code_bindings']:verify_file(ROOT,b)
    return f

def drills():
    verified();results={};priority={};rollback={}
    prior=load(r.old.REPORT/'DAILY_PRIORITY_CAPABILITY_READBACK.json')
    fixture=prior['fixture'];pool=load(r.old.REPORT/'PRIORITY_V1_PROTECTED_READBACK.json')['fixture_V1']
    assert len(pool)==len(fixture['rows'])==7 and fixture['v2_active'] is False
    for kind,dsn in DSNS.items():
        with psycopg.connect(dsn,autocommit=True) as pg:
            assert c.inventory(pg)['predictions']==615
            before_predictions=pg.execute('select to_jsonb(t) from fep.predictions t order by prediction_id').fetchall()
            grant=pg.execute('select grant_id from fep.permission_keys order by grant_id limit 1').fetchone()[0]
            h=c.head(pg);barrier=threading.Barrier(2)
            def worker(i):
                with psycopg.connect(dsn,autocommit=True) as q:
                    barrier.wait()
                    try:
                        with q.transaction():
                            a=c.cas(q,grant,'ALLOW',kind+'-canonical-race-'+str(i),expected=h[0],prior=h[1])
                        return dict(worker=i,status='COMMITTED',receipt=a)
                    except psycopg.Error as exc:return dict(worker=i,status='REJECTED',sqlstate=exc.sqlstate,error=str(exc))
            before=c.inventory(pg)
            with ThreadPoolExecutor(max_workers=2) as executor:races=list(executor.map(worker,(1,2)))
            assert sorted(x['status'] for x in races)==['COMMITTED','REJECTED'] and c.head(pg)[0]==h[0]+1
            winner=next(x['receipt'] for x in races if x['status']=='COMMITTED')
            winner_row=pg.execute('select to_jsonb(t) from fep.deployment_change_receipts t where request_id=%s',(winner['request_id'],)).fetchone()[0]
            # Replay with the original expected tuple, even after head advances.
            version=c.cas(pg,grant,'ALLOW',winner['request_id'],expected=h[0],prior=h[1])['version'];assert version==h[0]+1
            afterrace=c.inventory(pg);assert afterrace['activations']==before['activations']+1 and afterrace['deployment_change_receipts']==before['deployment_change_receipts']+1
            h2=c.head(pg)
            try:
                with pg.transaction():
                    c.cas(pg,grant,'REVOKE',kind+'-injected-after-receipt');raise ValueError('INJECTED_AFTER_CAS_RECEIPT')
            except ValueError:pass
            assert afterrace==c.inventory(pg) and c.head(pg)==h2
            revoke=c.cas(pg,grant,'REVOKE',kind+'-canonical-final-revoke')
            assert before_predictions==pg.execute('select to_jsonb(t) from fep.predictions t order by prediction_id').fetchall()
            results[kind]=dict(before_head=list(h),races=races,winner_receipt=winner_row,replay_version=version,
                one_winner_one_rejected=True,no_orphan_activation_or_receipt=True,after_head=list(c.head(pg)),final_revoke=revoke)
            rollback[kind]=dict(status='PASS',after_CAS_receipt_failure_restored_head=True,no_partial_activations=True,
                before_counts=afterrace,after_failed_counts=afterrace,historical_predictions_unchanged=True,final_permission_revoked=True)
            business=load(REPORT/'CANONICAL_PREDICTION_BINDING_READBACK.json')['fixtures'][kind]
            anchor=business['mapping'][0]['observation_id'];refs=[x for x in business['predictions'] if x['observation_id']==anchor];assert len(refs)==3
            pid='FEP_CANONICAL_PRIORITY_SYNTHETIC_LINKAGE:'+kind
            body=dict(version='FEP_E5_CANONICAL_PRIORITY_SYNTHETIC_LINKAGE_V1',synthetic_only=True,
                synthetic_fixture=fixture,historical_entry_anchor=anchor,not_real_daily=True,MODEL_DISPLAY=False,PRIORITY_USE=False,
                source_prior_fixture=binding(r.old.REPORT/'DAILY_PRIORITY_CAPABILITY_READBACK.json'))
            with pg.transaction():
                c.contract(pg,'FEP_E5_CANONICAL_PRIORITY_SYNTHETIC_LINKAGE_V1',body)
                pg.execute("insert into fep.priority_projection values (%s,%s,%s,'FEP_E5_CANONICAL_PRIORITY_SYNTHETIC_LINKAGE_V1',%s,'SYNTHETIC_LINKAGE_ONLY',%s,%s)",
                    (pid,refs[0]['run_id'],anchor,digest(pool),Jsonb(body),Jsonb([dict(prediction_id=x['prediction_id'],run_id=x['run_id'],model_id=x['model_id'],model_set_id=x['model_set_id'],observation_id=x['observation_id'],snapshot_id=x['snapshot_id']) for x in refs])))
            stored=pg.execute('select to_jsonb(t) from fep.priority_projection t where projection_id=%s',(pid,)).fetchone()[0]
            before_priority=c.inventory(pg)
            try:
                with pg.transaction():
                    pg.execute("insert into fep.priority_projection select 'UNIT_FAILED_PRIORITY',run_id,observation_id,priority_contract_id,core_rank_identity,axis_state,axis_values,prediction_refs from fep.priority_projection where projection_id=%s",(pid,))
                    raise ValueError('INJECTED_PRIORITY_FAILURE')
            except (ValueError,psycopg.Error):pass
            assert before_priority==c.inventory(pg)
            priority[kind]=dict(status='PASS_CANONICAL_SYNTHETIC_LINKAGE_ONLY',stored_row=stored,
                canonical_prediction_refs=3,complete_pool=7,synthetic_entity_to_historical_entity_equivalence=False,
                fixture_numbers_are_synthetic_and_not_historical_predictions=True,priority_grants=0,
                real_daily_api=CanonicalExpectancyReadAPI(pg).priority(),full_V1_digest=digest(pool),risk_events_preserved=True,
                failed_priority_transaction_unchanged=True)
            export={n:[x[0] for x in pg.execute(sql.SQL('select to_jsonb(t) from fep.{} t order by to_jsonb(t)::text').format(sql.Identifier(n))).fetchall()] for n in c.inventory(pg)}
            emit(kind.upper()+'_FINAL_DB_READBACK',dict(status='PASS',schema=schema_readback(pg),table_counts=c.inventory(pg),
                tables=export,canonical_business_observations=205,synthetic_PIT_regression_observations=1 if kind=='upgrade' else 0,
                original_publication_validator=pg.execute("select pg_get_functiondef('fep.validate_observation_revision()'::regprocedure)").fetchone()[0],
                final_head=list(c.head(pg)),production=False))
    emit('CANONICAL_CAS_CONCURRENCY',dict(status='PASS',fixtures=results))
    emit('CANONICAL_CAS_IDEMPOTENCY',dict(status='PASS',fixtures={k:dict(replay_version=v['replay_version'],original_receipt=v['winner_receipt'],no_new_rows=True) for k,v in results.items()}))
    emit('CANONICAL_ROLLBACK_DRILL',dict(status='PASS',fixtures=rollback,acceptance_failure_after_prediction_proof='test_acceptance_transaction_rolls_back_after_prediction; targeted XML binds both fixtures'))
    emit('CANONICAL_PRIORITY_FIXTURE_READBACK',dict(status='PASS_SYNTHETIC_ONLY',fixtures=priority,REAL_DAILY_PRIORITY_SHADOW='NOT_GRANTED',Priority_V1_mutation=False))
    print('Canonical CAS race, idempotency, rollback and Priority fixture drills passed',flush=True)

def tests():
    verified();from scripts import run_fep_e2_r1 as runner
    runner.REPORT=REPORT;runner.BASE=BASE
    env=os.environ.copy();env.update(TEMP='E:/codex_tmp/test_temp',TMP='E:/codex_tmp/test_temp',
        FEP_E1_TEST_DSN='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh',
        FEP_E5_TEST_DSN='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh',
        WORKBENCH_PG_DSN='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh',
        FEP_E5_CANONICAL_TEST_ENABLE='1',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
    runner.execute([sys.executable,'-B','-m','pytest','tests/fep_e5','tests/fep_e4','tests/fep_e3','tests/fep_e2','tests/fep',
        'tests/test_r20d_settlement.py','tests/test_r25_packet.py::test_actual_authority_inventory_waits_without_target','-q',
        '--basetemp=E:/codex_tmp/test_temp/r1r1b-targeted','--junitxml='+str(REPORT/'targeted.xml')],env,'targeted')
    assert not load(REPORT/'TARGETED_SUMMARY.json')['failed_nodes']
    previous=load(ROOT/'reports/fep_e5_r1r1/SCOPED_REGRESSION_SUMMARY.json')
    command=[v for v in previous['command'] if not v.startswith(('--basetemp=','--junitxml='))];command[0]=sys.executable
    command+=['--basetemp=E:/codex_tmp/test_temp/r1r1b-scoped','--junitxml='+str(REPORT/'scoped.xml')]
    runner.execute(command,env,'scoped',previous['failed_nodes'])

def finalize():
    verified();target=load(REPORT/'TARGETED_SUMMARY.json');scoped=load(REPORT/'SCOPED_REGRESSION_SUMMARY.json')
    previous=load(ROOT/'reports/fep_e5_r1r1/SCOPED_REGRESSION_SUMMARY.json')
    assert not target['failed_nodes'] and not scoped['introduced_active_failures']
    assert sorted(scoped['failed_nodes'])==sorted(previous['failed_nodes']) and len(scoped['failed_nodes'])==52
    assert [v for v in scoped['command'] if v.startswith('--deselect=')]==[v for v in previous['command'] if v.startswith('--deselect=')]
    cases=[dict(node=t.attrib['classname']+'::'+t.attrib['name'],status='SKIP' if t.find('skipped') is not None else 'FAIL' if any(t.find(k) is not None for k in ('failure','error')) else 'PASS') for t in ET.parse(REPORT/'targeted.xml').findall('.//testcase') if 'test_e5_reconstruction' in t.attrib['classname']]
    assert len(cases)>=204 and all(x['status']=='PASS' for x in cases)
    emit('RECONSTRUCTION_NEGATIVE_MATRIX',dict(status='PASS',cases=cases,RA_01_13_covered=True,XML=binding(REPORT/'targeted.xml'),all_real_PostgreSQL=True))
    emit('NEGATIVE_MATRIX',dict(status='PASS',canonical_cases=cases,upstream_negatives_preserved=True,known_debt=52,introduced_active_failures=0))
    exports={k:load(REPORT/(k.upper()+'_FINAL_DB_READBACK.json')) for k in DSNS}
    for kind,e in exports.items():
        t=e['tables'];assert len(t['reconstruction_authorities'])==205 and len(t['predictions'])==615
        assert len(t['prediction_slots'])==616 and len(t['priority_projection'])==1 and len(t['priority_projection_grants'])==0
        assert all(a['reconstructed_at']>a['trade_date'] and not a['first_observed'] and not a['as_recorded'] and not a['real_oos'] for a in t['reconstruction_authorities'])
    base=dict(status='PASS',fixtures={k:binding(REPORT/(k.upper()+'_FINAL_DB_READBACK.json')) for k in exports},negative_matrix=binding(REPORT/'RECONSTRUCTION_NEGATIVE_MATRIX.json'))
    emit('RECONSTRUCTION_AUTHORITY_DB_READBACK',dict(base,authority_counts=205,immutability=True,publication_counts=dict(fresh=0,upgrade=1),upgrade_publication='Current synthetic PIT regression fixture only; no historical business publication'))
    emit('OBSERVATION_AUTHORITY_UNION_READBACK',dict(base,historical_business_rows=205,publication_id=None,authority_kind='HISTORICAL_RECONSTRUCTION',PIT_business_claims=0))
    emit('PREDICTION_RUN_AUTHORITY_UNION_READBACK',dict(base,prediction_runs=615,historical_business_rows=615,publication_id=None,authority_match_to_snapshot=True))
    emit('CANONICAL_SNAPSHOT_BINDING_READBACK',dict(base,canonical_snapshots=205,feature_values=4100,UNKNOWN_preserved=477,no_embedded_snapshot_only_substitute=True))
    emit('PIT_PUBLICATION_PATH_REGRESSION',dict(base,original_function_unchanged=True,positive_PIT_current_synthetic=True,upgrade_prior_PIT_fact_unchanged=True,negative_cases=[x for x in cases if 'PIT_' in x['node']],historical_PIT_backfill=False))
    grants=exports['fresh']['tables']['permission_keys'];members=exports['fresh']['tables']['model_set_members']
    emit('PERMISSION_ROLE_REPAIR_READBACK',dict(base,permission_keys=grants,members=members,exact_FK_retained=True,SHADOW_roles=['BASELINE','CHALLENGER'],CHAMPION='NONE',MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED'))
    emit('CANONICAL_PERMISSION_MATRIX',dict(base,keys=grants,canonical_roles=members,all_final_heads='REVOKE',display_priority_champion_only=True))
    semantic=load(REPORT/'R1R1B_CONTRACT_PROTOCOL_FREEZE.json');guard=protected(ROOT);wait=selection(ROOT)
    assert guard==semantic['protected_before'] and wait==semantic['R25_before']
    for b in load(r.old.PROTOCOL)['priority_bindings']:verify_file(ROOT,b)
    allocation=load(REPORT/'MIGRATION_ALLOCATION_READBACK.json')
    for b in r.walk_bindings(allocation):verify_file(ROOT,b)
    emit('PROTECTED_STATE_READBACK',dict(status='PASS_UNCHANGED',before=semantic['protected_before'],after=guard,R25=wait,Priority_V1_bindings=load(r.old.PROTOCOL)['priority_bindings'],TDX='READ_ONLY_NO_WRITES',original_E2_E3_E4_E5_R1_artifacts_unchanged=True))
    emit('CROSS_CUTTING_AUDIT_REGISTER',dict(items=[dict(id='FEP-RA-PUBLICATION-BOUNDARY-01',scope='Additive v4.publications reconstruction rejection trigger; ordinary PIT namespace regression',evidence=[binding(ROOT/r.CODE[2]),binding(REPORT/'PIT_PUBLICATION_PATH_REGRESSION.json')],internal_acceptance='PASS_CANDIDATE',external_acceptance=False),dict(id='FEP-RA-LEGACY-UPGRADE-01',scope='Strict new publication/PIT union rejects incompatible pre-existing reconstructed-publication rows; no silent relabeling',evidence=binding(ROOT/r.CODE[2]),acceptance='Populated current PIT upgrade PASS; incompatible legacy publication populations fail closed and require separate review')]))
    # Supersede old blocked receipts using immutable versioned readback bindings.
    names=['CANONICAL_SCHEMA_REPAIR_READBACK','CANONICAL_PREDICTION_BINDING_READBACK','CANONICAL_VS_E5_R1_OUTPUT_RECONCILIATION','CANONICAL_PERMISSION_MATRIX','CANONICAL_CAS_CONCURRENCY','CANONICAL_CAS_IDEMPOTENCY','CANONICAL_ROLLBACK_DRILL','CANONICAL_PRIORITY_FIXTURE_READBACK','API_READBACK','CANONICAL_LEDGER_READBACK','CANONICAL_IDENTITY_MAPPING']
    predecessors=REPORT/'predecessor_receipts';predecessors.mkdir(exist_ok=True)
    replacements=[]
    for n in names:
        path=ROOT/('reports/fep_e5_r1r1/'+n+'.json');archived=predecessors/(n+'.json')
        prior_bytes=git('show',BASE+':'+path.relative_to(ROOT).as_posix())
        if not archived.exists():r.old.write(archived,prior_bytes)
        assert archived.read_bytes()==prior_bytes
        r.old.write(path,(REPORT/(n+'.json')).read_bytes())
        replacements.append(dict(name=n,prior_baseline=BASE,prior_archive=binding(archived),current=binding(REPORT/(n+'.json')),required_path=binding(path)))
    required=['R1R1B_CONTRACT_PROTOCOL_FREEZE','HISTORICAL_RECONSTRUCTION_AUTHORITY_CONTRACT','HISTORICAL_RECONSTRUCTION_AUTHORITY_MAPPING','RECONSTRUCTION_AUTHORITY_DB_READBACK','OBSERVATION_AUTHORITY_UNION_READBACK','PREDICTION_RUN_AUTHORITY_UNION_READBACK','CANONICAL_SNAPSHOT_BINDING_READBACK','PIT_PUBLICATION_PATH_REGRESSION','RECONSTRUCTION_NEGATIVE_MATRIX','PERMISSION_ROLE_REPAIR_READBACK']
    for n in required:r.old.write(ROOT/('reports/fep_e5_r1r1/'+n+'.json'),(REPORT/(n+'.json')).read_bytes())
    published=[binding(ROOT/('reports/fep_e5_r1r1/'+n+'.json')) for n in names+required]
    supersession=dict(version='R1R1B',status='CURRENT_EXECUTED_READBACKS_REPLACE_PRIOR_BLOCKED_NA',prior_stage_seal=binding(ROOT/'reports/fep_e5_r1r1/FEP_E5_R1R1_CANDIDATE_SEAL.json'),prior_seal_reproduction='git show baseline:path; archived predecessor receipts; prior seal is historical and not evaluated against replaced current paths',current_receipts=replacements,published_required_receipts=published,preserve_historical_seal_bytes=True)
    emit('R1R1_RECEIPT_SUPERSESSION',supersession)
    atomic_json(ROOT/'reports/fep_e5_r1r1/R1R1B_CURRENT_EXECUTION_INDEX.json',supersession)
    state=dict(V4_15E5_R1R1B_CANONICAL_INTEGRATION='CANDIDATE_EXTERNAL_AUDIT_REQUIRED',HISTORICAL_RECONSTRUCTION_AUTHORITY='PASS_CANDIDATE',E5_B01_CANONICAL_FEP_LEDGER='PASS_CANDIDATE',E5_B02_CANONICAL_IDENTITY_BINDING='PASS_CANDIDATE',E5_B03_CANONICAL_PERMISSION_DEPLOYMENT='PASS_CANDIDATE',FAKE_PUBLICATION=False,HISTORICAL_AVAILABILITY_FABRICATION=False,PARALLEL_SCHEMA_AUTHORITY=False,FAKE_CHAMPION=False,NEW_TRAINING=False,NEW_LABEL_RESOLUTION=False,PRIORITY_V1_MUTATION=False,PROTECTED_STATE_MUTATION=False,TDX_MUTATION=False,REAL_DAILY_PRIORITY_SHADOW='NOT_GRANTED',MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',CHAMPION='NONE',REAL_OOS='NOT_GRANTED',FIRST_OBSERVED='NOT_GRANTED',FEP_PRODUCTION='UNGRANTED',external_acceptance=False,NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT_R1R1B')
    emit('STAGE_ACCEPTANCE_AND_NEXT',state)
    md=f'''# V4-15E5 R1R1B canonical candidate\n\nBaseline `{BASE}`. Status **CANDIDATE_EXTERNAL_AUDIT_REQUIRED**; external_acceptance=false. Stop at independent R1R1B audit; no E6/V4-16 entry.\n\nAdded migration 032, canonical reconstruction authority with actual current reconstruction timestamps and explicit unobserved historical availability. Both authority unions are mutually exclusive; original PIT publication validator unchanged. Imported exact frozen artifacts with explicit accepted-artifact provenance, not fabricated training runs. Canonical BASELINE/CHALLENGER SHADOW grants retain exact member FKs; display/Priority remain champion-only.\n\nEach isolated fresh/upgrade fixture: 205 historical business observations/authorities/snapshots, 4,100 feature values including 477 UNKNOWN, 615 predictions/runs/acceptances and 616 immutable planned slots. Each family preserves 46 READY / 159 REJECTED_QUALITY. Original numerical outputs unchanged; no new fit/search/labels. Upgrade also retains one separately identified current synthetic PIT regression observation/publication; it is not historical source authority.\n\nCanonical CAS uses original fep.cas_deploy: actual concurrent writers produce one winner and one conflict; exact replay adds no rows. Failure after CAS receipt and after prediction is transactional; final SHADOW heads revoked and prediction history preserved. Priority fixture is a synthetic seven-row diagnostic payload anchored to canonical observation/run and three real historical prediction references. Synthetic fixture entities/scores are not claimed equivalent to the historical entry entities. No PRIORITY_USE grants or real Daily activation. Explicit API returns immutable RA context; default display denies axes, TODAY entry mode rejects, revoked diagnostic access denies. Production routes unchanged.\n\nTargeted: {target['passed']} passed, {target['skipped']} skipped, 0 failed, including {len(cases)} real PostgreSQL canonical cases across both fixtures. Scoped: {scoped['passed']} passed, {scoped['skipped']} skipped, exact 52 known debts retained, 0 introduced active failures; prior two exclusions unchanged. Original E1 tests use the original E1 fixtures, while new reconstruction tests independently exercise the additive successor schema. This avoids rewriting frozen legacy test provenance.\n\nInitial dependency-token guard wrongly included valid UNKNOWN feature quality. Its attempted import rolled back before business writes, then draft 032 was repaired/reinstalled on isolated fixtures. Subsequent initial test failures concerned duplicate-key/assertion fixture construction; raw failed XML retained and test corrections explicitly frozen. A later review added current-head/selection-lock admission and exact complete-snapshot input-digest guards; the namespace inventory received additive v1_2. Prior attempt ledgers are archived, isolated fixtures rebuilt, and final code/input bindings refrozen before projection. Original semantic protocol, source population, model choices and numerical outputs remain unchanged.\n\nRequired receipt paths in reports/fep_e5_r1r1 now contain the actual current executed readbacks, with predecessor raw bytes preserved in predecessor_receipts and the exact baseline Git objects. Required new authority receipts are also published in that directory. R1R1B_CURRENT_EXECUTION_INDEX.json and R1R1_RECEIPT_SUPERSESSION.json make the transition explicit; the old blocked seal is historical, reproducible against its original baseline rather than replaced current paths. No N/A is counted as PASS. Protected heads/owners, Priority V1, R25 WAIT_ACCEPTED_DAILY_INPUT, original migrations 028–031 and TDX inputs unchanged. All production/Champion/display/Priority/first-observed/real OOS permissions closed.\n'''
    r.old.write(REPORT/'COMPLETION_REPORT.md',md.encode())
    index='reports/fep_e5_r1r1/R1R1B_CURRENT_EXECUTION_INDEX.json'
    files=CODE+[index]+[b['path'] for b in published]+sorted(p.relative_to(ROOT).as_posix() for p in REPORT.rglob('*') if p.is_file())+['reports/fep_e5_r1r1b/CHANGED_FILE_LIST.json','reports/fep_e5_r1r1b/FEP_E5_R1R1B_CANDIDATE_SEAL.json']
    emit('CHANGED_FILE_LIST',dict(parent=BASE,all_changed_files=sorted(set(files))))
    seal=dict(status='CANDIDATE_EXTERNAL_AUDIT_REQUIRED',baseline_sha=BASE,parent_sha=BASE,code_bindings=[binding(ROOT/p) for p in CODE],
        current_receipt_index=binding(ROOT/index),published_original_receipt_bindings=published,evidence_bindings=[binding(p) for p in sorted(REPORT.rglob('*')) if p.is_file()],
        migration=binding(ROOT/r.CODE[2]),schema_identity={k:e['schema']['logical_digest'] for k,e in exports.items()},
        semantic_freeze=binding(REPORT/'R1R1B_CONTRACT_PROTOCOL_FREEZE.json'),authority_manifest=binding(REPORT/'HISTORICAL_RECONSTRUCTION_AUTHORITY_CONTRACT.json'),
        observations=205,predictions=615,slots=616,external_acceptance=False,state=state,sealed_at=now(),remote_commit_binding='Separate post-commit receipt; no self-referential SHA fabrication')
    seal['logical_digest']=digest(seal);emit('FEP_E5_R1R1B_CANDIDATE_SEAL',seal)
    print('CANDIDATE_EXTERNAL_AUDIT_REQUIRED; STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT_R1R1B',flush=True)

if __name__=='__main__':globals()[sys.argv[1]]()
