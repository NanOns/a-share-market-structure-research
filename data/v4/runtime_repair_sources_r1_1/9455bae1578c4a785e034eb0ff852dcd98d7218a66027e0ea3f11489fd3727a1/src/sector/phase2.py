"""Current snapshot atomic market and sector aggregates v1; no scores."""
import numpy as np
import pandas as pd
from sector.roles import sector_role

VERSION='sector-factor-contract-v1.1-correctness'
MARKET_VERSION='market-regime-factor-v1.0'
BASIS='CURRENT_TDX_MEMBERSHIP'


def specs(sector=False):
    prefix='sector_' if sector else ''
    out={}
    for n in (5,10,20,60): out[prefix+f'ret{n}_median' if sector else f'market_ret{n}_median']=(f'RET{n}','median')
    for n in (5,20,60): out[prefix+f'breadth_ret{n}_pos']=(f'RET{n}','positive')
    for n in (20,60):
        out[prefix+f'breadth_above_ma{n}']=(f'above_ma{n}','positive')
        out[prefix+f'trend_r2_{n}_median']=(f'TREND_R2_{n}','median')
        out[prefix+f'mdd{n}_median']=(f'MDD{n}','median')
    out[prefix+'pos60_median']=('POS60','median')
    if sector:
        out['sector_ret20_mean']=('RET20','mean')
        for n in (20,60):
            out[f'sector_trend_slope{n}_median']=(f'TREND_SLOPE_{n}','median')
            out[f'sector_dist_high{n}_median']=(f'DIST_HIGH{n}','median')
        for n in (20,120): out[f'sector_pos{n}_median']=(f'POS{n}','median')
        out['sector_amount_ratio_median']=('amount_ratio_5_20','median')
        out['sector_amount_expansion_breadth']=('amount_expansion','positive')
        out['sector_return_concentration20_median']=('RETURN_CONCENTRATION_20','median')
    else:
        for n in (20,60): out[f'breadth_trend{n}_pos']=(f'TREND_SLOPE_{n}','positive')
        out['market_rs20_p75']=('RS20','p75'); out['market_rs20_p25']=('RS20','p25')
        out['mdd20_p10']=('MDD20','p10')
        out['amount_ratio_5_20_median']=('amount_ratio_5_20','median')
        out['active_amount_expansion_ratio']=('amount_expansion','positive')
    return out


def aggregate(series,op):
    s=pd.to_numeric(series,errors='coerce'); s=s[np.isfinite(s)]
    if not len(s): return np.nan,0
    if op=='positive': value=float((s>0).mean())
    elif op.startswith('p'): value=float(s.quantile(int(op[1:])/100,interpolation='linear'))
    else: value=float(getattr(s,op)())
    return value,len(s)


def prepare(factors,latest):
    f=factors.merge(latest,on='security_id',how='left',validate='one_to_one')
    f['valid_member']=f.security_id.str.fullmatch(r'(SH|SZ|BJ)\.\d{6}') & f.missing_state.notna() & ~f.missing_state.isin(['FILE_MISSING','DELISTED_OR_INACTIVE'])
    for n in (20,60): f[f'above_ma{n}']=(f.aligned_close-f[f'MA{n}']).where(f.aligned_close.notna() & f[f'MA{n}'].notna())
    f['amount_ratio_5_20']=(f.AMOUNT_MA5/f.AMOUNT_MA20).where(f.AMOUNT_MA20>0)
    f['amount_expansion']=f.amount_ratio_5_20-1
    return f


def market_vector(stocks):
    normal=stocks[stocks.universe_status=='IN_NORMAL_UNIVERSE']
    valid=normal[normal.valid_member]
    row={'normal_universe_count':len(normal),'valid_universe_count':len(valid),'market_factor_version':MARKET_VERSION,'quality_flag':'OK'}
    for name,(col,op) in specs().items():
        value,count=aggregate(valid[col],op)
        row[name]=value; row[name+'__valid_count']=count
        row[name+'__valid_ratio']=count/len(normal) if len(normal) else np.nan
    if any(row[n+'__valid_count']==0 for n in specs()): row['quality_flag']='FACTOR_VALUE_UNAVAILABLE'
    return row


def validity(total,valid,role):
    reasons=[]
    if total < (5 if role=='INDUSTRY' else 8): reasons.append('MIN_TOTAL_MEMBERS')
    if valid<5: reasons.append('MIN_VALID_MEMBERS')
    if not total or valid/total<.70: reasons.append('LOW_COVERAGE')
    if role=='EXCLUDE_FROM_THEME_RANK': reasons.append('EXCLUDED_ROLE')
    return not reasons,'|'.join(reasons)


def top3(values):
    s=pd.to_numeric(values,errors='coerce'); s=s[np.isfinite(s)]
    p=s.where(s>0,0)
    if len(s)<8 or p.sum()<=0: return np.nan,len(s)
    return float(p.nlargest(3).sum()/p.sum()),len(s)


def sectors(stocks,memberships):
    rows=[]; member_frames={}; normal=stocks[stocks.universe_status=='IN_NORMAL_UNIVERSE']
    benchmarks={n:aggregate(normal[f'RET{n}'],'median')[0] for n in (5,10,20,60)}
    for (typ,code,name),group in memberships.groupby(['sector_type','sector_code','sector_name'],sort=True):
        role=sector_role(typ,name); stype={'industry':'INDUSTRY','concept':'THEME','style':'STYLE'}[typ]
        ids=sorted(set(group.security_id.dropna())); joined=pd.DataFrame({'security_id':pd.Series(ids,dtype='str')}).merge(stocks,on='security_id',how='left',validate='one_to_one')
        valid=joined[joined.valid_member.eq(True)]; total=len(ids); count=len(valid)
        good,reason=validity(total,count,role)
        sid=f'{stype}:{code}'
        row=dict(sector_id=sid,sector_name=name,sector_type=stype,sector_role=role,
            membership_basis=BASIS,pit_membership=False,historical_backtest_safe=False,
            total_member_count=total,valid_member_count=count,invalid_member_count=total-count,
            tradable_member_count=int(valid.tradable.eq(True).sum()),suspended_member_count=int(valid.missing_state.eq('SUSPENDED').sum()),
            coverage=count/total if total else 0,tradable_coverage=float(valid.tradable.eq(True).sum()/total) if total else 0,
            sector_valid=good,invalid_reason=reason,sector_factor_version=VERSION,quality_flag='OK' if good else reason)
        for field,(col,op) in specs(True).items():
            value,num=aggregate(valid[col],op)
            row[field]=value; row[field+'__valid_count']=num; row[field+'__valid_ratio']=num/total if total else 0
        common=valid[pd.to_numeric(valid.RET5,errors='coerce').map(np.isfinite) & pd.to_numeric(valid.RET20,errors='coerce').map(np.isfinite)]
        row['breadth_5_20_common_valid_count']=len(common);row['breadth_5_20_common_valid_ratio']=len(common)/total if total else 0
        row['breadth_ret5_pos_common']=float((common.RET5>0).mean()) if len(common) else np.nan
        row['breadth_ret20_pos_common']=float((common.RET20>0).mean()) if len(common) else np.nan
        row['breadth_5_minus_20_common']=row['breadth_ret5_pos_common']-row['breadth_ret20_pos_common'] if len(common) else np.nan
        required={'current_strength':['RET20','POS60','MDD20'],'stabilization':['RET5','RET20','amount_ratio_5_20'],'reacceleration':['RET60','RET20','RET5','amount_ratio_5_20']}
        for scanner,columns in required.items():
            mask=pd.Series(True,index=valid.index)
            for col in columns:mask &= pd.to_numeric(valid[col],errors='coerce').map(np.isfinite)
            row[f'{scanner}_joint_valid_count']=int(mask.sum());row[f'{scanner}_joint_valid_ratio']=float(mask.sum()/total) if total else 0
        for n in (5,10,20,60):
            val,num=aggregate(valid[f'RET{n}'],'median')
            row[f'sector_rs{n}']=val-benchmarks[n]
            row[f'sector_rs{n}__valid_count']=num; row[f'sector_rs{n}__valid_ratio']=num/total if total else 0
            alternative,_=aggregate(valid[f'RS{n}'],'median')
            row[f'sector_rs{n}__equivalence_error']=row[f'sector_rs{n}']-alternative
        val,num=top3(valid.RET1)
        row['top3_concentration']=val; row['top3_concentration__valid_count']=num; row['top3_concentration__valid_ratio']=num/total if total else 0
        rows.append(row); member_frames[sid]=joined
    return rank_sectors(pd.DataFrame(rows)),member_frames


RANKS={'sector_rs20_pct':'sector_rs20','sector_breadth20_pct':'sector_breadth_ret20_pos',
       'sector_mdd20_pct':'sector_mdd20_median','sector_amount_ratio_pct':'sector_amount_ratio_median'}


def rank_sectors(frame):
    frame=frame.copy()
    for name,col in RANKS.items():
        mask=frame.sector_valid & frame[col].notna() & frame.sector_role.ne('EXCLUDE_FROM_THEME_RANK')
        frame[name]=np.nan; frame[name+'__rank_denominator']=0
        groups=frame.loc[mask].groupby('sector_type')[col]
        frame.loc[mask,name]=groups.rank(pct=True,method='average',ascending=True)
        frame.loc[mask,name+'__rank_denominator']=groups.transform('count').astype(int)
    return frame


def snapshot_guard(dates,cutoff,membership_date):
    if membership_date!=cutoff or any(d!=cutoff for d in dates): raise ValueError('CURRENT_SNAPSHOT_ONLY_NO_BACKFILL_OR_FUTURE')


def phase2_gate(checks): return 'PASS' if all(checks.values()) else 'BLOCKED'
