"""Copy signed bounded package resources to dev; never changes formal policy."""
import argparse,json,hashlib,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_windows_package_v1 import exact_metadata_resources
from workbench_analysis.r43_owner_replay import checked,ref

def main():
    p=argparse.ArgumentParser();p.add_argument('--formal-root',required=True);p.add_argument('--dev-root',required=True);p.add_argument('--policy',required=True);p.add_argument('--out',required=True);p.add_argument('--replace-dev-canonical',action='store_true');a=p.parse_args()
    formal=Path(a.formal_root).resolve();dev=Path(a.dev_root).resolve();out=Path(a.out).resolve()
    if any(path.drive.upper()!='G:' for path in (formal,dev,out)) or dev==formal:raise ValueError('DISTINCT_G_ROOTS_REQUIRED')
    policy_path=Path(a.policy).resolve();binding=ref(formal,policy_path);policy=json.loads(checked(formal,binding).read_bytes())
    files,skipped=exact_metadata_resources(formal,binding,policy)
    files=sorted(set(files+[checked(formal,b) for b in policy['accepted_algorithm_bindings']+policy['component_source_bindings']]))
    conflicts=[]
    for source in files:
        target=dev/source.relative_to(formal)
        if target.exists() and target.read_bytes()!=source.read_bytes():conflicts.append(str(source.relative_to(formal)))
    if conflicts:raise ValueError('PRESERVE_EXISTING_RESOURCE_CONFLICT:'+','.join(conflicts))
    copied=[]
    for source in files:
        target=dev/source.relative_to(formal)
        if target.exists():continue
        target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_suffix(target.suffix+'.copy_tmp');shutil.copyfile(source,temp);temp.replace(target);copied.append(str(source.relative_to(formal)))
    backup=None
    if a.replace_dev_canonical:
        canonical=dev/'config/operational_daily_exact_release_policy_v2.json';backup=out.parent/('DEV_POLICY_BACKUP_'+hashlib.sha256(canonical.read_bytes()).hexdigest()+'.json');backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copyfile(canonical,backup)
        temp=canonical.with_suffix('.copy_tmp');temp.write_bytes(policy_path.read_bytes());temp.replace(canonical)
    report=dict(policy=binding,files=[str(p.relative_to(formal)) for p in files],copied=copied,skipped=skipped,dev_canonical_backup=str(backup) if backup else None,formal_canonical_changed=False)
    out.parent.mkdir(parents=True,exist_ok=True);temp=out.with_suffix('.tmp');temp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(out)
    print(json.dumps(dict(files=len(files),copied=len(copied),report=str(out))))
if __name__=='__main__':main()
