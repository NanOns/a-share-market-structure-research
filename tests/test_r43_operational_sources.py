import json
from pathlib import Path
import pytest
from workbench_analysis.r43_operational_sources import checked,date_valid_identity
from workbench_analysis.r43_operational_publication import validate,POLICY

def test_source_hash_refuses_mutated_bytes(tmp_path):
    path=tmp_path/'source.json';path.write_text('{}')
    with pytest.raises(ValueError,match='SOURCE_DIGEST_MISMATCH'):
        checked(tmp_path,dict(path='source.json',sha256='0'*64))

def test_date_effective_identity_uses_exclusive_delist_boundary():
    identity=dict(security_id='SEC-test',list_date='2026-09-29',delist_date='2026-10-08')
    assert not date_valid_identity(identity,'2026-09-28')
    assert date_valid_identity(identity,'2026-09-29')
    assert date_valid_identity(identity,'2026-09-30')
    assert not date_valid_identity(identity,'2026-10-08')
    assert not date_valid_identity(dict(identity,security_id=None),'2026-09-30')

@pytest.mark.parametrize('change,error',[
    ({'historical_PIT_permission':True},'PIT_ESCALATION'),
    ({'AS_RECORDED':True},'PIT_ESCALATION'),
    ({'taxonomy':'BAO_CSRC'},'TDX_LATEST_PRIMARY'),
    ({'dates':['2026-10-09']},'FOUR_SESSION_DATE'),
])
def test_operational_type_rejection(tmp_path,change,error):
    c=dict(contract_id=POLICY,dates=['2026-09-28','2026-09-29','2026-09-30','2026-10-08'],AS_RECORDED=False,historical_PIT_permission=False,taxonomy='TDX_INDUSTRY_CONCEPT',membership_mode='TDX_LATEST_MEMBER_RETRO_V1')
    c.update(change)
    with pytest.raises(ValueError,match=error):validate(tmp_path,c)
