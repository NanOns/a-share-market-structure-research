from validation.phase0_2b import Budget, EvidenceClient, FrozenRun, connectivity_status

def test_gate_a_cap_and_provider_shared_modes():
    b = Budget()
    assert all(b.take('EASTMONEY', True) for _ in range(12))
    assert not b.take('EASTMONEY', True)
    assert all(b.take('EASTMONEY') for _ in range(18))
    assert not b.take('EASTMONEY')

def test_three_failures_across_logical_queries_and_immediate_http_block():
    b = Budget()
    for _ in range(3):
        assert b.take('TENCENT')
        b.result('TENCENT', False)
    assert not b.take('TENCENT')
    b.result('EASTMONEY', False, 429)
    assert not b.take('EASTMONEY')

def test_success_resets_failure_counter_and_total_limit():
    b = Budget()
    b.result('TENCENT', False)
    b.result('TENCENT', True)
    assert b.failures['TENCENT'] == 0
    for source, n in [('EASTMONEY',30),('TENCENT',30),('OTHER',20)]:
        assert all(b.take(source) for _ in range(n))
    assert not b.take('OTHER')

def test_resume_preserves_circuit(tmp_path):
    prior = [dict(source='TENCENT', success=False, http_status=None) for _ in range(3)]
    client = EvidenceClient(FrozenRun(tmp_path/'runs', tmp_path/'tdx'), prior)
    assert client.get('TENCENT','https://invalid.test',{}) is None
    assert not client.audit

def test_connectivity_distinguishes_transport_and_parameters():
    assert connectivity_status([{'http_status':None}],False,False) == 'EASTMONEY_ENV_NETWORK_BLOCKED'
    assert connectivity_status([{'http_status':403}],False,False) == 'EASTMONEY_HTTP_BLOCKED'
    assert connectivity_status([{'http_status':200,'api_code':1}],False,False) == 'EASTMONEY_PARAM_ERROR'
