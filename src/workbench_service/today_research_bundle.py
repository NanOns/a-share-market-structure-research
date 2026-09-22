"""Fail-closed read model for the active P12 V3.3 research bundle."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import duckdb
from .research_bundle_v3_3 import ResearchBundleError, read_active

API_CONTRACT = "TODAY_RESEARCH_V3_3_API_01"
EFFECT_STATUS = "EFFECT_OBSERVATION_PENDING"

class TodayResearchBundleReader:
 def __init__(self, root: Path, pointer: Path | None = None, database_path: Path | None = None, repository: Any | None = None):
  self.root=Path(root).resolve();self.pointer=Path(pointer) if pointer else self.root/"data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json";self.database_path=Path(database_path) if database_path else None;self.repository=repository
 def _load(self)->tuple[dict[str,Any],list[dict[str,Any]]]:
  active=read_active(self.pointer)
  if active is None:raise ResearchBundleError("ACTIVE_BUNDLE_NOT_BUILT")
  rows=json.loads((Path(active["bundle_path"])/"results.json").read_text(encoding="utf-8"))
  if not isinstance(rows,list) or any(not isinstance(item,dict) for item in rows):raise ResearchBundleError("BUNDLE_RESULTS_INVALID")
  return active,rows
 def _decorate(self,active:dict[str,Any],rows:list[dict[str,Any]])->list[dict[str,Any]]:
  names={}
  if self.repository is not None:
   try:
    names=dict(self.repository.research_security_names(str(active["identity"]["publication_id"])))
   except Exception:
    names={}
  elif self.database_path and self.database_path.is_file():
   try:
    with duckdb.connect(str(self.database_path),read_only=True) as connection:
     names=dict(connection.execute("select security_id,security_name from stock_daily where publication_id=?",[active["identity"]["publication_id"]]).fetchall())
   except Exception:
    names={}
  return [{**row,"security_name":row.get("security_name") or names.get(row.get("security_id")),"display_rank":index} for index,row in enumerate(rows,1)]
 @staticmethod
 def _unavailable(code:str)->dict[str,Any]:
  status="NOT_BUILT" if code=="ACTIVE_BUNDLE_NOT_BUILT" else "UNAVAILABLE"
  return {"api_contract":API_CONTRACT,"status":status,"code":code,"effect_status":EFFECT_STATUS,"items":[],"total":0,"returned_count":0,"has_more":False,"empty_state":{"code":code,"message":"尚未生成今日 V3.3 研究包。" if status=="NOT_BUILT" else "研究包完整性校验失败，未展示任何候选。"}}
 @staticmethod
 def _context(active:dict[str,Any])->dict[str,Any]:
  return {**active["identity"],"bundle_contract_id":active["contract_id"],"output_digest":active["output_digest"]}
 def list(self,*,page:Any=1,page_size:Any=20,category:str="",selection_mode:str="",q:str="")->dict[str,Any]:
  try:active,rows=self._load()
  except (ResearchBundleError,OSError,ValueError,KeyError,json.JSONDecodeError) as exc:return self._unavailable(str(exc) or type(exc).__name__)
  page=max(1,int(page));page_size=min(100,max(1,int(page_size)));category=str(category or "").strip().upper();selection_mode=str(selection_mode or "").strip().upper();query=str(q or "").strip().upper()
  rows=self._decorate(active,rows)
  filtered=[row for row in rows if (not category or category in row.get("matched_categories",[])) and (not selection_mode or row.get("selection_mode")==selection_mode) and (not query or query in str(row.get("security_id","")).upper() or query in str(row.get("security_name","")).upper())]
  start=(page-1)*page_size;items=filtered[start:start+page_size];counts={"categories":{},"selection_modes":{},"rank_statuses":{}}
  for row in rows:
   for value in row.get("matched_categories",[]):counts["categories"][value]=counts["categories"].get(value,0)+1
   for key,field in (("selection_modes","selection_mode"),("rank_statuses","rank_status")):
    value=str(row.get(field) or "UNKNOWN");counts[key][value]=counts[key].get(value,0)+1
  return {"api_contract":API_CONTRACT,"status":"READY" if filtered else "EMPTY","effect_status":EFFECT_STATUS,"context":self._context(active),"filters":{"category":category or None,"selection_mode":selection_mode or None,"q":query or None},"counts":counts,"page":page,"page_size":page_size,"total":len(filtered),"returned_count":len(items),"has_more":start+len(items)<len(filtered),"items":items,"empty_state":None if filtered else {"code":"NO_MATCH","message":"当前筛选条件没有候选。"}}
 def detail(self,security_id:str,expected_digest:str="")->dict[str,Any]:
  try:active,rows=self._load()
  except (ResearchBundleError,OSError,ValueError,KeyError,json.JSONDecodeError) as exc:return self._unavailable(str(exc) or type(exc).__name__)
  if expected_digest and expected_digest!=active.get("output_digest"):
   return {**self._unavailable("BUNDLE_CONTEXT_CHANGED"),"empty_state":{"code":"BUNDLE_CONTEXT_CHANGED","message":"研究包已更新，请刷新候选列表后重试。"}}
  rows=self._decorate(active,rows);wanted=str(security_id or "").strip().upper();item=next((row for row in rows if str(row.get("security_id","")).upper()==wanted),None)
  return {"api_contract":API_CONTRACT,"status":"READY" if item else "EMPTY","effect_status":EFFECT_STATUS,"context":self._context(active),"security_id":wanted,"item":item,"items":[item] if item else [],"empty_state":None if item else {"code":"SECURITY_NOT_IN_BUNDLE","message":"该证券不在当前完整研究包中。"}}
