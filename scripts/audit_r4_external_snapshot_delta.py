"""Read-only old publication/PG candidate diff; never grants acceptance."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import gzip
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from workbench_db.v4_native import connection


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while part := stream.read(8 * 1024 * 1024):
            h.update(part)
    return h.hexdigest()


def changes(before, after, path=''):
    if type(before) is not type(after):
        yield path, before, after
    elif isinstance(before, dict):
        for key in sorted(before.keys() | after.keys()):
            field = path + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in before or key not in after:
                yield field, before.get(key), after.get(key)
            else:
                yield from changes(before[key], after[key], field)
    elif before != after:
        yield path, before, after


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(Path('G:/codex work').resolve()):
        raise ValueError('G_ENGINEERING_OUTPUT_REQUIRED')
    evidence = ROOT / 'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b'
    prior = json.loads((evidence / 'R4_04_REAL_SNAPSHOT_RESULT.json').read_bytes())
    binding = prior['original_binding']
    source = args.source_root.resolve() / binding['path']
    before = sha(source)
    if before != binding['sha256'] or source.stat().st_size != binding['bytes']:
        raise ValueError('OLD_PUBLICATION_BINDING_MISMATCH')
    if Path(str(source) + '-wal').exists():
        raise ValueError('IMMUTABLE_SOURCE_WITHOUT_WAL_REQUIRED')
    rows, fields, domains = [], Counter(), Counter()
    with connection(prior['pg_binding']['schema'], read_only=True) as pg:
        actual_dir = Path(pg.execute('SHOW data_directory').fetchone()[0]).resolve()
        if actual_dir != Path('G:/codex_tmp/full_system_r4_fbd23a6b/pg_data').resolve():
            raise ValueError('ISOLATED_CLUSTER_REQUIRED')
        new = {(r[0], r[1]): list(r) for r in pg.execute('SELECT * FROM objects ORDER BY domain,id')}
        with sqlite3.connect(source.as_uri() + '?mode=ro&immutable=1', uri=True) as old:
            columns = [r[1] for r in old.execute('PRAGMA table_info(objects)')]
            old_count = 0
            for record in old.execute('SELECT * FROM objects ORDER BY domain,id'):
                old_count += 1
                key = (record[0], record[1])
                candidate = new.pop(key, None)
                if candidate is None:
                    rows.append(dict(domain=key[0], id=key[1], disposition='MISSING_IN_CANDIDATE'))
                    continue
                left, right = dict(zip(columns, record)), dict(zip(columns, candidate))
                left['payload'] = json.loads(left['payload'])
                right['payload'] = json.loads(right['payload'])
                delta = [dict(field=p, old=a, candidate=b, disposition='UNREVIEWED_SOURCE_OR_TRANSFORM_DELTA')
                         for p, a, b in changes(left, right)]
                if delta:
                    domains[key[0]] += 1
                    fields.update(x['field'] for x in delta)
                    rows.append(dict(domain=key[0], id=key[1], changes=delta))
        rows.extend(dict(domain=k[0], id=k[1], disposition='ADDED_IN_CANDIDATE') for k in new)
    after = sha(source)
    if before != after:
        raise ValueError('OLD_PUBLICATION_CHANGED')
    result = dict(contract_id='R4_E03_OLD_PUBLICATION_DELTA_R1', run_utc=datetime.now(timezone.utc).isoformat(),
                  current_status='OBJECT_FIELD_DIFF_REVIEW_OPEN' if rows else 'OBJECT_FIELDS_EQUAL',
                  source_binding=binding, source_unchanged=True, pg_binding=prior['pg_binding'],
                  denominator=old_count, difference_records=len(rows), changed_objects=sum(domains.values()),
                  removed_objects=sum(r.get('disposition') == 'MISSING_IN_CANDIDATE' for r in rows),
                  added_objects=sum(r.get('disposition') == 'ADDED_IN_CANDIDATE' for r in rows), domains=dict(domains),
                  field_counts=dict(fields), differences=rows, owner='Codex / root',
                  limitations=['Field-level evidence does not authorize source changes, CAS, rollback or publication',
                               'Every delta remains unaccepted until provenance and contract review'],
                  next_conditions=['Classify source revision vs projection vs conversion per object', 'Joint CAS and rollback'])
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = out.with_suffix('.tmp')
    with gzip.open(temporary, 'wt', encoding='utf8') as stream:
        json.dump(result, stream, ensure_ascii=False, separators=(',', ':'))
    os.replace(temporary, out)
    print(json.dumps({k: result[k] for k in ('current_status', 'denominator', 'changed_objects', 'removed_objects', 'added_objects', 'domains')}))


if __name__ == '__main__':
    main()
