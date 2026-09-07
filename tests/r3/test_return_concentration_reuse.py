from pathlib import Path
def test_reused_not_redefined():
 s=Path('run_shadow_v2.py').read_text('utf8');assert "factors[['security_id','RETURN_CONCENTRATION_20'" in s
