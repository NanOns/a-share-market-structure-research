"""Verify P12-05 diagnostic replay, baseline, and ablation evidence."""
from __future__ import annotations
import hashlib,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/p12_05/p12_05_stage_gate.json'
def load(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p):h=hashlib.sha256();h.update(p.read_bytes());return h.hexdigest()
def main():
 prior=load(Path('reports/p12_04/p12_04_stage_gate.json'));replay=load(Path('reports/p12_05/replay_evaluation.json'));source=load(Path('reports/p12_02/three_day_factor_replay.json'))
 equal=all(all(len(v)==x['equal_count_baselines']['sample_count'] for v in x['equal_count_baselines'].values() if isinstance(v,list)) for x in source['dates'])
 checks={'p12_04_accepted':prior['acceptance_result']=='DEGRADED_PASS','ordered_preregistered_partitions':list(replay['summary'])==['2026-03-31','2026-06-30','2026-09-14'] and replay['preregistration']['embargo_sessions']==10,'four_equal_count_baselines':equal and all(len(x['baseline_median_fret'])==4 for x in replay['summary'].values()),'horizon_end_anchor_contract':replay['evaluation_basis']=='HORIZON_END_TDX_AFFINE_QFQ_V1','data_gap_retained':replay['summary']['2026-06-30']['status_counts'].get('DATA_GAP')==1,'locked_observation_not_due':replay['summary']['2026-09-14']['status_counts'].get('NOT_DUE')==900,'ablations_recorded':set(replay['ablation'])=={'loo','position_gate_by_date','freshness'},'reconstructed_mode_explicit':replay['history_basis']=='RECONSTRUCTED_CURRENT_MEMBERSHIP','effect_claim_withheld':replay['effect_status']=='EFFECT_OBSERVATION_PENDING'}
 result={'stage_contract':'P12-05_REPLAY_V3_3_ACCEPTANCE_V1','captured_at_utc':datetime.now(timezone.utc).isoformat(),'consulted_spec_sha256':sha(ROOT/'docs/V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md'),'input_identity':replay['input_identity'],'logical_result_sha256':replay['logical_result_sha256'],'checks':checks,'acceptance_result':'DEGRADED_PASS' if all(checks.values()) else 'BLOCKED','acceptance_scope':'Implementation and reconstructed diagnostic replay with equal-count baselines and ablations; PIT and effect validity excluded','effect_status':'EFFECT_OBSERVATION_PENDING','next_stage':'P12-06_BUNDLE_V3_3' if all(checks.values()) else 'P12-05_REPAIR'}
 OUT.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=OUT.parent)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as s:json.dump(result,s,ensure_ascii=False,indent=2);s.write('\n');s.flush();os.fsync(s.fileno())
  os.replace(tmp,OUT)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 if result['acceptance_result']=='BLOCKED':raise RuntimeError('P12-05 blocked')
 print(OUT)
if __name__=='__main__':main()
