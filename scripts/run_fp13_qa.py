"""FP13 reproducible real-source QA. Never writes into source roots."""
import argparse,hashlib,json,os,sys,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from scripts.fp_domain_evidence import enter,check_protected
OUT=ROOT/'docs/evidence/fp13_20261008'

def fingerprint(side):
    from scripts.forward_final_bootstrap import source_roots
    rows=[]
    for root in source_roots():
        if not root.is_dir():raise ValueError('SOURCE_ROOT_UNAVAILABLE')
        for directory,folders,names in os.walk(root,followlinks=False):
            folders.sort()
            for name in sorted(names):
                p=Path(directory)/name;before=p.stat();h=hashlib.sha256()
                with p.open('rb') as stream:
                    while block:=stream.read(8*1024*1024):h.update(block)
                after=p.stat()
                if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('SOURCE_CHANGED_DURING_READ')
                rows.append(dict(path=p.as_posix(),bytes=before.st_size,mtime_ns=before.st_mtime_ns,sha256=h.hexdigest()))
    raw=json.dumps(rows,sort_keys=True,separators=(',',':')).encode()
    write(ROOT/f'reports/fp13_20261008/TDX_{side}.json',rows)
    result=dict(roots=[p.as_posix() for p in source_roots()],files=len(rows),bytes=sum(r['bytes'] for r in rows),sha256=hashlib.sha256(raw).hexdigest())
    write(OUT/f'TDX_{side}.json',result)
    if side=='POST':assert result==json.loads((OUT/'TDX_PRE.json').read_bytes()),'TDX_FINGERPRINT_CHANGED'
    print(json.dumps(result),flush=True)

def api():
    from workbench_service.production_v4 import ProductionV4ResearchReader
    reader=ProductionV4ResearchReader(ROOT);records=[]
    def get(route,expect=200):
        start=time.perf_counter()
        try:
            with urllib.request.urlopen('http://127.0.0.1:28765/api/v4/'+route,timeout=30) as response:code=response.status;data=json.load(response)
        except urllib.error.HTTPError as error:code=error.code;data=json.load(error)
        if expect is not None:assert code==expect,(route,code,data)
        records.append(dict(route=route,http=code,ms=round((time.perf_counter()-start)*1000,2),status=data.get('status')))
        return data
    context=get('context');assert context['context_token']==reader.token
    pagination={};samples={}
    for domain in ('stocks','sectors','focus','forward','events','sources'):
        rows=[];offset=0
        while True:
            data=get(f'{domain}?limit=200&offset={offset}');assert data['context_token']==reader.token
            rows+=data['items'];offset+=200
            if not data['has_next']:break
        assert len(rows)==data['total'];assert len({r['entity_id'] for r in rows})==len(rows)
        ids={r['entity_id'] for r in rows};expected=reader.query(domain,{'limit':200})['total'];assert expected==len(rows)
        pagination[domain]=dict(total=len(rows),pages=(len(rows)+199)//200,unique=True)
        samples[domain]=rows[:3]
    sid=samples['stocks'][0]['entity_id'];sector=samples['sectors'][0]['entity_id']
    routes=['home','market/indices','market/breadth','market/limits','market/ladders','market/facts-events','focus/events','forward/statistics','forward/plans','forward/fep']
    routes += ['diagnostics/'+s for s in ('health','sources','contracts','jobs','legacy','shadow')]
    routes += ['stocks/'+sid+'/'+s for s in ('profile','chart','why-not-prewatch','anchors','structure-events','timeline','evidence')]
    routes += ['sectors/'+sector+'/'+s for s in ('members','timeline','rotation','rotation-timeline','overlap')]
    route_results={}
    for route in routes:
        route_results[route]=get(route,None)
    get('stocks?context_token=expired',409);get('stocks?limit=201',400)
    get('replay?as_of=2026-09-18');get('replay?as_of=2026-09-28&view=corrected&left=600000')
    get('compare?as_of=2026-09-30&view=corrected&mode=stock-market&left=600000')
    write(OUT/'HTTP_PERFORMANCE.json',dict(context=context,requests=records,pagination=pagination,samples=samples,subroutes={k:dict(status=v.get('status'),total=v.get('total'),reason=v.get('reason')) for k,v in route_results.items()},protected=check_protected(OUT)))
    write(OUT/'BROWSER_INPUTS.json',dict(stock=sid,sector=sector,focus=samples['focus'][0]['entity_id'],real_stock=samples['stocks'][0],real_sector=samples['sectors'][0],release_id=reader.context['release_id'],token=reader.token))
    print(json.dumps(dict(requests=len(records),pagination=pagination,sid=sid,sector=sector)),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['entry','PRE','POST','api']);args=parser.parse_args()
    if args.mode=='entry':enter(13)
    elif args.mode=='api':api()
    else:fingerprint(args.mode)
