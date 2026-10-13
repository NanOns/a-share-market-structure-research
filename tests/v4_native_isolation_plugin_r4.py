"""Small R4 isolation profile; refusal cannot satisfy business exceptions."""
import json
import os
from pathlib import Path
import traceback
import re
import hashlib
import sys
import pytest
from tests.v4_frozen_history_closeout import exact_pre16_history_native_scope,exact_registered_history_native_scope,exact_original_r17b_promotion_node,exact_original_stage13_native_scope,exact_original_r15_contract_node,exact_historical_dm01_preclose_clock
from tests.v4_frozen_history_closeout import original_pre_successor_v13_reader_gate
from tests.v4_frozen_history_closeout import original_fep_feature_owner_envelope
from tests.v4_static_stage_continuation import exact_original_static_stage_node,original_mutable_exact_policy_contract,original_pre_exact_synthetic_executor_contract

@pytest.fixture(autouse=True)
def exact_clean_phase0_database(request,monkeypatch):
    if not request.node.path.as_posix().endswith('/tests/v4_phase0/test_postgres_schema.py'):return
    import psycopg
    from scripts.v4_closeout_phase0_clean_fixture import DATABASE,connection
    monkeypatch.setattr(request.module,'connect',lambda:psycopg.connect(**connection(DATABASE)))

@pytest.fixture(autouse=True,scope='module')
def real_default_service_native_snapshot_scope(request):
    if request.node.path.name!='test_v4_default_workbench_service.py':return
    original=Path(__file__).resolve().parents[1]
    candidate=Path('G:/codex_tmp/v4_ui_default_r1')
    from workbench_service.joint_release import load,checked_path
    joint=load(candidate)
    assert joint['contract_id']=='V4_JOINT_RELEASE_V2_PG_CONTENT'
    for name in ('V4_OPERATIONAL_RESEARCH_HEAD.json','V4_DATA_ACCEPTED_HEAD.json'):
        assert (candidate/'data/v4'/name).read_bytes()==(original/'data/v4'/name).read_bytes()
    manifest=json.loads(checked_path(candidate,joint['snapshot']['manifest']).read_bytes())
    descriptor=json.loads(checked_path(candidate,manifest['database']).read_bytes())
    assert descriptor['contract_id']=='V4_PG_RESEARCH_SNAPSHOT_R2'
    assert descriptor['database_identity']['system_identifier']=='7695278778933357404'
    patch=pytest.MonkeyPatch();request.addfinalizer(patch.undo)
    patch.setattr(request.module,'ROOT',candidate)
    Path('G:/codex_tmp/v4_full_closeout_20261012/denominator/DEFAULT_SERVICE_NATIVE_SNAPSHOT_SCOPE.json').write_text(json.dumps(dict(
        scope='REAL_ISOLATED_CURRENT_PG_SNAPSHOT',root=str(candidate),manifest=joint['snapshot']['manifest'],
        descriptor=manifest['database'],protected_heads_identical=True,assertions_unchanged=True,
        current_production_acceptance=False),indent=2),encoding='utf8')

class V4DatabaseGuardViolation(BaseException): pass
ACTIVE=None
EVENTS=[]
FILESYSTEM_GUARD_ACTIVE=False

@pytest.fixture(autouse=True)
def unavailable_original_v1_v2_reports(request):
    """Keep unavailable pre-V4 nodes as explicit SKIP, never numerical PASS."""
    root=Path(__file__).resolve().parents[1]
    qualification=json.loads((root/'config/v4_unavailable_v1_v2_historical_nodes_r3.json').read_bytes())
    row=next((x for x in qualification['nodes'] if x['node']==request.node.nodeid),None)
    if row is None:return
    assert qualification['grants_current_permission'] is False
    assert hashlib.sha256(request.node.path.read_bytes()).hexdigest()==row['test_sha256']
    request.node.user_properties.append(('scope','HISTORICAL_ONLY_V1_V2_INPUT_UNAVAILABLE_NO_CURRENT_ADMISSION'))
    pytest.skip(row['reason'])

def source_write_guard(event,args):
    if not FILESYSTEM_GUARD_ACTIVE:return
    targets=[]
    if event=='open':
        mode=args[1] or '';flags=args[2]
        if any(x in mode for x in ('w','a','+','x')) or flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC):targets=args[:1]
    elif event in ('os.remove','os.rmdir','os.mkdir','os.rename'):targets=args[:2] if event=='os.rename' else args[:1]
    if not targets:return
    roots=[Path('D:/new_tdx').resolve(),Path('G:/codex work/大A交易').resolve()]
    for value in targets:
        if not isinstance(value,(str,bytes,os.PathLike)):continue
        target=Path(os.fsdecode(value)).resolve()
        if any(target==root or target.is_relative_to(root) for root in roots):
            EVENTS.append(dict(event='PROTECTED_SOURCE_WRITE_REJECTED',nodeid=ACTIVE,path=str(target)))
            raise V4DatabaseGuardViolation('R4_READONLY_SOURCE_MUTATION_FORBIDDEN')

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item,nextitem):
    global ACTIVE
    ACTIVE=item.nodeid
    try: yield
    finally: ACTIVE=None

def pytest_configure(config):
    global FILESYSTEM_GUARD_ACTIVE
    if not FILESYSTEM_GUARD_ACTIVE:sys.addaudithook(source_write_guard)
    FILESYSTEM_GUARD_ACTIVE=True
    import psycopg
    from psycopg.conninfo import conninfo_to_dict
    expected=conninfo_to_dict(os.environ['V4_NATIVE_PG_DSN'])
    original=psycopg.connect
    allowed_identities={tuple(expected[k] for k in ('host','port','dbname','user'))}
    fixture_clusters={}
    phase0_identity=None
    v41011_identity=None
    from scripts.v4_closeout_v41011_sql_fixture import RECEIPT as SQL_RECEIPT,DATABASE as SQL_DATABASE,verify as verify_full_sql,connection as sql_connection
    if SQL_RECEIPT.exists():
        sql_receipt=json.loads(SQL_RECEIPT.read_bytes())
        with original(**sql_connection(SQL_DATABASE)) as witness:verify_full_sql(witness,sql_receipt)
        v41011_identity=tuple(str(sql_connection(SQL_DATABASE)[k]) for k in ('host','port','dbname','user'))
    from scripts.v4_closeout_phase0_clean_fixture import RECEIPT,CONTRACT,DATABASE,connection,identity
    if RECEIPT.exists():
        receipt=json.loads(RECEIPT.read_bytes())
        if receipt['contract']!=CONTRACT or receipt['database']!=DATABASE or receipt['production_authorized'] is not False:
            raise V4DatabaseGuardViolation('PHASE0_EXACT_ENGINEERING_CONTRACT_REQUIRED')
        root=Path(__file__).resolve().parents[1]
        with original(**connection(DATABASE)) as witness:
            identity(witness)
            if witness.execute('select contract,admission from r4_evidence.phase0_clean_fixture').fetchall()!=[(CONTRACT,'ENGINEERING_ONLY_NO_PRODUCTION_AUTHORITY')]:
                raise V4DatabaseGuardViolation('PHASE0_ENGINEERING_MARKER_REQUIRED')
            actual=dict(witness.execute('select version,checksum_sha256 from v4_meta.schema_migrations').fetchall())
            for row in receipt['migrations']:
                raw=(root/row['path']).read_bytes()
                if hashlib.sha256(raw).hexdigest()!=row['source_sha256'] or actual.get(row['version'],'').strip()!=row['sql_checksum_sha256']:
                    raise V4DatabaseGuardViolation('PHASE0_EXECUTED_SQL_SOURCE_REQUIRED')
        phase0_identity=tuple(str(connection(DATABASE)[k]) for k in ('host','port','dbname','user'))
    capability=os.environ.get('R4_PG_TEST_CAPABILITIES')
    if capability:
        path=Path(capability).resolve()
        if not path.is_relative_to(Path(__file__).resolve().parents[1]/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b'):raise V4DatabaseGuardViolation('R4_CAPABILITY_MANIFEST_OUTSIDE_AUDIT')
        manifest=json.loads(path.read_bytes())
        if manifest.get('contract_id')!='R4_ISOLATED_PG_TEST_CAPABILITIES_R1':raise V4DatabaseGuardViolation('R4_CAPABILITY_CONTRACT_REQUIRED')
        for item in manifest['databases']:
            if item['purpose']!='FEP_ENGINEERING_FIXTURE_R1' or item['database'] not in ('fep_e1_fresh','fep_e1_upgrade'):raise V4DatabaseGuardViolation('R4_CAPABILITY_SCOPE_ESCAPE')
            if item['port'] not in ('55792','55793'):raise V4DatabaseGuardViolation('R4_CAPABILITY_PORT_SCOPE_ESCAPE')
            dsn=dict(expected,dbname=item['database'],port=item['port'])
            with original(**dsn) as pg:
                actual=Path(pg.execute('SHOW data_directory').fetchone()[0]).resolve()
                if actual!=Path(item['data_directory']).resolve() or not actual.is_relative_to(Path('G:/codex_tmp/full_system_r4_fbd23a6b').resolve()):raise V4DatabaseGuardViolation('R4_CAPABILITY_CLUSTER_IDENTITY_MISMATCH')
                if pg.execute('SELECT count(*) FROM r4_evidence.migrations').fetchone()[0]!=33:raise V4DatabaseGuardViolation('R4_CAPABILITY_001_033_REQUIRED')
            allowed_identities.add(tuple(dsn[k] for k in ('host','port','dbname','user')))
            fixture_clusters[(dsn['host'],dsn['port'],dsn['user'])]=(item['database'],actual)
    extra=os.environ.get('R4_R3_EXTRA_PG_FIXTURES')
    if extra:
        path=Path(extra).resolve();root=Path(__file__).resolve().parents[1]
        if not path.is_relative_to(root/'docs/audits/r4_r3_scope_20261011'):
            raise V4DatabaseGuardViolation('R3_EXTRA_FIXTURE_MANIFEST_ESCAPE')
        manifest=json.loads(path.read_bytes())
        if manifest.get('contract_id') not in ('R4_R3_EXPLICIT_ENGINEERING_PG_FIXTURES_R1','R4_R3_EXPLICIT_ENGINEERING_PG_FIXTURES_R2'):
            raise V4DatabaseGuardViolation('R3_EXPLICIT_FIXTURE_CONTRACT_REQUIRED')
        admitted={'fep_e5b_fresh','fep_e5b_upgrade','fep_e1_upgrade','fep_authority_isolated'}
        signal_databases={'fep_signal_baseline32_fresh','fep_signal_baseline32_upgrade','fep_signal_baseline32_actual_fresh'}
        if manifest['contract_id']=='R4_R3_EXPLICIT_ENGINEERING_PG_FIXTURES_R2':
            predecessor=root/'docs/audits/r4_r3_scope_20261011/R3_EXTRA_PG_FIXTURES.json'
            if manifest.get('predecessor_sha256')!=hashlib.sha256(predecessor.read_bytes()).hexdigest() or manifest.get('production_authorized') is not False or manifest.get('source_or_maturity_admission') is not False:
                raise V4DatabaseGuardViolation('R3_EXACT_ENGINEERING_FIXTURE_PREDECESSOR_REQUIRED')
            admitted.update(signal_databases)
        for row in manifest['databases']:
            if row['database'] not in admitted or row['port'] not in ('55792','55793','55794'):
                raise V4DatabaseGuardViolation('R3_FIXTURE_DATABASE_OR_PORT_SCOPE_ESCAPE')
            if row['port']=='55794' and (row['database'] not in ('fep_e5b_fresh','fep_signal_baseline32_actual_fresh') or Path(row['data_directory']).resolve()!=Path('G:/codex_tmp/r4_r3_fep_fixtures/fresh_data').resolve()):
                raise V4DatabaseGuardViolation('R3_FRESH_FIXTURE_IDENTITY_SCOPE_ESCAPE')
            if row['database'] in signal_databases and row['database']!='fep_signal_baseline32_actual_fresh' and (row['port']!='55793' or Path(row['data_directory']).resolve()!=Path('G:/codex_tmp/r4_r3_fep_fixtures/upgrade_data').resolve()):
                raise V4DatabaseGuardViolation('R3_SIGNAL_BASELINE_FIXTURE_IDENTITY_ESCAPE')
            if row['database']=='fep_signal_baseline32_actual_fresh' and row['port']!='55794':raise V4DatabaseGuardViolation('R3_ACTUAL_FRESH_SIGNAL_FIXTURE_PORT_REQUIRED')
            params=dict(expected,dbname=row['database'],port=row['port'])
            with original(**params) as witness:
                actual=Path(witness.execute('show data_directory').fetchone()[0]).resolve()
                if actual!=Path(row['data_directory']).resolve() or not actual.is_relative_to(Path('G:/codex_tmp').resolve()):
                    raise V4DatabaseGuardViolation('R3_FIXTURE_CLUSTER_IDENTITY_MISMATCH')
                if row['database'] in signal_databases:
                    marker=witness.execute('SELECT contract,source_receipt_sha256,admission FROM r4_evidence.signal_baseline_fixture').fetchall()
                    receipt=root/'docs/audits/r4_r3_scope_20261011/FEP_SIGNAL_BASELINE32_FIXTURE_RECEIPT_R1.json'
                    if row['database']=='fep_signal_baseline32_actual_fresh':receipt=root/'docs/audits/r4_r3_scope_20261011/FEP_SIGNAL_ACTUAL_FRESH_BASELINE32_RECEIPT_R1.json'
                    if marker!=[('R4_R3_FEP_SIGNAL_BASELINE32_ENGINEERING_R1',hashlib.sha256(receipt.read_bytes()).hexdigest(),'NOT_REAL_MATURITY_OR_PRODUCTION_ACCEPTANCE')]:
                        raise V4DatabaseGuardViolation('R3_EXACT_SIGNAL_BASELINE_FIXTURE_MARKER_REQUIRED')
                elif row['database']=='fep_authority_isolated':
                    if witness.execute("select contract from r4_evidence.fixture_identity").fetchall()!=[('FEP_AUTHORITY_SYNTHETIC_ENGINEERING_R1',)]:
                        raise V4DatabaseGuardViolation('R3_AUTHORITY_SYNTHETIC_FIXTURE_MARKER_REQUIRED')
                elif witness.execute('select count(*) from r4_evidence.migrations').fetchone()[0]!=33:
                    raise V4DatabaseGuardViolation('R3_FIXTURE_33_SQL_RECEIPTS_REQUIRED')
            allowed_identities.add(tuple(params[k] for k in ('host','port','dbname','user')))
            if row['database']=='fep_e1_upgrade':fixture_clusters[(params['host'],params['port'],params['user'])]=(row['database'],actual)
    with original(os.environ['V4_NATIVE_PG_DSN']) as pg:
        actual=Path(pg.execute('SHOW data_directory').fetchone()[0]).resolve()
        if actual!=Path(os.environ['R4_PG_DATA_DIRECTORY']).resolve() or not actual.is_relative_to(Path('G:/codex_tmp').resolve()): raise V4DatabaseGuardViolation('R4_ISOLATED_PG_IDENTITY_MISMATCH')
    patch=pytest.MonkeyPatch();config._r4_patch=patch
    def guarded_pg(conninfo='',**kwargs):
        parsed=conninfo_to_dict(conninfo,**{k:kwargs[k] for k in ('host','port','dbname','user') if k in kwargs})
        decision='ALLOW' if tuple(parsed.get(k) for k in ('host','port','dbname','user')) in allowed_identities else 'REJECT'
        if phase0_identity and tuple(str(parsed.get(k)) for k in ('host','port','dbname','user'))==phase0_identity and ACTIVE and ACTIVE.startswith('tests/v4_phase0/test_postgres_schema.py::'):
            decision='ALLOW'
        if v41011_identity and tuple(str(parsed.get(k)) for k in ('host','port','dbname','user'))==v41011_identity and ACTIVE and ACTIVE.startswith(('tests/v4_10/','tests/v4_11/','tests/v4_a09/test_consumer_identity_sql.py::')):
            decision='ALLOW'
        cluster=fixture_clusters.get(tuple(parsed.get(k) for k in ('host','port','user')))
        if decision=='REJECT' and cluster and ACTIVE and ACTIVE.endswith('test_E1_24_concurrent_cas_and_same_request'):
            base,directory=cluster;database=parsed.get('dbname','')
            if database=='postgres' or re.fullmatch(re.escape(base)+r'_concurrency_[0-9a-f]{8}',database):
                with original(conninfo) as witness:
                    if Path(witness.execute('SHOW data_directory').fetchone()[0]).resolve()!=directory:raise V4DatabaseGuardViolation('R4_DYNAMIC_FIXTURE_DIRECTORY_MISMATCH')
                    if database!='postgres' and witness.execute('SELECT count(*) FROM r4_evidence.migrations').fetchone()[0]!=33:raise V4DatabaseGuardViolation('R4_DYNAMIC_FIXTURE_SQL_IDENTITY_REQUIRED')
                decision='ALLOW'
        if decision=='REJECT' and cluster and ACTIVE and ACTIVE.endswith('test_actual_fep_migration_rollback'):
            base,directory=cluster;database=parsed.get('dbname','')
            if base=='fep_e1_upgrade' and (database=='postgres' or re.fullmatch(r'fep_e1_rollback_[0-9a-f]{8}',database)):
                with original(conninfo) as witness:
                    if Path(witness.execute('SHOW data_directory').fetchone()[0]).resolve()!=directory:
                        raise V4DatabaseGuardViolation('R3_ROLLBACK_DRILL_CLUSTER_MISMATCH')
                decision='ALLOW'
        EVENTS.append(dict(nodeid=ACTIVE,engine='postgresql',decision=decision,stack=traceback.format_stack(limit=8)))
        if decision=='REJECT': raise V4DatabaseGuardViolation('R4_UNATTESTED_PG_FORBIDDEN')
        return original(conninfo,**kwargs)
    patch.setattr(psycopg,'connect',guarded_pg)
    def sql_audit(original):
        def call(owner,query,*args,**kwargs):
            pg=owner if isinstance(owner,psycopg.Connection) else owner.connection
            text=query if isinstance(query,str) else query.as_string(pg) if hasattr(query,'as_string') else '<BINARY_SQL>'
            operation=text.lstrip().split(None,1)[0].upper() if text.strip() else 'EMPTY'
            EVENTS.append(dict(event='SQL_INTENT',nodeid=ACTIVE,engine='postgresql',database=pg.info.dbname,user=pg.info.user,host=pg.info.host,port=pg.info.port,operation=operation,read_write='READ' if operation in ('SELECT','SHOW','EXPLAIN') else 'WRITE_OR_CONTROL',relations=re.findall(r'\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+([a-zA-Z_][a-zA-Z0-9_.]*)',text,re.I)[:12],query_sha256=hashlib.sha256(text.encode()).hexdigest(),parameters_persisted=False))
            return original(owner,query,*args,**kwargs)
        return call
    for owner,method in ((psycopg.Connection,'execute'),(psycopg.Cursor,'execute'),(psycopg.Cursor,'executemany'),(psycopg.ServerCursor,'execute')):
        patch.setattr(owner,method,sql_audit(getattr(owner,method)))
    def reject(engine):
        def call(*args,**kwargs):
            EVENTS.append(dict(nodeid=ACTIVE,engine=engine,decision='REJECT',stack=traceback.format_stack(limit=8)))
            raise V4DatabaseGuardViolation('R4_NON_POSTGRES_FORBIDDEN:'+engine)
        return call
    import sqlite3
    patch.setattr(sqlite3,'connect',reject('sqlite3'))
    try: import duckdb
    except ImportError: pass
    else: patch.setattr(duckdb,'connect',reject('duckdb'))

def pytest_sessionfinish(session,exitstatus):
    p=Path(os.environ['R4_CONNECTION_LEDGER']);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix('.tmp');tmp.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in EVENTS),encoding='utf8');os.replace(tmp,p)

def pytest_unconfigure(config):
    global FILESYSTEM_GUARD_ACTIVE
    FILESYSTEM_GUARD_ACTIVE=False
    if hasattr(config,'_r4_patch'): config._r4_patch.undo()

def pytest_collection_modifyitems(session,config,items):
    if os.environ.get('R4_R3_EXTRA_PG_FIXTURES'):
        from scripts import run_fep_e5_r1r1b as builder
        from scripts.forward_remainder_pg import typed_pit
        # Explicit modern canonical fixture names, never a historical live DSN.
        # The builder validates the explicit manifest and selects each dedicated
        # cluster. Do not replace its fresh identity with the shared FEP cluster.
        for item in items:
            if item.module.__name__.rsplit('.',1)[-1]=='test_e5_reconstruction':
                item.module.pit_seed=typed_pit
            if item.nodeid.endswith('test_actual_fep_migration_rollback'):
                item.user_properties.append(('requires_upgrade_fixture',True))
    path=Path(os.environ['R4_CONNECTION_LEDGER']).with_name(Path(os.environ['R4_CONNECTION_LEDGER']).stem+'_COLLECTED_NODES.json')
    value=dict(contract_id='R4_R3_EXACT_COLLECTED_NODE_SET_R1',nodes=[item.nodeid for item in items],
               modules=sorted({str(item.path.relative_to(Path(__file__).resolve().parents[1])).replace('\\','/') for item in items}),
               source_sha256={str(item.path.relative_to(Path(__file__).resolve().parents[1])).replace('\\','/'):hashlib.sha256(item.path.read_bytes()).hexdigest() for item in items})
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(temp,path)

@pytest.fixture(autouse=True)
def r3_exact_upgrade_fixture_for_migration_drill(request,monkeypatch):
    if os.environ.get('R4_R3_EXTRA_PG_FIXTURES') and request.node.name=='test_actual_fep_migration_rollback':
        monkeypatch.setenv('FEP_E1_TEST_DSN','host=127.0.0.1 port=55793 user=r4_isolated_admin dbname=fep_e1_upgrade')

@pytest.fixture(autouse=True)
def v4_r3_exact_historical_v12_validator_root(request, monkeypatch):
    """Frozen V4-12 promotion replay reads its accepted stage, never moves Head.

    Only the five historical release-validator tests use this profile; current
    V4 consumers and numerical primitives continue to run against current code.
    """
    selected = {
        'test_contract_local_gate_and_negative_vectors': ('validate_v4_12_snapshot_v2_contract',),
        'test_full_independent_persisted_multi_anchor_oracle': ('validate_v4_12_r12_runtime',),
        'test_persisted_independent_a_oracle': ('validate_v4_12_r11_chain',),
        'test_persisted_independent_b_oracle': ('validate_v4_12_r11_chain',),
        'test_real_candidate_unknown_readback': ('validate_v4_12_runtime_r1','validate_v4_12_runtime_entry_r1'),
    }
    names = selected.get(request.node.name)
    if not names or not request.module.__name__.rsplit('.',1)[-1].startswith('test_v4_12_'): return
    import subprocess
    import importlib
    root = Path('G:/codex_tmp/test_temp/remainder_historical_stage13')
    expected = '7986acdb4db19e85f55045dbfc692c932d4e1499'
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip() != expected:
        raise V4DatabaseGuardViolation('V4_12_HISTORICAL_PROFILE_COMMIT_MISMATCH')
    for name in names:
        module=importlib.import_module('scripts.' + name)
        monkeypatch.setattr(module, 'ROOT', root)
        if hasattr(module,'protected_bytes'):
            original=module.protected_bytes
            def exact_git_agents(selected,path,sha256,_original=original):
                if path != 'AGENTS.md': return _original(selected,path,sha256)
                raw=subprocess.check_output(['git','show',expected+':AGENTS.md'],cwd=root)
                if hashlib.sha256(raw).hexdigest()!=sha256:
                    raise V4DatabaseGuardViolation('HISTORICAL_AGENTS_EXACT_GIT_SHA_MISMATCH')
                return raw
            monkeypatch.setattr(module,'protected_bytes',exact_git_agents)
    EVENTS.append(dict(event='EXACT_HISTORICAL_V4_12_PROFILE',nodeid=request.node.nodeid,root=str(root),
                       source_head=expected,meaning='Historical accepted V4 contract replay only; current runtime Head unchanged'))
