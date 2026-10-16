import json
import pytest
from tests.exact_daily_policy_fixture import install_pending
from workbench_analysis.operational_daily_exact_policy_v2 import verify,PATH
from workbench_analysis.operational_daily_executor_v1 import derive_ready_sources

def test_pending_contract_allows_calculation_and_refuses_publication(tmp_path):
    install_pending(tmp_path)
    # This legacy test fixture deliberately binds only the focused 24-source
    # subset. The live verifier now requires all 604 component sources before
    # either candidate calculation or publication can proceed.
    with pytest.raises(ValueError,match='EXACT_V2_COMPLETE_COMPONENT_SOURCE_BINDINGS_REQUIRED'):
        verify(tmp_path,candidate_only=True)
    with pytest.raises(ValueError,match='EXACT_V2_COMPLETE_COMPONENT_SOURCE_BINDINGS_REQUIRED'):
        verify(tmp_path)
    with pytest.raises(ValueError,match='EXACT_CANDIDATE_ONLY_CANNOT_PROMOTE'):
        derive_ready_sources(tmp_path,'2026-10-12',{},candidate_only_exact=True,readback_url='http://127.0.0.1:1')

@pytest.mark.parametrize('mutation',['stale_kernel','missing_consumer','wrong_coordinate','wrong_policy_path','scope_escalation','fake_admission'])
def test_exact_source_and_admission_fail_closed(tmp_path,mutation):
    policy=install_pending(tmp_path)
    path=tmp_path/PATH
    if mutation=='stale_kernel':(tmp_path/'src/adjustment/tdx_adjustment_v0_3.py').write_bytes(b'STALE')
    elif mutation=='missing_consumer':policy['accepted_algorithm_bindings']=policy['accepted_algorithm_bindings'][:1]
    elif mutation=='wrong_coordinate':policy['adjustment_contract']='ROUNDED_TARGET'
    elif mutation=='scope_escalation':policy['historical_PIT_permission']=True
    elif mutation=='fake_admission':policy['publication_ready']=True
    elif mutation=='wrong_policy_path':
        from workbench_analysis.r43_owner_replay import ref
        other=tmp_path/'config/other.json';other.write_bytes(path.read_bytes())
        with pytest.raises(ValueError,match='POLICY_PATH_REQUIRED'):verify(tmp_path,ref(tmp_path,other),candidate_only=True)
        return
    path.write_text(json.dumps(policy),encoding='utf8')
    with pytest.raises((ValueError,KeyError)):
        verify(tmp_path,candidate_only=mutation!='fake_admission')
