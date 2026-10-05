"""Event-specific successor admission; historical pooled artifacts stay immutable."""
from copy import deepcopy
from .historical_dataset import admissible,scoped_policy
from .conditional import baseline
from workbench_analysis.fep_e1.contracts import digest

EVENTS={'FIRST_PREWATCH','NEW_CONFIRMED','REENTRY'}

def event_observation(row,enrollment,event,state):
    admissible(row)
    signal={'REENTRY_PREWATCH':'REENTRY'}.get(enrollment['signal_type'],enrollment['signal_type'])
    if signal not in EVENTS:raise ValueError('E2_EVENT_SIGNAL_REQUIRED')
    for key,actual in [('entity_id',enrollment['entity_id']),('trade_date',enrollment['T0']),('episode_key',enrollment['episode_id'])]:
        if row[key]!=actual:raise ValueError('E2_EVENT_OWNER_IDENTITY')
    if event['logical_event_id']!=enrollment['logical_event_id'] or event['episode_id']!=enrollment['episode_id']:
        raise ValueError('E2_EVENT_EPISODE_BINDING')
    if signal=='FIRST_PREWATCH' and (state.get('parent_episode_id') or 'ENROLLED' not in state['transition_reasons'] or state['maturity']!='PREWATCH'):
        raise ValueError('E2_FIRST_PREWATCH_OWNER_PREDICATE')
    identity=dict(entity_id=row['entity_id'],observation_scope='FEP_STOCK_ENTRY_CORE',signal_type=signal,
        logical_event_id=event['logical_event_id'],episode_id=enrollment['episode_id'],trade_date=row['trade_date'],
        target='ABS_RETURN_N:T1',horizon=1,evidence_origin=row['evidence_origin'])
    if enrollment['enrollment_id']!=row['observation_id']:raise ValueError('E2_EVENT_OBSERVATION_IDENTITY')
    return dict(row,**identity,observation_id=enrollment['enrollment_id'],event_identity_digest=digest(identity),umbrella_signal_type='ENTRY',
        predecessor_observation_id=row['observation_id'],source_event_publication=dict(publication_id=state['publication_id'],
            logical_event_id=event['logical_event_id'],logical_event_payload_digest=digest(event)),
        source_state_publication=state['publication_id'])

def owner_gap(signal,field):
    if signal not in {'REENTRY','NEW_CONFIRMED'}:raise ValueError('E2_OWNER_GAP_SIGNAL')
    if field['implemented'] is False and field['required'] is True:
        return dict(signal_type=signal,status='NOT_ENABLED_OWNER_INPUT_UNAVAILABLE',reason='OWNER_REQUIRED_INPUT_UNAVAILABLE',
            input='frozen_invalidation',producer_contract_id=field['producer_contract_id'],value='UNKNOWN')
    raise ValueError('E2_OWNER_INPUT_REQUIRES_INDEPENDENT_ACCEPTANCE')

def event_policy(discovery,applicability,frozen_at):
    if applicability['signal_type'] not in EVENTS:raise ValueError('E2_POOLED_ENTRY_POLICY_REJECTED')
    result=scoped_policy(discovery,applicability,frozen_at)
    result['policy_id']='FEP_E2_'+applicability['signal_type']+'_CORE_ABS_RETURN_T1_RECONSTRUCTED_V1_1'
    result['derivation']['classification']='ENGINEERING_SUPPORT_HEURISTIC'
    return result

def event_baseline(dataset,query,policy,method,created_at):
    if query['signal_type'] not in EVENTS or policy.get('applicability',{}).get('signal_type') not in EVENTS:
        raise ValueError('E2_POOLED_ENTRY_POLICY_REJECTED')
    return baseline(dataset,query,policy,method,created_at)

def event_dataset(predecessor,rows):
    """E1-selected revisions transported unchanged, identities stratified one to one."""
    from .input import bind
    keys={r['observation_id'] for r in rows}
    frozen=deepcopy(predecessor['e1_frozen_payload'])
    # Pure event membership projection, never a new revision resolver or E1 rebuild.
    for name in ('rows','selections'):
        frozen[name]=[r for r in frozen[name] if r['observation_id'] in keys]
    frozen.pop('digest',None);frozen['digest']=digest(frozen)
    metadata={k:v for k,v in predecessor.items() if k not in {'digest','e1_dataset_digest','e1_frozen_payload','selections','denominator','rows'}}
    metadata.update(dataset_id='FEP_E2_FIRST_PREWATCH_CORE_R1R2',predecessor_e2_digest=predecessor['digest'],
        predecessor_e1_digest=predecessor['e1_dataset_digest'],event_membership_only_projection=True)
    return bind(frozen,metadata,{r['observation_id']:r for r in rows})
