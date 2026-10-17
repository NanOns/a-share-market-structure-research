import json
from pathlib import Path

import pytest

from workbench_service.current_v4_context import canonical, digest, SourceInvalid
from workbench_service import v4_daily_refresh


def test_candidate_validation_appends_pg_fact_without_workspace_authority(tmp_path, monkeypatch):
    root=tmp_path
    candidate=root/'candidate.json'
    raw=canonical(dict(contract_id='V4_CURRENT_ACCEPTED_READ_CONTRACT_V1',version='1.0.0'))
    candidate.write_bytes(raw)
    authority=root/v4_daily_refresh.AUTHORITY
    authority.parent.mkdir(parents=True)
    authority.write_text('{"old":"authority"}',encoding='utf8')
    authority_before=authority.read_bytes()
    archive=root/'data/v4/production_views'
    ingested=[];stored={}

    def admit_bound(_root,binding):
        ingested.append(binding)
        return {'raw':raw}

    class Reader:
        def __init__(self,*_args,**_kwargs):pass
        def load_context(self):
            return {'context':{'accepted_trade_date':'2026-09-30'},'context_token':'ctx'}
        def read(self,module):
            return 200,{'module':module}

    class Store:
        def __init__(self,*_args):pass
        def append(self,kind,key,value):
            stored.update(kind=kind,key=key,value=value)
            return {'descriptor':'pg-candidate'}
        def read(self,_descriptor):return stored['value']

    monkeypatch.setattr('workbench_db.v4_historical_source_ingress_pg_r1.admit_bound',admit_bound)
    monkeypatch.setattr('workbench_db.v4_historical_source_ingress_pg_r1.source_id_for_path',lambda _path:'source-id')
    monkeypatch.setattr(v4_daily_refresh,'CurrentAcceptedV4Reader',Reader)
    monkeypatch.setattr('workbench_db.v4_forward_pg_r1.ForwardFactStore',Store)

    result=v4_daily_refresh.validate_current_view_candidate(root,'candidate.json')

    assert result['status']=='VALIDATED_CANDIDATE_PENDING_PUBLICATION'
    assert result['accepted_head_changed'] is False
    assert result['workspace_authority_changed'] is False
    assert ingested==[dict(path='candidate.json',sha256=digest(raw),bytes=len(raw))]
    assert stored['kind']=='validated_candidate'
    assert stored['value']['acceptance']=='NOT_REQUESTED_NO_HEAD_CAS'
    assert authority.read_bytes()==authority_before
    assert not archive.exists()


def test_module_gate_failure_does_not_append_candidate(tmp_path, monkeypatch):
    candidate=tmp_path/'candidate.json'
    raw=canonical(dict(contract_id='V4_CURRENT_ACCEPTED_READ_CONTRACT_V1',version='1.0.0'))
    candidate.write_bytes(raw)

    monkeypatch.setattr('workbench_db.v4_historical_source_ingress_pg_r1.admit_bound',lambda *_args:{'raw':raw})
    monkeypatch.setattr('workbench_db.v4_historical_source_ingress_pg_r1.source_id_for_path',lambda _path:'source-id')

    class Reader:
        def __init__(self,*_args,**_kwargs):pass
        def load_context(self):return {'context':{'accepted_trade_date':'2026-09-30'},'context_token':'ctx'}
        def read(self,module):return (409,{'reason':'owner missing'}) if module=='sector' else (200,{})

    class Store:
        def __init__(self,*_args):pass
        def append(self,*_args):pytest.fail('candidate must not be recorded before all module gates pass')

    monkeypatch.setattr(v4_daily_refresh,'CurrentAcceptedV4Reader',Reader)
    monkeypatch.setattr('workbench_db.v4_forward_pg_r1.ForwardFactStore',Store)
    with pytest.raises(SourceInvalid,match='CANDIDATE_OWNER_GATE:sector'):
        v4_daily_refresh.validate_current_view_candidate(tmp_path,'candidate.json')
