"""Materialize due P12 outcomes with a common horizon-end affine anchor."""
from __future__ import annotations
from collections import defaultdict
from typing import Any,Iterable

from adjustment.tdx_adjustment import ADJUSTMENT_VERSION,build_affine_factors
from workbench_analysis.forward_outcome_v3_3 import EVALUATION_BASIS
from workbench_analysis.forward_v3_3 import digest

CONTRACT_ID="TODAY_RESEARCH_FORWARD_OUTCOME_MATERIALIZED_V3_3_CANDIDATE_01"

def materialize(plan:dict,bars:Iterable[dict]=(),events_by_security:dict[str,list]|None=None,*,evaluation_source_hash:str="NOT_CONSUMED_NOT_DUE",adjustment_version:str=ADJUSTMENT_VERSION)->dict:
 events_by_security=events_by_security or {};grouped=defaultdict(dict)
 for bar in bars:grouped[str(bar["security_id"])][str(bar["trade_date"])[:10]]=bar
 output=[]
 for item in plan["rows"]:
  logical={**item,"materialization_contract":CONTRACT_ID,"evaluation_source_hash":evaluation_source_hash,"adjustment_version":adjustment_version}
  if item["status"]=="NOT_DUE":output.append(logical);continue
  sid=item["security_id"];signal=item["signal_date"];end=item.get("end_date");stock=grouped.get(sid,{})
  ordered=sorted(day for day in stock if day<=end and stock[day].get("has_actual_bar",True))
  if signal not in stock or end not in stock or signal not in ordered:
   output.append({**logical,"status":"DATA_GAP","reason":"SIGNAL_OR_END_BAR_MISSING"});continue
  start=ordered.index(signal);window=ordered[start+1:]
  if len(window)!=item["horizon"] or window[-1:]!=[end]:
   output.append({**logical,"status":"DATA_GAP","reason":"HORIZON_WINDOW_INCOMPLETE"});continue
  required=[signal,*window]
  if any(any(stock[day].get(field) is None for field in ("raw_high","raw_low","raw_close")) for day in required):
   output.append({**logical,"status":"DATA_GAP","reason":"OHLC_MISSING"});continue
  dates=[int(day.replace("-","")) for day in ordered];effective=[event for event in events_by_security.get(sid,[]) if event.ex_day<=int(end.replace("-",""))]
  factors=build_affine_factors(dates,effective);base=float(factors[int(signal.replace("-",""))].qfq_price(stock[signal]["raw_close"]))
  if base<=0:
   output.append({**logical,"status":"DATA_GAP","reason":"NON_POSITIVE_SIGNAL_CLOSE"});continue
  end_close=float(factors[int(end.replace("-",""))].qfq_price(stock[end]["raw_close"]))
  highs=[float(factors[int(day.replace("-",""))].qfq_price(stock[day]["raw_high"])) for day in window]
  lows=[float(factors[int(day.replace("-",""))].qfq_price(stock[day]["raw_low"])) for day in window]
  metrics={"status":"OBSERVED","anchor":end,"fret":end_close/base-1,"mfe":max(highs)/base-1,"mae":min(lows)/base-1}
  identity={k:logical.get(k) for k in ("signal_run_id","security_id","episode_id","horizon","end_date","evaluation_contract","evaluation_source_hash","adjustment_version","evaluation_revision")}
  output.append({**logical,**metrics,"materialized_identity":digest(identity)})
 summary={status:sum(row["status"]==status for row in output) for status in ("NOT_DUE","OBSERVED","DATA_GAP")}
 body={"contract_id":CONTRACT_ID,"evaluation_basis":EVALUATION_BASIS,"plan_digest":plan["plan_digest"],"evaluation_source_hash":evaluation_source_hash,"adjustment_version":adjustment_version,"summary":summary,"rows":output}
 return {**body,"result_digest":digest(body)}
