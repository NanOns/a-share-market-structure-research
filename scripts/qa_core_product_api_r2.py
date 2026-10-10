"""Real HTTP field contract audit with before/after and independent invariants."""
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError
from datetime import datetime,timezone
import json,time,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.audit_core_algo_ui_r2 import write,OUT

def compact_samples(samples):
    """Persist numeric readback, not repeated full Owner provenance payloads."""
    def row(r):
        keys=('entity_id','security_id','symbol','display_name','trade_date','event','effective_event','href')
        result={k:r[k] for k in keys if k in r}
        selected=('close','scenario','final_eligibility','output_state','prior_rotation_state','sector_rs5','member_count','source_member_count','unmapped_count','effective_event','trade_date','ma20','atr20','ret1','ret5','ret20')
        result['fields']={k:{f:v for f,v in c.items() if f in ('value','unit','quality','source','field','as_of','contract_id','parameter_set_id','window_start_trade_date','window_end_trade_date','actual_count')} for k,c in r.get('fields',{}).items() if k in selected}
        return result
    home=samples['home']
    home['rotations']=[row(r) for r in home['rotations']]
    home['sector_changes']=[dict(item=row(c['item']),member_previews=[{k:r[k] for k in ('entity_id','symbol','display_name') if k in r} for r in c['member_previews']]) for c in home['sector_changes']]
    for k in ('changes','risks'):home[k]=[row(r) for r in home[k]]
    samples['stock']=row(samples['stock'])
    samples['sampling_scope']='Selected visible numeric fields; complete HTTP schema/source audit is separate; full raw Owners stay on G.'
    return samples

def request(base,path,query=None):
    start=time.perf_counter();url=base+(path if path.startswith('/api/') else '/api/v4/'+path)+'?'+urlencode(query or {})
    try:
        with urlopen(url,timeout=90) as response:code=response.status;data=json.load(response)
    except HTTPError as error:code=error.code;data=json.load(error)
    return code,data,round((time.perf_counter()-start)*1000,1)

def main():
    base='http://127.0.0.1:28767';_,context,_=request(base,'context');token=context['context_token'];q=dict(context_token=token)
    _,stocks,_=request(base,'stocks',dict(q,limit=30));sid=stocks['items'][0]['entity_id']
    _,sectors,_=request(base,'sectors',dict(q,limit=30));sector='INDUSTRY:T0706'
    _,focus,_=request(base,'focus',dict(q,limit=30));fid=focus['items'][0]['entity_id']
    routes=['/api/operations/status','context','home','stocks','sectors','focus','focus/events','market','market/breadth','market/indices','market/limits','market/ladders','events','sources','diagnostics/sources','diagnostics/health','diagnostics/contracts','diagnostics/jobs','diagnostics/legacy','diagnostics/shadow','diagnostics/fep','forward','forward/statistics','forward/plans','forward/fep','forward/settlement','replay','compare']
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
        field_cells=[r.get('fields',{}) for r in d.get('items',[]) if isinstance(r,dict)];schema['item_fields']={k:{'value_types':sorted({type(c[k].get('value')).__name__ for c in field_cells if k in c}), 'qualities':sorted({str(c[k].get('quality')) for c in field_cells if k in c}), 'units':sorted({str(c[k].get('unit')) for c in field_cells if k in c})} for k in sorted({k for c in field_cells for k in c})}
        audit.append(dict(route=route if route.startswith('/api/') else '/api/v4/'+route,http_status=code,business_status=d.get('status',d.get('state','ENVELOPE_READ')),role_in_page=('日更和处理状态诊断' if route=='/api/operations/status' else '六入口 '+route.split('/')[0]+' 独立读区块'),field_schema=schema,coverage_count=d.get('total',len(d.get('items',[]))),source_binding=d.get('source',d.get('source_bindings',d.get('sources',[r['source'] for r in d.get('items',[])[:3] if isinstance(r,dict) and r.get('source') is not None]))),data_cutoff=d.get('context',{}).get('trade_date'),context_token=d.get('context_token'),elapsed_ms=ms,before=dict(http_status=before_code,business_status=before.get('status'),reason=before.get('reason'),coverage_count=before.get('total')),verdict='PASS_SCOPED' if code==200 and (d.get('status') in ('READY','EMPTY_VALID') or route=='/api/operations/status') else 'SOURCE_NOT_PRESENT' if d.get('status')=='SOURCE_INCOMPLETE' else 'FAIL'))
        if code==200 and route!='/api/operations/status' and d.get('context_token')!=token:errors.append(dict(route=route,reason='TOKEN_MISMATCH'))
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
    extra=[]
    for params in [dict(q,type='INDUSTRY',maturity='UNKNOWN',health='UNKNOWN',sort='-sector_rs20',limit=200),dict(q,q='430017',limit=30)]:
        route='sectors' if 'type' in params else 'stocks';code,d,_=request(base,route,params);extra.append(dict(route=route,query=params,total=d.get('total'),query_explanation=d.get('query_explanation'),passed=code==200 and (all(r['fields']['maturity']['value']=='UNKNOWN' and r['fields']['sector_type']['value']=='INDUSTRY' for r in d.get('items',[])) if route=='sectors' else d.get('query_explanation',{}).get('status')=='OUT_OF_UNIVERSE')))
    if not all(r['passed'] for r in extra):errors.append(dict(reason='EXTRA_FILTER_IDENTITY'))
    home=samples['home'];shown={r['entity_id'] for card in home['sector_changes'] for r in card['member_previews']};independent={r['entity_id'] for r in home['changes']}
    if shown&independent or len(home['changes'])>30 or len(home['sector_changes'])>15:errors.append(dict(reason='HOME_CAP_OR_DEDUP'))
    focuslayers={kind:request(base,'focus/'+fid+'/'+kind,q)[1]['items'] for kind in ('episodes','timeline','anchors','observations','outcomes')}
    if focuslayers['episodes']==focuslayers['timeline'] or not all('episode_id' in r for r in focuslayers['observations']):errors.append(dict(reason='FOCUS_LAYER_COLLISION'))
    _,failed_focus,_=request(base,'focus',dict(q,q='301628',limit=200))
    _,failed_episodes,_=request(base,'focus/SEC-C08B6C24E4F39D8E85C03F8588661538/episodes',q)
    if not failed_focus['items'] or not any(e.get('end_date')=='2026-10-09' for e in failed_episodes['items']):errors.append(dict(reason='REAL_INVALIDATED_FOCUS_NOT_ENDED'))
    exposure=failed_focus['sector_exposure']
    if sum(r['count'] for r in exposure['items'])+exposure['unknown_industry']!=exposure['denominator']:errors.append(dict(reason='FOCUS_EXPOSURE_DENOMINATOR'))
    _,historical,_=request(base,'stocks',dict(q,trade_date='2026-09-30',q='688349',limit=30))
    if historical['context']['trade_date']!='2026-09-30' or historical['items'][0]['fields']['close']['value']!=13.24:errors.append(dict(reason='HISTORICAL_DATE_BINDING'))
    samples.update(repaired_focus=failed_focus['items'],repaired_episodes=failed_episodes['items'],focus_sector_exposure=exposure,historical_stock=historical['items'][0])
    samples.update(stock=target,charts=charts,sector_id=sector,member_count=len(members),focus_id=fid,focus_layer_counts={k:len(v) for k,v in focuslayers.items()})
    write(OUT/'API_FIELD_CONTRACT_AUDIT.json',dict(contract_id='CORE_PRODUCT_API_FIELD_AUDIT_R2',observed_at=datetime.now(timezone.utc).isoformat(),context=context['context'],routes=audit,charts=charts,negatives=negatives,extra=extra,errors=errors,acceptance='API_BINDING_SCOPED_PASS' if not errors else 'FAIL',production_reload='NOT_PERFORMED',scope='ISOLATED_REAL_ACCEPTED_HEAD; before=running old service'))
    write(OUT/'API_UI_NUMERIC_SAMPLES.json',compact_samples(samples))
    print(json.dumps(dict(routes=len(routes),charts=len(charts),member_count=len(members),errors=errors)))
    return bool(errors)

if __name__=='__main__':raise SystemExit(main())
