"""Prepare one exact candidate token's PG index under the existing writer lock."""
import argparse,json,os,sys,hashlib,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);a=p.parse_args()
    from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
    from workbench_db.v4_native import workspace_schema
    from workbench_db.v4_read_index_r1 import prepare_bff
    from workbench_analysis.operational_daily_storage_v1 import atomic_json
    import psycopg
    root=a.root.resolve();candidate=json.loads(a.candidate.read_bytes());credentials=load_credentials(root/'config/native_pg_roles.dpapi')
    os.environ.update(V4_NATIVE_PG_DSN=credentials[ROLES[1]],V4_NATIVE_PG_READER_DSN=credentials[ROLES[0]])
    head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';before=head.read_bytes();started=time.monotonic()
    key=int.from_bytes(hashlib.sha256(workspace_schema(root,'jobs').encode()).digest()[:8],'big',signed=True)^1
    with psycopg.connect(credentials[ROLES[1]],autocommit=True) as pg:
        if not pg.execute('SELECT pg_try_advisory_lock(%s)',(key,)).fetchone()[0]:raise ValueError('DAILY_WRITER_ALREADY_ACTIVE')
        try:index=prepare_bff(root,candidate)
        finally:pg.execute('SELECT pg_advisory_unlock(%s)',(key,))
    if head.read_bytes()!=before:raise ValueError('FORMAL_HEAD_CHANGED')
    atomic_json(root,a.candidate.parent/(a.candidate.stem+'_READ_INDEX.json'),dict(acceptance='PASS',index=index,seconds=time.monotonic()-started,head_unchanged=True))
    print(json.dumps(dict(acceptance='PASS',seconds=time.monotonic()-started)))

if __name__=='__main__':main()
