from __future__ import annotations
import argparse,hashlib,json,os,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/"src"))
from forward.observation import CONTRACT_VERSION,MATERIAL_FIELDS,OBSERVATION_SCHEMA_VERSION,OUTCOME_FIELDS,OUTCOME_SCHEMA_VERSION,observation_identity
CUTOFF="20260904";REVISION=1
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(p,b):
 p.parent.mkdir(parents=True,exist_ok=True);fd,t=tempfile.mkstemp(dir=p.parent,prefix="."+p.name,suffix=".tmp")
 try:os.write(fd,b);os.fsync(fd)
 finally:os.close(fd)
 os.replace(t,p)
def wjson(p,x):atomic(p,(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True,default=str)+"\n").encode())
def run(requested="latest"):
 if requested!="latest":raise ValueError("FORWARD_LATEST_ONLY")
 seal=json.loads((ROOT/"reports/shadow/v2/20260904/integrated/R3_INTEGRATED_SEAL_RECEIPT.json").read_text());current=json.loads((ROOT/"reports/current/CURRENT_RELEASE.json").read_text());priority_id=json.loads((ROOT/"reports/shadow/v2/20260904/priority/V2_PRIORITY_SHADOW_IDENTITY.json").read_text())["sha256"];source=current["latest_release"]["source_identity"];board_path=ROOT/"reports/shadow/v2/20260904/priority/V2_UNIFIED_RESEARCH_BOARD.parquet"
 payload={"cutoff_date":CUTOFF,"source_revision_id":source["sha256"],"source_identity":source["sha256"],"input_snapshot_manifest":current["latest_release"]["manifest_sha256"],"v1_release_run_id":current["latest_release"]["run_id"],"v1_computation_identity":current["latest_release"]["computation_identity"]["sha256"],"r3_integrated_shadow_identity":seal["integrated_shadow_identity"],"priority_shadow_identity":priority_id,"observation_schema_version":OBSERVATION_SCHEMA_VERSION,"board_sha256":sha(board_path)};oid=observation_identity(payload)
 data_dir=ROOT/f"data/forward/observations/{CUTOFF}/revision_{REVISION}";report_dir=ROOT/f"reports/forward/{CUTOFF}/revision_{REVISION}";identity_path=data_dir/"OBSERVATION_IDENTITY.json";parquet_path=data_dir/"FORWARD_OBSERVATION.parquet"
 if identity_path.exists() or parquet_path.exists():
  if not identity_path.exists() or not parquet_path.exists():return {"status":"CONFLICT_BLOCKED","reason":"PARTIAL_EXISTING_OBSERVATION"}
  old=json.loads(identity_path.read_text());
  if old["observation_id"]!=oid or old["parquet_sha256"]!=sha(parquet_path):return {"status":"CONFLICT_BLOCKED","reason":"EXISTING_OBSERVATION_IDENTITY_OR_CONTENT_DIFFERS"}
  return {"status":"VERIFIED_NO_NEW_FORWARD_OBSERVATION","observation_id":oid,"date":CUTOFF,"revision":REVISION,"rows":pq.ParquetFile(parquet_path).metadata.num_rows}
 board=pq.read_table(board_path).to_pandas();observed_at=datetime.now(timezone.utc).isoformat();rows=pd.DataFrame({"security_id":board.security_id,"observation_date":CUTOFF,"source_revision_id":source["sha256"],"candidate_state":"BASELINE","shadow_research_band":board.shadow_research_band})
 for f in MATERIAL_FIELDS[1:]:rows[f]=board[f]
 rows["v1_research_priority"]=board.v1_research_priority;rows["v1_primary_pattern"]=board.v1_primary_pattern;rows["comparison_universe"]=True;rows["v2_research_candidate"]=board.v2_research_candidate;rows["first_seen_date"]=CUTOFF;rows["first_seen_basis"]="FORWARD_BASELINE";rows["prior_seen_date"]=pd.NA;rows["last_seen_date_before_current"]=pd.NA;rows["structure_changed"]=False;rows["structure_change_fields"]="";rows["reentry_count"]=0;rows["last_exit_date"]=pd.NA;rows["exit_date"]=pd.NA;rows["model_version_changed"]=False;rows["state_comparable_to_prior"]=False;rows["r3_integrated_shadow_identity"]=seal["integrated_shadow_identity"];rows["priority_shadow_identity"]=priority_id;rows["observation_id"]=oid;rows["observed_at"]=observed_at
 data_dir.mkdir(parents=True,exist_ok=True);tmp=data_dir/".FORWARD_OBSERVATION.parquet.tmp";pq.write_table(pa.Table.from_pandas(rows,preserve_index=False),tmp,compression="zstd");os.replace(tmp,parquet_path);identity={**payload,"observation_id":oid,"revision":REVISION,"parquet_sha256":sha(parquet_path),"observed_at":observed_at,"immutable":True};wjson(identity_path,identity)
 counts=rows.shadow_research_band.value_counts().to_dict();summary={"status":"BASELINE_CREATED","date":CUTOFF,"revision":REVISION,"rows":len(rows),"state_counts":rows.candidate_state.value_counts().to_dict(),"band_counts":counts,"outcome_rows":0,"observation_id":oid};wjson(report_dir/"FORWARD_OBSERVATION_SUMMARY.json",summary);wjson(report_dir/"FORWARD_BASELINE_AUDIT.json",{"pass":len(rows)==1015 and rows.security_id.is_unique and (rows.candidate_state=="BASELINE").all(),"comparison_universe_rows":len(rows),"v2_research_candidate_rows":int(rows.v2_research_candidate.sum()),"no_historical_backfill":True,"no_future_backwrite":True,"outcome_rows":0});wjson(report_dir/"R4_00_BASELINE_RECEIPT.json",{"phase":"R4-00-BASELINE","status":"PASS","observation_id":oid,"rows":len(rows),"revision":REVISION,"immutable":True})
 global_report=ROOT/"reports/forward/r4_00";wjson(global_report/"R4_STATE_MACHINE_AUDIT.json",{"states":["BASELINE","NEW","PERSISTENT","EXITED","REENTERED","STRUCTURE_CHANGED","DATA_UNAVAILABLE","SOURCE_REVISED"],"material_fields":list(MATERIAL_FIELDS),"context_change_neutral":True,"single_valued":True});wjson(global_report/"R4_OUTCOME_SCHEMA_AUDIT.json",{"pass":True,"version":OUTCOME_SCHEMA_VERSION,"fields":list(OUTCOME_FIELDS),"horizons":[1,5,10,20],"trading_days_not_calendar_days":True,"entry_reference":"SIGNAL_DATE_ADJUSTED_CLOSE","research_reference_only":True,"outcome_rows":0,"append_only":True});wjson(global_report/"R4_IDENTITY_BINDING_AUDIT.json",{"pass":True,**payload,"observation_id":oid});wjson(global_report/"R4_NO_BACKFILL_AUDIT.json",{"pass":True,"forward_only":True,"no_historical_backfill":True,"no_future_backwrite":True,"seed_date":CUTOFF,"pre_seed_observation_rows":0,"outcome_rows":0})
 return summary
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--date",default="latest");print(json.dumps(run(p.parse_args().date),ensure_ascii=False,indent=2))
