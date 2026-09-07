from __future__ import annotations
import argparse,hashlib,importlib,json,os,shutil,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/"src"))
from production.daily import run_daily,source_fingerprint
from production.release import atomic_write_json
from production.workbench import render_workbench
from common.identity import source_identity
from common.v2_identity import v2_execution_identity
from common.paths import resolve_tdx_root
from sector.membership_snapshot import build_snapshot
from shadow_v2.queue_ranking import rank_queues,VERSION as QUEUE_RANKING_VERSION
from run_forward_evaluation import run as refresh_forward_evaluation
from forward.live import *
from forward.observation import OBSERVATION_SCHEMA_VERSION,OUTCOME_SCHEMA_VERSION

TDX=resolve_tdx_root(ROOT);SEALED_MODEL="cb3bdd356f01dfaad5990a393a44d10149cf81f9805c533219124d773aad8c94"
MODULES=("run_shadow_v2","run_steady_trend_v2","run_strong_pullback_v2","run_breakout_prep_v2","run_sector_leader_v2","run_early_mover_v2","run_priority_v2")
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source_snapshot(tdx):
    paths=[tdx/"T0002/hq_cache"/x for x in ("gbbq","gbbq.map","tdxhy.cfg","tdxzs.cfg","infoharbor_block.dat","shs.tnf","szs.tnf","bjs.tnf")];return {str(p):sha(p) for p in paths if p.exists()}
class ProductionServices:
    def refresh_forward_evaluation(self,root):return refresh_forward_evaluation(root)
    def identity_layers(self,root):
        root=Path(root);seal=json.loads((root/"reports/shadow/v2/20260904/integrated/R3_INTEGRATED_SHADOW_IDENTITY.json").read_text())
        approved=self.model_identity(root);economic_root="/".join(("src","shadow_v2",""))
        files={p:sha(root/p) for p in seal["files"] if p.startswith(economic_root) or (p.startswith("docs/") and "R4_" not in p)}
        economic={"version":"v2-economic-model-identity-v1.0","approval_identity":approved,"files":files}
        economic["sha256"]=hashlib.sha256(json.dumps(economic,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        return {"economic_model_identity":economic,"execution_identity":v2_execution_identity(root)}
    def run_v1(self,root,tdx):return run_daily(root,tdx,"latest")
    def run_v2(self,root,cutoff,v1):
        statuses=[]
        published_release_id=v1.get("published_release_id") or v1["run_id"]
        for name in MODULES:
            m=importlib.import_module(name);m.ROOT=Path(root);m.TDX_ROOT=resolve_tdx_root(root);m.CUTOFF=str(cutoff);m.BASE_RUN=published_release_id;value=m.run("latest");statuses.append({"module":name,"status":"PASS","cutoff":str(cutoff),"result":value})
        root=Path(root);source=root/f"reports/shadow/v2/{cutoff}";execution=v2_execution_identity(root);archive=root/f"reports/shadow/v2_runs/{cutoff}/{published_release_id}/{execution['sha256']}"
        files={str(p.relative_to(source)).replace("\\","/"):sha(p) for p in source.rglob("*") if p.is_file()}
        archive_identity={"version":"v2-runtime-snapshot-v1.1-execution-bound","cutoff":str(cutoff),"v1_release_id":published_release_id,"execution_identity":execution,"files":files}
        archive_identity["sha256"]=hashlib.sha256(json.dumps(archive_identity,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        if archive.exists():
            old=json.loads((archive/"V2_RUNTIME_SNAPSHOT.json").read_text("utf8"))
            if old.get("sha256")!=archive_identity["sha256"]:raise RuntimeError("V2_RUNTIME_SNAPSHOT_CONFLICT")
        else:
            archive.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix=".v2_",suffix=".tmp",dir=archive.parent))
            try:
                for relative in files:
                    target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/relative,target)
                (stage/"V2_RUNTIME_SNAPSHOT.json").write_text(json.dumps(archive_identity,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf8")
                os.replace(stage,archive)
            finally:shutil.rmtree(stage,ignore_errors=True)
        statuses[-1]["runtime_snapshot"]={"path":str(archive),"sha256":archive_identity["sha256"]}
        return statuses,pd.read_parquet(source/"priority/V2_UNIFIED_RESEARCH_BOARD.parquet")
    def publish_workbench(self,root,cutoff,v1,statuses,tdx=None):
        root=Path(root);release_id=v1.get("published_release_id") or v1["run_id"]
        release=root/f"reports/releases/{cutoff}/{release_id}";shadow=root/f"reports/shadow/v2/{cutoff}"
        sources={
            "稳健":shadow/"steady_trend/STEADY_TREND_V2_SHADOW.parquet",
            "回撤":shadow/"strong_pullback/STRONG_PULLBACK_V2_SHADOW.parquet",
            "突破":shadow/"breakout_prep/BREAKOUT_PREP_V2_SHADOW.parquet",
            "板块":shadow/"sector_leader/SECTOR_LEADER_V2_SHADOW.parquet",
            "早期":shadow/"early_mover/EARLY_MOVER_V2_SHADOW.parquet",
        }
        board_path=shadow/"priority/V2_UNIFIED_RESEARCH_BOARD.parquet"
        membership,membership_sources=build_snapshot(Path(tdx) if tdx is not None else resolve_tdx_root(root),cutoff)
        bound={str(p.relative_to(root)).replace("\\","/"):sha(p) for p in [release/"manifest.json",board_path,*sources.values()]}
        bound.update({str(p).replace("\\","/"):h for p,h in membership_sources.items()})
        layers=self.identity_layers(root);runtime=statuses[-1].get("runtime_snapshot",{})
        identity={"version":"research-workbench-v1.1-ranked-linked","cutoff":str(cutoff),"v1_release_id":release_id,"v2_runtime_snapshot_sha256":runtime.get("sha256"),"economic_model_identity":layers["economic_model_identity"]["sha256"],"execution_identity":layers["execution_identity"]["sha256"],"queue_ranking_contract":QUEUE_RANKING_VERSION,"membership_snapshot_version":str(membership.snapshot_version.iloc[0]),"inputs":bound}
        identity["sha256"]=hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        target=root/f"reports/workbench/{cutoff}/{release_id}/{layers['execution_identity']['sha256']}"
        if target.exists():
            old=json.loads((target/"WORKBENCH_IDENTITY.json").read_text("utf8"))
            if old.get("sha256")!=identity["sha256"]:raise RuntimeError("WORKBENCH_IDENTITY_CONFLICT")
        else:
            target.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix=".workbench_",suffix=".tmp",dir=target.parent))
            try:
                sectors=pd.read_csv(release/"sectors.csv",encoding="utf-8-sig");stocks=pd.read_csv(release/"stocks.csv",encoding="utf-8-sig");candidates=pd.read_csv(release/"candidates.csv",encoding="utf-8-sig");board=pd.read_parquet(board_path);details={k:pd.read_parquet(p) for k,p in sources.items()}
                ranking=rank_queues(board,{"steady":details["稳健"],"pullback":details["回撤"],"breakout":details["突破"],"leader":details["板块"],"early":details["早期"]})
                page=render_workbench(str(cutoff),release_id,sectors,stocks,candidates,board,details,identity,membership,ranking)
                ranking.to_parquet(stage/"V2_QUEUE_RANKING.parquet",index=False)
                membership.to_parquet(stage/"SECTOR_MEMBERSHIP_SNAPSHOT.parquet",index=False)
                (stage/"market_structure_workbench.html").write_text(page,encoding="utf8")
                (stage/"WORKBENCH_IDENTITY.json").write_text(json.dumps(identity,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf8")
                os.replace(stage,target)
            finally:shutil.rmtree(stage,ignore_errors=True)
        pointer={"version":"current-workbench-v1.0","cutoff":str(cutoff),"v1_release_id":release_id,"workbench_path":str(target/"market_structure_workbench.html"),"identity":identity}
        atomic_write_json(root/"reports/workbench/CURRENT_WORKBENCH.json",pointer)
        return {"path":pointer["workbench_path"],"sha256":identity["sha256"],"v1_release_id":release_id}
    def model_identity(self,root):
        root=Path(root);value=json.loads((root/"reports/shadow/v2/20260904/integrated/R3_INTEGRATED_SHADOW_IDENTITY.json").read_text())
        # Entry points also contain classification gates, so every file sealed
        # into the integrated model identity must pass this preflight.
        changed=[p for p,h in value["files"].items() if not (root/p).is_file() or sha(root/p)!=h]
        if changed:raise RuntimeError("MODEL_VERSION_CHANGED:"+",".join(changed))
        return value["sha256"]
    def current_source_identity(self,root,tdx,cutoff):return source_identity(source_fingerprint(Path(root),Path(tdx),str(cutoff)))["sha256"]
    def prices(self,root,cutoff,security_ids):
        d=pd.Timestamp(str(cutoff)).date();path=Path(root)/"data/normalized/adjusted_daily.parquet"
        values=pd.read_parquet(path,filters=[("date","=",d)],columns=["security_id","adj_close","adj_high","adj_low","has_actual_bar"])
        return values[values.security_id.isin(set(security_ids)) & values.has_actual_bar.eq(True)].drop(columns="has_actual_bar").drop_duplicates("security_id")
    def _baseline_prices(self,root,revision,rows):
        missing={x["security_id"] for x in rows if pd.isna(x.get("adj_close"))}
        if not missing:return rows
        identity=json.loads((revision/"OBSERVATION_IDENTITY.json").read_text("utf8"));run_id=identity.get("v1_release_run_id") or identity.get("v1_run_id")
        if not run_id:return rows
        path=Path(root)/f"reports/releases/{revision.parent.name}/{run_id}/stocks.csv"
        if not path.is_file():return rows
        prices=pd.read_csv(path,encoding="utf-8-sig",usecols=["security_id","adj_close"]).set_index("security_id").adj_close.to_dict()
        for row in rows:
            if pd.isna(row.get("adj_close")) and row["security_id"] in prices:row["adj_close"]=prices[row["security_id"]]
        return rows
    def outcomes(self,root,cutoff,frame,sequence):
        if frame.empty:return []
        root=Path(root);snapshots={}
        for d in sequence[:-1]:
            revision=latest_revision(root,d)
            if revision is not None:snapshots[d]=self._baseline_prices(root,revision,read_observation(revision))
        snapshots[str(cutoff)]=frame.to_dict("records");current_index=len(sequence)-1;result=[]
        for signal_index,signal_date in enumerate(sequence[:-1]):
            horizon=current_index-signal_index
            if horizon not in HORIZONS or signal_date not in snapshots:continue
            target={x["security_id"]:x for x in snapshots[str(cutoff)]};interval=sequence[signal_index+1:current_index+1]
            interval_maps={d:{x["security_id"]:x for x in snapshots.get(d,[])} for d in interval}
            for signal in snapshots[signal_date]:
                if signal.get("active_candidate") is False:continue
                sid=signal["security_id"];reference=pd.to_numeric(signal.get("adj_close"),errors="coerce");end=target.get(sid,{});close=pd.to_numeric(end.get("adj_close"),errors="coerce")
                highs=[pd.to_numeric(interval_maps[d].get(sid,{}).get("adj_high"),errors="coerce") for d in interval]
                lows=[pd.to_numeric(interval_maps[d].get(sid,{}).get("adj_low"),errors="coerce") for d in interval]
                observed=pd.notna(reference) and reference>0 and pd.notna(close) and all(pd.notna(x) for x in highs+lows)
                result.append({"security_id":sid,"signal_observation_id":signal["observation_id"],"signal_date":signal_date,"horizon":horizon,"target_trading_date":str(cutoff),"target_revision":int(frame.source_revision_id.iloc[0]),"entry_reference_price":float(reference) if pd.notna(reference) else None,"target_close":float(close) if pd.notna(close) else None,"forward_return":float(close/reference-1) if observed else None,"max_high_return":float(max(highs)/reference-1) if observed else None,"max_drawdown":float(min(lows)/reference-1) if observed else None,"outcome_status":"OBSERVED" if observed else "DATA_UNAVAILABLE","outcome_observed_at":datetime.now(timezone.utc).isoformat(),"price_basis":"TDX_NATIVE_QFQ","research_reference_only":True})
        return result
def latest_forward(root):
    dates=sealed_sequence(root);date=dates[-1];rev=latest_revision(root,date);identity=json.loads((rev/"OBSERVATION_IDENTITY.json").read_text("utf8"));return date,rev,identity
def all_seen(root):
    seen=set()
    for d in sealed_sequence(root):seen.update(x["security_id"] for x in read_observation(latest_revision(root,d)))
    return seen
def run(requested="latest",root=ROOT,tdx=TDX,services=None,fail_before_commit=False):
    root=Path(root);tdx=Path(tdx);services=services or ProductionServices()
    if requested!="latest":return 2,{"status":"BLOCKED","error":"LIVE_LATEST_ONLY"}
    # Fail closed before V1 can publish anything when the approved V2 economic
    # model no longer matches the checked-in rules and contracts.
    try:
        layers=services.identity_layers(root) if hasattr(services,"identity_layers") else {"economic_model_identity":{"approval_identity":services.model_identity(root)},"execution_identity":{}}
        if layers["economic_model_identity"].get("approval_identity")!=SEALED_MODEL:raise RuntimeError("MODEL_VERSION_CHANGED")
    except Exception as exc:
        return 1,{"status":"BLOCKED","stage":"MODEL_IDENTITY_PREFLIGHT","error":str(exc),"observation_written":False,"daily_receipt_written":False}
    cutoff,prior_rev,prior_identity=latest_forward(root);before=source_snapshot(tdx);code,v1=services.run_v1(root,tdx);after=source_snapshot(tdx)
    if code or v1.get("status") not in ("SUCCESS","VERIFIED_NO_NEW_DATA"):return code or 1,{"status":"BLOCKED","stage":"RUN_VERIFY_V1","v1":v1}
    resolved=str(v1["resolved_cutoff_date"]);source=v1["source_identity"]["sha256"];old_source=prior_identity.get("source_identity") or prior_identity.get("source_revision_id");event=live_event(resolved,cutoff,source,old_source)
    release_id=v1.get("published_release_id") or v1.get("run_id")
    base={"status":event,"live_event":event,"latest_resolved_cutoff":resolved,"latest_forward_cutoff":cutoff,"v1_run_id":release_id,"v1_invocation_id":v1.get("invocation_id",v1.get("run_id")),"v1_status":v1.get("status"),"steps_completed":list(ORCHESTRATION_ORDER[:2]),"observation_written":False,"daily_receipt_written":False,"revision_created":False,"runner_write_to_tdx_detected":before!=after,"v1_source_fingerprint_before":old_source,"v1_source_fingerprint_after":source,"model_rules_changed":False,"thresholds_changed":False}
    if before!=after:return 1,{**base,"status":"BLOCKED","error":"TDX_SOURCE_MODIFIED_BY_RUNNER"}
    base["economic_model_identity"]=layers["economic_model_identity"].get("sha256",SEALED_MODEL);base["execution_identity"]=layers["execution_identity"].get("sha256")
    if event=="VERIFIED_NO_NEW_FORWARD_OBSERVATION":
        try:
            wb_pointer=root/"reports/workbench/CURRENT_WORKBENCH.json"
            cached=json.loads(wb_pointer.read_text("utf8")) if wb_pointer.is_file() else {}
            if cached.get("v1_release_id")==release_id and cached.get("identity",{}).get("execution_identity")==base.get("execution_identity") and Path(cached.get("workbench_path","")).is_file():workbench={"path":cached["workbench_path"],"sha256":cached["identity"]["sha256"],"v1_release_id":release_id,"status":"REUSED"}
            else:
                statuses,_=services.run_v2(root,resolved,v1);workbench=services.publish_workbench(root,resolved,v1,statuses,tdx) if isinstance(services,ProductionServices) else (services.publish_workbench(root,resolved,v1,statuses) if hasattr(services,"publish_workbench") else {})
            if hasattr(services,"current_source_identity") and services.current_source_identity(root,tdx,resolved)!=source:raise RuntimeError("SOURCE_CHANGED_DURING_V2")
            evaluation=services.refresh_forward_evaluation(root) if hasattr(services,"refresh_forward_evaluation") else {}
            return 0,{**base,"workbench":workbench,"forward_evaluation":evaluation}
        except Exception as exc:return 1,{**base,"status":"BLOCKED","stage":"PUBLISH_WORKBENCH","error":str(exc)}
    try:
        statuses,board=services.run_v2(root,resolved,v1);base["steps_completed"]=list(ORCHESTRATION_ORDER[:4])
        workbench=services.publish_workbench(root,resolved,v1,statuses,tdx) if isinstance(services,ProductionServices) else (services.publish_workbench(root,resolved,v1,statuses) if hasattr(services,"publish_workbench") else {})
        base["workbench"]=workbench
        if len(statuses)!=7 or any(str(x.get("cutoff"))!=resolved or x.get("status")!="PASS" for x in statuses):raise RuntimeError("V2_CUTOFF_ALIGNMENT_BLOCKED")
        if hasattr(services,"current_source_identity") and services.current_source_identity(root,tdx,resolved)!=source:raise RuntimeError("SOURCE_CHANGED_DURING_V2")
        base["steps_completed"]=list(ORCHESTRATION_ORDER[:5]);revision=next_revision_number(root,resolved)
        prior_path=latest_revision(root,cutoff);prior=read_observation(prior_path)
        priority_identity=json.loads((root/f"reports/shadow/v2/{resolved}/priority/V2_PRIORITY_SHADOW_IDENTITY.json").read_text("utf8")) if isinstance(services,ProductionServices) else {}
        runtime_snapshot=statuses[-1].get("runtime_snapshot",{})
        payload={"cutoff_date":resolved,"source_identity":source,"source_revision_id":revision,"v1_run_id":release_id,"v1_computation_identity":v1.get("computation_identity",{}).get("sha256"),"input_snapshot_manifest_sha256":v1.get("input_snapshot_manifest_sha256"),"r3_integrated_shadow_identity":SEALED_MODEL,"economic_model_identity":base.get("economic_model_identity"),"execution_identity":base.get("execution_identity"),"priority_shadow_identity":priority_identity.get("sha256"),"v2_runtime_snapshot_sha256":runtime_snapshot.get("sha256"),"v2_runtime_snapshot_path":runtime_snapshot.get("path"),"observation_schema_version":OBSERVATION_SCHEMA_VERSION,"outcome_schema_version":OUTCOME_SCHEMA_VERSION};oid=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest();payload["observation_id"]=oid
        union_ids=set(board.security_id)|{x["security_id"] for x in prior};prices=services.prices(root,resolved,union_ids) if hasattr(services,"prices") else None
        frame=make_observation_rows(board,prior,all_seen(root),resolved,revision,oid,event=="SAME_CUTOFF_SOURCE_REVISION",prices);base["steps_completed"]=list(ORCHESTRATION_ORDER[:7])
        sequence=sealed_sequence(root)+([] if event=="SAME_CUTOFF_SOURCE_REVISION" else [resolved]);outcome_rows=services.outcomes(root,resolved,frame,sequence);outcomes=outcome_stats(outcome_rows);base["steps_completed"]=list(ORCHESTRATION_ORDER[:8])
        receipt={"cutoff":resolved,"revision":revision,"observation_id":oid,"steps_completed":list(ORCHESTRATION_ORDER),"v1_run_id":release_id,"v1_release_id":release_id,"v1_invocation_id":v1.get("invocation_id",v1.get("run_id")),"v1_event":v1.get("status"),"five_v2_statuses":statuses[1:6],"priority_status":statuses[-1],"state_counts":frame.candidate_state.value_counts().to_dict(),"research_band_counts":frame.shadow_research_band.value_counts().to_dict(),"outcomes":outcomes,"source_identity":source,"model_identity":SEALED_MODEL,"economic_model_identity":base.get("economic_model_identity"),"execution_identity":base.get("execution_identity"),"tdx_source_modified_by_runner":False,"model_rules_changed":False,"final_status":"PASS"}
        published=publish_observation(root,resolved,revision,frame,payload,receipt,fail_before_commit,outcome_rows);evaluation=services.refresh_forward_evaluation(root) if hasattr(services,"refresh_forward_evaluation") else {};base.update(status="PASS",observation_id=oid,steps_completed=list(ORCHESTRATION_ORDER),observation_written=published=="PUBLISHED",daily_receipt_written=published=="PUBLISHED",revision_created=event=="SAME_CUTOFF_SOURCE_REVISION",publish_status=published,outcomes=outcomes,forward_evaluation=evaluation);return 0,base
    except Exception as exc:return 1,{**base,"status":"BLOCKED","error":str(exc)}
def main():
    p=argparse.ArgumentParser();p.add_argument("--date",default="latest");code,result=run(p.parse_args().date)
    # A failed invocation is runtime state, not a new immutable observation.
    # Never overwrite a receipt already covered by a revision manifest.
    if result.get("status")=="BLOCKED":
        try:
            target=ROOT/"runtime/forward/LAST_BLOCKED_RUN.json"
            atomic_write_json(target,{"final_status":"BLOCKED","stage":result.get("stage"),"error":result.get("error"),"observation_written":False,"daily_receipt_written":False,"model_identity_preflight_pass":False,"next_allowed_stage":"REBUILD_CURRENT_R3_RECEIPTS_AND_EXTERNAL_REAUDIT"})
        except Exception:
            pass
    print(json.dumps(result,ensure_ascii=False,indent=2,default=str));return code
if __name__=="__main__":raise SystemExit(main())
