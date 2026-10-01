from copy import deepcopy
import pytest
from scripts.validate_v4_10_promotion_r1 import read,validate,CANDIDATE

def test_promotion_and_all_25_independent_checks():
    result=validate()
    assert result['status']=='PASS'
    assert len(result['checks'])==25

@pytest.mark.parametrize('field,value',[
    ('implementation_commit','wrong'),('audited_sealed_head','wrong'),
    ('external_acceptance_decision','wrong'),('production_permission',True),
    ('parent_binding',{}),('capabilities',{'FULL_D0_D1_D2_DAG':'ACCEPTED'}),
    ('open_audit_registry',{}),('global_head_parent_archive',{})])
def test_changed_authority_or_overclaim_rejected(field,value):
    h=deepcopy(read(CANDIDATE));h[field]=value
    assert validate(h)['status']=='FAIL'
