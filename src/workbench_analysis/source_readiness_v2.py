"""Evidence gates never infer provider readiness from the clock."""
from datetime import date, datetime, time, timedelta
from .operational_daily_calendar_v2 import SHANGHAI

CONTRACT = 'V4_DAILY_SOURCE_READINESS_V2'


def source_readiness(trade_date, now, evidence=None, main_check='18:35',
                     factor_publication='18:00', buffer_minutes=30):
    if now.tzinfo is None:
        raise ValueError('AWARE_TIME_REQUIRED')
    if buffer_minutes < 30:
        raise ValueError('FACTOR_BUFFER_AT_LEAST_30_MINUTES')
    now = now.astimezone(SHANGHAI)
    day = date.fromisoformat(trade_date)
    earliest = max(datetime.combine(day, time.fromisoformat(main_check), SHANGHAI),
                   datetime.combine(day, time.fromisoformat(factor_publication), SHANGHAI)
                   + timedelta(minutes=buffer_minutes))
    result = dict(contract_id=CONTRACT, trade_date=trade_date, observed_at=now.isoformat(),
                  time_eligible=now >= earliest, eligible_at=earliest.isoformat(),
                  source_ready=False, derived_ready=False, published=False,
                  external_acceptance='NOT_GRANTED')
    if now < earliest:
        return dict(result, status='WAIT_MARKET_CLOSE' if now < datetime.combine(day, time(15), SHANGHAI)
                    else 'WAIT_BAOSTOCK_FACTOR', reason='TIME_GATE_NOT_REACHED')
    evidence = evidence or {}
    for source, wait in [('tdx', 'WAIT_TDX'), ('baostock_daily', 'WAIT_BAOSTOCK_DAILY'),
                         ('baostock_factor', 'WAIT_BAOSTOCK_FACTOR')]:
        proof = evidence.get(source, {})
        if proof.get('status') != 'VERIFIED' or proof.get('target_session') != trade_date:
            return dict(result, status=wait, reason='DATED_VERIFIED_SOURCE_REQUIRED', source=source)
        digest = proof.get('source_sha256', '')
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            return dict(result, status=wait, reason='SOURCE_DIGEST_REQUIRED', source=source)
        try:
            observed = datetime.fromisoformat(proof['observed_at'])
            if observed.tzinfo is None or observed > now:
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            return dict(result, status=wait, reason='AUDITABLE_OBSERVATION_REQUIRED', source=source)
        if source == 'tdx' and trade_date not in proof.get('bars_date_coverage', []):
            return dict(result, status=wait, reason='ACTUAL_BAR_COVERAGE_REQUIRED')
        if source != 'tdx' and proof.get('provider_date') != trade_date:
            return dict(result, status=wait, reason='PROVIDER_DATE_MISMATCH')
        if source == 'baostock_daily' and (proof.get('row_count', 0) <= 0 or
                                           not proof.get('identity_reconciliation_passed')):
            return dict(result, status=wait, reason='DAILY_COVERAGE_RECONCILIATION_REQUIRED')
        if source == 'baostock_factor' and proof.get('row_count', 0) == 0 and not proof.get('verified_no_change'):
            return dict(result, status=wait, reason='EMPTY_FACTOR_PROOF_REQUIRED')
    return dict(result, status='SOURCE_READY', source_ready=True)
