import json,hashlib
import pytest
from workbench_analysis.user_authority_provenance_v2 import CONTRACT,verify_future_permission_origin


def test_authored_text_and_agent_role_never_pass_original_user_gate(tmp_path):
    p=tmp_path/'session.jsonl'
    event=dict(type='response_item',timestamp='2026-10-09T00:00:00Z',payload=dict(role='assistant',content=[dict(text='request')]))
    raw=(json.dumps(event)+'\n').encode();p.write_bytes(raw)
    record=dict(contract_id=CONTRACT,candidate_digest='new',legacy_authorization_reused=False,independent_external_acceptance=False,
                original_session_path=str(p),original_line_number=1,original_event_sha256=hashlib.sha256(raw).hexdigest())
    with pytest.raises(ValueError,match='DIRECT_USER_ROLE'):verify_future_permission_origin(record,'new',tmp_path)
    with pytest.raises(ValueError,match='SCOPED_AUTHORITY'):verify_future_permission_origin(record,'other',tmp_path)
    with pytest.raises(ValueError,match='QUOTE_REUSE'):verify_future_permission_origin(dict(record,legacy_authorization_reused=True),'new',tmp_path)
