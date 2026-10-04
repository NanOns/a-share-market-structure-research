"""Pure native-session contract checks; no real observation or authority writer."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OWNER_PATH='config/v4_16_observation_slot_contract_v2.json'
OWNER_BYTES=(ROOT/OWNER_PATH).read_bytes()
OWNER=json.loads(OWNER_BYTES)
OWNER_SHA=hashlib.sha256(OWNER_BYTES).hexdigest()


def production_binding(value):
    binding=value.get('production_session_authority')
    return bool(value.get('kind')=='CONTRACT_DESIGN_SIMULATION' and isinstance(binding,dict) and binding.get('status')=='CONTRACT_DESIGN_SIMULATION' and binding.get('authority_id','').startswith('SIM_') and binding.get('native_states') and binding.get('accepted_status') in binding['native_states'])


def session_errors(row,value):
    if row['evidence_lane'] not in ('SHADOW_REAL','PRODUCTION_REAL'): return []
    errors=[]
    if row['evidence_lane']=='SHADOW_REAL':
        if row.get('native_session_authority_id')!=OWNER['contract_id'] or row.get('native_session_authority_sha256')!=OWNER_SHA: errors.append('SHADOW_SESSION_OWNER_BINDING_MISMATCH')
        if row.get('native_session_status') not in OWNER['slot_states']: errors.append('UNKNOWN_SHADOW_NATIVE_SESSION_STATUS')
        accepted='ACCEPTED_ON_TIME'; missed='MISSED_OBSERVATION_SLOT'
    else:
        if not production_binding(value): return ['PRODUCTION_SESSION_AUTHORITY_REQUIRED_NOT_COUNTABLE']
        binding=value['production_session_authority']
        binding_sha=hashlib.sha256(json.dumps(binding,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if row.get('native_session_authority_id')!=binding['authority_id'] or row.get('native_session_authority_sha256')!=binding_sha: errors.append('PRODUCTION_SIMULATION_OWNER_BINDING_MISMATCH')
        if row.get('native_session_status') not in binding['native_states']: errors.append('UNKNOWN_PRODUCTION_SIMULATION_NATIVE_STATUS')
        accepted=binding['accepted_status']; missed=None
    if type(row.get('projection_evaluable')) is not bool: errors.append('PROJECTION_EVALUABLE_BOOLEAN_REQUIRED')
    if row.get('projection_evaluable') is False and not row.get('projection_evaluable_reason'): errors.append('PROJECTION_EVALUABILITY_REASON_REQUIRED')
    if missed and row.get('native_session_status')==missed and row.get('projection_evaluable') is not False: errors.append('MISSED_SLOT_CANNOT_BE_EVALUABLE')
    expected=row.get('evidence_origin')=='PIT_OBSERVED' and row.get('accepted_real_publication') is True and row.get('execution_mode')==('SHADOW' if row['evidence_lane']=='SHADOW_REAL' else 'PRODUCTION') and row.get('native_session_status')==accepted and row.get('projection_evaluable') is True
    if 'claimed_real_accepted_session' in row and row['claimed_real_accepted_session']!=int(expected): errors.append('CLAIMED_REAL_SESSION_COUNT_MISMATCH')
    if 'slot_status' in row and row['slot_status']!=row.get('native_session_status'): errors.append('COMPATIBILITY_SLOT_STATUS_MUST_EQUAL_NATIVE')
    return errors


def session_countable(row,value):
    if session_errors(row,value): return False
    lane=row['evidence_lane']
    if lane=='SHADOW_REAL': accepted='ACCEPTED_ON_TIME'
    elif lane=='PRODUCTION_REAL' and production_binding(value): accepted=value['production_session_authority']['accepted_status']
    else: return False
    return row.get('evidence_origin')=='PIT_OBSERVED' and row.get('accepted_real_publication') is True and row.get('execution_mode')==('SHADOW' if lane=='SHADOW_REAL' else 'PRODUCTION') and row.get('native_session_status')==accepted and row.get('projection_evaluable') is True


def receipt_session_status(row,value=None):
    errors=session_errors(row,value or {})
    if errors: raise ValueError(','.join(errors))
    return {k:row[k] for k in ('native_session_authority_id','native_session_authority_sha256','native_session_status','projection_evaluable','projection_evaluable_reason')}|{'accepted_session_status':row['native_session_status']}


def bind_future_production_fixture(value):
    binding=dict(authority_id='SIM_FUTURE_PRODUCTION_SESSION_AUTHORITY',status='CONTRACT_DESIGN_SIMULATION',native_states=['SIM_PRODUCTION_ACCEPTED'],accepted_status='SIM_PRODUCTION_ACCEPTED')
    value['production_session_authority']=binding
    binding_sha=hashlib.sha256(json.dumps(binding,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    for row in value['sessions']:
        if row['evidence_lane']=='PRODUCTION_REAL': row.update(native_session_authority_id=binding['authority_id'],native_session_authority_sha256=binding_sha,native_session_status=binding['accepted_status'])
