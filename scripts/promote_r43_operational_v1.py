"""One-shot checked R43 production CLI. Never writes independent acceptance.

All output paths stay inside the project. Existing CAS owns the write lock.
Rollback uses the exact pre-CAS bytes and refuses a changed/newer head.
"""
import argparse,hashlib,json,os,sys,urllib.request
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.r43_operational_publication import cas,digest,validate
from workbench_analysis.r43_operational_sources import ref,checked
from workbench_analysis.scoped_successor_r421 import sha,canonical,atomic
from workbench_analysis.r43_release_control import verify_record,verify_user_authorization
def health(base,token):
    records=[];payloads={}
    paths=['/api/v4/context','/api/operations/status','/api/v4/original-0930/context','/v4','/v4/','/v4/operational-preview']
    for day in ('2026-09-28','2026-09-29','2026-09-30','2026-10-08'):
        for domain in ('stocks','sectors','relative_sector','rotation','market','focus','forward'):
            paths.append('/api/v4/'+domain+'?context_token='+token+'&trade_date='+day+'&limit=1')
    for path in paths:
        with urllib.request.urlopen(base+path,timeout=180) as r:raw=r.read();code=r.status;kind=r.headers.get('Content-Type','')
        records.append(dict(url=base+path,status=code,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        if 'json' in kind:payloads[path]=json.loads(raw)
    ctx=payloads['/api/v4/context'];status=payloads['/api/operations/status']
    assert ctx['context_token']==token and ctx['context']['accepted_trade_date']=='2026-10-08'
    assert status['context_token']==token and status['current_operational_trade_date']=='2026-10-08' and status['strict_pit_legacy_trade_date']=='2026-09-30'
    assert payloads['/api/v4/original-0930/context']['context']['accepted_trade_date']=='2026-09-30'
    for path,p in payloads.items():
        if 'trade_date=' in path:assert p['context_token']==token and p['context']['trade_date']==path.split('trade_date=')[1][:10]
    return records
def rollback_exact(head,before,published):
    lock=head.with_suffix('.lock');fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    try:
        os.close(fd)
        if not head.exists() or sha(head)!=published:raise ValueError('ROLLBACK_NEWER_HEAD_REFUSED')
        if before is None:head.unlink()
        else:atomic(head,before)
    finally:lock.unlink()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--candidate',required=True);parser.add_argument('--candidate-sha',required=True);parser.add_argument('--expected-head-sha',required=True,help='ABSENT or exact SHA');parser.add_argument('--service-url',default='http://127.0.0.1:28765');parser.add_argument('--receipt',required=True)
    action=parser.add_mutually_exclusive_group(required=True);action.add_argument('--dry-run',action='store_true');action.add_argument('--promote',action='store_true')
    args=parser.parse_args();out=Path(args.receipt).resolve();candidate_path=Path(args.candidate).resolve();head=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';legacy=ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json';authority=ROOT/'data/v4/R43_OPERATIONAL_EXTERNAL_ACCEPTANCE.json'
    if not out.is_relative_to(ROOT/'docs/evidence') or not candidate_path.is_relative_to(ROOT):raise ValueError('RELEASE_PATH_OUTSIDE_ALLOWED_ROOT')
    result=dict(contract='R43_ONE_SHOT_RELEASE_CLI_V1',command=sys.argv,run_at=datetime.now(timezone.utc).isoformat(),service_url=args.service_url,production_CAS_executed=False,external_acceptance_created=False)
    before=head.read_bytes() if head.exists() else None;result.update(head_sha_before=sha(head) if before is not None else None,legacy_head_sha=sha(legacy))
    try:
        if sha(candidate_path)!=args.candidate_sha:raise ValueError('EXACT_CANDIDATE_SHA_REQUIRED')
        candidate=json.loads(candidate_path.read_bytes());token=digest(candidate)
        user_mode=candidate.get('authority_mode')=='USER_AUTHORIZED_SCOPED_OPERATIONAL_V1'
        if user_mode:authority=ROOT/'data/v4/R43_OPERATIONAL_USER_AUTHORIZATION.json'
        if token!=args.candidate_sha:raise ValueError('CANONICAL_CANDIDATE_REQUIRED')
        result['candidate_digest']=token;validate(ROOT,candidate)
        expected=None if args.expected_head_sha=='ABSENT' else args.expected_head_sha
        if result['head_sha_before']!=expected:raise ValueError('STALE_OPERATIONAL_HEAD_CAS')
        if not authority.exists():raise ValueError('INDEPENDENT_EXTERNAL_ACCEPTANCE_REQUIRED')
        record=json.loads(authority.read_bytes())
        if user_mode:verify_user_authorization(ROOT,candidate,record)
        else:verify_record(ROOT,candidate,record)
        result['authorization']=record;result['independent_external_acceptance']=not user_mode
        result['scope']='USER_AUTHORIZED_SCOPED_OPERATIONAL' if user_mode else 'INDEPENDENTLY_ACCEPTED_SCOPED_OPERATIONAL'
        if args.dry_run:result['status']='DRY_RUN_READY_NO_WRITE'
        else:
            result['CAS']=cas(ROOT,head,candidate,expected,**({'user_authorization':ref(ROOT,authority)} if user_mode else {'external_acceptance':ref(ROOT,authority)}));result['production_CAS_executed']=True
            published=sha(head)
            try:
                result['actual_HTTP']=health(args.service_url,token)
                from workbench_service.joint_release import load,checked_path
                expected_html=sha(checked_path(ROOT,load(ROOT)['ui_assets']['index.html']))
                assert all(r['sha256']==expected_html for r in result['actual_HTTP'] if r['url'].endswith(('/v4','/v4/')))
                assert sha(legacy)==result['legacy_head_sha']
                result['status']='SCOPED_PRODUCTION_CUTOVER_HTTP_PASS'
            except Exception:
                rollback_exact(head,before,published);result['rollback']='EXACT_PREDECESSOR_RESTORED';raise
        result['head_sha_after']=sha(head) if head.exists() else None;result['historical_PIT_permission']=False
    except Exception as exc:
        result.update(status='BLOCKED_NO_PRODUCTION_ACCEPTANCE',reason=str(exc),head_sha_after=sha(head) if head.exists() else None)
        atomic(out,canonical(result));print(json.dumps(result,ensure_ascii=False));return 2
    atomic(out,canonical(result));print(json.dumps(result,ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
