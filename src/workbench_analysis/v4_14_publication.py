"""Deterministic manifest identities and append-only replay revisions."""
import re,json
from datetime import datetime
from .v4_14_replay_io import publish,digest,exact
def validate_envelope(root,envelope,authority):
    schema=json.loads((authority.root/'config/v4_14_replay_input_envelope_r18_v1.json').read_bytes())
    if set(schema['required'])-set(envelope):raise ValueError('REPLAY_ENVELOPE_FIELDS_REQUIRED')
    if envelope['evidence_class'] not in schema['evidence_classes']:raise ValueError('REPLAY_EVIDENCE_CLASS_INVALID')
    if envelope['authority_bindings']!=authority.bindings() or envelope['contract_package_digest']!=authority.package_digest:raise ValueError('REPLAY_ENVELOPE_AUTHORITY_MISMATCH')
    if envelope['previous_market_session']!=authority.previous(envelope['target_trade_date']):raise ValueError('REPLAY_PREVIOUS_SESSION_INVALID')
    cutoff=datetime.fromisoformat(envelope['cutoff'].replace('Z','+00:00'))
    if cutoff.tzinfo is None:raise ValueError('REPLAY_AWARE_CUTOFF_REQUIRED')
    for r in envelope['source_refs']:exact(authority.root,r)
    for s in envelope['source_availability']:
        if s['max_source_trade_date']>envelope['target_trade_date']:raise ValueError('REPLAY_FUTURE_SOURCE_FORBIDDEN')
        if datetime.fromisoformat(s['system_available_at'].replace('Z','+00:00'))>cutoff:raise ValueError('REPLAY_SOURCE_AFTER_CUTOFF')
        if s.get('membership_effective_date',envelope['target_trade_date'])>envelope['target_trade_date']:raise ValueError('REPLAY_FUTURE_MEMBERSHIP_FORBIDDEN')
    previous=envelope['previous_state_publication'];prior=None
    if previous is not None:
        prior=json.loads(exact(root,previous))
        if prior['target_trade_date']!=envelope['previous_market_session']:raise ValueError('REPLAY_PRIOR_PUBLICATION_DATE_INVALID')
        if prior['input_digest']!=digest(prior['envelope']) or prior['output_digest']!=digest(prior['output']):raise ValueError('REPLAY_PRIOR_CONTENT_DIGEST_INVALID')
        if prior['envelope']['authority_bindings']!=authority.bindings():raise ValueError('REPLAY_PRIOR_ACTIVE_AUTHORITY_INVALID')
    if envelope['evidence_class']=='HISTORICAL_PIT_EFFECTIVENESS':raise ValueError('HISTORICAL_PIT_NOT_GRANTED')
    return prior

def publish_replay(root,envelope,output,authority,namespace='reports/v4_14_replay_r18'):
    target=envelope['target_trade_date'];revision=envelope['target_revision']
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',target) or not re.fullmatch(r'r[1-9]\d*',revision):raise ValueError('REPLAY_REVISION_IDENTITY_INVALID')
    if envelope['authority_bindings']!=authority.bindings() or envelope['contract_package_digest']!=authority.package_digest:raise ValueError('REPLAY_ENVELOPE_AUTHORITY_MISMATCH')
    if envelope['previous_market_session']!=authority.previous(target):raise ValueError('REPLAY_PREVIOUS_SESSION_INVALID')
    previous=envelope['previous_state_publication']
    validate_envelope(root,envelope,authority)
    payload=dict(contract_id='V4_14_REPLAY_PUBLICATION_V1',version='1.0.0',target_trade_date=target,target_revision=revision,previous_market_session=envelope['previous_market_session'],previous_state_publication=previous,contract_package_digest=authority.package_digest,input_digest=digest(envelope),output_digest=digest(output),evidence_class=envelope['evidence_class'],source_refs=envelope['source_refs'],quality=output.get('quality','DEGRADED'),dimension_results=output.get('dimension_results',[]),output=output,envelope=envelope,ALGORITHM_STATE_REPLAY_PASS='NOT_GRANTED_PENDING_EXTERNAL_AUDIT')
    payload['replay_publication_id']='REPLAY:'+digest(payload)
    return publish(root,namespace+'/'+target+'/'+revision+'/manifest.json',payload)
