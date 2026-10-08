"""R2 single atomic authority binds UI bytes, snapshot and operational scope."""
import json,os,uuid
from pathlib import Path
from .current_v4_context import canonical,digest,SourceInvalid
from .v4_daily_refresh import atomic_bytes

AUTHORITY='config/v4_joint_release_authority_v1.json'

def load(root):
    path=Path(root)/AUTHORITY
    if not path.exists():return None
    value=json.loads(path.read_bytes())
    if value.get('contract_id')!='V4_JOINT_RELEASE_V1':raise SourceInvalid('JOINT_CONTRACT_INVALID')
    return value

def checked_path(root,binding):
    root=Path(root).resolve();path=(root/binding['path']).resolve()
    if not path.is_relative_to(root):raise SourceInvalid('JOINT_PATH_OUTSIDE_PROJECT')
    if digest(path.read_bytes())!=binding['sha256']:raise SourceInvalid('JOINT_SOURCE_DIGEST_MISMATCH:'+binding['path'])
    return path

def validate(root,candidate):
    if candidate.get('contract_id')!='V4_JOINT_RELEASE_V1':raise SourceInvalid('JOINT_CONTRACT_INVALID')
    manifest=json.loads(checked_path(root,candidate['snapshot']['manifest']).read_bytes())
    checked_path(root,manifest['database'])
    for binding in manifest['sources'].values():checked_path(root,binding)
    for binding in candidate['ui_assets'].values():checked_path(root,binding)
    if manifest['context']['accepted_trade_date']!=candidate['trade_date']:raise SourceInvalid('JOINT_DATE_MISMATCH')
    # Production owner bindings must describe this exact snapshot, not merely
    # individually readable files from another accepted day or input head.
    owners=candidate.get('daily_owner_authorities')
    if owners is not None:
        for name in ('market','sector','stocks','market_center','forward'):
            owner=owners.get(name,{})
            if owner.get('trade_date')!=candidate['trade_date']:
                raise SourceInvalid('JOINT_OWNER_DATE_MISMATCH:'+name)
            head=owner.get('input_data_head',{})
            if head.get('sha256')!=manifest['context'].get('data_head_digest'):
                raise SourceInvalid('JOINT_OWNER_INPUT_HEAD_MISMATCH:'+name)
            # The accepted-head path is a moving pointer. Compare its frozen
            # identity to the manifest; read actual immutable payload bindings
            # below so a later input day does not invalidate a healthy rollback.
        features=manifest.get('domain_features',{})
        for name,keys in {'sector':('native','factors','profiles'),
                          'stocks':('series','factors','profiles')}.items():
            for key in keys:
                if owners[name].get(key)!=features.get(name,{}).get(key):
                    raise SourceInvalid('JOINT_OWNER_SNAPSHOT_BINDING_MISMATCH:'+name+':'+key)
                checked_path(root,owners[name][key])
        for name,key in (('market','market'),('market_center','publication'),('forward','publication')):
            binding=owners[name].get(key)
            if not binding or json.loads(checked_path(root,binding).read_bytes())!=features.get(name):
                raise SourceInvalid('JOINT_OWNER_SNAPSHOT_BINDING_MISMATCH:'+name+':'+key)
    if not candidate['operational_release_scope'] or candidate.get('trading') is not False:raise SourceInvalid('JOINT_SCOPE_INVALID')
    return manifest

def activate(root,candidate,expected,health):
    """One CAS covers all three authorities. On health failure restore exact bytes."""
    root=Path(root);path=root/AUTHORITY;lock=path.with_suffix('.lock');lock.parent.mkdir(parents=True,exist_ok=True)
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise SourceInvalid('JOINT_RELEASE_BUSY')
    os.write(fd,canonical(dict(pid=os.getpid())));os.fsync(fd);os.close(fd)
    before=path.read_bytes() if path.exists() else None
    run=uuid.uuid4().hex;folder=root/'runtime/joint_release'/run
    try:
        if (digest(before) if before else None)!=expected:raise SourceInvalid('JOINT_CAS_CONFLICT')
        validate(root,candidate)
        raw=canonical(candidate)
        if before==raw:return dict(result='NOOP',activation_performed=False,authority_digest=digest(raw))
        # An exact pointer restore is insufficient if its live dependencies have
        # become unreadable. Reject before CAS while the old authority is intact.
        if before is not None:validate(root,json.loads(before))
        folder.mkdir(parents=True)
        atomic_bytes(folder/'PREDECESSOR.json',canonical(dict(existed=before is not None,raw=before.decode() if before else None)))
        atomic_bytes(folder/'TRANSACTION.json',canonical(dict(state='PREPARED',candidate_digest=digest(raw))))
        atomic_bytes(path,raw)
        try:
            readback=health(candidate)
            if path.read_bytes()!=raw:raise SourceInvalid('JOINT_READBACK_CONFLICT')
            if not readback.get('pass'):raise SourceInvalid('JOINT_HEALTH_FAILED')
        except BaseException:
            if before is None:path.unlink()
            else:atomic_bytes(path,before)
            atomic_bytes(folder/'TRANSACTION.json',canonical(dict(state='ROLLED_BACK',exact_restore=(path.read_bytes() if path.exists() else None)==before)))
            raise
        receipt=dict(result='FULL_PRODUCT_RELEASE_PASS' if candidate.get('full_product_release') else 'SCOPED_OPERATIONAL_RELEASE_PASS',activation_performed=True,authority_digest=digest(raw),readback=readback,operational_release_scope=candidate['operational_release_scope'])
        atomic_bytes(folder/'RECEIPT.json',canonical(receipt))
        atomic_bytes(folder/'TRANSACTION.json',canonical(dict(state='COMMITTED',candidate_digest=digest(raw))))
        return receipt
    finally:lock.unlink()

def recover(root):
    """Startup recovery of interrupted post-CAS/pre-health transactions."""
    root=Path(root);path=root/AUTHORITY
    lock=path.with_suffix('.lock')
    if lock.exists():
        try:pid=json.loads(lock.read_bytes())['pid']
        except (ValueError,KeyError):raise SourceInvalid('JOINT_LOCK_OWNER_UNKNOWN')
        if os.name=='nt':
            import ctypes
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.OpenProcess.restype=ctypes.c_void_p
            handle=kernel.OpenProcess(0x1000,False,pid)
            if handle:
                kernel.CloseHandle.argtypes=[ctypes.c_void_p];kernel.CloseHandle(handle)
                raise SourceInvalid('JOINT_RELEASE_IN_PROGRESS')
            if ctypes.get_last_error()!=87:raise SourceInvalid('JOINT_LOCK_LIVENESS_UNPROVEN')
        else:
            try:os.kill(pid,0)
            except ProcessLookupError:pass
            else:raise SourceInvalid('JOINT_RELEASE_IN_PROGRESS')
        lock.unlink()
    for journal in sorted((root/'runtime/joint_release').glob('*/TRANSACTION.json')):
        state=json.loads(journal.read_bytes())
        if state['state']!='PREPARED':continue
        if not path.exists() or digest(path.read_bytes())!=state['candidate_digest']:continue
        predecessor=json.loads((journal.parent/'PREDECESSOR.json').read_bytes())
        if predecessor['existed']:atomic_bytes(path,predecessor['raw'].encode())
        else:path.unlink()
        atomic_bytes(journal,canonical(dict(state='RECOVERED_PREDECESSOR',exact_restore=True)))
