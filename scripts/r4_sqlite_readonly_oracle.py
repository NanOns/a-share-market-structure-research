"""Separate migration-oracle process. Never used by a V4 runtime connection."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import os

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while chunk:=f.read(8*1024*1024):h.update(chunk)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--output',required=True);ap.add_argument('--kind',choices=['history','jobs','snapshot'],required=True);args=ap.parse_args()
    source=Path(args.source).resolve();out=Path(args.output).resolve()
    if not out.is_relative_to(Path('G:/codex_tmp').resolve()):raise ValueError('G_ORACLE_OUTPUT_REQUIRED')
    before=sha(source)
    # Immutable indexes have no WAL. Live scheduler input must first be a frozen G copy.
    if Path(str(source)+'-wal').exists():raise ValueError('FROZEN_SQLITE_WITHOUT_WAL_REQUIRED')
    if args.kind=='jobs' and not source.is_relative_to(Path('G:/codex_tmp').resolve()):raise ValueError('FROZEN_G_JOB_COPY_REQUIRED')
    with sqlite3.connect(source.as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        if args.kind=='history':
            rows={}
            for sid,payload in db.execute('SELECT security,payload FROM history ORDER BY security'):
                bars=json.loads(payload);raw=json.dumps(bars,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
                rows[sid]=dict(digest=hashlib.sha256(raw).hexdigest(),bars=len(bars))
        elif args.kind=='snapshot':
            rows={}
            for table,order in [('objects','domain,id'),('aliases','alias,id'),('members','sector,security')]:
                digest=hashlib.sha256();count=0
                for row in db.execute('SELECT * FROM '+table+' ORDER BY '+order):
                    values=list(row)
                    if table=='objects':values[-1]=json.loads(values[-1])
                    digest.update(json.dumps(values,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()+b'\n');count+=1
                rows[table]=dict(rows=count,digest=digest.hexdigest())
            rows['numeric_sort']={}
            for direction in ('ASC','DESC'):
                rows['numeric_sort'][direction]=[r[0] for r in db.execute("SELECT id FROM objects WHERE domain='stocks' ORDER BY json_extract(payload,'$.fields.close.value') "+direction+",id ASC")]
        else:
            tables=['scheduler_policy','update_jobs','update_job_days','update_events','scheduler_dispatch','scheduler_attempts','scheduler_rearm']
            rows={}
            for table in tables:
                if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
                    cur=db.execute('SELECT * FROM '+table);rows[table]=dict(columns=[c[0] for c in cur.description],rows=cur.fetchall())
    after=sha(source)
    if before!=after:raise ValueError('ORACLE_SOURCE_CHANGED')
    out.parent.mkdir(parents=True,exist_ok=True);tmp=out.with_suffix('.tmp')
    tmp.write_text(json.dumps(dict(source=str(source),source_sha=before,after_sha=after,kind=args.kind,data=rows),ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(tmp,out)
    print(json.dumps(dict(kind=args.kind,records=len(rows),source_sha=before,unchanged=True)))
if __name__=='__main__':main()
