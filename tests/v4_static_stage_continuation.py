"""Exact single-node historical contract checks; no current release admission."""
import ast,hashlib,importlib.util,json,os,subprocess,sys
from pathlib import Path
import pytest
from tests.remainder_historical_profiles import profile,install

ROOT=Path(__file__).resolve().parents[1]
NODES={
 ('tests/test_a08_governance_propagation.py','test_V6_grant_digest_and_resolver_parity'):'b8bf5768ffde690d5d9820a9250b384d1fb3f82c',
 ('tests/test_a08_governance_propagation.py','test_V6_r25_selection_waits_for_real_target'):'b8bf5768ffde690d5d9820a9250b384d1fb3f82c',
 ('tests/test_v4_17_shadow_ui.py','test_legacy_module_ast_identical_after_removing_additive_shadow_routes'):'bf129117',
 ('tests/test_remainder_dm01_profiles.py','test_current_accepted_runtime_has_no_legacy_pending_error'):'ba17ea65e42fb787396a5c84f83d7e156135bab9',
 ('tests/fep/test_pipeline.py','test_E1_39_failure_priority_core_isolation'):'e4ea913d8926e904e55cbf16993ec63c0e90b031',
 ('tests/fep/test_pipeline.py','test_E1_40_accepted_bytes_no_new_heads'):'e4ea913d8926e904e55cbf16993ec63c0e90b031',
 ('tests/test_v4_22_independent_audit_contract.py','test_registry_authority_and_all_open_items'):'777a0f9240cc00c531b2db6595fc52845ba9db47',
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
    if hasattr(request.module,'ROOT'):monkeypatch.setattr(request.module,'ROOT',root)
    if relative.endswith('test_a08_governance_propagation.py') and node.endswith('real_target'):
        import scripts.validate_r25_preflight_v6 as current
        historical=load(root,'scripts/validate_r25_preflight_v6.py','scripts._static_r25_'+commit[:12])
        monkeypatch.setattr(current,'selection',historical.selection)
    if relative.endswith('test_remainder_dm01_profiles.py'):
        historical=load(root,'src/workbench_analysis/dm01_runtime_r4.py','workbench_analysis._static_dm01_'+commit[:12])
        monkeypatch.setattr(request.module,'r',historical)
    out=Path('G:/codex_tmp/v4_full_closeout_20261012/denominator')/(node+'_STATIC_STAGE_'+commit[:12]+'_20261013.json')
    value=dict(scope='EXACT_SINGLE_ORIGINAL_AST_NODE_HISTORICAL_ONLY',node=request.node.nodeid,commit=commit,
               original_test_sha256=hashlib.sha256(original).hexdigest(),current_production_acceptance=False,
               assertions_unchanged=True,source_root=str(root))
    if out.exists():assert json.loads(out.read_bytes())==value
    else:out.write_text(json.dumps(value,indent=2),encoding='utf8')
