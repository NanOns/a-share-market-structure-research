"""Apply only independently validated promotion and entry metadata."""
from scripts.v4_11_promotion_contract_r1 import *
from scripts.validate_v4_11_promotion_r1 import validate
from copy import deepcopy

def promote():
    before=validate()
    if before['status']!='PASS':raise ValueError('PROMOTION_VALIDATOR_MUST_PASS:'+str({k:v for k,v in before['checks'].items() if v=='FAIL'}))
    write(P+'V4_11_PROMOTION_VALIDATOR_R1.json',before)
    h=read(CANDIDATE);parent=read(ARCHIVE)
    if (ROOT/HEAD).exists():
        after=validate(post=True)
        if after['status']!='PASS':raise ValueError('IDEMPOTENT_POST_PROMOTION_REQUIRED')
        print('PASS_IDEMPOTENT_NO_MUTATION');return
    if read(GLOBAL)!=parent:raise ValueError('STALE_STAGE_PARENT_BEFORE_MUTATION')
    atomic(HEAD,(ROOT/CANDIDATE).read_bytes())
    surface=bound(h['entry_contract_surface'])
    entry=dict(contract_id='V4_12_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY_V1',stage='V4-12',stage_name='Structure / Anchor / Support',status='AUTHORIZED',scope='STAGE_ENTRY_ONLY_RUNTIME_NOT_IMPLEMENTED',accepted_parent=bind(HEAD),surface=h['entry_contract_surface'],upgrade=bind(UPGRADE),sections=surface['sections'],runtime_implemented=False,runtime_implementation_authorized=False,contract_completeness=surface['contract_completeness'],**PERMISSIONS)
    # Stage metadata and entry bytes are prepared together; the stage is advanced
    # before entry becomes a current authorized surface.
    entry_ref=dict(path=ENTRY,sha256=hashlib.sha256((json.dumps(entry,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8')).hexdigest(),bytes=len((json.dumps(entry,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8')))
    global_=deepcopy(parent);global_.update(accepted_stage_range='V4_00_TO_V4_11_ACCEPTED',version='2.5.0',v4_11_binding=bind(HEAD),v4_11_status=h['status'],v4_11_external_acceptance=DECISION,v4_11_capabilities=CAPABILITIES,v4_12_entry=dict(status='AUTHORIZED_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY_ONLY',binding=entry_ref),**PERMISSIONS)
    try:
        write(GLOBAL,global_,replace=True);write(ENTRY,entry)
        after=validate(post=True)
        if after['status']!='PASS':raise ValueError('POST_PROMOTION_READBACK_FAIL:'+str(after))
    except Exception:
        # Recover only this transaction's Stage Head; preserve independently
        # validated head and failed entry for audit instead of deleting evidence.
        atomic(GLOBAL,(ROOT/ARCHIVE).read_bytes());raise
    write(P+'V4_11_POST_PROMOTION_READBACK_R1.json',after)
    print('PASS_V4_11_PROMOTION_V4_12_STAGE_ENTRY_ONLY')

if __name__=='__main__':promote()
