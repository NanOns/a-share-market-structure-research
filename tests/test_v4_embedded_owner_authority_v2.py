"""Small real-PG engineering controls, never source or publication acceptance."""
import json
from copy import deepcopy
import pytest
from workbench_db.v4_operational_owner_authority_v2 import prepare,load,read,validate,KEY
from workbench_analysis.r43_owner_replay import ref
from workbench_db.v4_forward_pg_r1 import canonical,digest

def input_candidate(root):
    path=root/'source.json';path.write_text(json.dumps(dict(rows=[dict(security_id='ENGINEERING',amount=105.625,close=12.34)])))
    return dict(owners={'2026-10-12':{'raw':ref(root,path)}})

def test_exact_pg_payload_reuses_source_identity_across_head_metadata(tmp_path):
    candidate=input_candidate(tmp_path)
    binding,receipt=prepare(tmp_path,candidate)
    assert receipt['counts']==dict(reused=0,created=1) and receipt['publication'] is False
    candidate[KEY]=binding
    authority=load(tmp_path,candidate)
    assert read(tmp_path,authority,'2026-10-12','raw',candidate['owners']['2026-10-12']['raw'])==[dict(security_id='ENGINEERING',amount=105.625,close=12.34)]
    successor=deepcopy(candidate);successor['head_metadata']='NEW_CURRENT_HEAD'
    reused,reuse_receipt=prepare(tmp_path,successor,authority)
    assert reused==binding and reuse_receipt['counts']==dict(reused=1,created=0)
    assert digest(canonical(candidate))!=digest(canonical(successor))

@pytest.mark.parametrize('mutation',['source','digest','dates','domains','pit','token_shape'])
def test_embedded_authority_rejects_mismatched_metadata(tmp_path,mutation):
    candidate=input_candidate(tmp_path);binding,_=prepare(tmp_path,candidate)
    candidate[KEY]=binding;authority=load(tmp_path,candidate)
    if mutation=='source':authority['source_owners']={}
    elif mutation=='digest':authority['owner_source_digest']='different'
    elif mutation=='dates':authority['owners']={}
    elif mutation=='domains':authority['owners']['2026-10-12']={}
    elif mutation=='pit':authority['PIT_ELIGIBLE']=True
    else:authority['owners']['2026-10-12']['raw']['fact_token']='wrong'
    with pytest.raises(ValueError):validate(candidate,authority)

def test_real_pg_fact_token_rejected_and_no_archive_fallback(tmp_path):
    candidate=input_candidate(tmp_path);binding,_=prepare(tmp_path,candidate)
    candidate[KEY]=binding;authority=load(tmp_path,candidate)
    authority['owners']['2026-10-12']['raw']['fact_token']='a'*64
    with pytest.raises(ValueError,match='PG_OPERATIONAL_OWNER_CONTEXT_MISMATCH'):
        read(tmp_path,authority,'2026-10-12','raw',candidate['owners']['2026-10-12']['raw'])

def test_original_head_bound_fact_is_reused_without_rebinding_payload(tmp_path):
    from workbench_db.v4_operational_owner_pg_closeout import prepare as old_append,OWNER
    candidate=input_candidate(tmp_path);source=candidate['owners']['2026-10-12']['raw'];old_token='b'*64
    descriptor=old_append(tmp_path,old_token,'2026-10-12','raw',source,[dict(security_id='ENGINEERING',amount=105.625,close=12.34)])
    from workbench_db.v4_operational_owner_pg_closeout import read as old_read
    with pytest.raises(ValueError,match='PG_OPERATIONAL_OWNER_CONTEXT_MISMATCH'):
        old_read(tmp_path,descriptor,digest(canonical(candidate)),'2026-10-12','raw',source)
    predecessor=dict(contract_id=OWNER,head_token=old_token,source_owners=candidate['owners'],owners={'2026-10-12':{'raw':descriptor}})
    binding,receipt=prepare(tmp_path,candidate,predecessor)
    candidate[KEY]=binding;authority=load(tmp_path,candidate)
    assert receipt['counts']==dict(reused=1,created=0)
    assert authority['owners']['2026-10-12']['raw']==dict(descriptor=descriptor,fact_token=old_token)
    assert read(tmp_path,authority,'2026-10-12','raw',source)[0]['amount']==105.625
