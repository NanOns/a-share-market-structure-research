"""Canonical replay artifacts with atomic no-clobber publication."""
import hashlib,json,os,tempfile
from pathlib import Path
def path_in(root,path):
    root=Path(root).resolve();relative=Path(path)
    if relative.is_absolute() or '..' in relative.parts:raise ValueError('REPLAY_PATH_ESCAPE')
    # Resolve directories, preserving the requested final hard-link name on
    # Windows. GetFinalPathNameByHandle can report another link to that file.
    p=root/relative;parent=p.parent.resolve()
    if not parent.is_relative_to(root) or p.is_symlink():raise ValueError('REPLAY_PATH_ESCAPE')
    return root,parent/p.name
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def ref(root,path):
    root,p=path_in(root,path)
    raw=p.read_bytes();return dict(path=p.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def exact(root,binding):
    root,p=path_in(root,binding['path'])
    raw=p.read_bytes()
    if len(raw)!=binding.get('bytes',binding.get('byte_count')) or hashlib.sha256(raw).hexdigest()!=binding['sha256']:raise ValueError('REPLAY_EXACT_REF_MISMATCH')
    return raw
def publish(root,path,value):
    root,p=path_in(root,path)
    p.parent.mkdir(parents=True,exist_ok=True);raw=canonical(value)+b'\n'
    fd,tmp=tempfile.mkstemp(dir=p.parent,prefix='.replay-')
    try:
        with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        try:os.link(tmp,p)
        except FileExistsError:
            if p.read_bytes()!=raw:raise ValueError('REPLAY_CHANGED_BYTE_OVERWRITE_FORBIDDEN')
    finally:os.unlink(tmp)
    return ref(root,path)
