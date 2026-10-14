"""Manual R6 first-capture/daily-incremental preflight; never enrolls or grants."""
import argparse,hashlib,json,os,psutil,sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(r'G:\codex work\v4-production-20261012')
SOURCE=Path(__file__).resolve().parents[1]

def inherit_live_environment():
    for process in psutil.process_iter(['pid','name','cmdline']):
        try:
            argv=process.info.get('cmdline') or []
            if (process.info.get('name') or '').lower()=='daav4.exe' and '--port' in argv and argv[argv.index('--port')+1]=='28765':
                env=process.environ()
                for key in ('V4_NATIVE_PG_DSN','V4_NATIVE_PG_READER_DSN'):
                    os.environ[key]=env[key]
                return process.info['pid']
        except (psutil.Error,ValueError,IndexError,KeyError):pass
    raise RuntimeError('LIVE_28765_CONTROLLED_PG_ENVIRONMENT_UNAVAILABLE')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('first-capture','daily-incremental','status'),required=True)
    parser.add_argument('--trade-date',help='Optional accepted/candidate date; never permits a future Owner')
    parser.add_argument('--output',type=Path,default=Path('G:/codex_tmp/v4_r6_forward/latest.json'))
    args=parser.parse_args();pid=inherit_live_environment();sys.path[:0]=[str(SOURCE/'src'),str(SOURCE)]
    from workbench_analysis.market_source_acquisition import official_sessions
    from workbench_analysis.operational_successor_v1 import digest
    from workbench_analysis.r43_owner_replay import ref,checked
    from workbench_service.candidate_research_read_v2 import capture_calendar_contract,first_capture_readiness
    from workbench_analysis.cohort_first_capture_producer_r1 import extract_candidate
    from workbench_analysis.cohort_capture_readiness_r1 import prepare_capture
    head_path=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';raw=head_path.read_bytes();head=json.loads(raw)
    token=digest(head);accepted=head.get('accepted_trade_date');sessions=official_sessions(ROOT)
    close,calendar_source=capture_calendar_contract(ROOT)
    day=args.trade_date or (accepted if args.mode=='daily-incremental' else sessions[sessions.index(accepted)+1] if accepted in sessions and sessions.index(accepted)+1<len(sessions) else accepted)
    if day not in sessions:raise ValueError('OFFICIAL_SESSION_CALENDAR_DATE_REQUIRED')
    if day>accepted and day not in head.get('owners',{}):
        gate=first_capture_readiness(head,day,sessions,session_close=close)
        producer=None
    else:
        gate=first_capture_readiness(head,day,sessions,session_close=close)
        producer=head.get('cohort_signal_producers',{}).get(day)
    result=dict(contract_id='V4_COHORT_FIRST_CAPTURE_CURRENT_R1',mode=args.mode,T0=day,
        accepted_T0=accepted,context_token_sha256=hashlib.sha256(token.encode()).hexdigest(),
        head_sha256=hashlib.sha256(raw).hexdigest(),official_calendar=calendar_source,
        readiness=gate,source_producer=producer,operator_invocation_required=True,
        no_grant_issued=True,production_write_authorized=False,formal_enrollment=False,
        Focus_is_cohort=False,historical_backfill_permitted=False,auto_daily_changed=False,
        live_service_pid_used_for_controlled_environment=pid)
    if producer and args.mode in ('first-capture','daily-incremental'):
        # Extraction accepts only the exact accepted Head owner and leaves an
        # isolated immutable evidence candidate; it does not issue admission.
        if day==accepted:
            extraction=extract_candidate(ROOT,candidate_binding=ref(ROOT,head_path),
                trade_date=day,cutoff=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
                candidate_directory='docs/evidence/cohort_first_capture_candidates_r1')
            result['extraction']=extraction
            owner=head.get('owners',{}).get(day,{}).get('validation_cohort')
            receipt=head.get('cohort_capture_receipts',{}).get(day)
            grant=head.get('cohort_write_grants',{}).get(day)
            if owner and receipt and grant:
                owner_doc=json.loads(checked(ROOT,owner).read_bytes())
                result['isolated_preflight']=prepare_capture(ROOT,accepted_head=ref(ROOT,head_path),owner_binding=owner,
                    trade_date=day,revision=owner_doc['revision'],cutoff=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat())
                # A preflight candidate still cannot alter the accepted Head.
                result['formal_owner_write']='NOT_ATTEMPTED; SEPARATE POST-REVIEW RELEASE STEP REQUIRED'
            else:
                result['isolated_preflight']={'status':'NOT_ADMITTED','reason':'INDEPENDENT_OWNER_RECEIPT_AND_SEPARATE_WRITE_GRANT_REQUIRED',
                    'missing_inputs':[name for name,value in (('OWNER',owner),('RECEIPT',receipt),('WRITE_GRANT',grant)) if not value],
                    'formal_enrollment':False}
        else:
            result['extraction']={'status':'PENDING_ACCEPTED_HEAD','reason':'FUTURE_T0_MUST_BE_ACCEPTED_BEFORE_INCREMENTAL_EXTRACTION',
                'production_write_authorized':False}
    else:
        result['extraction']={'status':'SOURCE_INCOMPLETE','reason':'FULL_AS_RECORDED_SIGNAL_PRODUCER_NOT_PRESENT',
            'production_write_authorized':False,'observed_count':None}
    result['acceptance']='WAIT_REAL_SESSION' if gate.get('status') in ('PENDING_NEXT_SESSION','SOURCE_NOT_CAPTURED') else 'PREFLIGHT_ONLY'
    args.output=args.output.resolve();args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'acceptance':result['acceptance'],'mode':args.mode,'T0':day,'readiness':gate.get('status'),
        'extraction':result['extraction'].get('status'),'output':str(args.output)},ensure_ascii=False))

if __name__=='__main__':main()
