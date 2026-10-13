"""One complete frozen legal regression after historical fixture convergence."""
import hashlib,json,os,subprocess
from pathlib import Path
from scripts.v4_closeout_regression_continuation_r3 import ROOT,OUT,historical_modules,execute

DOC=ROOT/'docs/audits/v4_full_closeout_20261012/continuation_20261013/FINAL_REGRESSION_R4'

def main():
    DOC.mkdir(parents=True,exist_ok=False)
    prior=json.loads((OUT/'FINAL_LEGAL_COLLECTION_R3.json').read_bytes())
    nodes=prior['nodes'];assert len(nodes)==7288 and len(set(nodes))==7288
    historical=historical_modules()
    def old(node):return node.split('::')[0] in historical or node.startswith(('tests/upgrade_m','tests/upgrade_v3/'))
    groups={'native':[n for n in nodes if not old(n)],'historical':[n for n in nodes if old(n)]}
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    paths=sorted({n.split('::')[0] for n in nodes}|{p for p in tracked if p and (p.startswith(('tests/','src/','scripts/','config/')) or p=='conftest.py') and (ROOT/p).is_file()})
    hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    manifest=dict(contract_id='V4_COMPLETE_LEGAL_FINAL_SOURCE_FREEZE_R4',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),denominator=len(nodes),nodes=nodes,profiles=groups,source_sha256=hashes,exclusions=[],original_7288_preserved=True,shadow44_current_native=True,production_cutover=False)
    (DOC/'FREEZE.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    result={}
    for name,native in [('native',True),('historical',False)]:
        assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in hashes.items()),'FROZEN_SOURCE_DRIFT'
        result[name]=execute('FINAL_COMPLETE_'+name.upper()+'_R4',groups[name],native)
    drift=[p for p,sha in hashes.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=sha]
    (DOC/'EXECUTION.json').write_text(json.dumps(dict(exit_codes=result,source_drift=drift,denominator=len(nodes),acceptance='EXECUTED_RECONCILIATION_REQUIRED',production_cutover=False),indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(exit_codes=result,source_drift=drift)),flush=True)
    return max(result.values())

if __name__=='__main__':raise SystemExit(main())
