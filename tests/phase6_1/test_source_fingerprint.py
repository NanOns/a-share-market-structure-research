from pathlib import Path
from production.daily import source_fingerprint
def test_real_fingerprint_components():
 x=source_fingerprint(Path('.'),Path('D:/new_tdx'),'20260904');assert x['source_fingerprint_version']=='production-source-fingerprint-v1.1-full-content' and {'day','gbbq','gbbq_map','tdxhy','tdxzs','infoharbor_block','sh_tnf','sz_tnf','bj_tnf','master_calendar'}<=set(x['source_fingerprint_components'])
