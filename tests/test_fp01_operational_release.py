"""Operational policy counterexamples; synthetic inputs are engineering-only."""
import copy
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from v4.operational_release import (AdmissionError, ReleaseStore, admit, binding,
                                    encoded, presentation, project_path)


@pytest.fixture
def setup(tmp_path):
    def put(name, value):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded(value))
        return binding(tmp_path, name)
    source = put('input.json', {'engineering_fixture_only': True})
    output = put('output.json', {'fields': {'x': {'value': None, 'quality': 'UNKNOWN'}}})
    code, contract, verifier = [put(n + '.json', {'version': 1}) for n in ['code','contract','verifier']]
    policy = put('policy.json', dict(contract_id='V4_OPERATIONAL_PRODUCTION_RELEASE_POLICY_V1',
        trading_action_authorized=False, tdx_write_authorized=False,
        feature_ids=['core','dependent'], dependencies={'dependent':['core']},
        independent_verifier=verifier,
        required_metadata=['owner','release_id','source_snapshot','contract_version','source_as_of','trading_date','input_digest','published_at','evidence_origin','evidence_state','data_quality_state','knowledge_lineage']))
    meta = dict(owner='producer', release_id='engineering-fixture', source_snapshot=source['sha256'],
        contract_version='1', source_as_of='2026-09-30T16:00:00+08:00', trading_date='2026-09-30',
        input_digest=source['sha256'], published_at='2026-10-08T12:00:00+08:00',
        evidence_origin='REAL_PRODUCER_RUN', evidence_state='VALIDATION_ONGOING',
        data_quality_state='QUALITY_DEGRADED', knowledge_lineage='RECONSTRUCTED_CORRECTED')
    request = dict(feature_id='core', input=source, output=output, code=code, contract=contract, metadata=meta)
    def qa(req, patch=None):
        receipt = dict(contract_id='V4_OPERATIONAL_INDEPENDENT_QA_V1', feature_id=req['feature_id'],
            status='PASS', checked_by='independent-oracle', verifier=verifier, policy=policy,
            metadata=req['metadata'], **{k:req[k] for k in ['input','output','code','contract']},
            checks={k:'PASS' for k in ['REAL_LINEAGE','SCHEMA','FIELD_QUALITY','NO_FUTURE','SOURCE_READBACK','ROLLBACK_COMPATIBLE']})
        if patch:
            patch(receipt)
        req['qa'] = put('qa_' + req['feature_id'] + '.json', receipt)
        return req
    return tmp_path, put, policy, qa(request), qa


def release(item):
    return dict(contract_id='V4_OPERATIONAL_RELEASE_V1', release_id=item['metadata']['release_id'], admissions=[item])


def test_operational_admission_does_not_require_20_sessions_or_mature_forward(setup):
    root, put, policy, req, _ = setup
    legacy = put('legacy.json', {'production_permission': False, 'accepted_consecutive_market_sessions':20})
    old = (root / 'legacy.json').read_bytes()
    item = admit(root, policy, req)
    assert item['operational_state'] == 'OPERATIONAL_PRODUCTION_ACTIVE'
    assert item['evidence_state'] == 'VALIDATION_ONGOING'
    assert item['trading_action_authorized'] is False
    assert (root / legacy['path']).read_bytes() == old
    assert json.loads((root / req['output']['path']).read_bytes())['fields']['x']['quality'] == 'UNKNOWN'
    assert presentation(item, '2026-10-08') == dict(operational_state='DATA_PENDING',
        last_successful_trading_date='2026-09-30', evidence_state='VALIDATION_ONGOING',
        data_quality_state='QUALITY_DEGRADED', result_available=True)


@pytest.mark.parametrize('origin', ['FIXTURE','SYNTHETIC_HISTORY','SHADOW_TRIAL'])
def test_reject_nonreal_output(setup, origin):
    root, _, policy, req, qa = setup
    req['metadata']['evidence_origin'] = origin
    qa(req)
    with pytest.raises(AdmissionError, match='NON_REAL_OUTPUT'):
        admit(root, policy, req)


@pytest.mark.parametrize('field,value,error', [
    ('source_as_of','2026-10-09T00:00:00+08:00','FUTURE_SOURCE'),
    ('trading_date','2026-10-01','FUTURE_SOURCE'),
    ('input_digest','0'*64,'INPUT_IDENTITY'),
    ('data_quality_state','SOURCE_INCOMPLETE','REQUIRED_SOURCE'),
    ('data_quality_state','READY','INVALID_QUALITY'),
    ('evidence_state','STATISTICALLY_VALIDATED_SCOPED','STATISTICAL_CLAIM'),
    ('published_at','2026-10-08T12:00:00','TIMEZONE_REQUIRED'),
    ('owner','','METADATA_INCOMPLETE')])
def test_metadata_counterexamples(setup, field, value, error):
    root, _, policy, req, qa = setup
    req['metadata'][field] = value
    qa(req)
    with pytest.raises(AdmissionError, match=error):
        admit(root, policy, req)


@pytest.mark.parametrize('quality', ['PENDING','RIGHT_CENSORED'])
def test_unmatured_lifecycle_is_not_a_global_blocker(setup, quality):
    root, _, policy, req, qa = setup
    req['metadata']['data_quality_state'] = quality
    qa(req)
    assert admit(root, policy, req)['data_quality_state'] == quality


@pytest.mark.parametrize('patch,error', [
    (lambda r:r.update(status='FAIL'), 'INDEPENDENT_QA_REQUIRED'),
    (lambda r:r.update(checked_by='producer'), 'INDEPENDENCE'),
    (lambda r:r['checks'].update(NO_FUTURE='FAIL'), 'QA_CHECK_MISSING'),
    (lambda r:r['output'].update(sha256='1'*64), 'BOUND_SOURCE_CHANGED'),
    (lambda r:r.update(verifier={'path':'other.json'}), 'UNAPPROVED_QA_VERIFIER')])
def test_qa_fail_closed(setup, patch, error):
    root, _, policy, req, qa = setup
    qa(req, patch)
    with pytest.raises(AdmissionError, match=error):
        admit(root, policy, req)


def test_dependency_scope_does_not_block_independent_core(setup):
    root, _, policy, req, qa = setup
    core = admit(root, policy, req)
    dep = copy.deepcopy(req)
    dep['feature_id'] = 'dependent'
    qa(dep)
    with pytest.raises(AdmissionError, match='DEPENDENCY_NOT_OPERATIONAL'):
        admit(root, policy, dep)
    assert admit(root, policy, dep, {'core':core})['operational_state'] == 'OPERATIONAL_PRODUCTION_ACTIVE'


def test_exact_publish_failed_readback_and_rollback(setup):
    root, _, policy, req, _ = setup
    store = ReleaseStore(root)
    first = release(admit(root, policy, req))
    receipt = store.publish(first, None)
    previous = store.pointer.read_bytes()
    second = dict(first, description='green')
    def failure(_):
        raise RuntimeError('INJECTED_POST_SWAP_FAILURE')
    with pytest.raises(RuntimeError):
        store.publish(second, receipt['pointer_digest'], failure)
    assert store.pointer.read_bytes() == previous and store.read() == first
    success = store.publish(second, receipt['pointer_digest'])
    store.rollback(receipt['pointer_digest'], success['pointer_digest'])
    assert store.pointer.read_bytes() == previous
    with pytest.raises(AdmissionError, match='STALE_PREDECESSOR'):
        store.publish(second, 'f'*64)


def test_concurrent_cas_has_one_winner(setup):
    root, _, policy, req, _ = setup
    item = release(admit(root, policy, req))
    store = ReleaseStore(root)
    def call(i):
        try:
            return store.publish(dict(item, writer=i), None)['status']
        except AdmissionError as exc:
            return str(exc)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(call, range(2)))
    assert results.count('PASS') == 1
    assert all(r in ('PASS','PUBLISH_BUSY','STALE_PREDECESSOR') for r in results)
    assert store.read()['writer'] in (0,1)


def test_source_corruption_does_not_activate_candidate(setup):
    root, _, policy, req, _ = setup
    item = admit(root, policy, req)
    store = ReleaseStore(root)
    (root / req['output']['path']).write_bytes(b'corrupt')
    with pytest.raises(AdmissionError, match='BOUND_SOURCE_CHANGED'):
        store.publish(release(item), None)
    assert not store.pointer.exists()


@pytest.mark.parametrize('path', ['../outside','D:/new_tdx/file','/absolute','..\\outside'])
def test_path_boundary(setup, path):
    with pytest.raises(AdmissionError):
        project_path(setup[0], path)


def test_mixed_trading_context_rejected(setup):
    root, _, policy, req, qa = setup
    first = admit(root, policy, req)
    second = copy.deepcopy(req)
    second['feature_id'] = 'dependent'
    second['metadata']['trading_date'] = '2026-09-29'
    qa(second)
    other = admit(root, policy, second, {'core':first})
    value = release(first)
    value['admissions'].append(other)
    with pytest.raises(AdmissionError, match='MIXED_CONTEXT'):
        ReleaseStore(root).publish(value, None)
