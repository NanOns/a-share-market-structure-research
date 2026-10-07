"""Clean sparse Git checkout replay of all registered historical identities."""
import os,subprocess,json,uuid,sys
from pathlib import Path
from tests.final_disposable_paths import resolve_destination_inside_root
from scripts.full_chain_repair_io import ROOT,write,binding
P='reports/forward_r2_remainder_consolidated_20261007/'
def run():
    base=Path('G:/codex_tmp/test_temp');index=resolve_destination_inside_root(base,'remainder_index_'+uuid.uuid4().hex)
    env=dict(os.environ,GIT_INDEX_FILE=str(index))
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,env=env,text=True).strip()
    original=git('rev-parse','HEAD');git('read-tree','HEAD')
    paths=['src/workbench_analysis/historical_binding_routing_remainder.py','config/v4_historical_binding_routing_remainder_v1.json','docs/evidence/forward_r2_remainder_consolidated_20261007/.gitattributes','docs/evidence/forward_r2_remainder_consolidated_20261007/historical_blobs']
    git('add','--',*paths);tree=git('write-tree')
    commit=original if tree==git('rev-parse',original+'^{tree}') else git('commit-tree',tree,'-p',original,'-m','Isolated historical-reader replay tree; no branch movement')
    out=resolve_destination_inside_root(base,'remainder_clean_reader_'+uuid.uuid4().hex[:10])
    subprocess.run(['git','clone','--shared','--no-checkout',str(ROOT),str(out)],check=True)
    subprocess.run(['git','-C',str(out),'config','core.longpaths','true'],check=True)
    subprocess.run(['git','-C',str(out),'sparse-checkout','init','--no-cone'],check=True)
    patterns=['/src/workbench_analysis/historical_binding_routing_remainder.py','/config/v4_historical_binding_routing_remainder_v1.json','/docs/evidence/forward_r2_remainder_consolidated_20261007/.gitattributes','/docs/evidence/forward_r2_remainder_consolidated_20261007/historical_blobs/']
    subprocess.run(['git','-C',str(out),'sparse-checkout','set','--no-cone',*patterns],check=True)
    subprocess.run(['git','-C',str(out),'-c','core.autocrlf=false','checkout','--detach',commit],check=True)
    code="import runpy,json,hashlib;from pathlib import Path;m=runpy.run_path('src/workbench_analysis/historical_binding_routing_remainder.py');r=m['HistoricalExactReader'](Path.cwd());checks=[hashlib.sha256(r.read(x['binding'])[0]).hexdigest()==x['binding']['sha256'] for x in r.registry['occurrences']];assert len(checks)==20 and all(checks);print(json.dumps({'occurrences':len(checks),'unique_identities':len(r.registry['entries']),'all_exact':all(checks)}))"
    result=json.loads(subprocess.check_output([sys.executable,'-c',code],cwd=out,text=True))
    clean=subprocess.check_output(['git','status','--porcelain'],cwd=out,text=True);assert not clean
    assert git('rev-parse','HEAD')==original
    write(P+'IA08_CLEAN_CHECKOUT_REPLAY.json',dict(status='PASS',result=result,root=str(out),tree=tree,replay_commit=commit,source_parent=original,branch_moved=False,clean_status=clean,source_bindings=[binding(paths[0]),binding(paths[1])],historical_permission=False))
if __name__=='__main__':run()
