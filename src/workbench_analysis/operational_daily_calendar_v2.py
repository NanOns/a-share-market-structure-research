"""Dynamic operational gap planning; frozen R43 and strict PIT are untouched."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from .dm01_runtime_r4 import calendar

CONTRACT = 'V4_OPERATIONAL_DAILY_CALENDAR_V2'
SHANGHAI = ZoneInfo('Asia/Shanghai')


def plan_sessions(last_good, now, cal, through_date=None, main_check='18:35'):
    if now.tzinfo is None:
        raise ValueError('AWARE_TIME_REQUIRED')
    now = now.astimezone(SHANGHAI)
    date.fromisoformat(last_good)
    requested = through_date or now.date().isoformat()
    date.fromisoformat(requested)
    sessions = cal['session_dates']
    if sessions != sorted(set(sessions)):
        raise ValueError('CALENDAR_SESSION_ORDER')
    if not cal.get('agreement') or cal.get('exchanges') != ['SSE', 'SZSE']:
        raise ValueError('OFFICIAL_CALENDAR_AGREEMENT_REQUIRED')
    if not cal['coverage_start'] <= last_good <= cal['coverage_end']:
        raise ValueError('LAST_GOOD_OUTSIDE_CALENDAR')
    if requested < last_good:
        raise ValueError('TARGET_BEFORE_LAST_GOOD')
    gate = time.fromisoformat(main_check)
    end = min(requested, now.date().isoformat())
    covered_end = min(end, cal['coverage_end'])
    missing = [d for d in sessions if last_good < d <= covered_end]
    eligible, waiting = [], []
    for day in missing:
        trigger = datetime.combine(date.fromisoformat(day), gate, SHANGHAI)
        (eligible if now >= trigger else waiting).append(day)
    next_session = next((d for d in sessions if d > covered_end), None)
    next_trigger = (datetime.combine(date.fromisoformat(waiting[0] if waiting else next_session), gate, SHANGHAI).isoformat()
                    if waiting or next_session else None)
    exhausted = end > cal['coverage_end']
    return dict(contract_id=CONTRACT, observed_at=now.isoformat(),
                last_good_trade_date=last_good, requested_through_date=requested,
                latest_closed_session=max((d for d in sessions if d <= covered_end and
                    now >= datetime.combine(date.fromisoformat(d), time(15), SHANGHAI)), default=None),
                eligible_target=max(eligible, default=last_good), missing_sessions=missing,
                eligible_sessions=eligible, scheduled_sessions=waiting,
                next_trigger_at=next_trigger, calendar_binding=cal.get('binding'),
                calendar_acceptance=cal.get('status'),
                status='CALENDAR_COVERAGE_EXHAUSTED' if exhausted else
                    ('TIME_ELIGIBLE' if eligible else 'WAIT_MARKET_CLOSE' if waiting else 'UP_TO_DATE'),
                source_ready=False, head_mutated=False, external_acceptance='NOT_GRANTED')


def gap_plan(root, now=None, through_date=None, main_check='18:35'):
    import json
    from pathlib import Path
    from .scoped_successor_r421 import sha
    head_path = Path(root) / 'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    head = json.loads(head_path.read_bytes())
    result = plan_sessions(head['accepted_trade_date'], now or datetime.now(SHANGHAI),
                           calendar(root), through_date, main_check)
    result['last_good_head_sha256'] = sha(head_path)
    return result
