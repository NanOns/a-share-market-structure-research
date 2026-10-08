"""Actual accepted compression, risk and dated-reference numeric oracles."""
import collections,gzip,json,math,sqlite3,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.joint_release import checked_path
OUT=ROOT/'docs/evidence/r2_available_fields_continuation_20261008'

def records(binding):
    with gzip.open(checked_path(ROOT,binding),'rt',encoding='utf8') as stream:return [json.loads(line) for line in stream]

def risk(e,p):
    bias=e.get('bias20_atr')
    if isinstance(bias,(int,float)):
        if bias>=p['EXTENSION_EXTREME']:return 'EXTREME'
        if bias>=p['EXTENSION_HIGH']:return 'HIGH'
    if any(not isinstance(e.get(k),(int,float)) for k in ('bias20_atr','ret5','atr20','close','amount_ratio20','ret1')) or e['close']<=0:return 'UNKNOWN'
    if e['ret5']>=p['EXTENSION_RET5_ATR']*e['atr20']/e['close'] and e['amount_ratio20']>=p['EXTENSION_AMOUNT'] and e['ret1']<=0:return 'HIGH'
    return 'MEDIUM' if bias>=p['EXTENSION_MEDIUM'] else 'LOW'

def main():
    c=json.loads((OUT/'CANDIDATE.json').read_bytes());r=ProductionV4ResearchReader(ROOT,snapshot_authority=c['snapshot']);day=r.context['trade_date']
    authority=r.manifest['domain_features']['stocks'];factors={x['security_id']:x for x in records(authority['factors'])};profiles={x['security_id']:x for x in records(authority['profiles'])}
    p={x['parameter_id'].removeprefix('V4_04_'):x['value'] for x in json.loads((ROOT/'config/v4_04_parameter_set_v1.json').read_bytes())['parameters']}
    literals=json.loads((ROOT/'config/v4_03_parameter_set_v1.json').read_bytes())['contract_literals']
    market=json.loads(checked_path(ROOT,r.manifest['domain_features']['sector']['sources']['market']).read_bytes());bindings=market['sources']
    calendar=json.loads(checked_path(ROOT,bindings['calendar']).read_bytes())['session_dates'];wanted={n:calendar[calendar.index(day)-n] for n in (1,3,5)}
    universe={d:set() for d in wanted.values()}
    for x in records(bindings['historical_universe']):
        if x['trade_date'] in universe:universe[x['trade_date']].add(x['security_id'])
    for key,binding in bindings.items():
        if key.endswith(':IDENTITY_UNIVERSE') and key.split(':')[0] in universe:
            universe[key.split(':')[0]]={x['security_id'] for x in json.loads(checked_path(ROOT,binding).read_bytes())['rows'] if x['board_scope'] in ('SH_MAIN','SZ_MAIN','STAR','CHINEXT')}
    references={}
    for n,start in wanted.items():
        ids=universe[start];values=[factors[s]['fields']['ret'+str(n)]['value'] for s in ids if s in factors and factors[s]['fields']['ret'+str(n)]['value'] is not None]
        missing=len(ids)-len(values);reference=statistics.mean(values) if values and missing/len(ids)<=literals['market_reference_max_missing_fraction'] else None
        references[n]=dict(value=reference,start_date=start,universe_count=len(ids),evaluable_count=len(values),missing_count=missing)
    counts=collections.Counter();unknown=collections.Counter()
    with sqlite3.connect(r.path.as_uri()+'?mode=ro',uri=True) as db,sqlite3.connect(checked_path(ROOT,authority['series']).as_uri()+'?mode=ro',uri=True) as series:
        for payload, in db.execute('SELECT payload FROM objects WHERE domain=?',('stocks',)):
            item=json.loads(payload);sid=item['entity_id'];fields=item['fields'];factor=factors[sid]['fields']
            bars=[json.loads(p) for p, in series.execute('SELECT payload FROM bars WHERE security=? AND day<=? ORDER BY day DESC LIMIT 21',(sid,day))]
            for n in (1,3,5):
                key='rel_market_'+str(n);refvalue=references[n]['value'];ret=factor['ret'+str(n)]['value'];expected=ret-refvalue if ret is not None and refvalue is not None else None
                actual=fields[key]['value'];assert expected is None and actual is None or math.isclose(expected,actual,rel_tol=1e-12,abs_tol=1e-12),(sid,key)
                if actual is None:unknown[key]+=1
                else:counts[key]+=1
                metadata=factor[key]['reference'];assert metadata['universe_count']==references[n]['universe_count'] and metadata['evaluable_count']==references[n]['evaluable_count']
            compression_fields=('range_ratio','atr_ratio','vol_ratio')
            if all(fields[k]['value'] is not None for k in compression_fields):
                assert len(bars)==21 and all(b['qfq_ohlc'] for b in bars)
                prices=[list(map(float,b['qfq_ohlc'])) for b in reversed(bars)]
                ranges={n:max(x[1] for x in prices[-n:])-min(x[2] for x in prices[-n:]) for n in (5,20)}
                trs=[max(b[1]-b[2],abs(b[1]-a[3]),abs(b[2]-a[3])) for a,b in zip(prices,prices[1:])]
                logs=[math.log(b[3]/a[3]) for a,b in zip(prices,prices[1:])]
                expected=dict(range_ratio=ranges[5]/ranges[20],atr_ratio=(sum(trs[-5:])/5)/(sum(trs)/20),vol_ratio=statistics.pstdev(logs[-5:])/statistics.pstdev(logs))
                for key,value in expected.items():assert math.isclose(value,fields[key]['value'],rel_tol=1e-10,abs_tol=1e-10),(sid,key,value,fields[key]['value']);counts[key]+=1
            else:unknown['compression_composite']+=1
            damage=fields['core_price_damage']['value']
            if isinstance(damage,bool):
                assert len(bars)==21 and all(b['qfq_ohlc'] for b in bars)
                prices=[list(map(float,b['qfq_ohlc'])) for b in reversed(bars)]
                atr=sum(max(b[1]-b[2],abs(b[1]-a[3]),abs(b[2]-a[3])) for a,b in zip(prices,prices[1:]))/20
                expected=prices[-1][3]<min(b[2] for b in prices[:-1])-literals['core_price_damage_atr_multiple']*atr and prices[-1][3]/prices[-2][3]-1<0
                assert expected==damage;counts['core_price_damage']+=1
            else:unknown['core_price_damage']+=1
            expected_risk=risk(profiles[sid]['states']['core_extension_risk']['evidence'],p)
            assert fields['core_extension_risk']['value']==expected_risk
            counts['core_extension_risk']+=1
            assert fields['regime_ui']['value']==market['regime']['value'];counts['market_regime']+=1
    write(OUT/'STOCK_FACT_ORACLE.json',dict(result='PASS',known_comparisons=dict(counts),unknown_preserved=dict(unknown),market_references=references,
        source_factor=authority['factors'],source_profile=authority['profiles'],series=authority['series'],market=r.manifest['domain_features']['sector']['sources']['market'],
        parameters=[ref('config/v4_03_parameter_set_v1.json'),ref('config/v4_04_parameter_set_v1.json')],strict_pit=False,scope='CORRECTED_ACCEPTED_OWNER_UNIVERSES_EXPLICITLY_SEPARATE_FROM_CURRENT_RAW_DISPLAY_POOL'))
    print(json.dumps(dict(result='PASS',comparisons=sum(counts.values()),unknown=dict(unknown))))

if __name__=='__main__':main()
