"""Read-only next-session gate. Never extends the frozen R43 four-session contract."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from .dm01_runtime_r4 import calendar

CONTRACT = 'V4_OPERATIONAL_NEXT_SESSION_PREFLIGHT_V1'


def next_session_gate(root, now=None):
    root = Path(root)
    now = now or datetime.now(ZoneInfo('Asia/Shanghai'))
    from workbench_db.v4_operational_live_head_pg_r1 import read_current
    current=read_current(root)
    head=current['candidate']
    last = head['accepted_trade_date']
    cal = calendar(root)
    next_day = next((d for d in cal['session_dates'] if d > last), None)
    result = dict(contract_id=CONTRACT, observed_at=now.isoformat(), last_good_trade_date=last,
                  last_good_head_sha256=current['head_sha256'], next_session=next_day,
                  calendar_binding=cal['binding'], calendar_sources=cal['sources'],
                  calendar_acceptance=cal['status'], head_mutated=False,
                  publication_permission=False, fixed_R43_dates_extended=False,
                  existing_capture_entrypoints=['scripts/capture_tdx_official_daily_package.py',
                                                'scripts/capture_baostock_daily_update.py'],
                  successor_required=['independent dated source freeze and Source QA',
                                      'dated identity/lifecycle/GBBQ bindings',
                                      'versioned operational successor builder and date contract',
                                      'CAS, failure rollback, real HTTP readback'])
    if not next_day:
        return dict(result, status='BLOCKED_EXACT_REASON', reason='OFFICIAL_CALENDAR_COVERAGE_EXHAUSTED')
    if now < datetime.fromisoformat(next_day + 'T15:00:00+08:00'):
        return dict(result, status='WAIT_PROVIDER', reason='NEXT_SESSION_NOT_CLOSED', data_state='DATA_PENDING')
    return dict(result, status='BLOCKED_EXACT_REASON', reason='OPERATIONAL_SUCCESSOR_BUILDER_AND_SOURCE_QA_NOT_ADMITTED',
                provider_state='NOT_REQUESTED_NO_NEW_SOURCE_COMPLETENESS_CLAIM', data_state='DATA_PENDING')
