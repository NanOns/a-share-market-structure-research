from validation.external_qfq import decide_phase0_2a_gate


def test_unrelated_source_conflict_cannot_hide_contract_sample_failure():
    assert decide_phase0_2a_gate(
        sample_passed=4, sample_failed=1, sample_unverifiable=0, sample_count=5,
        security_count=32, verified_points=120, match_ratio=0.99,
        complex_types_pass=True, systematic_mismatch=False,
        external_disagreement_count=1,
    ) == 'BLOCKED_FOR_FORMAL_ADJUSTMENT'


def test_full_gate_requires_all_deterministic_contract_samples_and_batch_evidence() -> None:
    assert decide_phase0_2a_gate(
        sample_passed=5,
        sample_failed=0,
        sample_unverifiable=0,
        sample_count=5,
        security_count=30,
        verified_points=100,
        match_ratio=0.99,
        complex_types_pass=True,
        systematic_mismatch=False,
        external_disagreement_count=0,
    ) == "FULL_PASS"


def test_external_disagreement_remains_degraded() -> None:
    assert decide_phase0_2a_gate(
        sample_passed=4,
        sample_failed=0,
        sample_unverifiable=0,
        sample_count=5,
        security_count=30,
        verified_points=100,
        match_ratio=0.99,
        complex_types_pass=True,
        systematic_mismatch=False,
        external_disagreement_count=1,
    ) == "DEGRADED_PASS"


def test_systematic_sample_mismatch_blocks_formal_adjustment() -> None:
    assert decide_phase0_2a_gate(
        sample_passed=2,
        sample_failed=3,
        sample_unverifiable=0,
        sample_count=5,
        security_count=30,
        verified_points=100,
        match_ratio=0.80,
        complex_types_pass=False,
        systematic_mismatch=True,
        external_disagreement_count=0,
    ) == "BLOCKED_FOR_FORMAL_ADJUSTMENT"
