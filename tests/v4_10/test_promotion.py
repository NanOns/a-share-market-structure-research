from copy import deepcopy
import pytest
from scripts.promote_v4_09_accepted_head import read, validate, validate_head, HEAD, GLOBAL, RECEIPT

def test_promoted_exact():
    assert validate()['status'] == 'PASS'

@pytest.mark.parametrize('field,value', [('capabilities', {'REAL_SIGNAL_CAPABILITY':'REAL_SIGNAL_FULL_PASS'}),
    ('implementation_commit','wrong'), ('external_acceptance_decision','wrong'), ('production_permission', True),
    ('upstream_binding', {'path':'data/v4/V4_08_ACCEPTED_HEAD.json'}), ('artifact', {'sha256':'self-consistent-wrong'})])
def test_overclaim_or_wrong_authority_rejected(field, value):
    h=deepcopy(read(HEAD)); h[field]=value
    assert validate_head(h, read(GLOBAL), read(RECEIPT))['status']=='FAIL'
