from __future__ import annotations
import hashlib,json
import pandas as pd

CONTRACT_VERSION="r4-forward-observation-contract-v1.1"
OBSERVATION_SCHEMA_VERSION="forward-observation-schema-v1.1"
OUTCOME_SCHEMA_VERSION="forward-outcome-schema-v1.1"
FORWARD_ONLY=True;NO_HISTORICAL_BACKFILL=True;NO_FUTURE_BACKWRITE=True;OBSERVATION_IS_IMMUTABLE=True;OUTCOME_IS_APPEND_ONLY=True;OBSERVATION_CANNOT_MUTATE_MODEL=True
MATERIAL_FIELDS=("shadow_research_band","steady_queue_tier","pullback_queue_tier","breakout_queue_tier","leader_queue_tier","early_queue_tier")
STATES=("BASELINE","NEW","PERSISTENT","EXITED","REENTERED","STRUCTURE_CHANGED","DATA_UNAVAILABLE","SOURCE_REVISED")
OUTCOME_FIELDS=("security_id","signal_observation_id","signal_date","horizon","target_trading_date","entry_reference_price","target_close","forward_return","max_high_return","max_drawdown","outcome_status","outcome_observed_at")
def _same_value(left,right):
 try:
  if bool(pd.isna(left)) and bool(pd.isna(right)):return True
 except (TypeError,ValueError):pass
 return left==right
def changed_fields(previous,current):return [f for f in MATERIAL_FIELDS if not _same_value(previous.get(f),current.get(f))]
def transition(previous,current,ever_seen=False,same_cutoff_revision=False,data_available=True,model_identity_same=True):
 if not data_available:return "DATA_UNAVAILABLE"
 if same_cutoff_revision or not model_identity_same:return "SOURCE_REVISED"
 if previous is None and current is not None:return "REENTERED" if ever_seen else "NEW"
 if previous is not None and current is None:return "EXITED"
 if previous is not None and current is not None:
  if previous.get("candidate_state")=="EXITED":return "REENTERED"
  return "STRUCTURE_CHANGED" if changed_fields(previous,current) else "PERSISTENT"
 return "DATA_UNAVAILABLE"
def observation_identity(payload):return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def replay_status(existing_id,existing_hash,expected_id,actual_hash):
 return "VERIFIED_NO_NEW_FORWARD_OBSERVATION" if existing_id==expected_id and existing_hash==actual_hash else "CONFLICT_BLOCKED"
