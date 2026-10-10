"""Independent expected values plus original D2 synthetic vectors. No authority."""
from immediate_r3_common import *
import sys,copy,importlib.util
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from sector.d2_admission_candidate_r4 import extract,freeze_episode,observe_episode
from src.v4.research_state import reduce_state
from scripts.v4_10_r1_2_fixtures import adapt_r1_2_input
from scripts.freeze_v4_10_contract import fixture,with_prior
B=ROOT/'docs/evidence/v4_current_snapshot_r4_20261010/02_B_SECTOR'

def main():
    actual=load(B/'B_SECTOR_READINESS_CANDIDATE_OUTPUT.json')['rows']
    oracle=B/'B_SECTOR_ORACLE.py';spec=importlib.util.spec_from_file_location('oracle',oracle);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    inputs=load(B/'B_SECTOR_READINESS_CANDIDATE_INPUT.json')
    expected=[module.reference(r) for r in inputs['rows']]
    differences=[dict(entity_id=r['entity_id'],field=k,expected=v,actual=r.get(k)) for r,e in zip(actual,expected) for k,v in e.items() if r.get(k)!=v]
    write(B/'B_SECTOR_ORACLE_OUTPUT.json',dict(source_binding=inputs['source_binding'],rows=expected))
    results=[]
    def check(name,actual,expected):results.append(dict(case=name,actual=actual,expected=expected,pass_result=actual==expected))
    def rejects(name,call,expected):
        try:call();value='NO_ERROR'
        except ValueError as exc:value=str(exc)
        check(name,value,expected)
    base=inputs['rows'][0];source=inputs['source_binding'];cutoff='2026-10-09T23:59:59+08:00'
    def run(row=base,**kwargs):return extract(row,source_binding=source,cutoff=cutoff,**kwargs)
    wrong=copy.deepcopy(base);wrong['entity_type']='STOCK';rejects('wrong_entity',lambda:run(wrong),'SECTOR_ENTITY_REQUIRED')
    wrong=copy.deepcopy(base);wrong['member_ids'].append(wrong['member_ids'][0]);rejects('duplicate_members',lambda:run(wrong),'UNIQUE_MEMBER_DENOMINATOR_REQUIRED')
    rejects('naive_cutoff',lambda:extract(base,source_binding=source,cutoff='2026-10-09T23:00:00'),'AWARE_FIRST_AVAILABLE_REQUIRED')
    prior=dict(entity_id=base['sector_id'],trade_date='2026-09-30',episode_id='ep',invalidation_contract_sha256='a'*64)
    rejects('nonconsecutive_prior_holiday',lambda:run(prior=prior,sessions=['2026-09-30','2026-10-08','2026-10-09']),'EXACT_PRIOR_SESSION_REQUIRED')
    receipt=dict(source_sha256='a'*64,producer_contract_id='ISOLATED_TEST',parameter_set_id='TEST_R1',first_available='2026-10-09T20:00:00+08:00',trade_date='2026-10-09',value='TRUE',quality='ACCEPTED',window_identity='TEST_T0')
    check('candidate_positive_no_activation',run(upstream={'CONFIRMED':receipt})['upstream']['CONFIRMED']['value'],'TRUE')
    for name,changes,reason in [('late_capture',{'first_available':'2026-10-10T00:00:00+08:00'},'FIRST_AVAILABLE_AFTER_CUTOFF'),('wrong_date',{'trade_date':'2026-10-08'},'WRONG_TIME_ROLE'),('quality_unknown',{'quality':'UNKNOWN'},'REQUIRED_QUALITY_UNAVAILABLE'),('unknown_not_false',{'value':'UNKNOWN'},'REQUIRED_VALUE_UNKNOWN'),('bool_not_tri',{'value':True},'INVALID_TRI_VALUE'),('wrong_sha',{'source_sha256':'bad'},'INVALID_PRODUCER_IDENTITY')]:
        check(name,run(upstream={'CONFIRMED':dict(receipt,**changes)})['upstream']['CONFIRMED']['reason'],reason)
    check('warm_amount_missing',run(upstream={'WARM':dict(receipt,amount_a_required=True,strict_h21_verified=False)})['upstream']['WARM']['reason'],'STRICT_AMOUNT_A_HISTORY_UNVERIFIABLE')
    check('followup_right_censor',run(upstream={'followup_complete':dict(receipt,right_censored=True)})['upstream']['followup_complete']['reason'],'DUE_OR_SETTLEMENT_OWNER_NOT_PRESENT')
    episode=freeze_episode(entity_id=base['sector_id'],trade_date='2026-10-08',member_ids=base['member_ids'],contract_binding=dict(contract_id='TEST_INVALIDATION',version='R1',sha256='a'*64),conditions={'damage':'TRUE'},first_available='2026-10-08T20:00:00+08:00')
    event=observe_episode(episode,trade_date='2026-10-09',session_index=21,invalidated=True)
    check('invalidated_no_same_day_reentry',event['reentry_allowed'],False)
    check('same_day_idempotence',observe_episode(episode,trade_date='2026-10-09',session_index=21,invalidated=True,previous=event),event)
    rejects('same_day_conflict',lambda:observe_episode(episode,trade_date='2026-10-09',session_index=21,invalidated=False,previous=event),'SAME_SESSION_CONFLICT')
    changed=copy.deepcopy(episode);changed['member_ids'].append('NEW');check('member_change_does_not_mutate_frozen_identity',episode['episode_id']==freeze_episode(entity_id=base['sector_id'],trade_date='2026-10-08',member_ids=base['member_ids'],contract_binding=dict(contract_id='TEST_INVALIDATION',version='R1',sha256='a'*64),conditions={'damage':'TRUE'},first_available='2026-10-08T20:00:00+08:00')['episode_id'],True)
    vectors=load('config/v4_10_machine_vectors_v1.json')['vectors'];count=0
    entered=reduce_state(adapt_r1_2_input(fixture('SECTOR','CONFIRMED')))
    damaged=with_prior(fixture('SECTOR','CONFIRMED'),entered);damaged['core_price_damage']='TRUE'
    exited=reduce_state(adapt_r1_2_input(damaged))
    check('original_D2_sector_hard_invalidation',[exited['maturity'],exited['validity'],exited['health']],['NONE','INVALIDATED','DAMAGED'])
    repeat=reduce_state(adapt_r1_2_input(with_prior(fixture('SECTOR','CONFIRMED'),exited)))
    check('original_D2_sector_same_day_reentry',[repeat['maturity'],'SAME_SESSION_REENTRY_FORBIDDEN' in repeat['transition_reasons']],['NONE',True])
    next_session=with_prior(fixture('SECTOR','CONFIRMED'),exited);next_session['session_index']=21
    resumed=reduce_state(adapt_r1_2_input(next_session))
    check('original_D2_sector_next_session_reentry',[resumed['maturity'],resumed['parent_episode_id']==exited['episode_id']],['CONFIRMED',True])
    for vector in vectors:
        if vector['input']['entity_type']!='SECTOR':continue
        count+=1
        try:
            result=reduce_state(adapt_r1_2_input(vector['input']))
            actual_error=None
        except ValueError as exc:actual_error=str(exc);result={}
        if vector['expected_error']:check('original_D2_'+vector['id'],actual_error,vector['expected_error'])
        else:check('original_D2_'+vector['id'],{k:result.get(k) for k in vector['expected']},vector['expected'])
    failed=[r for r in results if not r['pass_result']]
    write(B/'B_SECTOR_ORACLE_RESULT.json',dict(input=binding(B/'B_SECTOR_READINESS_CANDIDATE_INPUT.json'),output=binding(B/'B_SECTOR_READINESS_CANDIDATE_OUTPUT.json'),oracle=binding(oracle),code=binding('src/sector/d2_admission_candidate_r4.py'),current_real_comparison_count=len(expected)*len(expected[0]),current_real_differences=differences,synthetic_original_reducer_vectors=count,negative_and_boundary_results=results,failure_count=len(failed)+len(differences),evidence_class='INDEPENDENT_CURRENT_FIELD_EXTRACTION_PLUS_SYNTHETIC_ORIGINAL_REDUCER_BOUNDARIES',formal_acceptance=False))
    print(dict(real_rows=len(expected),cases=len(results),failures=len(failed)+len(differences)));return bool(failed or differences)

if __name__=='__main__':raise SystemExit(main())
