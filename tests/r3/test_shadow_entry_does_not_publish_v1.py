from pathlib import Path
def test_entry_targets_shadow_only():
 s=Path('run_shadow_v2.py').read_text('utf8');assert "data/shadow/v2" in s and 'publish_generation' not in s
