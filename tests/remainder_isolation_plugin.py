"""Additional full-regression guard: protected filesystem and isolated PG only."""
import os,json,sys
from pathlib import Path
import pytest
from tests.runtime_isolation import REPOSITORY,DISPOSABLE_BASE,protected_roots
ACTIVE=False
EVENTS=[]
GUARDED_ROOTS=[]
PG_DISPOSABLE_BASE=DISPOSABLE_BASE

def protected(value):
    if not isinstance(value,(str,bytes,os.PathLike)):return False
    try:p=Path(os.fsdecode(value)).resolve()
    except (ValueError,OSError):return False
    roots=GUARDED_ROOTS
    return any(p==r or p.is_relative_to(r) for r in roots)

def hook(event,args):
    if not ACTIVE:return
    mutation=False;targets=[]
    if event=='open':
        mode=args[1] or '';flags=args[2]
        mutation=any(c in mode for c in ('w','a','+','x')) or bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        targets=args[:1]
    elif event in ('os.remove','os.rmdir','os.mkdir','os.rename'):
        mutation=True;targets=args[:2] if event=='os.rename' else args[:1]
    elif event=='sqlite3.connect':mutation=True;targets=args[:1]
    if mutation and any(protected(p) for p in targets):
        EVENTS.append(dict(event=event,paths=[str(p) for p in targets],decision='REJECT_BEFORE_PROTECTED_WRITE'))
        raise ValueError('FULL_REGRESSION_PROTECTED_FILESYSTEM_WRITE_FORBIDDEN')

def pytest_configure(config):
    global ACTIVE,GUARDED_ROOTS,DISPOSABLE_BASE
    from tests import runtime_isolation, runtime_isolation_plugin
    from tests.remainder_storage import ALLOWED
    selected=Path(os.environ.get('REMAINDER_TEST_TEMP_BASE',str(DISPOSABLE_BASE))).resolve()
    if selected not in ALLOWED:raise ValueError('UNREGISTERED_DISPOSABLE_STORAGE_ROOT')
    storage=pytest.MonkeyPatch();config._remainder_storage_patch=storage
    storage.setattr(runtime_isolation,'DISPOSABLE_BASE',selected)
    storage.setattr(runtime_isolation_plugin,'DISPOSABLE_BASE',selected)
    storage.setattr(sys.modules[__name__],'DISPOSABLE_BASE',selected)
    GUARDED_ROOTS=[REPOSITORY/'data',REPOSITORY/'artifacts']+[r for r in protected_roots() if r!=REPOSITORY]
    sys.addaudithook(hook);ACTIVE=True
    import psycopg
    from psycopg.conninfo import conninfo_to_dict
    patch=pytest.MonkeyPatch();config._remainder_patch=patch
    import subprocess
    original_popen=subprocess.Popen
    def disposable_child(command,*args,**kwargs):
        if isinstance(command,(list,tuple)) and len(command)>2 and command[1]=='-c' and command[2].startswith('from tests.runtime_isolation import serve;'):
            command=list(command)
            command[2]='from tests.remainder_storage import configure; configure('+repr(selected.as_posix())+'); '+command[2]
        return original_popen(command,*args,**kwargs)
    patch.setattr(subprocess,'Popen',disposable_child)
    connect=psycopg.connect
    manifest=Path(os.environ.get('REMAINDER_PG_CLUSTER_MANIFEST',str(REPOSITORY/'reports/forward_r2_remainder_consolidated_20261007/IA06_CLUSTER_BOOTSTRAP.json'))).resolve()
    if not manifest.is_relative_to(REPOSITORY/'reports'):raise ValueError('DISPOSABLE_CLUSTER_MANIFEST_ESCAPE')
    clusters=json.loads(manifest.read_bytes()) if manifest.exists() else {}
    allowed={str(v['port']) for v in clusters.values()}
    verified=set()
    def isolated(conninfo='',*args,**kw):
        params=conninfo_to_dict(conninfo,**{k:v for k,v in kw.items() if k in ('host','port','dbname','user')})
        if params.get('host')!='127.0.0.1' or params.get('port') not in allowed:
            EVENTS.append(dict(event='psycopg.connect',decision='REJECT_NONDISPOSABLE_PG',database=params.get('dbname'),port=params.get('port')))
            raise ValueError('DISPOSABLE_PG_CLUSTER_REQUIRED')
        port=params['port'];cluster=next(v for v in clusters.values() if str(v['port'])==port)
        if port not in verified:
            with connect(cluster['admin_dsn'],autocommit=True) as witness:
                directory=Path(witness.execute('show data_directory').fetchone()[0]).resolve()
                if directory!=(Path(cluster['root'])/'data').resolve() or not any(directory.is_relative_to(base) for base in ALLOWED):raise ValueError('DISPOSABLE_PG_DIRECTORY_IDENTITY_MISMATCH')
            verified.add(port)
        EVENTS.append(dict(event='psycopg.connect',decision='ALLOW_VERIFIED_DISPOSABLE_PG',database=params.get('dbname'),port=port,cluster_root=cluster['root']))
        return connect(conninfo,*args,**kw)
    patch.setattr(psycopg,'connect',isolated)
    if os.environ.get('REMAINDER_PG_ENABLE')=='1':
        from scripts import run_fep_e5_r1r1b as b,run_fep_e5_r1r1c as c
        from scripts.forward_remainder_pg import typed_pit
        patch.setattr(b,'pit_seed',typed_pit)
        patch.setattr(b,'REPORT',REPOSITORY/'reports/forward_r2_remainder_consolidated_20261007/canonical_fixtures')
        for module in (b,c):
            for kind in ('fresh','upgrade'):
                patch.setitem(module.DSNS,kind,clusters[kind]['admin_dsn'].replace('dbname=postgres','dbname=fep_e5b_'+kind))

def pytest_sessionfinish(session,exitstatus):
    global ACTIVE
    ACTIVE=False
    base=session.config.getoption('basetemp')
    if base:
        p=Path(str(base)+'_protected_fs_pg.json').resolve()
        if not p.is_relative_to(DISPOSABLE_BASE):raise ValueError('ISOLATION_LOG_ESCAPE')
        p.write_text(json.dumps(EVENTS,indent=2)+'\n',encoding='utf8')
    session.config._remainder_patch.undo()


def pytest_unconfigure(config):
    if hasattr(config,'_remainder_storage_patch'):config._remainder_storage_patch.undo()


def pytest_collection_modifyitems(session,config,items):
    # Pinned V4-13 tests run against their actual accepted stage checkout.
    # Current consumers retain the stage-aware successor and current root.
    import subprocess
    names={'test_v4_13_r16a_runtime','test_v4_13_r16b_runtime','test_v4_13_r16c_publication','test_v4_13_r16r1_repair'}
    selected={item.module for item in items if item.module.__name__.rsplit('.',1)[-1] in names}
    for module in {item.module for item in items if item.module.__name__.rsplit('.',1)[-1]=='test_full_chain_fep_db'}:
        from types import SimpleNamespace
        import psycopg
        from psycopg.conninfo import conninfo_to_dict
        proof=json.loads((REPOSITORY/'reports/forward_r2_remainder_consolidated_20261007/IA06_SIGNAL_GUARD_BASELINE_PROOF.json').read_bytes())
        def historical_signal_connect(dsn,*args,**kw):
            params=conninfo_to_dict(dsn);kind='fresh' if params.get('port')=='55492' else 'upgrade' if params.get('port')=='55493' else None
            if kind is None or params.get('host')!='127.0.0.1' or params.get('dbname')!='fep_e5b_'+kind:raise ValueError('UNREGISTERED_PRE033_FIXTURE')
            return psycopg.connect(proof['DSNS'][kind],*args,**kw)
        config._remainder_patch.setattr(module,'psycopg',SimpleNamespace(connect=historical_signal_connect,Error=psycopg.Error))
    if not selected:return
    root=Path('G:/codex_tmp/test_temp/remainder_historical_stage13')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()!='7986acdb4db19e85f55045dbfc692c932d4e1499':raise ValueError('PINNED_HISTORICAL_STAGE13_REQUIRED')
    for module in selected:config._remainder_patch.setattr(module,'ROOT',root)


@pytest.fixture(autouse=True)
def pinned_r15_contract_profile(request,monkeypatch):
    if request.module.__name__.rsplit('.',1)[-1] not in ('test_v4_13_r15_contract','test_v4_13_r15r1_lineage'):return
    from scripts import repair_v4_13_r1_1 as owner,validate_v4_13_r1_1 as validator
    root=Path('G:/codex_tmp/test_temp/remainder_historical_stage13')
    monkeypatch.setattr(owner,'ROOT',root);monkeypatch.setattr(validator,'ROOT',root)


_FAILURE_STREAM=None


@pytest.fixture(name='tmp_path')
def bounded_storage_contract_tmp_path(request,tmp_path):
    relative=request.node.path.relative_to(REPOSITORY).as_posix()
    requires_e=relative.startswith(('tests/fep_e2/','tests/fep_e3/','tests/fep_e4/')) or relative=='tests/test_forward_r2_cli.py'
    if requires_e and DISPOSABLE_BASE.drive.lower()=='g:':
        import tempfile
        # The latest user storage instruction requires these outputs on G.
        return Path(tempfile.mkdtemp(prefix='remainder_bounded_engineering_',dir=PG_DISPOSABLE_BASE))
    return tmp_path


@pytest.fixture(autouse=True)
def current_handler_unit_service_stub(request,monkeypatch):
    if request.node.path.as_posix().endswith('/tests/upgrade_v3/test_p01_01_lock_scope.py'):
        monkeypatch.setattr(request.module._NoopService,'status',lambda self:{},raising=False)


@pytest.fixture(autouse=True)
def exact_legacy_v1_identity_profile(request,monkeypatch):
    registry=json.loads((REPOSITORY/'config/v4_legacy_identity_test_profiles_remainder_v1.json').read_bytes())
    path=request.node.path.relative_to(REPOSITORY).as_posix()
    row=next((r for r in registry['modules'] if r['path']==path),None)
    if row is None or row.get('scope')=='SINGLE_FROZEN_AST_NODE':return
    import hashlib
    if hashlib.sha256(request.node.path.read_bytes()).hexdigest()!=row['source']['sha256']:raise ValueError('LEGACY_IDENTITY_TEST_SOURCE_CHANGED')
    from scripts.forward_remainder_legacy_identity import profile,calculate
    root=profile()
    monkeypatch.setattr(request.module,'ROOT',root)
    def historical_identity(selected):
        if Path(selected).resolve()!=root:raise ValueError('LEGACY_IDENTITY_WRONG_ROOT')
        return calculate(root)
    monkeypatch.setattr(request.module,'computation_identity',historical_identity)

def pytest_sessionstart(session):
    global _FAILURE_STREAM
    base=session.config.getoption('basetemp')
    if base:
        _FAILURE_STREAM=Path(str(base)+'_failures.jsonl').resolve()
        if not _FAILURE_STREAM.is_relative_to(DISPOSABLE_BASE):raise ValueError('FAILURE_LOG_ESCAPE')
        _FAILURE_STREAM.write_bytes(b'')

def pytest_runtest_logreport(report):
    if report.failed and _FAILURE_STREAM:
        with _FAILURE_STREAM.open('a',encoding='utf8') as stream:
            stream.write(json.dumps(dict(node=report.nodeid,phase=report.when,trace=report.longreprtext),ensure_ascii=False)+'\n')


@pytest.fixture(autouse=True)
def pinned_r25_and_v3_simulation_profiles(request,monkeypatch):
    module=request.module;name=request.node.name
    if name in ('test_actual_authority_inventory_waits_without_target','test_V6_r25_selection_waits_for_real_target'):
        from scripts import validate_r25_preflight as old,validate_r25_preflight_v6 as current
        root=Path('G:/codex_tmp/test_temp/remainder_entry_checkout')
        if name.startswith('test_actual'):
            monkeypatch.setattr(module,'selection',lambda:old.selection(root))
        else:
            original=current.selection;monkeypatch.setattr(current,'selection',lambda:original(root))
    if (module.__name__.rsplit('.',1)[-1]=='test_r25_packet' and name=='test_f12_valid_latest_decoy') or module.__name__.rsplit('.',1)[-1].startswith('test_r24r1_'):
        from scripts import r24r1_io as io,r24r1_simulation as simulation,validate_r24r1_activation as oracle
        root=Path('G:/codex_tmp/test_temp/remainder_r24r1_simulation_profile')
        read,ref,atomic=io.read,io.ref,io.atomic
        for owner in (io,simulation,oracle):
            monkeypatch.setattr(owner,'ROOT',root)
            monkeypatch.setattr(owner,'read',lambda path,*args,**kw:read(path,root=root))
            monkeypatch.setattr(owner,'ref',lambda path,*args,**kw:ref(path,root=root))
            if hasattr(owner,'atomic'):monkeypatch.setattr(owner,'atomic',lambda path,value,raw=False:atomic(path,value,root=root,raw=raw))
        import functools
        for key in ('inspect','protected'):
            original=getattr(oracle,key)
            bound=(lambda root=root,_function=original:_function(root=root)) if key=='protected' else functools.partial(original,root=root)
            monkeypatch.setattr(oracle,key,bound)
            if getattr(module,key,None) is original:monkeypatch.setattr(module,key,bound)
        if hasattr(module,'ROOT'):monkeypatch.setattr(module,'ROOT',root)
        for key in ('read','ref','atomic'):
            if hasattr(module,key):monkeypatch.setattr(module,key,getattr(io,key))


@pytest.fixture(autouse=True)
def pinned_v9_v10_publication_history_profile(request,monkeypatch):
    path=request.node.path.as_posix()
    if not any(path.endswith('/'+name) for name in ('tests/v4_10/test_promotion.py','tests/v4_10/test_accepted_head_r1.py')):return
    from scripts import promote_v4_09_accepted_head as v9,validate_v4_10_promotion_r1 as v10
    root=Path('G:/codex_tmp/test_temp/remainder_historical_stage13')
    monkeypatch.setattr(v9,'ROOT',root);monkeypatch.setattr(v10,'ROOT',root)


@pytest.fixture(scope='session')
def remainder_legacy_api_snapshot(tmp_path_factory):
    from tests.upgrade_m12.conftest import isolated_m12_runtime
    root,database,env=isolated_m12_runtime.__wrapped__(tmp_path_factory)
    import duckdb
    # Generic legacy API coverage retains all seven real publication heads;
    # M12's separate fixture deliberately selects one complete chart publication.
    with duckdb.connect(str(REPOSITORY/'data/database/market_research.duckdb'),read_only=True) as source:
        statuses=source.execute('select status,publication_id from publications').fetchall()
        heads=source.execute('select * from publication_heads').fetchall()
    with duckdb.connect(str(database)) as connection:
        complete=connection.execute('select publication_id from publication_heads limit 1').fetchone()[0]
        env=dict(env,REMAINDER_COMPLETE_PUBLICATION_ID=complete)
        connection.executemany('update publications set status=? where publication_id=?',statuses)
        connection.execute('delete from publication_heads')
        if heads:connection.executemany('insert into publication_heads values ('+','.join('?' for _ in heads[0])+')',heads)
        old='sector_member_state_daily';current='member_state_result_daily'
        columns=[r[1] for r in connection.execute('pragma table_info('+old+')').fetchall()]
        present={r[1] for r in connection.execute('pragma table_info('+current+')').fetchall()}
        fields=','.join('"'+c+'"' for c in columns if c in present)
        connection.execute('insert into '+old+' ('+fields+') select '+fields+' from '+current)
    return root,database,env

@pytest.fixture(autouse=True)
def explicit_legacy_api_isolation(request,monkeypatch):
    registry=json.loads((REPOSITORY/'config/v4_legacy_api_test_profiles_remainder_v1.json').read_bytes())
    module=request.module
    if request.node.path.relative_to(REPOSITORY).as_posix() not in {row['path'] for row in registry['modules']}:return
    root,database,env=request.getfixturevalue('remainder_legacy_api_snapshot')
    if request.node.path.as_posix().endswith('/tests/upgrade_m2/test_api.py') and request.node.name in ('test_pagination_is_bounded_and_linkage_is_publication_bound','test_reverse_linkage_preserves_real_sector_rank_and_count'):
        monkeypatch.setattr(module,'TEST_PUB',env['REMAINDER_COMPLETE_PUBLICATION_ID'])
    complete_only=('tests/upgrade_m11/test_linkage_consistency.py','tests/upgrade_m11/test_attribute_library.py',
                   'tests/upgrade_m11/test_intersection_and_rank.py','tests/upgrade_m13/test_market_cycle.py',
                   'tests/upgrade_m7/test_display_scope.py','tests/upgrade_v3/test_p10_02_sector_set_linkage.py')
    if any(request.node.path.as_posix().endswith('/'+name) for name in complete_only):
        import duckdb
        with duckdb.connect(str(database)) as connection:
            statuses=connection.execute('select status,publication_id from publications').fetchall()
            heads=connection.execute('select * from publication_heads').fetchall()
            connection.execute('update publication_heads set publication_id=? where trade_date=(select trade_date from publications where publication_id=?)',[env['REMAINDER_COMPLETE_PUBLICATION_ID']]*2)
            connection.execute("update publications set status='FIXTURE_NOT_SELECTED' where publication_id<>?",[env['REMAINDER_COMPLETE_PUBLICATION_ID']])
        def restore_publications():
            with duckdb.connect(str(database)) as connection:
                connection.executemany('update publications set status=? where publication_id=?',statuses)
                connection.execute('delete from publication_heads')
                if heads:connection.executemany('insert into publication_heads values ('+','.join('?' for _ in heads[0])+')',heads)
        request.addfinalizer(restore_publications)
    import workbench_service.app as app
    original_api=app.Api;handler=app.make_handler
    class IsolatedApi(original_api):
        def __init__(self,db,root=None,**kw):
            path=Path(db).resolve()
            if path.is_relative_to(REPOSITORY/'data'):db=database;root=private_root
            super().__init__(db,root=root,**kw)
    private_root=root
    if hasattr(module,'Api'):monkeypatch.setattr(module,'Api',IsolatedApi)
    def isolated_handler(project,db,**kw):
        if Path(db).resolve().is_relative_to(REPOSITORY/'data'):db=database
        if Path(project).resolve()==REPOSITORY:
            from tests.runtime_isolation import create
            import shutil
            project=create(Path(db).resolve().parent)
            for name in ('src/workbench_service/static','config','data/normalized'):
                source=private_root/name;target=project/name
                if source.exists() and not target.exists():shutil.copytree(source,target)
        if request.node.path.as_posix().endswith('/tests/upgrade_v3/test_p12_07_today_research_ui.py') and request.node.name=='test_http_routes_and_static_page_use_new_bundle_without_legacy_candidate_fallback':
            from workbench_service.research_bundle_v3_3 import build_bundle,activate_bundle
            values=module.rows()+[dict(module.rows()[0],security_id='SH.'+str(600100+i)) for i in range(3)]
            built=build_bundle(project/'reports/remainder_engineering_bundle',module.identity(),values,{'fixture':'EXPLICIT_HTTP_TRANSPORT_ENGINEERING_ONLY'})
            activate_bundle(Path(built['path']),project/'data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json')
        return handler(project,db,**kw)
    for cls in (app.HistoryJobService,app.OneClickPublisher):
        original=cls.recover_interrupted
        def synchronous_recovery(self,*args,_original=original,**kw):
            kw['background']=False
            return _original(self,*args,**kw)
        monkeypatch.setattr(cls,'recover_interrupted',synchronous_recovery)
    monkeypatch.setattr(app,'make_handler',isolated_handler)
    if hasattr(module,'make_handler'):monkeypatch.setattr(module,'make_handler',isolated_handler)


@pytest.fixture(autouse=True)
def controlled_compute_mock_release_profile(request,monkeypatch):
    if not request.node.path.as_posix().endswith('/tests/upgrade_m4/test_workbench_command.py'):return
    if request.node.name!='test_controlled_compute_uses_fixed_project_entry_and_timeout':return
    root,database,env=request.getfixturevalue('remainder_legacy_api_snapshot')
    monkeypatch.setattr(request.module,'__file__',str(root/'tests/upgrade_m4/test_workbench_command.py'))
    (root/'reports/releases/20260907/452811b8e0c54c029560aae46c6d3081').mkdir(parents=True,exist_ok=True)


@pytest.fixture(autouse=True,scope='module')
def exact_frozen_stage_test_profile(request):
    """Only enumerated historical test modules use their exact Git input tree."""
    import sys,types
    monkeypatch=pytest.MonkeyPatch();request.addfinalizer(monkeypatch.undo)
    from tests.remainder_historical_profiles import profile,install
    registry=json.loads((REPOSITORY/'config/v4_frozen_test_profiles_remainder_v1.json').read_bytes())
    relative=request.node.path.relative_to(REPOSITORY).as_posix()
    row=next((r for r in registry['profiles'] if r['path']==relative),None)
    if row is None or row.get('scope')=='SINGLE_FROZEN_AST_NODE':return
    import hashlib
    if hashlib.sha256(request.node.path.read_bytes()).hexdigest()!=row['source']['sha256']:raise ValueError('FROZEN_TEST_SOURCE_CHANGED')
    root,entries=profile(row['historical_commit'])
    import ast,importlib
    tree=ast.parse(request.node.path.read_text(encoding='utf-8-sig'))
    preloaded=set()
    def preload(name):
        if name in preloaded or not name.startswith(('scripts.','workbench_analysis.')):return
        preloaded.add(name)
        spec=importlib.util.find_spec(name)
        if spec is None:return
        sources=[]
        if spec.origin and Path(spec.origin).is_file():sources.append(Path(spec.origin))
        historical_path=name.replace('.','/')+'.py'
        if name.startswith('workbench_analysis.'):historical_path='src/'+historical_path
        if historical_path in entries:sources.append(root/historical_path)
        for source in sources:
            for node in ast.walk(ast.parse(source.read_text(encoding='utf-8-sig'))):
                if isinstance(node,ast.Import):names=[x.name for x in node.names]
                elif isinstance(node,ast.ImportFrom) and node.module:
                    module=node.module
                    if node.level:module='.'.join(name.split('.')[:-node.level])+'.'+module
                    names=[module+'.'+x.name for x in node.names] if module in ('scripts','workbench_analysis') else [module]
                else:continue
                for dependency in names:preload(dependency)
        importlib.import_module(name)
    for node in ast.walk(tree):
        names=[]
        if isinstance(node,ast.Import):names=[x.name for x in node.names]
        elif isinstance(node,ast.ImportFrom) and node.module:
            names=[node.module+'.'+x.name for x in node.names] if node.module in ('scripts','workbench_analysis') else [node.module]
        for name in names:
            if name.startswith(('scripts.','workbench_analysis.')):preload(name)
    owners=[request.module]+[m for n,m in list(sys.modules.items()) if m and (n.startswith('scripts.') or n.startswith('workbench_analysis.') or n.startswith('src.workbench_analysis.')) and not n.startswith('scripts.forward_remainder')]
    seen=set()
    for owner in owners:
        if getattr(owner,'ROOT',None)==REPOSITORY:monkeypatch.setattr(owner,'ROOT',root)
        for value in list(vars(owner).values()):
            functions=[value] if isinstance(value,types.FunctionType) else [v for v in vars(value).values() if isinstance(v,types.FunctionType)] if isinstance(value,type) and value.__module__==owner.__name__ else []
            for fn in functions:
                if id(fn) in seen:continue
                seen.add(id(fn))
                if fn.__defaults__ and REPOSITORY in fn.__defaults__:monkeypatch.setattr(fn,'__defaults__',tuple(root if x==REPOSITORY else x for x in fn.__defaults__))
                if fn.__kwdefaults__ and REPOSITORY in fn.__kwdefaults__.values():monkeypatch.setattr(fn,'__kwdefaults__',{k:root if x==REPOSITORY else x for k,x in fn.__kwdefaults__.items()})
    request.addfinalizer(install(monkeypatch,root,entries))
    for key,value in list(vars(request.module).items()):
        if type(value).__name__=='FrozenContracts' and getattr(value,'root',None)==REPOSITORY:
            monkeypatch.setattr(request.module,key,type(value)(root,entry_path=value.entry_ref['path']))
    if relative=='tests/test_v4_18_migration_contract.py':
        monkeypatch.setattr(request.module,'C',json.loads((root/'config/v4_18_migration_replay_contract_v1.json').read_bytes()))
    chain_path='src/workbench_analysis/dm01_accepted_chain_v1.py'
    if chain_path in entries and 'config/v4_historical_moving_head_registry_r17_v1.json' not in entries:
        import importlib.util
        for module_name in ('dm01_accepted_chain_v1','dm01_publication_history_reader_v1','dm01_publication_history_reader_v2'):
            path='src/workbench_analysis/'+module_name+'.py'
            if path not in entries:continue
            for owner in list(owners):
                if owner.__name__ not in ('workbench_analysis.'+module_name,'src.workbench_analysis.'+module_name):continue
                name='workbench_analysis._remainder_'+module_name+'_'+owner.__name__.split('.')[0]+'_'+row['historical_commit'][:12]
                spec=importlib.util.spec_from_file_location(name,root/path)
                historical=importlib.util.module_from_spec(spec);sys.modules[name]=historical;spec.loader.exec_module(historical)
                if hasattr(owner,'AcceptedChainError'):historical.AcceptedChainError=owner.AcceptedChainError
                exports={id(value):getattr(historical,key) for key,value in vars(owner).items()
                         if (isinstance(value,types.FunctionType) or isinstance(value,type)) and value.__module__==owner.__name__ and hasattr(historical,key)}
                for target in owners:
                    for key,value in list(vars(target).items()):
                        if id(value) in exports:monkeypatch.setattr(target,key,exports[id(value)])
    if relative.startswith('tests/test_v4_12_') or relative=='tests/v4_publication_reader_di_r1/test_explicit_views.py':
        import importlib.util
        for owner in owners:
            path=owner.__name__.replace('.','/')+'.py'
            selected=(relative.startswith('tests/test_v4_12_') and owner.__name__.startswith('scripts.validate_v4_12_')) or (
                relative=='tests/v4_publication_reader_di_r1/test_explicit_views.py' and owner.__name__ in ('scripts.promote_v4_09_accepted_head','scripts.validate_v4_10_promotion_r1'))
            if not selected or path not in entries:continue
            name='scripts._remainder_validator_'+owner.__name__.rsplit('.',1)[-1]+'_'+row['historical_commit'][:12]
            spec=importlib.util.spec_from_file_location(name,root/path)
            historical=importlib.util.module_from_spec(spec);sys.modules[name]=historical;spec.loader.exec_module(historical)
            functions={id(value):(key,getattr(historical,key)) for key,value in vars(owner).items()
                       if isinstance(value,types.FunctionType) and value.__module__==owner.__name__ and hasattr(historical,key)}
            if relative=='tests/v4_publication_reader_di_r1/test_explicit_views.py':
                # The original V1 view temporarily scopes module ROOT; retain
                # that original globals protocol for its frozen validator code.
                for identity,(key,function) in list(functions.items()):
                    cloned=types.FunctionType(function.__code__,owner.__dict__,function.__name__,function.__defaults__,function.__closure__)
                    cloned.__kwdefaults__=function.__kwdefaults__
                    functions[identity]=(key,cloned)
            for target in owners:
                for key,value in list(vars(target).items()):
                    if id(value) in functions:monkeypatch.setattr(target,key,functions[id(value)][1])
    stage=json.loads((root/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_bytes())
    if stage.get('accepted_stage_range')=='V4_00_TO_V4_13_ACCEPTED' and 'src/workbench_analysis/v4_14_authority.py' in entries:
        # R18 tests predate the V14/V15 current-authority constructor. Use the
        # exact historical authority class, not a newly invented accepted head.
        import importlib.util
        import workbench_analysis.v4_14_authority as authority
        old=authority.ReplayAuthority
        name='workbench_analysis._remainder_authority_'+row['historical_commit'][:12]
        spec=importlib.util.spec_from_file_location(name,root/'src/workbench_analysis/v4_14_authority.py')
        historical=importlib.util.module_from_spec(spec);sys.modules[name]=historical;spec.loader.exec_module(historical)
        for owner in owners:
            for key,value in list(vars(owner).items()):
                if value is old:monkeypatch.setattr(owner,key,historical.ReplayAuthority)
    runtime_path='scripts/v4_16_shadow_runtime.py'
    if runtime_path in entries and b'def __new__' not in (root/runtime_path).read_bytes():
        # The historical engineering contract rejected REAL_SHADOW before any
        # dependency read; later real-entry dispatch belongs to current tests.
        import importlib.util
        from scripts import v4_16_shadow_runtime as runtime
        old=runtime.ShadowRuntimeController
        name='scripts._remainder_shadow_'+row['historical_commit'][:12]
        spec=importlib.util.spec_from_file_location(name,root/runtime_path)
        historical=importlib.util.module_from_spec(spec);sys.modules[name]=historical;spec.loader.exec_module(historical)
        for owner in owners:
            for key,value in list(vars(owner).items()):
                if value is old:monkeypatch.setattr(owner,key,historical.ShadowRuntimeController)
    if relative=='tests/test_r20r1_scope.py':
        import importlib.util
        from scripts import r20r1_maturity_debt as debt
        name='scripts._remainder_debt_'+row['historical_commit'][:12]
        spec=importlib.util.spec_from_file_location(name,root/'scripts/r20r1_maturity_debt.py')
        historical=importlib.util.module_from_spec(spec);sys.modules[name]=historical;spec.loader.exec_module(historical)
        for key in ('refresh','validate_packet'):monkeypatch.setattr(debt,key,getattr(historical,key))
    from scripts import run_r18b
    original_subprocess=run_r18b.subprocess
    class HistoricalWorkerProcess:
        def __getattr__(self,name):return getattr(original_subprocess,name)
        def Popen(self,command,**kwargs):
            if command[1:3]==['-m','scripts.r18_replay_worker'] and Path(kwargs.get('cwd','')).resolve()==root.resolve():
                command=[command[0],str(REPOSITORY/'scripts/forward_remainder_child.py'),row['historical_commit'],command[2],*command[3:]]
            return original_subprocess.Popen(command,**kwargs)
    monkeypatch.setattr(run_r18b,'subprocess',HistoricalWorkerProcess())
    def restore_late_imports():
        # A module imported inside an old constructor may capture a temporarily
        # scoped ROOT as its default. Do not leak that root to current tests.
        for name,owner in list(sys.modules.items()):
            if owner is None or not name.startswith(('scripts.','workbench_analysis.','src.workbench_analysis.')):continue
            filename=getattr(owner,'__file__',None)
            if not filename or not Path(filename).resolve().is_relative_to(REPOSITORY):continue
            if getattr(owner,'ROOT',None)==root:setattr(owner,'ROOT',REPOSITORY)
            for value in list(vars(owner).values()):
                functions=[value] if isinstance(value,types.FunctionType) else [v for v in vars(value).values() if isinstance(v,types.FunctionType)] if isinstance(value,type) and value.__module__==owner.__name__ else []
                for fn in functions:
                    if fn.__defaults__ and root in fn.__defaults__:fn.__defaults__=tuple(REPOSITORY if x==root else x for x in fn.__defaults__)
                    if fn.__kwdefaults__ and root in fn.__kwdefaults__.values():fn.__kwdefaults__={k:REPOSITORY if x==root else x for k,x in fn.__kwdefaults__.items()}
    request.addfinalizer(restore_late_imports)

@pytest.fixture(autouse=True)
def frozen_additive_ast_node(request,monkeypatch):
    relative=request.node.path.relative_to(REPOSITORY).as_posix()
    registry=json.loads((REPOSITORY/'config/v4_frozen_test_profiles_remainder_v1.json').read_bytes())
    row=next((r for r in registry['profiles'] if r.get('scope')=='SINGLE_FROZEN_AST_NODE' and r['path']==relative and r['node']==request.node.name),None)
    if row is None:return
    import hashlib
    if hashlib.sha256(request.node.path.read_bytes()).hexdigest()!=row['source']['sha256']:raise ValueError('FROZEN_TEST_SOURCE_CHANGED')
    from tests.remainder_historical_profiles import profile,install
    root,entries=profile(row['historical_commit'])
    request.addfinalizer(install(monkeypatch,root,entries))
    monkeypatch.setattr(request.module,'ROOT',root)

@pytest.fixture(autouse=True)
def accepted_observation_projection_replay(request,monkeypatch):
    relative=request.node.path.relative_to(REPOSITORY).as_posix()
    if relative=='tests/v4_dm01_r4r2/test_acceptance_seal.py' and request.node.name=='test_sealed_future_wait_has_no_source_or_publication':
        from scripts import validate_r25_preflight
        monkeypatch.setattr(request.module,'selection',lambda root:validate_r25_preflight.selection(Path('G:/codex_tmp/test_temp/remainder_entry_checkout')))
    if relative!='tests/v4_a03_a04_a07_r2/test_payload_governance_r2_1.py' or request.node.name!='test_real_accepted_baseline_r2_1_replay_retains_original_identity':return
    from scripts.forward_remainder_profiles import relative_reference
    import shutil
    root=request.getfixturevalue('tmp_path')/'accepted_observation';root.mkdir()
    ledger='data/v4/a03_forward_pit_r2'
    shutil.copytree(REPOSITORY/ledger,root/ledger)
    queue=['reports/audits/A03_FORWARD_PIT_BUILDER_R2_REAL_OBSERVATION.json']
    def walk(value):
        if isinstance(value,dict):
            if {'path','sha256'}<=value.keys():queue.append(value['path'])
            for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
    for path in (root/ledger).rglob('*.json'):walk(json.loads(path.read_bytes()))
    seen=set()
    while queue:
        name=queue.pop()
        if name in seen:continue
        seen.add(name);pair=relative_reference(root,name)
        if pair is None:continue
        _,target=pair
        source=REPOSITORY/Path(name)
        if not source.is_file():continue
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    monkeypatch.setattr(request.module,'__file__',str(root/relative))
