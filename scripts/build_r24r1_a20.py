"""Reuse the accepted A01–A20 scenarios against the explicit successor path."""
from pathlib import Path

def build():
    p=Path('tests/test_r24_activation.py').read_text().split('def positive(name=None):')[0]
    p=p.replace('scripts.r24_io','scripts.r24r1_io').replace('scripts.r24_simulation','scripts.r24r1_simulation')
    p=p.replace('scripts.v4_16_real_shadow_runtime','scripts.v4_16_go_forward_shadow_runtime').replace('scripts.validate_r24_activation','scripts.validate_r24r1_activation')
    p=p.replace("'A03':'AUTHORITY_EFFECTIVE_DATE_MISMATCH'","'A03':'EXACT_TARGET_DAILY_INPUT_REQUIRED'")
    p=p.replace("'A13':'PREVIOUS_SHADOW_SESSION_GAP'","'A13':'EXACT_TARGET_DAILY_INPUT_REQUIRED'")
    p=p.replace("('A02','A08','A09')","('A02','A08','A09','A10')")
    p=p.replace('2026-09-28','2026-10-08').replace('2026-09-24','2026-09-30').replace('2026-09-29','2026-10-09')
    Path('tests/test_r24r1_a20.py').write_text(p,encoding='utf8',newline='\n')

if __name__=='__main__':build()
