"""Copy scheduler bytes with before/after identity checks; no source SQL open."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import argparse

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
    source=Path(args.source).resolve();out=Path(args.out).resolve()
    if not out.is_relative_to(Path('G:/codex_tmp').resolve()):raise ValueError('G_FROZEN_COPY_REQUIRED')
    if out.exists():raise ValueError('NEW_FROZEN_NAMESPACE_REQUIRED')
    out.mkdir(parents=True);files=[p for p in [source,Path(str(source)+'-wal'),Path(str(source)+'-shm')] if p.exists()]
    before={p.name:sha(p) for p in files}
    for p in files:shutil.copyfile(p,out/p.name)
    after={p.name:sha(p) for p in files}
    copied={p.name:sha(out/p.name) for p in files}
    if before!=after or before!=copied:raise ValueError('LIVE_SQLITE_CHANGED_DURING_FREEZE')
    copy=out/source.name;normalized=out/'consistent_snapshot.sqlite3'
    with sqlite3.connect(copy.as_uri()+'?mode=ro',uri=True) as old,sqlite3.connect(normalized) as snapshot:old.backup(snapshot)
    receipt=dict(contract_id='V4_JOB_READONLY_BYTE_FREEZE_R1',source=str(source),source_files_sha=before,after_files_sha=after,snapshot=str(normalized),snapshot_sha=sha(normalized),source_opened_by_sql=False,copy_WAL_included=Path(str(copy)+'-wal').exists())
    p=out/'FREEZE.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(tmp,p)
    print(json.dumps(dict(snapshot=str(normalized),source_unchanged=True,files=len(files))))
if __name__=='__main__':main()
