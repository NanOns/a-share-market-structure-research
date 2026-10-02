"""R15 contract witnesses; no production/runtime helper computes expected."""
from copy import deepcopy
import pytest
from scripts.validate_v4_13_r1_1 import load_bundle,audit_bundle,vector_actual,negatives,prove_membership_scope,EXPECTED_PAIRS,validate
B=load_bundle()
@pytest.mark.parametrize('vector',B['machine_vectors']['vectors'],ids=lambda v:v['id'])
def test_independent_vector(vector):
    assert vector_actual(vector,B)==vector['expected']
@pytest.mark.parametrize('key,expected',list(EXPECTED_PAIRS.items()))
def test_literal_quality_oracle(key,expected):
    assert B['quality_map']['component_pair_table'][key]==expected
@pytest.mark.parametrize('key',['provider_direct_read','raw_fallback','formal_consumers_flag_override','current_membership_replay_claimed_pit'])
def test_membership_route_fail_closed(key):
    route=deepcopy(B['membership_consumer_route']);route[key]=True
    assert prove_membership_scope(route)['status']=='BLOCKED_MEMBERSHIP_CONSUMER_SCOPE'
def test_negative_contracts():
    assert len(negatives(B))==15
    assert all(p['result']=='REJECTED' for p in negatives(B))
def test_full_contract_completeness_and_protected_artifacts():
    result=validate()
    assert len(result['completeness_matrix'])==17
    assert all(p['unchanged'] for p in result['protected'])
    assert result['V4_13_RUNTIME']=='NOT_IMPLEMENTED'
