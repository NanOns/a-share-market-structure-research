"""Real frozen-source replay; engineering output only until successor admission."""
import argparse,json
from pathlib import Path
from workbench_analysis.operational_daily_executor_v1 import execute_sources
from workbench_analysis.operational_daily_owner_v1 import build

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--date',required=True);parser.add_argument('--current-replay',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    result=execute_sources(root,args.date,'CATCH_UP',capture_only=True)
    if result['status']!='SOURCE_CAPTURED':raise SystemExit(json.dumps(result))
    produced,context=build(root,result['source_freeze'],replay_current=args.current_replay)
    print(json.dumps(dict(status='REAL_OWNER_REPLAY_COMPLETE',folder=str(context['folder']))))
