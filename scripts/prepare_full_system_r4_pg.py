"""Apply exact 001--033 only to an explicitly attested G disposable cluster."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import psycopg
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dsn',required=True);parser.add_argument('--data-directory',required=True);parser.add_argument('--receipt',required=True);args=parser.parse_args()
    expected=Path(args.data_directory).resolve()
    if not expected.is_relative_to(Path('G:/codex_tmp').resolve()):raise ValueError('G_ISOLATED_CLUSTER_REQUIRED')
    rows=[]
    with psycopg.connect(args.dsn) as pg:
        actual=Path(pg.execute('SHOW data_directory').fetchone()[0]).resolve()
        if actual!=expected:raise ValueError('PG_CLUSTER_IDENTITY_MISMATCH')
        identity=pg.execute('SELECT current_database(),current_user,version()').fetchone()
        files=sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('*.sql'))
        if len(files)!=33:raise ValueError('EXACT_001_033_REQUIRED')
        pg.execute('CREATE SCHEMA IF NOT EXISTS r4_evidence')
        pg.execute('CREATE TABLE IF NOT EXISTS r4_evidence.migrations(path text PRIMARY KEY,sha256 text NOT NULL,applied_at timestamptz NOT NULL DEFAULT clock_timestamp())')
        for p in files:
            text=p.read_text('utf8');sha=hashlib.sha256(text.encode()).hexdigest()
            prior=pg.execute('SELECT sha256 FROM r4_evidence.migrations WHERE path=%s',(p.name,)).fetchone()
            if prior and prior[0]!=sha:raise ValueError('R4_SQL_CHECKSUM_CONFLICT')
            if not prior:
                pg.execute(text);pg.execute('INSERT INTO r4_evidence.migrations(path,sha256) VALUES(%s,%s)',(p.name,sha))
            rows.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha,status='REUSED_EXACT_SQL' if prior else 'APPLIED_SOURCE_SQL'))
        constraints=pg.execute("SELECT n.nspname,c.conname,pg_get_constraintdef(c.oid) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname IN ('v4','fep') ORDER BY 1,2").fetchall()
    result=dict(contract_id='R4_00_ISOLATED_PG_SOURCE_SQL_R1',base_head='fbd23a6ba08d0948fe7ad421d1765fe363648522',source_SHA='fbd23a6ba08d0948fe7ad421d1765fe363648522',run_utc=datetime.now(timezone.utc).isoformat(),scope='ISOLATED_SCHEMA_001_033',denominator=33,negative_vectors=['PG_DATA_DIRECTORY_MISMATCH'],previous_status='NOT_STARTED',current_status='SOURCE_SQL_APPLIED',evidence_links=[],owner='Codex / root',limitations=['Not production database identity, locale C; no formal grants seeded'],next_conditions=['Full V4 regression fixtures and role checks'],database_identity=identity,data_directory=str(actual),migrations=rows,constraints=constraints)
    p=Path(args.receipt).resolve();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(tmp,p)
    print(json.dumps(dict(migrations=len(rows),constraints=len(constraints),database=identity[0],data_directory=str(actual))))
if __name__=='__main__':main()
