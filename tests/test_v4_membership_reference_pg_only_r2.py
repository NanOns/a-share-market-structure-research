"""Membership and authority owners are read through PG without opening artifacts."""
from contextlib import contextmanager

import pytest

import workbench_db.v4_membership_reference_pg_v1 as reference_pg
import workbench_db.v4_operational_owner_pg_closeout as owner_pg
from workbench_db.v4_forward_pg_r1 import canonical,digest,ForwardFactStore
from workbench_db.v4_native import workspace_schema


def test_membership_reference_loads_authority_and_rows_from_pg_only(tmp_path,monkeypatch):
    day='2026-10-12';source={'path':'missing/members.jsonl.gz','sha256':'a'*64,'bytes':200}
    snapshot={'path':'missing/snapshot.json','sha256':'b'*64,'bytes':120}
    rows=[{'sector_id':'INDUSTRY:FIXTURE','security_id':'SH.600000'}]
    context_key='c'*64
    fact_payload=dict(contract_id=owner_pg.OWNER,head_token=context_key,T0=day,
        domain='reference_memberships',source_binding=source,rows=rows,
        PIT_ELIGIBLE=False,AS_RECORDED=False)
    fact_raw=canonical(fact_payload).decode();fact_sha=digest(fact_raw.encode())
    fact_key='reference-memberships-fixture'
    fact_schema=workspace_schema(tmp_path/owner_pg.FOLDER,'forward')
    fact_descriptor=dict(contract_id=owner_pg.CONTRACT,engine='postgresql',schema=fact_schema,
        kind='reference_memberships',fact_key=fact_key,payload_sha256=fact_sha,
        database_identity={'system_identifier':'fixture'})
    fact_descriptor_raw=canonical(fact_descriptor)
    fact_binding=dict(path=f"{owner_pg.FOLDER}/reference_memberships/{digest(fact_key.encode())}.pg.json",
        sha256=digest(fact_descriptor_raw),bytes=len(fact_descriptor_raw),pg_descriptor=fact_descriptor)
    authority=dict(contract_id=reference_pg.CONTRACT,T0=day,membership_snapshot=snapshot,
        source=source,identity_source=None,membership_snapshot_id=None,descriptor=fact_binding,
        fact_token=context_key,rows=len(rows),AS_RECORDED=False,PIT_ELIGIBLE=False)
    authority_raw=canonical(authority).decode();authority_sha=digest(authority_raw.encode())
    authority_key=digest(canonical(authority));authority_schema='v4_forward_abcdef0123456789'
    candidate={
        'accepted_trade_date':day,'membership_snapshot':snapshot,
        reference_pg.KEY:dict(contract_id=reference_pg.PG_AUTHORITY_CONTRACT,engine='postgresql',
            schema=authority_schema,database_identity={'system_identifier':'fixture'},
            kind=reference_pg.AUTHORITY_KIND,fact_key=authority_key,payload_sha256=authority_sha)
    }

    class Cursor:
        def __init__(self,row):self.row=row
        def fetchone(self):return self.row
    class PG:
        def __init__(self,schema):self.schema=schema
        def execute(self,_query,params):
            kind=params[0]
            if kind==reference_pg.AUTHORITY_KIND:return Cursor((authority_raw,authority_sha))
            if kind=='reference_memberships':return Cursor((fact_raw,fact_sha))
            raise AssertionError(kind)
    @contextmanager
    def readonly_connection(schema,*,read_only=False):
        assert read_only is True
        yield PG(schema)

    monkeypatch.setattr(reference_pg,'connection',readonly_connection)
    monkeypatch.setattr(owner_pg,'connection',readonly_connection)
    monkeypatch.setattr(ForwardFactStore,'_database_identity',lambda pg:{'system_identifier':'fixture'})
    monkeypatch.setattr(owner_pg,'read_schema',lambda root,binding,descriptor,workspace_root=None:fact_schema)
    assert not (tmp_path/'missing/snapshot.json').exists()
    assert not (tmp_path/'missing/members.jsonl.gz').exists()
    assert reference_pg.read(tmp_path,candidate)==rows


def test_membership_reference_rejects_file_authority_binding(tmp_path):
    candidate={'accepted_trade_date':'2026-10-12','membership_snapshot':{},
        reference_pg.KEY:{'path':'old-authority.json','sha256':'d'*64,'bytes':20}}
    with pytest.raises(ValueError,match='PG_AUTHORITY_REQUIRED_NO_FILE_FALLBACK'):
        reference_pg._load_authority(tmp_path,candidate)


def test_core_product_bff_identity_records_calls_pg_reader_without_file_fallback(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1

    candidate={'accepted_trade_date':'2026-10-12',reference_pg.KEY:{'engine':'postgresql'}}
    rows=[{'security_id':'SID-1','source_security_key':'SH.600000','security_name':'Fixture'}]
    binding={'contract_id':'V4_NATIVE_IDENTITY_REFERENCE_FIXTURE_R1','sha256':'a'*64}
    calls=[]
    def read_search_identity(root,selected,*,workspace_root=None):
        calls.append((root,selected,workspace_root))
        return rows,binding
    monkeypatch.setattr(reference_pg,'read_search_identity',read_search_identity)
    api=SimpleNamespace(root=tmp_path,candidate=candidate,cache={},pg_owner_workspace_root=None)
    bff=object.__new__(CoreProductBFFR1);bff.api=api
    assert bff.identity_records()==(rows,binding)
    assert calls==[(tmp_path,candidate,None)]
    assert bff.identity_records()==(rows,binding)
    assert len(calls)==1


def test_core_product_bff_display_identity_falls_back_to_pg_identity_owner(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1

    bff=object.__new__(CoreProductBFFR1)
    bff.api=SimpleNamespace(root=tmp_path,candidate={},cache={})
    monkeypatch.setattr(bff,'_read_index_r2',lambda _day:None)
    monkeypatch.setattr(bff,'identity_records',lambda:([
        dict(security_id='SID-1',source_security_key='SH.600000',symbol='600000.SH',security_name='浦发银行')
    ],{'contract_id':'PG_IDENTITY_FIXTURE','T0':'2026-10-12'}))
    result=bff._display_identity_map('2026-10-12',[{'entity_id':'SID-1'},{'entity_id':'600000.SH'}])
    assert result['SID-1']['display_name']=='浦发银行'
    assert result['600000.SH']['display_name_source']['contract_id']=='PG_IDENTITY_FIXTURE'


def test_core_product_bff_rejects_identity_file_fallback_when_pg_authority_missing(tmp_path):
    from types import SimpleNamespace
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1

    api=SimpleNamespace(root=tmp_path,candidate={'accepted_trade_date':'2026-10-12'},cache={},pg_owner_workspace_root=None)
    bff=object.__new__(CoreProductBFFR1);bff.api=api
    with pytest.raises(ValueError,match='NATIVE_SEARCH_IDENTITY_REQUIRED_NO_FILE_FALLBACK'):
        bff.identity_records()

def test_core_product_bff_cohort_route_does_not_open_owner_json(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import workbench_service.core_product_bff_r1 as product_bff
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1

    day='2026-10-12';context_key='fixture-token'
    owner={'path':'data/v4/cohort_owner.json','sha256':'a'*64,'bytes':10}
    candidate={'accepted_trade_date':day,'data_cutoff_date':day,'published_sessions':[day],
        'observed_at':day,'membership_observed_at':'2026-10-12T09:00:00+08:00',
        'owners':{day:{'validation_cohort':owner}}}
    api=SimpleNamespace(root=tmp_path,candidate=candidate,
        context=lambda:dict(context_token=context_key,production_accepted=True))
    setattr(api,'token',context_key)
    bff=object.__new__(CoreProductBFFR1);bff.api=api;bff.isolated_history=None
    calls=[]
    monkeypatch.setattr(product_bff,'checked',lambda *_:pytest.fail('cohort Owner file opened by runtime BFF'))
    monkeypatch.setattr(product_bff,'read_authorized_statistics',lambda *args,**kwargs:
        (calls.append((args,kwargs)) or dict(status='READY',items=[],observed_count=0,matured_count=None)))
    code,response=bff._get_product('/api/v4/forward',{'trade_date':day,'context_token':context_key})
    assert code==200 and response['status']=='READY'
    assert response['data']['observed_count']==0 and len(calls)==1


def test_prepare_search_identity_uses_same_candidate_pg_identity_owner(tmp_path,monkeypatch):
    day='2026-10-12';source={'path':'missing/identity.jsonl.gz','sha256':'d'*64,'bytes':300}
    rows=[{'security_id':'SID-1','source_security_key':'SH.600000'}]
    authority={'contract_id':reference_pg.CONTRACT,'T0':day,'identity_source':source,
        'membership_snapshot':{'path':'snapshot.json','sha256':'e'*64,'bytes':120},
        'PIT_ELIGIBLE':False,'AS_RECORDED':False}
    candidate={'accepted_trade_date':day,'membership_snapshot':authority['membership_snapshot'],
        reference_pg.KEY:{'engine':'postgresql'}}
    appended=[];persisted={'contract_id':reference_pg.PG_AUTHORITY_CONTRACT,'engine':'postgresql'}
    monkeypatch.setattr(reference_pg,'_load_authority',lambda root,selected:authority)
    monkeypatch.setattr(reference_pg,'identity_source',lambda root,selected:source)
    monkeypatch.setattr(reference_pg,'read_identity',lambda root,selected:rows)
    monkeypatch.setattr(reference_pg,'append',lambda *args: (appended.append(args) or {'path':'pg-descriptor'}))
    monkeypatch.setattr(reference_pg,'read_fact',lambda *args:rows)
    monkeypatch.setattr(reference_pg,'_persist_authority',lambda root,value:persisted)

    result=reference_pg.prepare_search_identity(tmp_path,candidate)
    assert result['rows']==1
    assert appended[0][3:]==('reference_search_identity',source,rows)
    assert candidate[reference_pg.KEY] is persisted
    assert not (tmp_path/'data/v4/V4_DATA_ACCEPTED_HEAD.json').exists()


def test_prepare_search_identity_requires_pg_owner_instead_of_data_head_file(tmp_path):
    candidate={'accepted_trade_date':'2026-10-12','membership_snapshot':{},
        reference_pg.KEY:{'path':'untrusted.json','sha256':'f'*64,'bytes':12}}
    with pytest.raises(ValueError,match='PG_AUTHORITY_REQUIRED_NO_FILE_FALLBACK'):
        reference_pg.prepare_search_identity(tmp_path,candidate)
