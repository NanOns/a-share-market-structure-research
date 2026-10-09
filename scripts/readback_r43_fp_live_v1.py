import sys,json,hashlib
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.scoped_successor_r421 import atomic,canonical,sha
from workbench_analysis.r43_operational_publication import rows
OUT=ROOT/'docs/evidence/r43_r2_fp_entry_20261009';BASE='http://127.0.0.1:28765'

def main():
    records=[]
    def read(path):
        try:
            with urlopen(BASE+path,timeout=180) as response:raw=response.read();code=response.status
        except HTTPError as error:raw=error.read();code=error.code
        value=json.loads(raw) if path.startswith('/api/') else {'bytes':len(raw)}
        records.append(dict(url=BASE+path,status=code,sha256=hashlib.sha256(raw).hexdigest(),payload=value))
        return value
    context=read('/api/v4/context');token=context['context_token'];status=read('/api/operations/status')
    assert status['service_control_contract']=='V4_CONTROL_STATUS_NAMESPACES_V2'
    assert status['last_accepted_trade_date']==context['context']['accepted_trade_date']=='2026-10-08'
    assert status['data_head_digest']==sha(ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json')
    assert read('/api/v4/original-0930/context')['context']['accepted_trade_date']=='2026-09-30'
    read('/v4')
    stock=read('/api/v4/stocks?limit=1&context_token='+token)['items'][0]['entity_id']
    sector=read('/api/v4/sectors?limit=1&context_token='+token)['items'][0]['entity_id']
    paths=['home','stocks?limit=30','sectors?limit=30','focus?limit=30','focus/events?limit=1','market','market/breadth','market/indices','market/limits','market/ladders','events?limit=1',
           'sources?limit=1','diagnostics/sources','diagnostics/health','diagnostics/fep','forward','forward/statistics','forward/plans','forward/fep','forward/settlement',
           'replay','compare','stocks/'+stock,'stocks/'+stock+'/profile','stocks/'+stock+'/chart?period=D&price_basis=QFQ',
           'sectors/'+sector,'sectors/'+sector+'/members?limit=1','sectors/'+sector+'/timeline','sectors/'+sector+'/overlap']
    for path in paths:read('/api/v4/'+path+('&' if '?' in path else '?')+'context_token='+token)
    read('/api/v4/stocks?context_token=wrong');read('/api/v4/stocks?trade_date=2026-10-09&context_token='+token)
    head=json.loads((ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
    owners=head['owners']['2026-10-08']
    quotes=rows(ROOT,owners['raw']);native_sectors=rows(ROOT,owners['sector'])
    quote=next(r for r in quotes if r['security_id']==stock)
    native_sector=next(r for r in native_sectors if r['sector_id']==sector)
    stock_api=next(r['payload']['item'] for r in records if r['url'].split('?')[0]==BASE+'/api/v4/stocks/'+stock)
    sector_api=next(r['payload']['item'] for r in records if r['url'].split('?')[0]==BASE+'/api/v4/sectors/'+sector)
    assert float(stock_api['fields']['close']['value'])==float(quote['close'])
    assert sector_api['fields']['member_count']['value']==native_sector['current_member_count']
    sample=dict(stock=dict(entity_id=stock,close=quote['close'],source=owners['raw']),
                sector=dict(entity_id=sector,member_count=native_sector['current_member_count'],source=owners['sector']),
                result='REAL_OWNER_API_VALUE_EQUALITY_PASS',raw_count=len(quotes))
    entries=json.loads((OUT/'ENTRY_STAGE_CONTRACT.json').read_bytes());protected={p:sha(ROOT/p) for p in entries['protected']};assert protected==entries['protected']
    atomic(OUT/'LIVE_HTTP_AND_RESTART_READBACK.json',canonical(dict(contract_id='R43_FP_LIVE_READBACK_V1',
        observed_at=datetime.now(timezone.utc).isoformat(),status='SCOPED_ADAPTER_LIVE_READBACK_PASS',records=records,
        production_head_changed=False,protected=protected,owner_samples=sample,accepted_trade_date='2026-10-08',legacy_date='2026-09-30',
        FP_full_acceptance=False,independent_external_acceptance=False)))
    print(json.dumps(dict(HTTP=len(records),source_incomplete=[r['url'] for r in records if r['payload'].get('status')=='SOURCE_INCOMPLETE'],errors=[dict(url=r['url'],code=r['status']) for r in records if r['status']!=200]),ensure_ascii=True))

if __name__=='__main__':main()
