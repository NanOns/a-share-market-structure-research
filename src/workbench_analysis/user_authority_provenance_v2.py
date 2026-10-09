"""Future permission preflight requires replay of an original user event, not authored MD."""
import hashlib,json
from pathlib import Path
from datetime import datetime,timezone

CONTRACT='USER_PERMISSION_ORIGINAL_EVENT_GATE_V2'


def verify_future_permission_origin(record, candidate_digest, session_root):
    if record.get('contract_id') != CONTRACT or record.get('candidate_digest') != candidate_digest:
        raise ValueError('NEW_CANDIDATE_SCOPED_AUTHORITY_REQUIRED')
    if record.get('legacy_authorization_reused') is not False or record.get('independent_external_acceptance') is not False:
        raise ValueError('LEGACY_QUOTE_REUSE_OR_EXTERNAL_OVERCLAIM_FORBIDDEN')
    source=Path(record['original_session_path']).resolve();allowed=Path(session_root).resolve()
    if not source.is_relative_to(allowed) or source.suffix!='.jsonl':
        raise ValueError('ORIGINAL_CODEX_SESSION_REQUIRED')
    number=record['original_line_number']
    if not isinstance(number,int) or number<1:raise ValueError('ORIGINAL_MESSAGE_LOCATOR_REQUIRED')
    with source.open('rb') as stream:
        raw=next((line for i,line in enumerate(stream,1) if i==number),None)
    if raw is None or hashlib.sha256(raw).hexdigest()!=record['original_event_sha256']:
        raise ValueError('ORIGINAL_EVENT_DIGEST_MISMATCH')
    event=json.loads(raw);payload=event.get('payload',{})
    if event.get('type')!='response_item' or payload.get('role')!='user':
        raise ValueError('ORIGINAL_DIRECT_USER_ROLE_REQUIRED')
    text=''.join(c.get('text','') for c in payload.get('content',[]))
    if text!=record.get('request_text') or event.get('timestamp')!=record.get('message_timestamp'):
        raise ValueError('ORIGINAL_REQUEST_TEXT_OR_TIME_MISMATCH')
    timestamp=datetime.fromisoformat(event['timestamp'].replace('Z','+00:00'))
    if timestamp.tzinfo is None or timestamp>datetime.now(timezone.utc):raise ValueError('INVALID_USER_MESSAGE_TIME')
    if not record.get('session_id') or not record.get('explicit_permission_scope') or not record.get('trusted_scope_review_reference'):
        raise ValueError('TRUSTED_SCOPE_REVIEW_REQUIRED')
    return dict(status='ORIGINAL_EVENT_REPLAY_VERIFIED_SCOPE_REVIEW_RECORDED',
                permission_granted=False, independent_external_acceptance=False,
                limitation='Local replay and scope reference do not authenticate an independent signer; publisher must separately validate authority and release gates.')
