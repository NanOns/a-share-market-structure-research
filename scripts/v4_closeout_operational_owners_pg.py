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
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--out',required=True);parser.add_argument('--formal-roles')
    args=parser.parse_args();root=Path(args.root).resolve();out=Path(args.out).resolve()
    if args.formal_roles:
        if root!=Path('G:/codex work/v4-production-20261012').resolve() or not (root/'FORMAL_STAGING_FORK.json').exists():raise ValueError('FORMAL_STAGING_ROOT_REQUIRED')
        secret=Path(args.formal_roles).resolve()
        if secret!=root/'config/native_pg_roles.dpapi':raise ValueError('FORMAL_ROLE_FILE_REQUIRED')
        from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
        import psycopg
        os.environ['V4_NATIVE_PG_DSN']=load_credentials(secret)[ROLES[1]]
        with psycopg.connect(os.environ['V4_NATIVE_PG_DSN']) as pg:
            pg.execute('SET TRANSACTION READ ONLY')
            actual=pg.execute('SELECT current_user,current_database(),system_identifier::text FROM pg_control_system()').fetchone()
            if actual!=(ROLES[1],'market_research','7688198230782699460'):raise ValueError('FORMAL_CLUSTER_ROLE_IDENTITY_MISMATCH')
    elif not root.is_relative_to(Path('G:/codex_tmp').resolve()):raise ValueError('ISOLATED_G_ROOT_REQUIRED')
    if out.drive.upper()!='G:':raise ValueError('G_EVIDENCE_REQUIRED')
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
