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


def validate_current_view_candidate(root,candidate_contract,expected_authority_digest=None,*,now=None):
    """Validate and persist a PG candidate without promoting a workspace Head.

    ``candidate_contract`` is a one-time source-ingress input. Its exact bytes
    and all bound module sources are read back from PostgreSQL before use.
    Successful validation appends an immutable candidate fact; only the
    canonical publication workflow can promote an accepted Head.
    """
    root=Path(root).resolve()
    from workbench_db.v4_historical_source_ingress_pg_r1 import admit_bound, source_id_for_path
    candidate_path=Path(candidate_contract)
    if candidate_path.is_absolute():
        try:candidate_path=candidate_path.resolve().relative_to(root).as_posix()
        except ValueError as exc:raise SourceInvalid('CANDIDATE_CONTRACT_OUTSIDE_WORKSPACE') from exc
    else:candidate_path=candidate_path.as_posix()
    if not candidate_path or Path(candidate_path).is_absolute() or '..' in Path(candidate_path).parts:
        raise SourceInvalid('CANDIDATE_CONTRACT_PATH_INVALID')
    source_path=(root/candidate_path).resolve()
    if not source_path.is_relative_to(root) or not source_path.is_file():
        raise SourceInvalid('CANDIDATE_CONTRACT_SOURCE_UNAVAILABLE')
    raw=source_path.read_bytes();contract_digest=digest(raw)
    source=admit_bound(root,dict(path=candidate_path,sha256=contract_digest,bytes=len(raw)))
    try:contract=json.loads(source['raw'])
    except (UnicodeDecodeError,ValueError) as exc:raise SourceInvalid('CURRENT_READ_CONTRACT_INVALID') from exc
    if contract.get('contract_id')!='V4_CURRENT_ACCEPTED_READ_CONTRACT_V1':
        raise SourceInvalid('CURRENT_READ_CONTRACT_REQUIRED')
    # Freeze one exact PG-ingressed contract value for every module gate.
    reader=CurrentAcceptedV4Reader(root,contract_path=candidate_path,follow_runtime=False)
    reader._contract=lambda:(contract,contract_digest)
    candidate=reader.load_context()
    for module in ['summary','radar','entity','sector','cohort','settlement','health']:
        code,value=reader.read(module)
        if code!=200:raise SourceInvalid('CANDIDATE_OWNER_GATE:'+module+':'+value.get('reason',''))
    today=(now or datetime.now(ZoneInfo('Asia/Shanghai'))).date().isoformat()
    if candidate['context']['accepted_trade_date']>today:raise SourceInvalid('FUTURE_INPUT_FORBIDDEN')
    from workbench_db.v4_forward_pg_r1 import ForwardFactStore
    from .current_v4_context import canonical
    candidate_fact=dict(contract_id='V4_CURRENT_ACCEPTED_VIEW_VALIDATED_CANDIDATE_R1',
        contract_source=dict(source_id=source_id_for_path(candidate_path),path=candidate_path,
            sha256=contract_digest,bytes=len(source['raw'])),
        contract_version=contract.get('version'),context=candidate['context'],
        context_token=candidate['context_token'],
        validated_modules=['summary','radar','entity','sector','cohort','settlement','health'],
        validation='ALL_MODULES_READ_FROM_EXACT_PG_INGRESS_BINDINGS',
        acceptance='NOT_REQUESTED_NO_HEAD_CAS')
    fact_key=digest(canonical(candidate_fact))
    store=ForwardFactStore(root,'data/v4/current_accepted_view_candidates_r1')
    descriptor=store.append('validated_candidate',fact_key,candidate_fact)
    if canonical(store.read(descriptor))!=canonical(candidate_fact):
        raise SourceInvalid('PG_CANDIDATE_VALIDATION_READBACK_MISMATCH')
    return dict(status='VALIDATED_CANDIDATE_PENDING_PUBLICATION',candidate_descriptor=descriptor,
        context=candidate,accepted_head_changed=False,workspace_authority_changed=False)


# Compatibility name for callers retained during the transition. This no
# longer publishes or promotes an accepted view.
publish_accepted_view=validate_current_view_candidate


def refresh_status(root,*,now=None):
    root=Path(root).resolve()
    from workbench_db.dm01_data_accepted_head_pg_r1 import read_current as read_data_head
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_bound
    head=read_data_head(root);candidate=head['candidate']
    calendar_binding=candidate.get('calendar')
    if not isinstance(calendar_binding,dict):raise SourceInvalid('PG_DATA_HEAD_CALENDAR_BINDING_MISSING')
    calendar_source=read_bound(root,calendar_binding['path'],calendar_binding['sha256'])
    if len(calendar_source['raw'])!=calendar_binding.get('bytes'):
        raise SourceInvalid('PG_DATA_HEAD_CALENDAR_SIZE_MISMATCH')
    calendar=calendar_source.get('value')
    sessions=calendar.get('session_dates') or calendar.get('sessions') if isinstance(calendar,dict) else None
    if not sessions:raise SourceInvalid('OFFICIAL_CALENDAR_UNAVAILABLE')
    if isinstance(sessions[0],dict):sessions=sorted(set(row['trade_date'] for row in sessions))
    accepted_date=candidate.get('accepted_trade_date')
    if not isinstance(accepted_date,str):raise SourceInvalid('PG_DATA_HEAD_T0_MISSING')
    context=dict(context=dict(accepted_trade_date=accepted_date),
        data_head_sha256=head['head_sha256'],generation=head['generation'],
        database_identity=head['database_identity'],source_mode='PG_DATA_ACCEPTED_HEAD')
    # The accepted PG calendar is the sole date authority. A local DM-01
    # candidate calendar must never extend the operational run horizon.
    now=now or datetime.now(ZoneInfo('Asia/Shanghai'))
    completed=[d for d in sessions if accepted_date<d<now.date().isoformat() or (d==now.date().isoformat() and now.hour>=15 and d>accepted_date)]
    return dict(status='WAIT_NEXT_ACCEPTED_INPUT' if not completed else 'COMPLETED_INPUT_CAPTURE_REQUIRED',next_completed_session=min(completed) if completed else None,
        source_requests=0,data_preserved=True,context=context,contract_id='V4_PG_DATA_HEAD_REFRESH_STATUS_R1',
        calendar_source=dict(path=calendar_binding['path'],sha256=calendar_binding['sha256']),
        worker_started=False)
