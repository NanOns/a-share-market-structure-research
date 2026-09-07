from validation.phase0_2b import root_gate

def test_mismatch_without_causal_evidence_is_inconclusive():
    assert root_gate() == 'EXTERNAL_SOURCE_INCONCLUSIVE'

def test_only_proven_causes_change_status():
    assert root_gate(provider_evidence=True) == 'EXTERNAL_PROVIDER_BASIS_DIFFERENCE'
    assert root_gate(local_bug=True) == 'LOCAL_ALGORITHM_BUG_UNRESOLVED'
    assert root_gate(local_bug=True,fixed=True) == 'LOCAL_ALGORITHM_BUG_FOUND_AND_FIXED'
