"""Explicit four-board current V4 scope; raw provider rows stay represented."""
from collections import Counter
from decimal import Decimal,InvalidOperation
CONTRACT='V4_NATIVE_PROVIDER_ACCEPTED_SCOPE_RECONCILIATION_R3'
BOARDS={'SH_MAIN','SZ_MAIN','STAR','CHINEXT'}
def reconcile(native,daily,accepted_codes,policy,day):
    if policy.get('contract_id')!='TDX_A_STOCK_DELTA_SCOPE_POLICY_V2' or set(policy.get('required_boards',[]))!=BOARDS or policy.get('unknown_identity')!='QUARANTINE_NEVER_INVENT_CANONICAL_ID':
        raise ValueError('ACCEPTED_TYPED_SCOPE_POLICY_REQUIRED')
    accepted_codes=set(accepted_codes);errors=[];quarantine=[];compared=0
    keys=[row['source_security_key'].upper() for row in native]
    codes=[row['code'].upper() for row in daily]
    if len(keys)!=len(set(keys)):errors.append('DUPLICATE_NATIVE_CODE')
    if len(codes)!=len(set(codes)):errors.append('DUPLICATE_DAILY_CODE')
    if set(codes)!=accepted_codes:errors.append('DAILY_ACCEPTED_IDENTITY_SCOPE_MISMATCH')
    lookup={row['source_security_key'].upper():row for row in native}
    for code in sorted(set(keys)-accepted_codes):
        # No SH/SZ newcomer may disappear through this separate-board gate.
        if not code.startswith('BJ.'):errors.append('UNADMITTED_NATIVE_IDENTITY:'+code)
        quarantine.append(dict(code=code,reason='OUTSIDE_CURRENT_FOUR_BOARD_IDENTITY_SCOPE' if code.startswith('BJ.') else 'UNADMITTED_NATIVE_IDENTITY',formal_consumer_allowed=False))
    for row in daily:
        code=row['code'].upper();bar=lookup.get(code);state=row.get('tradestatus')
        if row.get('date')!=day or bar is not None and bar.get('trade_date')!=day:errors.append('TARGET_DATE_MISMATCH:'+code)
        if state not in ('0','1'):errors.append('UNKNOWN_TRADING_STATUS:'+code)
        elif state=='0' and bar:errors.append('SUSPENDED_WITH_TARGET_BAR:'+code)
        elif state=='1' and not bar:errors.append('ACTIVE_NATIVE_BAR_MISSING:'+code)
        elif state=='1':
            for field in ('open','high','low','close','volume'):
                compared+=1
                try:
                    left=Decimal(str(row[field]));right=Decimal(str(bar[field]))
                    if not left.is_finite() or not right.is_finite() or left!=right:errors.append('NATIVE_VALUE_MISMATCH:'+code+':'+field)
                except (KeyError,InvalidOperation,ValueError):errors.append('INVALID_NATIVE_VALUE:'+code+':'+field)
    return dict(contract_id=CONTRACT,status='SCOPED_REQUIRED_PROVIDER_FACTS_RECONCILED' if not errors else 'SOURCE_RECONCILIATION_FAILED',raw_native_rows=len(native),raw_daily_rows=len(daily),accepted_identity_rows=len(accepted_codes),compared_values=compared,errors=errors,quarantined_native_rows=quarantine,raw_denominator_preserved=True,all_market_scope_pass=False,scope='Explicit existing four-board contract and hash-bound dated canonical identity; BJ remains represented outside that capability')
