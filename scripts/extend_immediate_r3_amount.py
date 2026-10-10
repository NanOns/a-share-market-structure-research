"""Existing prior native rows vs complete frozen BaoStock day responses."""
from immediate_r3_common import *
from collections import Counter
import struct
def main():
    p=OUT/'04_P0_AMOUNT/P0_AMOUNT_SOURCE_COMPARISON.json';pack=load(p);h=load('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');acq=load('docs/evidence/source_acquisition_r4_20261009/capture/acquisition.json');snapshot=load(h['membership_snapshot']);ib={r['security_id']:r['source_security_key'] for r in load(snapshot['identity_source'])['rows']}
    sources=[]
    for day in ('2026-09-30','2026-10-08'):
        q=next(q for q in acq['queries'] if q['method']=='query_daily_history_k_AStock' and q['params']['date']==day and q['status']=='BAOSTOCK_FOUND');ref=binding(q['path']);data=load(ref);bb={r['code'].upper():r for r in data['rows']};nr=h['owners'][day]['raw'];sources.append(dict(trade_date=day,native=nr,baostock=ref,received_at=q['received_at'],PIT_scope='RECONSTRUCTED_CORRECTED; original first availability unproven'))
        for n in load(nr):
            code=ib.get(n['security_id']);b=bb.get(code)
            pack['rows'].append(dict(code=code,trade_date=day,native_amount=n['amount'],native_volume=n['volume'],baostock_amount=b['amount'] if b and b['amount'] else None,baostock_volume=b['volume'] if b and b['volume'] else None,tradestatus=b['tradestatus'] if b else None,adjustflag=b['adjustflag'] if b else None,source_entry='SEE_NATIVE_OWNER_SOURCE_LINEAGE',entry_sha256=nr['sha256']))
    pack['earlier_dates']=sources;write(p,pack)
    print(json.dumps(dict(earlier_dates=[s['trade_date'] for s in sources],total_rows=len(pack['rows']))))
if __name__=='__main__':main()
