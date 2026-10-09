from copy import deepcopy
import pytest
from workbench_analysis.tdx_member_retro_r43 import normalize_member_rows,normalized_frozen_rows


def test_complete_shared_normalization_is_pure_and_order_independent():
    identity={'SH.600001':{'security_id':'CANONICAL_1','list_date':'2000-01-01','delist_date':None}}
    rows=[dict(sector_id='INDUSTRY:T010101',sector_code='T010101',sector_type='INDUSTRY',sector_name='leaf',security_id='SH.600001',source='tdxhy.cfg'),
          dict(sector_id='INDUSTRY:T0101',sector_code='T0101',sector_type='INDUSTRY',sector_name='parent',security_id='SH.600001',source='tdxhy.cfg:DERIVED_PARENT'),
          dict(sector_id='THEME:GN1',sector_code='GN1',sector_type='THEME',sector_name='concept',security_id='BJ.920001',source='infoharbor_block.dat')]
    before=deepcopy((rows,identity))
    first=normalize_member_rows(rows,identity)
    assert first==normalize_member_rows(list(reversed(rows)),identity)
    assert (rows,identity)==before
    assert {r['industry_level'] for r in first}=={'LEAF','PARENT_DERIVED','CONCEPT'}
    assert next(r for r in first if r['industry_level']=='PARENT_DERIVED')['primary_industry_rank_eligible'] is False
    assert next(r for r in first if r['industry_level']=='CONCEPT')['identity_status']=='UNMAPPED_QUARANTINED'
    assert all(len(r)==12 for r in first)
    legacy=[{k:v for k,v in r.items() if k not in ('industry_level','primary_industry_rank_eligible')} for r in first]
    assert normalized_frozen_rows(legacy)==first


def test_duplicate_mapping_and_existing_classification_conflict_fail_closed():
    raw=dict(sector_id='INDUSTRY:T01',sector_code='T01',sector_type='INDUSTRY',sector_name='leaf',security_id='SH.600001',source='tdxhy.cfg')
    with pytest.raises(ValueError,match='DUPLICATE'):normalize_member_rows([raw,raw],{})
    row=normalize_member_rows([raw],{})[0]
    row['primary_industry_rank_eligible']=False
    with pytest.raises(ValueError,match='CLASSIFICATION_CONFLICT'):normalized_frozen_rows([row])
