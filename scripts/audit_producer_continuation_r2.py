"""Current accepted-day research replay and candidate UI/admission evidence."""
import sys
import json
import hashlib
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.producer_bootstrap_v1 import capture_daily_sources,build_review_and_display_candidates
from workbench_analysis.operational_daily_storage_v1 import atomic_json


def main():
    out=ROOT/'docs/evidence/producer_continuation_r2_20261010'
    names=['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json']
    before={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in names}
    head=json.loads((ROOT/names[0]).read_bytes());day=head['accepted_trade_date'];binding=ref(ROOT,ROOT/names[0])
    capture=capture_daily_sources(ROOT,day,head['source_registry'][day]['freeze'],research_replay=True)
    result=build_review_and_display_candidates(ROOT,day,binding,dict(candidate=capture),research_replay=True)
    assert all(result[k]['status']=='CANDIDATE_PRODUCED' for k in ('sector','full_state','strict_source')),result
    sector=json.loads(checked(ROOT,result['sector']['candidate']).read_bytes())
    state=json.loads(checked(ROOT,result['full_state']['candidate']).read_bytes())
    strict=json.loads(checked(ROOT,result['strict_source']['candidate']).read_bytes())
    counts={k:dict(Counter(r[k] for r in sector['rows'])) for k in ('CONFIRMED','WARM')}
    sample=[r for r in sector['rows'] if r['sector_id'] in ('INDUSTRY:T0706','THEME:880904')]
    positive=[r for r in sector['rows'] if r['CONFIRMED']=='TRUE'][:1]
    atomic_json(ROOT,out/'REAL_1009_RESEARCH_CANDIDATES.json',dict(bindings=result,sector_counts=counts,
        sample=sample,positive_counterpart=positive,state_count=state['signal_count'],universe_count=state['universe_count'],
        actual_state_frozen_at=state['signals'][0]['frozen_at_candidate'],
        strict_review_status=strict['review_readiness'],source_gaps=strict['source_gaps'],
        evidence_class='RECONSTRUCTED_RESEARCH_ONLY',production=False))
    after={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in names};assert before==after
    atomic_json(ROOT,out/'PROTECTED_HEAD_READBACK.json',dict(before=before,after=after,unchanged=True))
    # A review request describes gates; it neither fabricates a grant nor writes
    # an accepted Owner. Existing strict verifier/writer stay independent.
    atomic_json(ROOT,out/'PER_CAPABILITY_ADMISSION_REQUESTS.json',dict(contract_id='PRODUCER_SCOPED_ADMISSION_REQUESTS_V2',
        source_candidate=dict(binding=result['strict_source']['candidate'],status=strict['review_readiness'],
            required_review=['Actual new T0 original clocks','Frozen membership/raw/State windows','Full universe reconciliation']),
        sector_diagnostic=dict(binding=result['sector']['candidate'],scope='CANDIDATE_RESEARCH_DISPLAY',
            revised_identifier_contract='LEGACY_VALID_MEMBER_DIAGNOSTIC_CORRECTION_V2',formal_A05='NOT_GRANTED',
            required_review=['Compare frozen old regex with corrected diagnostic','Dated lifecycle mapping','Unchanged R5 qualification AST']),
        candidate_display=dict(contract=ref(ROOT,ROOT/'config/operational_candidate_display_contract_v2.json'),
            status='ENGINEERING_USER_AUTHORIZED_SCOPED_READ',formal_maturity_consumer=False),
        cohort_formal=dict(status='NOT_GRANTED',required=['Independently accepted full State source','Exact model/window/membership authority',
            'Real episode/event identity and benchmark','Independent writer grant','Owner admission and Head CAS']),
        FEP=dict(status='PRODUCTION_HOLD'),external_acceptance='NOT_GRANTED'))
    print(json.dumps(dict(sector_counts=counts,signal_count=state['signal_count'],strict_review_status=strict['review_readiness'],heads_unchanged=True)))


if __name__=='__main__':main()
