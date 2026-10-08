"""Build or inspect a versioned research snapshot; source inputs stay read only."""
import argparse
import json
import sys
import os
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from workbench_service.production_v4 import build_snapshot, ProductionV4ResearchReader, reference,rollback_snapshot,POINTER
from workbench_service.current_v4_context import digest
from workbench_service.v4_daily_refresh import atomic_bytes, refresh_status

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--daily',action='store_true');parser.add_argument('--rollback');args=parser.parse_args()
    before=(ROOT/POINTER).read_bytes() if (ROOT/POINTER).exists() else None
    try:return execute(args)
    except (ValueError,OSError,KeyError,subprocess.TimeoutExpired) as error:
        after=(ROOT/POINTER).read_bytes() if (ROOT/POINTER).exists() else None
        result=dict(status='BLOCKED_REFRESH_OR_BUILD',reason=str(error),pointer_preserved=before==after)
        atomic_bytes(ROOT/'runtime/research_daily/FAILED_RECEIPT.json',(json.dumps(result,ensure_ascii=False)+'\n').encode())
        print(json.dumps(result,ensure_ascii=False));return 2

def execute(args):
    status=refresh_status(ROOT)
    if args.rollback:result=rollback_snapshot(ROOT,args.rollback)
    elif args.daily and ProductionV4ResearchReader(ROOT).context['accepted_trade_date'] != status['context']['context']['accepted_trade_date']:
        result=build_snapshot(ROOT)
    elif args.daily and not status['next_completed_session']:
        result=dict(status='NO_NEW_COMPLETED_SESSION',last_successful_date=status['context']['context']['accepted_trade_date'],source_requests=0,pointer_preserved=True)
    elif args.daily:
        env=dict(os.environ,PYTHONPATH=str(ROOT/'src')+os.pathsep+str(ROOT))
        run=subprocess.run([sys.executable,'-B','-m','scripts.run_v4_current_daily'],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf8',timeout=900)
        if run.returncode==0:result=build_snapshot(ROOT)
        else:result=dict(status='BLOCKED_SOURCE_OR_OWNER_QA',next_session=status['next_completed_session'],pipeline_exit_code=run.returncode,pipeline_output=run.stdout[-4000:],pointer_preserved=True)
    else:result=build_snapshot(ROOT)
    if not result['status'].startswith('BLOCKED'):
        from workbench_service.pit_observation import freeze
        result['first_observed_freeze']=freeze(ProductionV4ResearchReader(ROOT))
    atomic_bytes(ROOT/('runtime/research_daily/DAILY_LATEST.json' if args.daily else 'runtime/research_daily/BUILD_LATEST.json'),(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps(result,ensure_ascii=False))
    return 2 if result['status'].startswith('BLOCKED') else 0
if __name__=='__main__':raise SystemExit(main())
