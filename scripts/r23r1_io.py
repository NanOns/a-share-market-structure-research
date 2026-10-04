"""Atomic, scoped R23R1 evidence writes."""
import hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='9724b0b2091b0d1e0ca55af17e1fc8c3948fdf42'
def read(path,root=ROOT):return json.loads((Path(root)/path).read_bytes())
def ref(path,root=ROOT):
    raw=(Path(root)/path).read_bytes()
    return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def atomic(path,value,root=ROOT,raw=False):
    p=(Path(root)/path).resolve()
    if not p.is_relative_to(Path(root).resolve()) or not path.startswith(('reports/r23r1/','docs/evidence/r23r1/')):raise ValueError('R23R1_OUTPUT_ONLY')
    data=value if raw else (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode()
    p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_name(p.name+'.tmp')
    with temp.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(temp,p);return ref(path,root)
