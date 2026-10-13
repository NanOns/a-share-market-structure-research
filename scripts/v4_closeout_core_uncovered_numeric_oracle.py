"""Independent current known Core formulas; no producer or passed oracle rerun.

Immutable history is the independently verified price input. Binary64 statistics
retain the declared arithmetic, with exact rational accumulation and variance.
"""
import gzip,json,math,decimal,os
from fractions import Fraction
from pathlib import Path
from collections import Counter
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def average(values):
    values=list(values);return float(sum((Fraction(v) for v in values),Fraction()))/len(values)

def deviation(values):
    values=[Fraction(v) for v in values];n=len(values);mean=sum(values)/n;variance=sum((v-mean)**2 for v in values)/n
    with decimal.localcontext() as context:
        context.prec=80
        return float((decimal.Decimal(variance.numerator)/decimal.Decimal(variance.denominator)).sqrt())

def jsonlines(path):
    with gzip.open(path,'rt',encoding='utf8') as stream:
        for line in stream:
            if line.strip():yield json.loads(line)

def main():
    report=OUT/'CORE_UNCOVERED_NUMERIC_ORACLE_R6_R1.json'
    if report.exists():raise ValueError('PRESERVE_PRIOR_UNCOVERED_CORE_ORACLE')
    preparation=json.loads((OUT/'SEALED_METADATA_CONSERVATION_R6_R2.json').read_bytes());candidate=json.loads(checked(ROOT,preparation['candidate']).read_bytes());day=candidate['accepted_trade_date']
    qa=json.loads(checked(ROOT,candidate['day_receipt']).read_bytes());replay=json.loads(checked(ROOT,qa['numeric_core_oracle']).read_bytes());owner=next(x for x in replay['owners'] if x['trade_date']==day)
    calendar=json.loads((ROOT/'docs/evidence/r4_3_four_session_closeout_20261009/owner_v3/FOCUS_CALENDAR.json').read_bytes())['session_dates'];index=calendar.index(day)
    previous={d:{x['security_id']:x for x in jsonlines(checked(ROOT,candidate['owners'][d]['core']))} for d in (calendar[index-1],calendar[index-3])}
    checks=Counter();unknown=Counter();errors=[];error_count=0;cross=[]
    params=json.loads((ROOT/'config/v4_03_parameter_set_v1.json').read_bytes());damage=params['contract_literals']['core_price_damage_atr_multiple']
    def check(sid,key,actual,expected):
        nonlocal error_count
        checks[key]+=1
        if actual!=expected:
            error_count+=1
            if len(errors)<100:errors.append(dict(security_id=sid,field=key,actual=actual,expected=expected))
    for hist,row in zip(jsonlines(checked(ROOT,owner['history'])),jsonlines(checked(ROOT,owner['core']))):
        if hist['security_id']!=row['security_id']:raise ValueError('CORE_HISTORY_ORDER_MISMATCH')
        sid=row['security_id'];fields=row['fields'];bars=hist['bars'];by={b['trade_date']:b for b in bars}
        if len(by)!=len(bars) or any(d>day for d in by):raise ValueError('CORE_FUTURE_OR_DUPLICATE_INPUT')
        observed=[b for b in bars if b['qfq_ohlc']];prior=[b for b in observed if b['trade_date']<day];current=by.get(day)
        q=lambda b,k:b['qfq_ohlc'][k]
        expected={}
        for n in (5,20,60):
            group=observed[-n:];old=prior[-n:]
            if len(group)==n:
                expected['ma'+str(n)]=average(q(b,3) for b in group)
                expected['hhv'+str(n)]=max(q(b,1) for b in group);expected['llv'+str(n)]=min(q(b,2) for b in group)
            if len(old)==n:
                expected['prior_high'+str(n)]=max(q(b,1) for b in old);expected['prior_low'+str(n)]=min(q(b,2) for b in old)
                if n in (5,20) and current:
                    for key in ('amount','volume'):
                        denominator=average(b[key] for b in old)
                        if denominator:expected[key+'_ratio'+str(n)]=current[key]/denominator
        for n in (1,3,5,20):
            start=by.get(calendar[index-n])
            if current and current['qfq_ohlc'] and start and start['qfq_ohlc']:expected['ret'+str(n)]=q(current,3)/q(start,3)-1
        for n in (5,20):
            dates=calendar[index-n:index+1];group=[by.get(d) for d in dates]
            if all(b and b['qfq_ohlc'] for b in group):expected['vol'+str(n)]=deviation(math.log(q(b,3)/q(a,3)) for a,b in zip(group,group[1:]))
            group=observed[-n-1:]
            if len(group)==n+1:expected['atr'+str(n)]=average(max(q(b,1)-q(b,2),abs(q(b,1)-q(a,3)),abs(q(b,2)-q(a,3))) for a,b in zip(group,group[1:]))
        if current and current['qfq_ohlc'] and len(observed)>=2:
            a,b=observed[-2:];expected['tr']=max(q(b,1)-q(b,2),abs(q(b,1)-q(a,3)),abs(q(b,2)-q(a,3)))
            if q(b,1)!=q(b,2):expected['clv']=(q(b,3)-q(b,2))/(q(b,1)-q(b,2))
        for n,offset in ((20,5),(60,10)):
            if len(observed)>=n+offset and fields['atr20']['value'] and fields['atr20']['value']>0:
                expected['slope'+str(n)]=(average(q(b,3) for b in observed[-n:])-average(q(b,3) for b in observed[-n-offset:-offset]))/fields['atr20']['value']
        if len(observed)>=10:
            for field,k,fn in (('hh_progress',1,max),('ll_progress',2,min)):
                expected[field]=fn(q(b,k) for b in observed[-5:])>fn(q(b,k) for b in observed[-10:-5]) if field=='hh_progress' else fn(q(b,k) for b in observed[-5:])<fn(q(b,k) for b in observed[-10:-5])
        if current and current['qfq_ohlc'] and len(prior)>=60:
            closes=[q(b,3) for b in prior[-60:]];close=q(current,3)
            expected['prior60_percentile']=100*(sum(v<close for v in closes)+0.5*sum(v==close for v in closes))/60
        if current and current['qfq_ohlc']:
            hi,lo=expected.get('hhv60'),expected.get('llv60')
            if hi is not None and lo is not None and hi!=lo:expected['pos60']=(q(current,3)-lo)/(hi-lo)
            if fields['prior_low20']['value'] is not None and fields['atr20']['value'] is not None and fields['ret1']['value'] is not None:
                expected['core_price_damage']=q(current,3)<fields['prior_low20']['value']-damage*fields['atr20']['value'] and fields['ret1']['value']<0
        if all(k in expected for k in ('hhv5','llv5','hhv20','llv20')) and expected['hhv20']!=expected['llv20']:expected['range_ratio']=(expected['hhv5']-expected['llv5'])/(expected['hhv20']-expected['llv20'])
        for key,numerator,denominator in (('atr_ratio','atr5','atr20'),('vol_ratio','vol5','vol20')):
            a=expected.get(numerator);b=expected.get(denominator)
            if a is not None and b and b>0:expected[key]=a/b
        for key,cell in fields.items():
            if key in ('ma20','atr20') or key.startswith(('rps','rel_market')):continue
            if cell['value'] is None:
                unknown[key]+=1
                if cell['quality_state']!='UNKNOWN' or not cell['unknown_reason']:raise ValueError('CORE_UNKNOWN_QUALITY_OR_REASON_REQUIRED')
                continue
            if key not in expected:raise ValueError('KNOWN_CORE_FORMULA_INPUT_NOT_AVAILABLE:'+key)
            check(sid,key,cell['value'],expected[key])
        cross.append(row)
    for n in (5,20):
        valid=sorted(row['fields']['ret'+str(n)]['value'] for row in cross if row['fields']['ret'+str(n)]['value'] is not None)
        import bisect
        for row in cross:
            sid=row['security_id'];value=row['fields']['ret'+str(n)]['value'];actual=row['fields']['rps'+str(n)]['value']
            expected=None if value is None or len(valid)<2 else 100*(bisect.bisect_left(valid,value)+0.5*(bisect.bisect_right(valid,value)-bisect.bisect_left(valid,value)-1))/(len(valid)-1)
            check(sid,'rps'+str(n),actual,expected)
            for lag in ((1,3) if n==5 else (3,)):
                old=previous[calendar[index-lag]].get(sid,{}).get('fields',{}).get('rps'+str(n),{}).get('value')
                expected_delta=actual-old if actual is not None and old is not None else None
                check(sid,'rps'+str(n)+'_delta'+str(lag),row['fields']['rps'+str(n)+'_delta'+str(lag)]['value'],expected_delta)
    result=dict(contract_id='V4_CURRENT_UNCOVERED_KNOWN_CORE_NUMERIC_ORACLE_R1',acceptance='PASS_KNOWN_SCOPE' if not error_count else 'FAIL',T0=day,candidate=preparation['candidate'],
        checks=dict(checks),total_checks=sum(checks.values()),unknown_cells=dict(unknown),error_count=error_count,first_errors=errors,
        history=owner['history'],core=owner['core'],producer_executed=False,previous_pass_ma20_atr20_affine_checks_reexecuted=False,
        comparison='EXACT_BINARY64_VALUE_EQUALITY_NO_TOLERANCE',scope='All non-null current technical/return/volatility/derived Core fields and full RPS/delta readback; market-reference fields and independent unknown-window conditions remain separate')
    atomic_json(OUT,report,result);print(json.dumps(dict(acceptance=result['acceptance'],checks=result['total_checks'],errors=error_count)),flush=True)

if __name__=='__main__':main()
