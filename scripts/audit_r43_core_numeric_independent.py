"""Read-only real-source scoped audit; no production compute/adjustment imports."""
import gzip, hashlib, json, os, struct, sys, zipfile
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from tdx.gbbq_reader import read_gbbq  # Decoder only; arithmetic below is independent.
OUT=ROOT/'docs/evidence/r4_3_four_session_closeout_20261009'
OLD=OUT/'owner_v3'
def read(p): return json.loads(p.read_bytes())
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size)
def bound(r):
    p=ROOT/r['path'];assert sha(p)==r['sha256'],p
    return p
def rows(p):
    with (gzip.open(p,'rt',encoding='utf8') if p.suffix=='.gz' else p.open(encoding='utf8')) as f:
        for line in f:
            if line.strip():yield json.loads(line)
def write(n,v):
    OUT.mkdir(parents=True,exist_ok=True);p=OUT/n;t=p.with_suffix(p.suffix+'.tmp.identity')
    t.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(t,p)

def audit(OWNER_INDEX):
    core=read(OLD/'CORE_REPLAY.json')['owners'] if (OLD/'CORE_REPLAY.json').exists() else [read(p) for p in sorted((OLD/'owners').glob('*/OWNER.json'))];owner=core[OWNER_INDEX];events=defaultdict(list)
    for e in read_gbbq(bound(owner['sources']['gbbq'])):
        if e.category==1:events[e.security_id.lower()].append(e)
    cores={r['security_id']:r for r in rows(bound(owner['core']))};priors={r['security_id']:r for r in rows(bound(owner['prior_core']))};raw={r['security_id']:r for r in rows(bound(owner['raw']))}
    samples=[];categories=Counter();errors=[];package=bound(owner['sources']['package'])
    # Independent average-rank enumeration over actual saved return endpoints.
    rank_checks=[]
    for horizon in (5,20):
        pairs=sorted((r['fields'][f'ret{horizon}']['value'],sid) for sid,r in cores.items() if r['fields'][f'ret{horizon}']['value'] is not None)
        n=len(pairs);index=0
        while index<n:
            end=index+1
            while end<n and pairs[end][0]==pairs[index][0]:end+=1
            expected=100*((index+end-1)/2)/(n-1)
            for _,sid in pairs[index:end]:
                actual=cores[sid]['fields'][f'rps{horizon}']['value']
                if abs(expected-actual)>1e-8:errors.append(dict(sid=sid,field=f'rps{horizon}',expected=expected,actual=actual))
            index=end
        rank_checks.append(dict(field=f'rps{horizon}',known_population=n,formula='mean zero-based positions in sorted tie group / (N-1) * 100',return_source=owner['core']))

    with zipfile.ZipFile(package) as z:
        names={p.lower().split('/')[-1]:p for p in z.namelist() if p.endswith('.day')}
        for hist in rows(bound(owner['history'])):
            sid=hist['security_id'];row=cores[sid];code=row['source_security_key'].lower();bs=hist['bars'];ev=events[code];cross=[e for e in ev if int(bs[0]['trade_date'].replace('-',''))<e.event_date<=int(owner['trade_date'].replace('-',''))]
            category='SUSPENDED_NO_BAR' if sid not in raw else 'SHORT_LISTING_WINDOW' if len(bs)<21 else 'CROSS_XRXD' if cross else 'ORDINARY_CONTROL'
            limit={'SUSPENDED_NO_BAR':4,'SHORT_LISTING_WINDOW':4,'CROSS_XRXD':12,'ORDINARY_CONTROL':12}[category]
            if categories[category]>=limit:continue
            leaf=code.replace('.','')+'.day';name=names.get(leaf)
            if not name:continue
            binary=z.read(name);official={str(b[0]):b for b in struct.iter_unpack('<IIIIIfII',binary)}
            values=[]
            for b in bs:
                record=official.get(b['trade_date'].replace('-',''));assert record is not None
                assert [v/100 for v in record[1:5]]==b['raw_ohlc']
                if b['qfq_ohlc'] is None:continue
                expected=[]
                for v in b['raw_ohlc']:
                    with localcontext() as ctx:
                        ctx.prec=40;p=Decimal(str(v))
                        for e in sorted(ev,key=lambda e:(e.event_date,e.source_record_index)):
                            if int(b['trade_date'].replace('-',''))<e.event_date<=int(owner['trade_date'].replace('-','')):
                                cash,price,bonus,rights=[Decimal(str(x)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) for x in (e.c1,e.c2,e.c3,e.c4)]
                                p=(p*10-cash+rights*price)/(10+bonus+rights)
                        expected.append(float(p.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)))
                if expected!=b['qfq_ohlc']:errors.append(dict(sid=sid,day=b['trade_date'],expected=expected,actual=b['qfq_ohlc']))
                values.append(dict(trade_date=b['trade_date'],raw=b['raw_ohlc'],independent_qfq=expected))
            checks=[]
            for endpoint,r in [('current',row),('prior',priors[sid])]:
                for field in ['ma5','ma20','ma60','atr5','atr20','prior_high5','prior_high20','prior_low20','ret1','ret3','ret5','ret20','amount_ratio20','volume_ratio20']:
                    cell=r['fields'].get(field,dict(value=None,unknown_reason='PRE_LISTING_NO_PRIOR_CORE_FIELDS'));actual=cell['value'];window=[b for b in values if (cell.get('window_start_trade_date') or '9999')<=b['trade_date']<=(cell.get('window_end_trade_date') or '0000')]
                    calc=None
                    if actual is not None:
                        ps=[b['independent_qfq'] for b in window];n=int(''.join(c for c in field if c.isdigit()))
                        if field.startswith('ma'):calc=sum(p[3] for p in ps)/n
                        elif field.startswith('atr'):calc=sum(max(b[1]-b[2],abs(b[1]-a[3]),abs(b[2]-a[3])) for a,b in zip(ps,ps[1:]))/n
                        elif field.startswith('prior_high'):calc=max(p[1] for p in ps)
                        elif field.startswith('prior_low'):calc=min(p[2] for p in ps)
                        elif field.startswith('ret'):calc=ps[-1][3]/ps[0][3]-1
                        else:
                            key='amount' if field.startswith('amount') else 'volume';lookup={b['trade_date']:b for b in bs};dates=[b['trade_date'] for b in window];calc=lookup[dates[-1]][key]/(sum(lookup[d][key] for d in dates[:-1])/n)
                        if abs(calc-actual)>1e-8:errors.append(dict(sid=sid,field=field,endpoint=endpoint,expected=calc,actual=actual))
                    checks.append(dict(endpoint=endpoint,field=field,expected=calc,actual=actual,unknown_reason=cell.get('unknown_reason'),window_start=cell.get('window_start_trade_date'),window_end=cell.get('window_end_trade_date')))
            samples.append(dict(trade_date=owner['trade_date'],security_id=sid,source_security_key=code,category=category,zip_entry=name,zip_entry_sha256=hashlib.sha256(binary).hexdigest(),target_bar_present=sid in raw,history_bar_count=len(bs),events=[dict(date=e.event_date,c1=e.c1,c2=e.c2,c3=e.c3,c4=e.c4,source_record_index=e.source_record_index) for e in cross],checks=checks,ohlc_samples=values[:2]+values[-2:]));categories[category]+=1
            if len(samples)>=32:break
    return dict(trade_date=owner['trade_date'],samples=samples,categories=dict(categories),errors=errors,source_digest=owner['source_digest'],inputs={k:owner[k] for k in ['core','prior_core','history','raw']},independent_cross_section_rank_checks=rank_checks)
def main():
    results=[audit(i) for i in range(4)]
    errors=[e for r in results for e in r['errors']]
    write('05_FOUR_SESSION_RAW_QFQ_CORE_PROFILE_NUMERIC_ORACLE.json',dict(contract='R43_INDEPENDENT_NUMERIC_ORACLE_V1',absolute_tolerance=1e-8,rounding='GBBQ parameters and final prices HALF_UP cents; intermediate decimal precision40',production_calculators_called=False,formula='Independent chronological XRXD recurrence; independent MA/ATR/previous high-low/returns/amount-volume ratios',dates=results,total_real_samples=sum(len(r['samples']) for r in results),errors=errors,acceptance='PASS_INDEPENDENT_ENGINEERING_NUMERIC_ORACLE' if not errors else 'FAIL'))
    print(json.dumps(dict(samples=sum(len(r['samples']) for r in results),errors=len(errors))))
if __name__=='__main__':main()
