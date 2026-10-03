"""Compatibility entry point for the versioned R20R1R1 debt repair.
Old R20R1 receipts stay immutable; new increments use reports/r20r1r1.
"""
import json
from pathlib import Path
from scripts.r20r1r1_packet_validation import validate_packet
from scripts.r20r1r1_maturity_debt import refresh
if __name__=='__main__':
    import sys
    print(json.dumps(refresh(json.loads(Path(sys.argv[1]).read_text(encoding='utf8')) if len(sys.argv)>1 else [])))
