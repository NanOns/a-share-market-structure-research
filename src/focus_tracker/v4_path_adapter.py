"""Verified V4 price paths and sealed-date outcomes, independent of legacy PG."""
import gzip
import json
import sqlite3
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from adjustment.tdx_adjustment import build_affine_factors, xrxd_from_gbbq
from tdx.gbbq_reader import read_gbbq
from workbench_service.current_v4_context import SourceInvalid, canonical, digest
from .outcomes import classify_outcome
from .path_state_v2 import STOCK_PRIORITY, classify_stock_v2
from .predicates import Tri
from .price_path import Bar, path_metrics
from .v4_successor import project

CONTRACT = 'R2_V4_FOCUS_PATH_OUTCOME_V2'


def checked(root, binding):
    root = Path(root).resolve()
    path = (root / binding['path']).resolve()
    if not path.is_relative_to(root) or digest(path.read_bytes()) != binding['sha256']:
        raise SourceInvalid('FOCUS_INPUT_DIGEST_OR_PATH_INVALID')
    return path


class AcceptedPaths:
    def __init__(self, root, bindings):
        self.root, self.bindings = Path(root), bindings
        for binding in bindings.get('implementation',{}).values():
            checked(root,binding)
        self.series = checked(root, bindings['series'])
        self.calendar = json.loads(checked(root, bindings['calendar']).read_bytes())['session_dates']
        self.events = defaultdict(list)
        for event in read_gbbq(checked(root, bindings['gbbq'])):
            self.events[event.security_id].append(event)
        self.dispositions = json.loads(checked(root, bindings['classification']).read_bytes())['dispositions']
        self.status = {}
        for day, binding in bindings['status'].items():
            rows = json.loads(checked(root, binding).read_bytes())['rows']
            if any(row['trade_date'] != day for row in rows):
                raise SourceInvalid('FOCUS_STATUS_DATE_MIX')
            self.status[day] = {row['security_id']: row for row in rows}
        self.cache = {}

    def path(self, sid, start, end):
        key = sid, start, end
        if key in self.cache:
            return self.cache[key]
        sessions = [day for day in self.calendar if start <= day <= end]
        if not sessions or sessions[0] != start or sessions[-1] != end:
            raise SourceInvalid('FOCUS_PATH_CALENDAR_BOUNDS')
        with sqlite3.connect(self.series.as_uri() + '?mode=ro', uri=True) as db:
            bars = {day: json.loads(payload) for day, payload in db.execute(
                'SELECT day,payload FROM bars WHERE security=? AND day>=? AND day<=?',
                (sid, start, end))}
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
                      anchor_actual_bar=start in bars, input_digest=digest(canonical(dict(
                          contract=CONTRACT, bindings=self.bindings, sid=sid, start=start, end=end))))
        if not missing and start in bars and end in bars:
            symbol = bars[end]['symbol']
            events = [e for e in self.events[symbol] if int(start.replace('-', '')) < e.event_date <= int(end.replace('-', ''))]
            blocked = any(self.dispositions.get(str(e.category), {}).get('formal_disposition', 'UNKNOWN_PRICE_IMPACT') in
                          ('PRICE_AFFECTING_UNSUPPORTED', 'UNKNOWN_PRICE_IMPACT') for e in events)
            if not blocked:
                factors = build_affine_factors([int(d.replace('-', '')) for d in sorted(bars)],
                                              [xrxd_from_gbbq(e) for e in events if e.category == 1])
                path = [Bar(date.fromisoformat(d), *[factors[int(d.replace('-', ''))].qfq_price(Decimal(v))
                            for v in bars[d]['raw_ohlc']]) for d in sorted(bars)]
                result.update(quality='READY', metrics={k: str(v) for k, v in path_metrics(path).items()},
                              close=str(path[-1].close), price_basis='TDX_NATIVE_AFFINE_AS_OF_OBSERVATION')
            else:
                result['reason'] = 'UNSUPPORTED_OR_UNKNOWN_PRICE_IMPACT'
        self.cache[key] = result
        return result


def enriched_project(days, paths):
    """Keep accepted lifecycle identities; enrich each observation at its own t.

    Exited episodes still receive price observations and settlement. Missing
    invalidation evidence stays UNKNOWN; partial confirmed predicates are kept.
    """
    result = project(days)
    rows = {day: {row['entity_id']: row for row in values} for day, values in days.items()}
    events = {(event['episode_id'], event['trade_date']): event for event in result['events']}
    for episode in result['episodes']:
        existing = {obs['trade_date']: obs for obs in episode['observations']}
        for day in sorted(days):
            if day < episode['start_date']:
                continue
            sid = episode['entity_id']
            row = rows[day].get(sid)
            obs = existing.get(day)
            if obs is None:
                obs = dict(trade_date=day, event='POST_EXIT_OBSERVATION', membership='NONE',
                           source_publication=row['publication_id'] if row else None,
                           knowledge_lineage='RECONSTRUCTED_CORRECTED', AS_RECORDED=False)
                episode['observations'].append(obs)
            fact = paths.path(sid, episode['start_date'], day)
            invalidation = {'INVALID': Tri.TRUE, 'VALID': Tri.FALSE}.get((row or {}).get('validity'), Tri.UNKNOWN)
            confirmed = ((row or {}).get('raw_qualification') or {}).get('CONFIRMED')
            predicate_facts = dict(has_actual_bar=fact['quality'] == 'READY', close=fact.get('close'),
                drawdown_current=(fact['metrics'] or {}).get('drawdown_current'), mfe=(fact['metrics'] or {}).get('mfe'),
                launch_confirm={'TRUE': True, 'FALSE': False}.get(confirmed),
                exited=episode['end_date'] is not None and day >= episode['end_date'],
                early_or_setup=obs.get('membership') == 'EARLY', waiting_evaluable=row is not None)
            decision = classify_stock_v2(predicate_facts, invalidation=invalidation, applicable=frozenset(STOCK_PRIORITY))
            obs.update(path_state=decision.resolved_primary_state, best_confirmed_state=decision.best_confirmed_state,
                       path_resolution=decision.path_resolution, path_reason='HIGHER_PRIORITY_UNRESOLVED' if decision.higher_priority_unresolved else None,
                       higher_priority_unresolved=list(decision.higher_priority_unresolved),
                       predicate_evidence=decision.predicate_evidence, price_path=fact, path_contract_id=CONTRACT)
            obs.pop('outcome_status',None)
            if (episode['episode_id'], day) in events:
                events[(episode['episode_id'], day)].pop('outcome_status',None)
                events[(episode['episode_id'], day)].update(obs)
        episode['outcomes'] = []
        asof = max(days)
        calendar = [date.fromisoformat(d) for d in paths.calendar if d <= asof]
        for anchor in episode['anchors']:
            for horizon in (1, 3, 5, 10, 20):
                start = anchor['trade_date']
                position = paths.calendar.index(start) + horizon
                target = paths.calendar[position] if position < len(paths.calendar) else None
                sealed = target in days
                fact = paths.path(episode['entity_id'], start, target) if sealed else None
                decision = classify_outcome(calendar=calendar, anchor_date=date.fromisoformat(start), horizon=horizon,
                    as_of_date=date.fromisoformat(asof), target_input_accepted=sealed, target_input_sealed=sealed,
                    anchor_actual_bar=bool(fact and fact['anchor_actual_bar']), target_data_state=fact['target_state'] if fact else None,
                    audited_suspension=bool(fact and fact['target_state'] == 'SUSPENDED'), path_complete=bool(fact and fact['quality'] == 'READY'))
                episode['outcomes'].append(dict(anchor_id=anchor['anchor_id'], horizon=horizon,
                    trade_date=asof, target_trade_date=decision.target_trade_date.isoformat() if decision.target_trade_date else None,
                    outcome_status=decision.status, reason_code=decision.reason_code, terminal=decision.terminal,
                    metrics=fact['metrics'] if fact and decision.status == 'OBSERVED' else None,
                    contract_id=CONTRACT, knowledge_lineage='RECONSTRUCTED_CORRECTED', AS_RECORDED=False))
    return result
