from scripts.complete_a12_cascade_r1 import normalize_availability,diff

def test_reconstructed_revision_retains_input_time_and_uses_actual_new_time():
    old={'security_id':'fixture','formal_publication_at':'2026-09-29T01:00:00+00:00','fields':{'ret1':{'value':1,'available_at':'2026-09-29T01:00:00+00:00'}}}
    new=normalize_availability(old,'2026-10-01T04:00:00+00:00')
    assert new['input_formal_publication_at']==old['formal_publication_at']
    assert new['formal_publication_at']=='2026-10-01T04:00:00+00:00'
    assert new['fields']['ret1']['available_at']==new['formal_publication_at']
    assert new['formal_publication'] is False and new['first_availability_at_target_proven'] is False
    assert old['fields']['ret1']['available_at']=='2026-09-29T01:00:00+00:00'

def test_business_comparison_separates_provenance_from_changed_unknown_state():
    old={'security_id':'fixture','states':{'trend':{'value':'UP','unknown_reason':None,'source_publications':{'path':'old'}}},'input_digest':'a','publication_id':'old'}
    new={'security_id':'fixture','states':{'trend':{'value':'UP','unknown_reason':None,'source_publications':{'path':'new'}}},'input_digest':'b','publication_id':'new'}
    assert diff([old],[new])['security_rows_changed']==0
    new['states']['trend'].update(value=None,unknown_reason='LOCAL_WINDOW_UNKNOWN')
    result=diff([old],[new])
    assert result['security_rows_changed']==1 and result['field_change_counts']=={'states.trend.unknown_reason':1,'states.trend.value':1}
