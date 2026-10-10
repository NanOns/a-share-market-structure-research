"""R3 evidence I/O: G-only, atomic; no production publication or source writes."""
from pathlib import Path
import gzip, hashlib, json, os, subprocess
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/v4_immediate_r3_20261010'
for key in ('TMP','TEMP','TMPDIR'):os.environ[key]='G:/codex_tmp'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
def path(ref):
    p=Path(ref['path'] if isinstance(ref,dict) else ref)
    return p if p.is_absolute() else ROOT/p
def sha(p):
    with path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def binding(p):
    p=path(p);return dict(path=p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p),sha256=sha(p),bytes=p.stat().st_size)
def checked(ref):
    assert sha(ref)==ref['sha256'],ref
    return path(ref)
def load(ref):
    p=checked(ref) if isinstance(ref,dict) else path(ref)
    with (gzip.open(p,'rt',encoding='utf8') if p.suffix=='.gz' else p.open(encoding='utf8')) as f:
        return [json.loads(s) for s in f if s.strip()] if '.jsonl' in p.name else json.load(f)
def write(p,value):
    p=path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(tmp,p)
def markdown(p,value):
    p=path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');tmp.write_text(value,encoding='utf8');os.replace(tmp,p)
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True,encoding='utf8').strip()
