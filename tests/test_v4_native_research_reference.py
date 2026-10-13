"""Actual native PG candidate display without business archive fallback."""
import json
import pytest
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.r43_owner_replay import ref
from workbench_analysis.r43_operational_publication import digest
from workbench_db.v4_membership_reference_pg_v1 import prepare,prepare_research,read_research
from workbench_service.candidate_research_read_v2 import read_candidates

def fixture(root):
    day='2026-10-12'
    def save(name,document):
        path=root/name;atomic_json(root,path,document);return ref(root,path)
    members=save('members.json',dict(rows=[dict(sector_id='S',security_id='TEST')]))
    snapshot=save('snapshot.json',dict(memberships=members))
    owner=save('owner.json',dict(rows=[]));metadata=save('metadata.json',{})
    head=dict(accepted_trade_date=day,exact_daily_adjustment_contract='V4_OPERATIONAL_CORE_EXACT_AFFINE_CANDIDATE_R3',membership_snapshot=snapshot,
        owners={day:dict(prewatch=owner)},source_registry={day:{}},day_receipt=metadata,exact_daily_generation_scope=metadata)
    prepare(root,head);input_candidate=save('input_candidate.json',head)
    state=save('state.json',dict(T0=day,production=False,source=owner,membership=snapshot,model=metadata,config=metadata,implementation=metadata,
        signals=[dict(frozen_at_candidate='2026-10-13T00:00:00Z')],universe_count=1,signal_count=1,research_eligible_count=1,evidence_class='RECONSTRUCTED_RESEARCH_ONLY'))
    index=dict(contract_id='PRODUCER_CANDIDATE_INDEX_V2',sessions={day:dict(production=False,head=input_candidate,full_state=state,next_session='2026-10-13')})
    prepare_research(root,head,input_candidate,index);save('data/v4/producer_candidate_index_v2.json',index);save('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json',head)
    return head,state,day

def test_current_candidate_display_reads_native_state_with_archive_business_load_forbidden(tmp_path,monkeypatch):
    head,state,day=fixture(tmp_path)
    from workbench_service import candidate_research_read_v2 as reader
    original=reader.checked
    def checked(root,binding):
        if binding==state:raise AssertionError('BUSINESS_STATE_JSON_READ_FORBIDDEN')
        return original(root,binding)
    monkeypatch.setattr(reader,'checked',checked)
    result=read_candidates(tmp_path,head=head,token=digest(head),day=day)
    assert result['candidate_status']=='RESEARCH_CANDIDATE_FROZEN' and result['research_signal_count']==1
    assert result['formal_admission']=='NOT_GRANTED' and result['observed_count'] is None

def test_changed_owner_lineage_rejected(tmp_path):
    head,state,day=fixture(tmp_path);head['source_registry']={day:dict(changed=True)}
    with pytest.raises(ValueError,match='OWNER_CONSERVATION_REQUIRED'):read_research(tmp_path,head,day,state)

def test_unbound_research_source_rejected(tmp_path):
    head,state,day=fixture(tmp_path)
    with pytest.raises(ValueError,match='SOURCE_NOT_BOUND_NO_FALLBACK'):read_research(tmp_path,head,day,dict(state,sha256='0'*64))
