"""Independent byte decoding and accepted-source read-domain checks."""
import json, struct, sys, zipfile
from collections import Counter
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.joint_release import checked_path
from workbench_service.research_bff import ResearchBFF
OUT=ROOT/'docs/evidence/r2_read_domains_continuation_20261008'

def main():
    r=ProductionV4ResearchReader(ROOT);m=r.manifest['domain_features']['market_center']
    raw=json.loads(checked_path(ROOT,m['sources']['RAW_DAILY']).read_bytes())['rows'];prices={x['security_id']:x for x in raw}
    limits=json.loads(checked_path(ROOT,m['sources']['PRICE_LIMIT']).read_bytes())['rows'];counts=Counter();breadth=Counter();classified=0
    for x in limits:
        counts[x['limit_status']]+=1;p=prices.get(x['security_id'])
        if p and x['trading_status']=='ACTUAL_TRADED' and x['reference_price'] is not None:
            delta=Decimal(str(p['close']))-Decimal(x['reference_price']);breadth['up' if delta>0 else 'down' if delta<0 else 'flat']+=1
        else:breadth['unknown']+=1
        if p and x['limit_up_price'] and x['limit_down_price'] and x['trading_status']=='ACTUAL_TRADED':
            close=Decimal(str(p['close']));expected='LIMIT_UP' if close==Decimal(x['limit_up_price']) else 'LIMIT_DOWN' if close==Decimal(x['limit_down_price']) else 'NOT_LIMIT'
            assert expected==x['limit_status'];classified+=1
    assert dict(counts)==m['limits']['counts']
    for k,v in breadth.items():assert m['breadth'][k]==v
    assert sum(breadth.values())==m['breadth']['denominator']==len(limits)
    assert float(sum(Decimal(str(x['amount'])) for x in raw))==m['breadth']['amount_cny']
    bars=0
    with zipfile.ZipFile(checked_path(ROOT,m['sources']['index_archive'])) as z:
        for index in m['indices']:
            data=z.read(index['source_member']);decoded=[]
            for off in range(0,len(data),32):
                day,o,h,l,c,amount,volume,_=struct.unpack('<IIIIIfII',data[off:off+32]);day=str(day);day=day[:4]+'-'+day[4:6]+'-'+day[6:]
                if day<=m['trade_date']:decoded.append(dict(trade_date=day,open=o/100,high=h/100,low=l/100,close=c/100,amount=amount,volume=volume,quality='KNOWN'))
            assert decoded[-120:]==index['bars'];bars+=len(index['bars'])
    dated={day.removeprefix('limits_'):json.loads(checked_path(ROOT,b).read_bytes())['rows'] for day,b in m['sources'].items() if day.startswith('limits_')}
    for item in m['ladders']:
        seq=[]
        for day in sorted(dated,reverse=True):
            x=next((x for x in dated[day] if x['security_id']==item['entity_id']),None);seq.append(x['limit_status'] if x else None)
        n=next((i for i,x in enumerate(seq) if x!='LIMIT_UP'),len(seq))
        exact=n if n<len(seq) and seq[n] not in (None,'UNKNOWN') else None
        assert item['consecutive_limit_up_lower_bound']==n and item['exact_streak']==exact
    bff=ResearchBFF(ROOT);responses={}
    for path in ['market/indices','market/breadth','market/limits','market/ladders']+['diagnostics/'+x for x in ('health','sources','contracts','jobs','legacy','shadow')]+['home']:
        code,data=bff.get('/api/v4/'+path,{'limit':'200'});assert code==200;responses[path]=data
    write(OUT/'READ_EXPECTED.json',responses)
    write(OUT/'SOURCE_ORACLE.json',dict(result='PASS',index_bars=bars,classified_price_limits=classified,limit_source_rows=len(limits),raw_amount_rows=len(raw),ladder_prefixes=len(m['ladders']),breadth=dict(breadth),scope='ACCEPTED_PRICE_LIMIT_CLASSIFICATION_NOT_INDEPENDENT_EXCHANGE_RULE_AUDIT',sources=m['sources'],tdx_readonly=True,strict_pit=False))
    print(json.dumps(dict(result='PASS',bars=bars,classified=classified)))
if __name__=='__main__':main()
