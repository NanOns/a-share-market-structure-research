from phase1_runner import phase1_gate
from factors.registry import REGISTRY

def test_gate():
    assert phase1_gate({'source':True,'tests':False})=='BLOCKED'
    assert phase1_gate({'source':True},pending=1)=='PARTIAL_PASS'
    assert phase1_gate({'source':True})=='PASS'

def test_registry_complete():
    assert len(REGISTRY)==29
    required={'name','version','formula','window','min_samples','include_t','input_columns','price_basis','universe','calendar_basis','null_rule','nonpositive_rule','suspension_rule','output_unit'}
    assert all(required<=set(r) for r in REGISTRY)
