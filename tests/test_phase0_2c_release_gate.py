import pytest
from validation.phase0_2c import REQUIRED, release_gate


def test_external_difference_does_not_block_verified_local_release():
    evidence = dict.fromkeys(REQUIRED, True)
    evidence['cross_vendor_exact_match'] = False
    result = release_gate(evidence)
    assert result['final_status'] == 'FULL_PASS_TDX_NATIVE'
    assert result['phase0_status'] == 'FULL_PASS'
    assert result['adjusted_dataset_allowed'] is True
    assert result['formal_trend_scanners_allowed'] is True
    assert result['next_allowed_phase'] == 'PHASE_1_NORMALIZATION_AND_FORMAL_FACTOR_ENGINE'


def test_proven_local_bug_revokes_permissions():
    result = release_gate(dict.fromkeys(REQUIRED, True), proven_local_systematic_bug=True)
    assert result['final_status'] == 'BLOCKED'
    assert result['adjusted_dataset_allowed'] is False
    assert result['formal_trend_scanners_allowed'] is False


@pytest.mark.parametrize('missing', REQUIRED)
def test_incomplete_evidence_cannot_silently_release(missing):
    evidence = dict.fromkeys(REQUIRED, True)
    del evidence[missing]
    with pytest.raises(ValueError, match=missing):
        release_gate(evidence)
