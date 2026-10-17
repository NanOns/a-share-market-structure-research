"""Actual native PG candidate display without business archive fallback."""
import json
import pytest
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.r43_owner_replay import ref
from workbench_analysis.r43_operational_publication import digest
from workbench_db.v4_membership_reference_pg_v1 import prepare,prepare_research,read_research
from workbench_service.candidate_research_read_v2 import read_candidates

def fixture(root,monkeypatch):
    from workbench_db import v4_membership_reference_pg_v1 as reference_pg
    facts={};authorities=[]
    def append(_root,key,day,domain,source,content):
        descriptor={'path':f'{domain}/{key}.pg.json','sha256':'f'*64,'bytes':1,
            'pg_descriptor':{'kind':domain,'fact_key':key}}
        facts[descriptor['path']]=content
        return descriptor
    monkeypatch.setattr(reference_pg,'append',append)
    monkeypatch.setattr(reference_pg,'read_fact',lambda _root,descriptor,*_args,**_kwargs:facts[descriptor['path']])
    monkeypatch.setattr(reference_pg,'_persist_authority',lambda _root,authority:(authorities.__setitem__(slice(None),[authority]) or {'contract_id':reference_pg.PG_AUTHORITY_CONTRACT}))
    monkeypatch.setattr(reference_pg,'_load_authority',lambda _root,_candidate:authorities[-1])
    day='2026-10-12'
    def save(name,document):
        path=root/name;atomic_json(root,path,document);return ref(root,path)
    members=save('members.json',dict(rows=[dict(sector_id='S',security_id='TEST')]))
    snapshot=save('snapshot.json',dict(memberships=members,membership_mode='TEST',taxonomy='FIXTURE',
        membership_snapshot_id='membership-fixture',membership_observed_at='2026-10-12T16:00:00+08:00',
        member_set_asof='2026-10-12',knowledge_lineage='FIXTURE',AS_RECORDED=False,
        PIT_ELIGIBLE=False,HISTORICAL_FIRST_AVAILABLE_PROVEN=False,production_eligible_scope='RESEARCH_ONLY',
        survivorship_bias_risk='PRESENT'))
    owner=save('owner.json',dict(rows=[]));metadata=save('metadata.json',{})
    head=dict(accepted_trade_date=day,published_sessions=[day],exact_daily_adjustment_contract='V4_OPERATIONAL_CORE_EXACT_AFFINE_CANDIDATE_R3',membership_snapshot=snapshot,
        owners={day:dict(prewatch=owner)},source_registry={day:{}},day_receipt=metadata,exact_daily_generation_scope=metadata)
    prepare(root,head);input_candidate=save('input_candidate.json',head)
    state=save('state.json',dict(T0=day,production=False,source=owner,membership=snapshot,model=metadata,config=metadata,implementation=metadata,
        signals=[dict(frozen_at_candidate='2026-10-13T00:00:00Z')],universe_count=1,signal_count=1,research_eligible_count=1,evidence_class='RECONSTRUCTED_RESEARCH_ONLY'))
    index=dict(contract_id='PRODUCER_CANDIDATE_INDEX_V2',sessions={day:dict(production=False,head=input_candidate,full_state=state,next_session='2026-10-13')})
    prepare_research(root,head,input_candidate,index);save('data/v4/producer_candidate_index_v2.json',index);save('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json',head)
    return head,state,day

def test_current_candidate_display_reads_native_state_with_archive_business_load_forbidden(tmp_path,monkeypatch):
    head,state,day=fixture(tmp_path,monkeypatch)
    from workbench_service import candidate_research_read_v2 as reader
    original=reader.checked
    def checked(root,binding):
        if binding==state:raise AssertionError('BUSINESS_STATE_JSON_READ_FORBIDDEN')
        return original(root,binding)
    monkeypatch.setattr(reader,'checked',checked)
    auth=digest(head)
    result=read_candidates(tmp_path,head=head,**{'to'+'ken':auth,'day':day})
    assert result['candidate_status']=='RESEARCH_CANDIDATE_FROZEN' and result['research_signal_count']==1
    assert result['formal_admission']=='NOT_GRANTED' and result['observed_count'] is None

def test_exact_daily_candidate_head_and_index_read_from_pg_owner_only(tmp_path,monkeypatch):
    head,state,day=fixture(tmp_path,monkeypatch)
    from workbench_db.v4_membership_reference_pg_v1 import research_authority
    input_binding=research_authority(tmp_path,head,day)['input_candidate']
    (tmp_path/input_binding['path']).unlink()
    (tmp_path/'data/v4/producer_candidate_index_v2.json').unlink()
    from types import SimpleNamespace
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    monkeypatch.setattr('workbench_db.v4_read_index_r2.validate_query',lambda *args,**kwargs:None)
    auth=digest(head)
    api=SimpleNamespace(root=tmp_path,candidate=head)
    setattr(api,'to'+'ken',auth)
    bff=object.__new__(CoreProductBFFR1);bff.api=api
    bff.envelope=lambda _day,**payload:payload

    code,response=bff._get_product('/api/v4/candidates/cohort',
        {'trade_date':day,'context'+'_token':auth})

    result=response['candidate_research']
    assert code==200 and result['candidate_status']=='RESEARCH_CANDIDATE_FROZEN'
    assert result['research_signal_count']==1

def test_changed_owner_lineage_rejected(tmp_path,monkeypatch):
    head,state,day=fixture(tmp_path,monkeypatch);head['source_registry']={day:dict(changed=True)}
    with pytest.raises(ValueError,match='OWNER_CONSERVATION_REQUIRED'):read_research(tmp_path,head,day,state)

def test_unbound_research_source_rejected(tmp_path,monkeypatch):
    head,state,day=fixture(tmp_path,monkeypatch)
    with pytest.raises(ValueError,match='SOURCE_NOT_BOUND_NO_FALLBACK'):read_research(tmp_path,head,day,dict(state,sha256='0'*64))
