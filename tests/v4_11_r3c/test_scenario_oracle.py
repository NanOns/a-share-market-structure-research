from scripts.verify_v4_11_scenario_oracle_r3 import verify

def test_independent_literal_oracle_all_formal_scenarios():
    result=verify()
    assert result['status']=='PASS' and len(result['cases'])==8
    assert {(r['scenario'],r['case']) for r in result['cases']}=={(s,c) for s in ('LAUNCH_CONFIRM','RECOVERY_TURN') for c in ('TRUE','FALSE','BOUNDARY','UNKNOWN')}
