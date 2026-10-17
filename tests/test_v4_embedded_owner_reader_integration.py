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
    data=candidate(tmp_path);data[KEY]=prepare(tmp_path,data)[0]
    # This control exercises Reader IO only; full admission has separate real data evidence.
    monkeypatch.setattr(module,'validate',lambda root,data:True)
    reader=module.OperationalSuccessorReaderV1(tmp_path,data)
    assert reader.read('raw','2026-10-12',reader.token)['rows']==[dict(security_id='FIXTURE',amount=105.625)]
    assert reader.read('raw','2026-10-12',reader.token)['rows'][0]['amount']==105.625
    with pytest.raises(ValueError,match='CONTEXT_TOKEN_MISMATCH'):reader.read('raw','2026-10-12','a'*64)

def test_exact_reader_rejects_missing_embedded_authority_without_static_fallback(tmp_path,monkeypatch):
    from workbench_analysis import operational_successor_v1 as module
    monkeypatch.setattr(module,'validate',lambda root,data:True)
    with pytest.raises(ValueError,match='EMBEDDED_AUTHORITY_REQUIRED_NO_FALLBACK'):
        module.OperationalSuccessorReaderV1(tmp_path,candidate(tmp_path))

def test_successor_preparation_preserves_original_serialized_head_fact_token(tmp_path):
    from workbench_db.v4_operational_owner_pg_closeout import prepare as old_append,OWNER
    previous=candidate(tmp_path);head=tmp_path/'predecessor.json';atomic_json(tmp_path,head,previous)
    binding=ref(tmp_path,head);source=previous['owners']['2026-10-12']['raw']
    descriptor=old_append(tmp_path,binding['sha256'],'2026-10-12','raw',source,[dict(security_id='FIXTURE',amount=105.625)])
    authority=dict(contract_id=OWNER,head_token=binding['sha256'],source_owners=previous['owners'],
        owners={'2026-10-12':dict(raw=descriptor)},historical_PIT_permission=False,PIT_ELIGIBLE=False,AS_RECORDED=False)
    atomic_json(tmp_path,tmp_path/'config/v4_operational_owner_pg_closeout_r1.json',authority)
    successor=deepcopy(previous);successor.update(predecessor=binding,metadata='NEW_HEAD')
    legacy_binding={'path':'config/v4_operational_owner_pg_closeout_r1.json',
        'sha256':hashlib.sha256((tmp_path/'config/v4_operational_owner_pg_closeout_r1.json').read_bytes()).hexdigest(),
        'bytes':(tmp_path/'config/v4_operational_owner_pg_closeout_r1.json').stat().st_size}
    assert prepare_successor(tmp_path,successor,predecessor_authority_binding=legacy_binding)['counts']==dict(reused=1,created=0)
