"""Versioned capability reporting admission; does not evaluate settlement formulas."""
DENIED='NOT_GRANTED_PENDING_MATURITY_EVIDENCE'
def admit_matured_claim(claim,evidence):
    if claim==DENIED:return True
    if claim!='PASS':raise ValueError('UNKNOWN_MATURITY_CLAIM')
    if evidence.get('accepted_future_endpoint_read_count',0)<=0 or not evidence.get('outcomes') or all(x.get('outcome_status')=='PENDING' for x in evidence['outcomes']):raise ValueError('PENDING_OR_ZERO_REAL_FUTURE_READS')
    if evidence.get('evidence_class')!='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED' or evidence.get('cohort_namespace')!='REALTIME_ACCEPTED':raise ValueError('ENGINEERING_SYNTHETIC_RECONSTRUCTED_NOT_REAL_MATURITY')
    if evidence.get('raw_provider_fallback') is not False or evidence.get('historical_prices_only') is not False:raise ValueError('NO_PROVIDER_OR_PRICE_ONLY_LINEAGE')
    if evidence.get('T0_freeze_before_future_read') is not True:raise ValueError('T0_BEFORE_ENDPOINT_REQUIRED')
    # Admission requires a separately independently verified exact proof, never a caller's boolean.
    if evidence.get('independent_exact_maturity_proof') is not True:raise ValueError('EXACT_BOUND_INDEPENDENT_PROOF_REQUIRED')
    raise ValueError('NEW_REAL_MATURITY_GATE_REQUIRED_CURRENT_R20R1_DOES_NOT_GRANT')
def assert_scope(gate,evidence):
    admit_matured_claim(gate['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT'],evidence)
    if gate.get('HISTORICAL_PIT_EFFECTIVENESS')!='NOT_GRANTED':raise ValueError('HISTORICAL_PIT_NEVER_UPGRADED')
    for k in ['Production','Shadow','Focus','V4_16']:
        if gate.get(k) is not False:raise ValueError('NO_OPERATIONAL_PERMISSION')
    if gate.get('V4_15_ACCEPTED_HEAD')!='NOT_CREATED':raise ValueError('NO_V4_15_ACCEPTANCE')
    return True
