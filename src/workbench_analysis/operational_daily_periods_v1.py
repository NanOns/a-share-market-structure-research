"""Reconstruct operational periods with the unchanged accepted increment kernel.

The private scope binds only IO. Each security is replayed in target QFQ
coordinates, so a later action cannot leave an earlier period in old coordinates.
No remote period API is involved.
"""
from types import FunctionType
from . import dm01_incremental_component_builders_r3_3 as kernels
from .v4_12_structure_io import digest

CONTRACT_ID = 'OPERATIONAL_DAILY_PERIOD_REPLAY_V1'


def derive_periods(member, history, statuses, sessions, target, coverage_end):
    if target not in sessions or coverage_end < target:
        raise ValueError('PERIOD_OFFICIAL_CALENDAR_REQUIRED')
    dates = [d for d in sessions if history and history[0]['trade_date'] <= d <= target]
    by = {b['trade_date']: b for b in history}
    if len(by) != len(history) or any(d > target for d in by):
        raise ValueError('PERIOD_FUTURE_OR_DUPLICATE_BAR')
    result = {}
    for adjusted in (False, True):
        previous_rows = []
        cap = 'PERIOD_ADJUSTED' if adjusted else 'PERIOD_RAW'
        scope = dict(vars(kernels))
        for name, function in vars(kernels).items():
            if isinstance(function, FunctionType) and function.__module__ == kernels.__name__:
                scope[name] = FunctionType(function.__code__, scope, name, function.__defaults__, function.__closure__)
                scope[name].__kwdefaults__ = function.__kwdefaults__
        for day in dates:
            index = sessions.index(day)
            if not index:
                raise ValueError('PERIOD_PREDECESSOR_CALENDAR_REQUIRED')
            bar = by.get(day)
            state = 'ACTUAL_TRADED' if bar else statuses.get(day, 'UNKNOWN')
            daily = []
            if bar:
                prices = bar['qfq_ohlc'] if adjusted else bar['raw_ohlc']
                row = dict(member, trade_date=day, **dict(zip(('open', 'high', 'low', 'close'), prices or [None]*4)),
                           amount=bar['amount'], volume=bar['volume'], record_quality='SOURCE_FILE_VALIDATED_RECORD')
                if not prices:
                    row['unknown_reason'] = 'UNSUPPORTED_OR_UNPROVED_ADJUSTMENT'
                daily.append(row)
            deps = {'RAW_DAILY': daily, 'ADJUSTED_DAILY': daily,
                    'TRADING_STATUS': [dict(member, status=state)], 'IDENTITY_UNIVERSE': [member]}
            parent = {'rows': previous_rows}
            scope.update(_dependency=lambda c, key: (deps[key], {'logical_digest': digest(deps[key])}),
                         _parent_component=lambda c, key: (parent, {'sha256': digest(parent)}),
                         _actions=lambda c: ({}, {}),
                         _finish=lambda c, rows, extra=None: rows)
            context = dict(cap=cap, target=day, calendar=dict(session_dates=sessions, coverage_end=coverage_end),
                           parent={'head': {'accepted_trade_date': sessions[index-1]}})
            previous_rows = scope['_build_period'](context, adjusted)
        result[cap] = previous_rows
    return result
