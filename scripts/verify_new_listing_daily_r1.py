"""Independent actual IPO/date/Owner/publication readback for the daily repair."""
import json,gzip,hashlib,os,sys,urllib.request
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlencode
ROOT=Path(__file__).resolve().parents[1]
RUNTIME=Path('G:/codex work/v4-production-20261012')
OUT=ROOT/'docs/audits/v4_new_listing_daily_20261013_r1'
CODE='SZ.301660';DAY='2026-10-13'
SID='SEC-'+hashlib.sha256(b'SZ\x00SZ.301660\x002026-10-13').hexdigest()[:32].upper()
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp')
    t.write_bytes(v if isinstance(v,bytes) else (json.dumps(v,ensure_ascii=False,indent=2,default=str)+'\n').encode('utf8'));os.replace(t,p)
def load(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(binding):
    p=RUNTIME/binding['path'];assert sha(p)==binding['sha256']
    with gzip.open(p,'rt',encoding='utf8') as f:return [json.loads(x) for x in f if x.strip()]
def http(route):
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:28765'+route,timeout=120) as r:return r.status,r.read()
def owner():
    folders=list((RUNTIME/'data/v4/dynamic_daily_owners'/DAY).iterdir())
    folder=next(p for p in folders if (p/'owner_v3/CORE_REPLAY.json').is_file())
    replay=load(folder/'owner_v3/CORE_REPLAY.json');o=next(x for x in replay['owners'] if x['trade_date']==DAY)
    raw=rows(o['raw']);adjusted=rows(o['adjusted']);cores=rows(o['core']);histories=rows(o['history'])
    r=next(x for x in raw if x['security_id']==SID);a=next(x for x in adjusted if x['security_id']==SID)
    c=next(x for x in cores if x['security_id']==SID);h=next(x for x in histories if x['security_id']==SID)
    assert len(h['bars'])==1 and h['bars'][0]['trade_date']==DAY
    for f in ['open','high','low','close']:
        assert r[f]==a[f]==h['bars'][0]['raw_ohlc'][['open','high','low','close'].index(f)]
    for f in ['ret1','ret5','ret20','ma5','ma20']:
        if f in c['fields']:assert c['fields'][f]['value'] is None,c['fields'][f]
    for x in replay['owners']:
        if x['trade_date']<DAY:assert not any(r['security_id']==SID for r in rows(x['raw']))
    assert all(x['result']=='PASS' for x in replay['oracle'])
    v=dict(contract_id='V4_NEW_IPO_REAL_CORE_HISTORY_ORACLE_R1',acceptance='PASS',folder=str(folder),SID=SID,raw_rows=len(raw),core_rows=len(cores),adjusted_rows=len(adjusted),ipo_raw=r,ipo_adjusted=a,ipo_core=c,ipo_history=h,core_oracle=replay['oracle'],prior_dates_exclude_new_IPO=True,insufficient_history_values_unknown=True)
    write(OUT/'ACTUAL_IPO_CORE_READBACK_R1.json',v);print(json.dumps(dict(acceptance='PASS',raw=len(raw),core=len(cores),IPO_history_bars=1)),flush=True)
def publication():
    head=load(RUNTIME/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');assert head['accepted_trade_date']==DAY
    code,raw=http('/api/v4/context');context=json.loads(raw);token=context['context_token'];assert context['context']['trade_date']==DAY
    records=[]
    for name in ['context','home','stocks','sectors','focus','market','diagnostics']:
        code,raw=http('/api/v4/'+name+'?'+urlencode(dict(trade_date=DAY,context_token=token,limit=30)))
        d=json.loads(raw);assert code==200 and d['context']['trade_date']==DAY and d['context_token']==token
        write(OUT/'HTTP_PUBLISHED_13_R1'/(name+'.json.gz'),gzip.compress(raw,mtime=0))
        records.append(dict(route=name,http=code,T0=DAY,token=token,total=d.get('total'),sha256=hashlib.sha256(raw).hexdigest()));print(name,flush=True)
    code,raw=http('/api/v4/operations/daily-update/status');daily=json.loads(raw)
    assert daily['last_job']['status']=='PUBLISHED_FULL'
    write(OUT/'FINAL_DAILY_STATUS_R1.json',raw)
    v=dict(contract_id='V4_NEW_LISTING_REAL_DAILY_PUBLICATION_READBACK_R1',acceptance='PASS_REAL_DAILY_PUBLISHED',observed_at=datetime.now(timezone.utc).isoformat(),T0=DAY,token=token,head_sha256=sha(RUNTIME/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'),records=records,job=daily['last_job'],full_product_release=False,PIT_ELIGIBLE=False,AS_RECORDED=False)
    write(OUT/'PUBLICATION_READBACK_R1.json',v);print(json.dumps({'acceptance':v['acceptance'],'T0':DAY,'token':token}))
if __name__=='__main__':
    if sys.argv[1]=='owner':owner()
    elif sys.argv[1]=='publication':publication()
