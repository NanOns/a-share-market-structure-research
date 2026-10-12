"""Versioned native PG authority for corrected Focus read projections."""
import gzip
import json
from pathlib import Path
import uuid
from .v4_snapshot_pg_r2 import Builder
from .v4_snapshot_pg_r1 import read as read_snapshot
from workbench_service.current_v4_context import canonical,digest,SourceInvalid
from workbench_service.v4_daily_refresh import atomic_bytes

CONTRACT='V4_FOCUS_CORRECTED_PROJECTION_NATIVE_PG_CLOSEOUT_R1'

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
    payload=canonical(document).decode()
    release=uuid.uuid4().hex
    target=root/'data/v4/focus_pg_projection_closeout'/release/'focus.pg.json'
    db=Builder(root,release,storage_kind='snapshot')
    try:
        db.executescript('CREATE TABLE objects(domain text,id text,name text,symbol text,state text,payload text,PRIMARY KEY(domain,id));CREATE TABLE aliases(alias text,id text,PRIMARY KEY(alias,id));CREATE TABLE members(sector text,security text,PRIMARY KEY(sector,security));CREATE TABLE metadata(key text PRIMARY KEY,value text);')
        db.execute('INSERT INTO objects VALUES(?,?,?,?,?,?)',('focus_projection',t0,'','','READY',payload))
        meta=dict(release_id=release,context=dict(accepted_trade_date=t0),source=source,
                  projection_digest=digest(payload.encode()),episodes=len(ids),head_token=head_token,
                  contract_id=CONTRACT,knowledge_lineage='RECONSTRUCTED_CORRECTED',PIT_ELIGIBLE=False,AS_RECORDED=False)
        descriptor=db.seal(meta,source_binding=source)
        db.commit()
    finally:db.close()
    atomic_bytes(target,canonical(descriptor)+b'\n')
    binding=dict(path=target.relative_to(root).as_posix(),bytes=target.stat().st_size,sha256=digest(target.read_bytes()))
    actual=read(root,binding,t0=t0,head_token=head_token)
    if canonical(actual)!=canonical(document):raise SourceInvalid('FOCUS_PG_COMPLETE_PAYLOAD_ORACLE_MISMATCH')
    return binding,dict(contract_id=CONTRACT,source=source,projection_sha256=digest(payload.encode()),episodes=len(ids),whole_payload_difference=0)

def read(root,binding,*,t0,head_token):
    from focus_tracker.v4_path_adapter import checked
    descriptor=json.loads(checked(root,binding).read_bytes())
    meta=descriptor.get('content_manifest',{}).get('metadata',{})
    if meta.get('contract_id')!=CONTRACT or descriptor.get('T0')!=t0 or meta.get('head_token')!=head_token:
        raise SourceInvalid('FOCUS_PG_PROJECTION_CONTEXT_MISMATCH')
    with read_snapshot(descriptor) as db:
        row=db.execute('SELECT payload FROM objects WHERE domain=? AND id=?',('focus_projection',t0)).fetchone()
        if row is None:raise SourceInvalid('FOCUS_PG_PROJECTION_MISSING')
        if digest(row[0].encode())!=meta['projection_digest']:
            raise SourceInvalid('FOCUS_PG_PROJECTION_PAYLOAD_MISMATCH')
        return json.loads(row[0])
