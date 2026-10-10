"""Actual loopback API/source comparisons for current snapshot deepening."""
from immediate_r3_common import *
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError
from statistics import median
D=OUT/'11_DEEPENING'
BASE='http://127.0.0.1:28767/api/v4/'
rows=[];fail=[]

def request(route,**q):
    try:r=urlopen(BASE+route+'?'+urlencode(q),timeout=90)
    except HTTPError as e:r=e
    data=json.load(r);return r.status,data

def main():
    _,context=request('context');token=context['context_token'];day=context['context']['trade_date'];q=dict(context_token=token,trade_date=day)
    def get(route,**params):
        status,d=request(route,**dict(q,**params))
        rows.append(dict(route=route,params=params,http_status=status,status=d.get('status'),total=d.get('total'),as_of=d.get('context',{}).get('trade_date'),source=d.get('source')))
        return status,d
    def check(name,condition,evidence=None):
        if not condition:fail.append(dict(check=name,evidence=evidence))
    _,allsectors=get('sectors',limit=200);_,other=get('sectors',limit=200,offset=200);sectors=allsectors['items']+other['items']
    check('all sectors pagination',len(sectors)==allsectors['total']==len({r['entity_id'] for r in sectors}))
    for typ in ('INDUSTRY','THEME'):
        _,filtered=get('sectors',type=typ,limit=200)
        check('full sector type filter '+typ,filtered['total']==sum(r['fields']['sector_type']['value']==typ for r in sectors))
    _,unknown=get('sectors',maturity='UNKNOWN',health='UNKNOWN',limit=200)
    check('unknown filters distinct source incomplete',unknown['total']==len(sectors) and all(r['fields']['maturity']['quality']=='SOURCE_INCOMPLETE' for r in unknown['items']))
    _,sortedrows=get('sectors',sort='-member_count',limit=200)
    expected=sorted(sectors,key=lambda r:(-r['fields']['member_count']['value'],r['entity_id']))
    check('full dataset sorting', [r['entity_id'] for r in sortedrows['items']]==[r['entity_id'] for r in expected[:200]])
    sid='INDUSTRY:T0706';members=[]
    for offset in range(0,400,100):
        _,d=get('sectors/'+sid+'/members',limit=100,offset=offset);members.extend(d['items'])
    check('member conservation',len(members)==d['total']==len({r['entity_id'] for r in members}))
    head=load('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');native=load(head['owners'][day]['sector']);subject=next(r for r in native if r['sector_id']==sid)
    check('member exact owner equality',set(subject['member_ids'])=={r['entity_id'] for r in members})
    _,timeline=get('sectors/'+sid+'/timeline',limit=200)
    check('timeline exact session dates',[r['trade_date'] for r in timeline['items']]==head['published_sessions'])
    _,overlap=get('sectors/'+sid+'/overlap',limit=200)
    target=set(subject['member_ids']);expected_overlap={r['sector_id']:len(target&set(r['member_ids']))/len(target|set(r['member_ids'])) for r in native if r['sector_id']!=sid and r['sector_type']=='THEME' and target&set(r['member_ids'])}
    check('overlap unique member jaccard',all(r['jaccard']==expected_overlap[r['sector_id']] for r in overlap['items']) and overlap['total']==len(expected_overlap))
    _,profile=get('stocks/301628/profile');hyp=profile['competitive_hypotheses'];check('real H explanations',hyp['status']=='READY' and len(hyp['items'])==2,hyp)
    check('H consistent price basis',hyp['evidence']['close']['adjustment_basis']==hyp['evidence']['ma20']['adjustment_basis'])
    _,cohort=get('forward/statistics');check('cohort absent not zero',cohort['status']=='SOURCE_INCOMPLETE' and cohort['data']['observed_count'] is None and cohort['data']['matured_count'] is None and not cohort['focus_is_validation_cohort'])
    _,fep=get('forward/fep');check('FEP explicit denial',fep['status']=='SOURCE_INCOMPLETE' and len(fep['data']['required_grant_key'])==6 and all(v=='NOT_GRANTED' for v in fep['data']['capabilities'].values()) and fep['data']['prediction'] is None and not fep['data']['focus_write_authorized'])
    _,settlement=get('forward/settlement');check('settlement absent not zero',settlement['total'] is None and settlement['data']['outcomes'] is None and not settlement['focus_is_validation_cohort'])
    _,current_stock=get('stocks/688349/profile');_,old_stock=get('stocks/688349/profile',trade_date='2026-09-30')
    old_raw=next(r for r in load(head['owners']['2026-09-30']['raw']) if r['security_id']==old_stock['item']['entity_id'])
    check('historical profile survives missing adjusted domain',old_stock['item']['fields']['close']['value']==old_raw['close'] and old_stock['context']['trade_date']=='2026-09-30')
    check('historical H does not use current adjusted source',old_stock['competitive_hypotheses']['status']=='SOURCE_INCOMPLETE')
    _,focus=get('focus',limit=200);_,home=get('home');_,breadth=get('market/breadth');_,health=get('diagnostics/health')
    raw=load(head['owners'][day]['raw']);check('market raw amount sum',breadth['data']['amount_cny']==sum(r['amount'] for r in raw))
    sidstock=profile['item']['entity_id'];rawstock=next(r for r in raw if r['security_id']==sidstock)
    check('stock raw amount binding',profile['item']['fields']['amount']['value']==rawstock['amount'])
    nativecell=subject['fields']['participation_proxy'];_,sectorview=get('sectors/'+sid)
    field=sectorview['item']['fields']['participation_proxy'];check('sector proxy exact source',field['value']==nativecell['value'])
    sector_sources=[]
    for d in head['published_sessions']:
        sector_sources.append(dict(trade_date=d,owner=head['owners'][d]['sector'],first_available='NOT_PROVEN_FOR_HISTORICAL_T0'))
    check('no future timeline',all(r['trade_date']<=day for r in timeline['items']))
    # Source family audit: known ratio, unknown quality, no relabelling to Amount A.
    amount_binding=dict(stock=dict(raw=rawstock,amount=profile['item']['fields']['amount'],ratio20=profile['item']['fields']['amount_ratio20']),
      sector=dict(sector_id=sid,participation_proxy=field,source=head['owners'][day]['sector'],is_Amount_A=False),
      market=dict(data=breadth['data'],source=breadth.get('source'),is_Amount_A=False),
      formal_Amount_A=dict(read_domain='data/v4/a04_go_forward_r3',status='H21_OBSERVATION_GAP',production_consumer_enabled=False))
    write(D/'AMOUNT_FIELD_FAMILY_API_BINDINGS.json',amount_binding)
    numeric=dict(home=dict(net_information_count=home['net_information_count'],source=home['source_bindings'],scope=home['change_scope']),
      sectors=dict(member_count=len(target),participation_proxy=field),stocks=dict(close=profile['item']['fields']['close'],amount=profile['item']['fields']['amount']),
      focus=dict(total=focus['total'],exposure=focus['sector_exposure']),market=dict(breadth=breadth['data'],source=breadth.get('source')),
      diagnostics=dict(items=health['items']),cohort=cohort,hypotheses=hyp,fep=fep,settlement=settlement,
      historical_stock=dict(context=old_stock['context'],close=old_stock['item']['fields']['close'],hypotheses=old_stock['competitive_hypotheses']),current688349=current_stock['item']['fields']['close'])
    write(D/'SIX_ENTRY_NUMERIC_SOURCE_BINDINGS.json',numeric)
    negatives=[]
    for name,route,params,expected in [('stale','stocks',dict(context_token='STALE',trade_date=day),409),('future','stocks',dict(q,trade_date='2026-10-12'),400),('sort_injection','stocks',dict(q,sort='amount_a'),400),('bad_offset','stocks',dict(q,offset=-1),400)]:
        status,d=request(route,**params);negatives.append(dict(name=name,status=status,expected=expected,data=d));check(name,status==expected,d)
    write(OUT/'06_P1_PRODUCT_QA/P1_PRODUCT_NEGATIVE_TESTS.json',dict(actual_http=negatives,fixture_transport_separate=True))
    write(OUT/'06_P1_PRODUCT_QA/P1_PRODUCT_FP_REGRESSION_MATRIX.json',dict(contract='R3_DEEPENING_API_SOURCE_QA_V1',T0=day,rows=rows,failures=fail,status='PASS_SCOPED' if not fail else 'FAIL',six_entry_source_samples=binding(D/'SIX_ENTRY_NUMERIC_SOURCE_BINDINGS.json')))
    print(json.dumps(dict(routes=len(rows),failures=fail),ensure_ascii=False))
    return bool(fail)
if __name__=='__main__':raise SystemExit(main())
