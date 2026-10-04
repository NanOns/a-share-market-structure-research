"""R4 actual nine kernels on explicit historical engineering inputs; never real PIT."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from workbench_analysis import dm01_runtime_r4 as r
from tests.v4_dm01.a01_fixture_inputs import make_inputs, save, rehash


@pytest.fixture
def env(tmp_path):
    e = make_inputs(tmp_path)
    # Copy exact external immutable inputs into the isolated fixture root.
    for collection in (e['freeze']['inputs'], e['freeze']['source_families']):
        for key, binding in list(collection.items()):
            source = Path(binding['path'])
            if not source.is_absolute(): source = r.ROOT / source
            if not source.is_relative_to(tmp_path):
                target = tmp_path / 'copied' / (key + source.suffix)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
                collection[key] = dict(binding, path=str(target))
            else:
                collection[key] = dict(binding,path=str(source))
    for binding in [e['identity']['binding'],e['calendar']['binding'],*e['parent']['components'].values()]:
        if not Path(binding['path']).is_absolute():binding['path']=str(r.ROOT/binding['path'])
    head = deepcopy(e['parent']['head']); head['contract_id']='V4_DATA_ACCEPTED_HEAD_V2'
    head['accepted_chain']=save(tmp_path,'fixture_chain.json',{'fixture_scope':'ENGINEERING_INPUT_ONLY'})
    e['parent']['head']=head; e['parent']['binding']=save(tmp_path,'fixture_v2_head.json',head)
    e['parent']['binding']['path']=str(tmp_path/'fixture_v2_head.json')
    f=e['freeze']; f.update(parent_data_head_digest=e['parent']['binding']['sha256'],
        knowledge_lineage='PIT_OBSERVED',AS_RECORDED=True,engineering_simulation=True)
    f['availability_evidence']={family:dict(binding=f['source_families'][native],
        target_trade_date=f['trade_date'],provider_date=f['trade_date'],
        captured_at='2026-09-28T08:00:00+00:00',received_at='2026-09-28T08:01:00+00:00',
        system_available_at='2026-09-28T08:01:00+00:00')
        for family,native in [('TDX_FULL_PACKAGE','TDX_PAGE_CAPTURE'),('BAOSTOCK_DAILY_UPDATE','BAOSTOCK_DAILY_UPDATE')]}
    for p in json.loads((r.ROOT/r.CONTRACT).read_bytes())['protected_runtime_paths']:
        target=tmp_path/p; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(b'protected fixture\n')
    rehash(f)
    return e


def build(e, **kw):
    return r.build_candidate(parent=e['parent'],freeze=e['freeze'],cal=e['calendar'],identity=e['identity'],root=e['root'],**kw)


def test_actual_all_nine_and_identical_rerun(env):
    result=build(env); marker=r.read(env['root'],result['candidate'])
    assert set(marker['components'])==set(r.CAPABILITIES)
    assert r.read(env['root'],marker['cross_postcheck'])['status']=='PASS'
    assert marker['knowledge_lineage']=='CONTRACT_DESIGN_OR_ENGINEERING_SIMULATION'
    assert marker['real_forward_evidence'] is False
    assert build(env)['status']=='NOOP_IDENTICAL_CANDIDATE'
    assert marker['permissions']==r.PERMISSIONS


@pytest.mark.parametrize('case,mutate,reason',[
 ('DM01R4-05',lambda e:e['parent']['head'].update(contract_id='V4_DATA_ACCEPTED_HEAD_V1'),'V1_PARENT'),
 ('DM01R4-06',lambda e:e['freeze'].update(parent_data_head_digest='0'*64),'PARENT_DIGEST'),
 ('DM01R4-13',lambda e:e['freeze'].update(knowledge_lineage='RECONSTRUCTED'),'RECONSTRUCTED'),
 ('DM01R4-14',lambda e:e['freeze']['availability_evidence']['TDX_FULL_PACKAGE'].update(received_at='2026-09-29T08:00:00+00:00'),'FUTURE_OR_RECONSTRUCTED'),
 ('DM01R4-15',lambda e:e['freeze']['availability_evidence']['BAOSTOCK_DAILY_UPDATE'].update(provider_date='2026-09-29'),'TARGET_SOURCE_DATE'),
])
def test_bad_inputs_before_marker(env,case,mutate,reason):
    mutate(env); rehash(env['freeze'])
    with pytest.raises(ValueError,match=reason): build(env)
    assert not list(env['root'].rglob('PROMOTION_CANDIDATE.json'))


def test_missing_builder(env):
    builders=dict(r.BUILDERS);builders.pop('ISST')
    with pytest.raises(ValueError,match='BUILDERS_MISSING'):build(env,builders=builders)


def test_component_oracle_failure(env,monkeypatch):
    monkeypatch.setattr(r,'check_component',lambda *a:dict(status='FAIL'))
    with pytest.raises(ValueError,match='COMPONENT_POSTCHECK_FAIL'):build(env)
    assert not list(env['root'].rglob('PROMOTION_CANDIDATE.json'))


def test_cross_oracle_failure(env,monkeypatch):
    monkeypatch.setattr(r,'check_cross_components',lambda *a:dict(status='FAIL'))
    with pytest.raises(ValueError,match='CROSS_COMPONENT_POSTCHECK_FAILED'):build(env)
    assert not list(env['root'].rglob('PROMOTION_CANDIDATE.json'))


def test_revised_source_immutable_candidate(env):
    first=build(env);old=r.path(env['root'],first['candidate']).read_bytes()
    env['freeze']['revision_fixture']='explicit changed simulation';rehash(env['freeze'])
    second=build(env)
    assert first['candidate_id']!=second['candidate_id']
    assert r.path(env['root'],first['candidate']).read_bytes()==old


def test_component_tamper_rerun(env):
    result=build(env);marker=r.read(env['root'],result['candidate'])
    Path(marker['components']['RAW_DAILY']['artifact_path']).write_bytes(b'{}')
    with pytest.raises((ValueError,KeyError)):build(env)


def test_stage_change_rejected(env):
    build(env); p=next(iter(json.loads((r.ROOT/r.CONTRACT).read_bytes())['protected_runtime_paths']))
    (env['root']/p).write_bytes(b'changed')
    with pytest.raises(ValueError,match='PROTECTED_STATE_MOVED'):build(env)


def test_current_real_v2_parent_and_future_wait():
    parent=r.current_parent();assert parent['head']['accepted_trade_date']=='2026-09-30'
    before=r.sha(r.ROOT/r.HEAD)
    gate=r.session_gate('2026-10-08','2026-10-05T09:00:00+00:00')
    assert gate['status']=='WAIT_MARKET_CLOSE' and gate['source_requests']==0
    assert not gate['candidate_created'] and r.sha(r.ROOT/r.HEAD)==before
    with pytest.raises(ValueError):r.session_gate('2026-10-09','2026-10-05T09:00:00+00:00')
    with pytest.raises(ValueError,match='COVERAGE'):r.session_gate('2027-01-04','2026-10-05T09:00:00+00:00')
    with pytest.raises(ValueError,match='PENDING_DM01_R4_EXTERNAL_ACCEPTANCE'):
        r.session_gate('2026-10-08','2026-10-08T09:00:00+00:00')


def test_actual_entrypoint_no_capture():
    result=subprocess.run([sys.executable,'-B',str(r.ROOT/'scripts/run_v4_dm01_daily_increment.py'),
        '--target-date','2026-10-08'],cwd=r.ROOT,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    value=json.loads(result.stdout);assert value['status']=='WAIT_MARKET_CLOSE'
    assert value['source_requests']==0 and value['candidate_created'] is False


def test_simulation_cannot_promote_even_with_fake_envelope(env,monkeypatch):
    result=build(env)
    # Only this admission dependency is replaced to reach the independent promotion guard.
    monkeypatch.setattr(r,'accepted_envelope',lambda root:{})
    policy=env['root']/r.POLICY;policy.parent.mkdir(parents=True,exist_ok=True)
    policy.write_bytes((r.ROOT/r.POLICY).read_bytes())
    (env['root']/r.HEAD).write_bytes(Path(env['parent']['binding']['path']).read_bytes())
    monkeypatch.setattr(r,'current_parent',lambda root:env['parent'])
    monkeypatch.setattr(r,'calendar',lambda root:env['calendar'])
    with pytest.raises(ValueError,match='SIMULATED_OR_ESCALATED'):
        r.promote(result['candidate'],expected_parent_sha=env['parent']['binding']['sha256'],root=env['root'])


def promotion_fixture(env,monkeypatch):
    """Isolated state machine test; replaced PIT admissions are not PIT acceptance evidence."""
    result=build(env);marker=r.read(env['root'],result['candidate'])
    marker['knowledge_lineage']='PIT_OBSERVED'
    monkeypatch.setattr(r,'accepted_envelope',lambda root:{})
    monkeypatch.setattr(r,'validate_lineage',lambda *a,**kw:True)
    monkeypatch.setattr(r,'current_parent',lambda root:env['parent'])
    monkeypatch.setattr(r,'calendar',lambda root:env['calendar'])
    for p in (r.POLICY,r.CONTRACT):
        target=env['root']/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((r.ROOT/p).read_bytes())
    r.atomic(env['root'],env['root']/r.ACCEPTANCE,{'fixture_scope':'CONTRACT_DESIGN_OR_ENGINEERING_SIMULATION'})
    r.atomic(env['root'],env['root']/r.HEAD,env['parent']['head'])
    return marker


@pytest.mark.parametrize('case', ['DM01R4-07','DM01R4-09','DM01R4-10','DM01R4-17','DM01R4-19'])
def test_promotion_negative(env,monkeypatch,case):
    marker=promotion_fixture(env,monkeypatch)
    expected=r.sha(env['root']/r.HEAD)
    if case=='DM01R4-07':expected='0'*64
    if case=='DM01R4-09':
        policy=json.loads((env['root']/r.POLICY).read_bytes());policy['output_contract_id']='V4_DATA_ACCEPTED_HEAD_V1'
        r.atomic(env['root'],env['root']/r.POLICY,policy)
    if case=='DM01R4-10':marker['components']['RAW_DAILY']['artifact_sha256']='0'*64
    if case=='DM01R4-17':marker['components'].pop('ISST')
    if case=='DM01R4-19':marker['permissions']=dict(r.PERMISSIONS,shadow=True)
    binding=r.atomic(env['root'],env['root']/'promotion_fixture.json',marker)
    before=(env['root']/r.HEAD).read_bytes()
    with pytest.raises(ValueError):r.promote(binding,expected_parent_sha=expected,root=env['root'])
    assert (env['root']/r.HEAD).read_bytes()==before


def test_promotion_state_machine_no_stage_r25_or_counter_grant(env,monkeypatch):
    marker=promotion_fixture(env,monkeypatch)
    binding=r.atomic(env['root'],env['root']/'promotion_fixture.json',marker)
    result=r.promote(binding,expected_parent_sha=r.sha(env['root']/r.HEAD),root=env['root'])
    head=json.loads((env['root']/r.HEAD).read_bytes())
    assert result['status']=='PROMOTED_V2' and head['contract_id']=='V4_DATA_ACCEPTED_HEAD_V2'
    assert result['r25_grant'] is False and result['real_shadow_observations_increment']==0
    assert head['permissions']==r.PERMISSIONS
    assert all(r.sha(env['root']/p)==d for p,d in marker['protected_heads'].items())
    assert r.promote(binding,expected_parent_sha=marker['parent_data_head_digest'],root=env['root'])['status']=='NOOP_IDENTICAL_PROMOTION'


def test_calendar_unaccepted(tmp_path):
    p=tmp_path/r.CALENDAR;p.parent.mkdir(parents=True)
    p.write_text(json.dumps(dict(contract_id='DM01_R4_CALENDAR_HEAD_V1',status='UNACCEPTED')))
    with pytest.raises(ValueError,match='CALENDAR_HEAD_NOT_ACCEPTED'):r.calendar(tmp_path)


def test_forged_external_acceptance_rejected(tmp_path):
    for p in (r.CONTRACT,r.POLICY,r.CALENDAR):
        target=tmp_path/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((r.ROOT/p).read_bytes())
    document=tmp_path/'false_authority.md';document.write_text('DM01 R4 FAIL, not PASS')
    value=dict(status='EXTERNALLY_ACCEPTED_DM01_R4_RUNTIME',runtime_contract=r.ref(tmp_path,tmp_path/r.CONTRACT),
        promotion_policy=r.ref(tmp_path,tmp_path/r.POLICY),calendar_head=r.ref(tmp_path,tmp_path/r.CALENDAR),
        independent_external_authority=r.ref(tmp_path,document),permissions=r.PERMISSIONS)
    r.atomic(tmp_path,tmp_path/r.ACCEPTANCE,value)
    with pytest.raises(ValueError,match='EXTERNAL_DISPOSITION_MISSING'):r.accepted_envelope(tmp_path)


def test_real_native_completion_stamp_cannot_be_invented(env):
    evidence=env['freeze']['availability_evidence']['BAOSTOCK_DAILY_UPDATE']
    p=Path(evidence['binding']['path']);native=json.loads(p.read_bytes());native.pop('fixture_scope')
    native.update(observed_at=evidence['captured_at'],received_at='2026-09-28T08:02:00+00:00')
    p.write_bytes(r.kernels.canonical(native)+b'\n');evidence['binding']=dict(path=str(p),sha256=r.sha(p),bytes=p.stat().st_size)
    # Reach the native BAOSTOCK check before any external admission.
    env['freeze']['availability_evidence'].pop('TDX_FULL_PACKAGE');rehash(env['freeze'])
    with pytest.raises(ValueError,match='EXACT_NATIVE_READBACK'):r.validate_lineage(env['freeze'],env['root'])


def test_current_parent_package_is_exact_accepted_chain():
    from workbench_analysis.dm01_sources_r4 import parent_tdx_package
    parent=r.current_parent();chain=r.read(r.ROOT,parent['head']['accepted_chain']);context=r.read(r.ROOT,chain['source_context'])
    assert parent_tdx_package(r.ROOT)==context['inputs']['2026-09-30']['families']['TDX_FULL_PACKAGE']
