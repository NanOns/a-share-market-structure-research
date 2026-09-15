from decimal import Decimal
from adjustment.tdx_adjustment import XrxdEvent
from workbench_analysis.forward_outcome_materializer_v3_3 import materialize
from workbench_analysis.forward_outcome_v3_3 import plan_outcomes
from workbench_analysis.forward_v3_3 import build_observation

def observation():
 active={"identity":{"trade_date":"2026-09-14","research_run_id":"run-1"},"output_digest":"bundle-1"}
 return build_observation(active,[{"security_id":"SH.1","primary_category":"LAUNCH_CONFIRM","selection_mode":"INDEPENDENT"}])

def due_plan():return plan_outcomes([observation()],["2026-09-14","2026-09-15","2026-09-16","2026-09-17","2026-09-18","2026-09-21","2026-09-22","2026-09-23","2026-09-24","2026-09-25","2026-09-28"],"2026-09-15")

def test_not_due_rows_never_gain_return_fields():
 plan=plan_outcomes([observation()],["2026-09-14"],"2026-09-14");result=materialize(plan)
 assert result["summary"]=={"NOT_DUE":4,"OBSERVED":0,"SUSPENDED":0,"DELISTED":0,"DATA_GAP":0}

def test_missing_quote_is_classified_as_suspended():
 plan=plan_outcomes([observation()],['2026-09-14','2026-09-15'],'2026-09-15')
 due=next(row for row in plan['rows'] if row['status']=='DUE_UNMATERIALIZED')
 bars=[{'security_id':due['security_id'],'trade_date':'2026-09-14','raw_high':10,'raw_low':9,'raw_close':9.5,'has_actual_bar':True},{'security_id':due['security_id'],'trade_date':'2026-09-15','raw_high':None,'raw_low':None,'raw_close':None,'has_actual_bar':False,'no_quote_status':'SUSPENDED'}]
 result=materialize({'plan_digest':plan['plan_digest'],'rows':[due]},bars)
 assert result['rows'][0]['status']=='SUSPENDED'
 assert result['rows'][0]['reason']=='SUSPENDED_NO_QUOTE'
 assert all("fret" not in row for row in result["rows"])

def test_horizon_end_affine_anchor_handles_bonus_event():
 plan=due_plan();bars=[{"security_id":"SH.1","trade_date":"2026-09-14","raw_high":10,"raw_low":10,"raw_close":10},{"security_id":"SH.1","trade_date":"2026-09-15","raw_high":5.5,"raw_low":4.5,"raw_close":5}]
 event=XrxdEvent("SH.1",20260915,bonus_transfer_per_10=Decimal("10"))
 result=materialize(plan,bars,{"SH.1":[event]},evaluation_source_hash="source-1");row=result["rows"][0]
 assert row["status"]=="OBSERVED" and row["anchor"]=="2026-09-15"
 assert row["fret"]==0 and abs(row["mfe"]-.1)<1e-12 and abs(row["mae"]+.1)<1e-12
 assert row["materialized_identity"]

def test_due_missing_bar_is_data_gap_without_zero_metrics():
 result=materialize(due_plan(),[],evaluation_source_hash="source-1");row=result["rows"][0]
 assert row["status"]=="DATA_GAP" and row["reason"]=="SIGNAL_OR_END_BAR_MISSING"
 assert "fret" not in row
