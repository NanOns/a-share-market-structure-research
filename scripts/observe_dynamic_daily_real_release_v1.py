"""Observe the actual service; never alters clock, sources, jobs, or Head."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,time,urllib.request,urllib.error,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_daily_http_readback_v1 import readback
from workbench_analysis.r43_owner_replay import ref
from workbench_analysis.tdx_official_daily_source import sha256_file


def observe(target,seconds):
    base='http://127.0.0.1:28765';evidence=ROOT/'docs/evidence/dynamic_daily_20261009'
    def get(path):
        with urllib.request.urlopen(base+path,timeout=30) as response:return json.load(response)
    deadline=time.monotonic()+seconds;last=None
    while time.monotonic()<deadline:
        status=get('/api/v4/operations/daily-update/status');job=status.get('active_job') or status.get('last_catch_up_job')
        stages=[]
        for f in (ROOT/'data/v4/dynamic_daily_owners'/target).glob('*'):
            if (f/'owner_v3/CORE_REPLAY.json').exists():stages.append('CORE_PASS')
            count=len(list((f/'owner_v3/owners').glob('*/PROFILE_STRUCTURE_OWNER.json')))
            if count:stages.append('PROFILE_DAYS_'+str(count))
            if (f/'sector_v3/SECTOR_REPLAY.json').exists():stages.append('SECTOR_COMPLETE')
            if (f/'owner_v3/MARKET_REPLAY.json').exists():stages.append('MARKET_COMPLETE')
            if (f/'owner_v3/FOCUS_FORWARD_REPLAY.json').exists():stages.append('FOCUS_COMPLETE')
        state=(job or {}).get('status');signature=(state,tuple(stages))
        if signature!=last:
            print(json.dumps(dict(observed_at=datetime.now(timezone.utc).isoformat(),job_status=state,stages=stages)),flush=True);last=signature
        if state in {'QA_BLOCKED','FAILED_TERMINAL','FAILED_RETRYABLE','CANCELLED'}:
            atomic_json(ROOT,evidence/'DD07_REAL_RELEASE_BLOCKER.json',dict(status=status,external_acceptance='NOT_GRANTED'))
            raise ValueError('ACTUAL_RELEASE_BLOCKED:'+str((job or {}).get('error')))
        if state=='PUBLISHED_FULL' and status['last_good_trade_date']==target:
            candidate=json.loads((ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
            http=readback(base,candidate)
            old=json.loads((evidence/'DD07_OLD_CONTEXT_BEFORE_REAL_CAS.json').read_bytes())
            context=old['operational_context'];oldtoken=(context.get('context') or context)['context_token']
            negatives=[]
            for path in ('/api/v4/stocks','/api/operations/status'):
                try:get(path+'?context_token='+oldtoken)
                except urllib.error.HTTPError as error:
                    negatives.append(dict(path=path,http_status=error.code,payload=json.load(error)))
                else:raise ValueError('STALE_CONTEXT_NOT_REJECTED')
            if any(r['http_status']!=409 for r in negatives):raise ValueError('WRONG_STALE_CONTEXT_STATUS')
            strict=get('/api/v4/original-0930/context')
            before=old['strict_context'].get('context',old['strict_context']);after=strict.get('context',strict)
            if old['strict_context']['context_token']!=strict['context_token']:raise ValueError('STRICT_PIT_TOKEN_CHANGED')
            if sha256_file(ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json')!='38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40':raise ValueError('STRICT_PIT_HEAD_CHANGED')
            result=dict(contract_id='DD07_ACTUAL_REAL_NEW_DAY_RELEASE_READBACK_V1',observed_at=datetime.now(timezone.utc).isoformat(),
                acceptance='PASS_ACTUAL_CAS_SIX_HTTP_STALE_TOKEN_AND_PIT_ISOLATION',status=status,http_readback=http,
                head=ref(ROOT,ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'),candidate=candidate,
                job_events=get('/api/v4/operations/daily-update/jobs/'+job['job_id']+'/events'),
                transaction=json.loads((ROOT/'runtime/dynamic_daily/publication_transaction.json').read_bytes()),
                stale_token_negatives=negatives,strict_context=strict,external_acceptance='NOT_GRANTED',next_stage='REAL_UI_RESTART_AND_FINAL_ARCHIVE')
            atomic_json(ROOT,evidence/'DD07_REAL_20261009_RELEASE_READBACK.json',result)
            print(json.dumps(dict(acceptance=result['acceptance'],date=target,token=http['context_token'])),flush=True)
            return result
        time.sleep(15)
    raise TimeoutError('ACTUAL_OWNER_EXECUTION_STILL_IN_PROGRESS')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--target',required=True);parser.add_argument('--seconds',type=int,default=3600)
    args=parser.parse_args();observe(args.target,args.seconds)
