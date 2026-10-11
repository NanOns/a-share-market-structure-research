"""Rehash original bound inputs; never follow the isolated fixture root."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.audit_full_system_r4_scope import OUT,write,sha

def main():
    origin=Path('G:/codex work/大A交易').resolve()
    baseline=json.loads((OUT/'R4_PROTECTED_BEFORE.json').read_bytes())['records']
    records=[];differences=[]
    for i,item in enumerate(baseline):
        path=Path(item['path']);path=path if path.is_absolute() else origin/path
        actual=sha(path) if path.is_file() else None
        record=dict(path=str(path),before_sha256=item['sha256'],after_sha256=actual,unchanged=actual==item['sha256']);records.append(record)
        if not record['unchanged']:differences.append(record)
        if (i+1)%2000==0:print(json.dumps(dict(rehashed=i+1,total=len(baseline))),flush=True)
    write('R4_PROTECTED_AFTER.json',dict(protected_original_root=str(origin),denominator=len(records),records=records,differences=differences,current_status='BOUND_ORIGINAL_BYTES_UNCHANGED' if not differences else 'PROTECTED_READBACK_DIFFERENCE_REVIEW_REQUIRED',limitations=['Bound frozen inputs only; not a full TDX directory inventory or proof of production PG identity','Live operational files can change naturally; every difference must be reviewed rather than silently ignored'],next_conditions=['Independent protected-root and production identity verification']))
    print(json.dumps(dict(records=len(records),differences=len(differences))))
    return int(bool(differences))
if __name__=='__main__':raise SystemExit(main())
