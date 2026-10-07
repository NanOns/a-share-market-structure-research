"""Cached full protected runtime bytes/mtime scan, no live database connection."""
import sys
from scripts import forward_p1_fingerprint as f
from scripts.full_chain_repair_io import write
original=f.file_state
cache={}
def cached(path):
    if path not in cache:cache[path]=original(path)
    return cache[path]
if __name__=='__main__':
    side=sys.argv[1]
    if side not in ('BEFORE','AFTER'):raise ValueError('INVALID_SIDE')
    f.file_state=cached
    write('reports/forward_repair_r2_20261007/PROTECTED_FINGERPRINT_'+side+'.json',f.capture())
    write('reports/forward_repair_r2_20261007/ALL_RUNTIME_ROOTS_'+side+'.json',f.supplemental())
