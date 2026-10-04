"""Exact bridge integration vectors. Every positive is synthetic, never real READY."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from scripts import r25_bridge_oracle_r4r2 as o
from scripts.build_r25_bridge_r4r2 import produce_bridge,produce_daily
from scripts.v4_16_go_forward_input_authority_r4r2 import GoForwardInputAuthority
from scripts.validate_r25_preflight import inspect_inputs,dependency_digest
from tests.v4_dm01_r4r1.test_lineage import env as prior_env
from workbench_analysis import dm01_runtime_r4 as r
from workbench_analysis import dm01_lineage_r4r1 as l

ROOT=Path(__file__).resolve().parents[2]
def put(root,path,obj):return r.atomic(root,Path(root)/path,obj)

@pytest.fixture
def vector(tmp_path):
    e=prior_env.__wrapped__(tmp_path)
    e['parent']['head']['component_artifacts']=e['parent']['components']
    e['parent']['binding']=put(tmp_path,'fixture_v2_head.json',e['parent']['head'])
    e['freeze']['parent_data_head_digest']=e['parent']['binding']['sha256']
    e['freeze']['manifest_sha256']=o.digest({k:x for k,x in e['freeze'].items() if k!='manifest_sha256'})
    built=r.build_candidate(parent=e['parent'],freeze=e['freeze'],cal=e['calendar'],identity=e['identity'],root=tmp_path)
    c=r.read(tmp_path,built['candidate']);obs=r.read(tmp_path,c['target_session_observation_receipt'])
    child=dict(e['parent']['head'],**l.head_lineage(e['parent']['head'],c,c['target_session_observation_receipt']),
        final_candidate=built['candidate'],parent_archive=e['parent']['binding'],parent_head_sha256=e['parent']['binding']['sha256'],
        calendar=c['calendar'],accepted_trade_date=c['target_trade_date'])
    child['component_artifacts']={cap:r.ref(tmp_path,Path(receipt['artifact_path'])) for cap,receipt in c['components'].items()}
    childref=put(tmp_path,r.HEAD,child)
    put(tmp_path,r.CALENDAR,dict(calendar=c['calendar']))
    for p in [o.CONTRACT_PATH,'config/v4_16_go_forward_input_authority_v1.json']:
        put(tmp_path,p,(ROOT/p).read_bytes())
    archival=json.loads((ROOT/o.CONTRACT_PATH).read_bytes())['immutable_data_head_readback']
    put(tmp_path,archival['path'],(ROOT/archival['path']).read_bytes())
    b=dict(contract_id=o.BRIDGE_ID,parent_data_head=e['parent']['binding'],child_data_head=childref,candidate=built['candidate'],
        target_trade_date=c['target_trade_date'],target_session_source_manifest=c['source_manifest'],
        target_session_all_nine_receipts=c['components'],target_session_observation_receipt=c['target_session_observation_receipt'])
    bref=put(tmp_path,'bridge.json',b)
    d=dict(contract_id=o.CONTRACT_ID,target_trade_date=b['target_trade_date'],target_session_pit_binding=bref,not_real_evidence=True)
    d['daily_input_digest']=o.digest(d)
    return dict(root=tmp_path,e=e,c=c,obs=obs,child=child,b=b,d=d,engineering=True)

def refresh(v):
    root=v['root'];c=v['c'];b=v['b'];child=v['child']
    c['target_session_observation_receipt']=put(root,'observation.json',v['obs']);b['target_session_observation_receipt']=c['target_session_observation_receipt'];child['target_session_observation_receipt']=c['target_session_observation_receipt']
    b['candidate']=put(root,'candidate.json',c);child['final_candidate']=b['candidate']
    b['child_data_head']=put(root,r.HEAD,child);v['d']['target_session_pit_binding']=put(root,'bridge.json',b)
    v['d']['daily_input_digest']=o.digest({k:x for k,x in v['d'].items() if k!='daily_input_digest'})

def shape(v):
    freeze=deepcopy(v['e']['freeze']);freeze['engineering_simulation']=False;freeze['manifest_sha256']=o.digest({k:x for k,x in freeze.items() if k!='manifest_sha256'})
    v['c'].update(real_forward_evidence=True,target_session_observation_proven=True,engineering_simulation=False,knowledge_lineage=o.MIXED,source_manifest=put(v['root'],'source.json',freeze))
    v['obs'].update(real_forward_evidence=True,target_session_observation_proven=True,engineering_simulation=False,evidence_class='PIT_OBSERVED',source_manifest_digest=freeze['manifest_sha256'])
    v['b']['target_session_source_manifest']=v['c']['source_manifest'];v['child'].update(target_session_source_manifest=v['c']['source_manifest'],target_session_real_forward_evidence=True,target_session_observation_proven=True,target_session_evidence_class='PIT_OBSERVED')
    v['engineering']=False;refresh(v)

def admission(v):
    return GoForwardInputAuthority.validate_bridge(v['root'],v['d'],o.binding(v['root'],o.CONTRACT_PATH),engineering=v['engineering'],test_only=True)

def packet_vector(v,bridge):
    from tests.test_r25_packet import vector as historical_vector
    return historical_vector(v['root'],successor=True,target=v['e']['freeze']['trade_date'],previous=v['e']['parent']['head']['accepted_trade_date'],bridge=bridge,
        calendar_binding=v['c']['calendar'],source_bindings={k:v['child']['component_artifacts'][cap] for k,cap in [('TDX_RAW_DAILY','RAW_DAILY'),('ADJUSTED_DAILY','ADJUSTED_DAILY')]})

@pytest.mark.parametrize('case',list(range(1,11))+[13])
def test_negative(case,vector):
    v=vector
    original_bridge=v['d']['target_session_pit_binding']
    if case in (6,7):shape(v)
    if case in (1,10):v['d'].pop('target_session_pit_binding')
    if case==2:v['b']['contract_id']='WRONG'
    if case==3:v['b']['target_trade_date']='2026-09-29'
    if case==4:v['b']['parent_data_head']=put(v['root'],'wrong_parent.json',dict(v['e']['parent']['head'],accepted_trade_date='2026-09-24'))
    if case==5:v['b']['child_data_head']=put(v['root'],'wrong_child.json',dict(v['child'],decoy=True))
    if case==6:v['c']['real_forward_evidence']=False
    if case==7:v['obs']['real_forward_evidence']=False
    if case==8:
        cap=next(iter(v['b']['target_session_all_nine_receipts']));v['b']['target_session_all_nine_receipts'][cap]['artifact_sha256']='0'*64
    if case==9:
        sourcepath=r.path(v['root'],v['b']['target_session_source_manifest']);raw=json.loads(sourcepath.read_bytes());raw['tampered']=True;put(v['root'],sourcepath,raw)
    if case in (2,3,4,5,8):v['d']['target_session_pit_binding']=put(v['root'],'bridge.json',v['b'])
    if case in (6,7):refresh(v)
    if case==13:v['d']['target_session_pit_binding']=put(v['root'],'different_bridge.json',v['b'])
    else:v['d']['daily_input_digest']=o.digest({k:x for k,x in v['d'].items() if k!='daily_input_digest'})
    with pytest.raises((ValueError,KeyError)):admission(v)
    packet=packet_vector(v,v['d'].get('target_session_pit_binding'))
    if v['engineering']:packet['daily']['bridge_mode']='ENGINEERING'
    packet['daily']['daily_input_digest']=o.digest({k:x for k,x in packet['daily'].items() if k!='daily_input_digest'})
    if case==13:packet['daily']['daily_input_digest']=o.digest(dict({k:x for k,x in packet['daily'].items() if k!='daily_input_digest'},target_session_pit_binding=original_bridge))
    packet['candidate']['grant']['daily_input_digest']=packet['daily']['daily_input_digest']
    packet['candidate']['grant']['daily_input_authority']=put(v['root'],'negative_daily.json',packet['daily'])
    with pytest.raises(ValueError):inspect_inputs(v['root'],*[packet[k] for k in ('candidate','daily','sources','deps','contract','predecessor')],test_only=True)
    with pytest.raises(ValueError):GoForwardInputAuthority(v['root'],packet['deps']['go_forward_input'],packet['candidate']['grant']['daily_input_authority'],packet['candidate']['grant'],packet['candidate']['grant']['daily_input_boundary'])
    if case in (6,7):
        with pytest.raises(ValueError):o.inspect_bridge_object(v['root'],v['b'],test_only=True)
        b=v['b']
        with pytest.raises(ValueError):produce_bridge(v['root'],parent=b['parent_data_head'],child=b['child_data_head'],candidate=b['candidate'],source=b['target_session_source_manifest'],receipts=b['target_session_all_nine_receipts'],observation=b['target_session_observation_receipt'],target=b['target_trade_date'],observed_at=v['e']['freeze']['observed_at'],output='reports/r25/target_session_bridge/blocked.json')
        assert not (v['root']/'reports/r25/target_session_bridge/blocked.json').exists()

def test_R4R2_11_engineering_producer(vector):
    v=vector;b=v['b']
    result=produce_bridge(v['root'],parent=b['parent_data_head'],child=b['child_data_head'],candidate=b['candidate'],source=b['target_session_source_manifest'],receipts=b['target_session_all_nine_receipts'],observation=b['target_session_observation_receipt'],target=b['target_trade_date'],observed_at=v['e']['freeze']['observed_at'],output='produced.json',engineering=True)
    assert result['status']=='PASS_ENGINEERING_BRIDGE_NOT_REAL' and result['r25_grant'] is False and result['real_ready'] is False
    assert admission(v)['real_ready'] is False
    packet=packet_vector(v,result['binding'])
    produced=produce_daily(v['root'],packet['daily'],result['binding'],output='produced_daily.json',engineering=True)
    packet['daily']=o.exact(v['root'],produced);packet['candidate']['grant'].update(daily_input_authority=produced,daily_input_digest=packet['daily']['daily_input_digest'])
    assert inspect_inputs(v['root'],*[packet[k] for k in ('candidate','daily','sources','deps','contract','predecessor')],test_only=True)['status']=='PASS_ENGINEERING_VECTOR_NOT_REAL'

def test_R4R2_12_real_shaped_parity(vector,monkeypatch):
    v=vector;shape(v)
    runtime=admission(v);preflight=o.inspect_daily_bridge(v['root'],v['d'],o.binding(v['root'],o.CONTRACT_PATH),test_only=True)
    assert runtime==preflight and runtime['real_ready'] is False and runtime['r25_grant'] is False
    packet=packet_vector(v,v['d']['target_session_pit_binding'])
    assert inspect_inputs(v['root'],*[packet[k] for k in ('candidate','daily','sources','deps','contract','predecessor')],test_only=True)['status']=='PASS_ENGINEERING_VECTOR_NOT_REAL'
    assert GoForwardInputAuthority.validate_bridge(v['root'],packet['daily'],packet['deps']['go_forward_input'],test_only=True)['real_ready'] is False
    # Complete packet producer -> exact manifest oracle in an isolated root.
    from scripts.build_r25_bridge_r4r2 import produce_packet
    from scripts.validate_r25_preflight import inspect_packet
    deps_ref=put(v['root'],'config/v4_16_runtime_dependencies_v4.json',(ROOT/'config/v4_16_runtime_dependencies_v4.json').read_bytes())
    for reference in packet['deps']['bindings']:
        put(v['root'],reference['path'],(ROOT/reference['path']).read_bytes())
    audit='docs/evidence/r25/V4_R24R1_GO_FORWARD_INPUT_AUTHORITY_COHORT_IDENTITY_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'
    put(v['root'],audit,(ROOT/audit).read_bytes())
    packetref=produce_packet(v['root'],daily=packet['candidate']['grant']['daily_input_authority'],candidate=put(v['root'],'reports/r25/activation_candidate/authority.json',packet['candidate']),sources=packet['candidate']['grant']['source_authority'],predecessor=packet['candidate']['grant']['predecessor'],output='reports/r25/activation_candidate/engineering_packet.json',engineering=True)
    result=inspect_packet(v['root'],packetref,test_only=True)
    assert result['status']=='PASS_ENGINEERING_VECTOR_NOT_REAL' and result['execution_authorized'] is False
    with pytest.raises(ValueError):inspect_packet(v['root'],packetref)
    with pytest.raises((ValueError,FileNotFoundError)):GoForwardInputAuthority(v['root'],o.binding(v['root'],o.CONTRACT_PATH),put(v['root'],'daily.json',v['d']),{},'2026-09-28T13:00:00Z')
    # Explicit synthetic authorization seam only; exercise the entire input
    # constructor with literal exact reads, without a controller, DB or grant.
    from scripts import v4_16_go_forward_input_authority as historical
    from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
    immutable=CurrentStageAuthority(ROOT);immutable.root=v['root']
    put(v['root'],'config/v4_current_stage_authority_v2.json',(ROOT/'config/v4_current_stage_authority_v2.json').read_bytes())
    class LiteralReader:
        def read(self,b):return o.exact_bytes(v['root'],b),dict(scope='ENGINEERING_LITERAL_READ_ONLY')
    immutable.exact_reader=LiteralReader()
    import scripts.v4_16_go_forward_input_authority_r4r2 as successor
    monkeypatch.setattr(successor,'CurrentStageAuthority',lambda root,exact_reader=None:immutable)
    monkeypatch.setattr(l,'validate_r25_binding',lambda *args,**kwargs:dict(r25_grant=False,real_forward_evidence=False))
    monkeypatch.setattr(GoForwardInputAuthority,'validate_bridge',staticmethod(lambda root,daily,contract:o.inspect_daily_bridge(root,daily,contract,test_only=True)))
    loaded=GoForwardInputAuthority(v['root'],packet['deps']['go_forward_input'],packet['candidate']['grant']['daily_input_authority'],packet['candidate']['grant'],packet['candidate']['grant']['daily_input_boundary'])
    assert loaded.daily==packet['daily'] and not (v['root']/'data/v4/shadow_real_v1').exists()

def test_R4R2_14_old_V1_historical_only(vector):
    v=vector;v['d']['contract_id']='V4_16_GO_FORWARD_INPUT_AUTHORITY_V1'
    with pytest.raises(ValueError,match='SUCCESSOR_DAILY_CONTRACT_REQUIRED'):admission(v)
    assert (ROOT/'config/v4_16_go_forward_input_authority_v1.json').read_bytes()==(v['root']/'config/v4_16_go_forward_input_authority_v1.json').read_bytes()

def test_R4R2_15_contract_parity():
    deps=json.loads((ROOT/'config/v4_16_runtime_dependencies_v4.json').read_bytes())
    assert deps['go_forward_input']==o.binding(ROOT,o.CONTRACT_PATH)
    assert o.exact(ROOT,deps['packet_contract'])['go_forward_input_contract']==deps['go_forward_input']
    assert GoForwardInputAuthority.validate_bridge is o.inspect_daily_bridge
    from scripts.v4_16_go_forward_shadow_runtime_r4r2 import RealShadowController
    with pytest.raises(ValueError,match='REAL_SHADOW_NOT_AUTHORIZED_BEFORE_CONSUMPTION'):RealShadowController(ROOT)

@pytest.mark.parametrize('target,observed_at',[('2026-10-08','2026-10-05T00:00:00Z'),('2026-09-28','2026-09-28T06:00:00Z')])
def test_R4R2_16_future_wait(tmp_path,target,observed_at):
    result=produce_bridge(tmp_path,parent=None,child=None,candidate=None,source=None,receipts=None,observation=None,target=target,observed_at=observed_at,output='reports/r25/target_session_bridge/bridge.json')
    assert result['status']=='WAIT_MARKET_CLOSE' and result['source_requests']==0 and result['bridge_created'] is False
    assert not (tmp_path/'bridge.json').exists()

def test_output_cannot_target_heads(tmp_path):
    with pytest.raises(ValueError,match='BRIDGE_OUTPUT_ROOT_REQUIRED'):
        produce_bridge(tmp_path,parent=None,child=None,candidate=None,source=None,receipts=None,observation=None,target='2026-10-08',observed_at='2026-10-05T00:00:00Z',output='reports/r25/target_session_bridge/../../../data/v4/V4_DATA_ACCEPTED_HEAD.json')
    assert not (tmp_path/r.HEAD).exists()
