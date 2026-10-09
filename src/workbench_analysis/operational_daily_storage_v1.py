"""Atomic project writes and kernel-owned cross-process locks (crash releases)."""
from contextlib import contextmanager
from pathlib import Path
import json,os,tempfile
from .daily_source_freeze import ensure_outside_tdx


def output_path(root,path):
    root=Path(root).resolve();path=Path(path).resolve()
    if not path.is_relative_to(root):
        raise ValueError('OUTPUT_OUTSIDE_PROJECT')
    roots=['D:/new_tdx']
    contract=root/'config/dm01_go_forward_runtime_contract_r4r1.json'
    if contract.is_file():
        roots+=json.loads(contract.read_bytes()).get('read_only_tdx_roots',[])
    for tdx in roots:
        ensure_outside_tdx(path,Path(tdx))
    return path


def atomic_json(root,path,payload):
    path=output_path(root,path);path.parent.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode()
    fd,name=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        Path(name).unlink(missing_ok=True)


@contextmanager
def exclusive_lock(root,path):
    path=output_path(root,path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as stream:
        stream.seek(0,2)
        if stream.tell()==0:
            stream.write(b'0');stream.flush()
        stream.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name=='nt':
                msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                fcntl.flock(stream,fcntl.LOCK_UN)
