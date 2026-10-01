"""Independent V0 golden producer, never a relabelled current reducer output."""
from scripts.v4_10_r1_1_fixtures import calendar
from src.v4.state_identity import digest,CANONICALIZATION

def emit_old_goldens():
    cal=calendar(False);cal_id='V4_10_INPUT:'+digest(cal)
    names=['SEED','PREWATCH','CONFIRMED','WARM','core_price_damage','frozen_invalidation','episode_invalidation_contract_id','risk','delta3','dq5','scenario','suspended','followup_complete']
    facts={n:dict(field=n,value='UNKNOWN',quality='UNKNOWN',status='NOT_IMPLEMENTED',producer_contract_id='OLD_V0_'+n,
        producer_parameter_set_id='OLD_PARAMETER_SET_V0',publication_id=None,source_output_digest=None,source_field_payload={},time_role='T',required=False,system_available_at=None) for n in names}
    inputs=['OLD_FACTS:V0_INDEPENDENT_GOLDEN_SOURCE'];out={}
    for key,episode,maturity,tracking in [('with_episode','OLD_AUTHORITY_EPISODE','PREWATCH','ACTIVE'),('without_episode',None,'NONE','CLOSED')]:
        row=dict(entity_id='fixture-entity',entity_type='STOCK',trade_date='2026-09-25',session_index=19,
            calendar_publication_id=cal_id,calendar_binding=dict(publication_id=cal_id,lineage_id=cal['lineage_id'],manifest_digest=digest(cal)),
            mode='ACCEPTED_FACT_INTERFACE',model_contract_id='OLD_RESEARCH_STATE_V0',parameter_set_id='OLD_PARAMETER_SET_V0',
            interface_contract_id='OLD_RESEARCH_STATE_INTERFACE_V0',canonicalization_contract_id=CANONICALIZATION,cutoff='2026-09-25T16:00:00+00:00',
            input_provenance=facts,input_publication_ids=inputs,input_publication_manifest_digest=digest(dict(input_publication_ids=inputs,fields=facts)),
            input_digest=digest('INDEPENDENT_V0_STATIC_GOLDEN_INPUT'),maturity=maturity,health='UNKNOWN',validity='UNKNOWN',tracking=tracking,
            scenario='NONE',scenario_status='UNKNOWN',state_freshness='STALE',final_eligibility='UNKNOWN',
            raw_qualification=dict(SEED='UNKNOWN',PREWATCH='UNKNOWN',CONFIRMED='UNKNOWN'),detector_statuses={n:'NOT_IMPLEMENTED' for n in ['SEED','PREWATCH','CONFIRMED','WARM']},
            episode_id=episode,parent_episode_id=None,invalidation_contract_id='OLD_INVALIDATION_RULESET_V0' if episode else None,
            prior_state_binding=None,matched_predicates=[],unknown_predicates=['OLD_V0_FROZEN_GOLDEN_UNKNOWN'],transition_reasons=['OLD_V0_LAST_KNOWN_STATE'],
            expiry_count=0,downgrade_count=0,downgrade_candidate=None,improvement_baseline=None,market_age=0,exit_session_index=None,boundary_event=None,preserved_followup_episode_ids=[])
        row['publication_id']='OLD_STATE:'+digest(row)
        authority=dict(contract_id='V4_10_BOUNDARY_SOURCE_AUTHORITY_R1_2',authorization='APPROVED_IMMUTABLE_OLD_STATE_IMPORT',
            source_publication_id=row['publication_id'],source_payload_digest=digest(row),source_model_contract_id=row['model_contract_id'],
            source_parameter_set_id=row['parameter_set_id'],source_interface_contract_id=row['interface_contract_id'],
            source_producer='V4_10_INDEPENDENT_V0_GOLDEN_PRODUCER',golden_case=key,scope='DISPOSABLE_INDEPENDENT_OLD_PRODUCER_GATE_FIXTURE')
        out[key]=dict(payload=row,authority=authority)
    return out
