from copy import deepcopy
import pytest
from scripts.verify_v4_11_semantics_r2 import verify
from scripts.v4_11_candidate_inputs_r2 import projection,positive_values,seal
from src.v4.confirmation import detect_confirmation,ConfirmationError

def test_source_formula_and_scenario_oracles():assert verify()['status']=='PASS_ENGINEERING'

def test_real_target_amr20_unavailable_remains_unknown():
    x=projection(real=True);out=detect_confirmation(x)
    assert len(out['rows'])==5224
    assert all(r['confirmation_status']=='UNKNOWN' for r in out['rows'])
    assert all(r['unavailable_input_facts']['amr20_mean_prior']=='STOCK_AMR20_TARGET_ACCEPTED_PRODUCER_PUBLICATION_UNAVAILABLE' for r in out['rows'])
    assert not any('AUD-AMOUNT-A-06' in str(r) for r in out['rows'])
    x['rows'][0]['facts']['amr20_mean_prior'].update(value=1.3,quality='KNOWN',acceptance='EXTERNALLY_ACCEPTED')
    with pytest.raises(ConfirmationError,match='SOURCE_FIELD_NOT_ACCEPTED_FOR_TARGET'):detect_confirmation(seal(x))

def test_sector_payload_cannot_alias_stock_ratio():
    x=projection(positive_values());x['rows'][0]['facts']['amount_a_value']=deepcopy(x['rows'][0]['facts']['amr20_mean_prior'])
    with pytest.raises(ConfirmationError,match='FACT_TIME_ROLE_MISMATCH'):detect_confirmation(seal(x))
