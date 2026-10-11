"""Separate readonly migration audit of Focus IDs and first-observation fields."""
import gzip
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from workbench_db.v4_native import connection
from scripts.audit_r4_external_snapshot_delta import changes, sha


def main():
    evidence = ROOT / 'docs/audits/r4_external_repair_batch2_20261011'
    prior = json.loads((ROOT / 'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b/R4_04_REAL_SNAPSHOT_RESULT.json').read_bytes())
    binding = prior['original_binding']
    source = Path('G:/codex work/大A交易') / binding['path']
    if sha(source) != binding['sha256'] or Path(str(source) + '-wal').exists():
        raise ValueError('FROZEN_OLD_PUBLICATION_REQUIRED')
    with sqlite3.connect(source.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        old = {json.loads(payload)['entity_id']: (ident, json.loads(payload))
               for ident, payload in db.execute("SELECT id,payload FROM objects WHERE domain='focus'")}
        count = db.execute("SELECT count(*) FROM objects WHERE domain='focus'").fetchone()[0]
        if len(old) != count:
            raise ValueError('OLD_FOCUS_ENTITY_AMBIGUOUS')
    with connection(prior['pg_binding']['schema'], read_only=True) as pg:
        if Path(pg.execute('SHOW data_directory').fetchone()[0]).resolve() != Path('G:/codex_tmp/full_system_r4_fbd23a6b/pg_data').resolve():
            raise ValueError('ISOLATED_CLUSTER_REQUIRED')
        new = {json.loads(payload)['entity_id']: (ident, json.loads(payload))
               for ident, payload in pg.execute("SELECT id,payload FROM objects WHERE domain='focus'")}
        if len(new) != pg.execute("SELECT count(*) FROM objects WHERE domain='focus'").fetchone()[0]:
            raise ValueError('CANDIDATE_FOCUS_ENTITY_AMBIGUOUS')
    rows = []
    field_counts = {}
    sensitive = []
    unexplained = []
    hash_mismatches = []
    identity_fields = ('episode_id', 'T0', 'end_date', 'parent_episode_id')
    for entity in sorted(old.keys() | new.keys()):
        left, right = old.get(entity), new.get(entity)
        if left is None or right is None:
            rows.append(dict(entity_id=entity, classification='ENTITY_ADDED_OR_REMOVED'))
            continue
        delta = [dict(field=p, old=a, candidate=b) for p, a, b in changes(left[1], right[1])]
        corrected = copy.deepcopy(left[1])
        for cell in corrected.get('fields', {}).values():
            if cell.get('value') == 'UNKNOWN' and cell.get('quality') == 'KNOWN':
                cell['quality'] = 'UNKNOWN'
                cell['reason'] = cell.get('reason') or 'OWNER_LITERAL_UNKNOWN_NOT_A_KNOWN_VALUE'
        if corrected != right[1]:
            unexplained.append(entity)
        def expected_id(payload):
            projected = {k: payload[k] for k in ('entity_id', 'display_name', 'symbol', 'fields')}
            raw = json.dumps(projected, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
            return entity + ':' + hashlib.sha256(raw).hexdigest()[:20]
        if expected_id(left[1]) != left[0] or expected_id(right[1]) != right[0]:
            hash_mismatches.append(entity)
        for d in delta:
            field_counts[d['field']] = field_counts.get(d['field'], 0) + 1
        field_identity = {k: dict(old=left[1].get('fields', {}).get(k),
                                  candidate=right[1].get('fields', {}).get(k)) for k in identity_fields}
        for key, values in field_identity.items():
            if values['old'] != values['candidate']:
                sensitive.append(dict(entity_id=entity, field=key, **values))
        rows.append(dict(entity_id=entity, old_id=left[0], candidate_id=right[0],
                         id_changed=left[0] != right[0], changes=delta,
                         first_observation_fields=field_identity,
                         classification='PAYLOAD_HASH_ID_CHANGED' if left[0] != right[0] else 'ID_UNCHANGED'))
    if sha(source) != binding['sha256']:
        raise ValueError('OLD_PUBLICATION_CHANGED')
    summary = dict(contract_id='R4_FOCUS_IDENTITY_DELTA_R1', denominator=len(old),
                   candidate_count=len(new), source_unchanged=True, source_binding=binding,
                   pg_binding=prior['pg_binding'], changed_ids=sum(r.get('id_changed', False) for r in rows),
                   entity_added=sorted(new.keys() - old.keys()), entity_removed=sorted(old.keys() - new.keys()),
                   changed_fields=field_counts, sensitive_identity_differences=sensitive,
                   quality_rule_reconstruction_mismatches=unexplained, producer_hash_reconstruction_mismatches=hash_mismatches,
                   producer_binding=dict(path='src/workbench_service/production_v4.py',sha256=sha(ROOT/'src/workbench_service/production_v4.py'),symbols=['compact_cell','build_snapshot.put']),
                   current_status='FIELD_PROVENANCE_REVIEW_OPEN',
                   owner='Codex / root', limitations=['Entity correspondence does not make old/new snapshot IDs equivalent',
                    'No joint CAS/rollback acceptance; observed T0 equality does not prove historical PIT'])
    for name, value in [('FOCUS_IDENTITY_SUMMARY.json', summary),
                         ('FOCUS_IDENTITY_PAIRS.json.gz', dict(summary, rows=rows))]:
        p = evidence / name
        temporary = p.with_suffix('.tmp')
        if name.endswith('.gz'):
            with gzip.open(temporary, 'wt', encoding='utf8') as stream:
                json.dump(value, stream, ensure_ascii=False, separators=(',', ':'))
        else:
            temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        os.replace(temporary, p)
    print(json.dumps({k: summary[k] for k in ('denominator', 'candidate_count', 'changed_ids', 'entity_added', 'entity_removed')}))
    print(json.dumps(dict(sensitive_identity_differences=len(sensitive), changed_fields=field_counts)))


if __name__ == '__main__':
    main()
