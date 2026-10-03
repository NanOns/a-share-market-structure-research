"""Clean detached final-source regression with verified local LFS hydration."""
import sys,json,subprocess,hashlib
from pathlib import Path
from scripts import validate_r17r1_clean_detached as checkout
ROOT=Path(__file__).resolve().parents[1]
checkout.CHECKOUT=ROOT.parent/'r18-clean-validation'

def run(source,output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True);hydrated=checkout.prepare(source);directory=checkout.CHECKOUT
    before=checkout.call(['git','status','--porcelain'],cwd=directory)
    result=subprocess.run([sys.executable,'-m','scripts.validate_r18_regression',str(output)],cwd=directory,capture_output=True,text=True,encoding='utf8',errors='replace')
    (output/'clean_runner.log').write_text(result.stdout+result.stderr,encoding='utf8')
    after=checkout.call(['git','status','--porcelain'],cwd=directory);g=json.loads((output/'regression_gate.json').read_bytes())
    receipt=dict(source_sha=source,status='PASS' if result.returncode==0 and before==after==b'' else 'FAIL',git_status_before=before.decode(),git_status_after=after.decode(),hydrated_verified_lfs_objects=hydrated,no_assume_unchanged_or_skip_worktree=True,test_totals=dict(passed=g['pass_count'],failed=len(g['failures']),errors=len(g['errors']),skipped=len(g['skipped']),deselected=g['deselected_count']),regression_gate_sha256=hashlib.sha256((output/'regression_gate.json').read_bytes()).hexdigest())
    (output/'clean_detached.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n',encoding='utf8');assert receipt['status']=='PASS',receipt
    return receipt
if __name__=='__main__':print(json.dumps(run(*sys.argv[1:]),sort_keys=True))
