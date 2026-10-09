"""Offline Python stdlib oracle. Does not import repository producer modules."""
from pathlib import Path
from datetime import date
from decimal import Decimal
from statistics import fmean,median
import argparse,hashlib,json,math

def read(p):return json.loads(p.read_bytes())
def match(actual,expected):
    if actual is None or expected is None:return actual is expected
    return math.isclose(float(actual),float(expected),rel_tol=1e-10,abs_tol=1e-10)

def run(root):
    errors=[];checks=0;unverifiable=[];examples=[]
    def check(label,a,b):
        nonlocal checks
        checks+=1
        if not match(a,b):errors.append(dict(label=label,actual=a,expected=b))
        if len(examples)<8:examples.append(dict(label=label,actual=a,expected=b))
    for day in ['2026-10-08','2026-10-09']:
        sample=read(root/'sampling'/f'{day}.json')
        order=sorted(sample['accepted_pool'],key=lambda s:hashlib.sha256((sample['seed']+'|'+day+'|'+s).encode()).hexdigest())
        assert sample['seeded_random_sample']==order[:25],'SAMPLE_FREEZE_MISMATCH'
        data=read(root/'numerical'/f'{day}.json')
        for s in data['core']:
            bars=s['bars'];assert all(b['trade_date']<=day for b in bars),'FUTURE_BAR'
            q=[b for b in bars if b.get('qfq_ohlc')]
            for key,expected in s['expected'].items():
                value=expected['value']
                if value is None:
                    unverifiable.append(dict(day=day,security_id=s['security_id'],field=key,reason=expected['unknown_reason']))
                    continue
                if key=='ma20' and len(q)>=20:actual=fmean(b['qfq_ohlc'][3] for b in q[-20:])
                elif key=='atr20' and len(q)>=21:
                    actual=fmean(max(b['qfq_ohlc'][1]-b['qfq_ohlc'][2],abs(b['qfq_ohlc'][1]-a['qfq_ohlc'][3]),abs(b['qfq_ohlc'][2]-a['qfq_ohlc'][3])) for a,b in zip(q[-21:-1],q[-20:]))
                elif key in ('amount_ratio20','volume_ratio20') and len(q)>=21 and s['status']=='ACTUAL_TRADED':
                    column='amount' if key.startswith('amount') else 'volume'
                    denominator=fmean(b[column] for b in q[-21:-1]);actual=q[-1][column]/denominator if denominator else None
                else:
                    unverifiable.append(dict(day=day,security_id=s['security_id'],field=key,reason='WINDOW_OR_STATE_INCOMPLETE'));continue
                check(day+'/'+s['security_id']+'/'+key,actual,value)
        cohort=data['cohort'];assert {x['security_id'] for x in cohort}==set(sample['accepted_pool'])
        for n in (5,20):
            values=[r[f'ret{n}'] for r in cohort if r[f'ret{n}'] is not None]
            for r in cohort:
                v=r[f'ret{n}'];expected=r[f'rps{n}']
                actual=None if v is None or len(values)<2 else 100*(sum(x<v for x in values)+0.5*(sum(x==v for x in values)-1))/(len(values)-1)
                check(day+'/'+r['security_id']+f'/rps{n}',actual,expected)
        for sector in data['sectors']:
            assert sorted(sector['member_ids'])==sorted(r['security_id'] for r in sector['contributions'])
            values=[r['ret1'] for r in sector['contributions'] if r['ret1'] is not None]
            check(day+'/'+sector['sector_id']+'/median',median(values) if values else None,sector['expected']['sector_rs1'])
            check(day+'/'+sector['sector_id']+'/breadth',sum(v>0 for v in values)/len(values) if values else None,sector['expected']['breadth_ret1'])
    period_checks=0
    for c in read(root/'periods/PERIOD_ORACLE_CASES.json'):
        p=c['expected'];bars=c['bars'];basis='raw_ohlc' if c['domain']=='period_raw' else 'qfq_ohlc'
        assert all(b['trade_date']<=c['trade_date'] for b in bars),'PERIOD_FUTURE_BAR'
        def period_key(d):
            y,w,_=date.fromisoformat(d).isocalendar()
            return d[:7] if p['period_type']=='MONTHLY' else f'{y}-W{w:02d}'
        assert all(period_key(b['trade_date'])==p['period_key'] for b in bars),'PERIOD_MEMBERSHIP_MISMATCH'
        expected=dict(actual_count=len(bars),volume=sum(b['volume'] for b in bars),amount=sum(b['amount'] for b in bars))
        if bars and all(b[basis] for b in bars):
            prices=[[Decimal(str(v)) for v in b[basis]] for b in bars]
            expected.update(open=prices[0][0],high=max(b[1] for b in prices),low=min(b[2] for b in prices),close=prices[-1][3])
        else:expected.update(open=None,high=None,low=None,close=None)
        for key,value in expected.items():
            check(c['trade_date']+'/'+p['security_id']+'/'+c['domain']+'/'+p['period_key']+'/'+key,value,p[key]);period_checks+=1
    return dict(acceptance='ENGINEERING_SCOPED_PASS' if not errors else 'FAIL',checks=checks,period_checks=period_checks,
        errors=errors,examples=examples,unverifiable=unverifiable,
        NOT_VERIFIABLE=['full source-to-normalized history provenance','all-cohort antecedent returns','event-to-affine adjustment chain','full Native/LOO state','Market axes/path','period closure calendar/state boundary','full population factor QA'],external_acceptance='NOT_GRANTED')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    for line in (a.input/'checksums/SHA256SUMS.txt').read_text().splitlines():
        digest,path=line.split('  ',1);assert hashlib.sha256((a.input/path).read_bytes()).hexdigest()==digest,'PAYLOAD_SHA_MISMATCH:'+path
    result=run(a.input);a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'ORACLE_OUTPUT.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf8')
    print(json.dumps(dict(acceptance=result['acceptance'],checks=result['checks'],period_checks=result['period_checks'],errors=len(result['errors']))))
    raise SystemExit(bool(result['errors']))
