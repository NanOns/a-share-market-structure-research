"""Declared fixtures exercise immutable admission, identity and session cutoff."""
import copy
import pytest
from workbench_analysis.validation_cohort_read_contract_r3 import *
def row():
    return dict(model_contract_id='M1',state_lineage_id='L1',entity_type='STOCK',entity_id='S1',episode_id='E1',event_type='NEW_CONFIRMED',T0='2026-09-30',publication_id='P1',frozen_signal_version='V1',frozen_at_T0='2026-09-30T16:00:00+08:00',eligible_at_T0=True,asof_first_available='2026-09-30T15:01:00+08:00',benchmark={'id':'B1'},no_lookahead=True,evidence_class='PIT_OBSERVED',cohort_namespace='SHADOW')
def read(rows):return read_statistics(dict(authorized_read=True,enrollments=rows),cutoff='2026-09-30T16:00:00+08:00',trade_date='2026-09-30')
def test_idempotent_distinct_events_and_no_source():
    a=row();b=dict(a,episode_id='E2');assert read([a,copy.deepcopy(a),b])['observed_count']==2
    assert read_statistics(None,cutoff='unused',trade_date='2026-09-30')['status']=='NO_AUTHORIZED_COHORT_OWNER'
def test_frozen_rewrite_rejected():
    a=row();b=dict(a,frozen_signal_version='V2')
    with pytest.raises(ValueError,match='REWRITE'):read([a,b])
@pytest.mark.parametrize('patch',[{'evidence_class':'RECONSTRUCTED_ASOF'},{'qualification_source':'Focus'},{'qualification_source':'Forward outcome'},{'no_lookahead':False},{'eligible_at_T0':False},{'asof_first_available':'2026-10-08T15:01:00+08:00'},{'T0':'2026-10-08'},{'asof_first_available':'2026-09-30T15:01:00'},{'future_outcome_in_prediction':True}])
def test_negative_admission(patch):
    with pytest.raises(ValueError):read([dict(row(),**patch)])
def test_holiday_gap_is_one_session_not_eight_days():
    s=['2026-09-30','2026-10-08','2026-10-09','2026-10-12','2026-10-13','2026-10-14'];p=maturity_schedule(s[0],s,'2026-10-09')
    assert p[1]['due_date']=='2026-10-08' and p[3]['due_date']=='2026-10-12' and p[3]['status']=='PENDING'
    assert p[5]['status']=='PENDING'

def test_later_read_cannot_backfill_historical_first_availability():
    a=dict(row(),asof_first_available='2026-10-08T15:00:00+08:00')
    with pytest.raises(ValueError,match='AFTER_T0_FREEZE'):
        read_statistics(dict(authorized_read=True,enrollments=[a]),cutoff='2026-10-09T16:00:00+08:00',trade_date='2026-10-09')

def test_missing_owner_counts_are_unknown():
    result=read_statistics(None,cutoff='unused',trade_date='2026-09-30')
    assert result['observed_count'] is None and result['matured_count'] is None
