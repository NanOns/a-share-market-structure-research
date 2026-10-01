"""Read exact frozen publication triplets. This reader never computes RPS."""
from .rps_pit_history_a02_v1 import read_publication

def read_triplet(root, current_ref, prior_refs, sessions, *, formal_consumer=False):
    if formal_consumer:
        raise ValueError('A02_INDEPENDENT_EXTERNAL_ACCEPTANCE_REQUIRED')
    current=read_publication(root,current_ref)
    if current.get('AS_RECORDED') is not False or current.get('first_availability_proven') is not False or current.get('knowledge_lineage')!='RECONSTRUCTED_CORRECTED' or current.get('publication_status')!='CANDIDATE_NOT_EXTERNALLY_ACCEPTED':
        raise ValueError('A02_PUBLICATION_SCOPE_OR_HISTORY_CLAIM_INVALID')
    if current['trade_date'] not in sessions: raise ValueError('A02_CURRENT_SESSION_NOT_CALENDAR')
    index=sessions.index(current['trade_date']); result={'T':current,'T_binding':current_ref,'consumption_scope':'CANDIDATE_REPLAY_ONLY'}
    for offset in (1,3):
        ref=prior_refs.get(offset)
        if ref is None:
            result[f'T-{offset}']=None;result[f'T-{offset}_unknown_reason']=f'T_MINUS_{offset}_PUBLICATION_MISSING';continue
        if index<offset: raise ValueError('A02_WARMUP_PRIOR_CONFLICT')
        prior=read_publication(root,ref)
        if prior.get('AS_RECORDED') is not False or prior.get('first_availability_proven') is not False or prior.get('knowledge_lineage')!='RECONSTRUCTED_CORRECTED' or prior.get('publication_status')!='CANDIDATE_NOT_EXTERNALLY_ACCEPTED':
            raise ValueError('A02_PUBLICATION_SCOPE_OR_HISTORY_CLAIM_INVALID')
        if prior['trade_date'] != sessions[index-offset]: raise ValueError('A02_PRIOR_SESSION_BINDING_MISMATCH')
        if prior['calendar_identity'] != current['calendar_identity']: raise ValueError('A02_CALENDAR_BINDING_MISMATCH')
        if prior['algorithm_identity'] != current['algorithm_identity']: raise ValueError('A02_ALGORITHM_BINDING_MISMATCH')
        result[f'T-{offset}']=prior;result[f'T-{offset}_binding']=ref
    return result
