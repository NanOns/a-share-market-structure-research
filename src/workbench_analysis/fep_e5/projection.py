"""Immutable projection acceptance. Inference supplied by exact-bound adapters only."""
from . import contracts as c

def missing(ledger,slot,status,at):
    c.require(status in ('NO_ACTIVE_MODEL','MISSED_SLOT','MISSING_DEPENDENCY'),'MISSING_RECEIPT_STATUS')
    record=dict(slot_id=slot['slot_id'],status=status,recorded_at=at)
    with ledger.pg.transaction():ledger.put('slot_receipts',c.logical(record),record,slot_id=slot['slot_id'])
    return record

def accept(ledger,slot_id,input_row,output,started_at,accepted_at,*,revision=1,supersedes=None,fail_before_receipt=False):
    slot=ledger.get('prediction_slots',slot_id);binding=ledger.get('slot_model_bindings',slot_id)
    c.require(slot is not None and binding is not None,'MISSING_MODEL_OR_SLOT')
    model=ledger.get('models',binding['model_id']);c.compatible(slot,model)
    c.require(c.utc(slot['model_selection_cutoff'])<=c.utc(started_at)<=c.utc(accepted_at)<=c.utc(slot['prediction_deadline']),'PREDICTION_DEADLINE_OR_SELECTION_CLOCK')
    c.require(input_row['observation_id']==slot['observation_id'],'OBSERVATION_ID_MISMATCH')
    for k in ('entity_id','trade_date'):c.require(input_row[k]==slot[k],'SNAPSHOT_SLOT_MISMATCH:'+k)
    c.require(input_row['snapshot']['max_feature_source_trade_date']<=slot['trade_date'],'FUTURE_FEATURE_READ')
    c.require(c.utc(input_row['source_available_at'])<=c.utc(started_at),'INPUT_NOT_AVAILABLE')
    input_digest=c.snapshot_input(input_row);c.evidence(output)
    identity_fields={'scope_id','observation_scope','namespace','target_id','horizon','feature_contract_id','model_id','model_set_id',
        'slot_id','prediction_slot_id','entity_id','trade_date','revision','supersedes','input_digest','prediction_digest','run_id','created_at','accepted_at','publication_id','feature_snapshot_id','feature_snapshot_digest'}
    c.require(not (identity_fields & set(output)),'OUTPUT_IDENTITY_OVERRIDE')
    c.require(output.get('inference_model_id')==model['model_id'] and output.get('inference_model_set_id')==model['model_set_id'], 'OUTPUT_MODEL_BINDING_MISMATCH')
    c.require(output.get('inference_snapshot_digest')==input_row['snapshot_digest'] and output.get('inference_source_digest')==model['artifact_digest'],'OUTPUT_SOURCE_SNAPSHOT_BINDING_MISMATCH')
    c.require(output['projection_state'] in c.STATES,'PROJECTION_STATE_INVALID')
    c.require(not (output['OOD_state'].get('JOINT_OOD')=='UNSET' and output['OOD_state'].get('global_OOD_OK')),'JOINT_OOD_UNSET_PROMOTED')
    c.require(output.get('threshold_state') in ('NOT_FROZEN','UNKNOWN'),'POST_RESULT_THRESHOLD')
    key=c.permission_key(model,'SHADOW_INFERENCE');c.require(ledger.allowed(model['model_id'],key,started_at),'EXACT_PERMISSION_REQUIRED')
    if revision==1:c.require(supersedes is None,'FIRST_REVISION_SUPERSEDES')
    else:
        old=ledger.get('predictions',supersedes)
        c.require(old is not None and old['slot_id']==slot_id and old['revision']==revision-1,'REVISION_LINEAGE_MISMATCH')
        c.require(output['prediction_evidence']=='CORRECTED_RECONSTRUCTION','CORRECTED_REVISION_EVIDENCE')
    run_id=c.logical(dict(slot_id=slot_id,revision=revision,input_digest=input_digest,model_id=model['model_id'],output=output))
    prediction_digest=c.logical(output);prediction_id=c.logical(dict(slot_id=slot_id,revision=revision,model_id=model['model_id'],input_digest=input_digest,prediction_digest=prediction_digest))
    record=dict(prediction_id=prediction_id,prediction_slot_id=slot_id,slot_id=slot_id,revision=revision,supersedes=supersedes,
        observation_id=input_row['observation_id'],entity_id=slot['entity_id'],trade_date=slot['trade_date'],
        feature_snapshot_id=input_row['snapshot_id'],feature_snapshot_digest=input_row['snapshot_digest'],
        model_set_id=model['model_set_id'],model_id=model['model_id'],model_family=model['model_family'],evidence_class=model['evidence_class'],
        target_id=slot['target_id'],horizon=slot['horizon'],feature_contract_id=slot['feature_contract_id'],feature_variant='CORE',
        namespace=slot['namespace'],scope_id=slot['scope_id'],observation_scope=slot['observation_scope'],input_digest=input_digest,
        prediction_digest=prediction_digest,run_id=run_id,created_at=started_at,accepted_at=accepted_at,execution_mode='ENGINEERING_SHADOW',
        publication_id=input_row['snapshot']['publication_identity'],**output)
    with ledger.pg.transaction():
        ledger.put('prediction_runs',run_id,dict(run_id=run_id,slot_id=slot_id,model_set_id=model['model_set_id'],input_digest=input_digest,
            started_at=started_at,finished_at=accepted_at,output_digest=prediction_digest),slot_id=slot_id)
        ledger.put('predictions',prediction_id,record,slot_id=slot_id,run_id=run_id,revision=revision,supersedes=supersedes)
        ledger.put('projections',prediction_id,record)
        if fail_before_receipt:raise ValueError('E5_INJECTED_ACCEPTANCE_FAILURE')
        receipt=dict(prediction_id=prediction_id,run_id=run_id,grant_key=key,grant_id=c.logical(key),accepted_at=accepted_at,
            state='ACCEPTED_ENGINEERING',model_display=False,priority_use=False)
        ledger.put('acceptance_receipts',prediction_id,receipt,run_id=run_id,grant_id=receipt['grant_id'])
        ledger.put('slot_receipts',prediction_id,dict(slot_id=slot_id,prediction_id=prediction_id,status='ACCEPTED',recorded_at=accepted_at),slot_id=slot_id)
    return ledger.get('projections',prediction_id)

def first_accepted(ledger,slot_id):
    matches=[p for p in ledger.rows('predictions') if p['slot_id']==slot_id and p['revision']==1]
    c.require(len(matches)<=1,'MULTIPLE_FIRST_ACCEPTED')
    return matches[0] if matches else None
