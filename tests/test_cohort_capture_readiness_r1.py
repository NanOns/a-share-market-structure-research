"""Synthetic receipt boundary tests; no real first-capture is produced."""
import copy
import hashlib
import json
import pytest
from test_cohort_admission_r4 import frozen
from workbench_analysis.cohort_capture_readiness_r1 import prepare_capture


def fixture(root, target=None, patch=None):
    def put(name, value):
        path = root / name
        path.write_text(json.dumps(value), encoding='utf8')
        return {'path': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    a = frozen()
    a['parameters_sha256'] = 'a' * 64
    b = dict(a, entity_id='S2', eligible_at_T0=False, ineligibility_reason='SOURCE_INCOMPLETE')
    rows = [a, b]
    if target == 'row':
        rows[1].update(patch)
    if target == 'duplicate':
        rows.append(copy.deepcopy(a))
    signals = put('signals.json', {'signals': rows})
    owner = put('owner.json', {'enrollments': [a], 'revision': 'r1', 'trade_date': a['T0']})
    receipt = dict(contract_id='COHORT_COMPLETE_SIGNAL_CAPTURE_R1', T0=a['T0'], revision='r1',
                   membership_basis='AS_RECORDED', membership_version='MEMBERS_R1', scope='ALL_ELIGIBLE_AND_INELIGIBLE_SIGNALS',
                   first_available=a['asof_first_available'], captured_at='2026-09-30T15:30:00+08:00',
                   accepted_at='2026-09-30T15:40:00+08:00', signals=signals, signal_count=len(rows),
                   publication_id='P1', frozen_signal_version='V1', parameters_sha256='a'*64)
    if target == 'receipt':
        receipt.update(patch)
    receipt_ref = put('receipt.json', receipt)
    grant = dict(contract_id='COHORT_FIRST_CAPTURE_WRITE_GRANT_R1', capability='PREPARE_FIRST_CAPTURE',
                 authorized=True, revoked=False, owner=owner, trade_date=a['T0'], revision='r1',
                 source_receipt=receipt_ref, valid_from='2026-09-30T15:00:00+08:00',
                 valid_until='2026-09-30T18:00:00+08:00')
    if target == 'grant':
        grant.update(patch)
    grant_ref = put('grant.json', grant)
    head = put('head.json', dict(owners={a['T0']: {'validation_cohort': owner}},
                               cohort_capture_receipts={a['T0']: receipt_ref},
                               cohort_write_grants={a['T0']: grant_ref}))
    return dict(root=root, accepted_head=head, owner_binding=owner, trade_date=a['T0'],
                revision='r1', cutoff=a['frozen_at_T0'])


@pytest.mark.parametrize('target,patch', [
    ('grant', {'capability': 'READ_STATISTICS'}), ('grant', {'revoked': True}),
    ('grant', {'revision': 'r2'}), ('grant', {'owner': {}}),
    ('grant', {'source_receipt': {}}), ('grant', {'authorized': False}),
    ('grant', {'valid_until': '2026-09-30T15:45:00+08:00'}),
    ('receipt', {'scope': 'FOCUS_TOP_K'}), ('receipt', {'membership_basis': 'CURRENT'}),
    ('receipt', {'signal_count': 1}), ('receipt', {'revision': 'r2'}),
    ('receipt', {'captured_at': '2026-10-09T15:00:00+08:00'}),
    ('row', {'eligible_at_T0': None}), ('row', {'ineligibility_reason': ''}),
    ('row', {'parameters_sha256': 'b'*64}), ('row', {'frozen_signal_version': 'V2'}),
    ('row', {'evidence_class': 'RECONSTRUCTED_ASOF'}),
    ('row', {'asof_first_available': '2026-10-09T15:00:00+08:00'}),
    ('duplicate', {}),
])
def test_denied(tmp_path, target, patch):
    with pytest.raises(ValueError):
        prepare_capture(**fixture(tmp_path, target, patch))


def test_prepared_isolated_only(tmp_path):
    result = prepare_capture(**fixture(tmp_path))
    assert result['eligible_count'] == 1 and result['ineligible_count'] == 1
    assert result['production_write_authorized'] is False
    assert result['observed_count'] is None and result['settled_count'] is None


@pytest.mark.parametrize('filename', ['signals.json', 'owner.json', 'receipt.json', 'grant.json'])
def test_digest_tamper(tmp_path, filename):
    args = fixture(tmp_path)
    (tmp_path / filename).write_text('{}', encoding='utf8')
    with pytest.raises(ValueError, match='DIGEST_MISMATCH'):
        prepare_capture(**args)
