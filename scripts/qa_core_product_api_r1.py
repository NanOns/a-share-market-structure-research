"""Real HTTP field contract audit with before/after and independent invariants."""
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError
from datetime import datetime,timezone
import json,time,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.audit_core_algo_ui_r1 import write,OUT

def request(base,path,query=None):
    start=time.perf_counter();url=base+'/api/v4/'+path+'?'+urlencode(query or {})
    try:
        with urlopen(url,timeout=90) as response:code=response.status;data=json.load(response)
    except HTTPError as error:code=error.code;data=json.load(error)
    return code,data,round((time.perf_counter()-start)*1000,1)

def main():
    base='http://127.0.0.1:28767';_,context,_=request(base,'context');token=context['context_token'];q=dict(context_token=token)
    _,stocks,_=request(base,'stocks',dict(q,limit=30));sid=stocks['items'][0]['entity_id']
    _,sectors,_=request(base,'sectors',dict(q,limit=30));sector='INDUSTRY:T0706'
    _,focus,_=request(base,'focus',dict(q,limit=30));fid=focus['items'][0]['entity_id']
    routes=['context','home','stocks','sectors','focus','focus/events','market','market/breadth','market/indices','market/limits','market/ladders','events','sources','diagnostics/sources','diagnostics/health','diagnostics/contracts','diagnostics/fep','forward','forward/statistics','forward/plans','forward/fep','forward/settlement','replay','compare']
    routes += ['stocks/'+sid+x for x in ('','/profile','/chart','/timeline','/why-not')]
    routes += ['sectors/'+sector+x for x in ('','/members','/timeline','/overlap')]
    routes += ['focus/'+fid+'/'+x for x in ('episodes','timeline','anchors','observations','outcomes')]
    audit=[];samples={};errors=[]
    for route in routes:
        params=dict(q,limit=30)
        if route=='compare':params.update(mode='stock-market',left=sid)
        code,d,ms=request(base,route,params)
        before_code,before,bms=request('http://127.0.0.1:28765',route,params)
        schema={k:type(v).__name__ for k,v in d.items()}
        audit.append(dict(route='/api/v4/'+route,http_status=code,business_status=d.get('status'),field_schema=schema,coverage_count=d.get('total',len(d.get('items',[]))),source_binding=d.get('source',d.get('source_bindings',d.get('sources'))),data_cutoff=d.get('context',{}).get('trade_date'),context_token=d.get('context_token'),elapsed_ms=ms,before=dict(http_status=before_code,business_status=before.get('status'),reason=before.get('reason'),coverage_count=before.get('total')),verdict='PASS_SCOPED' if code==200 and d.get('status') in ('READY','EMPTY_VALID') else 'SOURCE_NOT_PRESENT' if d.get('status')=='SOURCE_INCOMPLETE' else 'FAIL'))
        if code==200 and d.get('context_token')!=token:errors.append(dict(route=route,reason='TOKEN_MISMATCH'))
        if route in ('home','market/breadth','market/indices','market/limits'):samples[route]=d
    # Six actual chart combinations; every numeric and date must be valid.
    charts=[]
    for period in ('D','W','M'):
        for basis in ('RAW','QFQ'):
            code,d,ms=request(base,'stocks/'+sid+'/chart',dict(q,period=period,price_basis=basis,limit=120))
            ok=code==200 and d['items'] and all(b['trade_date']<='2026-10-09' for b in d['items']) and all(isinstance(b['close'],(float,int)) for b in d['items'] if b['quality']=='KNOWN')
            charts.append(dict(period=period,basis=basis,passed=bool(ok),bars=len(d.get('items',[])),last=d.get('items',[None])[-1],source=d.get('source')))
            if not ok:errors.append(dict(reason='CHART',period=period,basis=basis))
    # Search applies to the complete source; Chinese/code have exactly the same identities.
    target=stocks['items'][0];matches=[]
    for term in (target['symbol'].split('.')[-1],target['display_name']):
        code,d,_=request(base,'stocks',dict(q,q=term,limit=200));matches.append({r['entity_id'] for r in d['items']})
    if not all(sid in m for m in matches):errors.append(dict(reason='FULL_DATASET_CHINESE_CODE_SEARCH'))
    _,page2,_=request(base,'stocks',dict(q,offset=30,limit=30))
    if set(r['entity_id'] for r in stocks['items']) & set(r['entity_id'] for r in page2['items']):errors.append(dict(reason='PAGINATION_DUPLICATE'))
    members=[];offset=0
    while True:
        _,d,_=request(base,'sectors/'+sector+'/members',dict(q,offset=offset,limit=200));members += [r['entity_id'] for r in d['items']]
        if not d['has_next']:break
        offset += 200
    if len(members)!=d['total'] or len(members)!=len(set(members)):errors.append(dict(reason='MEMBER_CONSERVATION'))
    negatives=[]
    for path,params,expected in [('stocks',dict(context_token='OLD_TOKEN'),409),('stocks',dict(q,trade_date='2026-10-12'),400),('stocks/'+sid+'/chart',dict(q,period='X'),400),('stocks',dict(q,limit=201),400)]:
        code,d,_=request(base,path,params);negatives.append(dict(path=path,query=params,expected=expected,actual=code,passed=code==expected))
        if code!=expected:errors.append(dict(reason='NEGATIVE',path=path,code=code))
    home=samples['home'];shown={r['entity_id'] for card in home['sector_changes'] for r in card['member_previews']};independent={r['entity_id'] for r in home['changes']}
    if shown&independent or len(home['changes'])>30 or len(home['sector_changes'])>15:errors.append(dict(reason='HOME_CAP_OR_DEDUP'))
    focuslayers={kind:request(base,'focus/'+fid+'/'+kind,q)[1]['items'] for kind in ('episodes','timeline','anchors','observations','outcomes')}
    if focuslayers['episodes']==focuslayers['timeline'] or not all('episode_id' in r for r in focuslayers['observations']):errors.append(dict(reason='FOCUS_LAYER_COLLISION'))
    samples.update(stock=target,charts=charts,sector_id=sector,member_count=len(members),focus_id=fid,focus_layer_counts={k:len(v) for k,v in focuslayers.items()})
    write(OUT/'API_FIELD_CONTRACT_AUDIT.json',dict(contract_id='CORE_PRODUCT_API_FIELD_AUDIT_R1',observed_at=datetime.now(timezone.utc).isoformat(),context=context['context'],routes=audit,charts=charts,negatives=negatives,errors=errors,acceptance='API_BINDING_SCOPED_PASS' if not errors else 'FAIL',production_reload='NOT_PERFORMED',scope='ISOLATED_REAL_ACCEPTED_HEAD; before=running old service'))
    write(OUT/'API_UI_NUMERIC_SAMPLES.json',samples)
    print(json.dumps(dict(routes=len(routes),charts=len(charts),member_count=len(members),errors=errors)))
    return bool(errors)

if __name__=='__main__':raise SystemExit(main())
