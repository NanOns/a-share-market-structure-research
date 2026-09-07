"""TDX-native release governance v0.3; no market-data or algorithm operations."""
IDENTITY = 'TDX_NATIVE_AFFINE_QFQ'
STATUS = 'VERIFIED_REPRODUCIBLE_TDX_NATIVE'
NEXT = 'PHASE_1_NORMALIZATION_AND_FORMAL_FACTOR_ENGINE'
REQUIRED = ('local_raw', 'gbbq', 'xrxd', 'affine', 'source_unchanged')


def release_gate(evidence, *, proven_local_systematic_bug=False):
    if proven_local_systematic_bug:
        return {'final_status': 'BLOCKED', 'formal_trend_scanners_allowed': False,
                'adjusted_dataset_allowed': False, 'next_allowed_phase': 'NONE'}
    # Missing/stale evidence is not a new scientific bug claim; refuse to issue a seal.
    missing = [key for key in REQUIRED if evidence.get(key) is not True]
    if missing:
        raise ValueError('Release evidence must be verified: ' + ', '.join(missing))
    return {'final_status': 'FULL_PASS_TDX_NATIVE', 'phase0_status': 'FULL_PASS',
            'project_price_basis': 'FORWARD_ADJUSTED', 'adjustment_identity': IDENTITY,
            'adjustment_status': STATUS, 'formal_trend_scanners_allowed': True,
            'adjusted_dataset_allowed': True, 'next_allowed_phase': NEXT}
