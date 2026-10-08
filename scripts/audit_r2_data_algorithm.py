"""Read-only current publication inventory; atomic successor audit evidence."""
import collections
import gzip
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.fp01_evidence import write, ref
from workbench_service.joint_release import AUTHORITY, checked_path, validate
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.domain_views import objects

OUT = ROOT / 'docs/evidence/r2_data_algorithm_repair_20261008'


def main():
    if (OUT/'A0_GIT_AND_JOINT_MATRIX.json').exists():
        raise RuntimeError('A0_BASELINE_ALREADY_FROZEN_USE_NEW_EVIDENCE_NAMESPACE')
    before = (ROOT / AUTHORITY).read_bytes()
    joint = json.loads(before)
    manifest = validate(ROOT, joint)
    reader = ProductionV4ResearchReader(ROOT)
    git = {name: subprocess.check_output(args, cwd=ROOT, text=True).strip()
           for name, args in {
               'head': ['git', 'rev-parse', 'HEAD'],
               'status': ['git', 'status', '-sb'],
               'remote_system_reform': ['git', 'ls-remote', 'origin', 'refs/heads/codex/v4-system-reform'],
               'remote_work_branch': ['git', 'ls-remote', 'origin', 'refs/heads/codex/v4-fp14-r2-repair'],
           }.items()}
    write(OUT / 'A0_GIT_AND_JOINT_MATRIX.json', dict(
        contract_id='R2_DATA_ALGORITHM_REPAIR_V1', baseline='c68964eecc3653e3fb588113f615c925696959f9',
        git=git, joint_authority=ref(AUTHORITY), context=manifest['context'], metadata=manifest['metadata'],
        sources=manifest['sources'], owners=manifest['owners'], owner_authorities=joint['daily_owner_authorities'],
        snapshot=joint['snapshot'], first_available_at_target_proven=False,
        price_basis=manifest['domain_features']['stocks']['price_basis'],
        phase0=ref('reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json')))
    report = {}
    for domain in ('stocks', 'sectors', 'focus'):
        rows = objects(reader, domain)
        fields = collections.defaultdict(lambda: dict(known=0, unknown=0, reasons=collections.Counter(), samples=[]))
        for row in rows:
            for key, cell in row['fields'].items():
                entry = fields[key]
                missing = cell.get('value') is None or cell.get('value') == 'UNKNOWN' or cell.get('quality') == 'UNKNOWN'
                entry['unknown' if missing else 'known'] += 1
                if missing:
                    entry['reasons'][str(cell.get('reason') or cell.get('unknown_reason') or 'OWNER_UNKNOWN')] += 1
                if len(entry['samples']) < 2:
                    entry['samples'].append(dict(entity_id=row['entity_id'], cell=cell))
        report[domain] = dict(rows=len(rows), fields=dict(fields))
    write(OUT / 'CURRENT_FIELD_DEPENDENCIES.json', report)
    features = manifest['domain_features']
    focus = features['focus']
    obs = [o for e in focus['episodes'] for o in e['observations']]
    write(OUT / 'FOCUS_DEPENDENCY_COUNTS.json', dict(
        observations=len(obs), resolutions=dict(collections.Counter(o.get('path_resolution') for o in obs)),
        higher_priority_unknown=dict(collections.Counter(p for o in obs for p in o.get('higher_priority_unresolved', []))),
        native_unavailable=dict(collections.Counter(o.get('native_core_evidence', {}).get('reason') for o in obs
                                                   if o.get('native_core_evidence', {}).get('status') != 'BOUND')),
        forward_statistics=features['forward']['statistics']))
    sector = features['sector']
    write(OUT / 'SECTOR_OWNER_DEPENDENCIES.json', sector)
    native = []
    with gzip.open(checked_path(ROOT, sector['native']), 'rt', encoding='utf8') as stream:
        for line in stream:
            native.append(json.loads(line))
    write(OUT / 'SECTOR_NATIVE_SAMPLES.json', native[:5])
    assert (ROOT / AUTHORITY).read_bytes() == before
    print(json.dumps(dict(result='INVENTORIED',counts={k:v['rows'] for k,v in report.items()},
                         focus_observations=len(obs),sector_native=len(native))))


if __name__ == '__main__':
    main()
