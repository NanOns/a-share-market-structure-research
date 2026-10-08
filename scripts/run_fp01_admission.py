"""Prepare and publish scoped operational admission for retained real V4 output."""
import json
import sys
from datetime import datetime, timezone

from fp01_evidence import ROOT, OUT, ref, write

sys.path.insert(0, str(ROOT / 'src'))
from v4.operational_release import ReleaseStore, admit, presentation


def prepare():
    head = json.loads((ROOT / 'data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json').read_bytes())
    output = next(r for r in head['artifact_refs'] if r['path'].endswith('/profile_advanced.jsonl.gz'))
    code = next(r for r in head['runtime_source_bindings'] if r['original_path'].endswith('/v4_13_profile_runtime.py'))
    source = ref('data/v4/V4_DATA_ACCEPTED_HEAD.json')
    meta = dict(owner='V4-13', release_id='FP01_RETAINED_REAL_PROFILE_20261008_R1',
        source_snapshot=source['sha256'], contract_version=head['contract_digest'],
        source_as_of='2026-10-03T00:00:00+08:00', trading_date='2026-09-30', input_digest=source['sha256'],
        published_at=datetime.now(timezone.utc).isoformat(), evidence_origin='REAL_ACCEPTED_SOURCE',
        evidence_state='VALIDATION_ONGOING', data_quality_state='QUALITY_DEGRADED',
        knowledge_lineage=head['knowledge_lineage'])
    request = dict(feature_id='V4_13_PROFILE_ADVANCED', metadata=meta, input=source,
        output=ref(output['path']), code=ref(code['path']), contract=ref('config/v4_13_active_contract_family_closure_r17r1.json'))
    write(OUT / 'admission_requests.json', dict(policy=ref('config/v4_operational_production_release_policy_v1.json'), requests=[request]))


def publish():
    package = json.loads((OUT / 'admission_requests.json').read_bytes())
    admissions = []
    for request in package['requests']:
        assert request.get('qa'), 'Run independent QA first; publication pins immutable QA receipt'
        admissions.append(admit(ROOT, package['policy'], request))
    release = dict(contract_id='V4_OPERATIONAL_RELEASE_V1', release_id=admissions[0]['metadata']['release_id'],
        admissions=admissions, full_product_release=False,
        consumption_scope='Existing real advanced-profile projection only; field UNKNOWN/degraded preserved. No newly computed sector/LOO signals or Focus writes.',
        next_stage='FP02_FP03_FP04_SEPARATE_TASK_DISPATCH')
    store = ReleaseStore(ROOT)
    before = store.current_digest()
    receipt = store.publish(release, before)
    readback = store.read()
    assert readback == release
    write(OUT / 'OPERATIONAL_RELEASE.json', release)
    write(OUT / 'OPERATIONAL_PUBLISH_RECEIPT.json', dict(**receipt, request_date='2026-10-08',
        presentation=presentation(admissions[0], '2026-10-08'),
        activation_scope='SUCCESSOR_OPERATIONAL_REGISTRY; HTTP_FULL_PRODUCT_ACTIVATION_RESERVED_FOR_FP14',
        external_acceptance='NOT_CLAIMED'))
    value = dict(contract_id='V4_PRODUCTION_RUNTIME_AUTHORITY_V2', version='2.0.0',
        predecessor=ref('config/v4_production_runtime_authority_v1.json'),
        policy=package['policy'], operational_registry=ref(OUT / 'OPERATIONAL_RELEASE.json'),
        operational_publish_receipt=ref(OUT / 'OPERATIONAL_PUBLISH_RECEIPT.json'),
        active_operational_scopes=[r['feature_id'] for r in admissions],
        source_mode='OPERATIONAL_PRODUCTION', activation_scope='RESEARCH_OPERATIONAL_REGISTRY',
        service_default_cutover='FP14_NOT_EXECUTED', data_date='2026-09-30',
        historical_production_permission='UNCHANGED_V1_EVIDENCE',
        full_product_release=False, focus_source_cutover=False, trading_action_authorized=False, tdx_write_authorized=False)
    write(ROOT / 'config/v4_production_runtime_authority_v2.json', value)
    print(json.dumps(receipt))


if __name__ == '__main__':
    prepare() if sys.argv[1] == 'prepare' else publish()
