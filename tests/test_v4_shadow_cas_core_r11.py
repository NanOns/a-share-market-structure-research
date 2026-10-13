import json
import pytest
from workbench_analysis.operational_successor_release_v1 import _commit_pointers
from workbench_analysis.operational_successor_v1 import digest

@pytest.mark.parametrize('fail',[False,True])
def test_shared_cas_exact_rollback_and_token(tmp_path,fail):
    root=tmp_path;head=root/'head.json';archive=root/'old.json';tx=root/'tx.json';joint=root/'joint.json'
    before=b'{"accepted_trade_date":"2026-10-12"}';head.write_bytes(before);archive.write_bytes(before)
    candidate={'accepted_trade_date':'2026-10-13'}
    def readback(value):
        assert json.loads(head.read_bytes())==candidate
        if fail:raise ValueError('HTTP_FAILED')
        return dict(status='PASS',accepted_trade_date='2026-10-13',context_token=digest(value))
    if fail:
        with pytest.raises(ValueError,match='HTTP_FAILED'):_commit_pointers(root,head,joint,tx,candidate,before,archive,{},None,None,readback)
        assert head.read_bytes()==before and json.loads(tx.read_bytes())['state']=='ROLLED_BACK'
    else:
        result=_commit_pointers(root,head,joint,tx,candidate,before,archive,{},None,None,readback)
        assert result['context_token']==digest(candidate) and json.loads(tx.read_bytes())['state']=='COMMITTED'
    assert not joint.exists()
