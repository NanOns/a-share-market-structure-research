"""Declared synthetic D2 vectors; expected events are independently declared."""
from copy import deepcopy
from scripts.freeze_v4_10_contract import fixture
from scripts.v4_10_r1_1_fixtures import adapt_r1_input,refresh
from src.v4.confirmation import digest,detect_confirmation
from src.v4.confirmation_d2_bridge import engineering_d2_publication
from src.v4.confirmation_events import freeze_prior_session,state_events
from scripts.v4_11_candidate_inputs_r1 import projection,positive_values

def state_input(stage,*,session=22,prior=None,scenario='STRONG_PULLBACK',delta=0,damage=False):
    old=fixture('STOCK',stage);old.update(session_index=session,entity_id='synthetic-entity',delta3=delta,core_price_damage='TRUE' if damage else 'FALSE',scenario=dict(value=scenario,status='KNOWN'))
    x=adapt_r1_input(old)
    if prior:
        x['prior_state']=deepcopy(prior);x['prior_state_binding']=dict(publication_id=prior['publication_id'],payload_digest=digest(prior),ledger_id='SYNTHETIC_ENGINEERING_LEDGER')
        f=x['input_provenance']['frozen_invalidation'];f['source_field_payload'].update(episode_id=prior['episode_id'],invalidation_contract_id=prior['invalidation_contract_id']);f['source_output_digest']=digest(f['source_field_payload'])
    return refresh(x)

def from_confirmation(fact,*,prior=None):
    if fact['mode']!='SYNTHETIC_ENGINEERING_VECTOR':raise ValueError('EXTERNAL_ACCEPTANCE_REQUIRED_FOR_REAL_D0_D2_ADOPTION')
    x=state_input('CONFIRMED' if fact['confirmation_status']=='TRUE' else 'NONE',prior=prior,scenario=fact['primary_scenario'] or 'NONE')
    f=x['input_provenance']['CONFIRMED'];f.update(value=fact['confirmation_status'],quality='UNKNOWN' if fact['confirmation_status']=='UNKNOWN' else 'KNOWN',publication_id='SYNTHETIC_FACTS:'+fact['publication_id'])
    f['source_field_payload'].update(value=fact['confirmation_status'],confirmation_row_digest=digest(fact));f['source_output_digest']=digest(f['source_field_payload'])
    x['input_publication_ids']=sorted(set(x['input_publication_ids']+[f['publication_id']]))
    return refresh(x)

def event_vector(prior_stage='NONE',current_stage='CONFIRMED',*,prior_scenario='STRONG_PULLBACK',current_scenario='STRONG_PULLBACK',delta=0,damage=False,prior=None):
    old=engineering_d2_publication([state_input(prior_stage,session=21,scenario=prior_scenario)]) if prior is None else prior
    previous=old['rows'][0] if old['rows'] else None
    x=state_input(current_stage,prior=previous,scenario=current_scenario,delta=delta,damage=damage)
    new=engineering_d2_publication([x])
    frozen=freeze_prior_session(target_date='2026-09-30',prior_date='2026-09-29',calendar_publication_id=x['calendar_publication_id'],
        rows=old['rows'],source_binding=old,scope='SYNTHETIC_ENGINEERING_ONLY',calendar_manifest=x['synthetic_calendar_manifest'])
    return old,new,frozen,state_events(new,frozen)

# Expectations are literal contract assertions, never generated from runtime.
EXPECTED={
 'NONE_TO_CONFIRMED':'NEW_CONFIRMED','SEED_TO_CONFIRMED':'NEW_CONFIRMED','PREWATCH_TO_CONFIRMED':'NEW_CONFIRMED',
 'PERSISTENT_CONFIRMED':'PERSISTENT_CONFIRMED','SAME_DAY_R1_R2_R3_NEW_CONFIRMED':'NEW_CONFIRMED',
 'RECONFIRMED':'RECONFIRMED','SCENARIO_UPGRADED':'SCENARIO_UPGRADED','SCENARIO_CHANGED_NOT_UPGRADED':'SCENARIO_CHANGED',
 'CONFIRMATION_WEAKENED':'CONFIRMATION_WEAKENED','HARD_INVALIDATION_WINS':'CONFIRMATION_INVALIDATED',
 'REQUIRED_FACT_UNKNOWN':'UNKNOWN','AMOUNT_A_DISABLED':'UNKNOWN','MULTI_SCENARIO_DEDUP':'ONE_CANONICAL_ROW_ALL_LEGACY_MATCHES_RETAINED',
 'PRODUCER_MISMATCH':'PRODUCER_MISMATCH','PARAMETER_MISMATCH':'PARAMETER_MISMATCH','PUBLICATION_MISMATCH':'PUBLICATION_MISMATCH',
 'FUTURE_TIMESTAMP_REJECTED':'FUTURE_TIMESTAMP_REJECTED','SAME_DAY_FEEDBACK_REJECTED':'SAME_DAY_FEEDBACK_REJECTED','NO_SYMBOL':'PASS'}
