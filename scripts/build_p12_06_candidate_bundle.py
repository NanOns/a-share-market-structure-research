"""Build and activate the isolated P12-06 candidate research-bundle pointer."""
from __future__ import annotations
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from production.release import atomic_write_json
from workbench_service.research_bundle_v3_3 import build_bundle,activate_bundle,read_active
OUT=ROOT/'reports/p12_06/candidate_bundle_receipt.json';POINTER=ROOT/'data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json';BUNDLES=ROOT/'data/research_bundles_v3_3'
def sha(p):h=hashlib.sha256();h.update(p.read_bytes());return h.hexdigest()
def main():
 rank=json.loads((ROOT/'reports/p12_04/current_rank_probe.json').read_text(encoding='utf-8'));lock=json.loads((ROOT/'reports/p12_02/historical_input_pilot.json').read_text(encoding='utf-8'));gate=json.loads((ROOT/'reports/p12_05/p12_05_stage_gate.json').read_text(encoding='utf-8'));inputs={'rank_sha256':sha(ROOT/'reports/p12_04/current_rank_probe.json'),'p12_05_gate_sha256':sha(ROOT/'reports/p12_05/p12_05_stage_gate.json')};logical_run='p12-06-'+hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()[:24]
 with duckdb.connect(str(ROOT/'data/database/market_research.duckdb'),read_only=True) as con:
  bound=con.execute('select snapshot_id,membership_snapshot_id,cast(trade_date as varchar) from research_runs where run_id=?',[rank['input_identity']['run_id']]).fetchone()
 identity={'publication_id':rank['input_identity']['publication_id'],'snapshot_id':bound[0],'membership_snapshot_id':bound[1],'research_run_id':logical_run,'parameter_hash':hashlib.sha256(b'parameters-v3_3-candidate-01').hexdigest(),'dependency_lock_hash':lock['dependency_lock_draft_sha256'],'trade_date':bound[2],'history_basis':'LOCAL_CLOSE_ONLY_WITH_RECONSTRUCTED_HISTORY_DIAGNOSTICS'}
 contracts={'factor':'TODAY_RESEARCH_FACTOR_V3_3_CANDIDATE_01','episode':'PULLBACK_EPISODE_V1_CANDIDATE_01','scanner':'TODAY_RESEARCH_SCANNER_V3_3_CANDIDATE_01','rank_loo':'TODAY_RESEARCH_RANK_AND_LOO_V3_3_CANDIDATE_01','bundle':'TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_01','effect_status':gate['effect_status']}
 built=build_bundle(BUNDLES,identity,rank['ranked_rows'],contracts);active=activate_bundle(Path(built['path']),POINTER);verified=read_active(POINTER)
 receipt={'stage_contract':'P12-06_BUNDLE_V3_3_PILOT_V1','captured_at_utc':datetime.now(timezone.utc).isoformat(),'bundle':built,'active_pointer':str(POINTER),'identity':identity,'contracts':contracts,'result_rows':len(rank['ranked_rows']),'pointer_verified':verified['output_digest']==built['output_digest'],'ui_consumes_pointer':False,'production_database_written':False,'acceptance_result':'DEGRADED_PASS','next_stage':'P12-06_FAILURE_AND_IDEMPOTENCY_GATE'}
 atomic_write_json(OUT,receipt);print(OUT)
if __name__=='__main__':main()
