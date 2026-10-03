"""New R20R1 evidence only; historical R20 artifacts are never rewritten."""
import hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='7f97f4487e2c8aaccb7e7701af4ccfddfa7ddec9'
def ref(path,root=ROOT):
    raw=(Path(root)/path).read_bytes()
    return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def atomic(path,value,raw=False,root=ROOT):
    if not (path.startswith('reports/r20r1/') or path.startswith('docs/evidence/r20r1/')):raise ValueError('NEW_R20R1_NAMESPACE_ONLY')
    p=Path(root)/path;p.parent.mkdir(parents=True,exist_ok=True)
    data=value if raw else (json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode()
    if p.exists() and p.read_bytes()==data:return
    t=p.with_name(p.name+'.r20r1.tmp')
    with t.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(t,p)
