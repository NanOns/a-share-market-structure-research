"""Read-only 10/09 replay, lightweight engineering evidence; no future run."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT))
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.v4_14_replay_io import publish
from workbench_analysis.producer_bootstrap_v1 import capture_daily_sources,produce_daily_state,produce_daily_sector

OUT='docs/evidence/producer_bootstrap_r1_20261010'


def main():
    heads=['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json']
    before={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in heads}
    head=json.loads((ROOT/heads[0]).read_bytes());day='2026-10-09'
    binding=ref(ROOT,ROOT/heads[0])
    capture=capture_daily_sources(ROOT,day,head['source_registry'][day]['freeze'],research_replay=True)
    source=json.loads(checked(ROOT,capture).read_bytes())
    state_binding=produce_daily_state(ROOT,day,binding)
    state=json.loads(checked(ROOT,state_binding).read_bytes())
    sector_binding=produce_daily_sector(ROOT,day,binding)
    sector=json.loads(checked(ROOT,sector_binding).read_bytes())
    def write(name,value):
        from workbench_analysis.operational_daily_storage_v1 import atomic_json
        from workbench_analysis.v4_14_replay_io import digest
        target=ROOT/OUT/name
        if target.exists():
            old=json.loads(target.read_bytes())
            if old!=value:publish(ROOT,f'{OUT}/revisions/{digest(old)}/{name}',old)
        atomic_json(ROOT,target,value)
    write('W1_REAL_1009_CANDIDATE_REPLAY.json',dict(candidate=capture,evidence_class=source['evidence_class'],
        gaps=source['gaps'],source_count=len(source['sources']),security_count=len(source['security_ids']),
        sector_count=len(source['sector_ids']),production=False))
    write('W1_NEXT_T0_CAPTURE_READINESS.json',dict(code_candidate_ready=True,source_capture_requires_grant=False,
        real_future_T0_test='NOT_RUN',formal_authority='INDEPENDENT_REVIEW_REQUIRED',
        loaded_service='NOT_RESTARTED_RUNTIME_LOAD_NOT_PROVEN',request_time_gap='Original existing network receipts have no exact requested_at; retained null',
        scope_gap='Captured security scope is predecessor active universe; new identities require dated identity admission'))
    signals=state['signals']
    write('W3_FULL_UNIVERSE_ELIGIBILITY_RECONCILIATION.json',dict(candidate=state_binding,
        universe_count=state['universe_count'],signal_count=len(signals),missing_state_count=state['missing_state_count'],
        research_eligible_count=state['research_eligible_count'],research_ineligible_count=sum(not r['research_eligible'] for r in signals),
        identity_unique=len({r['signal_id'] for r in signals})==len(signals),
        all_excluded_reasoned=all(r['research_exclusion_reason'] for r in signals if not r['research_eligible']),
        formal_eligible_count=0,observed_count=None,matured_count=None,evidence_class=state['evidence_class'],
        source=state['source'],membership=state['membership'],sample=signals[:4]))
    from collections import Counter
    counts={field:dict(Counter(r[field] for r in sector['rows'])) for field in ('CONFIRMED','WARM')}
    sample=[r for r in sector['rows'] if r['sector_id'] in ('INDUSTRY:T0706','THEME:880904')]
    write('W2_USER_VISIBLE_OPERATIONAL_RESEARCH_SAMPLE.json',dict(candidate=sector_binding,
        trade_date=day,rows=sample,scope='RECONSTRUCTED_RESEARCH_ONLY',production=False,
        warning='All exact legacy qualification results FALSE because frozen identifier regex does not match ordinary source identifiers; independent audit required',
        counts=counts,formal_consumer_enabled=False))
    write('W2_FORMAL_VS_OPERATIONAL_FIELD_MATRIX.json',dict(counts=counts,fields={
        'CONFIRMED':dict(candidate='COMPUTED_FALSE_EXACT_LEGACY_IDENTIFIER',formal='NOT_GRANTED'),
        'WARM':dict(candidate='COMPUTED_FALSE_EXACT_LEGACY_IDENTIFIER',formal='NOT_GRANTED'),
        'frozen_invalidation':dict(candidate='NO_PRIOR_EPISODE',mechanism='create_episode/evaluate_invalidation'),
        'episode_invalidation_contract_id':dict(candidate=None,mechanism='Frozen at genuine genesis'),
        'followup_complete':dict(candidate='UNKNOWN',mechanism='PENDING until actual calendar horizon; receipt required'),
        'scenario':dict(candidate='UNKNOWN',mechanism='Genesis priority binding; no fabricated prior episode')},
        engineering_gate='PARTIAL_NOT_BUSINESS_ACCEPTED',reason='Independent frozen valid-member regex audit and exact rank/window producer remain required'))
    after={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in heads}
    assert before==after
    write('PROTECTED_HEAD_READBACK.json',dict(before=before,after=after,unchanged=True,production_restart=False))
    write('STAGE_RESULT.json',dict(task='V4-PRODUCER-BOOTSTRAP-AND-PROGRESS-RECOVERY-R1-20261010',
        W1='CANDIDATE_ENGINEERING_IMPLEMENTED_WITH_RECORDED_SOURCE_GAPS',
        W2='PARTIAL_INDEPENDENT_ALGORITHM_AUDIT_REQUIRED',W3='FULL_RESEARCH_CANDIDATE_IMPLEMENTED',
        W4='PRODUCTION_HOLD',W5='DISPLAY_CONTRACT_PROPOSAL_NO_FORMAL_CUTOVER',
        W6='GIT_AND_LIGHTWEIGHT_ARCHIVE_PENDING',external_acceptance='NOT_GRANTED',
        next_stage='INDEPENDENT_SCOPED_REVIEW_AND_REAL_T0_CAPTURE_WHEN_OBSERVED'))
    print(json.dumps(dict(sector_counts=counts,universe_count=state['universe_count'],signal_count=len(signals),
        research_eligible_count=state['research_eligible_count'],heads_unchanged=True),ensure_ascii=False))


if __name__=='__main__':main()
