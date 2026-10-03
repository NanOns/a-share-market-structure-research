"""Clean detached checkout with verified local LFS objects, no index bypass flags."""
from pathlib import Path
import os,subprocess,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
CHECKOUT=ROOT.parent/'r17r1-clean-validation'
def call(args,cwd=ROOT,**kw):return subprocess.check_output(args,cwd=cwd,**kw)
def prepare(source):
    env=dict(os.environ,GIT_LFS_SKIP_SMUDGE='1')
    if CHECKOUT.exists():
        assert not call(['git','status','--porcelain'],cwd=CHECKOUT).strip()
        call(['git','checkout','--detach',source],cwd=CHECKOUT,env=env)
    else:call(['git','worktree','add','--detach',str(CHECKOUT),source],env=env)
    common=Path(call(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True,encoding='utf8').strip())
    if not common.is_absolute():common=(ROOT/common).resolve()
    names=call(['git','lfs','ls-files','--name-only'],cwd=CHECKOUT,text=True,encoding='utf8').splitlines()
    hydrated=0
    for name in names:
        target=CHECKOUT/name
        if target.stat().st_size>1024:continue
        raw=target.read_bytes()
        if not raw.startswith(b'version https://git-lfs.github.com/spec/v1'):continue
        lines=raw.decode().splitlines();oid=next(x.split('sha256:')[1] for x in lines if x.startswith('oid '));size=int(next(x.split()[1] for x in lines if x.startswith('size ')))
        obj=common/'lfs/objects'/oid[:2]/oid[2:4]/oid
        assert obj.stat().st_size==size
        with obj.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==oid
        target.unlink();os.link(obj,target);hydrated+=1
    if names:call(['git','add','-f','--',*names],cwd=CHECKOUT)
    assert subprocess.run(['git','diff','--cached','--quiet','--exit-code'],cwd=CHECKOUT).returncode==0
    assert not call(['git','status','--porcelain'],cwd=CHECKOUT).strip()
    return hydrated
def run(stage,output,source=None):
    source=source or call(['git','rev-parse','HEAD'],text=True).strip();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    hydrated=prepare(source);before=call(['git','status','--porcelain'],cwd=CHECKOUT)
    result=subprocess.run([sys.executable,'-m','scripts.validate_r17r1_regression',str(output)],cwd=CHECKOUT,capture_output=True,text=True,encoding='utf8',errors='replace')
    (output/'clean_runner.log').write_text(result.stdout+result.stderr,encoding='utf8')
    after=call(['git','status','--porcelain'],cwd=CHECKOUT)
    gate=json.loads((output/'regression_gate.json').read_bytes())
    refs={}
    for p in ['AGENTS.md','data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_12_ACCEPTED_HEAD.json','data/v4/V4_13_ACCEPTED_HEAD.json']:
        if (CHECKOUT/p).exists():
            raw=(CHECKOUT/p).read_bytes();refs[p]=dict(path=p,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    receipt=dict(stage=stage,source_sha=source,status='PASS' if result.returncode==0 and before==after==b'' else 'FAIL',git_clean_before=not before,git_clean_after=not after,hydrated_verified_lfs_objects=hydrated,head_bindings=refs,test_totals=dict(passed=gate['pass_count'],failed=len(gate['failures']),errors=len(gate['errors']),skipped=len(gate['skipped']),deselected=gate['deselected_count']),regression_gate_sha256=hashlib.sha256((output/'regression_gate.json').read_bytes()).hexdigest(),no_assume_unchanged_or_skip_worktree=True)
    (output/'clean_detached.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n',encoding='utf8')
    assert receipt['status']=='PASS',receipt
    print(json.dumps(receipt))
if __name__=='__main__':run(*sys.argv[1:])
