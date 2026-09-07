from __future__ import annotations
import argparse,hashlib,json,os,sys,tempfile
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/"src"))
from phase4_runner import memberships
from shadow_v2.early_mover import RULESET_ID,classify,position_support,sector_context,trend_support
from common.paths import resolve_tdx_root
CUTOFF="20260904";BASE_RUN="4255c2f108ac4cdabca3e212079d8bf8";TDX_ROOT=resolve_tdx_root(ROOT)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(p,b):
 p.parent.mkdir(parents=True,exist_ok=True);fd,t=tempfile.mkstemp(dir=p.parent,prefix="."+p.name,suffix=".tmp")
 try:os.write(fd,b);os.fsync(fd)
 finally:os.close(fd)
 os.replace(t,p)
def wjson(p,x):atomic(p,(json.dumps(x,ensure_ascii=False,indent=2,default=str)+"\n").encode())
def wcsv(p,x):atomic(p,x.to_csv(index=False).encode("utf-8-sig"))
def distribution(f):
 out={}
 for c in ("RET5","RS5","stock_rs5_pct","TREND_R2_20","UP_DAY_RATIO20","RETURN_CONCENTRATION_20","POS60","AMOUNT_RATIO_5_20"):
  s=pd.to_numeric(f[c],errors="coerce");q=s.quantile([.1,.25,.5,.75,.9]);out[c]={"valid_count":int(s.notna().sum()),"null_count":int(s.isna().sum()),**{n:(None if pd.isna(v) else float(v)) for n,v in zip(("p10","p25","median","p75","p90"),q)}}
 return out
def state(g,typ):
 x=g[g.sector_type.eq(typ)]
 if x.empty:return "UNMAPPED"
 if x.reacceleration.any():return "REACCELERATION"
 if x.current_strength.any():return "CURRENT_STRENGTH"
 if x.stabilization.any():return "STABILIZATION"
 return "NO_SIGNAL"
def run(requested="latest"):
 if requested!="latest":raise ValueError("SHADOW_LATEST_ONLY")
 pointer=ROOT/"reports/current/CURRENT_RELEASE.json";before=pointer.read_bytes();cur=json.loads(before);identity=cur["latest_release"]["computation_identity"]["sha256"]
 release=ROOT/f"reports/releases/{CUTOFF}/{BASE_RUN}";v1p=[release/x for x in ("stocks.csv","candidates.csv","manifest.json")]+[pointer];hashes={str(p.relative_to(ROOT)):sha(p) for p in v1p}
 stock=pd.read_csv(release/"stocks.csv",encoding="utf-8-sig");diag=pq.read_table(ROOT/f"reports/shadow/v2/{CUTOFF}/V2_DIAGNOSTIC_FACTORS.parquet").to_pandas()
 cols=["security_id","date","early_mover","RET5","RS5","stock_rs5_pct","TREND_R2_20","POS60","AMOUNT_RATIO_5_20","has_current_strength_sector","has_reacceleration_sector"]
 out=stock[cols].copy();out["v1_early_mover"]=out.pop("early_mover").astype(str).str.lower().eq("true");out=out.merge(diag[["security_id","UP_DAY_RATIO20","RETURN_CONCENTRATION_20"]],on="security_id",how="left",validate="one_to_one")
 steady=pq.read_table(ROOT/f"reports/shadow/v2/{CUTOFF}/steady_trend/STEADY_TREND_V2_SHADOW.parquet",columns=["security_id","continuity_class","pulse_class","v2_steady_class"]).to_pandas().rename(columns={"v2_steady_class":"steady_v2_class"});out=out.merge(steady,on="security_id",how="left",validate="one_to_one")
 sector=pd.read_csv(release/"sectors.csv",encoding="utf-8-sig");sector=sector[sector.sector_valid.astype(str).str.lower().eq("true") & sector.sector_role.ne("EXCLUDE_FROM_THEME_RANK")]
 style=pd.read_csv(ROOT/f"reports/shadow/v2/{CUTOFF}/V2_STYLE_CLASSIFICATION.csv",encoding="utf-8-sig")[["sector_id","STYLE_SEMANTIC_CLASS"]];sector=sector.merge(style,on="sector_id",how="left")
 rel=memberships(TDX_ROOT)[["security_id","sector_id"]].merge(sector[["sector_id","sector_name","sector_type","current_strength","stabilization","reacceleration","STYLE_SEMANTIC_CLASS"]],on="sector_id",how="inner");groups={sid:g for sid,g in rel.groupby("security_id")};empty=rel.iloc[0:0]
 contexts=[]
 for sid in out.security_id:
  g=groups.get(sid,empty);econ=g[g.sector_type.isin(["INDUSTRY","THEME"])];pb=g[g.STYLE_SEMANTIC_CLASS.eq("PRICE_BEHAVIOR")];unknown=g[g.sector_type.eq("STYLE")&g.STYLE_SEMANTIC_CLASS.eq("UNKNOWN")]
  ctx=sector_context(not econ.empty,bool(econ.stabilization.any()),not pb.empty,not unknown.empty)
  contexts.append({"security_id":sid,"industry_context":state(g,"INDUSTRY"),"theme_context":state(g,"THEME"),"style_context":state(g,"STYLE"),"price_behavior_style_context":"PRESENT" if not pb.empty else "NONE","stabilization_present":bool(g.stabilization.any()),"current_strength_present":bool(g.current_strength.any()),"reacceleration_present":bool(g.reacceleration.any()),"v2_sector_context_class":ctx})
 out=out.merge(pd.DataFrame(contexts),on="security_id",validate="one_to_one");out["trend_support"]=[trend_support(x) for x in out.TREND_R2_20];out["position_support"]=[position_support(x) for x in out.POS60]
 z=[classify(v,c,t,u,p,o) for v,c,t,u,p,o in zip(out.v1_early_mover,out.v2_sector_context_class,out.trend_support,out.continuity_class,out.pulse_class,out.position_support)];out["v2_early_class"]=[x[0] for x in z];out["v2_early_relative_hit"]=[x[1] for x in z];out["early_signal_date"]=out.date
 for path,col in (("strong_pullback/STRONG_PULLBACK_V2_SHADOW.parquet","v2_pullback_class"),("breakout_prep/BREAKOUT_PREP_V2_SHADOW.parquet","v2_breakout_class"),("sector_leader/SECTOR_LEADER_V2_SHADOW.parquet","v2_leader_class")):
  x=pq.read_table(ROOT/f"reports/shadow/v2/{CUTOFF}"/Path(path),columns=["security_id",col]).to_pandas();out=out.merge(x,on="security_id",how="left",validate="one_to_one")
 out["shadow_ruleset_id"]=RULESET_ID;out["shadow"]=True;out["production_eligible"]=False;out=out.sort_values("security_id").reset_index(drop=True)
 target=ROOT/f"reports/shadow/v2/{CUTOFF}/early_mover";target.mkdir(parents=True,exist_ok=True);tmp=target/".EARLY_MOVER_V2_SHADOW.parquet.tmp";pq.write_table(pa.Table.from_pandas(out,preserve_index=False),tmp,compression="zstd");os.replace(tmp,target/"EARLY_MOVER_V2_SHADOW.parquet")
 hits=out[out.v1_early_mover].copy();classes=("EARLY_CORE","EARLY_SUPPORTED","SHORT_TERM_PULSE","SECTOR_ALREADY_STABILIZING","CONTEXT_UNCERTAIN","DATA_INSUFFICIENT");counts={c:int(hits.v2_early_class.eq(c).sum()) for c in classes}
 summary={"phase":"R3-05","cutoff":CUTOFF,"display_name":"EARLY_RELATIVE_MOVER_V2","ruleset_id":RULESET_ID,"v1_early_mover_count":len(hits),"class_counts":counts,"v2_hit_count":int(hits.v2_early_relative_hit.sum()),"sector_context_counts":hits.v2_sector_context_class.value_counts().to_dict(),"distributions":{n:distribution(f) for n,f in (("V1_EARLY_MOVER",hits),*[(c,hits[hits.v2_early_class.eq(c)]) for c in classes if c!="DATA_INSUFFICIENT"])}}
 wjson(target/"EARLY_MOVER_V2_SUMMARY.json",summary);wcsv(target/"EARLY_MOVER_V1_V2_DIFF.csv",hits);audit_cols=["security_id","industry_context","theme_context","style_context","price_behavior_style_context","stabilization_present","current_strength_present","reacceleration_present","v2_sector_context_class","v2_early_class"];wcsv(target/"EARLY_MOVER_SECTOR_CONTEXT_AUDIT.csv",hits[audit_cols]);sample=pd.concat([hits[hits.v2_early_class.eq(c)].head(20) for c in classes],ignore_index=True);wcsv(target/"EARLY_MOVER_AUDIT_SAMPLE.csv",sample)
 assert pointer.read_bytes()==before and json.loads(pointer.read_text("utf8"))["latest_release"]["computation_identity"]["sha256"]==identity and hashes=={str(p.relative_to(ROOT)):sha(p) for p in v1p}
 return {"rows":len(out),"counts":counts,"summary":summary,"target":str(target),"v1_identity":identity}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--date",default="latest");print(json.dumps(run(p.parse_args().date),ensure_ascii=False,indent=2,default=str))
