"""Standard-library reference from factor contracts; no production imports.

Numerical check of all OBSERVED declared windows. Quality gaps are explicit,
not silently mapped to a synthetic bar or an alternative denominator.
"""
from pathlib import Path
from statistics import mean
import json,math,sys

def formulas(bars,damage,date,calendar):
    bs=[dict(zip(('open','high','low','close'),b['qfq_ohlc']),amount=b['amount'],volume=b['volume'],date=b['trade_date']) for b in bars if b.get('qfq_ohlc')]
    result={}
    def w(n,lag=0):return bs[len(bs)-n-lag:len(bs)-lag if lag else len(bs)] if len(bs)>=n+lag else None
    def calc(n,fn,lag=0):
        x=w(n,lag);return fn(x) if x else None
    prior_lag=1 if bs and bs[-1]['date']==date else 0
    for n in (5,20,60):
        result['ma'+str(n)]=calc(n,lambda b:mean(x['close'] for x in b))
        for stem,key,fn,lag in [('hhv','high',max,0),('llv','low',min,0),('prior_high','high',max,prior_lag),('prior_low','low',min,prior_lag)]:result[stem+str(n)]=calc(n,lambda b,k=key,f=fn:f(x[k] for x in b),lag)
    tr=lambda a,b:max(b['high']-b['low'],abs(b['high']-a['close']),abs(b['low']-a['close']))
    result['tr']=calc(2,lambda b:tr(*b)) if prior_lag else None
    for n in (5,20):result['atr'+str(n)]=calc(n+1,lambda b:mean(tr(a,c) for a,c in zip(b,b[1:])))
    atr=result['atr20']
    for n,k in ((20,5),(60,10)):result['slope'+str(n)]=calc(n+k,lambda b:(mean(x['close'] for x in b[-n:])-mean(x['close'] for x in b[:-k]))/atr) if atr else None
    result['hh_progress']=calc(10,lambda b:max(x['high'] for x in b[-5:])>max(x['high'] for x in b[:5]))
    result['ll_progress']=calc(10,lambda b:min(x['low'] for x in b[-5:])<min(x['low'] for x in b[:5]))
    def ratio(a,b):return a/b if a is not None and b is not None and b!=0 else None
    last=bars[-1];close=last['qfq_ohlc'][3] if last.get('qfq_ohlc') and last['trade_date']==date else None
    result['atr_ratio']=ratio(result['atr5'],atr)
    hi,lo=result['hhv60'],result['llv60'];result['pos60']=ratio(close-lo,hi-lo) if close is not None and lo is not None and hi is not None else None
    result['range_ratio']=ratio(result['hhv5']-result['llv5'],result['hhv20']-result['llv20']) if result['hhv20'] is not None and result['hhv5'] is not None else None
    old=w(60,prior_lag);result['prior60_percentile']=100*sum((x['close']<close)+.5*(x['close']==close) for x in old)/60 if old and close is not None else None
    previous=calendar[calendar.index(date)-1];previous_close=next((b['close'] for b in bs if b['date']==previous),None)
    ph=result['prior_low20'];result['core_price_damage']=close<ph-damage*atr and close<previous_close if close is not None and ph is not None and atr is not None and previous_close is not None else None
    return result

def main():
    here=Path(__file__).parent;data=json.loads(Path(sys.argv[1] if len(sys.argv)>1 else here/'UPSTREAM_ORACLE_INPUT.json').read_text(encoding='utf8'));checks=[];unknown=[]
    for r in data['records']:
        expected=formulas(r['bars'],data['damage_atr_multiple'],r['trade_date'],data['calendar'])
        for field,cell in r['actual'].items():
            if cell['quality_state']!='OBSERVED':
                e=expected[field];passed=e is None and cell['value'] is None
                unknown.append(dict(security_id=r['security_id'],trade_date=r['trade_date'],field=field,reason=cell.get('unknown_reason'),expected=e,actual=cell['value'],passed=passed,verdict='INDEPENDENT_WINDOW_OR_ENDPOINT_ABSENCE' if passed else 'QUALITY_REASON_REQUIRES_SOURCE_STATE_PROOF'))
                checks.append(dict(security_id=r['security_id'],trade_date=r['trade_date'],field=field,expected=e,actual=cell['value'],passed=passed,domain='UNKNOWN_WINDOW_ENDPOINT'))
                continue
            a=cell['value'];e=expected[field];passed=a==e if isinstance(a,bool) or a is None or e is None else math.isclose(a,e,rel_tol=1e-12,abs_tol=1e-12)
            checks.append(dict(security_id=r['security_id'],trade_date=r['trade_date'],field=field,expected=e,actual=a,passed=passed,input_window_start=cell.get('window_start_trade_date'),input_window_end=cell.get('window_end_trade_date')))
    errors=[c for c in checks if not c['passed']];out=dict(contract=data['contract'],checks=len(checks),errors=len(errors),differences=errors,results=checks,unknown_quality_branches=unknown,acceptance='PASS_SCOPED' if not errors else 'FAIL')
    dest=Path(sys.argv[2] if len(sys.argv)>2 else here/'UPSTREAM_ORACLE_RESULT.json');tmp=dest.with_suffix('.tmp');tmp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(dest);print(json.dumps(dict(checks=len(checks),errors=len(errors),unknown=len(unknown))));return bool(errors)
if __name__=='__main__':sys.exit(main())
