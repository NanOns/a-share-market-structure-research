"""Fail-closed posterior schedule for frozen P12 stock episodes."""
from __future__ import annotations

from datetime import date
from typing import Any,Iterable

from workbench_analysis.forward_v3_3 import atomic_write,digest

CONTRACT_ID="TODAY_RESEARCH_FORWARD_OUTCOME_V3_3_CANDIDATE_01"
EVALUATION_BASIS="HORIZON_END_TDX_AFFINE_QFQ_V1"
HORIZONS=(1,3,5,10)

def _iso(value:Any)->str:return value.isoformat() if hasattr(value,"isoformat") else str(value)[:10]

def first_episode_signals(observations:Iterable[dict])->list[dict]:
 first={}
 for observation in sorted(observations,key=lambda value:value["trade_date"]):
  for row in observation["rows"]:
   episode_id=row.get("episode_id")
   if not episode_id:continue
   first.setdefault(episode_id,{"signal_run_id":observation["research_run_id"],"signal_date":observation["trade_date"],"bundle_digest":observation["bundle_digest"],"security_id":row["security_id"],"episode_id":episode_id,"primary_category":row.get("primary_category"),"selection_mode":row.get("selection_mode")})
 return sorted(first.values(),key=lambda value:(value["signal_date"],value["security_id"],value["episode_id"]))

def plan_outcomes(observations:Iterable[dict],sessions:Iterable[Any],as_of_data_date:Any)->dict:
 calendar=sorted({_iso(value) for value in sessions});as_of=_iso(as_of_data_date);rows=[]
 for signal in first_episode_signals(observations):
  if signal["signal_date"] not in calendar:raise ValueError("SIGNAL_DATE_NOT_IN_SESSION_CALENDAR")
  index=calendar.index(signal["signal_date"])
  for horizon in HORIZONS:
   end_date=calendar[index+horizon] if index+horizon<len(calendar) else None
   status="DUE_UNMATERIALIZED" if end_date and end_date<=as_of else "NOT_DUE"
   logical={**signal,"horizon":horizon,"end_date":end_date,"evaluation_contract":CONTRACT_ID,"evaluation_basis":EVALUATION_BASIS,"evaluation_revision":1,"status":status}
   rows.append({**logical,"outcome_identity":digest({k:logical[k] for k in ("signal_run_id","security_id","episode_id","horizon","end_date","evaluation_contract","evaluation_revision")})})
 summary={status:sum(row["status"]==status for row in rows) for status in ("NOT_DUE","DUE_UNMATERIALIZED")}
 logical={"contract_id":CONTRACT_ID,"evaluation_basis":EVALUATION_BASIS,"as_of_data_date":as_of,"horizons":list(HORIZONS),"episode_count":len(first_episode_signals(observations)),"summary":summary,"rows":rows}
 return {**logical,"plan_digest":digest(logical)}

def seal_plan(path,plan:dict)->None:atomic_write(path,plan)
