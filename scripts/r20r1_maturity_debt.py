"""Active entry point uses production DM01 integration.
Old R20R1/R20R1R1 receipts stay immutable; new increments use reports/r20r1r2.
"""
import json
from pathlib import Path
from scripts.r20r1r2_packet_validation import validate_packet
from scripts.r20r1r2_maturity_debt import refresh
if __name__=='__main__':
    import sys
    print(json.dumps(refresh(json.loads(Path(sys.argv[1]).read_text(encoding='utf8')) if len(sys.argv)>1 else [])))
