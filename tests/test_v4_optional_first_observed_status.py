"""New observed metadata bug: missing first capture cannot become produced."""
from workbench_analysis.producer_bootstrap_v1 import optional_step

def test_missing_first_observed_source_preserves_truthful_status():
    result=optional_step(lambda:dict(status='SOURCE_INCOMPLETE',formal_status='BLOCKED',observed_count=None,production_write_authorized=False))
    assert result['status']=='SOURCE_INCOMPLETE' and result['observed_count'] is None
    assert 'candidate' not in result and result['main_flow_blocked'] is False
