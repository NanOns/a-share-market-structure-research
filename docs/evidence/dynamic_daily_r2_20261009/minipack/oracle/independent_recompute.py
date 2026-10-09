"""Offline Python stdlib oracle. Does not import repository producer modules."""
from pathlib import Path
from datetime import date,timedelta
import calendar
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
            for case in sector.get('loo_cases',[]):
                others=[r for r in sector['contributions'] if r['security_id']!=case['excluded_target_id']]
                check(day+'/'+sector['sector_id']+'/loo_member_count',len(others),case['non_target_member_count'])
                assert all(r['security_id']!=case['excluded_target_id'] for r in others)
                for n in (1,5):
                    values=[r[f'ret{n}'] for r in others if r[f'ret{n}'] is not None]
                    stock=case['stock_returns'][f'ret{n}']
                    actual=stock-median(values) if stock is not None and values else None
                    check(day+'/'+sector['sector_id']+f'/loo_rel{n}',actual,case['expected_relative_substitutions'][f'rel_market_{n}'])
        market=data.get('market_participation')
        if market:
            assert {r['security_id'] for r in market['contributions']}==set(sample['accepted_pool'])
            values=[r['amount_ratio20'] for r in market['contributions'] if r['amount_ratio20'] is not None]
            value=median(values) if values else None
            axis=None if value is None else 'EXPANDING' if value>=market['thresholds']['expanding'] else 'THIN' if value<market['thresholds']['thin'] else 'NORMAL'
            checks+=1
            if axis!=market['expected_axis']:errors.append(dict(label=day+'/market_participation',actual=axis,expected=market['expected_axis']))
    period_checks=0
    calendar_path=root/'periods/CALENDAR_STATE_INPUT.json'
    calendar_input=read(calendar_path) if calendar_path.is_file() else None
    for c in read(root/'periods/PERIOD_ORACLE_CASES.json'):
        p=c['expected'];bars=c['bars'];basis='raw_ohlc' if c['domain']=='period_raw' else 'qfq_ohlc'
        assert all(b['trade_date']<=c['trade_date'] for b in bars),'PERIOD_FUTURE_BAR'
        def period_key(d):
            y,w,_=date.fromisoformat(d).isocalendar()
            return d[:7] if p['period_type']=='MONTHLY' else f'{y}-W{w:02d}'
        assert all(period_key(b['trade_date'])==p['period_key'] for b in bars),'PERIOD_MEMBERSHIP_MISMATCH'
        if calendar_input and c['evidence_kind']!='FIXTURE':
            dates=[d for d in calendar_input['session_dates'] if period_key(d)==p['period_key']]
            if p['period_type']=='MONTHLY':
                y,m=map(int,p['period_key'].split('-'));natural=date(y,m,calendar.monthrange(y,m)[1])
            else:
                y,w=p['period_key'].split('-W');natural=date.fromisocalendar(int(y),int(w),7)
            closed=bool(dates) and calendar_input['coverage_end']>=natural.isoformat() and max(dates)<=c['trade_date']
            view='CLOSED_ONLY' if closed else 'AS_OF_PARTIAL'
            checks+=1;period_checks+=1
            if view!=p['period_view']:errors.append(dict(label=c['trade_date']+'/'+p['period_key']+'/period_view',actual=view,expected=p['period_view']))
        expected=dict(actual_count=len(bars),volume=sum(b['volume'] for b in bars),amount=sum(b['amount'] for b in bars))
        if bars and all(b[basis] for b in bars):
            prices=[[Decimal(str(v)) for v in b[basis]] for b in bars]
            expected.update(open=prices[0][0],high=max(b[1] for b in prices),low=min(b[2] for b in prices),close=prices[-1][3])
        else:expected.update(open=None,high=None,low=None,close=None)
        for key,value in expected.items():
            check(c['trade_date']+'/'+p['security_id']+'/'+c['domain']+'/'+p['period_key']+'/'+key,value,p[key]);period_checks+=1
    fixture_path=root/'periods/STATE_BOUNDARY_FIXTURES.json'
    state_checks=0
    if fixture_path.is_file():
        for case in read(fixture_path):
            assert case['evidence_kind']=='FIXTURE'
            history={b['trade_date']:b for b in case['history']}
            for domain,periods in case['expected'].items():
                for p in periods:
                    def key(d):
                        y,w,_=date.fromisoformat(d).isocalendar()
                        return d[:7] if p['period_type']=='MONTHLY' else f'{y}-W{w:02d}'
                    dates=[d for d in case['session_dates'] if case['start']<=d<=case['target'] and key(d)==p['period_key']]
                    states=['ACTUAL_TRADED' if d in history else case['statuses'].get(d,'UNKNOWN') for d in dates]
                    for field,value in dict(calendar_count=len(dates),actual_count=states.count('ACTUAL_TRADED'),suspended_count=states.count('SUSPENDED'),data_gap_count=states.count('DATA_GAP'),unknown_count=states.count('UNKNOWN')).items():
                        check(case['case']+'/'+domain+'/'+field,value,p[field]);state_checks+=1
                    unready=domain=='PERIOD_ADJUSTED' and any(not history[d]['qfq_ohlc'] for d in dates if d in history)
                    all_dates=[d for d in case['session_dates'] if key(d)==p['period_key']]
                    if p['period_type']=='MONTHLY':
                        y,m=map(int,p['period_key'].split('-'));natural=date(y,m,calendar.monthrange(y,m)[1])
                    else:
                        y,w=p['period_key'].split('-W');natural=date.fromisocalendar(int(y),int(w),7)
                    closed=case['coverage_end']>=natural.isoformat() and max(all_dates)<=case['target']
                    view='CLOSED_ONLY' if closed else 'AS_OF_PARTIAL'
                    status='BLOCKED_BY_ADJUSTMENT' if unready else 'BLOCKED_BY_DATA_GAP' if 'DATA_GAP' in states else 'BLOCKED_BY_UNKNOWN_STATUS' if 'UNKNOWN' in states else 'NO_ACTUAL_BARS' if 'ACTUAL_TRADED' not in states else 'CLOSED_ONLY_READY' if closed else 'AS_OF_PARTIAL_READY'
                    for field,value in [('period_view',view),('period_status',status)]:
                        checks+=1;state_checks+=1
                        if p[field]!=value:errors.append(dict(label=case['case']+'/'+domain+'/'+field,actual=value,expected=p[field]))
                    if unready or 'ACTUAL_TRADED' not in states:
                        for field in ('open','high','low','close'):
                            check(case['case']+'/'+domain+'/'+field,None,p[field]);state_checks+=1
    return dict(acceptance='ENGINEERING_SCOPED_PASS' if not errors else 'FAIL',checks=checks,period_checks=period_checks,state_boundary_checks=state_checks,
        errors=errors,examples=examples,unverifiable=unverifiable,
        NOT_VERIFIABLE=['full source-to-normalized history provenance','all-cohort antecedent returns','event-to-affine adjustment chain','full Native/LOO state beyond selected substitutions','Market axes/path beyond participation','real historical missing-day status accounting','full population factor QA'],external_acceptance='NOT_GRANTED')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    for line in (a.input/'checksums/SHA256SUMS.txt').read_text().splitlines():
        digest,path=line.split('  ',1);assert hashlib.sha256((a.input/path).read_bytes()).hexdigest()==digest,'PAYLOAD_SHA_MISMATCH:'+path
    result=run(a.input);a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'ORACLE_OUTPUT.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf8')
    print(json.dumps(dict(acceptance=result['acceptance'],checks=result['checks'],period_checks=result['period_checks'],errors=len(result['errors']))))
    raise SystemExit(bool(result['errors']))
