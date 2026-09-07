from __future__ import annotations
import hashlib,json,math
import numpy as np
import pandas as pd

VERSION='v2-diagnostic-factor-v1.1-anchor-corrected';SHADOW_RULESET='v2-shadow-foundation-v1.1-anchor-corrected'
def finite(s):
 x=pd.Series(pd.to_numeric(s,errors='coerce'));return x[np.isfinite(x)]
def up_day_ratio20(close,min_valid=15):
 r=finite(close).pct_change().dropna().tail(20);n=len(r)
 return (float((r>0).mean()) if n>=min_valid else np.nan,n,n/20)
def recent_peak20(dates,close):
 x=pd.DataFrame({'date':dates,'close':pd.to_numeric(close,errors='coerce')}).dropna().tail(20)
 if x.empty:return (None,np.nan,np.nan,np.nan)
 peak=x.close.max();positions=np.flatnonzero(x.close.to_numpy()==peak);pos=int(positions[-1]);row=x.iloc[pos]
 return (row.date,float(peak),int(len(x)-1-pos),float(x.close.iloc[-1]/peak-1))
def nonoverlap_ranges(close,high,low):
 x=pd.DataFrame({'c':close,'h':high,'l':low}).apply(pd.to_numeric,errors='coerce').dropna().tail(20)
 if len(x)<20:return (np.nan,np.nan,np.nan)
 p,r=x.iloc[:10],x.iloc[10:];pv=(p.h.max()-p.l.min())/p.c.iloc[0];rv=(r.h.max()-r.l.min())/r.c.iloc[0]
 return float(rv),float(pv),float(rv/pv) if pv>0 else np.nan
def nonoverlap_vol(close):
 x=finite(close).tail(21)
 if len(x)<21:return (np.nan,np.nan,np.nan)
 lr=np.log(x/x.shift()).dropna();p,r=lr.iloc[:10],lr.iloc[10:];pv=p.std(ddof=1);rv=r.std(ddof=1)
 return float(rv),float(pv),float(rv/pv) if pv>0 else np.nan
def pullback_amount(dates,close,amount):
 x=pd.DataFrame({'date':dates,'c':close,'a':amount}).apply(lambda s:pd.to_numeric(s,errors='coerce') if s.name!='date' else s).dropna().tail(20).reset_index(drop=True)
 if x.empty:return (np.nan,np.nan,np.nan)
 peak_value=x.c.max();positions=np.flatnonzero(x.c.to_numpy()==peak_value);peak=int(positions[-1])
 advance=x.iloc[:peak+1].a;pull=x.iloc[peak+1:].a
 if len(advance)<2 or len(pull)<1:return (np.nan,np.nan,np.nan)
 a=advance.mean();b=pull.mean()
 return float(a),float(b),float(b/a) if a>0 else np.nan
def quality_percentiles(frame,group='sector_id'):
 out=frame.copy();groups=out.groupby(group);total=groups[group].transform('size')
 specs=(('member_trend_r2_20_pct','TREND_R2_20',True),('member_mdd20_quality_pct','MDD20',True),
        ('member_pos60_pct','POS60',True),('member_return_concentration_quality_pct','RETURN_CONCENTRATION_20',False))
 for target,source,ascending in specs:
  numeric=pd.to_numeric(out[source],errors='coerce');valid=numeric.where(np.isfinite(numeric))
  out[target]=valid.groupby(out[group]).rank(pct=True,method='average',ascending=ascending)
  count=valid.groupby(out[group]).transform('count').astype('int64')
  out[target+'__valid_count']=count
  out[target+'__valid_ratio']=(count/total).where(total>0)
  out[target+'__rank_denominator']=count
 return out
PRICE_WORDS=('强势','弱势','涨停','跌停','连板','断板','新高','新低','异动','上榜','振荡','换手','活跃')
EVENT_WORDS=('重组','增持','减持','回购','解禁','复牌','要约','转让','调研','上市')
STATUS_WORDS=('亏损','绩优','微利','风险提示','高负债','高商誉','高质押')
def classify_style(name):
 if any(x in name for x in PRICE_WORDS):return 'PRICE_BEHAVIOR'
 if any(x in name for x in EVENT_WORDS):return 'EVENT'
 if any(x in name for x in STATUS_WORDS):return 'STATUS'
 return 'UNKNOWN'
def shadow_identity(files,baseline):
 payload={'version':'shadow-computation-identity-v1.0','shadow_ruleset_id':SHADOW_RULESET,'files':files,'v1_comparison_baseline':baseline}
 payload['sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest();return payload
