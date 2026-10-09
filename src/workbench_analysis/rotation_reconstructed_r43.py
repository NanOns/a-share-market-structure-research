"""Versioned finite-window operational episode, never historical PIT state."""
import inspect
import hashlib
from copy import deepcopy
from functools import lru_cache
from sector import rotation_r5

CONTRACT='RECONSTRUCTED_EPISODE_V1'


@lru_cache(maxsize=1)
def evaluator():
    source=inspect.getsource(rotation_r5.advance_rotation)
    old="prior.get('acceptance')!='ACCEPTED'"
    new="prior.get('episode_contract_id')!='RECONSTRUCTED_EPISODE_V1' or prior.get('membership_mode')!='TDX_LATEST_MEMBER_RETRO_V1' or prior.get('PIT_ELIGIBLE') is not False"
    if source.count(old)!=1:raise ValueError('ROTATION_AUTHORITY_AST_CHANGED')
    source=source.replace(old,new)
    namespace=dict(rotation_r5.__dict__);exec(compile(source,'RECONSTRUCTED_EPISODE_V1','exec'),namespace)
    return namespace['advance_rotation'],hashlib.sha256(source.encode()).hexdigest()


def advance(native, current, *, previous, prior_native, prior_members, prior_core,
            prior_date, calendar_sessions, contract, registry, parameters, seed_truth):
    if native['membership_mode']!='TDX_LATEST_MEMBER_RETRO_V1' or native['PIT_ELIGIBLE']:
        raise ValueError('OPERATIONAL_RETRO_ONLY')
    # The evaluator body is exactly the original ordered reduction. Its sole
    # authority boundary is versioned here, rather than forging an old ACCEPTED
    # publication. The finite research window starts a new synthetic episode.
    kernel,kernel_sha=evaluator()
    prior=deepcopy(previous) if previous else dict(output_state='NONE',episode=None,negative_out_count=0,
        native_fields=prior_native['fields'] if prior_native else {},
        initial_boundary='FINITE_OPERATIONAL_WINDOW_RESET; NOT_HISTORICAL_EPISODE_ABSENCE')
    prior.update(episode_contract_id=CONTRACT,membership_mode=native['membership_mode'],PIT_ELIGIBLE=False,
        target_trade_date=prior_date,membership_snapshot_id=native['membership_snapshot_id'])
    if prior.get('episode'):
        prior['episode']['accepted']=prior['episode'].pop('operational_accepted',False)
    result=kernel(native,current,prior_publication=prior,prior_members=prior_members,
        prior_core=prior_core,calendar_sessions=calendar_sessions,contract=contract,registry=registry,
        parameters=parameters,seed_truth=seed_truth,seed_capability=True)
    result.update(episode_contract_id=CONTRACT,quality='UNKNOWN' if result['output_state']=='UNKNOWN' else 'PROXY_RECONSTRUCTED',
        kernel_sha256=kernel_sha,initial_boundary=prior.get('initial_boundary'),
        membership_mode=native['membership_mode'],PIT_ELIGIBLE=False,AS_RECORDED=False,
        knowledge_lineage='RECONSTRUCTED_LATEST_MEMBERSHIP',target_trade_date=native['target_trade_date'])
    if result.get('episode'):
        result['episode']['operational_accepted']=result['episode'].pop('accepted')
        # R5 internal flag means within-episode phase admission, not external
        # historical publication acceptance. Persist a distinct field.
    return result
