"""A product gate cannot be replaced by test count or incomplete QA evidence."""
import pytest
from scripts.run_fp14_release_readiness import readiness

@pytest.mark.parametrize('qa',[{},dict(acceptance='DEGRADED_PASS',tests={'passed':10000}),dict(acceptance='PASS',product_complete=False,required_field_coverage_pass=True,edge_pass=True,offline_pass=True)])
def test_partial_or_empty_qa_blocks_release(qa):
    assert readiness(qa)

def test_complete_qa_gate_requires_all_product_and_browser_flags():
    qa=dict(acceptance='PASS',product_complete=True,required_field_coverage_pass=True,edge_pass=True,offline_pass=True)
    assert readiness(qa)==[]
    for key in ('product_complete','required_field_coverage_pass','edge_pass','offline_pass'):
        bad=dict(qa);bad.pop(key);assert readiness(bad)
