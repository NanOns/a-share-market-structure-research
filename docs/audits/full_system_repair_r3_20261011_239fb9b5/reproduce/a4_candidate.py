"""Opt-in exact v0.3 candidate; accepted files and historical audit bytes stay read-only."""
from pathlib import Path
import sys,os,json,gzip,hashlib,time,struct,zipfile
from decimal import Decimal
from fractions import Fraction
ROOT=Path('G:/codex work/大A交易');BASE=Path('G:/codex_tmp/full_system_repair_r3_239fb9b5');OUT=ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
source=ROOT/'docs/audits/full_system_audit_r2_20261011_58faf74e/reproduce/b2_full_native_oracle.py'
code=source.read_text(encoding='utf8');prefix=code[:code.index('cores={};')].replace("BASE=Path('G:/codex_tmp/full_system_audit_r2_58faf74e')",f"BASE=Path({str(BASE)!r})")
ns={};exec(compile(prefix,str(source),'exec'),ns)
from adjustment.tdx_adjustment_v0_3 import build_affine_factors,XrxdEvent,ADJUSTMENT_VERSION
from decimal import ROUND_HALF_UP
started=time.perf_counter();owner=ns['owners'][-1];history_path=ns['read'](owner['history']);target=int(owner['trade_date'].replace('-',''))
with gzip.open(ns['read'](owner['core']),'rt',encoding='utf8') as stream:
    core={r['security_id']:r for r in map(json.loads,stream)}
keys={sid:r['source_security_key'].lower().replace('.','') for sid,r in core.items()}
events=ns['events'];dispositions=ns['dispositions'];deltas=[];stocks=bars_count=cells=0;oracle_mismatches=0
candidate=BASE/'candidate_v0_3_history.jsonl.gz';temporary=candidate.with_suffix('.tmp')
current_delta=[];window_impacts=[]
def oracle(raw,day,evs):
    v=Fraction(Decimal(str(raw)))
    for ex,index,cat,params in evs:
        if cat!=1 or not day<ex<=target:continue
        cash,rp,bonus,rights=[Fraction(Decimal(str(x)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)) for x in params]
        v=(v*10-cash+rp*rights)/(10+bonus+rights)
    q,r=divmod(abs(v.numerator)*100,v.denominator);q+=int(2*r>=v.denominator)
    return (-q if v<0 else q)/100
with temporary.open('wb') as rawout,gzip.GzipFile(fileobj=rawout,mode='wb',mtime=0) as output,gzip.open(history_path,'rt',encoding='utf8') as stream:
    for line in stream:
        row=json.loads(line);sid=row['security_id'];key=keys[sid];bars=row['bars'];evs=events[key]
        admitted=[]
        for ex,index,cat,params in evs:
            if cat==1 and ex<=target:
                values=[Decimal(str(x)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) for x in params]
                admitted.append(XrxdEvent(sid,ex,*values,source_record_index=index))
        dates=[int(b['trade_date'].replace('-','')) for b in bars]
        factors=build_affine_factors(dates+[target],admitted)
        changed=[]
        for i,(bar,day) in enumerate(zip(bars,dates)):
            factor=factors[day];original=bar['qfq_ohlc']
            barriers=any(day<ex<=target and dispositions.get(str(cat),{}).get('formal_disposition','UNKNOWN_PRICE_IMPACT') in ('UNKNOWN_PRICE_IMPACT','PRICE_AFFECTING_UNSUPPORTED') for ex,_,cat,_ in evs)
            assert (original is None)==barriers
            if original is not None:
                actual=[float(factor.qfq_price(Decimal(str(v)))) for v in bar['raw_ohlc']]
                expected=[oracle(v,day,evs) for v in bar['raw_ohlc']]
                oracle_mismatches+=sum(a!=e for a,e in zip(actual,expected));cells+=4
                for col,(a,old) in enumerate(zip(actual,original)):
                    if a!=old:deltas.append(dict(security_id=sid,source_key=key,trade_date=bar['trade_date'],column=('open','high','low','close')[col],old=old,candidate=a));changed.append(i)
                bar['qfq_ohlc']=actual
            bar['exact_affine_coefficients']=factor.exact_coefficients()
            bar['adjustment_version']=ADJUSTMENT_VERSION
        if changed:
            current_delta.append(dict(security_id=sid,last_250_affected=True,last_60_affected=any(i>=len(bars)-60 for i in changed),last_20_affected=any(i>=len(bars)-20 for i in changed),last_5_affected=any(i>=len(bars)-5 for i in changed)))
            for i in sorted(set(changed)):
                window_impacts.append(dict(security_id=sid,bar_date=bars[i]['trade_date'],possible_technical_consumer_dates={str(n):[b['trade_date'] for b in bars[i:min(len(bars),i+n+1)]] for n in (5,20,60,120,250)},scope='Dependency reachability only; does not establish dated PIT or actual reducer output differences'))
        row['adjustment_version']=ADJUSTMENT_VERSION
        output.write((json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n').encode())
        stocks+=1;bars_count+=len(bars)
        if stocks%500==0:print(f'CANDIDATE_PROGRESS stocks={stocks} cells={cells} deltas={len(deltas)}',flush=True)
os.replace(temporary,candidate)
old_counter=json.loads((ROOT/'docs/audits/full_system_audit_r2_20261011_58faf74e/b2_rounding_counterexamples.json').read_bytes())
expected_set={(r['sid'],r['trade_date'],r['column'],r['exact_rational']) for r in old_counter['rows']}
actual_set={(r['security_id'],r['trade_date'],r['column'],r['candidate']) for r in deltas}
assert actual_set==expected_set,(len(actual_set),len(expected_set))
assert oracle_mismatches==0
ns['atomic']('a4_numeric_checkpoint.json',dict(stocks=stocks,bars=bars_count,cells=cells,oracle_mismatches=oracle_mismatches,deltas=deltas,current_delta=current_delta,window_impacts=window_impacts))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value):
    p=OUT/name;t=p.with_suffix('.tmp');t.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode());os.replace(t,p)
consumers=[]
for p in (ROOT/'src').rglob('*.py'):
    text=p.read_text(encoding='utf-8-sig')
    if any(k in text for k in ('qfq_mul','qfq_price','adjust_ohlc','qfq_ohlc','adj_close')):
        consumers.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),uses_exact_v0_3='tdx_adjustment_v0_3' in text,transport='DECIMAL_COEFFICIENT' if 'qfq_mul' in text else 'ROUNDED_PRICE',status='LEGACY_CONSUMER_NOT_PROMOTED' if 'tdx_adjustment_v0_3' not in text else 'CANDIDATE_ONLY'))
write('A4_CONSUMER_IMPACT.json',dict(contract_id='QFQ_V0_3_CONSUMER_IMPACT_R3',consumers=consumers,stock_window_reach=current_delta,historical_window_reach=window_impacts,formal_consumer_delta='NOT_GRANTED; dated legal PIT/prior/source and v0.3 transport admission required',current_short_windows='No changed cells in latest 60-bar windows; still verify consumer outputs before promotion',economic_event_formula='Existing category=1 per-10 native contract preserved; not an independent issuer-economic-truth certificate'))
write('A4_CANDIDATE_RECOMPUTE.json',dict(contract_id='TDX_AFFINE_QFQ_V0_3_EXACT_RATIONAL',scope='Every stock and every bar of latest frozen Owner history; not all decades in the native archive',inputs=ns['inputs'],source_engine=dict(path='src/adjustment/tdx_adjustment_v0_3.py',sha256=sha(ROOT/'src/adjustment/tdx_adjustment_v0_3.py')),candidate=dict(path=str(candidate),sha256=sha(candidate),bytes=candidate.stat().st_size),stocks=stocks,bars=bars_count,qfq_cells=cells,independent_chronological_oracle_mismatches=oracle_mismatches,changed_cells=len(deltas),changed_stocks=len({r['security_id'] for r in deltas}),deltas=deltas,all_r2_counterexamples_corrected=True,accepted_owner_overwrite=False,acceptance='NUMERIC_CANDIDATE_PASS; CONSUMER_PROMOTION_PENDING',seconds=time.perf_counter()-started))
print(json.dumps(dict(stocks=stocks,bars=bars_count,cells=cells,deltas=len(deltas),oracle_mismatches=oracle_mismatches,seconds=time.perf_counter()-started)),flush=True)
