"""Import a frozen old scheduler oracle into a G isolated PG candidate only."""
from datetime import datetime,timezone,date
import hashlib
import json
from pathlib import Path
import tempfile
from psycopg import sql
from .v4_native import connection

CONTRACT='V4_PG_JOB_FROZEN_ORACLE_MIGRATION_R1'
ORDER=('scheduler_policy','update_jobs','update_job_days','update_events','scheduler_dispatch','scheduler_attempts','scheduler_rearm')
RECEIPTS='v4.jobs_frozen_oracle_migration_receipts_r1'

def _require_fixed_receipts(pg):
    relation=pg.execute('SELECT to_regclass(%s)',(RECEIPTS,)).fetchone()
    guard=pg.execute('''SELECT count(*) FROM pg_trigger t
        JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_proc p ON p.oid=t.tgfoid JOIN pg_namespace pn ON pn.oid=p.pronamespace
        WHERE n.nspname='v4' AND c.relname='jobs_frozen_oracle_migration_receipts_r1'
          AND t.tgname='jobs_frozen_oracle_migration_receipts_immutable_r1'
          AND t.tgenabled IN ('O','A') AND NOT t.tgisinternal
          AND pn.nspname='v4' AND p.proname='reject_jobs_frozen_oracle_migration_receipt_mutation_r1' ''').fetchone()[0]
    if not relation or relation[0] is None or guard!=1:
        raise ValueError('V4_FIXED_JOB_MIGRATION_RECEIPTS_NOT_MIGRATED')

def import_oracle(jobs,oracle):
    if not jobs.root.is_relative_to(Path(tempfile.gettempdir()).resolve()):raise ValueError('ISOLATED_MIGRATION_TARGET_REQUIRED')
    if jobs.schema!='v4':raise ValueError('V4_SINGLE_SCHEMA_JOB_MIGRATION_REQUIRED')
    if oracle.get('kind')!='jobs' or oracle.get('source_sha')!=oracle.get('after_sha'):raise ValueError('FROZEN_JOB_ORACLE_REQUIRED')
    payload=hashlib.sha256(json.dumps(oracle['data'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    migration_id=oracle['source_sha'];counts={};time_mappings=[]
    with connection(jobs.schema,dsn=jobs.dsn) as pg:
        pg.execute('SELECT pg_advisory_xact_lock(%s)',(jobs.lock_key,))
        _require_fixed_receipts(pg)
        old=pg.execute('SELECT payload_sha,counts FROM v4.jobs_frozen_oracle_migration_receipts_r1 WHERE source_sha=%s',(migration_id,)).fetchone()
        if old:
            if old[0]!=payload:raise ValueError('FROZEN_JOB_MIGRATION_IDENTITY_CONFLICT')
            return dict(contract_id=CONTRACT,status='ALREADY_IMPORTED',source_sha=migration_id,counts=old[1],time_mappings=[])
        if pg.execute('SELECT count(*) FROM update_jobs').fetchone()[0]:raise ValueError('EMPTY_CANDIDATE_JOB_STORE_REQUIRED')
        migrated_at=datetime.now(timezone.utc)
        for table in ORDER:
            item=oracle['data'].get(table)
            if not item:counts[table]=0;continue
            cols=item['columns'];rows=[]
            if table=='scheduler_policy':pg.execute('DELETE FROM scheduler_policy')
            for source in item['rows']:
                row=list(source)
                for i,col in enumerate(cols):
                    if col in ('updated_at','created_at','finished_at','timestamp','next_retry_at') and row[i] is not None:
                        if row[i]=='DEFAULT_AUTO_ON':
                            time_mappings.append(dict(table=table,column=col,source='DEFAULT_AUTO_ON',target=migrated_at.isoformat(),reason='LEGACY_SENTINEL_NOT_A_TIMESTAMP'));row[i]=migrated_at
                        else:
                            parsed=datetime.fromisoformat(row[i])
                            if parsed.tzinfo is None:raise ValueError('LEGACY_TIMESTAMP_TIMEZONE_UNKNOWN')
                            row[i]=parsed
                rows.append(tuple(row))
            query=sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(sql.Identifier(table),sql.SQL(',').join(map(sql.Identifier,cols)),sql.SQL(',').join(sql.Placeholder() for _ in cols))
            with pg.cursor() as cur:cur.executemany(query,rows)
            actual=pg.execute(sql.SQL('SELECT {} FROM {}').format(sql.SQL(',').join(map(sql.Identifier,cols)),sql.Identifier(table))).fetchall()
            def normalize(row):
                return tuple(v.astimezone(timezone.utc).isoformat() if isinstance(v,datetime) else v.isoformat() if isinstance(v,date) else v for v in row)
            expected=[]
            for row in rows:
                expected.append(tuple(datetime.fromisoformat(v).astimezone(timezone.utc).isoformat() if isinstance(v,str) and cols[i] in ('updated_at','created_at','finished_at','timestamp','next_retry_at') else str(v) if isinstance(v,date) and not isinstance(v,datetime) else v.astimezone(timezone.utc).isoformat() if isinstance(v,datetime) else v for i,v in enumerate(row)))
            if sorted(map(repr,expected))!=sorted(repr(normalize(r)) for r in actual):raise ValueError('JOB_MIGRATION_FULL_ROW_DIFF:'+table)
            counts[table]=len(actual)
        pg.execute("SELECT setval(pg_get_serial_sequence('update_events','event_id'),GREATEST(COALESCE((SELECT max(event_id) FROM update_events),0),1),EXISTS(SELECT 1 FROM update_events))")
        from psycopg.types.json import Jsonb
        pg.execute('INSERT INTO v4.jobs_frozen_oracle_migration_receipts_r1(source_sha,payload_sha,counts) VALUES(%s,%s,%s)',(migration_id,payload,Jsonb(counts)))
    return dict(contract_id=CONTRACT,status='IMPORTED_FULL_ROW_EQUIVALENT',source_sha=migration_id,payload_sha=payload,counts=counts,time_mappings=time_mappings)
