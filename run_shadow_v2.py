from __future__ import annotations
from pathlib import Path
from datetime import date,timedelta
import argparse,hashlib,json,os,tempfile
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from shadow_v2.diagnostics import *
from common.paths import resolve_tdx_root

ROOT=Path(__file__).resolve().parent;TDX_ROOT=resolve_tdx_root(ROOT);BASE_RUN='4255c2f108ac4cdabca3e212079d8bf8';CUTOFF='20260904'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(p,b):
 p.parent.mkdir(parents=True,exist_ok=True);fd,t=tempfile.mkstemp(dir=p.parent,prefix='.'+p.name,suffix='.tmp');os.write(fd,b);os.fsync(fd);os.close(fd);os.replace(t,p)
def run(requested='latest'):
 if requested!='latest':raise ValueError('SHADOW_LATEST_ONLY')
 cur=json.loads((ROOT/'reports/current/CURRENT_RELEASE.json').read_text('utf8'));before=(ROOT/'reports/current/CURRENT_RELEASE.json').read_bytes()
 base={'formal_cutoff':CUTOFF,'formal_run_id':BASE_RUN,'manifest_sha256':cur['latest_release']['manifest_sha256'],'computation_identity':cur['latest_release']['computation_identity'],'contracts':cur['current_ruleset_versions'],'immutable':True}
 d=date(int(CUTOFF[:4]),int(CUTOFF[4:6]),int(CUTOFF[6:]));start=d-timedelta(days=100);cols=['security_id','date','adj_close','adj_high','adj_low','raw_amount','has_actual_bar','universe_status']
 bars=pq.read_table(ROOT/'data/normalized/adjusted_daily.parquet',columns=cols,filters=[('date','>=',start),('date','<=',d)]).to_pandas();bars=bars[bars.has_actual_bar.eq(True)]
 factors=pq.read_table(ROOT/'data/factors/factors_daily.parquet',filters=[('date','=',d)]).to_pandas();factors=factors[factors.universe_status.eq('IN_NORMAL_UNIVERSE')]
 rows=[]
 for sid,g in bars[bars.security_id.isin(factors.security_id)].sort_values('date').groupby('security_id'):
  up,n,ratio=up_day_ratio20(g.adj_close);pdte,pclose,days,dd=recent_peak20(g.date,g.adj_close);rr,pr,rc=nonoverlap_ranges(g.adj_close,g.adj_high,g.adj_low);rv,pv,vc=nonoverlap_vol(g.adj_close);advance_amt,pullback_amt,ar=pullback_amount(g.date,g.adj_close,g.raw_amount)
  rows.append({'security_id':sid,'date':d,'UP_DAY_RATIO20':up,'UP_DAY_RATIO20__valid_count':n,'UP_DAY_RATIO20__valid_ratio':ratio,'recent_peak_date_20':pdte,'recent_peak_close_20':pclose,'days_since_peak_20':days,'current_drawdown_from_peak_20':dd,'advance_amount_mean':advance_amt,'pullback_amount_mean':pullback_amt,'pullback_amount_ratio':ar,'recent_range_10':rr,'prior_range_10':pr,'range_contraction_ratio':rc,'recent_realized_vol_10':rv,'prior_realized_vol_10':pv,'realized_vol_contraction_ratio':vc})
 out=factors[['security_id','RETURN_CONCENTRATION_20','TREND_R2_20','MDD20','POS60']].merge(pd.DataFrame(rows),on='security_id',how='left');out['LIMIT_UP_DAY_COUNT_20']=pd.NA;out['limit_up_status']='NOT_AVAILABLE';out['shadow']=True;out['production_eligible']=False;out['shadow_diagnostic_version']=VERSION
 from phase4_runner import memberships
 mem=memberships(TDX_ROOT)[['security_id','sector_id']]
 quality=quality_percentiles(mem.merge(factors[['security_id','TREND_R2_20','MDD20','POS60','RETURN_CONCENTRATION_20']],on='security_id',how='inner'))
 qcols=['member_trend_r2_20_pct','member_mdd20_quality_pct','member_pos60_pct','member_return_concentration_quality_pct']
 q=quality.groupby('security_id')[qcols].max().reset_index();out=out.merge(q,on='security_id',how='left')
 release=ROOT/f'reports/releases/{CUTOFF}/{BASE_RUN}';v1=pd.read_csv(release/'candidates.csv',encoding='utf-8-sig');cmp=v1[['security_id','primary_pattern','scanner_hits','priority_score','research_priority']].rename(columns={'primary_pattern':'v1_primary_pattern','scanner_hits':'v1_hits','priority_score':'v1_priority','research_priority':'v1_rating'});out=out.merge(cmp,on='security_id',how='left');out['v2_primary_pattern']=pd.NA
 target=ROOT/f'data/shadow/v2/{CUTOFF}';report=ROOT/f'reports/shadow/v2/{CUTOFF}';target.mkdir(parents=True,exist_ok=True);report.mkdir(parents=True,exist_ok=True)
 table=pa.Table.from_pandas(out,preserve_index=False);tmp=target/'.V2_DIAGNOSTIC_FACTORS.tmp';pq.write_table(table,tmp,compression='zstd');os.replace(tmp,target/'V2_DIAGNOSTIC_FACTORS.parquet');(report/'V2_DIAGNOSTIC_FACTORS.parquet').write_bytes((target/'V2_DIAGNOSTIC_FACTORS.parquet').read_bytes())
 nums=['UP_DAY_RATIO20','RETURN_CONCENTRATION_20','current_drawdown_from_peak_20','pullback_amount_ratio','range_contraction_ratio','realized_vol_contraction_ratio'];summary={}
 for group,frame in [('NORMAL_UNIVERSE',out),*[(p,out[out.v1_primary_pattern.eq(p)]) for p in out.v1_primary_pattern.dropna().unique()]]:
  summary[group]={c:{'count':len(frame),'valid_count':int(frame[c].notna().sum()),'null_count':int(frame[c].isna().sum()),**{q:frame[c].quantile(v) for q,v in [('p10',.1),('p25',.25),('median',.5),('p75',.75),('p90',.9)]}} for c in nums}
 styles=pd.read_csv(release/'sectors.csv',encoding='utf-8-sig');styles=styles[styles.sector_type.eq('STYLE')][['sector_id','sector_name']];styles['STYLE_SEMANTIC_CLASS']=styles.sector_name.map(classify_style);styles['classification_basis']='AUDITED_NAME_RULE_OR_UNKNOWN'
 exposure=mem.merge(styles[['sector_id']],on='sector_id').merge(pd.read_csv(release/'stocks.csv',encoding='utf-8-sig')[['security_id','sector_leader']],on='security_id',how='left').merge(v1[['security_id','research_priority']],on='security_id',how='left')
 exp=exposure.groupby('sector_id').agg(current_leader_exposure=('sector_leader',lambda x:int(x.astype(str).str.lower().eq('true').sum())),current_a_plus_a_exposure=('research_priority',lambda x:int(x.isin(['A+','A']).sum()))).reset_index();styles=styles.merge(exp,on='sector_id',how='left').fillna({'current_leader_exposure':0,'current_a_plus_a_exposure':0});styles.to_csv(report/'V2_STYLE_CLASSIFICATION.csv',index=False,encoding='utf-8-sig')
 files={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'src/shadow_v2/diagnostics.py',ROOT/'run_shadow_v2.py',ROOT/'docs/V2_SHADOW_CONTRACT_V1.md',ROOT/'docs/V2_DIAGNOSTIC_FACTOR_CONTRACT_V1.md')};identity=shadow_identity(files,base)
 atomic(report/'V1_BASELINE_FREEZE_RECEIPT.json',(json.dumps(base,ensure_ascii=False,indent=2)+'\n').encode());atomic(report/'V2_DIAGNOSTIC_SUMMARY.json',(json.dumps(summary,ensure_ascii=False,indent=2,default=str)+'\n').encode());atomic(report/'V2_SHADOW_IDENTITY.json',(json.dumps(identity,ensure_ascii=False,indent=2)+'\n').encode())
 assert before==(ROOT/'reports/current/CURRENT_RELEASE.json').read_bytes()
 return {'rows':len(out),'report_dir':str(report),'shadow_identity':identity,'v1_pointer_unchanged':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--date',default='latest');a=p.parse_args();print(json.dumps(run(a.date),ensure_ascii=False,indent=2))
