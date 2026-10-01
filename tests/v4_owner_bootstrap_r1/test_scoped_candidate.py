from copy import deepcopy
from pathlib import Path
import json
import pytest
from workbench_analysis.source_authority_owner_bootstrap_r1 import RULES,validate_owner,validate_registry

ROOT=Path(__file__).resolve().parents[2]

def registry():return json.loads((ROOT/'data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R4_CANDIDATE.json').read_bytes())
def owner(field):return next(x for x in registry()['owners'] if x['field_id']==field)
def check(o,**kw):return validate_owner(ROOT,o,field_id=o['field_id'],consumer=kw.get('consumer',o['allowed_consumers'][0]),target_date=kw.get('target_date','2026-09-30'),historical_mode=kw.get('historical_mode',o['historical_mode']))

def test_all_seven_fields_independent_candidates():
    assert validate_registry(ROOT,registry())['fields']==7
    assert all(x['external_acceptance']=='PENDING_INDEPENDENT_EXTERNAL_REAUDIT' for x in registry()['owners'])

@pytest.mark.parametrize('field',list(RULES))
@pytest.mark.parametrize('fault',['scope','consumer','hash','historical','external','promotion','supplemental'])
def test_each_field_fail_closed(field,fault):
    o=deepcopy(owner(field));kw={}
    if fault=='scope':kw['target_date']='2026-09-29'
    if fault=='consumer':kw['consumer']='UNREGISTERED_V4_11_FORMAL_BRANCH'
    if fault=='hash':o['artifact']['sha256']='0'*64
    if fault=='historical':kw['historical_mode']='MUTABLE_CURRENT_SNAPSHOT'
    if fault=='external':o['external_acceptance_evidence'][0]['sha256']='0'*64
    if fault=='promotion':o['external_acceptance']='EXTERNALLY_ACCEPTED';o['formal_consumer_authorization']=True
    if fault=='supplemental':o['source_family']='BAOSTOCK_SUPPLEMENTAL'
    with pytest.raises(ValueError):check(o,**kw)

def test_explicit_limits_and_inactive_global_root():
    assert owner('AMOUNT')['amount_a_formal_authority'] is False
    assert owner('QFQ')['degraded_capability']['status']=='DEGRADED_PASS'
    assert owner('QFQ')['canonical_adjustment']=='GBBQ_CANONICAL'
    assert 'HISTORICAL_LEGAL_LIFECYCLE_AND_TYPE_NOT_LOCAL_TDX_CONFIRMED' in owner('SECURITY_IDENTITY')['known_limitations']
    o=registry();o['active_global_trust_root']=True
    with pytest.raises(ValueError):validate_registry(ROOT,o)

@pytest.mark.parametrize('field,change',[('AMOUNT',('amount_a_formal_authority',True)),('QFQ',('historical_as_recorded_proven',True)),('SECURITY_IDENTITY',('known_limitations',[])),('SECTOR_MEMBERSHIP',('mutable_current_snapshot_is_historical_authority',True))])
def test_no_hidden_scope_upgrade(field,change):
    o=owner(field);o[change[0]]=change[1]
    with pytest.raises(ValueError):check(o)
