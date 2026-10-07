"""V4_ACCEPTED_CURRENT_REFRESH_V1: CAS publication of validated accepted views."""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .current_v4_context import CurrentAcceptedV4Reader, canonical, digest, SourceInvalid

AUTHORITY='config/v4_production_runtime_authority_v1.json'


def atomic_bytes(path,raw):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temp.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        if temp.exists():temp.unlink()


def publish_accepted_view(root,candidate_contract,expected_authority_digest,*,now=None):
    root=Path(root).resolve()
    locator=CurrentAcceptedV4Reader(root,contract_path=candidate_contract,follow_runtime=False)
    raw=locator._path(candidate_contract).read_bytes();contract=json.loads(raw)
    archive=root/'data/v4/production_views'/digest(raw)/'read_contract.json'
    if archive.exists() and archive.read_bytes()!=raw:raise SourceInvalid('IMMUTABLE_VIEW_CONFLICT')
    if not archive.exists():atomic_bytes(archive,raw)
    # All module gates consume one frozen candidate, even if a concurrent daily
    # build replaces the mutable candidate configuration during validation.
    reader=CurrentAcceptedV4Reader(root,contract_path=archive.relative_to(root).as_posix(),follow_runtime=False)
    candidate=reader.load_context()
    for module in ['summary','radar','entity','sector','cohort','settlement','health']:
        code,value=reader.read(module)
        if code!=200:raise SourceInvalid('CANDIDATE_OWNER_GATE:'+module+':'+value.get('reason',''))
    today=(now or datetime.now(ZoneInfo('Asia/Shanghai'))).date().isoformat()
    if candidate['context']['accepted_trade_date']>today:raise SourceInvalid('FUTURE_INPUT_FORBIDDEN')
    path=root/AUTHORITY;old_raw=path.read_bytes()
    if digest(old_raw)!=expected_authority_digest:raise SourceInvalid('AUTHORITY_CAS_CONFLICT')
    old=json.loads(old_raw)
    if candidate['context']['accepted_trade_date']<old['last_accepted_trade_date']:raise SourceInvalid('OLDER_CANDIDATE_FORBIDDEN')
    previous=root/'data/v4/production_views'/digest(old_raw)/'authority.json'
    if not previous.exists():atomic_bytes(previous,old_raw)
    new={**old,'read_authority':dict(path=archive.relative_to(root).as_posix(),bytes=len(raw),sha256=digest(raw),owner_stage='CURRENT_ACCEPTED',contract_id=contract['contract_id']),
        'data_head_binding':contract['anchors']['data_head'],'stage_authority_binding':contract['anchors']['stage_authority'],
        'last_accepted_trade_date':candidate['context']['accepted_trade_date'],
        'rollback_binding':dict(path=previous.relative_to(root).as_posix(),bytes=len(old_raw),sha256=digest(old_raw)),
        'source_mode':'V4_ACCEPTED_RESEARCH_READONLY'}
    lock=path.with_suffix('.lock')
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    try:
        os.close(fd)
        if digest(path.read_bytes())!=expected_authority_digest:raise SourceInvalid('AUTHORITY_CAS_CONFLICT')
        atomic_bytes(path,canonical(new)+b'\n')
        # Fresh reader must verify the exact newly visible pointer.
        try:
            readback=CurrentAcceptedV4Reader(root,require_runtime=True).load_context()
        except (ValueError,OSError,KeyError):
            # Keep the previous accepted pointer even if an external source
            # mutation or readback failure occurs after the atomic swap.
            atomic_bytes(path,old_raw)
            raise
        return dict(status='PUBLISHED_CURRENT_ACCEPTED',before=digest(old_raw),after=digest(path.read_bytes()),context=readback)
    finally:lock.unlink()


def refresh_status(root,*,now=None):
    root=Path(root);reader=CurrentAcceptedV4Reader(root,require_runtime=True);context=reader.load_context()
    contract,_=reader._contract();heads=reader._heads(contract)
    calendar=reader._read(heads['stage_authority']['calendar'])
    sessions=calendar.get('session_dates') or calendar.get('sessions')
    if not sessions:raise SourceInvalid('OFFICIAL_CALENDAR_UNAVAILABLE')
    if isinstance(sessions[0],dict):sessions=sorted(set(row['trade_date'] for row in sessions))
    now=now or datetime.now(ZoneInfo('Asia/Shanghai'))
    completed=[d for d in sessions if context['context']['accepted_trade_date']<d<now.date().isoformat() or (d==now.date().isoformat() and now.hour>=15 and d>context['context']['accepted_trade_date'])]
    return dict(status='WAIT_NEXT_ACCEPTED_INPUT' if not completed else 'COMPLETED_INPUT_CAPTURE_REQUIRED',next_completed_session=min(completed) if completed else None,
        source_requests=0,data_preserved=True,context=context,contract_id='V4_ACCEPTED_CURRENT_REFRESH_V1')
