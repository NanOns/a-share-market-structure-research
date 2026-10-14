"""Explicit offline migration of the versioned R2 read index; never launched by HTTP."""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',required=True)
    p.add_argument('--trade-date',action='append')
    p.add_argument('--roles')
    a=p.parse_args();root=Path(a.root).resolve()
    if root.drive.upper()!='G:':raise ValueError('G_WORKSPACE_REQUIRED')
    for key in ('TMP','TEMP','TMPDIR'):os.environ[key]='G:/codex_tmp'
    if a.roles:
        from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
        credentials=load_credentials(a.roles)
        os.environ['V4_NATIVE_PG_DSN']=credentials[ROLES[1]]
        os.environ['V4_NATIVE_PG_READER_DSN']=credentials[ROLES[0]]
    from workbench_db.v4_read_index_r2 import prepare_bff
    head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';before=head.read_bytes()
    result=prepare_bff(root,json.loads(before),days=a.trade_date)
    if head.read_bytes()!=before:raise ValueError('READ_INDEX_R2_MIGRATION_HEAD_CHANGED')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
