import hashlib
from workbench_analysis.identity_authority_audit_r1 import field_matrix,independently_check_stable_id,FIELDS

def sample():
    r=dict(exchange='SH',symbol='SH.'+'123456',list_date='2001-01-02',delist_date=None,source_contract_id='BAOSTOCK_LIFECYCLE_FACTS_R5_V1',source_revision_id='sha256:fixture')
    r['security_id']='SEC-'+hashlib.sha256(b'SH\x00SH.123456\x002001-01-02').hexdigest()[:32].upper()
    return r

def test_current_tnf_cannot_prove_historical_type_or_lifecycle():
    m=field_matrix(sample(),tnf_present=True)
    assert set(m)==set(FIELDS)
    assert m['symbol']['local_current_corrob']=='LOCAL_TDX_AUTHORITY_CONFIRMED'
    assert m['security_type']['local_decoder_proves_historical_type'] is False
    assert m['lifecycle']['local_day_boundary_proves_legal_lifecycle'] is False
    assert m['listing_anchor']['classification']=='PROVIDER_RECONSTRUCTED_FACT'

def test_current_catalogue_discrepancy_does_not_rekey():
    r=sample();before=dict(r)
    m=field_matrix(r,official=dict(board='SH_MAIN',list_date='1999-01-01'))
    assert m['listing_anchor']['independent_corrob']=='DISCREPANCY'
    assert r==before and independently_check_stable_id(r)

def test_matched_current_catalogue_does_not_prove_historical_delisting():
    m=field_matrix(sample(),official=dict(board='SH_MAIN',list_date='2001-01-02'))
    assert m['listing_anchor']['independent_corrob']=='MATCH'
    assert m['lifecycle']['current_active_catalogue_proves_historical_delist'] is False

def test_official_alias_and_independent_derivation_fail_closed():
    r=sample();assert independently_check_stable_id(r)
    assert not independently_check_stable_id(r,'SH.'+'654321')
    m=field_matrix(r,official_alias={'path':'accepted-fixture','sha256':'a'*64})
    assert m['alias_relation']['classification']=='OFFICIAL_EXCHANGE_AUTHORITY_CONFIRMED'
    assert m['alias_relation']['fingerprint']=='RESEARCH_ONLY_NO_AUTOMATIC_ENTITY_UNION'
