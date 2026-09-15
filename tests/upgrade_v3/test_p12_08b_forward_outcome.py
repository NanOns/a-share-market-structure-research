from workbench_analysis.forward_outcome_v3_3 import first_episode_signals,plan_outcomes
from workbench_analysis.forward_v3_3 import build_observation

def active(day="2026-09-14",digest="a"):return {"identity":{"trade_date":day,"research_run_id":"run-"+day},"output_digest":digest}
def candidates():return [{"security_id":"SH.1","primary_category":"LAUNCH_CONFIRM","selection_mode":"INDEPENDENT"}]

def test_first_episode_signal_deduplicates_continuation_days():
 first=build_observation(active(),candidates());second=build_observation(active("2026-09-15","b"),candidates(),previous=first)
 signals=first_episode_signals([second,first])
 assert len(signals)==1 and signals[0]["signal_date"]=="2026-09-14"

def test_last_available_session_keeps_every_horizon_not_due():
 observation=build_observation(active(),candidates());plan=plan_outcomes([observation],["2026-09-11","2026-09-14"],"2026-09-14")
 assert plan["summary"]=={"NOT_DUE":4,"DUE_UNMATERIALIZED":0}
 assert all(row["end_date"] is None for row in plan["rows"])

def test_due_rows_are_exposed_without_fabricating_returns():
 observation=build_observation(active(),candidates());sessions=["2026-09-14","2026-09-15","2026-09-16","2026-09-17","2026-09-18","2026-09-21","2026-09-22","2026-09-23","2026-09-24","2026-09-25","2026-09-28"]
 plan=plan_outcomes([observation],sessions,"2026-09-18")
 assert [row["status"] for row in plan["rows"]]==["DUE_UNMATERIALIZED","DUE_UNMATERIALIZED","NOT_DUE","NOT_DUE"]
 assert all("fret" not in row and "mfe" not in row and "mae" not in row for row in plan["rows"])

def test_identity_changes_with_horizon_and_end_date():
 observation=build_observation(active(),candidates());sessions=["2026-09-14","2026-09-15","2026-09-16","2026-09-17","2026-09-18","2026-09-21","2026-09-22","2026-09-23","2026-09-24","2026-09-25","2026-09-28"]
 rows=plan_outcomes([observation],sessions,"2026-09-14")["rows"]
 assert len({row["outcome_identity"] for row in rows})==4
