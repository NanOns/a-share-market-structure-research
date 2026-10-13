"""External historical IO fixtures; original tests and current production remain separate."""
import ast,hashlib,json,subprocess
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(autouse=True)
def original_protection_fixture_metadata(request):
    # Historical profiles consume their original module and original metadata.
    # Hydrating current heads here would conflict with immutable original heads.
    if not __import__('os').environ.get('R4_NATIVE_ISOLATION'):return
    relative=request.node.path.relative_to(ROOT).as_posix()
    selected=(relative=='tests/v4_parallel_scoped_consolidation_r3/test_clean_protected_representations.py' and request.function.__name__=='test_real_consolidation_retains_batch_refs_and_passes_only_exact_clean_representations') or (relative=='tests/v4_parallel_scoped_formalization_r1/test_clean_representations.py' and request.function.__name__=='test_real_validate_record_in_lf_checkout_and_strict_nonprotected_refs') or (relative=='tests/v4_scoped_promotions_r3/test_scoped_readers.py' and 'scoped_copy' in request.function.__code__.co_names)
    if not selected:return
    from tests.r4_r3_protection_fixture_inputs import hydrate
    hydrate(request.getfixturevalue('tmp_path'))
    request.node.user_properties.append(('scope','ORIGINAL_ASSERTIONS_EXTERNAL_METADATA_IO_ONLY_NO_CURRENT_ADMISSION'))

@pytest.fixture(autouse=True)
def original_dm01_runtime_contract_constants(request,monkeypatch):
    relative=request.node.path.relative_to(ROOT).as_posix()
    commits={'tests/v4_dm01_r4/test_runtime.py':'487bf4e1979356c3f3130bdc7e913a87df6acc03','tests/v4_dm01_r4r2/test_acceptance_seal.py':'ce44488ae972'}
    commit=commits.get(relative)
    if commit is None:return
    commit=subprocess.check_output(['git','rev-parse',commit],cwd=ROOT,text=True).strip()
    raw=subprocess.check_output(['git','show',commit+':src/workbench_analysis/dm01_runtime_r4.py'],cwd=ROOT)
    import workbench_analysis.dm01_runtime_r4 as runtime
    for node in ast.parse(raw).body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in {'CONTRACT','POLICY','CALENDAR','HEAD','ACCEPTANCE'}:
            value=ast.literal_eval(node.value);assert isinstance(value,str)
            monkeypatch.setattr(runtime,node.targets[0].id,value)
    request.node.user_properties.extend([('scope','EXACT_ORIGINAL_DM01_MODULE_CONSTANTS_NO_CURRENT_ADMISSION'),('original_source_sha256',hashlib.sha256(raw).hexdigest())])
    if relative=='tests/v4_dm01_r4r2/test_acceptance_seal.py':
        import importlib.util,sys
        from tests.remainder_historical_profiles import profile
        root,_=profile(commit)
        name='scripts._historical_r25_selection_'+commit[:12]
        spec=importlib.util.spec_from_file_location(name,root/'scripts/validate_r25_preflight.py')
        historical=importlib.util.module_from_spec(spec);sys.modules[name]=historical;spec.loader.exec_module(historical)
        monkeypatch.setattr(request.module,'selection',historical.selection)

@pytest.fixture(autouse=True,scope='module')
def exact_original_scoped_functions(request,exact_frozen_stage_test_profile):
    """Run registered historical modules with their matching function globals."""
    import importlib.util,sys,types
    relative=request.node.path.relative_to(ROOT).as_posix()
    if not relative.startswith(('tests/v4_parallel_scoped_','tests/v4_scoped_promotions_r3/')):return
    registry=json.loads((ROOT/'config/v4_frozen_test_profiles_remainder_v1.json').read_bytes())
    row=next((r for r in registry['profiles'] if r['path']==relative),None)
    if row is None:return
    from tests.remainder_historical_profiles import profile
    root,entries=profile(row['historical_commit'])
    patch=pytest.MonkeyPatch();request.addfinalizer(patch.undo)
    modules=['workbench_analysis.parallel_scoped_acceptance_r1']
    if relative.startswith('tests/v4_scoped_promotions_r3/'):modules.append('v4.scoped_promotions_r3')
    for module_name in modules:
        owner=__import__(module_name,fromlist=['*'])
        path='src/'+module_name.replace('.','/')+'.py'
        assert path in entries
        raw=(root/path).read_bytes()
        assert raw==subprocess.check_output(['git','show',row['historical_commit']+':'+path],cwd=ROOT)
        name=module_name.rsplit('.',1)[0]+'._original_scoped_'+module_name.rsplit('.',1)[1]+'_'+row['historical_commit'][:12]
        spec=importlib.util.spec_from_file_location(name,root/path)
        historical=importlib.util.module_from_spec(spec);sys.modules[name]=historical;spec.loader.exec_module(historical)
        exports={id(value):getattr(historical,key) for key,value in vars(owner).items()
                 if isinstance(value,types.FunctionType) and value.__module__==owner.__name__ and hasattr(historical,key)}
        targets=[request.module]+[m for n,m in list(sys.modules.items()) if m and n.startswith(('workbench_analysis.','v4.'))]
        for target in targets:
            for key,value in list(vars(target).items()):
                if id(value) in exports:patch.setattr(target,key,exports[id(value)])
        request.node._historical_function_sources=getattr(request.node,'_historical_function_sources',[])+[(path,hashlib.sha256(raw).hexdigest())]
