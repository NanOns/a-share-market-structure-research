"""Explicit E1R1 local receipt/owner discovery; no source fetching or promotion."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess

from workbench_analysis.fep_e1.contracts import atomic_json, digest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/fep_e1_r1_repair'
BASELINE = 'e4ea913d8926e904e55cbf16993ec63c0e90b031'


def bind(path):
    p = ROOT / path
    raw = p.read_bytes()
    return dict(path=path, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def load(path):
    return json.loads((ROOT / path).read_bytes())


def checked(ref):
    actual = bind(ref['path'])
    assert actual['sha256'] == ref['sha256'], ref['path']
    if 'bytes' in ref or 'byte_count' in ref:
        assert actual['bytes'] == ref.get('bytes', ref.get('byte_count'))
    return actual


def atomic_raw(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_bytes(raw)
    os.replace(tmp, path)


def receipt_and_namespace():
    REPORT.mkdir(parents=True, exist_ok=True)
    atomic_raw(REPORT / '.gitattributes', b'* -text\n')
    desktop = Path('D:/Users/lps/Desktop/阶段任务')
    names = ['V4_FEP_EXECUTION_MASTER_V4_15E1_R1_REPAIR_20261005.md',
             'V4_15E1_R1_BLOCKER_REPAIR_TASK_20261005.md',
             'V4_15E1_R1_INDEPENDENT_EXTERNAL_AUDIT_20261005.md']
    for name in names:
        atomic_raw(REPORT / name, (desktop / name).read_bytes())
    name = 'V4_2_2_FEP_R2_EXTERNAL_DESIGN_ACCEPTANCE_20260930.md'
    raw = (desktop / name).read_bytes()
    assert len(raw) == 14019
    assert hashlib.sha256(raw).hexdigest() == 'cd279e26fb9753eb1e333c7554f9f06393c9232ee44ff7be6d86e2f2f65d178e'
    path = 'docs/evidence/fep_e1/' + name
    atomic_raw(ROOT / path, raw)
    receipt = bind(path)
    atomic_json(REPORT / 'EXTERNAL_DESIGN_RECEIPT_READBACK.json',
                dict(status='PASS', FEP_E1_EXTERNAL_DESIGN_RAW_RECEIPT='PASS',
                     raw_receipt=receipt, drive_authority_id='1SdxQCravi5BpyHQ7yb7_IanQpcI0wBW2',
                     delivery='USER_SUPPLIED_EXACT_LOCAL_RAW_BYTES'))
    authority = load('reports/fep_e1/DESIGN_AUTHORITY_READBACK.json')
    authority['external_design_acceptance'] = dict(status='PASS', binding=receipt)
    atomic_json(ROOT / 'reports/fep_e1/DESIGN_AUTHORITY_READBACK.json', authority)
    old = 'config/v4_18_migration_replay_contract_v1.json'
    successor = load(old)
    successor['contract_id'] = 'V4_18_MIGRATION_REPLAY_CONTRACT_V1_1'
    successor['supersedes'] = bind(old)
    successor['namespaces'].append('FEP_E1_ENGINEERING')
    successor['fep_engineering_namespace'] = dict(
        scope='FEP_ONLY_CURRENT_ENGINEERING', production_cutover=False,
        migration_replay_pass='NOT_GRANTED')
    for t in load('config/fep_namespace_contract_v1.json')['tables']:
        successor['namespace_matrix'].append(dict(
            state_or_table=t['table'], declaration=t['declaration'],
            read_source='FEP_E1_ENGINEERING', disposition='REFERENCE', write_target=None,
            immutable_source_identity='FEP_SCHEMA_DESIGN_V2 explicit primary/composite key and append-only fact identity; controlled CAS head',
            target_identity_rule=t['target_identity_rule'], rollback=t['rollback'],
            production_cutover=False, migration_replay_pass='NOT_GRANTED'))
    atomic_json(ROOT / 'config/v4_18_migration_replay_contract_v1_1.json', successor)
    atomic_json(REPORT / 'V4_18_NAMESPACE_SUCCESSOR_GATE.json', dict(
        status='PENDING_TEST', predecessor=bind(old),
        successor=bind('config/v4_18_migration_replay_contract_v1_1.json'),
        added_tables=33, production_cutover=False, migration_execution='NOT_GRANTED',
        accepted_head='NOT_CREATED'))
    protected = [str(p.relative_to(ROOT)).replace('\\', '/') for p in (ROOT / 'data/v4').glob('*ACCEPTED_HEAD*.json')]
    migrations = [str(p.relative_to(ROOT)).replace('\\', '/') for p in (ROOT / 'src/workbench_db/migrations/v4_postgres').glob('0[23][0-9]_*.sql')]
    atomic_json(REPORT / 'ENTRY_BASELINE.json', dict(
        baseline=BASELINE, stage_contract=bind('reports/fep_e1_r1_repair/' + names[1]),
        evidence=[bind('reports/fep_e1_r1_repair/' + n) for n in names],
        protected=[bind(p) for p in protected], pass_keep_migrations=[bind(p) for p in migrations],
        acceptance='PENDING_REPAIR', next='E1R1_INTEGRATED_RETEST',
        unrelated_worktree=subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True)))


def sample(ref, container=None):
    binding = checked(ref)
    p = ROOT / binding['path']
    if p.suffix == '.gz':
        with gzip.open(p, 'rt', encoding='utf8') as f:
            value = json.load(f) if p.name.endswith('.json.gz') else json.loads(next(f))
    else:
        value = load(binding['path'])
    if container:
        value = value[container][0]
    return binding, value


def occurrences(value, field, path=()):
    hits = []
    if isinstance(value, dict):
        for k, v in value.items():
            if k == field:
                hits.append(dict(path=list(path + (k,)), value=v))
            hits.extend(occurrences(v, field, path + (k,)))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            hits.extend(occurrences(v, field, path + (i,)))
    return hits


def owners():
    heads = {s: f'data/v4/V4_{s:02}_ACCEPTED_HEAD.json' for s in (4, 6, 9, 11, 12, 13)}
    heads[3] = 'data/v4/V4_03_ACCEPTED_HEAD_AMENDED_R1.json'
    inventories = []
    candidates = []
    # Explicit accepted head allocations. These are fixed paths, never latest.
    h3 = load(heads[3])
    receipt = checked(h3['evidence_bindings']['reports/v4_03/V4_03_FINAL_STAGE_RECEIPT_R1_20260928.json'])
    for path, sha in load(receipt['path'])['hashes']['artifacts'].items():
        if path.endswith('.jsonl.gz'):
            candidates.append((3, dict(path=path, sha256=sha), None, 'ACCEPTED_HISTORICAL'))
    candidates.append((4, load(heads[4])['accepted_artifact'], None, 'ACCEPTED_HISTORICAL'))
    matrix_path = 'reports/v4_11_r5a/OWNER_INPUT_AUTHORITY_MATRIX.json'
    checked(load(heads[11])['evidence_bindings'][matrix_path])
    ref = load(matrix_path)['fields'][0]['target_date_source_binding']['2026-09-30']
    candidates.append((11, ref, 'rows', 'ACCEPTED_ENGINEERING_RECONSTRUCTED'))
    with gzip.open(ROOT / ref['path'], 'rt', encoding='utf8') as f:
        owner_publication = json.load(f)
    candidates.append((11, owner_publication['profile'], 'rows', 'BOUND_RECONSTRUCTED_CORE_CANDIDATE'))
    checked(owner_publication['profile'])
    with gzip.open(ROOT / owner_publication['profile']['path'], 'rt', encoding='utf8') as f:
        core_owner = json.load(f)
    required_names = [f['field_name'] for f in load('config/fep_feature_registry_v1.json')['fields']]
    coverage = {name: sum(name in r['factor']['fields'] for r in core_owner['rows']) for name in required_names}
    atomic_json(REPORT / 'CURRENT_CORE_OWNER_FULL_FIELD_INVENTORY.json', dict(
        artifact=checked(owner_publication['profile']), row_count=len(core_owner['rows']),
        exact_field_presence=coverage, missing_fields=[k for k,v in coverage.items() if v==0],
        source_status=core_owner['accepted'], AS_RECORDED=core_owner['AS_RECORDED'],
        cutoff=core_owner['context']['knowledge_cutoff'], scope='RECONSTRUCTED_CORRECTED'))
    h12 = load(heads[12])
    manifest_ref = next(r for r in h12['publication_authority']['authorized_manifests']
                        if r['path'] == 'reports/v4_12_runtime_r13/real/2026-09-30/r1/runtime_manifest.json')
    checked(manifest_ref)
    manifest = load(manifest_ref['path'])
    candidates.append((12, manifest['artifacts'][0], None, 'ACCEPTED_ENGINEERING_RECONSTRUCTED'))
    candidates.append((13, load(heads[13])['artifact_refs'][0], None, 'ACCEPTED_ENGINEERING_RECONSTRUCTED'))
    samples = []
    for stage, ref, container, status in candidates:
        binding, row = sample(ref, container)
        samples.append((stage, binding, row, status))
        inventories.append(dict(owner_stage=f'V4-{stage:02}', owner_head=bind(heads[stage]),
                                artifact=binding, evidence_scope=status,
                                row_digest=digest(row), root_keys=sorted(row),
                                trade_date=row.get('trade_date'), entity=row.get('security_id')))
    fields = []
    for required in load('config/fep_feature_registry_v1.json')['fields']:
        name = required['field_name']
        discoveries = []
        for stage, binding, row, status in samples:
            for hit in occurrences(row, name):
                discoveries.append(dict(owner_stage=f'V4-{stage:02}', owner_head=bind(heads[stage]),
                                        owner_artifact=binding, evidence_scope=status,
                                        trade_date=row.get('trade_date'), **hit))
        historical = next((d for d in discoveries if d['owner_stage']=='V4-03'
                           and isinstance(d['value'], dict) and 'value' in d['value']), None)
        current = next((d for d in discoveries if d['evidence_scope']=='BOUND_RECONSTRUCTED_CORE_CANDIDATE'
                        and isinstance(d['value'],dict) and 'value' in d['value']), None)
        fields.append(dict(field_name=name, feature_contract_id='FEP_E1_FEATURES_V1',
                           owner_stage='V4-03' if historical else None,
                           owner_accepted_head=bind(heads[3]) if historical else None,
                           owner_artifact=historical['owner_artifact'] if historical else None,
                           owner_publication_revision_identity='CORE_FACTOR_V1 / V4_03_CORE_FACTOR_PARAMETER_SET_V1' if historical else None,
                           entity_key_path=['security_id'], trade_date_path=['trade_date'],
                           value_path=historical['path']+['value'] if historical else None,
                           quality_path=historical['path']+['quality_state'] if historical else None,
                           availability_authority=None, source_digest_rule=historical['path']+['output_digest'] if historical else None,
                           unit_source=required['source_registry_binding'], unit=required['unit'],
                           unit_transform='IDENTITY_ONLY', window_identity_path=historical['path']+['window_identity'] if historical else None,
                           allowed_scope=['FEP_STOCK_ENTRY_CORE'], mapping_status='CONFLICT_CURRENT_ENTRY_NOT_PROVEN',
                           reason='Historical exact owner path located where present; 2026-09-30 primitive value/quality/publication availability and ENTRY identity not proven. Reconstructed candidates cannot supply FIRST_OBSERVED identity.',
                           exact_name_discoveries=discoveries))
        fields[-1]['current_reconstructed_owner_mapping'] = (dict(
            owner_stage='V4-11 accepted sealed owner input', owner_accepted_head=bind(heads[11]),
            owner_artifact=current['owner_artifact'], entity_key_path=['factor','security_id'],
            trade_date_path=['factor','trade_date'], value_path=current['path']+['value'],
            quality_path=current['path']+['quality_state'], source_digest_path=current['path']+['output_digest'],
            window_identity_path=current['path']+['window_identity'],
            availability_authority=dict(path=current['path']+['available_at'], value=current['value']['available_at'],
                                        proof='Exact-bound sealed reconstructed owner factor receipt; not historical first availability'),
            mapping_status='RECONSTRUCTED_ENGINEERING_PATH_ONLY',
            value=current['value']['value'],
            quality=current['value']['quality_state'], source_digest=current['value']['output_digest'],
            full_inventory_present_rows=coverage[name]) if current else None)
        if current:
            mapping = fields[-1]['current_reconstructed_owner_mapping']
            fields[-1]['historical_owner_mapping'] = {k: fields[-1][k] for k in (
                'owner_stage','owner_accepted_head','owner_artifact','value_path','quality_path')}
            fields[-1].update(owner_stage=mapping['owner_stage'],
                              owner_accepted_head=mapping['owner_accepted_head'],
                              owner_artifact=mapping['owner_artifact'],
                              owner_publication_revision_identity=core_owner['rows'][0]['factor']['publication_id'],
                              entity_key_path=mapping['entity_key_path'], trade_date_path=mapping['trade_date_path'],
                              value_path=mapping['value_path'], quality_path=mapping['quality_path'],
                              availability_authority=mapping['availability_authority'],
                              source_digest_rule=mapping['source_digest_path'],
                              window_identity_path=mapping['window_identity_path'],
                              reason='Exact current reconstructed engineering owner path found; no complete accepted ENTRY admission or FIRST_OBSERVED authority. Required current market-relative/RPS owner fields remain missing.')
    atomic_json(REPORT / 'FEATURE_OWNER_EXACT_SAMPLE_READBACK.json', dict(
        evidence_class='OWNER_DISCOVERY_SAMPLE_NOT_RUNTIME_CONFIGURATION',
        fields=[dict(field_name=f['field_name'], discoveries=f['exact_name_discoveries']) for f in fields]))
    # Runtime mapping config holds selectors and contracts, never sample security IDs.
    for f in fields:
        for d in f['exact_name_discoveries']:
            d['value_digest']=digest(d.pop('value'))
    atomic_json(ROOT / 'config/fep_feature_source_map_v1.json', dict(
        contract_id='FEP_FEATURE_SOURCE_MAP_V1', required_trade_date='2026-09-30',
        required_count=47, fields=fields, status='FEP_E1_FEATURE_MAPPING_CONTRACT_CONFLICT',
        guessed_aliases=0, latest_or_mtime_mappings=0, dataset_complete=False))
    atomic_json(REPORT / 'FEATURE_OWNER_MAPPING_GATE.json', dict(
        status='BLOCKED', conflict='FEP_E1_FEATURE_MAPPING_CONTRACT_CONFLICT',
        required=47, implemented_current_entry=0,
        historical_exact_value_paths=sum(f['value_path'] is not None for f in fields),
        current_reconstructed_value_paths=sum(f['current_reconstructed_owner_mapping'] is not None for f in fields),
        current_core_missing_fields=[k for k,v in coverage.items() if v==0],
        inventory= inventories, explicit_head_discovery=[bind(p) for p in heads.values()],
        missing_owner_families=dict(V4_06='Scoped degraded engineering; accepted_input 2026-09-28, no current primitive field publication allocated',
                                    V4_09='PREWATCH engineering owner; priority/predicate fields do not grant primitive factor aliases'),
        contract=bind('config/fep_feature_source_map_v1.json')))
    atomic_json(REPORT / 'FEATURE_CURRENT_ENTRY_READBACK.json', dict(
        status='BLOCKED_NO_EXACT_CURRENT_ENTRY_47_FIELD_ADMISSION',
        target_trade_date='2026-09-30', accepted_data_head=bind('data/v4/V4_DATA_ACCEPTED_HEAD.json'),
        accepted_stage_head=bind('data/v4/V4_STAGE_ACCEPTED_HEAD.json'),
        dependency_manifest= inventories, manifest_digest=digest(inventories),
        logical_entry_observation='NOT_PROVEN_NO_FIRST_OBSERVED_EVENT',
        source_lineage='RECONSTRUCTED_CORRECTED_RETAINED',
        publication_lifecycle=dict(owner='V4-12', exact_manifest=checked(manifest_ref),
                                   available_at=manifest['available_at'], scope='ENGINEERING_RECONSTRUCTED_ONLY'),
        feature_side_complete=False, prediction_deadline='NOT_ENABLED', model_deadline='NOT_ENABLED',
        snapshots_inserted=0))
    timing_path='config/fep_entry_observation_timing_v1.json'
    atomic_json(ROOT/timing_path,dict(
        contract_id='FEP_ENTRY_OBSERVATION_TIMING_V1',
        status='ENGINEERING_RECONSTRUCTED_ONLY; CURRENT_ENTRY_ADMISSION_BLOCKED',
        owner_head=bind(heads[12]),publication_manifest=checked(manifest_ref),
        publication_available_at=manifest['available_at'],source_lineage='RECONSTRUCTED_CORRECTED',
        observation_time_rule='Exact accepted publication available_at is the earliest engineering read boundary; observed_at/feature_cutoff cannot precede consumed owner receipts',
        current_trade_date='2026-09-30',FIRST_OBSERVED='NOT_PROVEN',
        prediction_deadline='NOT_ENABLED',model_deadline='NOT_ENABLED',
        missing_47_field_admission='BLOCKED; no real ENTRY observation inserted'))
    entry=load('reports/fep_e1_r1_repair/FEATURE_CURRENT_ENTRY_READBACK.json')
    entry['timing_contract']=bind(timing_path)
    atomic_json(REPORT/'FEATURE_CURRENT_ENTRY_READBACK.json',entry)


def label_contract():
    head = bind('data/v4/V4_15_ACCEPTED_HEAD.json')
    atomic_json(ROOT / 'config/v4_15_fep_label_time_authority_v1.json', dict(
        contract_id='V4_15_FEP_LABEL_TIME_AUTHORITY_V1', version='1.0.0',
        stage='E1R1_ENGINEERING_CANDIDATE', accepted_owner_head=head,
        source_fact_available_at='MAX actual available_at of ALL exact consumed accepted fact receipts; complete immutable fact inventory required',
        label_training_mature_at='Exact owner maturity receipt requires full N-window and all quality/completeness gates; otherwise NOT_PROVEN',
        label_revision_available_at='Exact revision owner acceptance/readability receipt available_at; must be >= source_fact_available_at',
        forbidden_substitutes=['trade_date', 'due_date', 'report_cutoff', 'mtime', 'wall_clock'],
        pending_policy='NO_TRAINING_BINDING; retain denominator PENDING',
        real_maturity_permission='NOT_GRANTED', allocations=[]))
    from workbench_analysis.v4_15_persistence import Store
    from workbench_analysis.fep_e1.labels import read_source, project_with_owner_time
    from workbench_analysis.v4_15_fep_label_time import resolve
    store = Store(ROOT, 'reports/v4_15_runtime_r20/r20d_accepted_source_r3')
    rows = []
    for ref in store.refs('outcomes'):
        row = store.read(ref)
        if row['evidence_class'] != 'REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED':
            continue
        row = read_source(store, ref, row['outcome_revision_id'], row['evaluation_revision'], row['evaluation_source_digest'])
        authority = resolve(ROOT, row, '2026-10-05T00:00:00Z')
        result = project_with_owner_time(ROOT,row,dict(family='ABS_RETURN_N',horizon=row['horizon']),
                                        authority_head=load(head['path']),cutoff='2026-10-05T00:00:00Z')
        assert authority['binding'] is None and not result['training_allowed']
        rows.append(dict(upstream_binding=ref, authority=authority, adapter_result=result))
    atomic_json(REPORT / 'LABEL_ADAPTER_REAL_PENDING_READBACK.json', dict(
        status='PASS_ENGINEERING_FAIL_CLOSED_REAL_PENDING', real_rows=rows,
        label_source_bindings_inserted=0, denominator_disposition='PENDING',
        CURRENT_REAL_MATURITY_EVIDENCE='NONE', PROVED_HORIZONS=[],
        price_recomputation=False, accepted_owner_head=head))
    atomic_json(REPORT / 'LABEL_TIME_AUTHORITY_GATE.json', dict(
        status='PENDING_ENGINEERING_TEST', contract=bind('config/v4_15_fep_label_time_authority_v1.json'),
        real_receipt_authority='NOT_PROVEN', real_training='NOT_GRANTED'))


if __name__ == '__main__':
    receipt_and_namespace()
    owners()
    label_contract()
