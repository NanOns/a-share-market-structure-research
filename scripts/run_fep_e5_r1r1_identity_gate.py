"""Exact-baseline R1R1 diagnostic execution. Stop at missing canonical authority.

Phases diagnose/tests/finalize preserve honest blocked evidence; this is not a
canonical projection importer, migration installer or acceptance workaround.
"""
import json, os, subprocess, sys, xml.etree.ElementTree as ET
from pathlib import Path
import psycopg
from scripts import run_fep_e5_r1 as prior
from scripts.build_fep_e2_r1r1_history import ROOT, binding, now
from scripts.validate_r25_preflight import protected, selection
from workbench_analysis.fep_e1.contracts import atomic_json, digest
from workbench_analysis.fep_e1.feature_owner import verify_file
from workbench_analysis.fep_e5.canonical_identity import readback_population, inventory, CONFLICT

BASE = '2bdca9dd87d210f778f4ec90aa4fbaa5f1708866'
REPORT = ROOT / 'reports/fep_e5_r1r1'
TASK = 'V4_15E5_R1R1_CANONICAL_FEP_INTEGRATION_REPAIR_TASK_R1_20261006.md'
DOCUMENTS = ('V4_15E5_R1R1A_REMOTE_PUBLICATION_EVIDENCE_CLOSURE_TASK_R1_20261006.md',
             'V4_15E5_R1R1_REMOTE_EXECUTION_VISIBILITY_INDEPENDENT_AUDIT_R1_20261006.md')
CODE = ['src/workbench_analysis/fep_e5/canonical_identity.py', 'tests/fep_e5/test_e5_canonical_identity.py',
        'scripts/run_fep_e5_r1r1_identity_gate.py']
DSNS = dict(fresh='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh',
            upgrade='host=127.0.0.1 port=55489 user=fep_e1_admin dbname=fep_e1_upgrade')

def load(path):
    return json.loads(Path(path).read_bytes())

def emit(name, payload):
    atomic_json(REPORT / (name + '.json'), payload)

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def frozen():
    freeze = load(REPORT / 'BASELINE_AUTHORITY_BINDINGS.json')
    for b in freeze['authority_bindings'] + freeze['diagnostic_code_bindings']:
        verify_file(ROOT, b)
    return freeze

def source_rows():
    ids = load(prior.PROTOCOL)['planned_observation_ids']
    all_rows = {r['observation_id']: r for r in prior.e3.rows()}
    # Copy only identity evidence; never resolve labels or call inference.
    return [{k: all_rows[i][k] for k in ('observation_id', 'entity_id', 'trade_date', 'original_e2_row_digest')} for i in ids]

def schema_readback(pg):
    constraints = pg.execute("""select c.relname,k.conname,pg_get_constraintdef(k.oid)
        from pg_constraint k join pg_class c on c.oid=k.conrelid
        join pg_namespace n on n.oid=c.relnamespace where n.nspname='fep' order by 1,2""").fetchall()
    functions = pg.execute("""select p.proname,pg_get_functiondef(p.oid) from pg_proc p
        join pg_namespace n on n.oid=p.pronamespace where n.nspname='fep' order by 1""").fetchall()
    triggers = pg.execute("""select c.relname,t.tgname,t.tgenabled from pg_trigger t
        join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace
        where n.nspname='fep' and not t.tgisinternal order by 1,2""").fetchall()
    body = dict(constraints=constraints, functions=functions, triggers=triggers)
    return dict(body, logical_digest=digest(body))

def diagnose():
    assert git('rev-parse', 'HEAD').decode().strip() == BASE
    assert git('branch', '--show-current').decode().strip() == 'codex/v4-system-reform'
    assert not REPORT.exists(), 'ONE_SHOT_DIAGNOSTIC_ALREADY_EXISTS'
    remote = git('ls-remote', 'origin', 'refs/heads/codex/v4-system-reform').decode().split()[0]
    assert remote == BASE
    preflight = dict(LOCAL_HEAD=BASE, LOCAL_BRANCH='codex/v4-system-reform', REMOTE_HEAD=remote,
        LOCAL_STATUS=git('status', '--short').decode().splitlines(),
        LOCAL_UNPUSHED_COMMITS=git('log', 'origin/codex/v4-system-reform..HEAD', '--oneline').decode().splitlines(),
        LOCAL_CHANGED_FILES=git('diff', '--name-only', 'HEAD').decode().splitlines(),
        R1R1_LOCAL_IMPLEMENTATION='NOT_FOUND_AT_TASK_ENTRY', R1R1_COMPLETE=False,
        action='RETURN_TO_ORIGINAL_R1R1_IMPLEMENTATION_TASK', checked_at=now(),
        new_untracked_diagnostic_code_not_complete_implementation=CODE)
    print(json.dumps(preflight, ensure_ascii=False), flush=True)
    REPORT.mkdir(parents=True); prior.write(REPORT / '.gitattributes', b'* -text\n')
    prior.write(REPORT / TASK, (Path('E:/codex_tmp') / TASK).read_bytes())
    for name in DOCUMENTS:
        prior.write(REPORT / name, (Path('D:/Users/lps/Desktop/阶段任务') / name).read_bytes())
    emit('EXECUTION_ENTRY_PREFLIGHT', preflight)
    old = load(prior.REPORT / 'FEP_E5_R1_CANDIDATE_SEAL.json')
    refs = old['code_bindings'] + old['evidence_bindings'] + load(prior.PROTOCOL)['upstream_bindings']
    refs += [binding(ROOT / 'AGENTS.md'), binding(ROOT / 'scripts/AGENTS.md')]
    refs += [binding(p) for p in sorted((ROOT / 'reports/fep_e5_external_audit_r1').iterdir()) if p.is_file()]
    refs += [binding(p) for p in sorted((ROOT / 'src/workbench_db/migrations/v4_postgres').glob('*.sql'))]
    refs = list({b['path']: b for b in refs}.values())
    for b in refs:
        verify_file(ROOT, b)
    assert load(ROOT / 'reports/fep_e5_external_audit_r1/EXTERNAL_AUDIT_ARCHIVE_SEAL.json')['authority']['sha256'] == '202385558843367b756a193499ee308f17bd7c6651b5efc38d3025bf88aaa0d2'
    guard = protected(ROOT); wait = selection(ROOT)
    assert not guard['historical_git_diff'] and wait['status'] == 'WAIT_ACCEPTED_DAILY_INPUT'
    emit('BASELINE_AUTHORITY_BINDINGS', dict(baseline=BASE, task_card=binding(REPORT / TASK),
        task_acquisition=dict(source='GOOGLE_DRIVE_READABLE_UTF8', source_url='https://drive.google.com/file/d/18rvGTXKwCsktOMgPXe0LEE_1lLg79gsP/view',
            provider_size_bytes=30408, persisted_size_bytes=(REPORT / TASK).stat().st_size, provider_created_at='2026-10-06T02:06:51.717Z'),
        authority_bindings=refs, diagnostic_code_bindings=[binding(ROOT / p) for p in CODE],
        protected_before=guard, R25_before=wait, run_started_at=now(), stage_contract='R1R1 sections B6/26: block on missing canonical publication authority'))
    populations = {}; database = {}
    for kind, dsn in DSNS.items():
        with psycopg.connect(dsn, autocommit=True) as pg:
            with pg.transaction():
                pg.execute('set transaction read only')
                before = inventory(pg); result = readback_population(pg, source_rows(), {})
                assert before == inventory(pg) and result['affected_observations'] == 205
                assert result['status'] == CONFLICT
                schema = schema_readback(pg)
                pubs = pg.execute('select count(*) from v4.publications').fetchone()[0]
                database[kind] = dict(status='BLOCKED_CANONICAL_PUBLICATION_AUTHORITY', canonical_schema='fep',
                    existing_accepted_E1_fixture=True, migrations_reinstalled_this_run=False,
                    table_counts=before, canonical_publications=pubs, schema_readback=schema,
                    identity_population=result, readonly=True, no_rows_inserted=True,
                    fresh_upgrade_full_integration_pass=False)
                emit(kind.upper() + '_DB_READBACK', database[kind]); populations[kind] = result
    assert database['fresh']['schema_readback']['logical_digest'] == database['upgrade']['schema_readback']['logical_digest']
    runtime = dict(status='UNAVAILABLE', configured_runtime_DSN_present=bool(os.environ.get('WORKBENCH_PG_DSN')),
        database='market_research', port=5432, global_authority_absence_claim=False)
    try:
        with psycopg.connect('host=127.0.0.1 port=5432 user=postgres dbname=market_research connect_timeout=3', autocommit=True) as pg:
            with pg.transaction():
                pg.execute('set transaction read only')
                runtime.update(status='READONLY_AVAILABLE', canonical_publications=pg.execute('select count(*) from v4.publications').fetchone()[0])
    except psycopg.Error as exc:
        runtime['exception_class'] = type(exc).__name__
    emit('CANONICAL_PUBLICATION_BINDING_READBACK', dict(status=CONFLICT, populations=populations,
        runtime_database_readback=runtime, missing_authority='No exact accepted historical identity manifest supplied for any source observation',
        not_inferable='Content digests and date-matched/current publications do not prove canonical publication/namespace/accepted_at/dependency identity',
        smallest_repair='Provide/import authentic historical canonical publications and exact dependency manifests through an approved authority path; no fake seeding',
        production_mutation=False))
    emit('CANONICAL_IDENTITY_MAPPING', dict(status=CONFLICT, logical_population=205,
        rows=populations['fresh']['population'], successful_mapping_count=0, dropped_observations=0))
    sql_path = ROOT / 'src/workbench_db/migrations/v4_postgres/028_fep_schema_v1.sql'
    assert "CHECK(model_role='CHAMPION')" in sql_path.read_text()
    emit('CONTRACT_CONFLICT_DISPOSITION', dict(status='BLOCKED_CONTRACT_CONFLICT',
        blockers=[dict(blocker_id='E5-B02', exact_failing_contract='030 fep.validate_observation_revision + canonical publication FK',
            conflict=CONFLICT, affected_observations=205, missing_authority='exact historical publication/revision/snapshot/namespace/dependency authority',
            attempted_legal_path='Read-only exact binding against canonical fep/v4 in both accepted E1 fixtures; inspect source identity artifact',
            workaround_forbidden='Fake accepted publication, digest identity, current backfill and silent row skip',
            smallest_proposed_repair='Supply authentic canonical historical authority manifest and accessible read-only authority database/export'),
            dict(blocker_id='E5-B03', conflict='CONFIRMED_CHAMPION_ONLY_SHADOW_PERMISSION_CONTRACT',
                exact_failing_contract=binding(sql_path), disposition='Narrow additive role-aware SHADOW repair authorized, deferred because identity authority gate blocks execution',
                proposed_repair='SHADOW_INFERENCE exact model_set_member role; display/priority remain CHAMPION-only; retain FK')],
        E5_B01='OPEN_BLOCKER_NOT_IMPLEMENTED', E5_B02='OPEN_BLOCKER', E5_B03='OPEN_BLOCKER', NEXT='STOP_WAIT_EXTERNAL_CONTRACT_REPAIR'))
    migration_names = sorted(p.name for p in sql_path.parent.glob('*.sql'))
    emit('MIGRATION_ALLOCATION_READBACK', dict(status='NOT_APPLICABLE', reason='Execution stopped at missing publication authority before migration allocation',
        scanned_files=migration_names, highest_existing_number=max(int(n.split('_')[0]) for n in migration_names),
        allocated_number=None, new_migrations=[], historical_028_031_unchanged=True))
    emit('ISOLATED_NAMESPACE_NONAUTHORITY_READBACK', dict(status='NON_AUTHORITY_ONLY',
        isolated_namespace='fep_e5_engineering', canonical_authority='fep',
        isolated_R1_rows_not_used_to_close_B01_B02_B03=True, old_615_projection_denominator_retained_in_frozen_prior_evidence=True))
    emit('CANONICAL_LEDGER_READBACK', dict(status='BLOCKED_NOT_IMPLEMENTED', schema='fep', canonical_rows_written=0,
        logical_source_observations=205, prior_logical_projection_denominator=615, prior_planned_slots=616,
        dropped_source_observations=0, fixture_counts={k:v['table_counts'] for k,v in database.items()}, fep_e5_engineering_used_as_authority=False))
    for name in ('CANONICAL_SCHEMA_REPAIR_READBACK', 'CANONICAL_PREDICTION_BINDING_READBACK',
                 'CANONICAL_VS_E5_R1_OUTPUT_RECONCILIATION', 'CANONICAL_PERMISSION_MATRIX', 'CANONICAL_CAS_CONCURRENCY',
                 'CANONICAL_CAS_IDEMPOTENCY', 'CANONICAL_ROLLBACK_DRILL', 'CANONICAL_PRIORITY_FIXTURE_READBACK', 'API_READBACK'):
        emit(name, dict(status='NOT_APPLICABLE', reason='No canonical implementation may proceed without exact historical publication authority (original task B6/26)',
            not_a_pass=True, B01_B02_B03_closed=False, REAL_DAILY_PRIORITY_SHADOW='NOT_GRANTED', MODEL_DISPLAY='UNGRANTED',
            PRIORITY_USE='UNGRANTED', CHAMPION='NONE', REAL_OOS='NOT_GRANTED', FIRST_OBSERVED='NOT_GRANTED', FEP_PRODUCTION='UNGRANTED'))
    print('205/205 unresolved canonical identity authorities; BLOCKED_CONTRACT_CONFLICT', flush=True)

def tests():
    frozen()
    from scripts import run_fep_e2_r1 as runner
    runner.REPORT = REPORT; runner.BASE = BASE
    env = os.environ.copy()
    env.update(TEMP='E:/codex_tmp/test_temp', TMP='E:/codex_tmp/test_temp', FEP_E1_TEST_DSN=DSNS['fresh'],
        FEP_E5_TEST_DSN=DSNS['fresh'], WORKBENCH_PG_DSN=DSNS['fresh'], OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2', MKL_NUM_THREADS='2')
    runner.execute([sys.executable, '-B', '-m', 'pytest', 'tests/fep_e5', 'tests/fep_e4', 'tests/fep_e3', 'tests/fep_e2', 'tests/fep',
        'tests/test_r20d_settlement.py', 'tests/test_r25_packet.py::test_actual_authority_inventory_waits_without_target', '-q',
        '--basetemp=E:/codex_tmp/test_temp/r1r1-targeted', '--junitxml=' + str(REPORT / 'targeted.xml')], env, 'targeted')
    env['FEP_E1_TEST_DSN'] = DSNS['upgrade']
    runner.execute([sys.executable, '-B', '-m', 'pytest', 'tests/fep_e5/test_e5_canonical_identity.py', '-q',
        '--basetemp=E:/codex_tmp/test_temp/r1r1-id-upgrade-final', '--junitxml=' + str(REPORT / 'upgrade_identity.xml')], env, 'upgrade_identity')
    # The inherited runner writes a generic scoped summary for auxiliary runs.
    os.replace(REPORT / 'SCOPED_REGRESSION_SUMMARY.json', REPORT / 'UPGRADE_IDENTITY_SUMMARY.json')
    env['FEP_E1_TEST_DSN'] = DSNS['fresh']
    previous = load(prior.REPORT / 'SCOPED_REGRESSION_SUMMARY.json')
    command = [v for v in previous['command'] if not v.startswith(('--basetemp=', '--junitxml='))]
    command[0] = sys.executable
    command += ['--basetemp=E:/codex_tmp/test_temp/r1r1-scoped', '--junitxml=' + str(REPORT / 'scoped.xml')]
    runner.execute(command, env, 'scoped', previous['failed_nodes'])

def finalize():
    freeze = frozen(); target = load(REPORT / 'TARGETED_SUMMARY.json'); scoped = load(REPORT / 'SCOPED_REGRESSION_SUMMARY.json')
    upgrade = load(REPORT / 'UPGRADE_IDENTITY_SUMMARY.json')
    assert not target['failed_nodes'] and not upgrade['failed_nodes'] and not scoped['introduced_active_failures']
    prior_nodes = load(prior.REPORT / 'SCOPED_REGRESSION_SUMMARY.json')['failed_nodes']
    assert sorted(scoped['failed_nodes']) == sorted(prior_nodes)
    assert [x for x in scoped['command'] if x.startswith('--deselect=')] == [x for x in load(prior.REPORT / 'SCOPED_REGRESSION_SUMMARY.json')['command'] if x.startswith('--deselect=')]
    cases = [dict(node=t.attrib['classname'] + '::' + t.attrib['name'], status='PASS' if all(t.find(k) is None for k in ('failure','error','skipped')) else 'FAIL')
        for t in ET.parse(REPORT / 'targeted.xml').findall('.//testcase') if 'test_e5' in t.attrib['classname']]
    emit('NEGATIVE_MATRIX', dict(status='PASS_EXECUTED_REJECTION_TESTS_ONLY', cases=cases, executed_cases=len(cases),
        inherited_R1_negative_semantics_preserved=True, canonical_CAS_and_permission_repair_cases='NOT_EXECUTED_BLOCKED_IDENTITY_AUTHORITY',
        canonical_integration_acceptance=False, synthetic_fixtures_not_authority_for_historical_population=True))
    guard = protected(ROOT); wait = selection(ROOT)
    assert guard == freeze['protected_before'] and wait == freeze['R25_before']
    emit('PROTECTED_STATE_READBACK', dict(status='PASS_UNCHANGED', before=freeze['protected_before'], after=guard,
        R25=wait, priority_owner_bindings=load(prior.PROTOCOL)['priority_bindings'], TDX='READ_ONLY_NO_WRITES',
        TDX_evidence_scope='Execution did not invoke TDX writers; no exhaustive concurrent third-party filesystem mutation claim'))
    state = dict(V4_15E5_R1R1_CANONICAL_INTEGRATION='BLOCKED_CONTRACT_CONFLICT',
        V4_15E5_R1R1_REMOTE_PUBLICATION='BLOCKED_NO_COMPLETE_IMPLEMENTATION', E5_B01='OPEN_BLOCKER', E5_B02='OPEN_BLOCKER', E5_B03='OPEN_BLOCKER',
        conflict=CONFLICT, implementation_complete=False, canonical_rows_written=0, affected_observations=205,
        REAL_DAILY_PRIORITY_SHADOW='NOT_GRANTED', MODEL_DISPLAY='UNGRANTED', PRIORITY_USE='UNGRANTED', CHAMPION='NONE',
        REAL_OOS='NOT_GRANTED', FIRST_OBSERVED='NOT_GRANTED', FEP_PRODUCTION='UNGRANTED', external_acceptance=False,
        NEXT='STOP_WAIT_EXTERNAL_CONTRACT_REPAIR')
    emit('GITHUB_CI_READBACK', dict(status='NOT_APPLICABLE', reason='No complete R1R1 implementation HEAD exists; post-commit remote receipt will check diagnostic code HEAD only', candidate_implementation_head=None, ci_pass_claim=False))
    prior.write(REPORT / 'COMPLETION_REPORT.md', f'''# V4-15E5 R1R1 diagnostic execution / R1R1A blocked\n\nStatus: BLOCKED_CONTRACT_CONFLICT / CONTRACT_CONFLICT_CANONICAL_PUBLICATION_BINDING. Baseline: {BASE}. R1R1A entry found no completed local implementation or unpushed commit. The original issued R1R1 task was located on Drive and executed through authority availability diagnosis (sections B6/26); no completion is fabricated.\n\nAdded a read-only canonical identity availability gate and seven real PostgreSQL rejection tests. All 205 historical source observations remain in the missing-authority mapping evidence; no rows skipped. Accepted E1 fresh and upgrade fixtures each have zero canonical publications and no populated fep facts. Source artifacts have content lineage but no exact canonical historical authority manifest. Runtime market_research database was unavailable; absence outside the inspected sources is not claimed.\n\nRequired upstream repair: supply authentic historical v4.publications identities and exact namespace/accepted_at/dependency manifests, plus accepted revision/snapshot mapping. Current publication backfill, row-digest identity and fake publication seeding are forbidden. The CHAMPION-only permission conflict is confirmed; narrow additive SHADOW repair remains deferred behind the identity gate. No migration allocated or installed, no canonical inference/prediction/permission/CAS implemented, no B01/B02/B03 closed.\n\nNew tests: targeted {target['passed']} passed/{target['skipped']} skipped/0 failed; upgrade identity {upgrade['passed']} passed; scoped {scoped['passed']} passed/{scoped['skipped']} skipped/{len(scoped['failed_nodes'])} exact known debt failures/0 introduced active failures. Existing two exclusions preserved, no additional exclusions. These validate the diagnostic guard and unchanged capabilities, not integration readiness. NOT_APPLICABLE downstream receipts are explicitly not PASS.\n\nHistorical migrations 028–031, prior E5 code/outputs, models, all accepted heads and Priority V1 remain unchanged; no new model fit, search or label resolution; TDX read-only. All production/display/Priority/Champion/real Daily/OOS/first-observed permissions closed.\n\nNext: STOP_WAIT_EXTERNAL_CONTRACT_REPAIR. This is a blocked diagnostic code/evidence publication, not R1R1_REMOTE_CANDIDATE_VISIBLE_READY_FOR_EXTERNAL_AUDIT. Do not proceed to E6/V4-16.\n'''.encode())
    files = CODE + sorted(p.relative_to(ROOT).as_posix() for p in REPORT.iterdir() if p.is_file())
    files += [(REPORT / n).relative_to(ROOT).as_posix() for n in ('CHANGED_FILE_LIST.json', 'FEP_E5_R1R1_CANDIDATE_SEAL.json')]
    emit('CHANGED_FILE_LIST', dict(parent=BASE, all_changed_files=sorted(files)))
    seal = dict(status='BLOCKED_NOT_CANDIDATE', baseline_sha=BASE, parent_sha=BASE, implementation_head=None,
        implementation_head_reason='No completed canonical integration; exact diagnostic code commit will be bound in separate remote receipt',
        task_card_sha256=binding(REPORT / TASK)['sha256'], code_bindings=[binding(ROOT / p) for p in CODE],
        evidence_bindings=[binding(p) for p in sorted(REPORT.iterdir()) if p.is_file()],
        protected_state_digest=binding(REPORT / 'PROTECTED_STATE_READBACK.json')['sha256'],
        canonical_schema_identity={k:load(REPORT / (k.upper() + '_DB_READBACK.json'))['schema_readback']['logical_digest'] for k in DSNS},
        migrations_added=[], external_acceptance=False, candidate_ready=False, state=state, sealed_at=now())
    seal['logical_digest'] = digest(seal); emit('FEP_E5_R1R1_CANDIDATE_SEAL', seal)
    print('BLOCKED_CONTRACT_CONFLICT; NO COMPLETE R1R1 CANDIDATE', flush=True)

if __name__ == '__main__':
    globals()[sys.argv[1]]()
