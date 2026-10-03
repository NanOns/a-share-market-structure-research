"""R20 governance artifact writes, outside source roots."""
import hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='2020234020e09020aca13fd84cdabde6fbb81f50'
def read(path):return json.loads((ROOT/path).read_bytes())
def ref(path):
    raw=(ROOT/path).read_bytes();return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def atomic(path,value,raw=False):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
    data=value if raw else (json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode()
    t=p.with_name(p.name+'.r20.tmp')
    with t.open('wb') as s:s.write(data);s.flush();os.fsync(s.fileno())
    os.replace(t,p)
