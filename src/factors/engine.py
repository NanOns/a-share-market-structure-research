import numpy as np
import pandas as pd
from .registry import REGISTRY, VERSION


def calculate(context, *, cutoff=None):
    if cutoff is not None: context=context[context.date<=cutoff]
    result={}; diagnostics={}
    for rule in REGISTRY:
        name,kind,n=rule['name'],rule['kind'],rule['window']
        if kind=='rs': continue
        count=rule['min_samples']; w=context.tail(count)
        cols=['amount'] if kind.startswith('amount') else ['close']
        if kind in ('pos','dist'): cols+=['high']
        if kind=='pos': cols+=['low']
        valid=np.isfinite(w[cols].to_numpy(dtype=float)).all(axis=1)
        valid_count=int(valid.sum()); flags=[]; value=np.nan
        if len(w)<count or valid_count<count:
            flags.append('INSUFFICIENT_HISTORY')
            if w.state.isin(['MISSING_DATA','FILE_MISSING','DELISTED_OR_INACTIVE']).any(): flags.append('MISSING_DATA')
        if rule['positive'] and (w.close<=0).any(): flags+=['NONPOSITIVE_QFQ','NONPOSITIVE_PRICE_WINDOW']
        if len(w) and w.synthetic.sum()/count>.25: flags.append('SUSPENSION_HEAVY_WINDOW')
        blocked=valid_count<count or len(w)<count or 'NONPOSITIVE_QFQ' in flags
        if not blocked:
            c=w.close.to_numpy(dtype=float); a=w.amount.to_numpy(dtype=float)
            if kind=='ret': value=c[-1]/c[0]-1
            elif kind=='ma': value=c.mean()
            elif kind in ('slope','r2'):
                x=np.arange(n,dtype=float); xc=x-x.mean(); y=np.log(c); yc=y-y.mean()
                slope=float(xc@yc/(xc@xc)); sst=float(yc@yc)
                if kind=='slope': value=slope
                elif np.ptp(c)==0: flags.append('CONSTANT_PRICE_WINDOW')
                else: value=1-float(((yc-slope*xc)**2).sum())/sst
            elif kind=='pos':
                hi=w.high.max(); lo=w.low.min()
                if hi==lo: flags.append('ZERO_PRICE_RANGE')
                else: value=(c[-1]-lo)/max(hi-lo,rule['epsilon'])
            elif kind=='dist':
                hi=w.high.max()
                if hi<=0: flags.append('NONPOSITIVE_QFQ')
                else: value=c[-1]/hi-1
            elif kind=='mdd': value=float(np.min(c/np.maximum.accumulate(c)-1))
            elif kind=='vol': value=float(np.std(np.diff(np.log(c)),ddof=1))
            elif kind=='amount_ma': value=a.mean()
            elif kind=='amount_ratio':
                if a.mean()<=0: flags.append('ZERO_AMOUNT')
                else: value=a[-1]/a.mean()
            elif kind=='concentration':
                positive=np.maximum(c[1:]/c[:-1]-1,0)
                if positive.sum()==0: flags.append('ZERO_POSITIVE_RETURN_SUM')
                else: value=positive.max()/positive.sum()
        if np.isfinite(value) and rule['output_unit']=='ratio' and abs(value)>10: flags.append('EXTREME_VALUE')
        if not np.isfinite(value): value=np.nan
        result[name]=value
        result[name+'__valid_sample_count']=valid_count
        result[name+'__quality_flag']='|'.join(sorted(set(flags))) or 'OK'
        diagnostics[name]=dict(valid_sample_count=valid_count,flags=flags,value=value)
    return result,diagnostics


def add_rs(frame):
    frame=frame.copy()
    for n in (5,10,20,60):
        ret=f'RET{n}'; rs=f'RS{n}'
        eligible=frame.universe_status.eq('IN_NORMAL_UNIVERSE') & frame[ret].notna()
        grouped=frame.loc[eligible].groupby('date')[ret].agg(['median','count'])
        med=frame.date.map(grouped['median']); count=frame.date.map(grouped['count']).fillna(0).astype(int)
        frame[f'rs_valid_universe_count_{n}']=count
        frame[rs]=(frame[ret]-med).where(count>=100)
        frame[rs+'__valid_sample_count']=frame[ret+'__valid_sample_count']
        frame[rs+'__quality_flag']=frame[ret+'__quality_flag']
        frame.loc[count<100,rs+'__quality_flag']=frame.loc[count<100,rs+'__quality_flag'].map(lambda f: ('' if f=='OK' else f+'|')+'INSUFFICIENT_RS_UNIVERSE')
    flags=[c for c in frame if c.endswith('__quality_flag')]
    frame['factor_quality_flag']=frame[flags].apply(lambda r:'|'.join(sorted({v for x in r for v in x.split('|') if v!='OK'})) or 'OK',axis=1)
    frame['factor_version']=VERSION
    frame['calculation_status']='CALCULATED'
    return frame
