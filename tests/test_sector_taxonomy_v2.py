import pytest
from workbench_analysis.sector_taxonomy_v2 import primary_projection, auxiliary_projection


def member(sid='A'):
    return dict(sector_type='INDUSTRY', sector_id='INDUSTRY:T1', security_id=sid,
                membership_asof_date='2026-09-30', membership_basis='PIT_OBSERVED',
                membership_quality='PIT_OBSERVED_ACCEPTED', source_revision_id='sha256:x',
                source_file='T0002/hq_cache/tdxhy.cfg', source_file_digests={'x': 'sha256'},
                cutoff='2026-09-30T15:00:00Z', provider_available_at='2026-09-30T10:00:00Z',
                system_available_at='2026-09-30T10:00:00Z')


def test_aux_mutation_cannot_change_primary_and_tdx_mutation_does():
    producer = lambda rows: sorted(r['security_id'] for r in rows)
    a = primary_projection('2026-09-30', [member()], producer, auxiliary=['A'])
    assert a == primary_projection('2026-09-30', [member()], producer, auxiliary=['B', 'C'])
    assert a != primary_projection('2026-09-30', [member('B')], producer)


def test_wrong_namespace_and_future_membership_rejected():
    for changes in ({'sector_id': 'BAO_CSRC:C1'}, {'taxonomy': 'BAOSTOCK_CSRC_INDUSTRY'},
                    {'membership_asof_date': '2026-10-08'},
                    {'system_available_at': '2026-10-09T00:00:00Z'}):
        with pytest.raises(ValueError):
            primary_projection('2026-09-30', [dict(member(), **changes)], lambda x: x)


def test_missing_primary_keeps_auxiliary_separate():
    result = primary_projection('2026-10-08', [], lambda x: pytest.fail('must not run'), auxiliary={'value': 42})
    assert all(v['quality'] == 'UNKNOWN' for v in result.values())
    assert auxiliary_projection({'relative_sector_state': {'value': 42}, 'rotation_state': 'UNKNOWN'}) == {
        'csrc_relative_sector_state': {'csrc_value': 42}, 'csrc_rotation_state': 'UNKNOWN'}


def test_primary_rejects_auxiliary_producer_or_prior_outputs():
    for output in ({'prior_rotation': {'sector_id': 'BAO_CSRC:C1'}},
                   {'csrc_sector_rs5': 42}, {'taxonomy': 'BAOSTOCK_CSRC_INDUSTRY'}):
        with pytest.raises(ValueError):
            primary_projection('2026-09-30', [member()], lambda rows: output)
