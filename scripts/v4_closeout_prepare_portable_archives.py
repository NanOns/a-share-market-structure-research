"""Offline exact Git witness for frozen three-source archives in formal staging."""
import json,hashlib,subprocess,os
from pathlib import Path
from workbench_analysis.portable_historical_archives_r1 import CONTRACT,PATH,BOOK
from workbench_analysis.r43_owner_replay import checked,ref

ROOT=Path(__file__).resolve().parents[1]
STAGING=Path('G:/codex work/v4-production-20261012')

def main():
    book=json.loads((ROOT/BOOK).read_bytes());rows=[]
    for row in book['entries']:
        raw=checked(ROOT,row['archive']).read_bytes()
        original=subprocess.check_output(['git','show',row['source_commit']+':'+row['original']['path']],cwd=ROOT)
        if raw!=original or hashlib.sha256(raw).hexdigest()!=row['original']['sha256']:
            raise ValueError('PORTABLE_OFFLINE_EXACT_GIT_WITNESS_REQUIRED')
        rows.append(dict(row,verified_git_blob_sha256=hashlib.sha256(original).hexdigest()))
        staged=STAGING/row['archive']['path']
        if staged.read_bytes()!=raw:raise ValueError('PRESERVE_FORMAL_ARCHIVE_BYTES')
    if (STAGING/BOOK).read_bytes()!=(ROOT/BOOK).read_bytes():raise ValueError('PRESERVE_FORMAL_HISTORICAL_REGISTRY')
    document=dict(contract_id=CONTRACT,authority_granted=False,production_permission=False,
        registry_binding=ref(ROOT,ROOT/BOOK),entries=rows,scope='IDENTICAL_SIGNED_ORIGINAL_BYTES_LOCATION_ONLY',
        git_repository_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    for root in (ROOT,STAGING):
        p=root/PATH
        if p.exists():raise ValueError('PRESERVE_PRIOR_PORTABLE_WITNESS')
        tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(document,indent=2),encoding='utf8');os.replace(tmp,p)
    print(json.dumps(dict(status='EXACT_OFFLINE_GIT_WITNESS_PREPARED',sources=len(rows),authority_granted=False)))

if __name__=='__main__':main()
