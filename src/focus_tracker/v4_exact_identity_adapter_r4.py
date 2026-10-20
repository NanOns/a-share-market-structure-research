"""Explicit candidate path: frozen security identity and exact local actions."""
from datetime import date
from decimal import Decimal
import json
import re

from adjustment.tdx_adjustment_v0_3 import build_affine_factors, xrxd_from_gbbq
from workbench_db.v4_series_pg_r1 import range_rows
from workbench_service.current_v4_context import SourceInvalid, canonical, digest
from .price_path import Bar, path_metrics
from .v4_native_core_adapter import AcceptedPaths as NativePaths
from .v4_path_adapter import checked, _resolve_series_identity

CONTRACT = 'V4_FOCUS_EXACT_SOURCE_IDENTITY_CANDIDATE_R4'
ACTION_CONTRACT = 'V4_FOCUS_EXACT_ACTION_ALLOWLIST_S1B_V1'


def action_supported(event, dispositions):
    """Only category 1 has a price formula; other categories need explicit ignore."""
    disposition = dispositions.get(str(event.category), {}).get('formal_disposition')
    if event.category == 1:
        return disposition in ('PRICE_AFFECTING_SUPPORTED', 'SUPPORTED_PRICE_AFFECTING')
    return disposition == 'NON_PRICE_AFFECTING'


def security_symbols(root, binding):
    """One frozen bijection shared by the Series producers and path consumer."""
    identity = json.loads(checked(root, binding).read_bytes())
    symbols, reverse = {}, {}
    for row in identity['rows']:
        sid, symbol = row['security_id'], row['source_security_key']
        if not re.fullmatch(r'(SH|SZ|BJ)\.[0-9]{6}', symbol):
            raise SourceInvalid('FOCUS_SOURCE_SECURITY_KEY_INVALID')
        if sid in symbols or symbol in reverse:
            raise SourceInvalid('FOCUS_SOURCE_SECURITY_IDENTITY_DUPLICATE')
        symbols[sid] = symbol
        reverse[symbol] = sid
    return symbols


class AcceptedPaths(NativePaths):
    def __init__(self, root, bindings):
        if bindings.get('path_contract') != CONTRACT:
            raise SourceInvalid('FOCUS_EXACT_IDENTITY_CONTRACT_REQUIRED')
        self.symbols = security_symbols(root, bindings['security_identity'])
        super().__init__(root, bindings)

    def path(self, sid, start, end):
        key = sid, start, end
        if key in self.cache:
            return self.cache[key]
        symbol = self.symbols.get(sid)
        if symbol is None:
            raise SourceInvalid('FOCUS_SOURCE_SECURITY_IDENTITY_MISSING')
        sessions = [day for day in self.calendar if start <= day <= end]
        if not sessions or sessions[0] != start or sessions[-1] != end:
            raise SourceInvalid('FOCUS_PATH_CALENDAR_BOUNDS')
        bars = dict(range_rows(self.series, sid, start, end))
        symbol=_resolve_series_identity(bars,sid,symbol)
        suspended, missing = [], []
        for day in sessions:
            status = self.status.get(day, {}).get(sid, {})
            if day in bars:
                if status.get('status_conflict') or status.get('actual_bar_present') is False:
                    missing.append(day)
            elif status.get('status') == 'SUSPENDED' and status.get('actual_bar_present') is False and not status.get('status_conflict'):
                suspended.append(day)
            else:
                missing.append(day)
        result = dict(quality='DATA_UNAVAILABLE', metrics=None, suspended_dates=suspended,
                      missing_dates=missing, target_state='BAR' if end in bars else 'SUSPENDED' if end in suspended else None,
                      anchor_actual_bar=start in bars, source_security_key=symbol, action_contract=ACTION_CONTRACT,
                      input_digest=digest(canonical(dict(contract=CONTRACT, action_contract=ACTION_CONTRACT, bindings=self.bindings, sid=sid, start=start, end=end))))
        if not missing and start in bars and end in bars:
            events = [e for e in self.events[symbol] if int(start.replace('-', '')) < e.event_date <= int(end.replace('-', ''))]
            blocked = any(not action_supported(e, self.dispositions) for e in events)
            if not blocked:
                factors = build_affine_factors([int(d.replace('-', '')) for d in sorted(bars)], [xrxd_from_gbbq(e) for e in events if e.category == 1])
                path = [Bar(date.fromisoformat(d), *[factors[int(d.replace('-', ''))].qfq_price(Decimal(str(v))) for v in bars[d]['raw_ohlc']]) for d in sorted(bars)]
                result.update(quality='READY', metrics={k: str(v) for k, v in path_metrics(path).items()}, close=str(path[-1].close), price_basis='TDX_EXACT_NATIVE_AFFINE_AS_OF_OBSERVATION_R4')
            else:
                result['reason'] = 'UNSUPPORTED_OR_UNKNOWN_PRICE_IMPACT'
        self.cache[key] = result
        return result
