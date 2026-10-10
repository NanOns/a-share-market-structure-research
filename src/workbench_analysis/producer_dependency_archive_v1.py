"""Freeze exact computation dependencies for historical research readback."""
from pathlib import Path
import hashlib
from .r43_owner_replay import checked
from .tdx_official_daily_source import _atomic_write

CONTRACT='PRODUCER_COMPUTATION_DEPENDENCY_ARCHIVE_V1'


def freeze_dependencies(root,bindings):
    root=Path(root).resolve()
    if root.drive.upper()!='G:':raise ValueError('G_STORAGE_REQUIRED')
    receipts=[]
    for binding in bindings:
        relative=Path(binding['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('DEPENDENCY_PATH_ESCAPE')
        if not relative.parts or relative.parts[0] not in ('src','config'):continue
        source=checked(root,binding)
        raw=source.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=binding['sha256']:
            raise ValueError('DEPENDENCY_CHANGED_DURING_FREEZE')
        path='docs/evidence/producer_dependency_archive_v1/'+binding['sha256']+'.bin'
        target=root/path
        if target.exists():
            if target.read_bytes()!=raw:raise ValueError('FROZEN_DEPENDENCY_ARCHIVE_MUTATED')
        else:
            _atomic_write(target,raw,tdx_root=Path('D:/new_tdx'))
        receipts.append(dict(binding,path=path))
    return receipts
