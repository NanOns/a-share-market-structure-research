"""Exact versioned integration governance IO; no accepted namespace writes."""
import hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='0a6b8b0553ac9503b1d6a78681659b35c2ba934e'
from scripts.r20r1r1_io import ref,exact as _exact

def exact(binding,root=ROOT):
    if 'byte_count' in binding and 'bytes' not in binding:
        binding=dict(path=binding['path'],sha256=binding['sha256'],bytes=binding['byte_count'])
    return _exact(binding,root)

def require(ok,message):
    if not ok:raise ValueError(message)

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def atomic(path,value,root=ROOT,raw=False,immutable=False):
    root=Path(root).resolve();p=(root/path).resolve()
    require(any(p.is_relative_to(root/n) for n in ['reports/r20r1r2','docs/evidence/r20r1r2']),'VERSIONED_NAMESPACE_ONLY')
    data=value if raw else (json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
    if p.exists():
        if p.read_bytes()==data:return ref(path,root)
        require(not immutable,'APPEND_ONLY_BYTES_CHANGED')
    p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp')
    with t.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(t,p);return ref(path,root)
