"""Promotion rejects expanded scope, stale parents and disabled source gates."""
from copy import deepcopy
import pytest
from scripts import validate_v4_11_promotion_r1 as validator
from scripts.v4_11_promotion_contract_r1 import read,CANDIDATE,GLOBAL,HEAD,ROOT,bind

@pytest.mark.parametrize('change,expected_gate',[
    ({'production_permission':True},'P22_permissions_false'),
    ({'AS_RECORDED':True},'P24_historical_AS_RECORDED_not_overclaimed'),
    ({'implementation_commit':'UNTESTED'},'P03_implementation_commit_exact'),
    ({'capabilities':{'FULL_D0_D1_D2_DAG':'ENGINEERING_ACCEPTED'}},'P23_capability_map_exact'),
])
def test_promotion_rejects_unaccepted_expansion_read_only(change,expected_gate):
    before=bind(GLOBAL);head_before=bind(HEAD) if (ROOT/HEAD).exists() else None
    candidate=deepcopy(read(CANDIDATE));candidate.update(change)
    result=validator.validate(candidate)
    assert result['status']=='FAIL' and result['checks'][expected_gate]=='FAIL'
    assert bind(GLOBAL)==before
    assert (bind(HEAD) if (ROOT/HEAD).exists() else None)==head_before

def test_stale_global_parent_cannot_promote(monkeypatch):
    original=validator.read
    def stale(path):
        result=original(path)
        if path==GLOBAL:result['accepted_stage_range']='V4_00_TO_V4_09_ACCEPTED'
        return result
    monkeypatch.setattr(validator,'read',stale)
    assert validator.validate()['checks']['P27_idempotent_promotion_parent_preserved']=='FAIL'
