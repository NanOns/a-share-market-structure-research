import pytest
from workbench_analysis.operational_new_listing_r1 import validate_basic
from workbench_analysis.security_entity_identity import stable_security_id

def basic(**kwargs):
    return dict(code='sz.301999',ipoDate='2026-10-13',outDate='',type='1',status='1',code_name='Example',**kwargs)

def test_current_day_ipo_stable_id_and_date_boundary():
    row=validate_basic('SZ.301999','2026-10-13',[basic()],set())
    assert row['security_id']==stable_security_id('SZ','SZ.301999','2026-10-13')
    from workbench_analysis.r43_operational_sources import date_valid_identity
    assert not date_valid_identity(row,'2026-10-12')
    assert date_valid_identity(row,'2026-10-13')
    assert row['board_scope']=='CHINEXT' and row['AS_RECORDED'] is False

@pytest.mark.parametrize('field,value',[('ipoDate','2026-10-12'),('ipoDate','2026-10-14'),('code','sz.301998'),('type','2'),('status','0'),('outDate','2026-10-13')])
def test_bad_lifecycle_or_code_stays_blocked(field,value):
    row=basic();row[field]=value
    with pytest.raises(ValueError):validate_basic('SZ.301999','2026-10-13',[row],set())

def test_duplicate_and_colliding_identity_stays_blocked():
    with pytest.raises(ValueError):validate_basic('SZ.301999','2026-10-13',[basic(),basic()],set())
    with pytest.raises(ValueError):validate_basic('SZ.301999','2026-10-13',[basic()],{stable_security_id('SZ','SZ.301999','2026-10-13')})
