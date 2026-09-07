from common.identity import computation_identity
def test_shadow_excluded_from_v1_identity(tmp_path):
 a=computation_identity('.')['sha256'];tmp_path.joinpath('shadow.py').write_text('x');assert computation_identity('.')['sha256']==a
