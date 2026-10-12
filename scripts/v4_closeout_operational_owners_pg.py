"""Candidate-only full owner migration, immutable Head, exact complete readback."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

SOURCE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(SOURCE),str(SOURCE/'src')]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();root=Path(args.root).resolve();out=Path(args.out).resolve()
    if not root.is_relative_to(Path('G:/codex_tmp').resolve()) or out.drive.upper()!='G:':raise ValueError('ISOLATED_G_ROOT_REQUIRED')
    out.mkdir(parents=True,exist_ok=False)
    os.environ.update(TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp')
    from workbench_analysis.operational_successor_v1 import accepted_api
    from workbench_analysis.r43_operational_publication import rows
    from workbench_analysis.r43_owner_replay import checked
    from workbench_db.v4_operational_owner_pg_closeout import prepare,read,OWNER
    from workbench_service.v4_daily_refresh import atomic_bytes
    from workbench_db.v4_forward_pg_r1 import canonical
    head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';before=head.read_bytes();api=accepted_api(root)
    path=root/'config/v4_operational_owner_pg_closeout_r1.json'
    if path.exists():raise ValueError('PRESERVE_EXISTING_PG_OWNER_AUTHORITY')
    owners={};evidence=[]
    for day,bindings in api.candidate['owners'].items():
        owners[day]={}
        for domain,binding in bindings.items():
            source=checked(root,binding);source_before=hashlib.sha256(source.read_bytes()).hexdigest()
            content=rows(root,binding)
            reference=prepare(root,api.token,day,domain,binding,content)
            actual=read(root,reference,api.token,day,domain,binding)
            if canonical(actual)!=canonical(content):raise ValueError('PG_OWNER_COMPLETE_READBACK_DIFFERENCE')
            if hashlib.sha256(source.read_bytes()).hexdigest()!=source_before:raise ValueError('PG_OWNER_SOURCE_CHANGED')
            owners[day][domain]=reference
            evidence.append(dict(T0=day,domain=domain,source=binding,pg=reference,rows=len(actual),whole_payload_difference=0))
            print(json.dumps(dict(T0=day,domain=domain,owners=len(evidence))),flush=True)
    if head.read_bytes()!=before:raise ValueError('PROTECTED_HEAD_CHANGED')
    authority=dict(contract_id=OWNER,head_token=api.token,source_owners=api.candidate['owners'],owners=owners,
                   historical_PIT_permission=False,AS_RECORDED=False,PIT_ELIGIBLE=False)
    atomic_bytes(path,canonical(authority))
    migrated=accepted_api(root)
    if migrated.pg_owner_authority is None:raise ValueError('PG_OWNER_DEFAULT_READER_NOT_BOUND')
    for row in evidence:
        migrated.read(row['domain'],row['T0'],migrated.token)
    if head.read_bytes()!=before:raise ValueError('PROTECTED_HEAD_CHANGED')
    (out/'RESULT.json').write_bytes(canonical(dict(contract_id=OWNER,head_sha256=hashlib.sha256(before).hexdigest(),
        acceptance='COMPLETE_MIGRATION_READBACK_ONLY_NUMERIC_ORACLE_SEPARATE',production_changed=False,owners=evidence)))

if __name__=='__main__':main()
