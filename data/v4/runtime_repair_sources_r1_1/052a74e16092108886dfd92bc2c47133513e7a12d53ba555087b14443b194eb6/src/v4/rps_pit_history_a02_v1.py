"""A02 immutable, accepted-input RPS candidates; never runtime reconstruction."""
from __future__ import annotations
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import tempfile

CONTRACT = 'V4_RPS_PIT_HISTORY_V1'

def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()

def binding(root, path):
    path = Path(path)
    if not path.is_absolute(): path = root / path
    payload = path.read_bytes()
    return dict(path=path.relative_to(root).as_posix(), sha256=sha256(payload).hexdigest(), bytes=len(payload))

def read_bound(root, ref):
    path = (root / ref['path']).resolve()
    if not path.is_relative_to(root.resolve()): raise ValueError('RPS_BINDING_ESCAPE')
    data = path.read_bytes()
    if sha256(data).hexdigest() != ref['sha256'] or len(data) != ref.get('bytes', ref.get('byte_count',len(data))):
        raise ValueError('RPS_BINDING_MISMATCH')
    return json.loads(data)

def immutable_json(path, value):
    data = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)+'\n').encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data: raise ValueError('RPS_APPEND_ONLY_CONFLICT')
        return
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.'+path.name)
    try:
        with os.fdopen(fd,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
        # Link has atomic create-if-absent semantics, preserving earlier publication.
        os.link(name, path)
    finally:
        Path(name).unlink(missing_ok=True)

def scores(returns, universe):
    """Sorted tie groups implement the frozen 0..100 midrank/(N-1)."""
    values = sorted((value, sid) for sid in universe if (value := returns.get(sid)) is not None and math.isfinite(value))
    result = dict.fromkeys(universe)
    n = len(values)
    if n < 2: return result
    i=0
    while i<n:
        j=i+1
        while j<n and values[j][0] == values[i][0]: j+=1
        value=100*(i+0.5*(j-i-1))/(n-1)
        for _, sid in values[i:j]: result[sid]=value
        i=j
    return result

def publish(input_payload, previous=None):
    required={'trade_date','data_authority','universe_identity','calendar_identity','cutoff_timestamp','algorithm_identity','source_revision','sessions','universe','returns','endpoint_evidence','source_bindings'}
    if set(input_payload) != required: raise ValueError('RPS_INPUT_SCHEMA')
    day=input_payload['trade_date']; sessions=input_payload['sessions']
    if sessions != sorted(set(sessions)) or day not in sessions: raise ValueError('RPS_CALENDAR_INVALID')
    if input_payload['cutoff_timestamp'][:10] < day: raise ValueError('RPS_CUTOFF_BEFORE_TRADE')
    if input_payload['data_authority']['accepted_through'] < day: raise ValueError('RPS_BEYOND_ACCEPTED_INPUT')
    members=input_payload['universe']
    if members != sorted(set(members)): raise ValueError('RPS_UNIVERSE_DUPLICATE')
    rows=[]; computed={h:scores(input_payload['returns'][str(h)],members) for h in (5,20)}
    for sid in members:
        rows.append(dict(security_id=sid, **{f'rps{h}':dict(value=computed[h][sid],quality_state='OBSERVED' if computed[h][sid] is not None else 'UNKNOWN',unknown_reason=None if computed[h][sid] is not None else input_payload['endpoint_evidence'][sid][str(h)]['unknown_reason']) for h in (5,20)}))
    result=dict(contract_id=CONTRACT, version='1.0.0', publication_status='CANDIDATE_NOT_EXTERNALLY_ACCEPTED',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False, first_availability_proven=False, input_digest=digest(input_payload), previous_publication=previous, **{k:input_payload[k] for k in ('trade_date','data_authority','universe_identity','calendar_identity','cutoff_timestamp','algorithm_identity','source_revision','source_bindings')},universe=members, rows=rows)
    result['logical_digest']=digest(result)
    return result

def delta(current, prior, offset, sessions):
    day=current['trade_date']; index=sessions.index(day)
    reason=None
    if index<offset or prior is None: reason=f'T_MINUS_{offset}_PUBLICATION_MISSING'
    elif prior['trade_date'] != sessions[index-offset]: raise ValueError('RPS_EXACT_PRIOR_SESSION_MISMATCH')
    elif current['calendar_identity'] != prior['calendar_identity']: reason='CALENDAR_REVISION'
    elif current['algorithm_identity'] != prior['algorithm_identity']: reason='ALGORITHM_REVISION'
    # A revised universe is explicit UNKNOWN rather than comparable survivor reranking.
    elif (current['universe_identity'].get('producer_sha') if isinstance(current['universe_identity'],dict) else current['universe_identity']) != (prior['universe_identity'].get('producer_sha') if isinstance(prior['universe_identity'],dict) else prior['universe_identity']): reason='UNIVERSE_AUTHORITY_REVISION'
    priors={r['security_id']:r for r in prior['rows']} if prior else {}
    output=[]
    for row in current['rows']:
        fields={}
        for h in (5,20):
            name=f'rps{h}'; now=row[name]['value']; old=priors.get(row['security_id'],{}).get(name,{}).get('value')
            unknown=reason or ('PRIOR_UNIVERSE_MEMBER_MISSING' if row['security_id'] not in priors else 'RPS_ENDPOINT_UNKNOWN' if now is None or old is None else None)
            fields[f'{name}_delta{offset}']=dict(value=None if unknown else now-old,quality_state='UNKNOWN' if unknown else 'OBSERVED',unknown_reason=unknown,current_publication_digest=current['logical_digest'],prior_publication_digest=prior['logical_digest'] if prior else None,current_trade_date=day,prior_trade_date=prior['trade_date'] if prior else None,current_universe_identity=current['universe_identity'],prior_universe_identity=prior['universe_identity'] if prior else None)
        output.append(dict(security_id=row['security_id'],fields=fields))
    return output

def read_publication(root, ref):
    publication=read_bound(root,ref)
    if publication.get('contract_id') != CONTRACT: raise ValueError('RPS_PUBLICATION_CONTRACT')
    expected=publication['logical_digest']
    if digest({k:v for k,v in publication.items() if k!='logical_digest'}) != expected: raise ValueError('RPS_LOGICAL_DIGEST')
    return publication
