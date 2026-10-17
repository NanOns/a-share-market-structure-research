"""New Reader wiring controls; tiny PG fixtures do not grant admission."""
import hashlib
import json
from copy import deepcopy
import pytest
from workbench_analysis.r43_owner_replay import ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_db.v4_operational_owner_authority_v2 import KEY,prepare,prepare_successor

def candidate(root):
    source=root/'raw.json';atomic_json(root,source,dict(rows=[dict(security_id='FIXTURE',amount=105.625)]))
    snapshot=root/'snapshot.json'
    atomic_json(root,snapshot,{key:False for key in ('membership_mode','taxonomy','membership_snapshot_id',
        'membership_observed_at','member_set_asof','knowledge_lineage','AS_RECORDED','PIT_ELIGIBLE',
        'HISTORICAL_FIRST_AVAILABLE_PROVEN','production_eligible_scope','survivorship_bias_risk')})
    return dict(owners={'2026-10-12':dict(raw=ref(root,source))},published_sessions=['2026-10-12'],
        membership_snapshot=ref(root,snapshot),exact_daily_adjustment_contract='V4_OPERATIONAL_CORE_EXACT_AFFINE_CANDIDATE_R3')

def test_new_reader_uses_fact_token_and_enforces_current_http_token(tmp_path,monkeypatch):
    from workbench_analysis import operational_successor_v1 as module
    data=candidate(tmp_path)
    binding={"path":"authority.pg.json","sha256":"d"*64,"bytes":3,"pg_descriptor":{"kind":"authority_manifest"}}
    data[KEY]=binding
    authority={"contract_id":"V4_HEAD_EMBEDDED_NATIVE_PG_OWNER_AUTHORITY_V2",
        "source_owners":data['owners'],"owner_source_digest":"e"*64,
        "owners":{"2026-10-12":{"raw":{"descriptor":{"path":"owner.pg.json","sha256":"f"*64,
            "bytes":4,"pg_descriptor":{"kind":"raw","fact_key":"fact"}},"fact_token":"a"*64}}},
        "historical_PIT_permission":False,"AS_RECORDED":False,"PIT_ELIGIBLE":False}
    # This control exercises Reader IO only; full admission has separate real data evidence.
    monkeypatch.setattr(module,'validate',lambda root,data,**kwargs:True)
    monkeypatch.setattr('workbench_db.v4_operational_owner_authority_v2.load',lambda root,data:authority)
    monkeypatch.setattr('workbench_db.v4_operational_owner_authority_v2.read',lambda *a,**k:[dict(security_id='FIXTURE',amount=105.625)])
    monkeypatch.setattr('workbench_db.v4_operational_owner_authority_v2.attest',lambda *a,**k:None)
    reader=module.OperationalSuccessorReaderV1(tmp_path,data)
    assert reader.read('raw','2026-10-12',reader.token)['rows']==[dict(security_id='FIXTURE',amount=105.625)]
    assert reader.read('raw','2026-10-12',reader.token)['rows'][0]['amount']==105.625
    with pytest.raises(ValueError,match='CONTEXT_TOKEN_MISMATCH'):reader.read('raw','2026-10-12','a'*64)

def test_exact_reader_rejects_missing_embedded_authority_without_static_fallback(tmp_path,monkeypatch):
    from workbench_analysis import operational_successor_v1 as module
    monkeypatch.setattr(module,'validate',lambda root,data,**kwargs:True)
    with pytest.raises(ValueError,match='EMBEDDED_AUTHORITY_REQUIRED_NO_FALLBACK'):
        module.OperationalSuccessorReaderV1(tmp_path,candidate(tmp_path))

def test_operational_reader_rejects_legacy_head_authority_file_fallback(tmp_path,monkeypatch):
    from workbench_analysis import operational_successor_v1 as module
    data=candidate(tmp_path)
    data.pop('exact_daily_adjustment_contract')
    monkeypatch.setattr(module,'validate',lambda root,data,**kwargs:True)
    with pytest.raises(ValueError,match='PG_OPERATIONAL_OWNER_EMBEDDED_AUTHORITY_REQUIRED_NO_FALLBACK'):
        module.OperationalSuccessorReaderV1(tmp_path,data)

def test_successor_preparation_preserves_original_serialized_head_fact_token(tmp_path):
    from workbench_db.v4_operational_owner_pg_closeout import OWNER
    from workbench_db import v4_operational_owner_authority_v2 as authority_module
    from workbench_db import v4_operational_owner_pg_closeout as closeout_module
    previous=candidate(tmp_path);head=tmp_path/'predecessor.json';atomic_json(tmp_path,head,previous)
    binding=ref(tmp_path,head);source=previous['owners']['2026-10-12']['raw']
    descriptor={"path":"owner.pg.json","sha256":"b"*64,"bytes":2,"pg_descriptor":{"kind":"raw","fact_key":"fact"}}
    authority=dict(contract_id=OWNER,head_token=binding['sha256'],source_owners=previous['owners'],
        owners={'2026-10-12':dict(raw=descriptor)},historical_PIT_permission=False,PIT_ELIGIBLE=False,AS_RECORDED=False)
    atomic_json(tmp_path,tmp_path/'config/v4_operational_owner_pg_closeout_r1.json',authority)
    successor=deepcopy(previous);successor.update(predecessor=binding,metadata='NEW_HEAD')
    legacy_binding={'path':'config/v4_operational_owner_pg_closeout_r1.json',
        'sha256':hashlib.sha256((tmp_path/'config/v4_operational_owner_pg_closeout_r1.json').read_bytes()).hexdigest(),
        'bytes':(tmp_path/'config/v4_operational_owner_pg_closeout_r1.json').stat().st_size}
    monkeypatch = __import__('pytest').MonkeyPatch()
    monkeypatch.setattr(closeout_module,'load_authority',lambda *args,**kwargs:authority)
    monkeypatch.setattr(authority_module,'prepare',lambda *args,**kwargs:({'path':'manifest.pg.json','sha256':'c'*64,'bytes':3},
        {'counts':dict(reused=1,created=0)}))
    try:
        receipt=prepare_successor(tmp_path,successor,predecessor_authority_binding=legacy_binding)
    finally:monkeypatch.undo()
    assert receipt['counts']==dict(reused=1,created=0)
    assert receipt['legacy_authority_ingress']==dict(path=legacy_binding['path'],sha256=legacy_binding['sha256'],
        disposition='EXACT_BOUND_ONE_TIME_INGRESS_THEN_PG_MANIFEST')


def test_runtime_owner_validation_uses_pg_authority_without_opening_owner_files(tmp_path,monkeypatch):
    from workbench_analysis import operational_successor_v1 as module
    from workbench_db.v4_operational_owner_authority_v2 import CONTRACT,validate as validate_pg
    from workbench_db.v4_forward_pg_r1 import canonical, digest as pg_digest
    owners={'2026-10-12':{'raw':{'path':'raw.json','sha256':'b'*64,'bytes':1}}}
    candidate={'owners':owners,'accepted_trade_date':'2026-10-12'}
    authority={'contract_id':CONTRACT,'source_owners':owners,
        'owner_source_digest':pg_digest(canonical(owners)),
        'owners':{'2026-10-12':{'raw':{'descriptor':{'kind':'raw'},'fact_token':'a'*64}}},
        'historical_PIT_permission':False,'AS_RECORDED':False,'PIT_ELIGIBLE':False}
    checked=[]
    monkeypatch.setattr(module,'checked',lambda *args,**kwargs:checked.append(args) or (_ for _ in ()).throw(AssertionError('OWNER_FILE_OPENED')))
    module._validate_owner_bindings(tmp_path,candidate,authority)
    assert checked==[]
    validate_pg(candidate,authority)


def test_successor_http_context_uses_head_bound_pg_membership_metadata_without_file_fallback(tmp_path,monkeypatch):
    from workbench_analysis import operational_successor_v1 as module
    from workbench_db import v4_membership_reference_pg_v1 as membership
    data=candidate(tmp_path)
    data.update(accepted_trade_date='2026-10-12',data_cutoff_date='2026-10-12',
        membership_snapshot_id='SNAP-PG',observed_at='2026-10-12T19:00:00+08:00',published_sessions=['2026-10-12'])
    data[membership.KEY]={'contract_id':membership.PG_AUTHORITY_CONTRACT}
    metadata={key:False for key in ('AS_RECORDED','PIT_ELIGIBLE','HISTORICAL_FIRST_AVAILABLE_PROVEN','production_eligible_scope','survivorship_bias_risk')}
    metadata.update(membership_mode='CURRENT',taxonomy='TDX',membership_snapshot_id='SNAP-PG',
        membership_observed_at='2026-10-12T18:00:00+08:00',member_set_asof='2026-10-12',knowledge_lineage='CURRENT_DAY')
    monkeypatch.setattr(module,'validate',lambda root,data,**kwargs:True)
    monkeypatch.setattr('workbench_db.v4_operational_owner_authority_v2.load',lambda root,data:{})
    pg_membership_descriptor={'path':'membership.json','sha256':'a'*64,'pg_descriptor':{'kind':'reference_memberships'}}
    monkeypatch.setattr(membership,'context_snapshot',lambda root,candidate:dict(metadata,memberships=pg_membership_descriptor))
    monkeypatch.setattr(module,'checked',lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('MEMBERSHIP_FILE_OPENED')))

    reader=module.OperationalSuccessorReaderV1(tmp_path,data)
    context=reader.context()

    assert context['membership_snapshot_id']=='SNAP-PG'
    assert context['taxonomy']=='TDX'
    assert context['PIT_ELIGIBLE'] is False
    assert context['membership_snapshot']==data['membership_snapshot']
    assert reader.snapshot['memberships']==pg_membership_descriptor


def test_successor_validation_uses_pg_membership_and_identity_authorities_without_file_fallback(tmp_path,monkeypatch):
    from workbench_analysis import operational_successor_v1 as module
    from workbench_db import v4_membership_reference_pg_v1 as membership
    data=candidate(tmp_path)
    data.update(membership_snapshot_id='SNAP-PG')
    data[membership.KEY]={'contract_id':membership.PG_AUTHORITY_CONTRACT}
    snapshot={'membership_snapshot_id':'SNAP-PG','PIT_ELIGIBLE':False,
        'memberships':{'pg_descriptor':{'kind':'reference_memberships'}}}
    calls=[]
    monkeypatch.setattr(membership,'context_snapshot',lambda root,candidate:snapshot)
    monkeypatch.setattr(membership,'read',lambda root,candidate:calls.append('memberships') or [])
    monkeypatch.setattr(membership,'read_identity',lambda root,candidate:calls.append('identity') or [])
    monkeypatch.setattr(module,'checked',lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('MEMBERSHIP_FILE_OPENED')))

    result=module._validate_membership_inputs(tmp_path,data)

    assert result is snapshot
    assert calls==['memberships','identity']


def test_candidate_preparation_owner_validation_keeps_exact_file_binding_check(tmp_path,monkeypatch):
    from workbench_analysis import operational_successor_v1 as module
    binding={'path':'owner.json','sha256':'a'*64}
    candidate={'owners':{'2026-10-12':{'raw':binding}},'accepted_trade_date':'2026-10-12'}
    opened=[]
    monkeypatch.setattr(module,'checked',lambda root,value:opened.append(value) or b'owner')
    module._validate_owner_bindings(tmp_path,candidate)
    assert opened==[binding]
