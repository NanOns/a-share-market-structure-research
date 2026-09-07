"""Independent latest-window recomputation using Python math/statistics."""
import math
import statistics as st
import numpy as np
import pandas as pd
from factors.registry import REGISTRY, NAMES
from validation.phase0_2b import atomic, encoded


def reference(w,rule):
    k=rule['kind']; n=rule['min_samples']; w=w.tail(n)
    cols=['amount'] if k.startswith('amount') else ['close']
    if k in ('pos','dist'): cols+=['high']
    if k=='pos': cols+=['low']
    if len(w)<n or not all(math.isfinite(float(x)) for c in cols for x in w[c]): return math.nan
    c=list(map(float,w.close)); a=list(map(float,w.amount))
    if rule['positive'] and min(c)<=0: return math.nan
    if k=='ret': return c[-1]/c[0]-1
    if k=='ma': return st.mean(c)
    if k=='amount_ma': return st.mean(a)
    if k=='amount_ratio': return a[-1]/st.mean(a) if st.mean(a)>0 else math.nan
    if k in ('slope','r2'):
        y=list(map(math.log,c)); xm=(n-1)/2; ym=st.mean(y)
        slope=sum((i-xm)*(v-ym) for i,v in enumerate(y))/sum((i-xm)**2 for i in range(n))
        if k=='slope': return slope
        total=sum((v-ym)**2 for v in y)
        return 1-sum((v-ym-slope*(i-xm))**2 for i,v in enumerate(y))/total if max(c)!=min(c) else math.nan
    if k=='pos':
        hi=max(w.high); lo=min(w.low)
        return (c[-1]-lo)/max(hi-lo,1e-12) if hi!=lo else math.nan
    if k=='dist': return c[-1]/max(w.high)-1 if max(w.high)>0 else math.nan
    if k=='mdd': return min(v/max(c[:i+1])-1 for i,v in enumerate(c))
    if k=='vol': return st.stdev(math.log(c[i]/c[i-1]) for i in range(1,n))
    if k=='concentration':
        r=[max(c[i]/c[i-1]-1,0) for i in range(1,n)]
        return max(r)/sum(r) if sum(r)>0 else math.nan
    raise ValueError(k)


def audit_outputs(root,tdx,frame,contexts,cutoff,metadata):
    latest=frame[frame.date==frame.date.max()]
    normal=latest[latest.universe_status=='IN_NORMAL_UNIVERSE']
    distributions=[]
    for rule in REGISTRY:
        name=rule['name']; values=normal[name].dropna()
        quantiles=values.quantile([0,.01,.05,.5,.95,.99,1]).to_list() if len(values) else [None]*7
        flags=normal[name+'__quality_flag']
        distributions.append(dict(factor_name=name,factor_version=rule['version'],normal_universe_count=len(normal),
            calculated_count=len(values),non_null_count=len(values),null_count=len(normal)-len(values),null_ratio=1-len(values)/len(normal) if len(normal) else None,
            **dict(zip(['min','p01','p05','median','p95','p99','max'],quantiles)),
            insufficient_history_count=int(flags.str.contains('INSUFFICIENT_HISTORY').sum()),
            nonpositive_price_count=int(flags.str.contains('NONPOSITIVE_QFQ').sum()),
            missing_data_count=int(flags.str.contains('MISSING_DATA').sum()),formula_hash=rule['formula_hash']))
    output=root/'reports/phase1'
    atomic(output/'FACTOR_DISTRIBUTION.csv',pd.DataFrame(distributions).to_csv(index=False).encode('utf-8-sig'),tdx)
    sample_rows=[]; pass_all=True; rs_pass=True
    for sid,context in contexts.items():
        row=latest[latest.security_id==sid].iloc[0]
        atomic(output/f'SAMPLE_WINDOW_{sid}.csv',context.tail(121).to_csv(index=False).encode('utf-8-sig'),tdx)
        for rule in REGISTRY:
            name=rule['name']
            if rule['kind']=='rs':
                ret='RET'+str(rule['window']); v=normal[ret].dropna().tolist()
                expected=float(row[ret])-st.median(v) if len(v)>=100 and math.isfinite(row[ret]) else math.nan
            else: expected=reference(context,rule)
            actual=float(row[name])
            match=(math.isnan(expected) and math.isnan(actual)) or math.isclose(expected,actual,rel_tol=1e-9,abs_tol=1e-10)
            pass_all=pass_all and match
            sample_rows.append({'security_id':sid,'factor':name,'window':rule['window'],'formula':rule['formula'],
                                'reference':expected,'calculated':actual,'match':match})
    for n in (5,10,20,60):
        v=normal[f'RET{n}'].dropna().to_numpy(); expected_count=len(v)
        assert (latest[f'rs_valid_universe_count_{n}']==expected_count).all()
        if expected_count>=100:
            mask=latest[f'RET{n}'].notna()
            rs_pass=rs_pass and np.allclose(latest.loc[mask,f'RS{n}'],latest.loc[mask,f'RET{n}']-st.median(v),atol=1e-12)
    assert len(contexts)==5 and len(sample_rows)==145 and pass_all and rs_pass
    lines=['# Factor sample calculations',f'\nCutoff {cutoff}; independent math/statistics recomputation. 145/145 checks PASS.',
           '\nInput windows: SAMPLE_WINDOW_<security_id>.csv (121 market sessions, sufficient for the longest 120-session factor). Close/amount are aligned; high/low NULL on suspension. RS additionally uses the same-day NORMAL_UNIVERSE returns.',
           '\n| Security | Factor | Formula | Reference | Output | Match |','|---|---|---|---:|---:|---|']
    for r in sample_rows: lines.append(f"| {r['security_id']} | {r['factor']} | {r['formula']} | {r['reference']:.12g} | {r['calculated']:.12g} | {r['match']} |")
    atomic(output/'FACTOR_SAMPLE_CALC.md','\n'.join(lines).encode('utf8'),tdx)
    atomic(output/'FACTOR_AUDIT.json',encoded({'cutoff_date':cutoff,'scope':'LATEST_NORMAL_UNIVERSE','factor_count':29,
        'factors':distributions,'sample_checks':145,'sample_pass':pass_all,'rs_pass':bool(rs_pass),
        'rs_benchmark':'NORMAL_UNIVERSE_MEDIAN','index_ohlc_used':False}),tdx)
    return {'sample_pass':pass_all,'rs_pass':bool(rs_pass)}
