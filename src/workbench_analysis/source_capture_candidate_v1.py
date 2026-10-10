"""Append-only source observations; candidates never confer PIT authority."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib
import os
import tempfile
from .v4_14_replay_io import publish, digest, ref, path_in

CONTRACT = 'FIRST_CAPTURE_SOURCE_CANDIDATE_V1'


def instant(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('AWARE_TIMESTAMP_REQUIRED')
    return result


def capture(root, *, trade_date, sessions, calendar_binding, sources,
            security_ids, sector_ids, model_binding, config_binding,
            namespace='data/v4/source_candidates', research_replay=False,
            preliminary_scope=None):
    """Read sources now, retaining their actual request/receive times.

    No injected production clock, no grant prerequisite, no accepted Head write.
    Same content slot returns the first observation; changed bytes append a slot.
    """
    root = Path(root).resolve()
    if root.drive.upper() != 'G:':
        raise ValueError('G_STORAGE_REQUIRED')
    if namespace != 'data/v4/source_candidates':
        raise ValueError('ISOLATED_NAMESPACE_REQUIRED')
    now = datetime.now(timezone.utc)
    today = now.astimezone(timezone(timedelta(hours=8))).date().isoformat()
    if trade_date not in sessions or (not research_replay and trade_date != today):
        raise ValueError('REAL_CURRENT_SESSION_REQUIRED')
    if not sources or not security_ids or len(set(security_ids)) != len(security_ids):
        raise ValueError('COMPLETE_SCOPE_REQUIRED')
    if len(set(sector_ids)) != len(sector_ids):
        raise ValueError('DUPLICATE_SECTOR_SCOPE')
    # Bind calendar and computation identities without treating them as grants.
    for binding in (calendar_binding, model_binding, config_binding):
        from .r43_owner_replay import checked
        checked(root, binding)
    observations = []
    names = set()
    for source in sources:
        if source['name'] in names:
            raise ValueError('DUPLICATE_SOURCE_NAME')
        names.add(source['name'])
        requested = instant(source['requested_at']) if source.get('requested_at') else None
        received = instant(source['received_at'])
        if received > now or (requested is not None and requested > received):
            raise ValueError('SOURCE_TIMESTAMP_ORDER_REQUIRED')
        path = Path(source['path'])
        if not path.is_absolute():
            path = root / path
        local_requested = datetime.now(timezone.utc)
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
        local_received = datetime.now(timezone.utc)
        if source.get('timestamp_basis') == 'LOCAL_READ':
            requested, received = local_requested, local_received
            source = dict(source, requested_at=requested.isoformat(), received_at=received.isoformat())
        sha = hashlib.sha256(raw).hexdigest()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('SOURCE_CHANGED_DURING_CAPTURE')
        if source.get('sha256') and source['sha256'] != sha:
            raise ValueError('SOURCE_SHA_MISMATCH')
        same_day = (received.astimezone(timezone(timedelta(hours=8))).date().isoformat() == trade_date
                    and source['trade_date'] == trade_date and not research_replay)
        relative = f'{namespace}/bytes/{sha}.bin'
        _, target = path_in(root, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target.parent, prefix='.capture-')
        try:
            with os.fdopen(fd, 'wb') as out:
                out.write(raw); out.flush(); os.fsync(out.fileno())
            try:
                os.link(tmp, target)
            except FileExistsError:
                if target.read_bytes() != raw:
                    raise ValueError('SOURCE_BLOB_COLLISION')
        finally:
            os.unlink(tmp)
        observations.append(dict(name=source['name'], original_path=str(path),
            original_bytes=ref(root, relative), requested_at=source.get('requested_at'),
            received_at=source['received_at'], first_available=source.get('first_available', source['received_at']),
            trade_date=source['trade_date'], observation_class='CURRENT_SOURCE_OBSERVED' if same_day else 'RECONSTRUCTED',
            timestamp_basis=source.get('timestamp_basis','SOURCE_RECEIPT'),
            AS_RECORDED=False, first_capture_admission='INDEPENDENT_REVIEW_REQUIRED'))
        available=instant(observations[-1]['first_available'])
        if available > received or (requested is not None and requested > available):
            raise ValueError('SOURCE_AVAILABILITY_ORDER_REQUIRED')
    identity = dict(format_version=2,T0=trade_date, sources=observations, security_ids=sorted(security_ids),
                    sector_ids=sorted(sector_ids), calendar=calendar_binding,
                    model=model_binding, config=config_binding, research_replay=research_replay)
    if preliminary_scope is not None:
        identity.update(scope_class='PRELIMINARY_PREVIOUS_HEAD_SCOPE',
                        scope_status='PROVISIONAL_SCOPE', preliminary_scope=preliminary_scope,
                        capture_status='SOURCE_BYTES_CAPTURED')
    slot = digest(dict(identity, sources=[dict(name=r['name'],sha256=r['original_bytes']['sha256'],
        trade_date=r['trade_date'],observation_class=r['observation_class']) for r in observations]))
    path = f'{namespace}/{trade_date}/{slot}/capture.json'
    _, existing = path_in(root, path)
    if existing.exists():
        return ref(root, path)
    return publish(root, path, dict(identity, contract_id=CONTRACT, captured_at=datetime.now(timezone.utc).isoformat(),
        production=False, formal_consumer_enabled=False, PIT_ELIGIBLE=False,
        evidence_class='RECONSTRUCTED_RESEARCH_ONLY' if research_replay else 'CURRENT_OBSERVATION_CANDIDATE',
        gaps=([r['name']+':RECONSTRUCTED' for r in observations if r['observation_class']=='RECONSTRUCTED']
              +[r['name']+':REQUEST_TIME_UNKNOWN' for r in observations if r['requested_at'] is None]),
        next_gate='INDEPENDENT_SOURCE_ADMISSION'))
