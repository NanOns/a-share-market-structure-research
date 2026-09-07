from __future__ import annotations
import argparse,hashlib,json,os,sys,tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/"src"))
from phase4_runner import memberships,sector_context
from shadow_v2.diagnostics import quality_percentiles
from shadow_v2.sector_leader import RULESET_ID,choose_primary,classify,quality_class,semantic_category,support_counts
from common.paths import resolve_tdx_root
CUTOFF="20260904";BASE_RUN="4255c2f108ac4cdabca3e212079d8bf8";TDX_ROOT=resolve_tdx_root(ROOT)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(p,b):
 p.parent.mkdir(parents=True,exist_ok=True);fd,t=tempfile.mkstemp(dir=p.parent,prefix="."+p.name,suffix=".tmp")
 try:os.write(fd,b);os.fsync(fd)
 finally:os.close(fd)
 os.replace(t,p)
def write_json(p,x):atomic(p,(json.dumps(x,ensure_ascii=False,indent=2,default=str)+"\n").encode())
def write_csv(p,x):atomic(p,x.to_csv(index=False).encode("utf-8-sig"))
def dist(frame):
 result={}
 for c in ("member_rs20_pct","member_trend_r2_20_pct","member_mdd20_quality_pct","member_pos60_pct","member_return_concentration_quality_pct"):
  s=pd.to_numeric(frame[c],errors="coerce");q=s.quantile([.1,.25,.5,.75,.9]);result[c]={"valid_count":int(s.notna().sum()),"null_count":int(s.isna().sum()),**{n:(None if pd.isna(v) else float(v)) for n,v in zip(("p10","p25","median","p75","p90"),q)}}
 return result
def change_reason(v1,v2,row):
 if v1==v2:return "NO_CHANGE"
 if str(v1).startswith("STYLE:") and row.v2_primary_sector_semantic!="PRICE_BEHAVIOR_STYLE":return "PRICE_BEHAVIOR_STYLE_DEPRIORITIZED"
 if row.v2_primary_sector_semantic=="ECONOMIC_SECTOR":return "ECONOMIC_SECTOR_PREFERRED"
 if row.reacceleration:return "REACCELERATION_PREFERRED"
 return "HIGHER_SECTOR_RS_OR_MEMBER_RS"
def run(requested="latest"):
 if requested!="latest":raise ValueError("SHADOW_LATEST_ONLY")
 pointer=ROOT/"reports/current/CURRENT_RELEASE.json";before=pointer.read_bytes();current=json.loads(before);identity=current["latest_release"]["computation_identity"]["sha256"]
 release=ROOT/f"reports/releases/{CUTOFF}/{BASE_RUN}";v1paths=[release/x for x in ("stocks.csv","candidates.csv","manifest.json")]+[pointer];hashes={str(p.relative_to(ROOT)):sha(p) for p in v1paths}
 stock=pd.read_csv(release/"stocks.csv",encoding="utf-8-sig");sector=pd.read_csv(release/"sectors.csv",encoding="utf-8-sig");mem=memberships(TDX_ROOT)[["security_id","sector_id"]]
 factor_date=pd.Timestamp(CUTOFF).date();factor=pq.read_table(ROOT/"data/factors/factors_daily.parquet",filters=[("date","=",factor_date)]).to_pandas();factor=factor[factor.universe_status.eq("IN_NORMAL_UNIVERSE")]
 if factor.empty or set(pd.to_datetime(factor.date).dt.strftime("%Y%m%d"))!={CUTOFF}:raise RuntimeError("V2_FACTOR_CUTOFF_MISMATCH")
 _,detail=sector_context(factor,mem,sector);qual=detail[detail.leader_rank_ok].drop(columns=["member_pos60_pct"]).copy()
 # Preserve every current member in the coverage denominator. Finite factor
 # values are ranked; absent values remain explicit missing evidence.
 quality_input=mem.merge(factor[["security_id","TREND_R2_20","MDD20","POS60","RETURN_CONCENTRATION_20"]],on="security_id",how="left",validate="many_to_one")
 quality=quality_percentiles(quality_input).drop(columns=["TREND_R2_20","MDD20","POS60","RETURN_CONCENTRATION_20"])
 qual=qual.merge(quality,on=["security_id","sector_id"],how="left",validate="one_to_one")
 styles=pd.read_csv(ROOT/f"reports/shadow/v2/{CUTOFF}/V2_STYLE_CLASSIFICATION.csv",encoding="utf-8-sig")[["sector_id","STYLE_SEMANTIC_CLASS"]]
 qual=qual.merge(styles,on="sector_id",how="left");qual["sector_semantic"]=[semantic_category(t,c) for t,c in zip(qual.sector_type,qual.STYLE_SEMANTIC_CLASS)]
 leaders=stock[stock.sector_leader.astype(str).str.lower().eq("true")].copy();leader_ids=set(leaders.security_id);qual=qual[qual.security_id.isin(leader_ids)]
 rows=[];quality_cols=["member_trend_r2_20_pct","member_mdd20_quality_pct","member_pos60_pct","member_return_concentration_quality_pct"]
 qual["quality_evidence_sufficient"]=True
 for c in quality_cols:
  qual["quality_evidence_sufficient"] &= (pd.to_numeric(qual[c+"__valid_count"],errors="coerce")>=5) & (pd.to_numeric(qual[c+"__valid_ratio"],errors="coerce")>=.70) & pd.to_numeric(qual[c],errors="coerce").map(np.isfinite)
 groups={sid:g for sid,g in qual.groupby("security_id")};empty=qual.iloc[0:0]
 for _,s in stock.sort_values("security_id").iterrows():
  is_leader=str(s.sector_leader).lower()=="true";g=groups.get(s.security_id,empty);relations=g.to_dict("records");primary=choose_primary(relations)
  counts={k:int(g.sector_semantic.eq(k).sum()) for k in ("ECONOMIC_SECTOR","NON_PRICE_STYLE","PRICE_BEHAVIOR_STYLE","UNKNOWN_STYLE")}
  if primary:
   qclasses=[quality_class(primary[c],primary[c+"__valid_count"],primary[c+"__valid_ratio"]) for c in quality_cols];strong,nonweak=support_counts(qclasses);semantic=primary["sector_semantic"]
  else:qclasses=["QUALITY_DATA_INSUFFICIENT"]*4;strong=nonweak=0;semantic=None
  cls,hit=classify(is_leader,semantic,qclasses)
  row={"security_id":s.security_id,"date":s.date,"v1_sector_leader":is_leader,"v1_primary_sector_id":s.primary_leader_sector,"v1_primary_sector_type":next((str(x) for x in sector.loc[sector.sector_id.eq(s.primary_leader_sector),"sector_type"]),None),"v2_primary_sector_id":None if not primary else primary["sector_id"],"v2_primary_sector_type":None if not primary else primary["sector_type"],"v2_primary_sector_semantic":semantic,"qualifying_sector_count":len(g),"economic_sector_count":counts["ECONOMIC_SECTOR"],"non_price_style_count":counts["NON_PRICE_STYLE"],"price_behavior_style_count":counts["PRICE_BEHAVIOR_STYLE"],"unknown_style_count":counts["UNKNOWN_STYLE"],"member_rs20_pct":np.nan if not primary else primary["member_rs20_pct"]}
  for c,v in zip(quality_cols,[np.nan]*4 if not primary else [primary[c] for c in quality_cols]):
   row[c]=v
   row[c+"__valid_count"]=0 if not primary else int(primary[c+"__valid_count"])
   row[c+"__valid_ratio"]=np.nan if not primary else float(primary[c+"__valid_ratio"])
  row["quality_evidence_sufficient"]=False if not primary else bool(primary["quality_evidence_sufficient"])
  for name,value in zip(("trend_quality_class","drawdown_quality_class","position_quality_class","persistence_quality_class"),qclasses):row[name]=value
  row.update({"quality_dimension_strong_support_count":strong,"quality_dimension_nonweak_support_count":nonweak,
              "independent_strong_support_count":strong,"independent_nonweak_support_count":nonweak,
              "v2_leader_class":cls,"v2_sector_leader_hit":hit,"shadow_ruleset_id":RULESET_ID,"shadow":True,"production_eligible":False,"primary_pattern":None if not primary else primary["primary_pattern"],"reacceleration":False if not primary else bool(primary["reacceleration"]),"sector_rs20_pct":np.nan if not primary else primary["sector_rs20_pct"]})
  rows.append(row)
 out=pd.DataFrame(rows);target=ROOT/f"reports/shadow/v2/{CUTOFF}/sector_leader";target.mkdir(parents=True,exist_ok=True);tmp=target/".SECTOR_LEADER_V2_SHADOW.parquet.tmp";pq.write_table(pa.Table.from_pandas(out,preserve_index=False),tmp,compression="zstd");os.replace(tmp,target/"SECTOR_LEADER_V2_SHADOW.parquet")
 hits=out[out.v1_sector_leader].copy();classes=("LEADER_CORE","LEADER_SUPPORTED","RETURN_LEADER_ONLY","STYLE_SELF_REINFORCED","DATA_INSUFFICIENT");class_counts={c:int(hits.v2_leader_class.eq(c).sum()) for c in classes};sem_counts={c:int(hits.v2_primary_sector_semantic.eq(c).sum()) for c in ("ECONOMIC_SECTOR","NON_PRICE_STYLE","PRICE_BEHAVIOR_STYLE","UNKNOWN_STYLE")}
 candidates=pd.read_csv(release/"candidates.csv",encoding="utf-8-sig");high=set(candidates.loc[candidates.research_priority.isin(["A+","A"]),"security_id"]);aa=hits[hits.security_id.isin(high)].v2_leader_class.value_counts().to_dict()
 sem_counts["UNDETERMINED"]=int(hits.v2_primary_sector_semantic.isna().sum());v1_primary=hits.v1_primary_sector_type.value_counts(dropna=False).to_dict()
 summary={"phase":"R3-04","cutoff":CUTOFF,"ruleset_id":RULESET_ID,"v1_sector_leader_count":len(hits),"class_counts":class_counts,"v1_primary_type_counts":v1_primary,"primary_semantic_counts":sem_counts,"v2_hit_count":int(hits.v2_sector_leader_hit.sum()),"a_plus_a_class_counts":aa,"distributions":{name:dist(frame) for name,frame in (("V1_SECTOR_LEADER",hits),*[(c,hits[hits.v2_leader_class.eq(c)]) for c in classes])}}
 write_json(target/"SECTOR_LEADER_V2_SUMMARY.json",summary);write_csv(target/"SECTOR_LEADER_V1_V2_DIFF.csv",hits)
 changes=hits.copy();changes["reason"]=[change_reason(v1,v2,row) for v1,v2,(_,row) in zip(changes.v1_primary_sector_id,changes.v2_primary_sector_id,changes.iterrows())];write_csv(target/"SECTOR_LEADER_PRIMARY_SECTOR_CHANGE.csv",changes[["security_id","v1_primary_sector_id","v1_primary_sector_type","v2_primary_sector_id","v2_primary_sector_type","v2_primary_sector_semantic","reason"]])
 pb=qual[qual.sector_semantic.eq("PRICE_BEHAVIOR_STYLE")].groupby("security_id").sector_name.apply(lambda x:"|".join(sorted(set(x)))).rename("qualifying_price_behavior_styles");style=hits[hits.price_behavior_style_count.gt(0)].merge(pb,on="security_id",how="left");style["economic_sector_also_qualifies"]=style.economic_sector_count.gt(0);write_csv(target/"SECTOR_LEADER_STYLE_SELF_REINFORCEMENT.csv",style[["security_id","qualifying_price_behavior_styles","economic_sector_also_qualifies","v1_primary_sector_id","v2_primary_sector_id","v2_leader_class"]])
 sample=pd.concat([hits[hits.v2_leader_class.eq(c)].head(20) for c in classes],ignore_index=True);write_csv(target/"SECTOR_LEADER_AUDIT_SAMPLE.csv",sample)
 assert pointer.read_bytes()==before and json.loads(pointer.read_text("utf8"))["latest_release"]["computation_identity"]["sha256"]==identity and hashes=={str(p.relative_to(ROOT)):sha(p) for p in v1paths}
 return {"rows":len(out),"class_counts":class_counts,"semantic_counts":sem_counts,"summary":summary,"target":str(target),"v1_identity":identity}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--date",default="latest");print(json.dumps(run(p.parse_args().date),ensure_ascii=False,indent=2,default=str))
