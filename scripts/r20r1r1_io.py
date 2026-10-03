"""Atomic versioned governance artifacts, never writes accepted source authority."""
import hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='555409d79c58517761472531404f0ee5cccd81af'
def ref(path,root=ROOT):
    raw=(Path(root)/path).read_bytes();return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def exact(binding,root=ROOT):
    path=(Path(root)/binding['path']).resolve()
    if not path.is_relative_to(Path(root).resolve()):raise ValueError('PATH_ESCAPE')
    if ref(binding['path'],root)!=binding:raise ValueError('EXACT_BINDING_MISMATCH')
    return json.loads(path.read_bytes()) if path.suffix=='.json' else path.read_bytes()
def atomic(path,value,root=ROOT,raw=False,immutable=False):
    if not path.startswith(('reports/r20r1r1/','docs/evidence/r20r1r1/')):raise ValueError('NEW_GOVERNANCE_NAMESPACE_ONLY')
    p=(Path(root)/path).resolve()
    allowed=[(Path(root)/name).resolve() for name in ['reports/r20r1r1','docs/evidence/r20r1r1']]
    if not any(p.is_relative_to(a) for a in allowed):raise ValueError('PATH_ESCAPE')
    p.parent.mkdir(parents=True,exist_ok=True)
    data=value if raw else (json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    if p.exists():
        if p.read_bytes()==data:return ref(path,root)
        if immutable:raise ValueError('APPEND_ONLY_BYTES_CHANGED')
    tmp=p.with_name(p.name+'.tmp')
    with tmp.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(tmp,p);return ref(path,root)
