"""G-local formal staging fork; original service and Head bytes stay protected."""
import hashlib,json,os,shutil
from pathlib import Path
SOURCE=Path('G:/codex_tmp/v4_ui_default_r1')
TARGET=Path('G:/codex work/v4-production-20261012')
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012/formal_workspace')

def main():
    if (TARGET/'FORMAL_STAGING_FORK.json').exists():raise ValueError('PRESERVE_EXISTING_FORMAL_STAGING_FORK')
    if (TARGET/'data').exists():raise ValueError('DO_NOT_OVERWRITE_EXISTING_FORMAL_DATA')
    heads=('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json')
    before={name:(SOURCE/name).read_bytes() for name in heads}
    OUT.mkdir(parents=True,exist_ok=True);count=linked=copied=0;skipped=[]
    for tree in ('src','scripts','config','data','docs'):
        for base,dirs,files in os.walk(SOURCE/tree):
            dirs[:]=[name for name in dirs if name not in ('__pycache__','.git','.pytest_cache')]
            for name in files:
                path=Path(base)/name;relative=path.relative_to(SOURCE)
                if name=='.env' or name.endswith(('.pg.json','.tmp','.lock')):
                    skipped.append(relative.as_posix());continue
                destination=TARGET/relative
                if destination.exists():raise ValueError('FORMAL_COPY_DESTINATION_ALREADY_EXISTS:'+relative.as_posix())
                destination.parent.mkdir(parents=True,exist_ok=True)
                # Configuration, code and moving pointers have independent bytes.
                mutable=tree!='data' or 'HEAD' in name.upper() or 'AUTHORITY' in name.upper()
                if not mutable:
                    try:os.link(path,destination);linked+=1
                    except OSError:shutil.copy2(path,destination);copied+=1
                else:shutil.copy2(path,destination);copied+=1
                count+=1
    for name,raw in before.items():
        if (SOURCE/name).read_bytes()!=raw or (TARGET/name).read_bytes()!=raw:raise ValueError('FORMAL_COPY_HEAD_IDENTITY_MISMATCH')
    old=TARGET/'config/v4_operational_owner_pg_closeout_r1.json'
    if old.exists():os.replace(old,old.with_name('v4_operational_owner_pg_closeout_r1.source_isolated.json'))
    result=dict(contract_id='V4_FORMAL_G_LOCAL_STAGING_FORK_R1',source=str(SOURCE),target=str(TARGET),
        files=count,immutable_hardlinks=linked,independent_copies=copied,skipped_pg_descriptors_and_private_files=skipped,
        protected_heads={name:hashlib.sha256(raw).hexdigest() for name,raw in before.items()},
        active_production_changed=False,production_acceptance=False,formal_pg_migration='REQUIRED_BEFORE_ACTIVATION')
    raw=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
    (TARGET/'FORMAL_STAGING_FORK.json').write_bytes(raw);(OUT/'RESULT.json').write_bytes(raw)
    print(json.dumps(dict(status='FORMAL_STAGING_FORK_COMPLETE_NOT_ACTIVATED',files=count,production_changed=False)))
if __name__=='__main__':main()
