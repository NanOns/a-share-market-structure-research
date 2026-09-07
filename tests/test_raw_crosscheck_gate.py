from validation.phase0_2b import raw_gate, classify, FIELDS

def test_mismatching_raw_blocks_algorithm_inference():
    gate = raw_gate(dict.fromkeys(FIELDS, 10), dict.fromkeys(FIELDS, 10.01))
    assert gate['raw_match'] is False
    assert classify(1, 0, {}, gate) == 'RAW_BASIS_DIFFERENCE'

def test_missing_is_not_false_match():
    assert raw_gate({}, None)['raw_match'] is None

def test_equal_decimal_representations_match():
    assert raw_gate(dict.fromkeys(FIELDS, '10.00'), dict.fromkeys(FIELDS, '10.000'))['raw_match']
