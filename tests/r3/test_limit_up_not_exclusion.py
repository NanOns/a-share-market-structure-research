from pathlib import Path
def test_limit_up_is_not_exclusion():
 assert 'LIMIT_UP_IS_NOT_AN_EXCLUSION=true' in Path('docs/V2_SHADOW_CONTRACT_V1.md').read_text('utf8')
