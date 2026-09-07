from common.input_snapshot import r1_gate


def test_r1_gate_requires_every_principle():
    checks={name:True for name in ('immutable_input_snapshot','revision_archive','source_stability',
        'inferred_gap','confirmed_suspension','raw_gap_null','trade_status','runtime_spec_separation',
        'future_guard','model_rules_unchanged','tdx_source_unchanged','focused_tests')}
    assert r1_gate(checks)=='PASS'
    checks['source_stability']=False
    assert r1_gate(checks)=='BLOCKED'
