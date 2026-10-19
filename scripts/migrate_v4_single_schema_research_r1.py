"""Migrate one exact, descriptor-verified legacy research release into v4."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PREFIXES = ('v4_research_',)
RELATIONS = {
    'objects': ('research_objects', ('domain','id','name','symbol','state','payload')),
    'aliases': ('research_aliases', ('alias','id')),
    'members': ('research_members', ('sector','security')),
    'metadata': ('research_metadata', ('key','value')),
    'bars': ('research_series_bars', ('security','day','payload')),
    'days': ('research_journal_days', ('day','source_digest','payload')),
    'day_inputs': ('research_journal_inputs', ('day','payload')),
}


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf8')


def table_digest(pg, schema, table, storage_kind):
    from workbench_db.v4_snapshot_pg_r2 import EXTRA_TABLES, TABLES, ORDER, canonical_json_payload
    definitions={name:tuple((column,'text') for column in columns) for name,columns in TABLES.items()}
    definitions.update(EXTRA_TABLES[storage_kind])
    definition=definitions[table]
    names=tuple(column for column,_ in definition)
    order=ORDER.get(table,(names[0],))
    query=sql.SQL('SELECT {} FROM {}.{} ORDER BY {}').format(
        sql.SQL(',').join(map(sql.Identifier,names)),sql.Identifier(schema),sql.Identifier(table),
        sql.SQL(',').join((sql.SQL('{} COLLATE "C" NULLS FIRST' if dict(definition)[column]=='text' else '{} NULLS FIRST')
                          .format(sql.Identifier(column)) for column in order))
    )
    h=hashlib.sha256(); count=0
    with pg.cursor(name='r7_migrate_'+hashlib.sha256((schema+table).encode()).hexdigest()[:16]) as cur:
        cur.itersize=128;cur.execute(query)
        for row in cur:
            values=[value.isoformat() if kind=='date' and value is not None else value
                    for value,(_,kind) in zip(row,definition)]
            if table=='objects' and values[-1] is not None:
                values[-1]=canonical_json_payload(values[-1])
            h.update(canonical(values)+b'\n');count+=1
    return count,h.hexdigest()


def central_digest(pg, relation, release_id, columns, source_table):
    from workbench_db.v4_snapshot_pg_r2 import TABLES, EXTRA_TABLES, ORDER, canonical_json_payload
    storage_kind=pg.execute('SELECT storage_kind FROM v4.research_releases WHERE release_id=%s',(release_id,)).fetchone()[0]
    definition=dict((name,tuple((column,'text') for column in cols)) for name,cols in TABLES.items())
    definition.update(EXTRA_TABLES[storage_kind])
    d=definition[source_table];order=ORDER.get(source_table,(columns[0],))
    def sort_expr(column):
        ident=sql.Identifier(column)
        if column=='day' and source_table in {'bars','days','day_inputs'}:
            return sql.SQL('{} NULLS FIRST').format(ident)
        return (sql.SQL('{} COLLATE "C" NULLS FIRST').format(ident) if dict(d)[column]=='text'
                else sql.SQL('{} NULLS FIRST').format(ident))
    q=sql.SQL('SELECT {} FROM v4.{} WHERE release_id=%s ORDER BY {}').format(
        sql.SQL(',').join(map(sql.Identifier,columns)),sql.Identifier(relation),
        sql.SQL(',').join(sort_expr(column) for column in order)
    )
    h=hashlib.sha256();count=0
    with pg.cursor(name='r7_canonical_'+hashlib.sha256((release_id+source_table).encode()).hexdigest()[:16]) as cur:
        cur.itersize=128;cur.execute(q,(release_id,))
        for row in cur:
            values=[value.isoformat() if (kind=='date' or (column=='day' and source_table in {'bars','days','day_inputs'})) and value is not None else value
                    for value,(_,kind),column in zip(row,d,columns)]
            if source_table=='objects' and values[-1] is not None: values[-1]=canonical_json_payload(values[-1])
            h.update(canonical(values)+b'\n');count+=1
    return count,h.hexdigest()


def migrate(schema, expected_release):
    if not schema.startswith(SCHEMA_PREFIXES) or not schema.replace('_','').isalnum():
        raise ValueError('EXACT_LEGACY_RESEARCH_SCHEMA_REQUIRED')
    from workbench_db.v4_native import configured_dsn
    from workbench_db.v4_snapshot_pg_r2 import CONTRACT, database_identity, table_manifest, EXTRA_FIELDS
    result={'source_schema':schema,'release_id':expected_release,'status':'STARTED'}
    with psycopg.connect(configured_dsn(),connect_timeout=5) as pg:
        pg.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        pg.execute("SET LOCAL statement_timeout='180s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        db=pg.execute("SELECT current_database(),inet_server_addr()::text,inet_server_port(),(SELECT oid::text FROM pg_database WHERE datname=current_database())").fetchone()
        if db[:3]!=('market_research','127.0.0.1/32',5432) or db[3]!='646711':
            raise RuntimeError('R7_SINGLE_DATABASE_IDENTITY_MISMATCH')
        descriptor_row=pg.execute(sql.SQL('SELECT digest,contract_id,descriptor FROM {}.snapshot_identity').format(sql.Identifier(schema))).fetchall()
        if len(descriptor_row)!=1: raise ValueError('LEGACY_SNAPSHOT_IDENTITY_CARDINALITY')
        old_digest,contract_id,raw=descriptor_row[0]
        if contract_id!=CONTRACT: raise ValueError('LEGACY_R2_DESCRIPTOR_REQUIRED')
        descriptor=json.loads(raw)
        if descriptor.get('schema')!=schema or descriptor.get('release_id')!=expected_release:
            raise ValueError('LEGACY_DESCRIPTOR_IDENTITY_MISMATCH')
        if descriptor.get('logical_digest')!=old_digest: raise ValueError('LEGACY_DESCRIPTOR_DIGEST_MISMATCH')
        if database_identity(pg)!=descriptor.get('database_identity'): raise ValueError('LEGACY_DATABASE_IDENTITY_MISMATCH')
        storage_kind=descriptor.get('content_manifest',{}).get('storage_kind')
        if storage_kind not in EXTRA_FIELDS: raise ValueError('LEGACY_STORAGE_KIND_INVALID')
        table_digests={name:table_digest(pg,schema,name,storage_kind) for name in ('objects','aliases','members','metadata',*descriptor['content_manifest']['tables'].keys()) if name!='snapshot_identity'}
        if set(table_digests)!=set(descriptor['content_manifest']['tables']): raise ValueError('LEGACY_TABLE_SET_MISMATCH')
        actual_manifest={name:dict(rows=value[0],digest=value[1]) for name,value in table_digests.items()}
        for name,actual in actual_manifest.items():
            expected=descriptor['content_manifest']['tables'][name]
            if actual!={'rows':expected['rows'],'digest':expected['digest']}:
                raise ValueError('LEGACY_CONTENT_VERIFICATION_FAILED:'+name)
        original=raw.encode('utf8');original_sha=hashlib.sha256(original).hexdigest()
        identity=(old_digest,contract_id,descriptor.get('release_id'))
        existing=pg.execute('SELECT storage_kind,legacy_digest,original_descriptor_sha256 FROM v4.research_releases WHERE release_id=%s',(expected_release,)).fetchone()
        if existing:
            map_rows=pg.execute('SELECT source_table,canonical_relation,original_sha256 FROM v4.legacy_schema_migration_map WHERE source_schema=%s AND legacy_identity=%s ORDER BY source_table',(schema,f'{contract_id}:{expected_release}:{storage_kind}')).fetchall()
            if existing[0]!=storage_kind or existing[1]!=old_digest or existing[2]!=original_sha or len(map_rows)!=len(table_digests):
                raise ValueError('CANONICAL_RELEASE_IDENTITY_CONFLICT')
            result.update(status='ALREADY_MIGRATED',logical_digest=old_digest,descriptor_sha256=original_sha,table_count=len(map_rows))
            return result
        pg.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(f'v4-research-release:{expected_release}',))
        manifest=dict(descriptor['content_manifest'],migration_contract_id='V4_SINGLE_SCHEMA_RESEARCH_STORAGE_R1')
        pg.execute('INSERT INTO v4.research_releases(release_id,storage_kind,contract_id,t0,source_schema,legacy_digest,original_descriptor,original_descriptor_sha256,canonical_manifest,sealed) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,false)',
                   (expected_release,storage_kind,contract_id,descriptor['T0'],schema,old_digest,original,original_sha,json.dumps(manifest,ensure_ascii=False,separators=(',',':'))))
        migrated=[]
        for source_table,(relation,columns) in RELATIONS.items():
            if source_table not in table_digests: continue
            select_cols=sql.SQL(',').join(map(sql.Identifier,columns))
            select_values=sql.SQL(',').join(
                sql.SQL('{}::date').format(sql.Identifier(column))
                if source_table in {'days','day_inputs'} and column=='day' else sql.Identifier(column)
                for column in columns)
            pg.execute(sql.SQL('INSERT INTO v4.{}(release_id,{}) SELECT %s,{} FROM {}.{}').format(
                sql.Identifier(relation),select_cols,select_values,sql.Identifier(schema),sql.Identifier(source_table)),(expected_release,))
            target_count,target_sha=central_digest(pg,relation,expected_release,columns,source_table)
            source_count,source_sha=table_digests[source_table]
            if (target_count,target_sha)!=(source_count,source_sha): raise ValueError('CANONICAL_CONTENT_VERIFICATION_FAILED:'+source_table)
            pg.execute('INSERT INTO v4.legacy_schema_migration_map(source_schema,source_table,legacy_identity,canonical_relation,canonical_version,original_sha256,verification) VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb)',
                       (schema,source_table,f'{contract_id}:{expected_release}:{storage_kind}',f'v4.{relation}',expected_release,source_sha,json.dumps({'source_rows':source_count,'target_rows':target_count,'source_digest':source_sha,'target_digest':target_sha,'status':'VERIFIED'},separators=(',',':'))))
            migrated.append({'table':source_table,'target':relation,'rows':target_count,'digest':target_sha})
        if storage_kind=='series':
            bind={key:descriptor[key] for key in EXTRA_FIELDS[storage_kind]}
            pg.execute('INSERT INTO v4.research_series_versions(release_id,series_contract_id,source_digest,bar_count,symbol_count,price_basis) VALUES(%s,%s,%s,%s,%s,%s)',(expected_release,bind['series_contract_id'],bind['source_digest'],bind['bar_count'],bind['symbol_count'],descriptor.get('content_manifest',{}).get('metadata',{}).get('price_basis','RAW_OR_CONTRACT_BOUND')))
        if storage_kind=='journal':
            bind={key:descriptor[key] for key in EXTRA_FIELDS[storage_kind]}
            head=bind['head']
            if isinstance(head,str):
                try: head=json.loads(head)
                except json.JSONDecodeError: pass
            # Physical registry schema is migrated to the fixed v4 relation;
            # its original locator remains byte-for-byte in original_descriptor.
            pg.execute('INSERT INTO v4.research_journal_versions(release_id,journal_contract,head,registry_schema,registry_key) VALUES(%s,%s,%s::jsonb,%s,%s)',(expected_release,bind['journal_contract'],json.dumps(head,ensure_ascii=False,separators=(',',':')),'v4',bind['registry_key']))
        pg.execute('UPDATE v4.research_releases SET sealed=true WHERE release_id=%s',(expected_release,))
        result.update(status='MIGRATED_AND_VERIFIED',storage_kind=storage_kind,T0=descriptor['T0'],logical_digest=old_digest,descriptor_sha256=original_sha,tables=migrated)
        return result


if __name__=='__main__':
    sys.path.insert(0,str(ROOT/'src'))
    parser=argparse.ArgumentParser();parser.add_argument('--schema',required=True);parser.add_argument('--release-id',required=True)
    args=parser.parse_args()
    print(json.dumps(migrate(args.schema,args.release_id),ensure_ascii=False,sort_keys=True,default=str))
