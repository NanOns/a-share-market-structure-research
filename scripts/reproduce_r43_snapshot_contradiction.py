"""Execute the frozen verifier before fixing it, preserving real failure evidence."""
import json
import ast
import gzip
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sector.membership_snapshot import build_snapshot
from workbench_analysis.tdx_member_retro_r43 import EVIDENCE,validate_snapshot,digest
from workbench_analysis.corrected_owner_replay import load,ref,checked
from workbench_analysis.market_source_acquisition import write
OUT=ROOT/'docs/evidence/r4_3_r1_targeted_repair_20261009'

def main():
    snapshot=load(ROOT/EVIDENCE/'MEMBER_SNAPSHOT_S.json')
    original=validate_snapshot(snapshot,ROOT)
    frame,_=build_snapshot(ROOT/EVIDENCE/'latest_member_parse',snapshot['membership_observed_at'])
    mapping={r['source_security_key'].upper():r for r in load(checked(ROOT,snapshot['identity_source']))['rows'] if r.get('identity_status')=='IDENTITY_BOUND'}
    reparsed=[]
    for row in frame.to_dict('records'):
        if row['sector_type'] not in ('INDUSTRY','THEME'):continue
        code=row['security_id'];ident=mapping.get(code)
        reparsed.append(dict(sector_id=row['sector_id'],sector_type=row['sector_type'],sector_code=row['sector_code'],sector_name=row['sector_name'],source_security_key=code,source=row['source'],security_id=ident['security_id'] if ident else None,identity_status='MAPPED' if ident else 'UNMAPPED_QUARANTINED',list_date=ident.get('list_date') if ident else None,delist_date=ident.get('delist_date') if ident else None))
    reparsed.sort(key=lambda r:(r['sector_type'],r['sector_id'],r['source_security_key']))
    samples=[]
    for kind in ['LEAF','PARENT_DERIVED','CONCEPT']:
        samples.extend(dict(original=a,reparsed=b) for a,b in list((a,b) for a,b in zip(original,reparsed) if ('PARENT_DERIVED' if 'DERIVED_PARENT' in a['source'] else 'LEAF' if a['sector_type']=='INDUSTRY' else 'CONCEPT')==kind)[:8])
    # Execute the current capture row-builder AST on the real frozen parser frame.
    # This preserves the actual code, avoiding a fabricated fresh-capture mismatch.
    code=OUT/'before_fix/tdx_member_retro_r43.py'
    if not code.is_file():code=ROOT/'src/workbench_analysis/tdx_member_retro_r43.py'
    tree=ast.parse(code.read_text(encoding='utf8'))
    capture=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='capture')
    row_loop=next(n for n in capture.body if isinstance(n,ast.For) and ast.unparse(n.iter)=="frame.to_dict('records')")
    scope=dict(frame=frame,mapping=mapping,rows=[],quarantine=[])
    exec(compile(ast.fix_missing_locations(ast.Module(body=[row_loop],type_ignores=[])),str(code),'exec'),scope)
    captured=sorted(scope['rows'],key=lambda r:(r['sector_type'],r['sector_id'],r['source_security_key']))
    command=[sys.executable,'-c',"import sys,importlib.util;from pathlib import Path;sys.path.insert(0,"+repr(str(ROOT/'src'))+");spec=importlib.util.spec_from_file_location('workbench_analysis.r43_before_fix',"+repr(str(code))+");module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.reparse_verification(Path.cwd())"]
    sandbox=Path('E:/codex_tmp/r43_r1_reparse_before_fix');sandbox.mkdir(parents=True,exist_ok=True)
    bindings=[snapshot['memberships'],snapshot['identity_source']]+snapshot['sources']
    for b in bindings:
        target=sandbox/b['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(checked(ROOT,b),target)
    for p in list((ROOT/EVIDENCE/'latest_member_parse').rglob('*'))+[ROOT/EVIDENCE/'01_LATEST_TDX_INDUSTRY_CONCEPT_CAPTURE_LEDGER.json',code,ROOT/'src/sector/membership_snapshot.py',ROOT/'src/tdx/block_reader.py']:
        if p.is_file():
            target=sandbox/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    verifier=sandbox/'src/workbench_analysis/tdx_member_retro_r43.py';verifier.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(code,verifier)
    sp=sandbox/EVIDENCE/'MEMBER_SNAPSHOT_S.json';sp.write_text(json.dumps(snapshot),encoding='utf8')
    env=__import__('os').environ|{'PYTHONPATH':str(ROOT/'src'),'PYTHONIOENCODING':'utf8','PYTHONUTF8':'1'}
    legacy=subprocess.run(command,cwd=sandbox,text=True,capture_output=True,encoding='utf8',env=env)
    assert legacy.returncode==0
    mp=sandbox/snapshot['memberships']['path']
    with gzip.open(mp,'wt',encoding='utf8') as f:
        for row in captured:f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n')
    fresh=dict(snapshot,member_digest=digest(captured),membership_snapshot_id='TDX_MEMBER_SNAPSHOT_S_20261009_'+digest(captured),memberships=ref(sandbox,mp))
    sp.write_text(json.dumps(fresh),encoding='utf8')
    run=subprocess.run(command,cwd=sandbox,text=True,capture_output=True,encoding='utf8',env=env)
    assert run.returncode!=0 and 'AssertionError' in run.stderr
    write(OUT/'R43_SOURCE_REPARSE_FAILURE_REPRODUCTION.json',dict(command=command,cwd=str(sandbox),exit_code=run.returncode,stdout=run.stdout,traceback=run.stderr,legacy_verifier=dict(exit_code=legacy.returncode,stdout=legacy.stdout,stderr=legacy.stderr),executed_verifier=ref(ROOT,code),capture_projection_execution='Exact current capture for-loop AST, real frozen parser frame and canonical identity mapping; no live TDX capture',frozen_sources=snapshot['sources'],original_field_names=sorted(set().union(*(r.keys() for r in original))),current_capture_field_names=sorted(set().union(*(r.keys() for r in captured))),reparsed_field_names=sorted(set().union(*(r.keys() for r in reparsed))),original_digest=digest(original),current_capture_digest=digest(captured),reparsed_digest=digest(reparsed),relation_count=len(original),legacy_mismatched_records=sum(a!=b for a,b in zip(original,reparsed)),mismatched_current_capture_records=sum(a!=b for a,b in zip(captured,reparsed)),first_difference=next(dict(index=i,capture=a,reparse=b) for i,(a,b) in enumerate(zip(captured,reparsed)) if a!=b),samples=samples,conclusion='LEGACY_FROZEN_S_HAS_TEN_FIELDS_AND_OLD_VERIFIER_SUCCEEDS; CURRENT_CAPTURE_TWELVE_FIELDS_FAILS_OLD_VERIFIER; DO_NOT_FABRICATE_LEGACY_FAILURE'))
    print(json.dumps(dict(actual_verifier_exit_code=run.returncode,legacy_verifier_exit_code=legacy.returncode,mismatched_current_capture_records=sum(a!=b for a,b in zip(captured,reparsed)),samples=len(samples))))

if __name__=='__main__':main()
