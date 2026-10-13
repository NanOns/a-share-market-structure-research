"""Read-only T4 smoke/performance capture. Never enqueue, publish or restart."""
import argparse,json,time,statistics
from pathlib import Path
from urllib.request import urlopen,Request
from urllib.parse import urlencode

ROUTES=['/api/v4/context','/api/v4/stocks','/api/v4/sectors','/api/v4/focus','/api/v4/home','/api/v4/operations/daily-update/progress','/api/v4/desktop/status']
PAGES=['/v4','/v4/research/stocks','/v4/research/sectors','/v4/research/focus','/v4/research/market','/v4/research/diagnostics?tab=jobs']

def read(base,path):
    start=time.perf_counter()
    with urlopen(Request(base+path,headers={'Accept-Encoding':'identity'}),timeout=30) as response:
        raw=response.read();return response.status,raw,time.perf_counter()-start

def run(base,samples):
    status,raw,_=read(base,ROUTES[0]);context=json.loads(raw);token=context['context_token']
    t0=context['context'].get('trade_date');results={}
    for route in ROUTES:
        query={} if route in (ROUTES[0],ROUTES[5],ROUTES[6]) else {'context_token':token,'limit':30}
        path=route+('?' + urlencode(query) if query else '')
        timings=[];sizes=[];last=None
        for _ in range(samples):
            code,raw,elapsed=read(base,path);last=json.loads(raw)
            if code!=200:raise ValueError('HTTP_STATUS_FAILED:'+route)
            if route in ROUTES[:5] and (last.get('context_token')!=token or last.get('context',{}).get('trade_date')!=t0):raise ValueError('MIXED_HEAD_RESPONSE:'+route)
            timings.append(elapsed);sizes.append(len(raw))
        ordered=sorted(timings)
        results[route]=dict(median_seconds=statistics.median(timings),p95_seconds=ordered[min(len(ordered)-1,int(len(ordered)*.95))],max_seconds=max(timings),bytes=max(sizes))
    pages={p:read(base,p)[0] for p in PAGES}
    final=json.loads(read(base,ROUTES[0])[1])
    if final['context_token']!=token:raise ValueError('HEAD_SWITCH_DURING_SAMPLE_RETRY_WITH_NEW_TOKEN')
    progress=json.loads(read(base,ROUTES[5])[1]);desktop=json.loads(read(base,ROUTES[6])[1])
    return dict(contract_id='V4_DELIVERY_READ_ONLY_SMOKE_R11',base=base,T0=t0,context_token=token,samples=samples,routes=results,pages=pages,progress=progress,desktop=desktop,actual_deriving=progress.get('stage_state') in ('RUNNING','PUBLISHING') and progress.get('stage') not in ('SOURCE_CHECKING','SOURCE_READY','WAIT_TDX'),tray_menu_manual_check='REQUIRED',production_acceptance=False)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base',default='http://127.0.0.1:28765');parser.add_argument('--samples',type=int,default=20);parser.add_argument('--out',required=True);args=parser.parse_args()
    out=Path(args.out).resolve()
    if out.drive.upper()!='G:' or not 1<=args.samples<=30:raise ValueError('G_OUTPUT_AND_BOUNDED_SAMPLES_REQUIRED')
    result=run(args.base,args.samples)
    out.parent.mkdir(parents=True,exist_ok=True);temp=out.with_suffix('.tmp');temp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(out)
    print(json.dumps(dict(T0=result['T0'],routes=len(result['routes']),actual_deriving=result['actual_deriving'],out=str(out))))

if __name__=='__main__':main()
