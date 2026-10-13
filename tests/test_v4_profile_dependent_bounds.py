import copy
import pytest
from workbench_db.v4_profile_dependent_corrections_pg_v1 import validate_replacement

def test_correction_cannot_change_d2_maturity():
    original=dict(maturity='NONE',input_provenance=dict(risk=dict(value='UNKNOWN')))
    replacement=copy.deepcopy(original);replacement['maturity']='CONFIRMED'
    with pytest.raises(ValueError,match='BUSINESS_STATE_CHANGED'):validate_replacement('focus',original,replacement)

def test_correction_cannot_turn_unknown_prewatch_into_eligible():
    original=dict(security_id='TEST',prewatch=dict(raw_qualification='UNKNOWN',risk_axis='UNKNOWN'))
    replacement=copy.deepcopy(original);replacement['prewatch'].update(raw_qualification='TRUE',risk_axis='LOW')
    with pytest.raises(ValueError,match='RAW_QUALIFICATION_CHANGED'):validate_replacement('prewatch',original,replacement)

def test_correction_cannot_change_confirmed_input():
    original=dict(input_provenance=dict(risk=dict(value='UNKNOWN'),CONFIRMED=dict(value='UNKNOWN')))
    replacement=copy.deepcopy(original);replacement['input_provenance']['CONFIRMED']['value']='TRUE'
    with pytest.raises(ValueError,match='UNRELATED_INPUT_VALUE_CHANGED'):validate_replacement('focus',original,replacement)
