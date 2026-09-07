from __future__ import annotations
import argparse,hashlib,json,os,sys,tempfile
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/"src"))
from shadow_v2.research_priority import DISPLAY_ORDER_ONLY,MAPPINGS,RULESET_ID,queue_tier,research_band
CUTOFF="20260904";BASE_RUN="4255c2f108ac4cdabca3e212079d8bf8"
SOURCES={"STEADY_QUEUE":("steady_trend/STEADY_TREND_V2_SHADOW.parquet","v2_steady_class"),"PULLBACK_QUEUE":("strong_pullback/STRONG_PULLBACK_V2_SHADOW.parquet","v2_pullback_class"),"BREAKOUT_QUEUE":("breakout_prep/BREAKOUT_PREP_V2_SHADOW.parquet","v2_breakout_class"),"LEADER_QUEUE":("sector_leader/SECTOR_LEADER_V2_SHADOW.parquet","v2_leader_class"),"EARLY_QUEUE":("early_mover/EARLY_MOVER_V2_SHADOW.parquet","v2_early_class")}
RECEIPTS={"R3-01":"steady_trend/R3_01_RECEIPT.json","R3-02":"strong_pullback/R3_02_RECEIPT.json","R3-03":"breakout_prep/R3_03_RECEIPT.json","R3-04":"sector_leader/R3_04_RECEIPT.json","R3-05":"early_mover/R3_05_RECEIPT.json"}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(p,b):
 p.parent.mkdir(parents=True,exist_ok=True);fd,t=tempfile.mkstemp(dir=p.parent,prefix="."+p.name,suffix=".tmp")
 try:os.write(fd,b);os.fsync(fd)
 finally:os.close(fd)
 os.replace(t,p)
def wjson(p,x):atomic(p,(json.dumps(x,ensure_ascii=False,indent=2,default=str,sort_keys=True)+"\n").encode())
def wcsv(p,x):atomic(p,x.to_csv(index=False).encode("utf-8-sig"))
def reason(row):
 rules=(("v2_steady_class","CONTINUITY_WEAK","STEADY_CONTINUITY_WEAK"),("v2_pullback_class","DEPTH_MISMATCH","PULLBACK_DEPTH_MISMATCH"),("v2_breakout_class","NEAR_HIGH_NO_CONTRACTION","BREAKOUT_NO_CONTRACTION"),("v2_leader_class","RETURN_LEADER_ONLY","LEADER_RETURN_ONLY"),("v2_leader_class","STYLE_SELF_REINFORCED","LEADER_STYLE_SELF_REINFORCED"),("v2_early_class","SHORT_TERM_PULSE","EARLY_SHORT_TERM_PULSE"),("v2_early_class","SECTOR_ALREADY_STABILIZING","EARLY_SECTOR_STABILIZING"))
 x=[label for field,value,label in rules if row[field]==value]
 if any(row[field]=="DATA_INSUFFICIENT" for field in ("v2_steady_class","v2_pullback_class","v2_breakout_class","v2_leader_class","v2_early_class")):x.append("DATA_INSUFFICIENT")
 return "|".join(x) or "V2_ONLY_DIAGNOSTIC_CONTEXT"
def run(requested="latest"):
 if requested!="latest":raise ValueError("SHADOW_LATEST_ONLY")
 pointer=ROOT/"reports/current/CURRENT_RELEASE.json";before=pointer.read_bytes();cur=json.loads(before);v1id=cur["latest_release"]["computation_identity"]["sha256"];release=ROOT/f"reports/releases/{CUTOFF}/{BASE_RUN}";v1p=[release/x for x in ("stocks.csv","candidates.csv","manifest.json")]+[pointer];v1hash={str(p.relative_to(ROOT)):sha(p) for p in v1p}
 shadow=ROOT/f"reports/shadow/v2/{CUTOFF}";bound={};rules={}
 # Bind artifacts produced for this cutoff. R3 receipts certify a rule version;
 # they are not daily inputs and therefore are not required in every new date.
 for phase,(queue,(relative,class_col)) in zip(RECEIPTS,SOURCES.items()):
  p=shadow/relative;x=pq.read_table(p).to_pandas()
  if x.empty or "date" not in x or set(pd.to_datetime(x.date).dt.strftime("%Y%m%d"))!={CUTOFF}:raise RuntimeError("V2_SOURCE_CUTOFF_MISMATCH:"+phase)
  ids=set(x.get("shadow_ruleset_id",pd.Series(dtype=str)).dropna().astype(str))
  if len(ids)!=1:raise RuntimeError("V2_SOURCE_RULESET_ID_MISSING_OR_AMBIGUOUS:"+phase)
  bound[phase]={"path":str(p.relative_to(ROOT)),"sha256":sha(p),"rows":len(x)};rules[phase]=ids.pop()
 candidates=pd.read_csv(release/"candidates.csv",encoding="utf-8-sig");board=candidates[["security_id","date","primary_pattern","research_priority"]].rename(columns={"primary_pattern":"v1_primary_pattern","research_priority":"v1_research_priority"})
 long=[]
 for queue,(relative,class_col) in SOURCES.items():
  x=pq.read_table(shadow/relative,columns=["security_id",class_col]).to_pandas();board=board.merge(x,on="security_id",how="left",validate="one_to_one");tier_col=queue.lower()+"_tier";board[tier_col]=[queue_tier(queue,v) for v in board[class_col]]
  for _,r in board[board[tier_col].notna()][["security_id",tier_col,class_col]].iterrows():long.append({"security_id":r.security_id,"queue_name":queue,"queue_tier":r[tier_col],"source_v2_class":r[class_col]})
 tiercols=[q.lower()+"_tier" for q in SOURCES];board["queue_memberships"]=["|".join(q for q,c in zip(SOURCES,tiercols) if pd.notna(r[c])) for _,r in board.iterrows()];board["queue_membership_count"]=board[tiercols].notna().sum(axis=1);board["core_structure_count"]=(board[tiercols]=="CORE").sum(axis=1);board["supported_structure_count"]=(board[tiercols]=="SUPPORTED").sum(axis=1);board["has_any_core"]=board.core_structure_count.gt(0);board["has_any_supported"]=board.supported_structure_count.gt(0);board["shadow_research_band"]=[research_band(r) for r in board[tiercols].itertuples(index=False,name=None)];board["v2_research_candidate"]=board.shadow_research_band.ne("DIAGNOSTIC_ONLY")
 board["has_data_insufficient_structure"]=board[[v[1] for v in SOURCES.values()]].eq("DATA_INSUFFICIENT").any(axis=1);board["has_style_self_reinforcement_context"]=board.v2_leader_class.eq("STYLE_SELF_REINFORCED");board["has_short_term_pulse_context"]=board.v2_early_class.eq("SHORT_TERM_PULSE");board["has_depth_mismatch_context"]=board.v2_pullback_class.eq("DEPTH_MISMATCH");board["has_no_contraction_context"]=board.v2_breakout_class.eq("NEAR_HIGH_NO_CONTRACTION");board["shadow_ruleset_id"]=RULESET_ID;board["display_order_only"]=DISPLAY_ORDER_ONLY;board["shadow"]=True;board["production_eligible"]=False;board=board.sort_values("security_id").reset_index(drop=True)
 long=pd.DataFrame(long,columns=["security_id","queue_name","queue_tier","source_v2_class"]).sort_values(["queue_name","queue_tier","security_id"],ascending=[True,True,True]);target=shadow/"priority";target.mkdir(parents=True,exist_ok=True)
 for name,frame in (("V2_UNIFIED_RESEARCH_BOARD.parquet",board),("V2_QUEUE_MEMBERSHIP.parquet",long)):
  tmp=target/("."+name+".tmp");pq.write_table(pa.Table.from_pandas(frame,preserve_index=False),tmp,compression="zstd");os.replace(tmp,target/name)
 qcounts={q:{t:int(((long.queue_name==q)&(long.queue_tier==t)).sum()) for t in ("CORE","SUPPORTED")} for q in SOURCES};bands=board.shadow_research_band.value_counts().to_dict();overlap=[]
 queues=list(SOURCES);members={q:set(long.loc[long.queue_name.eq(q),"security_id"]) for q in queues}
 for i,a in enumerate(queues):
  for b in queues[i+1:]:overlap.append({"left":a,"right":b,"intersection_count":len(members[a]&members[b])})
 for n in range(1,6):overlap.append({"left":f"EXACTLY_{n}_QUEUES","right":"", "intersection_count":int(board.queue_membership_count.eq(n).sum())})
 wcsv(target/"V2_STRUCTURE_OVERLAP_MATRIX.csv",pd.DataFrame(overlap))
 board["v1_v2_diff_category"]=board.shadow_research_band.map({"CORE_RESEARCH":"V2_CORE_RESEARCH","SUPPORTED_RESEARCH":"V2_SUPPORTED_RESEARCH","DIAGNOSTIC_ONLY":"V2_NO_STRUCTURE_CONFIRMATION"});board["v1_v2_diff_reasons"]=board.apply(reason,axis=1);wcsv(target/"V1_V2_PRIORITY_DIFF.csv",board)
 cross=pd.crosstab(board.v1_research_priority,board.shadow_research_band).to_dict();leader_v1=set(candidates.loc[candidates.v1_primary_pattern.eq("SECTOR_LEADER") if "v1_primary_pattern" in candidates else candidates.primary_pattern.eq("SECTOR_LEADER"),"security_id"])
 high=board.v1_research_priority.isin(["A+","A"]);v1_leaders=set(pq.read_table(shadow/SOURCES["LEADER_QUEUE"][0],columns=["security_id","v1_sector_leader"]).to_pandas().query("v1_sector_leader").security_id);den=int(high.sum());leader_count=len(set(board.loc[high,"security_id"])&v1_leaders);dominance={"multi_membership":True,"v1_a_plus_a_count":den,"v1_a_plus_a_sector_leader_count":leader_count,"v1_a_plus_a_sector_leader_ratio":leader_count/den if den else None,"band_queue_coverage":{band:{q:len(set(board.loc[board.shadow_research_band.eq(band),"security_id"])&members[q]) for q in queues} for band in ("CORE_RESEARCH","SUPPORTED_RESEARCH")}};wjson(target/"V2_LEADER_DOMINANCE_AUDIT.json",dominance)
 summary={"phase":"R3-06","ruleset_id":RULESET_ID,"v1_candidate_count":len(board),"queue_counts":qcounts,"band_counts":bands,"unique_v2_research_candidate_count":int(board.v2_research_candidate.sum()),"v1_v2_cross_tab":cross,"overlap":overlap};wjson(target/"V2_PRIORITY_SUMMARY.json",summary)
 identity_payload={"version":"priority-shadow-identity-v1.1-runtime-artifacts","ruleset_id":RULESET_ID,"source_artifacts":bound,"source_rulesets":rules,"files":{"src/shadow_v2/research_priority.py":sha(ROOT/"src/shadow_v2/research_priority.py"),"docs/RESEARCH_PRIORITY_V2_SHADOW_CONTRACT_V1.md":sha(ROOT/"docs/RESEARCH_PRIORITY_V2_SHADOW_CONTRACT_V1.md"),"run_priority_v2.py":sha(ROOT/"run_priority_v2.py")}};identity_payload["sha256"]=hashlib.sha256(json.dumps(identity_payload,sort_keys=True,separators=(",",":")).encode()).hexdigest();wjson(target/"V2_PRIORITY_SHADOW_IDENTITY.json",identity_payload)
 samples=[board[board.shadow_research_band.eq(b)].head(30).assign(sample_scope="UNIFIED_"+b) for b in ("CORE_RESEARCH","SUPPORTED_RESEARCH","DIAGNOSTIC_ONLY")]+[board[board[q.lower()+"_tier"].eq(t)].head(20).assign(sample_scope=q+"_"+t) for q in queues for t in ("CORE","SUPPORTED")];wcsv(target/"V2_PRIORITY_AUDIT_SAMPLE.csv",pd.concat(samples,ignore_index=True))
 assert board.security_id.is_unique and pointer.read_bytes()==before and v1hash=={str(p.relative_to(ROOT)):sha(p) for p in v1p}
 return {"queue_counts":qcounts,"bands":bands,"unique":int(board.v2_research_candidate.sum()),"identity":identity_payload,"dominance":dominance,"target":str(target),"v1_identity":v1id}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--date",default="latest");print(json.dumps(run(p.parse_args().date),ensure_ascii=False,indent=2,default=str))
