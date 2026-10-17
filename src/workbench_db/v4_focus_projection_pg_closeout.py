"""Versioned PostgreSQL Owner fact for corrected Focus projections."""
import gzip
import hashlib
import json
from pathlib import Path
from workbench_service.current_v4_context import canonical,digest,SourceInvalid
from workbench_db.v4_operational_owner_pg_closeout import (
    prepare as append_owner_fact, read as read_owner_fact, inline_descriptor,
    descriptor_metadata,
)

CONTRACT='V4_FOCUS_CORRECTED_PROJECTION_NATIVE_PG_CLOSEOUT_R2'
DOMAIN='focus_projection'

def build(root,source,*,t0,head_token):
    root=Path(root).resolve()
    from focus_tracker.v4_path_adapter import checked
    path=checked(root,source)
    raw=path.read_bytes()
    document=json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)
    ids=set()
    for episode in document['episodes']:
        if episode['episode_id'] in ids:raise SourceInvalid('FOCUS_PROJECTION_DUPLICATE_EPISODE')
        ids.add(episode['episode_id'])
        if episode.get('AS_RECORDED') is True or episode.get('PIT_ELIGIBLE') is True:
            raise SourceInvalid('CORRECTED_FOCUS_PIT_ESCALATION')
        for observation in episode['observations']:
            if observation['trade_date']>t0:raise SourceInvalid('FOCUS_PROJECTION_FUTURE_OBSERVATION')
        for outcome in episode['outcomes']:
            if outcome['trade_date']>t0 or outcome.get('target_trade_date') and outcome['target_trade_date']>t0:
                raise SourceInvalid('FOCUS_PROJECTION_FUTURE_SETTLEMENT')
    payload=canonical(document)
    projection_sha=digest(payload)
    fact_token=digest(canonical(dict(contract_id=CONTRACT,T0=t0,head_token=head_token,
                           source_binding=source,projection_sha256=projection_sha)))
    descriptor=append_owner_fact(root,fact_token,t0,DOMAIN,source,[document])
    binding=inline_descriptor(root,descriptor)
    binding.update(contract_id=CONTRACT,T0=t0,head_token=head_token,
                   source_binding=source,fact_token=fact_token,
                   projection_sha256=projection_sha,PIT_ELIGIBLE=False,AS_RECORDED=False)
    actual=read(root,binding,t0=t0,head_token=head_token)
    if canonical(actual)!=canonical(document):raise SourceInvalid('FOCUS_PG_COMPLETE_PAYLOAD_ORACLE_MISMATCH')
    return binding,dict(contract_id=CONTRACT,source=source,projection_sha256=digest(payload),episodes=len(ids),whole_payload_difference=0,storage_engine='postgresql')

def read(root,binding,*,t0,head_token):
    descriptor=descriptor_metadata(root,binding)
    source=binding.get('source_binding')
    fact_token=binding.get('fact_token')
    if (binding.get('contract_id')!=CONTRACT or binding.get('T0')!=t0
            or binding.get('head_token')!=head_token or not isinstance(source,dict)
            or not isinstance(fact_token,str) or len(fact_token)!=64
            or descriptor.get('kind')!=DOMAIN or descriptor.get('engine')!='postgresql'):
        raise SourceInvalid('FOCUS_PG_PROJECTION_CONTEXT_MISMATCH')
    rows=read_owner_fact(root,binding,head_token,t0,DOMAIN,source)
    if not isinstance(rows,list) or len(rows)!=1 or not isinstance(rows[0],dict):
        raise SourceInvalid('FOCUS_PG_PROJECTION_MISSING')
    payload=canonical(rows[0])
    if hashlib.sha256(payload).hexdigest()!=binding.get('projection_sha256'):
        raise SourceInvalid('FOCUS_PG_PROJECTION_PAYLOAD_MISMATCH')
    expected=digest(canonical(dict(contract_id=CONTRACT,T0=t0,head_token=head_token,
                         source_binding=source,projection_sha256=hashlib.sha256(payload).hexdigest())))
    if fact_token!=expected:raise SourceInvalid('FOCUS_PG_PROJECTION_FACT_TOKEN_MISMATCH')
    return rows[0]
