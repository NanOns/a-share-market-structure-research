"""Classify old publication field deltas against exact source and unit registries."""
from collections import Counter
import gzip
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.audit_r4_external_snapshot_delta import sha
from workbench_service.raw_turnover import cells
from workbench_service.production_v4 import compact_cell


def main():
    source_root = Path('G:/codex work/大A交易')
    out = ROOT / 'docs/audits/r4_external_repair_batch2_20261011'
    bindings = []
    def read(binding):
        path = source_root / binding['path']
        if sha(path) != binding['sha256']:
            raise ValueError('SOURCE_BINDING_CHANGED:' + binding['path'])
        bindings.append(binding)
        raw = gzip.decompress(path.read_bytes()) if str(path).endswith('.gz') else path.read_bytes()
        return [json.loads(line) for line in raw.splitlines() if line] if '.jsonl' in str(path) else json.loads(raw)
    old_manifest_path = source_root / 'data/v4/research_snapshots/8b4bbcc6a81e48a6b158e3bdf3bb84c8/manifest.json'
    prior = json.loads((ROOT / 'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b/R4_04_REAL_SNAPSHOT_RESULT.json').read_bytes())
    manifest_binding=prior['staged']['pointer']['previous']['manifest']
    if sha(old_manifest_path)!=manifest_binding['sha256']: raise ValueError('OLD_MANIFEST_CHANGED')
    old_manifest = json.loads(old_manifest_path.read_bytes())
    database = source_root / prior['original_binding']['path']
    if sha(database) != prior['original_binding']['sha256'] or Path(str(database) + '-wal').exists():
        raise ValueError('OLD_PUBLISHED_BINDING_CHANGED')
    raw_binding = old_manifest['sources']['RAW_DAILY']
    raw = {r['security_id']: r for r in read(raw_binding)['rows']}
    sector_binding = old_manifest['sources']['sector_operational']
    sectors = {r['sector_id']: r for r in read(sector_binding)}
    factor_denominators = {r['security_id']: {k: r['fields'][k] for k in
        ('rel_market_1', 'rel_market_3', 'rel_market_5', 'rps20', 'rps5') if k in r['fields']}
        for r in read(old_manifest['sources']['stock_factors'])}
    unit_path = source_root / 'config/v4_stock_unit_projection_v1.json'
    units = json.loads(unit_path.read_bytes())
    registries = [read(binding) for binding in units['registries']]
    registry = {(r['field_id'], r['parameter_set_id']): r for reg in registries for r in reg['fields']}
    with gzip.open(ROOT / 'docs/audits/r4_external_repair_20261011/E03_OBJECT_FIELD_DIFF.json.gz', 'rt', encoding='utf8') as stream:
        diff = json.load(stream)
    counts, uncovered = Counter(), []
    classified = []
    with sqlite3.connect(database.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        for object_diff in diff['differences']:
            if 'changes' not in object_diff:
                continue  # Focus IDs handled by the independent identity audit
            domain, ident = object_diff['domain'], object_diff['id']
            payload = json.loads(db.execute('SELECT payload FROM objects WHERE domain=? AND id=?', (domain, ident)).fetchone()[0])
            for change in object_diff['changes']:
                path = change['field'].split('/')
                field = path[3]
                property_name = path[4] if len(path) > 4 else None
                old_cell = payload['fields'].get(field, {})
                category = 'UNEXPLAINED'
                if domain == 'stocks' and field in ('amount', 'volume') and property_name is None:
                    expected = compact_cell(cells(raw[ident], old_manifest['context']['accepted_trade_date'], 'SHARES', 'CNY')[field],
                                            raw_binding, field, old_manifest['context']['accepted_trade_date'])
                    if change['old'] is None and change['candidate'] == expected:
                        category = 'EXACT_ACCEPTED_RAW_TURNOVER_NEW_PROJECTION'
                elif domain == 'stocks' and property_name in ('unit', 'adjustment_basis'):
                    spec = registry.get((field, old_cell.get('parameter_set_id')))
                    if spec:
                        expected = spec['unit'] if property_name == 'unit' else (
                            old_manifest['domain_features']['stocks']['price_basis'] if spec.get('price_basis') in ('QFQ', 'verified_affine_adjusted_OHLC') else spec.get('price_basis'))
                        if change['candidate'] == expected:
                            category = 'HASH_BOUND_UNIT_REGISTRY_PROJECTION'
                elif property_name in ('quality', 'reason') and old_cell.get('value') == 'UNKNOWN' and old_cell.get('quality') == 'KNOWN':
                    expected = 'UNKNOWN' if property_name == 'quality' else old_cell.get('reason') or 'OWNER_LITERAL_UNKNOWN_NOT_A_KNOWN_VALUE'
                    if change['candidate'] == expected:
                        category = 'LITERAL_UNKNOWN_QUALITY_CORRECTION'
                elif domain == 'sectors' and property_name == 'denominator':
                    native = sectors[ident]['fields'][field]
                    expected = native.get('n') if native.get('n') is not None else native.get('denominator') if native.get('denominator') is not None else native.get('known_count')
                    if change['candidate'] == expected:
                        category = 'EXACT_ACCEPTED_NATIVE_DENOMINATOR_PROJECTION'
                elif domain == 'stocks' and property_name == 'denominator':
                    native = factor_denominators[ident][field]
                    expected = native.get('n') if native.get('n') is not None else native.get('denominator') if native.get('denominator') is not None else native.get('known_count')
                    if change['candidate'] == expected:
                        category = 'EXACT_ACCEPTED_STOCK_DENOMINATOR_PROJECTION'
                counts[category] += 1
                record = dict(domain=domain, id=ident, field=change['field'], classification=category)
                classified.append(record)
                if category == 'UNEXPLAINED': uncovered.append(dict(record, **change))
    if sha(database) != prior['original_binding']['sha256']:
        raise ValueError('OLD_PUBLICATION_CHANGED')
    summary = dict(contract_id='R4_E03_FIELD_PROVENANCE_R1', owner='Codex / root',
                   current_status='FIELD_RULE_EXPLANATION_COMPLETE_ACCEPTANCE_OPEN' if not uncovered else 'PROVENANCE_REVIEW_OPEN',
                   denominator=len(classified), classifications=dict(counts), unexplained=uncovered,
                   bound_inputs=bindings, unit_contract_sha256=sha(unit_path), old_database_binding=prior['original_binding'],
                   source_unchanged=True, producer_sha256=sha(ROOT/'src/workbench_service/production_v4.py'),
                   limitations=['Explains candidate projection changes; does not prove byte-equivalent old publication migration',
                                'Approval of quality/unit/new fields, Amount A audit, Focus identity, CAS and rollback remain independent'])
    for name, data in [('FIELD_PROVENANCE_SUMMARY.json', summary), ('FIELD_PROVENANCE_OBJECT_LEDGER.json.gz', dict(summary, rows=classified))]:
        p = out / name; temporary = p.with_suffix('.tmp')
        if name.endswith('.gz'):
            with gzip.open(temporary, 'wt', encoding='utf8') as stream: json.dump(data, stream, ensure_ascii=False, separators=(',', ':'))
        else:
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        os.replace(temporary, p)
    print(json.dumps(dict(denominator=len(classified), classifications=dict(counts), unexplained=len(uncovered))))


if __name__ == '__main__': main()
