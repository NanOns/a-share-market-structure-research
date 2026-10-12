"""Opt-in candidate period quality correction over the frozen current kernel."""
from .operational_daily_periods_v1 import derive_periods

CONTRACT='V4_EXACT_CANDIDATE_PERIOD_CONSUMER_R3'

def derive_exact_periods(member,history,statuses,sessions,target,coverage_end,*,indexed_calendar=False):
    """Never confuse inherited missing-status evidence with adjustment damage.

    No accepted publication is written and no missing bar becomes suspension.
    The frozen kernel's original classification is retained for audit.
    """
    results=derive_periods(member,history,statuses,sessions,target,coverage_end,indexed_calendar=indexed_calendar)
    by_date={bar['trade_date']:bar for bar in history}
    for capability,rows in results.items():
        for row in rows:
            row['candidate_contract_id']=CONTRACT
            row['original_kernel_period_status']=row['period_status']
            dates=[date for date in sessions if row['first_source_date'] and row['first_source_date']<=date<=row['max_source_date']]
            actual=[by_date[date] for date in dates if date in by_date]
            genuine_adjustment=(capability=='PERIOD_ADJUSTED' and any(not bar.get('qfq_ohlc') for bar in actual))
            if row['period_status']=='BLOCKED_BY_ADJUSTMENT' and not genuine_adjustment:
                if row.get('data_gap_count',0):
                    row.update(period_status='BLOCKED_BY_DATA_GAP',unknown_reason='PERIOD_REQUIRED_DATA_GAP')
                elif row.get('unknown_count',0):
                    row.update(period_status='BLOCKED_BY_UNKNOWN_STATUS',unknown_reason='PERIOD_REQUIRED_STATUS_UNKNOWN')
            row.update(production_accepted=False,PIT_ELIGIBLE=False,knowledge_lineage='RECONSTRUCTED')
    return results
