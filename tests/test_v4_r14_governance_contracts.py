"""Authorized promotion scope and contract-only negative gates."""
import pytest
from copy import deepcopy
from scripts.v4_12_promotion_r14 import read,OUT,HEAD,ROOT,promote,ref
from scripts.validate_v4_12_promotion_r14 import validate,check_head
from scripts.validate_v4_13_contract_r1 import validate as contracts,policy,witnesses
def test_exact_scoped_promotion():assert validate(post=True)['status']=='PASS'
@pytest.mark.parametrize('mutation',['permission','as_recorded','capability','round','binding','lineage'])
def test_promotion_fail_closed(mutation):
 h=deepcopy(read(HEAD))
 if mutation=='permission':h['production_permission']=True
 elif mutation=='as_recorded':h['AS_RECORDED']=True
 elif mutation=='capability':h['capabilities']['HISTORICAL_AS_RECORDED_D1']='PROVEN'
 elif mutation=='round':del h['round_bindings']['R8']
 elif mutation=='binding':h['contracts_runtime_validators_external_evidence'].pop()
 else:h['knowledge_lineage']='PIT_OBSERVED'
 with pytest.raises(AssertionError):check_head(h)
def test_zero_mutation_repeat():
 before={p.relative_to(ROOT).as_posix():ref(p.relative_to(ROOT).as_posix()) for d in ['reports/v4_12_promotion_r14','data/v4'] for p in (ROOT/d).glob('*.json')}
 promote()
 after={p.relative_to(ROOT).as_posix():ref(p.relative_to(ROOT).as_posix()) for d in ['reports/v4_12_promotion_r14','data/v4'] for p in (ROOT/d).glob('*.json')}
 assert before==after
@pytest.mark.parametrize('case',[dict(self_including=True),dict(ui_first=True),dict(membership_basis='CURRENT_MEMBERSHIP_REPLAY',pit=True),dict(context_writes_raw=True),dict(edge=['D1','B0','T']),dict(edge=['D2','D1','T']),dict(missing_as_false=True),dict(unknown_as_weak=True),dict(display_cap_changes_set=True),dict(recompute_structure=True)])
def test_forbidden_contract_use(case):
 with pytest.raises(AssertionError):policy(case)
def test_independent_vectors():assert len(witnesses())==12
def test_full_contract_completeness():
 result=contracts();assert result['status']=='PASS' and result['V4_13_RUNTIME']=='NOT_IMPLEMENTED'
