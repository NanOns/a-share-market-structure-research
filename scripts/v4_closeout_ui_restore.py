"""Recover exact missing bound product inputs into an isolated G: candidate.

Never alters a bound file already present, the archived originals, or authority.
"""
import argparse
import hashlib
import json
from pathlib import Path
import os
import sys

SOURCE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(SOURCE),str(SOURCE/'src')]
sys.dont_write_bytecode=True
os.environ.update(TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp')


def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--archive',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    root,archive,out=(Path(x).resolve() for x in (a.candidate,a.archive,a.out))
    if root.drive.upper()!='G:' or archive.drive.upper()!='G:' or out.drive.upper()!='G:' or not root.is_relative_to(Path('G:/codex_tmp').resolve()):raise SystemExit('G_ISOLATED_RESTORE_REQUIRED')
    from workbench_service.v4_daily_refresh import atomic_bytes
    bindings=[];results=[]
    def collect(value):
        if isinstance(value,dict):
            if value.get('path') and value.get('sha256'):bindings.append(value)
            for child in value.values():collect(child)
        elif isinstance(value,list):
            for child in value:collect(child)
    protected={}
    for name in ('core_product_read_authority_r1.json','core_product_focus_read_authority_r2.json'):
        path=root/'config'/name
        if path.exists():
            protected[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest();value=json.loads(path.read_bytes());collect(value)
    seen=set()
    for binding in bindings:
        relative=binding['path']
        if relative in seen:continue
        seen.add(relative);target=(root/relative).resolve();source=(archive/relative).resolve()
        if not target.is_relative_to(root) or not source.is_relative_to(archive):raise SystemExit('BINDING_PATH_ESCAPE')
        if not target.exists():
            if not source.is_file():results.append(dict(binding=binding,result='SOURCE_MISSING'));continue
            raw=source.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=binding['sha256']:results.append(dict(binding=binding,result='ARCHIVE_SHA_MISMATCH'));continue
            atomic_bytes(target,raw);results.append(dict(binding=binding,result='RESTORED_EXACT_BYTES'))
        elif hashlib.sha256(target.read_bytes()).hexdigest()!=binding['sha256']:
            results.append(dict(binding=binding,result='EXISTING_SHA_MISMATCH_NOT_OVERWRITTEN'));continue
        else:results.append(dict(binding=binding,result='ALREADY_EXACT'))
        if target.name in ('MANIFEST.json','snapshot.pg.json','HISTORY_INDEX.json'):
            collect(json.loads(target.read_bytes()))
    if any(hashlib.sha256(Path(name).read_bytes()).hexdigest()!=sha for name,sha in protected.items()):raise SystemExit('AUTHORITY_CHANGED')
    result=dict(contract='EXACT_ARCHIVE_PRODUCT_INPUT_RESTORE_V1',candidate=str(root),archive=str(archive),authority_unchanged=True,restored_inputs=results,acceptance='FAIL' if any(x['result'] in ('SOURCE_MISSING','ARCHIVE_SHA_MISMATCH','EXISTING_SHA_MISMATCH_NOT_OVERWRITTEN') for x in results) else 'EXACT_INPUT_RECOVERY_ONLY_NOT_PG_OR_PRODUCT_ACCEPTANCE')
    atomic_bytes(out,json.dumps(result,ensure_ascii=False,indent=2).encode());print(json.dumps(dict(status=result['acceptance'],counts={state:sum(x['result']==state for x in results) for state in {x['result'] for x in results}})))


if __name__=='__main__':main()
