"""Single V4 daily entry: existing gated capture/build, then accepted view CAS."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'src')]
from scripts.v4_production_cutover_evidence import ROOT
from workbench_service.v4_daily_refresh import refresh_status, validate_current_view_candidate
from workbench_analysis.operational_daily_executor_v1 import _daily_runtime_contract
from workbench_db.dm01_data_accepted_head_pg_r1 import read_current as read_data_head


def can_publish_increment(child, returncode, accepted_date, target_date):
    return (returncode==0 and (child or {}).get('status') in ('PROMOTED_V2','NOOP_IDENTICAL_PROMOTION')
            and accepted_date==target_date)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--candidate-contract');args=parser.parse_args()
    try:
        status=refresh_status(ROOT)
        if args.candidate_contract:
            status=validate_current_view_candidate(ROOT,args.candidate_contract)
        elif status['next_completed_session']:
            scope_policy=_daily_runtime_contract(
                'TDX_A_STOCK_DELTA_SCOPE_POLICY_V2','2.0.0',version_field='version')
            if scope_policy.get('source_mode')!='RECONSTRUCTED_CORRECTED' or scope_policy.get('production_permission') is not False:
                raise ValueError('DAILY_TDX_SCOPE_POLICY_NOT_CORRECTED_CANDIDATE')
            source_args=['--typed-scope-v2']
            process=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/run_v4_dm01_daily_increment.py'),'--target-date',status['next_completed_session'],'--active-source-policy',*source_args],cwd=ROOT,capture_output=True,text=True,encoding='utf8')
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
            actual_head=read_data_head(ROOT)['candidate']
            if can_publish_increment(child,process.returncode,actual_head['accepted_trade_date'],status['next_completed_session']):
                status.update(status='INPUT_CAPTURED_PENDING_CANONICAL_PG_PUBLICATION',
                    accepted_trade_date=actual_head['accepted_trade_date'],
                    candidate_contract_status='NOT_BUILT_FROM_WORKSPACE_HEAD_FILES',
                    data_preserved=True,accepted_research_head_changed=False)
            else:
                policy=ROOT/'config/v4_corrected_owner_replay_v1.json'
                if policy.exists() and status['next_completed_session'] in json.loads(policy.read_bytes())['target_sessions']:
                    corrected=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/run_v4_dm01_daily_increment.py'),
                        '--target-date',status['next_completed_session'],'--corrected-owner-repair'],cwd=ROOT,capture_output=True,text=True,encoding='utf8')
                    status.update(corrected_owner_exit_code=corrected.returncode,corrected_owner_output=corrected.stdout,
                        corrected_owner_error=corrected.stderr,status='BLOCKED_SCOPED_OWNER_RELEASE_GATE',data_preserved=True)
                else:status.update(status='BLOCKED_SOURCE_OR_OWNER_GATE',data_preserved=True)
        print(json.dumps(status,ensure_ascii=False))
        return 0 if status.get('status') in ('WAIT_NEXT_ACCEPTED_INPUT','COMPLETED_INPUT_CAPTURE_REQUIRED') else 2
    except (ValueError,OSError,KeyError) as error:
        receipt=dict(status='BLOCKED_DAILY_REFRESH',reason=str(error))
        print(json.dumps(receipt,ensure_ascii=False));return 2


if __name__=='__main__':raise SystemExit(main())
