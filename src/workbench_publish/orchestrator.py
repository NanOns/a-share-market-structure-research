"""Controlled computation adapter for M4 one-click publication."""
from __future__ import annotations
import csv, json, subprocess, sys, hashlib, os, uuid
from pathlib import Path
from typing import Any
import pyarrow.parquet as pq
import pandas as pd
from production.workbench import render_workbench
from .service import PublicationRequest, OneClickPublisher
from workbench_db import WorkbenchRepository, PostgresPublicationBackendFactory

def _csv(path:Path):
 with path.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def _parquet(path:Path): return pq.read_table(path).to_pylist() if path.is_file() else []
def _observation_row_id(batch_id:str,row:dict[str,Any],publication_id:str="")->str:
 return hashlib.sha256((publication_id+"|"+batch_id+"|"+str(row["security_id"])).encode()).hexdigest()
def _publication_id(request:PublicationRequest,release:Path)->str:
 body={"source_bundle_id":request.source_bundle_id,"daily_release_id":release.name,"economic_model_id":request.economic_model_id,"computation_contract_id":request.computation_contract_id}
 return "m4-"+hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:32]
def _observations(path:Path,publication_id:str=""):
 rows=[]
 for row in _parquet(path):
  batch=str(row.get("observation_id") or "")
  rows.append({**row,"batch_observation_id":batch,"observation_id":_observation_row_id(batch,row,publication_id)})
 return rows

def write_static_workbench(root:Path,request:PublicationRequest,release:Path)->None:
 day=request.trade_date.strftime("%Y%m%d");base=root/"reports/shadow/v2"/day
 existing=list((root/"reports/workbench"/day/request.publication_id).glob("*/market_structure_workbench.html"))
 if existing:return
 details={}
 for queue,rel in (("steady","steady_trend/STEADY_TREND_V2_SHADOW.parquet"),("pullback","strong_pullback/STRONG_PULLBACK_V2_SHADOW.parquet"),("breakout","breakout_prep/BREAKOUT_PREP_V2_SHADOW.parquet"),("leader","sector_leader/SECTOR_LEADER_V2_SHADOW.parquet"),("early","early_mover/EARLY_MOVER_V2_SHADOW.parquet")):
  details[queue]=pd.DataFrame(_parquet(base/rel))
 rank_paths=sorted((root/"reports/workbench"/day).glob("*/*/V2_QUEUE_RANKING.parquet"),key=lambda p:p.stat().st_mtime_ns,reverse=True)
 receipt=json.loads((release/"PRODUCTION_RECEIPT.json").read_text("utf-8"))
 membership=pd.DataFrame([x for x in _parquet(root/"data/sectors/sector_membership_daily.parquet") if str(x.get("date"))[:10]==request.trade_date.isoformat()])
 html=render_workbench(day,request.publication_id,pd.DataFrame(_csv(release/"sectors.csv")),pd.DataFrame(_csv(release/"stocks.csv")),pd.DataFrame(_csv(release/"candidates.csv")),pd.DataFrame(_parquet(base/"priority/V2_UNIFIED_RESEARCH_BOARD.parquet")),details,receipt.get("source_identity",{}),membership,pd.DataFrame(_parquet(rank_paths[0])))
 output=root/"reports/workbench"/day/request.publication_id/uuid.uuid4().hex/"market_structure_workbench.html";output.parent.mkdir(parents=True,exist_ok=True)
 temp=output.with_suffix(".tmp");temp.write_text(html,encoding="utf-8");os.replace(temp,output)

def load_computed_results(root:Path,request:PublicationRequest,release:Path)->PublicationRequest:
 day=request.trade_date.strftime("%Y%m%d");base=root/"reports/shadow/v2"/day
 prepared=PublicationRequest(request.trade_date,request.source_bundle_id,request.economic_model_id,request.computation_contract_id,release_id=_publication_id(request,release));write_static_workbench(root,prepared,release)
 structures=[]
 for queue,rel in (("STEADY","steady_trend/STEADY_TREND_V2_SHADOW.parquet"),("PULLBACK","strong_pullback/STRONG_PULLBACK_V2_SHADOW.parquet"),("BREAKOUT","breakout_prep/BREAKOUT_PREP_V2_SHADOW.parquet"),("LEADER","sector_leader/SECTOR_LEADER_V2_SHADOW.parquet"),("EARLY","early_mover/EARLY_MOVER_V2_SHADOW.parquet")):
  structures.extend(({**row,"queue_name":queue} for row in _parquet(base/rel)))
 rank_paths=sorted((root/"reports/workbench"/day).glob("*/*/V2_QUEUE_RANKING.parquet"),key=lambda p:p.stat().st_mtime_ns,reverse=True)
 forward=root/"data/forward/observations"/day
 revisions=sorted(forward.glob("revision_*"),key=lambda p:int(p.name.split("_")[-1]),reverse=True)
 observations=_observations(revisions[0]/"FORWARD_OBSERVATION.parquet",prepared.publication_id) if revisions else []
 raw_outcomes=json.loads((revisions[0]/"OUTCOME_BATCH.json").read_text("utf-8")).get("rows",[]) if revisions and (revisions[0]/"OUTCOME_BATCH.json").is_file() else []
 # A due outcome belongs to its original historical signal observation, not
 # today's publication.  Keep that stable key while today's new observations
 # receive publication-scoped IDs above.
 outcomes=[{**row,"observation_id":_observation_row_id(str(row["signal_observation_id"]),row)} for row in raw_outcomes]
 return PublicationRequest(request.trade_date,request.source_bundle_id,request.economic_model_id,request.computation_contract_id,release_id=prepared.release_id,
  stocks=tuple(_csv(release/"stocks.csv")),sectors=tuple(_csv(release/"sectors.csv")),candidates=tuple(_csv(release/"candidates.csv")),structures=tuple(structures),
  queue_memberships=tuple(_parquet(base/"priority/V2_QUEUE_MEMBERSHIP.parquet")),unified_board=tuple(_parquet(base/"priority/V2_UNIFIED_RESEARCH_BOARD.parquet")),queue_rankings=tuple(_parquet(rank_paths[0]) if rank_paths else []),memberships=tuple(row for row in _parquet(root/"data/sectors/sector_membership_daily.parquet") if str(row.get("date"))[:10]==request.trade_date.isoformat()),observations=tuple(observations),outcomes=tuple(outcomes))

def seed_forward_baseline(root:Path,database_path,through_date):
 """Migrate prior sealed observations so today's due outcomes have a real signal."""
 with WorkbenchRepository(root,database_path) as repo:
  con=repo.connection
  for day_dir in sorted((root/"data/forward/observations").glob("20*")):
   day=day_dir.name
   if day>=through_date.strftime("%Y%m%d"):continue
   pub=con.execute("select publication_id from publication_heads where trade_date=?",[f"{day[:4]}-{day[4:6]}-{day[6:]}"]).fetchone()
   if not pub: continue
   revisions=sorted(day_dir.glob("revision_*"),key=lambda p:int(p.name.split("_")[-1]),reverse=True)
   if not revisions:continue
   for row in _observations(revisions[0]/"FORWARD_OBSERVATION.parquet"):
    con.execute("insert into observations values (?,?,?) on conflict do nothing",[row["observation_id"],pub[0],json.dumps(row,ensure_ascii=False,default=str)])

class ControlledProduction:
 def __init__(self,root:Path,timeout_seconds:int=1800):self.root=Path(root).resolve();self.timeout_seconds=timeout_seconds
 def __call__(self,request:PublicationRequest)->PublicationRequest:
  command=[sys.executable,str(self.root/"run_bundle_compute.py"),"--bundle-id",request.source_bundle_id,"--date",request.trade_date.strftime("%Y%m%d")]
  result=subprocess.run(command,cwd=self.root,capture_output=True,text=True,timeout=self.timeout_seconds)
  if result.returncode:raise RuntimeError("CONTROLLED_COMPUTE_FAILED:"+result.stderr[-2000:])
  payload=json.loads(result.stdout.strip().splitlines()[-1]);release=Path(payload["release_path"]).resolve()
  if self.root not in release.parents or not release.is_dir():raise ValueError("COMPUTE_RELEASE_PATH_INVALID")
  return load_computed_results(self.root,request,release)

def submit_one_click(root:Path,bundle_id:str,trade_date,economic_model_id:str,computation_contract_id:str,database_path=None):
 # PostgreSQL mode already owns the publication/observation state.  Opening
 # the shared DuckDB file here only to seed an offline forward baseline would
 # reintroduce the lock race that the application cutover removed.
 if str(os.environ.get("WORKBENCH_API_BACKEND", "")).lower() != "postgresql":
  seed_forward_baseline(Path(root),database_path,trade_date)
 pg_factory = PostgresPublicationBackendFactory() if str(os.environ.get("WORKBENCH_API_BACKEND", "")).lower() == "postgresql" else None
 publisher=OneClickPublisher(root,database_path,postgres_backend_factory=pg_factory);request=PublicationRequest(trade_date,bundle_id,economic_model_id,computation_contract_id)
 return publisher,publisher.submit(request,ControlledProduction(Path(root)))
