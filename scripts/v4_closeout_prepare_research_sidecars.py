"""Exercise current optional research producers from completed immutable Owners."""
import json
from pathlib import Path
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.producer_bootstrap_v1 import build_review_and_display_candidates
from scripts.r4_r3_consumer_trace import ConsumerTrace

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def main():
    report=OUT/'RESEARCH_SIDECAR_PREPARATION_R6_R1.json'
    if report.exists():raise ValueError('PRESERVE_PRIOR_RESEARCH_SIDECAR_PREPARATION')
    preparation=json.loads((OUT/'SEALED_METADATA_CONSERVATION_R6_R1.json').read_bytes());binding=preparation['candidate'];candidate=json.loads(checked(ROOT,binding).read_bytes());day=candidate['accepted_trade_date']
    heads={n:(ROOT/'data/v4'/n).read_bytes() for n in ('V4_DATA_ACCEPTED_HEAD.json','V4_OPERATIONAL_RESEARCH_HEAD.json')}
    trace=ConsumerTrace(OUT/'RESEARCH_SIDECAR_EXACT56_TRACE_R6_R1.json','Current optional research-sidecar producers; existing immutable Owners only, no first capture')
    trace.start()
    try:result=build_review_and_display_candidates(ROOT,day,binding,dict(status='HISTORICAL_FIRST_CAPTURE_NOT_VERIFIABLE'),research_replay=True)
    finally:trace.close()
    if any((ROOT/'data/v4'/n).read_bytes()!=raw for n,raw in heads.items()):raise ValueError('HEAD_CHANGED_BY_RESEARCH_SIDECAR')
    receipt=dict(contract_id='V4_REAL_CURRENT_RESEARCH_SIDECAR_PREPARATION_R1',acceptance='RESEARCH_ONLY_PENDING_READBACK',candidate=binding,T0=day,
        result=result,producer_index=ref(ROOT,ROOT/'data/v4/producer_candidate_index_v2.json'),publication=False,
        first_capture='HISTORICAL_FIRST_AVAILABLE_NOT_VERIFIABLE',formal_cohort_enrollment=False,core_profile_sector_focus_period_math_repeated=False)
    atomic_json(OUT,report,receipt);print(json.dumps({k:v.get('status',v.get('formal_status')) for k,v in result.items() if isinstance(v,dict)}),flush=True)

if __name__=='__main__':main()
