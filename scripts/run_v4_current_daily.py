"""Single V4 daily entry: existing gated capture/build, then accepted view CAS."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'src')]
from scripts.v4_production_cutover_evidence import ROOT, REPORT, write
from workbench_service.current_v4_context import digest
from workbench_service.v4_daily_refresh import AUTHORITY, publish_accepted_view, refresh_status


def can_publish_increment(child, returncode, accepted_date, target_date):
    return (returncode==0 and (child or {}).get('status') in ('PROMOTED_V2','NOOP_IDENTICAL_PROMOTION')
            and accepted_date==target_date)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--candidate-contract');args=parser.parse_args()
    before=digest((ROOT/AUTHORITY).read_bytes())
    try:
        status=refresh_status(ROOT)
        if args.candidate_contract:
            status=publish_accepted_view(ROOT,args.candidate_contract,before)
        elif status['next_completed_session']:
            process=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/run_v4_dm01_daily_increment.py'),'--target-date',status['next_completed_session'],'--active-source-policy'],cwd=ROOT,capture_output=True,text=True,encoding='utf8')
            status['daily_pipeline_exit_code']=process.returncode;status['daily_pipeline_output']=process.stdout;status['daily_pipeline_error']=process.stderr
            child=None
            try:
                child=json.loads(process.stdout.strip().splitlines()[-1]);receipt=json.loads(Path(child['receipt']).read_bytes())
                active=receipt.get('active_source_capture') or {}
                status['source_requests']=active.get('baostock_request_count_this_run')
                status['source_request_count_scope']='BAOSTOCK_ONLY;TDX_REQUESTS_IN_CAPTURE_RECEIPTS'
                status['source_request_receipt']=child['receipt']
            except (ValueError,KeyError,IndexError,OSError):
                status['source_requests']=None
                status['source_request_count_scope']='UNVERIFIED;INSPECT_CHILD_RECEIPT'
            actual_head=json.loads((ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes())
            if can_publish_increment(child,process.returncode,actual_head['accepted_trade_date'],status['next_completed_session']):
                build=subprocess.run([sys.executable,'-m','scripts.build_v4_current_read_contract'],cwd=ROOT,capture_output=True,text=True,encoding='utf8')
                status['owner_view_build_exit_code']=build.returncode
                if build.returncode==0:status=publish_accepted_view(ROOT,'config/v4_current_accepted_read_contract_v1.json',before)
                else:status.update(status='BLOCKED_OWNER_ACCEPTANCE_REQUIRED',owner_error=build.stderr,data_preserved=True)
            else:
                policy=ROOT/'config/v4_corrected_owner_replay_v1.json'
                if policy.exists() and status['next_completed_session'] in json.loads(policy.read_bytes())['target_sessions']:
                    corrected=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/run_v4_dm01_daily_increment.py'),
                        '--target-date',status['next_completed_session'],'--corrected-owner-repair'],cwd=ROOT,capture_output=True,text=True,encoding='utf8')
                    status.update(corrected_owner_exit_code=corrected.returncode,corrected_owner_output=corrected.stdout,
                        corrected_owner_error=corrected.stderr,status='BLOCKED_SCOPED_OWNER_RELEASE_GATE',data_preserved=True)
                else:status.update(status='BLOCKED_SOURCE_OR_OWNER_GATE',data_preserved=True)
        write(REPORT/'DAILY_REFRESH_LATEST_RECEIPT.json',status)
        print(json.dumps(status,ensure_ascii=False))
        return 2 if status['status'].startswith('BLOCKED') else 0
    except (ValueError,OSError,KeyError) as error:
        receipt=dict(status='BLOCKED_DAILY_REFRESH',reason=str(error),production_pointer_preserved=digest((ROOT/AUTHORITY).read_bytes())==before)
        write(REPORT/'DAILY_REFRESH_LATEST_RECEIPT.json',receipt);print(json.dumps(receipt));return 2


if __name__=='__main__':raise SystemExit(main())
