"""Compatibility entry for the R2 scoped formalization implementation.

The original R1 bytes are preserved in the explicit source-evidence archive.
"""
import json
from scripts.formalize_parallel_scoped_acceptance_r2 import prepare, readback

if __name__ == '__main__':
    prepare()
    print(json.dumps(dict(status=readback())))
