from __future__ import annotations

import argparse, hashlib, json, os, sys, tempfile
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/"src"))
from shadow_v2.breakout_prep import RULESET_ID,classify,range_status,vol_status
CUTOFF="20260904";BASE_RUN="4255c2f108ac4cdabca3e212079d8bf8"

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def atomic(path,body):
 path.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=path.parent,prefix="."+path.name,suffix=".tmp")
 try: os.write(fd,body);os.fsync(fd)
 finally: os.close(fd)
 os.replace(tmp,path)
def write_json(path,value): atomic(path,(json.dumps(value,ensure_ascii=False,indent=2,default=str)+"\n").encode())
def write_csv(path,frame): atomic(path,frame.to_csv(index=False).encode("utf-8-sig"))
def distribution(frame):
 result={}
 for column in ("range_contraction_ratio","realized_vol_contraction_ratio","DIST_HIGH20","TREND_R2_20","AMOUNT_RATIO_5_20"):
  series=pd.to_numeric(frame[column],errors="coerce");q=series.quantile([.10,.25,.50,.75,.90])
  result[column]={"valid_count":int(series.notna().sum()),"null_count":int(series.isna().sum()),**{name:(None if pd.isna(value) else float(value)) for name,value in zip(("p10","p25","median","p75","p90"),q)}}
 return result
def run(requested="latest"):
 if requested!="latest": raise ValueError("SHADOW_LATEST_ONLY")
 pointer=ROOT/"reports/current/CURRENT_RELEASE.json";pointer_before=pointer.read_bytes();current=json.loads(pointer_before);identity=current["latest_release"]["computation_identity"]["sha256"]
 release=ROOT/f"reports/releases/{CUTOFF}/{BASE_RUN}";v1paths=[release/name for name in ("stocks.csv","candidates.csv","manifest.json")]+[pointer];hashes={str(p.relative_to(ROOT)):sha(p) for p in v1paths}
 diagnostic=pq.read_table(ROOT/f"reports/shadow/v2/{CUTOFF}/V2_DIAGNOSTIC_FACTORS.parquet").to_pandas();stocks=pd.read_csv(release/"stocks.csv",encoding="utf-8-sig")
 columns=["security_id","date","breakout_prep","warning_codes","DIST_HIGH20","POS20","POS60","TREND_R2_20","RS20","AMOUNT_RATIO_5_20"]
 base=stocks[columns].copy();base["v1_breakout_prep"]=base.pop("breakout_prep").astype(str).str.lower().eq("true");base["v1_late_extension_warning"]=base.pop("warning_codes").fillna("").str.contains("LATE_EXTENSION_WARNING",regex=False)
 dc=["security_id","recent_range_10","prior_range_10","range_contraction_ratio","recent_realized_vol_10","prior_realized_vol_10","realized_vol_contraction_ratio"]
 out=base.merge(diagnostic[dc],on="security_id",how="left",validate="one_to_one")
 out["range_status"]=[range_status(a,b,r) for a,b,r in zip(out.recent_range_10,out.prior_range_10,out.range_contraction_ratio)]
 out["vol_status"]=[vol_status(a,b,r) for a,b,r in zip(out.recent_realized_vol_10,out.prior_realized_vol_10,out.realized_vol_contraction_ratio)]
 classified=[classify(v,r,vv) for v,r,vv in zip(out.v1_breakout_prep,out.range_status,out.vol_status)];out["v2_breakout_class"]=[x[0] for x in classified];out["v2_breakout_structure_hit"]=[x[1] for x in classified]
 out["shadow_ruleset_id"]=RULESET_ID;out["shadow"]=True;out["production_eligible"]=False;out=out.sort_values("security_id").reset_index(drop=True)
 target=ROOT/f"reports/shadow/v2/{CUTOFF}/breakout_prep";target.mkdir(parents=True,exist_ok=True);tmp=target/".BREAKOUT_PREP_V2_SHADOW.parquet.tmp";pq.write_table(pa.Table.from_pandas(out,preserve_index=False),tmp,compression="zstd");os.replace(tmp,target/"BREAKOUT_PREP_V2_SHADOW.parquet")
 hits=out[out.v1_breakout_prep].copy();classes=("BREAKOUT_CORE","BREAKOUT_RANGE_ONLY","BREAKOUT_VOL_ONLY","NEAR_HIGH_NO_CONTRACTION","DATA_INSUFFICIENT");counts={name:int(hits.v2_breakout_class.eq(name).sum()) for name in classes}
 summary={"phase":"R3-03","cutoff":CUTOFF,"ruleset_id":RULESET_ID,"v1_breakout_prep_count":len(hits),"class_counts":counts,"structure_hit_count":int(hits.v2_breakout_structure_hit.sum()),"late_extension_warning_count":int(hits.v1_late_extension_warning.sum()),"distributions":{name:distribution(frame) for name,frame in (("NORMAL_UNIVERSE",out),("V1_BREAKOUT_PREP",hits),("BREAKOUT_CORE",hits[hits.v2_breakout_class.eq("BREAKOUT_CORE")]),("BREAKOUT_RANGE_ONLY",hits[hits.v2_breakout_class.eq("BREAKOUT_RANGE_ONLY")]),("NEAR_HIGH_NO_CONTRACTION",hits[hits.v2_breakout_class.eq("NEAR_HIGH_NO_CONTRACTION")]))}}
 write_json(target/"BREAKOUT_PREP_V2_SUMMARY.json",summary)
 diff=["security_id","v1_breakout_prep","v1_late_extension_warning","range_status","vol_status","v2_breakout_class","v2_breakout_structure_hit","range_contraction_ratio","realized_vol_contraction_ratio","DIST_HIGH20","POS20","POS60","TREND_R2_20","RS20","AMOUNT_RATIO_5_20"];write_csv(target/"BREAKOUT_PREP_V1_V2_DIFF.csv",hits[diff])
 sample=pd.concat([hits[hits.v2_breakout_class.eq(name)].head(20) for name in classes],ignore_index=True);write_csv(target/"BREAKOUT_PREP_AUDIT_SAMPLE.csv",sample)
 assert pointer.read_bytes()==pointer_before and json.loads(pointer.read_text("utf8"))["latest_release"]["computation_identity"]["sha256"]==identity
 assert hashes=={str(p.relative_to(ROOT)):sha(p) for p in v1paths}
 return {"rows":len(out),"counts":counts,"summary":summary,"target":str(target),"v1_identity":identity,"v1_hashes":hashes}
if __name__=="__main__":
 parser=argparse.ArgumentParser();parser.add_argument("--date",default="latest");print(json.dumps(run(parser.parse_args().date),ensure_ascii=False,indent=2,default=str))
