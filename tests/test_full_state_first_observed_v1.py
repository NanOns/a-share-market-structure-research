"""Synthetic future-day engineering checks; no real Source Owner acceptance."""
import json
from datetime import datetime
import pytest
from workbench_analysis.v4_14_replay_io import publish
from workbench_analysis.full_state_first_observed_v1 import freeze_first_observed
from workbench_analysis.cohort_capture_readiness_r1 import prepare_capture

DAY = '2026-10-12'
NOW = DAY + 'T16:00:00+08:00'


def inputs(root, *, patch=None, row_patch=None):
    clock = dict(first_available=DAY+'T15:01:00+08:00', frozen_at=DAY+'T15:10:00+08:00')
    members = publish(root, 'members.json', dict(clock, T0=DAY, membership_basis='AS_RECORDED',
        membership_version='M2', security_ids=['SH.600001','SZ.000001']))
    model = publish(root, 'model.json', dict(clock, model_contract_id='STATE_MODEL_V1',
        parameters_sha256='a'*64, window_version='W20', scenarios=['BREAKOUT','PULLBACK']))
    rows = []
    for sid in ('SH.600001','SZ.000001'):
        for scenario in ('BREAKOUT','PULLBACK'):
            rows.append(dict(security_id=sid, scenario=scenario, state='TRUE' if scenario=='BREAKOUT' else 'FALSE',
                exclusion_reasons=[] if scenario=='BREAKOUT' else ['PREDICATE_FALSE'],
                episode_id=sid+scenario, event_type=scenario, benchmark={'id':'CSI300'},
                first_available=DAY+'T15:20:00+08:00', frozen_at=DAY+'T15:30:00+08:00'))
    rows[0].update(row_patch or {})
    state = dict(contract_id='FULL_MARKET_STATE_PRODUCER_OUTPUT_V1', T0=DAY,
        scope='ALL_ELIGIBLE_AND_INELIGIBLE_SIGNALS', evidence_class='PIT_OBSERVED',
        membership=members, model=model, publication_id='SYNTHETIC_P2', revision='r1',
        state_lineage_id='SYNTHETIC_L2', frozen_signal_version='V1', scenario_outputs=rows,
        first_available=DAY+'T15:15:00+08:00', frozen_at=DAY+'T15:40:00+08:00',
        capture_deadline=DAY+'T18:00:00+08:00')
    state.update(patch or {})
    binding = publish(root, 'state'+str(len(list(root.glob('state*'))))+'.json', state)
    return dict(root=root, state_binding=binding, membership_binding=members, model_binding=model,
                candidate_directory='docs/evidence/synthetic', clock=lambda:datetime.fromisoformat(NOW))


def test_new_t0_generated_freeze_extract_separate_grant(tmp_path):
    result = freeze_first_observed(**inputs(tmp_path))
    extracted = result['extraction']
    assert (extracted['eligible_count'], extracted['ineligible_count']) == (2,2)
    assert result['formal_status']=='BLOCKED' and result['observed_count'] is None
    assert result['source_owner_admitted'] is False
    owner = json.loads((tmp_path/result['state_owner']['path']).read_bytes())
    assert len(owner['cohort_signals'])==4
    assert all(r['window_version']=='W20' for r in owner['cohort_signals'])
    missing = publish(tmp_path, 'without_grant.json', dict(owners={DAY:{'validation_cohort':extracted['owner_binding']}},
        cohort_capture_receipts={DAY:extracted['capture_receipt_binding']}))
    args = dict(root=tmp_path, accepted_head=missing, owner_binding=extracted['owner_binding'],
                trade_date=DAY, revision='r1', cutoff=NOW)
    with pytest.raises(ValueError, match='WRITE_GRANT_REQUIRED'):
        prepare_capture(**args)
    grant = publish(tmp_path, 'synthetic_grant.json', dict(contract_id='COHORT_FIRST_CAPTURE_WRITE_GRANT_R1',
        capability='PREPARE_FIRST_CAPTURE', authorized=True, revoked=False, owner=extracted['owner_binding'],
        source_receipt=extracted['capture_receipt_binding'], trade_date=DAY, revision='r1',
        valid_from=DAY+'T15:00:00+08:00', valid_until=DAY+'T18:00:00+08:00'))
    head = publish(tmp_path, 'with_grant.json', dict(owners={DAY:{'validation_cohort':extracted['owner_binding']}},
        cohort_capture_receipts={DAY:extracted['capture_receipt_binding']}, cohort_write_grants={DAY:grant}))
    prepared = prepare_capture(**dict(args, accepted_head=head))
    assert prepared['eligible_count']==2 and prepared['production_write_authorized'] is False


@pytest.mark.parametrize('patch,row_patch', [
    ({}, {'state':None}), ({'scope':'FOCUS_TOP_K'}, {}),
    ({'first_available':DAY+'T17:00:00+08:00'}, {}),
    ({'capture_deadline':DAY+'T15:59:00+08:00'}, {}),
    ({}, {'first_available':DAY+'T17:00:00+08:00'}),
    ({'scenario_outputs':[]}, {}), ({}, {'benchmark':{}}),
])
def test_end_to_end_illegal_source_rejected(tmp_path, patch, row_patch):
    with pytest.raises(ValueError):
        freeze_first_observed(**inputs(tmp_path, patch=patch, row_patch=row_patch))
    assert not (tmp_path/'docs').exists()


def test_source_missing_and_original_missing_file(tmp_path):
    args = inputs(tmp_path)
    result = freeze_first_observed(**dict(args, state_binding=None))
    assert result['status']=='SOURCE_INCOMPLETE' and result['formal_status']=='BLOCKED'
    (tmp_path/args['state_binding']['path']).unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        freeze_first_observed(**args)


def test_same_revision_change_cannot_replace_original(tmp_path):
    original = freeze_first_observed(**inputs(tmp_path))
    raw = (tmp_path/original['state_owner']['path']).read_bytes()
    with pytest.raises(ValueError, match='OVERWRITE_FORBIDDEN'):
        freeze_first_observed(**inputs(tmp_path, row_patch={'episode_id':'CHANGED'}))
    assert (tmp_path/original['state_owner']['path']).read_bytes()==raw
