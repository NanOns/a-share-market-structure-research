"""Old accepted publication export/oracle in a child, exact immutable PG import."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
SOURCE = Path('G:/codex work/大A交易')
OUT = ROOT / 'docs/audits/r4_external_repair_batch2_20261011'
TABLES = [('objects', 'domain,id'), ('aliases', 'alias,id'), ('members', 'sector,security'), ('metadata', 'key')]


def canonical(row):
    return json.dumps(row, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while part := stream.read(8 * 1024 * 1024): h.update(part)
    return h.hexdigest()


def write(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    os.replace(temporary, path)


def prior():
    return json.loads((ROOT / 'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b/R4_04_REAL_SNAPSHOT_RESULT.json').read_bytes())


def export(path):
    import sqlite3  # only the explicitly separate migration-oracle child
    if not path.resolve().is_relative_to(Path('G:/codex_tmp').resolve()):
        raise ValueError('G_ORACLE_OUTPUT_REQUIRED')
    binding = prior()['original_binding']
    source = SOURCE / binding['path']
    if sha(source) != binding['sha256'] or Path(str(source) + '-wal').exists():
        raise ValueError('IMMUTABLE_OLD_PUBLICATION_REQUIRED')
    digests = {}
    temporary = path.with_suffix('.tmp')
    with sqlite3.connect(source.as_uri() + '?mode=ro&immutable=1', uri=True) as db, gzip.open(temporary, 'wt', encoding='utf8') as stream:
        for table, order in TABLES:
            cur = db.execute('SELECT * FROM ' + table + ' ORDER BY ' + order)
            stream.write(json.dumps(dict(table=table, columns=[c[0] for c in cur.description])) + '\n')
            h = hashlib.sha256(); count = 0
            for row in cur:
                stream.write(json.dumps(dict(table=table, row=row), ensure_ascii=False, separators=(',', ':')) + '\n')
                values = list(row)
                if table == 'objects': values[-1] = json.loads(values[-1])
                h.update(canonical(values) + b'\n'); count += 1
            digests[table] = dict(rows=count, digest=h.hexdigest())
    os.replace(temporary, path)
    if sha(source) != binding['sha256']:
        raise ValueError('OLD_PUBLICATION_CHANGED')
    write(path.with_suffix('.receipt.json'), dict(source_binding=binding, source_unchanged=True, tables=digests,
        export_sha256=sha(path), oracle='Separate readonly SQLite process'))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--export-only', type=Path); args = parser.parse_args()
    if args.export_only:
        export(args.export_only)
        return
    staging = Path('G:/codex_tmp/test_temp/r4_old_snapshot_exact_' + uuid.uuid4().hex[:8])
    staging.mkdir(parents=True)
    exported = staging / 'old_tables.jsonl.gz'
    subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--export-only', str(exported)], check=True)
    oracle = json.loads(exported.with_suffix('.receipt.json').read_bytes())
    if sha(exported) != oracle['export_sha256']: raise ValueError('EXPORT_CHANGED')
    old_manifest_binding=prior()['staged']['pointer']['previous']['manifest']
    manifest_path=SOURCE/old_manifest_binding['path']
    if sha(manifest_path)!=old_manifest_binding['sha256']: raise ValueError('OLD_MANIFEST_CHANGED')
    old_manifest = json.loads(manifest_path.read_bytes())
    from tests import v4_native_isolation_plugin_r4 as guard
    from workbench_db.v4_snapshot_pg_r1 import Builder, read
    os.environ['R4_PG_DATA_DIRECTORY'] = 'G:/codex_tmp/full_system_r4_fbd23a6b/pg_data'
    os.environ['R4_CONNECTION_LEDGER'] = str(OUT / 'EXACT_OLD_SNAPSHOT_CONNECTIONS.jsonl')
    config = SimpleNamespace(); guard.pytest_configure(config); guard.ACTIVE = 'EXACT_OLD_PUBLICATION_IMPORT_AND_READBACK'
    code = 1; builder = None
    try:
        builder = Builder(staging, old_manifest['release_id'])
        builder.executescript('CREATE TABLE objects(domain text,id text,name text,symbol text,state text,payload text,PRIMARY KEY(domain,id)); CREATE TABLE aliases(alias text,id text,PRIMARY KEY(alias,id)); CREATE TABLE members(sector text,security text,PRIMARY KEY(sector,security)); CREATE TABLE metadata(key text PRIMARY KEY,value text);')
        with gzip.open(exported, 'rt', encoding='utf8') as stream:
            for line in stream:
                record = json.loads(line)
                if 'row' in record:
                    values = record['row']
                    builder.execute('INSERT INTO ' + record['table'] + ' VALUES(' + ','.join('?' for _ in values) + ')', values)
        descriptor = builder.seal(old_manifest); builder.commit(); builder.close(); builder = None
        actual = {}
        with read(descriptor) as tx:
            for table, order in TABLES:
                h = hashlib.sha256(); count = 0
                with tx.pg.cursor(name='exact_old_' + table) as cur:
                    cur.execute('SELECT * FROM ' + table + ' ORDER BY ' + order)
                    for row in cur:
                        values = list(row)
                        if table == 'objects': values[-1] = json.loads(values[-1])
                        h.update(canonical(values) + b'\n'); count += 1
                actual[table] = dict(rows=count, digest=h.hexdigest())
        if actual != oracle['tables']: raise ValueError('EXACT_OLD_PUBLICATION_DIFF')
        from workbench_db.v4_native import connection
        import psycopg
        try:
            with connection(descriptor['schema']) as pg: pg.execute('DELETE FROM objects')
        except psycopg.Error as exc:
            if 'IMMUTABLE_RESEARCH_SNAPSHOT' not in str(exc): raise
        else: raise ValueError('PG_EXPORT_MUTATION_NOT_REJECTED')
        source = SOURCE / oracle['source_binding']['path']
        if sha(source) != oracle['source_binding']['sha256']: raise ValueError('OLD_SOURCE_CHANGED')
        code = 0
        write(OUT / 'EXACT_OLD_SNAPSHOT_RESULT.json', dict(contract_id='R4_EXACT_OLD_PUBLICATION_PG_MIGRATION_R1',
            current_status='SCOPED_FOUR_TABLE_EXACT_MIGRATION_PASS', source_binding=oracle['source_binding'],
            original_manifest_binding=old_manifest_binding, original_publication_id=old_manifest['release_id'], pg_binding=descriptor, source_unchanged=True,
            denominator={k:v['rows'] for k,v in actual.items()}, whole_table_oracle=actual, differences=[],
            negative_vectors=['Immutable snapshot mutation rejected'], owner='Codex / root',
            limitations=['PG storage equivalence of old publication only; no current producer or series migration claim',
                         'No consumer authority, joint release, CAS, rollback or production switch'],
            next_conditions=['All old-publication consumer/series bindings', 'Joint CAS/rollback and external acceptance']))
        print(json.dumps(dict(status='SCOPED_EXACT_MIGRATION_PASS', rows={k:v['rows'] for k,v in actual.items()}, differences=0)))
    finally:
        if builder: builder.close()
        guard.pytest_sessionfinish(None, code); guard.pytest_unconfigure(config)


if __name__ == '__main__': main()
