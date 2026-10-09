"""Actual service readback, recorded independently from unit-test simulations."""
from pathlib import Path
import json,sys,urllib.request,urllib.parse
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.scoped_successor_r421 import atomic,canonical,sha
OUT=ROOT/'docs/evidence/dynamic_daily_20261009'

def get(path):
    with urllib.request.urlopen('http://127.0.0.1:28766'+path,timeout=60) as r:
        return json.load(r)

if __name__=='__main__':
    status=get('/api/v4/operations/daily-update/status')
    context=get('/api/v4/context');token=context['context_token']
    reads=[]
    for domain in ['stocks','sectors','market','focus']:
        response=get('/api/v4/'+domain+'?'+urllib.parse.urlencode(dict(context_token=token,limit=3)))
        assert response['context_token']==token
        reads.append(dict(domain=domain,context_token=response['context_token'],
                          status=response['status'],trade_date=response.get('trade_date'),count=response.get('count')))
    job=status['last_job'];events=get('/api/v4/operations/daily-update/jobs/'+job['job_id']+'/events') if job else {}
    result=dict(contract_id='DD04_DD05_REAL_SERVICE_READBACK_V1',evidence_kind='ACTUAL_LOCAL_HTTP_IAB_SEPARATE',
        status=status,context=context,domain_readback=reads,job_events=events,
        scope='Durable source-job scheduler and UI; inherited last-good domain reads; no successor CAS',
        service_port=28766,production_port_28765_replaced=False,
        protected_heads={p:sha(ROOT/p) for p in ['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json']},
        successor_publication=False,external_acceptance='NOT_GRANTED')
    atomic(OUT/'DD04_DD05_REAL_SERVICE_READBACK.json',canonical(result))
    print(json.dumps(dict(auto_enabled=status['settings']['auto_enabled'],service_alive=status['settings']['service_alive'],
        last_good=status['last_good_trade_date'],same_token_domains=len(reads),last_job=job['status'] if job else None)))
