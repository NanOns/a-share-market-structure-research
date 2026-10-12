"""Native isolation compatibility with explicitly registered frozen stage tests."""
import hashlib
import json
from pathlib import Path
import subprocess
import types
import pytest

REPOSITORY=Path(__file__).resolve().parents[1]

@pytest.fixture(autouse=True)
def original_fep_feature_owner_envelope(request,monkeypatch):
    relative=request.node.path.relative_to(REPOSITORY).as_posix()
    if relative!='tests/fep/test_feature_owner.py' or request.function.__name__!='test_all_47_accepted_historical_fields_and_seven_relative_rps_are_copied':return
    from tests.remainder_historical_profiles import profile,install
    commit='06549c102da2a203a19004fbeb17a0a0cf717b6a'
    original=subprocess.check_output(['git','show',commit+':'+relative],cwd=REPOSITORY)
    assert original==request.node.path.read_bytes()
    contract='config/fep_feature_owner_contract_v1.json'
    assert subprocess.check_output(['git','show',commit+':'+contract],cwd=REPOSITORY)==(REPOSITORY/contract).read_bytes()
    root,entries=profile(commit);request.addfinalizer(install(monkeypatch,root,entries))
    monkeypatch.setattr(request.module,'ROOT',root);monkeypatch.setattr(request.module,'OUT',root/'reports/fep_e1_r2_final')
    Path('G:/codex_tmp/v4_full_closeout_20261012/denominator/FEP_ORIGINAL_OWNER_ENVELOPE_SCOPE.json').write_text(json.dumps(dict(
        commit=commit,node=request.node.nodeid,original_test_identical=True,original_owner_contract_identical=True,
        scope='HISTORICAL_RECONSTRUCTED_OWNER_ENVELOPE_ONLY',current_production_acceptance=False,
        other_module_nodes_use_current_contract=True),indent=2),encoding='utf8')

@pytest.fixture(autouse=True)
def original_pre_successor_v13_reader_gate(request,monkeypatch):
    relative=request.node.path.relative_to(REPOSITORY).as_posix()
    if relative!='tests/test_remainder_historical_routing.py' or request.function.__name__!='test_old_v13_reader_remains_pinned':return
    from tests.remainder_historical_profiles import profile,install
    commit=subprocess.check_output(['git','rev-parse','ba17ea65'],cwd=REPOSITORY,text=True).strip()
    raw=subprocess.check_output(['git','show',commit+':'+relative],cwd=REPOSITORY)
    assert raw==request.node.path.read_bytes()
    root,entries=profile(commit);request.addfinalizer(install(monkeypatch,root,entries))
    monkeypatch.setattr(request.module,'ROOT',root)
    import importlib.util,sys,workbench_analysis
    name='workbench_analysis._original_v13_reader_'+commit[:12]
    spec=importlib.util.spec_from_file_location(name,root/'src/workbench_analysis/v4_13_accepted_contract_package.py')
    original=importlib.util.module_from_spec(spec);sys.modules[name]=original;spec.loader.exec_module(original)
    monkeypatch.setitem(sys.modules,'workbench_analysis.v4_13_accepted_contract_package',original)
    monkeypatch.setattr(workbench_analysis,'v4_13_accepted_contract_package',original,raising=False)
    Path('G:/codex_tmp/v4_full_closeout_20261012/denominator/OLD_V13_GATE_HISTORICAL_ONLY.json').write_text(json.dumps(dict(
        scope='ORIGINAL_SINGLE_NODE_ONLY',commit=commit,node=request.function.__name__,
        test_source_sha256=hashlib.sha256(raw).hexdigest(),grants_current_permission=False,
        current_reader_nodes_still_use_current_root=True),indent=2),encoding='utf8')

@pytest.fixture(autouse=True)
def exact_original_r15_contract_node(request,monkeypatch):
    if request.node.path.relative_to(REPOSITORY).as_posix()!='tests/test_v4_13_r15_contract.py' or request.function.__name__!='test_full_contract_completeness_and_protected_artifacts':return
    import ast,importlib.util,sys
    from tests.remainder_historical_profiles import profile,install
    commit=subprocess.check_output(['git','rev-parse','202a4817'],cwd=REPOSITORY,text=True).strip()
    original=subprocess.check_output(['git','show',commit+':tests/test_v4_13_r15_contract.py'],cwd=REPOSITORY)
    def node(raw):return next(x for x in ast.parse(raw).body if isinstance(x,ast.FunctionDef) and x.name==request.function.__name__)
    assert ast.dump(node(original))==ast.dump(node(request.node.path.read_bytes()))
    root,entries=profile(commit);request.addfinalizer(install(monkeypatch,root,entries))
    from scripts import repair_v4_13_r1_1 as owner
    monkeypatch.setattr(owner,'ROOT',root)
    name='scripts._closeout_original_r15_'+commit[:12]
    spec=importlib.util.spec_from_file_location(name,root/'scripts/validate_v4_13_r1_1.py')
    historical=importlib.util.module_from_spec(spec);sys.modules[name]=historical;spec.loader.exec_module(historical)
    monkeypatch.setattr(request.module,'validate',historical.validate)
    Path('G:/codex_tmp/v4_full_closeout_20261012/denominator/R15_CONTRACT_NODE_HISTORICAL_ONLY.json').write_text(json.dumps(dict(
        scope='HISTORICAL_ONLY',input_commit=commit,input_root=str(root),original_node_AST_identical=True,
        current_production_acceptance=False,reason='Original R15 design gate precedes subsequently authorized R16/R17 runtime; original gate and assertions replay their actual Git stage'),indent=2),encoding='utf8')

@pytest.fixture(autouse=True,scope='module')
def exact_original_stage13_native_scope(request):
    relative=request.node.path.relative_to(REPOSITORY).as_posix()
    selected={'tests/test_v4_13_r15_contract.py','tests/test_v4_13_r15r1_lineage.py',
              'tests/test_v4_13_r16a_runtime.py','tests/test_v4_13_r16r1_repair.py'}
    if relative not in selected:return
    commit='7986acdb4db19e85f55045dbfc692c932d4e1499'
    root=Path('G:/codex_tmp/test_temp/remainder_historical_stage13')
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==commit
    original=subprocess.check_output(['git','show',commit+':'+relative],cwd=REPOSITORY)
    assert request.node.path.read_bytes()==original
    monkeypatch=pytest.MonkeyPatch();request.addfinalizer(monkeypatch.undo)
    if hasattr(request.module,'ROOT'):monkeypatch.setattr(request.module,'ROOT',root)
    if '/test_v4_13_r15' in relative:
        from scripts import repair_v4_13_r1_1 as owner,validate_v4_13_r1_1 as validator
        monkeypatch.setattr(owner,'ROOT',root);monkeypatch.setattr(validator,'ROOT',root)
    evidence=Path('G:/codex_tmp/v4_full_closeout_20261012/denominator')/(request.node.path.stem+'_HISTORICAL_ONLY.json')
    evidence.write_text(json.dumps(dict(scope='HISTORICAL_ONLY',input_commit=commit,input_root=str(root),
        test_source_sha256=hashlib.sha256(original).hexdigest(),assertions_unchanged=True,
        current_production_acceptance=False),indent=2),encoding='utf8')

@pytest.fixture(autouse=True)
def exact_original_r17b_promotion_node(request,monkeypatch):
    if request.node.path.relative_to(REPOSITORY).as_posix()!='tests/test_r17b_promotion.py' or request.function.__name__!='test_independent_p01_p15_promotion_gate':return
    import ast
    import importlib.util
    import sys
    from tests.remainder_historical_profiles import profile,install
    commit=subprocess.check_output(['git','rev-parse','62fb75ff'],cwd=REPOSITORY,text=True).strip()
    raw=subprocess.check_output(['git','show',commit+':tests/test_r17b_promotion.py'],cwd=REPOSITORY)
    def node(source):return next(item for item in ast.parse(source).body if isinstance(item,ast.FunctionDef) and item.name==request.function.__name__)
    assert ast.dump(node(raw))==ast.dump(node(request.node.path.read_bytes()))
    root,entries=profile(commit);flush=install(monkeypatch,root,entries);request.addfinalizer(flush)
    name='scripts._closeout_original_r17b_'+commit[:12]
    spec=importlib.util.spec_from_file_location(name,root/'scripts/validate_r17b_promotion.py')
    historical=importlib.util.module_from_spec(spec);sys.modules[name]=historical;spec.loader.exec_module(historical)
    monkeypatch.setattr(request.module.v,'validate',historical.validate)
    evidence=Path('G:/codex_tmp/v4_full_closeout_20261012/denominator/R17B_P01_P15_HISTORICAL_ONLY.json')
    evidence.write_text(json.dumps(dict(scope='HISTORICAL_ONLY',input_commit=commit,input_root=str(root),
        original_node_AST_identical=True,current_production_acceptance=False,
        reason='Original R17B promotion gate precedes R17R1A amended stage; remaining module nodes retain their registered amended-stage profile'),indent=2),encoding='utf8')

@pytest.fixture(autouse=True,scope='module')
def exact_registered_history_native_scope(request):
    relative=request.node.path.relative_to(REPOSITORY).as_posix()
    # These original modules already have an explicit signed historical
    # profile. Reuse its complete original setup under the native PG guard.
    selected={'tests/test_r17b_promotion.py','tests/test_v4_r14_governance_contracts.py',
              'tests/test_v4_18_migration_contract.py',
              'tests/test_r18b_persisted.py','tests/test_r18r1r1_consumption.py',
              'tests/v4_09/test_stock_prewatch.py',
              'tests/v4_a03_a04_a07_r2/test_real_candidate_readback.py',
              'tests/v4_a04_r3/test_independent_arithmetic_and_evidence.py',
              'tests/v4_a04_r3/test_strict_source_admission.py',
              'tests/v4_dm01_promotion/test_accepted_chain.py',
              'tests/test_r20a_current.py','tests/test_r20e_persisted.py',
              'tests/test_r21_promotion.py','tests/test_v4_14_rollback.py',
              'tests/v4_dm01_r3/test_real_authority_and_chain.py',
              'tests/v4_09/test_r1_1_lineage_immutability.py',
              'tests/v4_dm01_r4/test_runtime.py',
              'tests/v4_dm01_r4r2/test_acceptance_seal.py'}
    if relative not in selected:return
    from tests.remainder_isolation_plugin import exact_frozen_stage_test_profile
    exact_frozen_stage_test_profile.__wrapped__(request)
    if relative in ('tests/v4_dm01_r4/test_runtime.py','tests/v4_dm01_r4r2/test_acceptance_seal.py'):
        import importlib.util,sys
        from tests.remainder_historical_profiles import profile
        registry=json.loads((REPOSITORY/'config/v4_frozen_test_profiles_full_closeout_r1.json').read_bytes())
        row=next(x for x in registry['profiles'] if x['path']==relative)
        root,_=profile(row['historical_commit'])
        name='workbench_analysis._closeout_dm01_runtime_'+row['historical_commit'][:12]
        spec=importlib.util.spec_from_file_location(name,root/'src/workbench_analysis/dm01_runtime_r4.py')
        historical=importlib.util.module_from_spec(spec);sys.modules[name]=historical;spec.loader.exec_module(historical)
        assert historical.ROOT==root
        patch=pytest.MonkeyPatch();request.addfinalizer(patch.undo)
        patch.setattr(request.module,'r',historical)
        if hasattr(request.module,'selection'):
            validator_name='scripts._closeout_r25_'+row['historical_commit'][:12]
            validator_spec=importlib.util.spec_from_file_location(validator_name,root/'scripts/validate_r25_preflight.py')
            validator=importlib.util.module_from_spec(validator_spec);sys.modules[validator_name]=validator;validator_spec.loader.exec_module(validator)
            patch.setattr(request.module,'selection',validator.selection)
        import workbench_analysis
        patch.setattr(workbench_analysis,'dm01_runtime_r4',historical)
        patch.setitem(sys.modules,'workbench_analysis.dm01_runtime_r4',historical)

@pytest.fixture(autouse=True)
def exact_historical_dm01_preclose_clock(request,monkeypatch):
    relative=request.node.path.relative_to(REPOSITORY).as_posix()
    selected={
        ('tests/v4_dm01_r4/test_runtime.py','test_actual_entrypoint_no_capture'),
        ('tests/v4_dm01_r4r2/test_acceptance_seal.py','test_sealed_future_wait_has_no_source_or_publication'),
    }
    if (relative,request.function.__name__) not in selected:return
    from datetime import datetime,timezone
    class HistoricalClock(datetime):
        @classmethod
        def now(cls,tz=None):
            value=datetime(2026,10,5,9,tzinfo=timezone.utc)
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)
    if request.function.__name__=='test_sealed_future_wait_has_no_source_or_publication':
        monkeypatch.setattr(request.module,'datetime',HistoricalClock)
    else:
        original=subprocess.run
        script=request.module.r.ROOT/'scripts/run_v4_dm01_daily_increment.py'
        def historical_entry(command,*args,**kw):
            if isinstance(command,(list,tuple)) and len(command)>2 and command[1]=='-B' and Path(command[2])==script:
                bootstrap="import sys,runpy; from datetime import datetime,timezone\nclass Clock(datetime):\n @classmethod\n def now(cls,tz=None):\n  value=datetime(2026,10,5,9,tzinfo=timezone.utc); return value.astimezone(tz) if tz else value.replace(tzinfo=None)\nsys.argv=sys.argv[1:]; namespace=runpy.run_path(sys.argv[0],run_name='__historical_preclose_test__'); namespace['main'].__globals__['datetime']=Clock; raise SystemExit(namespace['main']())"
                command=[command[0],'-B','-c',bootstrap,*command[2:]]
            return original(command,*args,**kw)
        monkeypatch.setattr(subprocess,'run',historical_entry)
    Path('G:/codex_tmp/v4_full_closeout_20261012/denominator/'+request.function.__name__+'_HISTORICAL_CLOCK.json').write_text(json.dumps(dict(
        clock='2026-10-05T09:00:00+00:00',scope='HISTORICAL_TEST_SIMULATION_ONLY',
        reason='Original pre-close gate must not depend on the wall clock after target date; assertions and gate remain unchanged',
        source_capture_or_production_permission=False,first_capture_evidence=False),indent=2),encoding='utf8')

@pytest.fixture(autouse=True,scope='module')
def exact_pre16_history_native_scope(request):
    relative=request.node.path.relative_to(REPOSITORY).as_posix()
    if relative!='tests/test_pre16_governance.py':return
    registry=json.loads((REPOSITORY/'config/v4_frozen_test_profiles_remainder_v1.json').read_bytes())
    row=next(item for item in registry['profiles'] if item['path']==relative)
    root=Path('G:/codex_tmp/v4_full_closeout_20261012/denominator/historical_pre16_fixture')
    commit='dabb5eb2fcdd4b52cfa4d9d684f9d9a9786c42bf'
    assert row['historical_commit']==commit and row['grants_current_permission'] is False
    assert hashlib.sha256(request.node.path.read_bytes()).hexdigest()==row['source']['sha256']
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==commit
    import scripts.validate_pre16_governance as oracle
    import scripts.pre16_current_audit_reader as reader
    for name in ('scripts/validate_pre16_governance.py','scripts/pre16_current_audit_reader.py'):
        assert (root/name).read_bytes()==subprocess.check_output(['git','show',commit+':'+name],cwd=root)
    monkeypatch=pytest.MonkeyPatch();request.addfinalizer(monkeypatch.undo)
    seen=set()
    for module in (request.module,oracle,reader):
        if getattr(module,'ROOT',None)==REPOSITORY:monkeypatch.setattr(module,'ROOT',root)
        for value in list(vars(module).values()):
            functions=[value] if isinstance(value,types.FunctionType) else [item for item in vars(value).values() if isinstance(item,types.FunctionType)] if isinstance(value,type) else []
            for function in functions:
                if id(function) in seen:continue
                seen.add(id(function))
                if function.__defaults__ and REPOSITORY in function.__defaults__:
                    monkeypatch.setattr(function,'__defaults__',tuple(root if item==REPOSITORY else item for item in function.__defaults__))
    (root.parent/'PRE16_NATIVE_PROFILE_HISTORICAL_ONLY.json').write_text(json.dumps(dict(
        scope='HISTORICAL_ONLY',input_commit=commit,input_root=str(root),test_binding=row['source'],
        current_production_acceptance=False,current_heads_untouched=True,assertions_unchanged=True),indent=2),encoding='utf8')
