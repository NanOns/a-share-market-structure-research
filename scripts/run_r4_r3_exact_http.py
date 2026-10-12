"""Actual PG -> typed transport -> chart/Core -> HTTP independent replay."""
from pathlib import Path
import os,sys,json,hashlib,threading,urllib.request,urllib.parse,urllib.error,time
from fractions import Fraction
from decimal import Decimal,ROUND_HALF_UP
from http.server import ThreadingHTTPServer
from datetime import datetime,timezone
import psycopg

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from workbench_service.exact_candidate_chart_r3 import make_exact_candidate_handler,PATH
from workbench_service.core_product_bff_r1 import dated_product_manifest
from workbench_db.v4_history_pg_r1 import read
from workbench_analysis.operational_successor_v1 import accepted_api
from workbench_analysis.r43_owner_replay import checked
from tdx.gbbq_reader import read_gbbq
from workbench_analysis.market_source_acquisition import official_sessions

OUT=Path(os.environ.get('R4_EXACT_EVIDENCE_DIR',str(ROOT/'docs/audits/r4_r3_semantics_http_20261011'))).resolve()
CANDIDATE=Path('G:/codex_tmp/r4_r3_ui_candidate')

def atomic(name,value):
    path=OUT/name;tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(tmp,path)
def oracle_price(raw,day,events,basis):
    price=Fraction(str(raw))
    for event in sorted(events,key=lambda e:(e.event_date,e.source_record_index)):
        if event.category!=1 or not day<event.event_date<=basis:continue
        cash,rights_price,bonus,rights=[Fraction(Decimal(str(v)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)) for v in (event.c1,event.c2,event.c3,event.c4)]
        price=(price*10-cash+rights_price*rights)/(10+bonus+rights)
    whole,remainder=divmod(abs(price.numerator)*100,price.denominator)
    whole+=int(2*remainder>=price.denominator)
    return (-whole if price<0 else whole)/100

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if not os.environ.get('V4_NATIVE_PG_DSN'):raise ValueError('EXPLICIT_ISOLATED_PG_REQUIRED')
    with psycopg.connect(os.environ['V4_NATIVE_PG_DSN']) as pg:
        identity=pg.execute("SELECT current_database(),(SELECT oid FROM pg_database WHERE datname=current_database()),(pg_control_system()).system_identifier,current_setting('data_directory')").fetchone()
        if not identity[3].replace('\\','/').startswith('G:/codex_tmp/'):raise ValueError('ISOLATED_PG_REQUIRED')
    protected=[CANDIDATE/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json',CANDIDATE/'config/core_product_read_authority_r1.json',ROOT/'src/adjustment/tdx_adjustment.py']
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    api=accepted_api(CANDIDATE);day='2026-10-09';sid='SEC-3A5B40C6141461B88CA555E0BB852BDF'
    authority=json.loads((CANDIDATE/'config/core_product_read_authority_r1.json').read_bytes())
    manifest=dated_product_manifest(CANDIDATE,authority,day);rows=read(CANDIDATE,manifest['history_index'],day,sid)
    source=api.candidate['source_registry'][day]['gbbq'];source_path=checked(CANDIDATE,source)
    events=[e for e in read_gbbq(source_path) if e.security_id.upper()=='SH.688553']
    dispositions=json.loads((CANDIDATE/'config/v4_02_gbbq_price_impact_classification_v1.json').read_bytes())['dispositions']
    blocked=[e for e in events if e.event_date<=20261009 and dispositions.get(str(e.category),{}).get('formal_disposition','UNKNOWN_PRICE_IMPACT') in ('PRICE_AFFECTING_UNSUPPORTED','UNKNOWN_PRICE_IMPACT')]
    expected=[]
    for row in rows:
        date=int(row['trade_date'].replace('-',''));known=not any(date<e.event_date for e in blocked)
        prices=[oracle_price(raw,date,events,20261009) for raw in row['raw_ohlc']] if known else [None]*4
        expected.append(dict(trade_date=row['trade_date'],**dict(zip(('open','high','low','close'),prices)),amount=row['amount'],volume=row['volume']))
    server=ThreadingHTTPServer(('127.0.0.1',0),make_exact_candidate_handler(CANDIDATE,None,engineering_enable=True))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();port=server.server_address[1]
    receipts=[];additional_oracles=[]
    def request(query):
        url=f'http://127.0.0.1:{port}{PATH}?'+urllib.parse.urlencode(query);started=time.perf_counter()
        try:
            with urllib.request.urlopen(url,timeout=120) as response:code=response.status;raw=response.read()
        except urllib.error.HTTPError as error:code=error.code;raw=error.read()
        value=json.loads(raw);receipt=dict(query=query,status=code,elapsed_seconds=time.perf_counter()-started,body_sha256=hashlib.sha256(raw).hexdigest(),response=value)
        receipts.append(receipt);atomic('HTTP_RAW_RECEIPTS.json',receipts);return code,value
    try:
        q=dict(context_token=api.token,trade_date=day,security_id=sid,period='D',limit=200)
        code,value=request(q);assert code==200
        actual=value['items'];assert actual==[{**row,'quality':'KNOWN' if row['close'] is not None else 'UNKNOWN','reason':None if row['close'] is not None else 'BLOCKED_ADJUSTMENT_EVENT'} for row in expected[-200:]]
        for n in (5,20,60):
            target=sum(Fraction(str(row['close'])) for row in expected[-n:])/n
            assert abs(value['core']['ma'+str(n)]['value']-float(target))<1e-10
        calendar=[d for d in official_sessions(CANDIDATE) if rows[0]['trade_date']<=d<=day];by_day={r['trade_date']:r for r in expected}
        for n in (1,3,5,20):
            start=calendar[-n-1]
            if start in by_day:
                target=float(Fraction(str(expected[-1]['close']))/Fraction(str(by_day[start]['close']))-1)
                assert abs(value['core']['ret'+str(n)]['value']-target)<1e-10
        params=json.loads((ROOT/'config/v4_04_parameter_set_v1.json').read_bytes())['parameters']
        thresholds={row['parameter_id'].removeprefix('V4_04_'):row['value'] for row in params}
        for name in ('amount','volume'):
            ratio=value['core'][name+'_ratio20']['value']
            target=('VERY_DRY' if ratio<thresholds['RATIO_VERY_DRY'] else 'CONTRACTED' if ratio<thresholds['RATIO_CONTRACTED'] else
                'NORMAL' if ratio<thresholds['RATIO_NORMAL'] else 'EXPANDED' if ratio<thresholds['RATIO_EXPANDED'] else 'VERY_EXPANDED')
            assert value['profile_states'][name+'_state']['value']==target
        for horizon in (20,60):
            distance=(value['core']['prior_high'+str(horizon)]['value']-expected[-1]['close'])/value['core']['atr20']['value']
            target='ABOVE_PRIOR_HIGH' if distance<0 else 'NEAR' if distance<=thresholds['NEAR_HIGH_ATR'] else 'BELOW'
            assert value['profile_states']['near_high'+str(horizon)+'_state']['value']==target
        primitives=value['profile_primitives']
        compress=[value['core'][field]['value'] for field in ('range_ratio','atr_ratio','vol_ratio','amount_ratio20')]
        liquid=primitives['minimum_liquidity']['value']
        if any(item is None for item in compress) or liquid is None:compress_expected='UNKNOWN'
        else:
            ran,atr,vol,amount=compress
            if atr>=thresholds['COMPRESS_EXTREME'] or vol>=thresholds['COMPRESS_EXTREME']:compress_expected='EXPANDING_EXTREME'
            elif atr>=thresholds['COMPRESS_EXPAND'] or vol>=thresholds['COMPRESS_EXPAND']:compress_expected='EXPANDING'
            elif ran<=thresholds['COMPRESS_STRONG_RANGE'] and atr<=thresholds['COMPRESS_STRONG_ATR_VOL'] and vol<=thresholds['COMPRESS_STRONG_ATR_VOL'] and amount<=thresholds['COMPRESS_STRONG_AMOUNT'] and liquid:compress_expected='COMPRESSING_STRONG'
            elif ran<=thresholds['COMPRESS_RANGE'] and atr<=thresholds['COMPRESS_ATR_VOL'] and vol<=thresholds['COMPRESS_ATR_VOL'] and liquid:compress_expected='COMPRESSING'
            else:compress_expected='NORMAL'
        assert value['profile_states']['compression_state']['value']==compress_expected
        ma10=sum(Fraction(str(row['close'])) for row in expected[-10:])/10
        assert abs(primitives['ma10']['value']-float(ma10))<1e-12
        high250=max(Fraction(str(row['high'])) for row in expected[-250:]);low250=min(Fraction(str(row['low'])) for row in expected[-250:])
        pos250=(Fraction(str(expected[-1]['close']))-low250)/(high250-low250)
        assert abs(primitives['pos250']['value']-float(pos250))<1e-12
        bias=(Fraction(str(expected[-1]['close']))-Fraction(str(value['core']['ma20']['value'])))/Fraction(str(value['core']['atr20']['value']))
        assert abs(primitives['bias20_atr']['value']-float(bias))<1e-12
        focus=value['focus_path'];assert focus['status']=='READY' and focus['PIT_ELIGIBLE'] is False
        path=[by_day[d] for d in calendar[-21:]];initial=Fraction(str(path[0]['close']));peak=initial;worst=Fraction(0)
        for bar in path:
            close=Fraction(str(bar['close']));peak=max(peak,close);worst=min(worst,close/peak-1)
        targets=dict(return_close=Fraction(str(path[-1]['close']))/initial-1,
            mfe=max(Fraction(str(bar['high'])) for bar in path)/initial-1,
            mae=min(Fraction(str(bar['low'])) for bar in path)/initial-1,
            peak_close=peak,drawdown_current=Fraction(str(path[-1]['close']))/peak-1,mdd_close=worst)
        for field,target in targets.items():assert abs(float(focus['metrics'][field])-float(target))<1e-12
        # Independent Python bucket grouping; no aggregate helper used.
        for period in ('W','M'):
            code,value=request(dict(q,period=period));assert code==200 and not value['PIT_ELIGIBLE']
            from datetime import date
            buckets={}
            for row in expected:
                d=date.fromisoformat(row['trade_date']);key=d.isocalendar()[:2] if period=='W' else (d.year,d.month)
                buckets.setdefault(key,[]).append(row)
            oracle=[]
            for key,bucket in sorted(buckets.items()):
                oracle.append(dict(open=bucket[0]['open'],high=max(r['high'] for r in bucket),low=min(r['low'] for r in bucket),close=bucket[-1]['close'],amount=sum(r['amount'] for r in bucket),volume=sum(r['volume'] for r in bucket)))
            assert [{key:row[key] for key in oracle[0]} for row in value['items']]==oracle[-200:]
        for negative in [dict(q,context_token='0'*64),dict(q,period='X'),dict(q,limit=201),dict(q,trade_date='2026-10-12')]:
            code,value=request(negative);assert code==400
        frozen=json.loads((ROOT/'docs/audits/full_system_audit_r2_20261011_58faf74e/b2_rounding_counterexamples.json').read_bytes())['rows']
        for other_sid in sorted({r['sid'] for r in frozen}-{sid}):
            code,value=request(dict(q,security_id=other_sid));assert code==200
            other_rows=read(CANDIDATE,manifest['history_index'],day,other_sid)
            other_events=[e for e in read_gbbq(source_path) if e.security_id.upper()==value['symbol'].upper()]
            checked_cells=0
            for raw_row,actual in zip(other_rows[-200:],value['items']):
                date=int(raw_row['trade_date'].replace('-',''))
                if actual['quality']!='KNOWN':continue
                for name,raw in zip(('open','high','low','close'),raw_row['raw_ohlc']):
                    target=oracle_price(raw,date,other_events,20261009)
                    assert actual[name]==target;checked_cells+=1
            additional_oracles.append(dict(security_id=other_sid,symbol=value['symbol'],ohlc_cells=checked_cells,differences=0,core_returned=len(value['core'])))
        old_dsn=os.environ['V4_NATIVE_PG_DSN'];os.environ['V4_NATIVE_PG_DSN']='host=127.0.0.1 port=1 user=invalid dbname=invalid connect_timeout=1'
        code,value=request(q);assert code==503 and value['reason']=='PG_REQUIRED_NO_FALLBACK';os.environ['V4_NATIVE_PG_DSN']=old_dsn
    finally:server.shutdown();server.server_close();thread.join()
    after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected};assert before==after
    files=['src/workbench_service/exact_candidate_chart_r3.py','src/focus_tracker/exact_path_candidate_r3.py','src/focus_tracker/price_path.py','src/adjustment/exact_factor_transport_r1.py','src/adjustment/exact_ohlc_consumer_r1.py','src/v4/factors/core.py','src/v4/profile_core.py','src/v4/profile_primitives.py','config/v4_04_parameter_set_v1.json','scripts/run_r4_r3_exact_http.py']
    atomic('HTTP_CORE_INDEPENDENT_ORACLE.json',dict(contract_id='R4_R3_REAL_PG_EXACT_HTTP_CORE_ORACLE_R1',run_utc=datetime.now(timezone.utc).isoformat(),
        source_head=os.popen('git rev-parse HEAD').read().strip(),sources={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files},
        database_identity=identity,gbbq_source=source,history_index=manifest['history_index'],actual_http_requests=len(receipts),
        oracle_ohlc_cells=len(expected)*4+sum(row['ohlc_cells'] for row in additional_oracles),additional_securities=additional_oracles,oracle_price_difference=0,core_oracles=['ma5','ma20','ma60','ret1','ret3','ret5','ret20'],
        period_oracles=['W','M'],focus_path_oracles=list(targets),profile_primitives_oracles=['ma10','pos250','bias20_atr'],profile_oracles=['amount_state','volume_state','near_high20_state','near_high60_state','compression_state'],negative_cases=5,protected_before=before,protected_after=after,status='SCOPED_PASS',
        full_56_consumers='OPEN',formal_pit='NOT_GRANTED',production_loaded=False))
    print(json.dumps(dict(requests=len(receipts),ohlc_cells=len(expected)*4,status='SCOPED_PASS')))

if __name__=='__main__':main()
