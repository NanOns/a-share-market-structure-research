"""Export real source session states for independent exact UNKNOWN reason checks."""
from immediate_r3_common import *
D=OUT/'11_DEEPENING'
def main():
    h=load('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');u=load(OUT/'09_CONTINUATION/UPSTREAM_ORACLE_INPUT.json')
    ref=load('config/v4_sector_operational_authority_v1.json')['sources']['historical_status'];status={}
    for r in load(ref):status[(r['security_id'],r['trade_date'])]=r['status']
    sources=[ref]
    for day,refs in h['source_registry'].items():
        life=load(refs['lifecycle']);sources.append(refs['lifecycle'])
        for r in life['source_rows']:
            if r.get('trading_status')=='0' or r.get('status')=='SUSPENDED':status[(r['security_id'],day)]='SUSPENDED'
    records=[]
    for r in u['records']:
        if not any(c['quality_state']!='OBSERVED' for c in r['actual'].values()):continue
        by={b['trade_date']:b for b in r['bars']};start=r['bars'][0]['trade_date']
        states=[dict(trade_date=d,state='ACTUAL' if by.get(d,{}).get('qfq_ohlc') else 'ADJUSTMENT_UNKNOWN' if d in by else 'CONFIRMED_SUSPENSION' if status.get((r['security_id'],d))=='SUSPENDED' else 'UNKNOWN') for d in u['calendar'] if start<=d<=r['trade_date']]
        records.append(dict(security_id=r['security_id'],trade_date=r['trade_date'],states=states,actual={k:v for k,v in r['actual'].items() if v['quality_state']!='OBSERVED'}))
    write(D/'EXACT_QUALITY_INPUT.json',dict(records=records,sources=sources,upstream=binding(OUT/'09_CONTINUATION/UPSTREAM_ORACLE_INPUT.json'),scope='Real selected 325 core UNKNOWN reasons; no all-detector acceptance'))
    print('quality records',len(records))
if __name__=='__main__':main()
