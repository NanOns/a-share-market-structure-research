from shadow_v2.diagnostics import shadow_identity
def test_identity_binds_baseline():assert shadow_identity({'x':'1'},{'run_id':'v1'})['version']=='shadow-computation-identity-v1.0'
