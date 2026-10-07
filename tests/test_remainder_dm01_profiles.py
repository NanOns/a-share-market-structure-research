import pytest
from workbench_analysis import dm01_runtime_r4 as r
from tests.runtime_isolation import create

def test_current_accepted_runtime_has_no_legacy_pending_error():
    assert r.accepted_envelope(r.ROOT)['status']=='EXTERNALLY_ACCEPTED_DM01_R4_RUNTIME'
    assert r.session_gate('2026-10-08','2026-10-08T09:00:00+00:00')['status']=='SOURCE_CAPTURE_ALLOWED'

def test_historical_missing_and_unaccepted_authority_fail_closed(tmp_path):
    root=create(tmp_path/'historical')
    with pytest.raises(ValueError,match='PENDING_DM01_R4_EXTERNAL_ACCEPTANCE'):r.accepted_envelope(root)
    path=root/r.ACCEPTANCE;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'{"status":"UNACCEPTED"}')
    with pytest.raises(ValueError,match='R4_ENVELOPE_NOT_ACCEPTED'):r.accepted_envelope(root)
