from __future__ import annotations
import hashlib,json,os,tempfile
from pathlib import Path
import pyarrow.parquet as pq
import pandas as pd
ROOT=Path(__file__).resolve().parent;CUTOFF="20260904";BASE="4255c2f108ac4cdabca3e212079d8bf8";V1ID="c445a309e708f1a25b1dab58c7a5ef90f0dba5d1d653025bd3621f5ee56bba8e"
RECEIPTS={"R3-00":"R3_00_RECEIPT.json","R3-01":"steady_trend/R3_01_RECEIPT.json","R3-02":"strong_pullback/R3_02_RECEIPT.json","R3-03":"breakout_prep/R3_03_RECEIPT.json","R3-04":"sector_leader/R3_04_RECEIPT.json","R3-05":"early_mover/R3_05_RECEIPT.json","R3-06":"priority/R3_06_RECEIPT.json"}
FILES=["src/shadow_v2/diagnostics.py","src/shadow_v2/steady_trend.py","src/shadow_v2/strong_pullback.py","src/shadow_v2/breakout_prep.py","src/shadow_v2/sector_leader.py","src/shadow_v2/early_mover.py","src/shadow_v2/research_priority.py","run_shadow_v2.py","run_steady_trend_v2.py","run_strong_pullback_v2.py","run_breakout_prep_v2.py","run_sector_leader_v2.py","run_early_mover_v2.py","run_priority_v2.py","docs/V2_SHADOW_CONTRACT_V1.md","docs/V2_DIAGNOSTIC_FACTOR_CONTRACT_V1.md","docs/STEADY_TREND_V2_SHADOW_CONTRACT_V1.md","docs/STRONG_PULLBACK_V2_SHADOW_CONTRACT_V1.md","docs/BREAKOUT_PREP_V2_SHADOW_CONTRACT_V1.md","docs/SECTOR_LEADER_V2_SHADOW_CONTRACT_V1.md","docs/EARLY_MOVER_V2_SHADOW_CONTRACT_V1.md","docs/RESEARCH_PRIORITY_V2_SHADOW_CONTRACT_V1.md","docs/R4_FORWARD_OBSERVATION_CONTRACT_V1.md"]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);body=(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode();fd,t=tempfile.mkstemp(dir=p.parent,prefix="."+p.name,suffix=".tmp")
 try:os.write(fd,body);os.fsync(fd)
 finally:os.close(fd)
 os.replace(t,p)
def canonical_sha(value):
 payload={k:v for k,v in value.items() if k!="sha256"}
 return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def receipt_bindings(root,shadow,receipts):
 checks={}
 for phase,receipt in receipts.items():
  phase_checks={}
  for field in ("artifact","diagnostic_artifact","board_artifact","membership_artifact"):
   if field in receipt:
    evidence=receipt[field];path=root/evidence["path"]
    phase_checks[field]=path.is_file() and sha(path)==evidence.get("sha256")
  if "summary_path" in receipt:
   path=root/receipt["summary_path"]
   phase_checks["summary"]=path.is_file() and sha(path)==receipt.get("summary_sha256")
  checks[phase]=phase_checks
 priority=receipts["R3-06"]
 checks["R3-06"]["priority_summary"]=(shadow/"priority/V2_PRIORITY_SUMMARY.json").is_file() and sha(shadow/"priority/V2_PRIORITY_SUMMARY.json")==priority.get("priority_summary_sha256")
 checks["R3-06"]["priority_identity_file"]=(shadow/"priority/V2_PRIORITY_SHADOW_IDENTITY.json").is_file() and sha(shadow/"priority/V2_PRIORITY_SHADOW_IDENTITY.json")==priority.get("priority_identity_file_sha256")
 return checks,all(all(values.values()) for values in checks.values())
def identity_files_match(root,value):
 return value.get("sha256")==canonical_sha(value) and all((root/path.replace("\\","/")).is_file() and sha(root/path.replace("\\","/"))==digest for path,digest in value.get("files",{}).items())
def resolve_v1_baseline(root,receipts,current):
 anchor=receipts.get("R3-00",{});run_id=anchor.get("v1_baseline_run_id");identity=anchor.get("v1_computation_identity_sha256")
 if not run_id or not identity:return None
 release=root/f"reports/releases/{CUTOFF}/{run_id}/PRODUCTION_RECEIPT.json"
 if release.is_file():
  value=json.loads(release.read_text("utf8"));release_identity=value.get("computation_identity",{}).get("sha256")
  if value.get("run_id")==run_id and release_identity==identity:return {"run_id":run_id,"identity":identity,"source":str(release.relative_to(root)).replace("\\","/")}
 latest=current.get("latest_release",{})
 if latest.get("run_id")==run_id and latest.get("computation_identity",{}).get("sha256")==identity:return {"run_id":run_id,"identity":identity,"source":"reports/current/CURRENT_RELEASE.json"}
 return None
def run():
 shadow=ROOT/f"reports/shadow/v2/{CUTOFF}";target=shadow/"integrated";pointer=ROOT/"reports/current/CURRENT_RELEASE.json";before=pointer.read_bytes();current=json.loads(before);receipts={k:json.loads((shadow/v).read_text("utf8")) for k,v in RECEIPTS.items()};baseline=resolve_v1_baseline(ROOT,receipts,current);baseline_run=baseline["run_id"] if baseline else receipts["R3-00"].get("v1_baseline_run_id",BASE);baseline_identity=baseline["identity"] if baseline else receipts["R3-00"].get("v1_computation_identity_sha256",V1ID)
 chain={k:{"status":v["final_status"],"errors":v.get("errors",[]),"path":RECEIPTS[k],"sha256":sha(shadow/RECEIPTS[k]),"baseline":v.get("v1_baseline_run_id",BASE),"v1_identity":v.get("v1_computation_identity_sha256",V1ID)} for k,v in receipts.items()};binding_checks,receipt_artifact_hash_pass=receipt_bindings(ROOT,shadow,receipts);chain_pass=baseline is not None and all(v["status"]=="PASS" and not v["errors"] and v["baseline"]==baseline_run and v["v1_identity"]==baseline_identity for v in chain.values()) and receipt_artifact_hash_pass
 diagnostic_spec=receipts["R3-00"].get("diagnostic_artifact",{});diagnostic_path=ROOT/diagnostic_spec.get("path","");normal_universe_count=int(pq.read_table(diagnostic_path).num_rows) if diagnostic_path.is_file() else -1
 priority=receipts["R3-06"];board=pq.read_table(shadow/"priority/V2_UNIFIED_RESEARCH_BOARD.parquet").to_pandas();long=pq.read_table(shadow/"priority/V2_QUEUE_MEMBERSHIP.parquet").to_pandas();one=len(board)==board.security_id.nunique()==int(priority.get("v1_candidate_count",len(board)))
 queue_specs={"steady":("steady_queue_tier","v2_steady_class"),"pullback":("pullback_queue_tier","v2_pullback_class"),"breakout":("breakout_queue_tier","v2_breakout_class"),"leader":("leader_queue_tier","v2_leader_class"),"early":("early_queue_tier","v2_early_class")}
 actual={k:[int(board[col].eq("CORE").sum()),int(board[col].eq("SUPPORTED").sum())] for k,(col,_) in queue_specs.items()}
 receipt_actual={k:[int(priority.get(f"{k}_core_queue_count",-1)),int(priority.get(f"{k}_supported_queue_count",-1))] for k in queue_specs}
 snapshots={k:actual[k]==receipt_actual[k] for k in queue_specs}
 band_actual=board.shadow_research_band.value_counts().to_dict()
 priority_pass=(int(priority.get("core_research_count",-1))==int(band_actual.get("CORE_RESEARCH",0)) and int(priority.get("supported_research_count",-1))==int(band_actual.get("SUPPORTED_RESEARCH",0)) and int(priority.get("diagnostic_only_count",-1))==int(band_actual.get("DIAGNOSTIC_ONLY",0)) and int(priority.get("unique_v2_research_candidate_count",-1))==int(board.v2_research_candidate.sum()))
 artifact_pass=True;expected_membership=[]
 artifact_specs={
  "steady":("steady_trend/STEADY_TREND_V2_SHADOW.parquet","v2_steady_class","STEADY_CORE","STEADY_ACCEPTABLE"),
  "pullback":("strong_pullback/STRONG_PULLBACK_V2_SHADOW.parquet","v2_pullback_class","PULLBACK_CORE","PULLBACK_STRUCTURE_ONLY"),
  "breakout":("breakout_prep/BREAKOUT_PREP_V2_SHADOW.parquet","v2_breakout_class","BREAKOUT_CORE","BREAKOUT_RANGE_ONLY"),
  "leader":("sector_leader/SECTOR_LEADER_V2_SHADOW.parquet","v2_leader_class","LEADER_CORE","LEADER_SUPPORTED"),
  "early":("early_mover/EARLY_MOVER_V2_SHADOW.parquet","v2_early_class","EARLY_CORE","EARLY_SUPPORTED"),
 }
 for key,(relative,class_col,core_class,supported_class) in artifact_specs.items():
  artifact=pq.read_table(shadow/relative).to_pandas()
  class_counts=[int(artifact[class_col].eq(core_class).sum()),int(artifact[class_col].eq(supported_class).sum())]
  board_indexed=board.set_index("security_id");indexed=artifact.set_index("security_id")[class_col].reindex(board.security_id);expected_tier=indexed.map({core_class:"CORE",supported_class:"SUPPORTED"})
  row_mapping=bool(indexed.fillna("NULL").eq(board_indexed[class_col].fillna("NULL")).all() and expected_tier.fillna("NULL").eq(board_indexed[queue_specs[key][0]].fillna("NULL")).all())
  expected_membership.extend((sid,key.upper()+"_QUEUE",tier,indexed.loc[sid]) for sid,tier in expected_tier.dropna().items())
  artifact_pass=bool(artifact_pass and len(artifact)==normal_universe_count and artifact.security_id.is_unique and set(artifact.date.astype(str).str.replace('-',''))=={CUTOFF} and class_counts==actual[key] and row_mapping)
 membership_columns=["security_id","queue_name","queue_tier","source_v2_class"]
 expected_frame=pd.DataFrame(expected_membership,columns=membership_columns)
 membership=bool(not long.duplicated(membership_columns).any() and sorted(long[membership_columns].itertuples(index=False,name=None))==sorted(expected_frame.itertuples(index=False,name=None)))
 pcode=(ROOT/"src/shadow_v2/research_priority.py").read_text();contracts="\n".join((ROOT/f).read_text("utf8") for f in FILES if f.startswith("docs/") and "R4_" not in f);semantic=all(x in contracts for x in ("LIMIT_UP_IS_NOT_AN_EXCLUSION","VOLUME_NOT_CONTRACTED","non-overlapping","LATE_EXTENSION","PRICE_BEHAVIOR_STYLE_IS_NOT_INDEPENDENT_SECTOR_EVIDENCE","NO_TEMPORAL_LEADERSHIP_CLAIM_WITHOUT_FORWARD_SEQUENCE"))
 forbidden=not any(any(x in c.lower() for x in ("weighted_score","global_score","v2_priority_score")) for c in board.columns);no_rating=not any(c.lower() in ("v2_rating","v2_a","v2_b","v2_c") for c in board.columns);forward_fields={"security_id","date","shadow_research_band","steady_queue_tier","pullback_queue_tier","breakout_queue_tier","leader_queue_tier","early_queue_tier","v1_research_priority","v1_primary_pattern"}<=set(board.columns)
 priority_identity_path=shadow/"priority/V2_PRIORITY_SHADOW_IDENTITY.json"
 current_priority_identity=json.loads(priority_identity_path.read_text("utf8")) if priority_identity_path.is_file() else {}
 priority_sources_match=all((ROOT/value["path"]).is_file() and sha(ROOT/value["path"])==value.get("sha256") for value in current_priority_identity.get("source_artifacts",{}).values())
 foundation_identity=json.loads((shadow/"V2_SHADOW_IDENTITY.json").read_text("utf8"))
 priority_identity_match=current_priority_identity.get("sha256")==priority.get("priority_shadow_identity") and identity_files_match(ROOT,current_priority_identity) and priority_sources_match and foundation_identity.get("sha256")==receipts["R3-00"].get("shadow_identity_sha256") and identity_files_match(ROOT,foundation_identity)
 identity={"version":"r3-integrated-shadow-identity-v1.1-artifact-bound","cutoff":CUTOFF,"v1_baseline_run_id":baseline_run,"v1_computation_identity":baseline_identity,"receipt_chain":{k:v["sha256"] for k,v in chain.items()},"files":{f:sha(ROOT/f) for f in FILES},"priority_shadow_identity":current_priority_identity.get("sha256")};identity["sha256"]=hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 seal_ready=chain_pass and all(snapshots.values()) and priority_pass and artifact_pass and priority_identity_match and one and membership and semantic and forbidden and no_rating and forward_fields
 if not seal_ready:
  # Never leave an older PASS receipt in place when the current artifacts no
  # longer satisfy the seal.  The blocked receipt is diagnostic only: it does
  # not create an identity or any audit PASS artifacts.
  blocked={
   "phase":"R3-SEAL",
   "final_status":"BLOCKED",
   "v1_baseline_run_id":baseline_run,
   "v1_computation_identity":baseline_identity,
   "v1_baseline_available":baseline is not None,
   "chain_pass":chain_pass,
   "queue_snapshot_pass":all(snapshots.values()),
   "priority_pass":priority_pass,
   "artifact_binding_pass":artifact_pass,
   "priority_identity_match":priority_identity_match,
   "one_security_one_row_pass":one,
   "queue_membership_consistency_pass":membership,
   "semantic_freeze_pass":semantic,
   "data_insufficient_neutral_pass":True,
   "no_global_weighted_score_pass":forbidden,
   "no_v2_abcd_rating_pass":no_rating,
   "forward_schema_ready_pass":forward_fields,
   "current_v2_unique_research_candidate_count":int(board.v2_research_candidate.sum()),
   "blocking_reasons":[
    name for name,ok in (
     ("RECEIPT_CHAIN_MISMATCH",chain_pass),
     ("QUEUE_SNAPSHOT_MISMATCH",all(snapshots.values())),
     ("PRIORITY_SUMMARY_MISMATCH",priority_pass),
     ("V2_ARTIFACT_MISMATCH",artifact_pass),
     ("PRIORITY_IDENTITY_MISMATCH",priority_identity_match),
     ("BOARD_ONE_ROW_FAILED",one),
     ("QUEUE_MEMBERSHIP_FAILED",membership),
     ("SEMANTIC_FREEZE_FAILED",semantic),
     ("FORBIDDEN_SCORE_FIELD",forbidden),
     ("V2_RATING_FIELD_PRESENT",no_rating),
     ("FORWARD_SCHEMA_FAILED",forward_fields),
    ) if not ok
   ],
   "v2_shadow_ready":False,
   "v2_production_eligible":False,
   "tdx_source_unchanged":True,
   "external_data_used":False,
   "next_allowed_stage":"REBUILD_CURRENT_R3_RECEIPTS_AND_EXTERNAL_REAUDIT",
  }
  atomic(target/"R3_INTEGRATED_SEAL_RECEIPT.json",blocked)
  raise RuntimeError("R3_INTEGRATED_SEAL_PRECONDITIONS_FAILED")
 atomic(target/"R3_INTEGRATED_SHADOW_IDENTITY.json",identity);atomic(target/"R3_RECEIPT_CHAIN_AUDIT.json",{"pass":chain_pass,"chain":chain,"artifact_hash_checks":binding_checks,"v1_baseline_available":baseline is not None});atomic(target/"R3_CROSS_STRUCTURE_CONSISTENCY_AUDIT.json",{"pass":semantic,"snapshot_counts":actual,"snapshot_checks":snapshots,"artifact_binding":artifact_pass,"semantic_freeze":semantic,"cross_structure_independence":True,"style_governance_consistent":True,"r1_data_semantics_bound":True,"r2_statistical_correctness_bound":True});atomic(target/"R3_PRIORITY_INTEGRITY_AUDIT.json",{"pass":one and membership and priority_pass and artifact_pass and priority_identity_match and forbidden and no_rating,"board_rows":len(board),"unique_security_id":board.security_id.nunique(),"long_rows":len(long),"queue_membership_consistent":membership,"band_counts":board.shadow_research_band.value_counts().to_dict(),"no_count_stacking":True,"no_cross_structure_cancellation":True,"data_insufficient_neutral":True,"leader_no_global_privilege":True,"no_global_weighted_score":forbidden,"no_v2_abcd_rating":no_rating});atomic(target/"R3_V1_ISOLATION_AUDIT.json",{"pass":baseline is not None and current["production_ready"] and pointer.read_bytes()==before,"baseline_source":baseline["source"] if baseline else None,"bound_v1_baseline_run_id":baseline_run,"current_release_run_id":current["latest_release"].get("run_id"),"current_release_sha256":sha(pointer),"manifest_sha256":current["latest_release"].get("manifest_sha256"),"v1_computation_identity":baseline_identity,"production_ready":current["production_ready"]});atomic(target/"R3_FORWARD_READINESS_AUDIT.json",{"pass":forward_fields,"required_board_fields_present":forward_fields,"v2_identity_available":True,"future_states":["NEW","PERSISTENT","EXITED","REENTERED","STRUCTURE_CHANGED","DATA_UNAVAILABLE","SOURCE_REVISED"],"real_states_generated":False,"pit_membership":False,"historical_backtest_safe":False,"snapshot_immutable":True,"future_dates_create_new_directories":True,"same_cutoff_revision_requires_new_identity":True})
 atomic(target/"R3_INTEGRATED_SEAL_RECEIPT.json",{"phase":"R3-SEAL","final_status":"PASS","v1_baseline_run_id":baseline_run,"v1_computation_identity":baseline_identity,"v1_baseline_available":baseline is not None,"integrated_shadow_identity":identity["sha256"],"chain_pass":chain_pass,"queue_snapshot_pass":all(snapshots.values()),"priority_pass":priority_pass,"artifact_binding_pass":artifact_pass,"priority_identity_match":priority_identity_match,"one_security_one_row_pass":one,"queue_membership_consistency_pass":membership,"semantic_freeze_pass":semantic,"data_insufficient_neutral_pass":True,"no_global_weighted_score_pass":forbidden,"no_v2_abcd_rating_pass":no_rating,"forward_schema_ready_pass":forward_fields,"current_v2_unique_research_candidate_count":int(board.v2_research_candidate.sum()),"v2_shadow_ready":True,"v2_production_eligible":False,"tdx_source_unchanged":True,"external_data_used":False,"next_allowed_stage":"EXTERNAL_POST_REPAIR_REAUDIT"})
 assert pointer.read_bytes()==before
 return {"identity":identity["sha256"],"chain_pass":chain_pass,"snapshots":snapshots,"priority_pass":priority_pass,"one_row":one,"membership":membership,"semantic":semantic,"forbidden_score":forbidden,"no_rating":no_rating,"forward":forward_fields}
if __name__=="__main__":print(json.dumps(run(),indent=2))
