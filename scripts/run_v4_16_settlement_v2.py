"""Settlement-only explicit daily invocation; cannot initialize/accept Shadow."""
import argparse
import json
from pathlib import Path
from scripts.v4_16_go_forward_shadow_runtime_r4r3 import SettlementObligationControllerR4R2,settlement_cycle

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--database',required=True)
    parser.add_argument('--daily-input-binding',required=True,help='Exact path/bytes/sha256 JSON; no implicit lookup')
    parser.add_argument('--boundary',required=True)
    parser.add_argument('--cutoff',required=True)
    parser.add_argument('--worker-id',required=True)
    args=parser.parse_args()
    controller=SettlementObligationControllerR4R2(args.root,args.database)
    db=controller.database(args.database)
    try:
        results=settlement_cycle(db,json.loads(args.daily_input_binding),args.boundary,args.cutoff,args.worker_id)
        print(json.dumps(dict(status='SETTLEMENT_CYCLE_COMPLETED',outcomes=results),ensure_ascii=False,allow_nan=False))
    finally:db.close()

if __name__=='__main__':main()
