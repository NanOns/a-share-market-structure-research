from datetime import datetime, date, timedelta
import pytest
from workbench_analysis.operational_daily_calendar_v2 import plan_sessions, SHANGHAI
from workbench_analysis.source_readiness_v2 import source_readiness


def calendar():
    start, end = date(2026, 9, 1), date(2026, 11, 30)
    days = [start + timedelta(days=i) for i in range((end-start).days+1)]
    return dict(session_dates=[d.isoformat() for d in days if d.weekday()<5 and
                  not date(2026, 10, 1)<=d<=date(2026, 10, 7)], agreement=True,
                exchanges=['SSE','SZSE'], coverage_start=start.isoformat(), coverage_end=end.isoformat())


@pytest.mark.parametrize('clock,eligible,waiting', [
    ('16:00',['2026-10-08'],['2026-10-09']),
    ('18:34',['2026-10-08'],['2026-10-09']),
    ('18:35',['2026-10-08','2026-10-09'],[])])
def test_holiday_and_time(clock, eligible, waiting):
    p=plan_sessions('2026-09-30',datetime.fromisoformat('2026-10-09T'+clock+'+08:00'),calendar())
    assert p['eligible_sessions']==eligible and p['scheduled_sessions']==waiting
    assert p['source_ready'] is False


@pytest.mark.parametrize('count',[1,2,5,10,20,40])
def test_unbounded_catchup(count):
    cal=calendar(); sessions=cal['session_dates']; last=sessions[0]; target=sessions[count]
    p=plan_sessions(last,datetime.fromisoformat(target+'T22:10+08:00'),cal)
    assert p['eligible_sessions']==sessions[1:count+1]


def test_calendar_exhaustion():
    p=plan_sessions('2026-10-09',datetime(2026,12,1,tzinfo=SHANGHAI),calendar())
    assert p['status']=='CALENDAR_COVERAGE_EXHAUSTED'


def test_clock_is_not_provider_readiness():
    now=datetime.fromisoformat('2026-10-09T18:35+08:00')
    assert source_readiness('2026-10-09',now)['status']=='WAIT_TDX'
    assert not source_readiness('2026-10-09',now)['source_ready']


def test_sources_and_empty_factors():
    now=datetime.fromisoformat('2026-10-09T19:05+08:00'); day='2026-10-09'
    base=dict(status='VERIFIED',target_session=day,provider_date=day,source_sha256='a'*64,
              observed_at=now.isoformat(),row_count=5,identity_reconciliation_passed=True)
    evidence={k:dict(base) for k in ['tdx','baostock_daily','baostock_factor']}
    evidence['tdx']['bars_date_coverage']=[day]
    evidence['baostock_factor']['row_count']=0
    assert source_readiness(day,now,evidence)['status']=='WAIT_BAOSTOCK_FACTOR'
    evidence['baostock_factor']['verified_no_change']=True
    assert source_readiness(day,now,evidence)['source_ready']
    evidence['baostock_factor'].update(provider_date=None,proof_target_session=day,no_change_proof_sha256='b'*64)
    assert source_readiness(day,now,evidence)['source_ready']
    evidence['baostock_daily']['provider_date']='2026-10-08'
    assert source_readiness(day,now,evidence)['reason']=='PROVIDER_DATE_MISMATCH'


def test_naive_time_rejected():
    with pytest.raises(ValueError,match='AWARE_TIME'):
        plan_sessions('2026-09-30',datetime(2026,10,9),calendar())
