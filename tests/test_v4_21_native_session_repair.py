"""Independent native contract assertions and S21 negative matrix."""
import hashlib
import json
from pathlib import Path
import pytest
from reports.r30.design_ledger import fixture,readback,scenario
from reports.r30r1.session_authority import receipt_session_status,session_countable

ROOT=Path(__file__).resolve().parents[1]


def negative(index):
    value=fixture(); row=value['sessions'][0]
    if index in (1,2,3,4): row['native_session_status']={1:'ACCEPTED',2:'MISSED',3:'NON_EVALUABLE',4:'UNKNOWN_NATIVE'}[index]
    if index==5: row['native_session_authority_sha256']='WRONG'
    if index==6:
        for ledger in ('sessions','events','outcomes'):
            for item in value[ledger]: item.update(evidence_lane='PRODUCTION_REAL',execution_mode='PRODUCTION')
    if index==7: row.update(projection_evaluable=False,projection_evaluable_reason='SIM_QUALITY',claimed_real_accepted_session=1)
    if index==8: row.update(native_session_status='MISSED_OBSERVATION_SLOT',projection_evaluable=True)
    return value


@pytest.mark.parametrize('i',range(1,9),ids=lambda i:f'S21-{i:02}')
def test_native_negative_matrix(i):
    result=readback(negative(i))
    assert result['status']=='BLOCKED_AFFECTED_SCOPE' and result['actual_real_rows_written']==0 and result['production_grant'] is False
    expected='UNKNOWN_SHADOW_NATIVE_SESSION_STATUS' if i<=4 else {5:'SHADOW_SESSION_OWNER_BINDING_MISMATCH',6:'PRODUCTION_SESSION_AUTHORITY_REQUIRED_NOT_COUNTABLE',7:'CLAIMED_REAL_SESSION_COUNT_MISMATCH',8:'MISSED_SLOT_CANNOT_BE_EVALUABLE'}[i]
    assert expected in result['errors']


def test_exact_owner_and_statuses_read_from_accepted_contract():
    source=ROOT/'config/v4_16_observation_slot_contract_v2.json'; owner=json.loads(source.read_bytes())
    c=json.loads((ROOT/'config/v4_21_continued_forward_observation_contract_v1.json').read_bytes()); policy=c['native_session_policy']
    assert policy['shadow_allowed_statuses']==owner['slot_states']
    binding=policy['shadow_owner']; assert binding['native_slot_states']==owner['slot_states']
    assert binding['contract_id']==owner['contract_id'] and binding['sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
    assert binding in c['owner_bindings']
    assert policy['production_accepted_binding'] is None and policy['production_current_real_gate_count']=='NOT_COUNTABLE_FOR_REAL_GATE'


def test_missing_or_wrong_owner_and_compatibility_alias_rejected():
    for field in ('native_session_authority_id','native_session_authority_sha256'):
        value=fixture(); del value['sessions'][0][field]
        assert readback(value)['status']=='BLOCKED_AFFECTED_SCOPE'
        value=fixture(); value['sessions'][0][field]='WRONG'
        assert 'SHADOW_SESSION_OWNER_BINDING_MISMATCH' in readback(value)['errors']
    value=fixture(); value['sessions'][0]['slot_status']='ACCEPTED'
    assert 'COMPATIBILITY_SLOT_STATUS_MUST_EQUAL_NATIVE' in readback(value)['errors']


def test_receipt_keeps_native_and_projection_states_distinct():
    accepted=receipt_session_status(scenario(1)['sessions'][-1]); missed=receipt_session_status(scenario(5)['sessions'][-1]); quality=receipt_session_status(scenario(6)['sessions'][-1])
    assert accepted['accepted_session_status']==quality['accepted_session_status']=='ACCEPTED_ON_TIME'
    assert missed['accepted_session_status']=='MISSED_OBSERVATION_SLOT'
    assert accepted['projection_evaluable'] is True and missed['projection_evaluable'] is quality['projection_evaluable'] is False
    assert quality['projection_evaluable_reason'] and quality!=missed


def test_production_fixture_explicit_simulation_not_current_authority():
    value=scenario(16)
    assert value['kind']==value['production_session_authority']['status']=='CONTRACT_DESIGN_SIMULATION'
    assert readback(value)['status']=='PASS_DESIGN_ONLY'
    value['kind']='REAL_OBSERVATION'
    assert 'PRODUCTION_SESSION_AUTHORITY_REQUIRED_NOT_COUNTABLE' in readback(value)['errors']


def test_count_derivation_never_counts_non_evaluable_or_missed():
    for index in (5,6):
        value=scenario(index); row=value['sessions'][-1]
        assert not session_countable(row,value)
        assert readback(value)['breakdown'][0]['consecutive_accepted_sessions']==0
