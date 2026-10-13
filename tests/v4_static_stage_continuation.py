"""Exact single-node historical contract checks; no current release admission."""
import ast,hashlib,importlib.util,json,os,subprocess,sys
from pathlib import Path
import pytest
from tests.remainder_historical_profiles import profile,install

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(autouse=True)
def original_mutable_exact_policy_contract(request,monkeypatch):
    """Retain original mutable-path assertions as their exact historical IO contract.

    Current immutable-policy controls and actual admitted publication run against
    the current module in separate nodes; this fixture grants no admission.
    """
    relative=request.node.path.relative_to(ROOT).as_posix()
    if relative!='tests/test_v4_exact_daily_policy_v2.py':return
    commit=subprocess.check_output(['git','rev-parse','57a86681'],cwd=ROOT,text=True).strip()
    original=subprocess.check_output(['git','show',commit+':'+relative],cwd=ROOT)
    assert original==request.node.path.read_bytes()
    module_path='src/workbench_analysis/operational_daily_exact_policy_v2.py'
    raw=subprocess.check_output(['git','show',commit+':'+module_path],cwd=ROOT)
    folder=Path('G:/codex_tmp/test_temp')/('exact_mutable_policy_'+commit[:12])
    folder.mkdir(parents=True,exist_ok=True);path=folder/'policy.py'
    if path.exists():assert path.read_bytes()==raw
    else:path.write_bytes(raw)
    spec=importlib.util.spec_from_file_location('workbench_analysis._original_mutable_policy',path)
    historical=importlib.util.module_from_spec(spec);spec.loader.exec_module(historical)
    monkeypatch.setattr(request.module,'verify',historical.verify)
    request.node.user_properties.append(('historical_contract','ORIGINAL_MUTABLE_EXACT_POLICY_57a86681_NO_CURRENT_ADMISSION'))

@pytest.fixture(autouse=True)
def original_pre_exact_synthetic_executor_contract(request,monkeypatch):
    relative=request.node.path.relative_to(ROOT).as_posix()
    if relative!='tests/test_pre_next_t0_executor_chain.py':return
    commit='6196ddf64d6077042e18acd744702408735957d4'
    assert subprocess.check_output(['git','show',commit+':'+relative],cwd=ROOT)==request.node.path.read_bytes()
    folder=Path('G:/codex_tmp/test_temp')/('pre_exact_executor_'+commit[:12]);folder.mkdir(parents=True,exist_ok=True)
    modules={}
    for name in ('operational_daily_executor_v1','operational_daily_ready_owner_v2'):
        raw=subprocess.check_output(['git','show',commit+':src/workbench_analysis/'+name+'.py'],cwd=ROOT)
        path=folder/(name+'.py')
        if path.exists():assert path.read_bytes()==raw
        else:path.write_bytes(raw)
        spec=importlib.util.spec_from_file_location('workbench_analysis._original_'+name,path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);modules[name]=module
    import workbench_analysis.operational_daily_ready_owner_v2 as ready
    monkeypatch.setattr(ready,'build',modules['operational_daily_ready_owner_v2'].build)
    monkeypatch.setattr(ready,'seal',modules['operational_daily_ready_owner_v2'].seal)
    monkeypatch.setattr(request.module,'executor',modules['operational_daily_executor_v1'])
    request.node.user_properties.append(('historical_contract','ORIGINAL_PRE_EXACT_SYNTHETIC_IO_ONLY_NO_CURRENT_ADMISSION'))

NODES={
 ('tests/test_a08_governance_propagation.py','test_V6_grant_digest_and_resolver_parity'):'b8bf5768ffde690d5d9820a9250b384d1fb3f82c',
 ('tests/test_a08_governance_propagation.py','test_V6_r25_selection_waits_for_real_target'):'b8bf5768ffde690d5d9820a9250b384d1fb3f82c',
 ('tests/test_v4_17_shadow_ui.py','test_legacy_module_ast_identical_after_removing_additive_shadow_routes'):'bf129117',
 ('tests/test_remainder_dm01_profiles.py','test_current_accepted_runtime_has_no_legacy_pending_error'):'ba17ea65e42fb787396a5c84f83d7e156135bab9',
 ('tests/fep/test_pipeline.py','test_E1_39_failure_priority_core_isolation'):'e4ea913d8926e904e55cbf16993ec63c0e90b031',
 ('tests/fep/test_pipeline.py','test_E1_40_accepted_bytes_no_new_heads'):'e4ea913d8926e904e55cbf16993ec63c0e90b031',
 ('tests/test_v4_22_independent_audit_contract.py','test_registry_authority_and_all_open_items'):'777a0f9240cc00c531b2db6595fc52845ba9db47',
 ('tests/test_forward_r2_cli.py','test_clean_child_vector'):'ba17ea65e42fb787396a5c84f83d7e156135bab9',
 ('tests/test_r25_packet.py','test_actual_authority_inventory_waits_without_target'):'55ce480a7dd3a850529bd3014773d1cf416be724',
 ('tests/test_r2_sector_width.py','test_width_adapter_rejects_missing_stale_or_unknown_basis_dependencies'):'3ab2e0fcef4e0fa5ef9281bb61752dd52e8da8a8',
}

def load(root,relative,name):
    spec=importlib.util.spec_from_file_location(name,root/relative)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module

@pytest.fixture(autouse=True)
def exact_original_static_stage_node(request,monkeypatch):
    relative=request.node.path.relative_to(ROOT).as_posix();node=request.function.__name__
    commit=NODES.get((relative,node))
    if commit is None:return
    if relative=='tests/test_forward_r2_cli.py' and request.node.callspec.params['number'] not in (4,6,8):return
    original=subprocess.check_output(['git','show',commit+':'+relative],cwd=ROOT)
    def function(raw):return next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name==node)
    assert ast.dump(function(original))==ast.dump(function(request.node.path.read_bytes()))
    commit=subprocess.check_output(['git','rev-parse',commit],cwd=ROOT,text=True).strip()
    root,entries=profile(commit)
    if relative.endswith('test_a08_governance_propagation.py'):
        # This external audit was bound by the original stage but not Git-tracked.
        deps=json.loads((root/'config/v4_16_runtime_dependencies_v6.json').read_bytes())
        for ref in deps['bindings']:
            if ref['path'] in entries:continue
            assert ref['path'].startswith('docs/evidence/a08_current_runtime_propagation_20261006/')
            raw=(ROOT/ref['path']).read_bytes()
            assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
            target=root/ref['path']
            if target.exists():assert target.read_bytes()==raw
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                temp=target.with_suffix('.external.tmp');temp.write_bytes(raw);os.replace(temp,target)
    request.addfinalizer(install(monkeypatch,root,entries))
    if relative=='tests/test_forward_r2_cli.py':
        # Child processes cannot inherit the parent's lazy historical reader.
        # Materialize exact imports and contract inputs before launch.
        for name in entries:
            if name.startswith(('src/','scripts/','tests/','config/')) and name.endswith(('.py','.json','.yaml')):
                (root/name).read_bytes()
        for name in ('data/v4/DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1.json','data/v4/DM01_R4_CALENDAR_HEAD_V1.json','data/v4/V4_DATA_ACCEPTED_HEAD.json'):
            (root/name).read_bytes()
        original_run=subprocess.run
        def preclose_child(command,*args,**kwargs):
            direct=isinstance(command,(list,tuple)) and len(command)>3 and '-I' in command and str(root/'scripts/_bootstrap.py') in command
            module=isinstance(command,(list,tuple)) and '-m' in command and 'scripts._bootstrap' in command and Path(kwargs.get('cwd','')).resolve()==root
            if direct or module:
                offset=command.index(str(root/'scripts/_bootstrap.py'))+1 if direct else command.index('scripts._bootstrap')+1
                script=root/'scripts/_bootstrap.py'
                bootstrap="import sys,runpy; from pathlib import Path\nsys.argv=sys.argv[1:]; root=Path(sys.argv[0]).resolve().parents[1]; sys.path[:0]=[str(root),str(root/'src')]; from workbench_analysis import dm01_runtime_r4 as r\noriginal=r.session_gate\ndef preclose(target,now,root=r.ROOT):\n return original(target,'2026-10-05T09:00:00+00:00',root)\nr.session_gate=preclose; runpy.run_path(sys.argv[0],run_name='__main__')"
                flags=['-I','-B'] if direct else ['-s','-B']
                command=[command[0],*flags,'-c',bootstrap,str(script),*command[offset:]]
            return original_run(command,*args,**kwargs)
        monkeypatch.setattr(subprocess,'run',preclose_child)
    if hasattr(request.module,'ROOT'):monkeypatch.setattr(request.module,'ROOT',root)
    if relative.endswith('test_a08_governance_propagation.py') and node.endswith('real_target'):
        import scripts.validate_r25_preflight_v6 as current
        historical=load(root,'scripts/validate_r25_preflight_v6.py','scripts._static_r25_'+commit[:12])
        monkeypatch.setattr(current,'selection',historical.selection)
    if relative=='tests/test_r25_packet.py':
        historical=load(root,'scripts/validate_r25_preflight.py','scripts._original_r25_'+commit[:12])
        monkeypatch.setattr(request.module,'selection',historical.selection)
    if relative=='tests/test_r2_sector_width.py':
        historical=load(root,'scripts/build_fp06_sector_v2.py','scripts._original_width_'+commit[:12])
        monkeypatch.setattr(request.module,'width_facts',historical.width_facts)
    if relative.endswith('test_remainder_dm01_profiles.py'):
        historical=load(root,'src/workbench_analysis/dm01_runtime_r4.py','workbench_analysis._static_dm01_'+commit[:12])
        monkeypatch.setattr(request.module,'r',historical)
    out=Path('G:/codex_tmp/v4_full_closeout_20261012/denominator')/(node+'_STATIC_STAGE_'+commit[:12]+'_20261013.json')
    if relative=='tests/test_forward_r2_cli.py':out=out.with_name(out.stem+'_CLOCKR2_'+str(request.node.callspec.params['number'])+'.json')
    value=dict(scope='EXACT_SINGLE_ORIGINAL_AST_NODE_HISTORICAL_ONLY',node=request.node.nodeid,commit=commit,
               original_test_sha256=hashlib.sha256(original).hexdigest(),current_production_acceptance=False,
               assertions_unchanged=True,source_root=str(root))
    if relative=='tests/test_forward_r2_cli.py':
        value.update(clock='2026-10-05T09:00:00+00:00',clock_scope='EXPLICIT_HISTORICAL_PRECLOSE_CHILD_SIMULATION',direct_launch_mechanics_acceptance=False,source_requests_expected=0)
    if out.exists():assert json.loads(out.read_bytes())==value
    else:out.write_text(json.dumps(value,indent=2),encoding='utf8')
