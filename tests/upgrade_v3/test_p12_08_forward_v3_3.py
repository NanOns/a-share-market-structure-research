import copy,json
from pathlib import Path
from workbench_analysis.forward_v3_3 import build_observation,report,seal,transitions

def active(day="2026-09-14",digest="a"):
 return {"identity":{"trade_date":day,"research_run_id":"run-"+day},"output_digest":digest}
def rows():return [{"security_id":"SH.1","primary_category":"LAUNCH_CONFIRM","matched_categories":["LAUNCH_CONFIRM"],"selection_mode":"INDEPENDENT","rank_status":"QUALIFIED_UNRANKED"},{"security_id":"SZ.2","primary_category":"TREND_CONTINUE","matched_categories":["TREND_CONTINUE"],"selection_mode":"SUPPORTED","rank_status":"SCORED"}]

def test_observation_is_deterministic_and_sealed_idempotently(tmp_path):
 obs=build_observation(active(),rows(),{"SH.1":{"sector_relations_tested":2},"SZ.2":{"sector_relations_tested":7}})
 assert build_observation(active(),rows(),{"SH.1":{"sector_relations_tested":2},"SZ.2":{"sector_relations_tested":7}})==obs
 assert seal(tmp_path,obs)["reused"] is False and seal(tmp_path,obs)["reused"] is True

def test_transition_reports_entry_exit_category_mode_and_continuation():
 first=build_observation(active(),rows());changed=rows();changed[0]["primary_category"]="RECOVERY_TURN";changed[1]["selection_mode"]="INDEPENDENT";changed.append({"security_id":"BJ.3","primary_category":"STRONG_PULLBACK","matched_categories":[],"selection_mode":"INDEPENDENT","rank_status":"SCORED"})
 second=build_observation(active("2026-09-15","b"),changed)
 counts=transitions(first,second)["counts"]
 assert counts=={"ENTERED":1,"CATEGORY_CHANGED":1,"MODE_CHANGED":1}

def test_report_stays_pending_below_preregistered_gate_and_stratifies_relations():
 obs=build_observation(active(),rows(),{"SH.1":{"sector_relations_tested":2},"SZ.2":{"sector_relations_tested":7}});result=report([obs])
 assert result["status"]=="EFFECT_OBSERVATION_PENDING" and result["gate"]["signal_days"]==1
 assert result["gate"]["sealed_independent_episodes"]==2
 assert result["gate"]["candidate_episode_upper_bound"]==2
 assert result["gate"]["episode_identity_status"]=="AVAILABLE"
 assert result["relationship_band_by_mode"]=={"1-2":{"INDEPENDENT":1},"6+":{"SUPPORTED":1}}

def test_report_counts_generated_episode_identities():
 obs=build_observation(active(),rows());result=report([obs])
 assert result["gate"]["sealed_independent_episodes"]==2
 assert result["gate"]["episode_identity_status"]=="AVAILABLE"

def test_episode_identity_continues_until_exit_or_category_change():
 first=build_observation(active(),rows())
 second=build_observation(active("2026-09-15","b"),rows(),previous=first)
 assert second["rows"][0]["episode_id"]==first["rows"][0]["episode_id"]
 changed=copy.deepcopy(rows());changed[0]["primary_category"]="RECOVERY_TURN"
 third=build_observation(active("2026-09-16","c"),changed,previous=second)
 assert third["rows"][0]["episode_id"]!=second["rows"][0]["episode_id"]
 assert third["rows"][0]["episode_started_on"]=="2026-09-16"

def test_digest_changes_when_signal_fact_changes():
 first=build_observation(active(),rows());changed=copy.deepcopy(rows());changed[0]["selection_mode"]="SUPPORTED"
 assert build_observation(active(),changed)["observation_digest"]!=first["observation_digest"]
