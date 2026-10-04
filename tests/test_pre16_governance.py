"""Independent governance scope, exact lineage and no-permission regression."""
from copy import deepcopy
import inspect
import pytest
from scripts import validate_pre16_governance as o
from scripts.pre16_current_audit_reader import CurrentAuditStatus

@pytest.fixture
def h():return deepcopy(o.read(o.HEAD,o.ROOT))

def test_historical_r1_registry_immutable():
    assert (o.ROOT/o.R1).read_bytes()==o.frozen(o.R1,o.ROOT)

def test_current_a01_not_taken_from_stale_r1(h):
    assert h['entries']['A01']['capability_dimensions']['external_acceptance']=='EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN'
    h['entries']['A01']['current_state']='OPEN_ENGINEERING'
    with pytest.raises(ValueError,match='DERIVED_STATE_A01'):o.verify_entries(h,o.ROOT)

def test_current_a02_exact_scoped_acceptance(h):
    assert o.verify_entries(h,o.ROOT)
    h['entries']['A02']['evidence_bindings']=[]
    with pytest.raises(ValueError,match='REQUIRED_ENTRY_FIELDS_A02'):o.verify_entries(h,o.ROOT)

def test_a02_as_recorded_not_upgraded(h):
    h['entries']['A02']['capability_dimensions']['AS_RECORDED']=True
    with pytest.raises(ValueError,match='A02_AS_RECORDED_OVERCLAIM'):o.verify_entries(h,o.ROOT)

@pytest.mark.parametrize('field,value',[('formal_consumer_enabled',True),('historical_formal_capability','PASS'),('known_amount_a',1),('consumer_auto_activation_after_H21',True)])
def test_a04_scope_not_overclaimed(h,field,value):
    h['entries']['A04']['capability_dimensions'][field]=value
    with pytest.raises(ValueError,match='A04_SCOPE_OVERCLAIM'):o.verify_entries(h,o.ROOT)

@pytest.mark.parametrize('key',['A08','A09','A08_CURRENT_RUNTIME'])
def test_a08_a09_implementation_only_does_not_close_audit(h,key):
    assert h['entries']['A08']['current_state']==h['entries']['A09']['current_state']=='ACCEPTED_SCOPED'
    assert h['entries']['A08_CURRENT_RUNTIME']['current_state']=='OPEN_EXTERNAL_REAUDIT'
    e=h['entries'][key];e['current_authority']={'implementation':h['sources']['open_items']};e['evidence_bindings']=list(e['current_authority'].values())
    with pytest.raises(ValueError,match='EXACT_REQUIRED_AUTHORITY'):o.verify_entries(h,o.ROOT)

def test_current_stage_is_v4_15():
    from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
    assert CurrentStageAuthority(o.ROOT).head['stage']=='V4-15'

def test_data_head_is_2026_09_30():assert o.read('data/v4/V4_DATA_ACCEPTED_HEAD.json',o.ROOT)['accepted_trade_date']=='2026-09-30'

def test_v4_10_to_v4_15_heads_unchanged():
    for name in ['V4_10_ACCEPTED_HEAD','V4_11_ACCEPTED_HEAD','V4_12_ACCEPTED_HEAD','V4_13_ACCEPTED_HEAD_AMENDED_R1','V4_14_ACCEPTED_HEAD','V4_15_ACCEPTED_HEAD','V4_STAGE_ACCEPTED_HEAD','V4_DATA_ACCEPTED_HEAD']:
        path='data/v4/'+name+'.json';assert (o.ROOT/path).read_bytes()==o.frozen(path,o.ROOT)

def test_historical_pit_not_granted(h):
    h['entries']['HISTORICAL_PIT_EFFECTIVENESS']['capability_dimensions']['capability']='PASS'
    with pytest.raises(ValueError,match='HISTORICAL_PIT_NOT_GRANTED'):o.verify_entries(h,o.ROOT)

def test_real_maturity_none(h):
    assert o.read('data/v4/V4_15_ACCEPTED_HEAD.json',o.ROOT)['CURRENT_REAL_MATURITY_EVIDENCE']=='NONE'
    h['entries']['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME']['capability_dimensions']['PROVED_HORIZONS']=[1]
    with pytest.raises(ValueError,match='NONBLOCKING_DEBT_NOT_PASS'):o.verify_entries(h,o.ROOT)

@pytest.mark.parametrize('key',['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME','REALTIME_ACCEPTED_COHORT_MATURITY','V4_15_FWD_ADJ_VECTOR_01'])
def test_nonblocking_debt_not_promoted_to_pass(h,key):
    h['entries'][key]['current_state']='ACCEPTED_FULL_REQUIRED_SCOPE'
    with pytest.raises(ValueError,match='DERIVED_STATE'):o.verify_entries(h,o.ROOT)

@pytest.mark.parametrize('key',['production','shadow','focus'])
def test_permissions_all_false(h,key):
    h[key]=True
    with pytest.raises(ValueError,match='PERMISSIONS_FALSE'):o.validate(head=h)

def test_v4_16_false(h):
    h['V4_16']=True
    with pytest.raises(ValueError,match='PERMISSIONS_FALSE'):o.validate(head=h)

def test_supersession_graph_acyclic(h):
    assert o.acyclic(h['supersession_graph'])
    h['supersession_graph'][o.R1]=[o.HEAD]
    with pytest.raises(ValueError,match='SUPERSESSION_CYCLE'):o.acyclic(h['supersession_graph'])

def test_no_latest_glob_discovery():
    from scripts import pre16_current_audit_reader as reader
    source=inspect.getsource(reader)+inspect.getsource(o)
    assert all(token not in source for token in ['.glob(','.rglob(','mtime','latest_file'])
    assert reader.CONTRACT=='config/v4_cross_stage_current_audit_authority_v1.json'

@pytest.mark.parametrize('key',['A01','A02','A03','A04','A05','A06','A07','A08','A09','OWNER','READER','HISTORICAL_PIT_EFFECTIVENESS','REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME','REALTIME_ACCEPTED_COHORT_MATURITY','V4_15_FWD_ADJ_VECTOR_01'])
def test_missing_mandatory_item_fail_closed(h,key):
    del h['entries'][key]
    with pytest.raises(ValueError,match='COMPLETE_CURRENT_ITEM_SET'):o.verify_entries(h,o.ROOT)

@pytest.mark.parametrize('key',['A03','A06','A07','OWNER','READER'])
def test_no_global_authority_activation(h,key):
    h['entries'][key]['capability_dimensions']['active_global_trust_root']=True
    with pytest.raises(ValueError,match='INACTIVE_OWNER_NO_CUTOVER'):o.verify_entries(h,o.ROOT)

def test_reader_metadata_not_permission():
    reader=CurrentAuditStatus();assert reader.stage_permission() is False
    e=reader.entry('A01');e['current_state']='ALTERED'
    assert reader.entry('A01')['current_state']=='ACCEPTED_SCOPED'

def test_independent_oracle_no_writer_or_business_evaluator():
    import ast
    tree=ast.parse(inspect.getsource(o))
    imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    assert not any(n and any(x in n for x in ['build_pre16','radar_cohort','settlement']) for n in imports)

def test_full_independent_oracle():assert o.validate()['PRE16_CROSS_STAGE_GOVERNANCE_RECONCILIATION']=='PASS_LOCAL'

def test_protected_all_history():assert len(o.protected(o.ROOT))>=25

def test_governance_namespace_cannot_change_accepted():
    from scripts.pre16_governance_io import atomic
    with pytest.raises(ValueError,match='GOVERNANCE_OUTPUT_ONLY'):atomic('data/v4/V4_15_ACCEPTED_HEAD.json',{})

def test_source_selection_cannot_use_implementation(h):
    h['sources']['a02']=h['sources']['open_items']
    with pytest.raises(ValueError,match='SOURCE_SELECTION_a02'):o.validate(head=h)

@pytest.mark.parametrize('name',['V4_STAGE_ACCEPTED_HEAD','V4_DATA_ACCEPTED_HEAD','V4_10_ACCEPTED_HEAD','V4_11_ACCEPTED_HEAD','V4_12_ACCEPTED_HEAD','V4_13_ACCEPTED_HEAD_AMENDED_R1','V4_14_ACCEPTED_HEAD','V4_15_ACCEPTED_HEAD'])
def test_protected_literal_newline_change_rejected(tmp_path,monkeypatch,name):
    path='data/v4/'+name+'.json';old=(o.ROOT/path).read_bytes()
    target=tmp_path/path;target.parent.mkdir(parents=True);target.write_bytes(old.replace(b'\n',b'\r\n'))
    monkeypatch.setattr(o.subprocess,'check_output',lambda *a,**k:old)
    with pytest.raises(ValueError,match='PROTECTED_LITERAL_BYTES'):o.frozen(path,tmp_path)

def test_historical_status_cannot_be_rewritten(h):
    h['entries']['A01']['superseded_historical_statuses'][0]['status']='FABRICATED_PASS'
    with pytest.raises(ValueError,match='EXACT_HISTORICAL_STATUS_A01'):o.verify_entries(h,o.ROOT)

def test_consumer_inventory_complete():
    s=o.read('reports/pre16_governance/CONSUMER_SCAN.json',o.ROOT)
    assert sum(s['counts'].values())==len(s['matches'])==128
    assert s['counts']['CURRENT_RUNTIME_CONSUMER']==s['counts']['UNKNOWN']==0
