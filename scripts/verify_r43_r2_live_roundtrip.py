"""Authorized live rollback and re-promotion; final state remains 10/08."""
import hashlib,json,sys,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.scoped_successor_r421 import atomic,canonical,sha
from workbench_analysis.r43_operational_sources import ref
from workbench_analysis.r43_operational_publication import cas,digest
from promote_r43_operational_v1 import rollback_exact,health
OUT=ROOT/'docs/evidence/r4_3_r2_release_control_20261009'
BASE='http://127.0.0.1:28765'
def get(path,expected=200):
    try:
        with urllib.request.urlopen(BASE+path,timeout=180) as r:raw=r.read();code=r.status
    except urllib.error.HTTPError as exc:raw=exc.read();code=exc.code
    assert code==expected,(path,code)
    return dict(url=BASE+path,status=code,sha256=hashlib.sha256(raw).hexdigest(),payload=json.loads(raw))
def main():
    head=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';legacy=ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json';authority=ref(ROOT,ROOT/'data/v4/R43_OPERATIONAL_USER_AUTHORIZATION.json')
    c=json.loads(head.read_bytes());token=digest(c);old=sha(legacy);records=[]
    for path,code in [('/api/v4/stocks?context_token=wrong',409),('/api/v4/stocks?context_token='+token+'&trade_date=2026-10-09',400)]:records.append(get(path,code))
    result=dict(contract='R43_R2_REAL_PRODUCTION_ROUNDTRIP_V1',production_head_sha_before=sha(head),legacy_head_sha_before=old,actual_negative_HTTP=records,independent_external_acceptance=False)
    try:cas(ROOT,head,c,'0'*64,user_authorization=authority);raise AssertionError('STALE_ACCEPTED')
    except ValueError as exc:assert str(exc)=='STALE_OPERATIONAL_HEAD_CAS';result['stale_CAS']=str(exc)
    result['NOOP']=cas(ROOT,head,c,token,user_authorization=authority);assert result['NOOP']['status']=='NOOP_IDENTICAL'
    rollback_exact(head,None,token);result['rollback_head_exists']=head.exists();assert not head.exists()
    try:
        result['rollback_context']=get('/api/v4/context');result['rollback_control']=get('/api/operations/status')
        assert result['rollback_context']['payload']['context']['accepted_trade_date']=='2026-09-30'
        assert result['rollback_control']['payload']['current_operational_trade_date'] is None
    finally:result['re_promote']=cas(ROOT,head,c,None,user_authorization=authority)
    result['final_HTTP']=health(BASE,token);result['final_context']=get('/api/v4/context');result['final_control']=get('/api/operations/status')
    assert sha(legacy)==old and sha(head)==token
    result.update(production_head_sha_after=sha(head),legacy_head_sha_after=sha(legacy),final_accepted_trade_date='2026-10-08',result='LIVE_ROLLBACK_REPROMOTION_AND_HTTP_PASS')
    atomic(OUT/'R43_R2_LIVE_ROLLBACK_AND_REPROMOTION.json',canonical(result));print(json.dumps(dict(result=result['result'],head=token,HTTP=len(result['final_HTTP']))))
if __name__=='__main__':main()
