"""R4 versioned, resumable acquisition. Observations never publish owners."""
from __future__ import annotations

import hashlib
import json
import math
import struct
import time
from datetime import datetime, timezone
from pathlib import Path

from .baostock_supplemental import BaoStockClient, RequestBudget, package_metadata
from .daily_source_freeze import ensure_outside_tdx
from .tdx_official_daily_source import _atomic_write, capture_tdx_official_daily_package

CONTRACT = 'V4_MARKET_SOURCE_FALLBACK_POLICY_V1'
FIELDS = 'date,code,open,high,low,close,volume,amount,tradestatus,isST,adjustflag'


def is_stock_code(code):
    # SZ.399xxx is an index, not a CHINEXT stock.
    return code.lower().startswith(('sh.6','sz.00','sz.30','bj.'))


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    raw=(json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    for attempt in range(4):
        try:
            _atomic_write(Path(path), raw, tdx_root=Path('D:/new_tdx'))
            return
        except PermissionError:
            if attempt==3:raise
            time.sleep(0.1)


def official_sessions(root):
    from .dm01_runtime_r4 import calendar
    head = json.loads((root / 'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes())
    historical = json.loads((root / head['calendar']['path']).read_bytes())
    return sorted(set(historical['session_dates']) | set(calendar(root)['session_dates']))


def read_day_bytes(data, dates):
    if len(data) % 32:
        raise ValueError('TDX_DAY_RECORD_ALIGNMENT')
    wanted = {int(d.replace('-', '')): d for d in dates}
    bars, last = {}, None
    for offset in range(0, len(data), 32):
        day, o, h, l, c, amount, volume, _ = struct.unpack_from('<IIIIIfII', data, offset)
        last = day
        if day in wanted:
            if wanted[day] in bars:
                raise ValueError('TDX_DUPLICATE_DATE')
            bars[wanted[day]] = dict(open=o / 100, high=h / 100, low=l / 100, close=c / 100,
                                      amount=amount, volume=volume, unit='CNY/share;shares;CNY',
                                      hash=digest(data[offset:offset + 32]), price_basis_id='TDX_RAW')
    return bars, last


def corrected_candidate(tdx, bao, *, identity_verified, session_verified, overlap_verified,
                        tolerance_accepted, coordinate_verified):
    """Field admission is explicit. A staged RAW never grants an ATR coordinate."""
    if tdx is not None:
        return dict(status='TDX_PRESERVED', source='TDX', raw=tdx, production_admission=False)
    required = ['code', 'date', 'tradestatus', 'open', 'high', 'low', 'close', 'volume', 'amount']
    if not bao or any(k not in bao for k in required):
        return dict(status='REJECTED_WITH_EVIDENCE', reason='COVERAGE_INSUFFICIENT')
    try:
        values = {k: float(bao[k]) for k in required[3:]}
        valid = (all(math.isfinite(v) for v in values.values()) and
                 0 < values['low'] <= min(values['open'], values['close']) <=
                 max(values['open'], values['close']) <= values['high'] and
                 values['volume'] >= 0 and values['amount'] >= 0 and
                 values['volume'].is_integer() and bao['tradestatus']=='1')
    except (ValueError, TypeError):
        valid = False
    gates = dict(identity=identity_verified, session=session_verified, OHLCVA=valid,
                 independent_overlap=overlap_verified, source_tolerance=tolerance_accepted)
    return dict(status='BAOSTOCK_FALLBACK_CORRECTED' if all(gates.values()) else 'REJECTED_WITH_EVIDENCE',
                gates=gates, raw=bao, price_basis_id='BAOSTOCK_RAW_V1',
                qfq='UNPROVEN' if not coordinate_verified else 'COORDINATE_VERIFIED',
                ATR_allowed=all(gates.values()) and coordinate_verified,
                lineage='RECONSTRUCTED_CORRECTED', AS_RECORDED=False, production_admission=False)


def freeze_membership_observation(root, folder, dates, roots):
    files = []
    for source_root in roots:
        for name in ('tdxhy.cfg', 'tdxzs.cfg', 'infoharbor_block.dat', 'block_gn.dat', 'block_fg.dat', 'block_zs.dat'):
            path = Path(source_root) / 'T0002/hq_cache' / name
            if not path.exists():
                files.append(dict(path=str(path), status='LOCAL_FILE_ABSENT')); continue
            before = path.stat(); data = path.read_bytes(); after = path.stat()
            if (before.st_mtime_ns,before.st_size)!=(after.st_mtime_ns,after.st_size):
                files.append(dict(path=str(path), status='SOURCE_CHANGED_DURING_READ')); continue
            target = folder / 'membership' / digest(data) / name
            if not target.exists():
                _atomic_write(target, data, tdx_root=Path(source_root))
            files.append(dict(path=str(path), snapshot=str(target), hash=digest(data), bytes=len(data),
                              mtime_utc=datetime.fromtimestamp(after.st_mtime,timezone.utc).isoformat(),
                              observed_at=now(), status='OBSERVED_CURRENT', effective_date=None,
                              historical_first_available='UNKNOWN', target_dates=dates))
    record=dict(contract_id='R4_DAILY_MEMBERSHIP_OBSERVATION_V1', files=files,
                policy='FREEZE_ON_EACH_DM01_RUN; NEVER_BACKDATE_MTIME_AS_EFFECTIVE_DATE',
                effective_date_admission=False)
    write(folder / 'membership_observation.json',record)
    return record


def acquire(root, dates, folder, gap_codes=()):
    """Live probes with append-only run folders, per-query successful checkpoints."""
    root, folder = Path(root), Path(folder)
    if not dates or any(d not in official_sessions(root) for d in dates):
        raise ValueError('OFFICIAL_SESSION_REQUIRED')
    ensure_outside_tdx(folder, Path('D:/new_tdx'))
    policy = json.loads((root / 'config/v4_market_source_fallback_policy_v1.json').read_bytes())
    if policy['contract_id'] != CONTRACT or policy['production_admission']:
        raise ValueError('ACQUISITION_STAGING_POLICY_REQUIRED')
    folder.mkdir(parents=True, exist_ok=True)
    receipt = dict(contract_id=CONTRACT, requested_at=now(), dates=dates, sdk=package_metadata(),
                   local={}, official={}, queries=[], session_attempts=[], production_admission=False)
    if (folder / 'acquisition.json').exists():
        receipt = json.loads((folder / 'acquisition.json').read_bytes())
        if receipt['dates'] != dates or receipt['contract_id'] != CONTRACT:
            raise ValueError('CHECKPOINT_SCOPE_MISMATCH')
    def checkpoint():
        write(folder / 'acquisition.json', receipt)
    checkpoint()
    # Every configured TDX root is a read-only input.
    roots = json.loads((root / 'config/dm01_go_forward_runtime_contract_r4.json').read_bytes())['read_only_tdx_roots']
    receipt['membership'] = freeze_membership_observation(root, folder, dates, roots)
    for source_root in roots:
        for market in ('sh', 'sz', 'bj'):
            for path in sorted((Path(source_root) / 'vipdoc' / market / 'lday').glob('*.day')):
                key = market + '.' + path.stem[-6:]
                try:
                    before = path.stat()
                    bars, last = read_day_bytes(path.read_bytes(), dates)
                    after = path.stat()
                    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
                        raise ValueError('SOURCE_CHANGED_DURING_READ')
                    receipt['local'][key] = dict(path=str(path), last_date=last, bars=bars, observed_at=now())
                except (ValueError, OSError) as exc:
                    receipt['local'][key] = dict(path=str(path), error=type(exc).__name__ + ':' + str(exc))
    checkpoint()
    # Capture metadata each date; historical packages can only be read as corrected observations.
    for day in sorted(dates, reverse=True):
        for attempt in range(2):
            started = now()
            try:
                result = capture_tdx_official_daily_package(target_date=day, snapshot_root=folder / 'official', timeout=30)
                receipt['official'].setdefault(day, []).append(dict(requested_at=started, received_at=now(), attempt=attempt, result=result))
                break
            except Exception as exc:
                receipt['official'].setdefault(day, []).append(dict(requested_at=started, received_at=now(), attempt=attempt,
                    status='PROVIDER_CALL_ERROR', error=BaoStockClient._safe_message(f'{type(exc).__name__}:{exc}')))
            checkpoint()
        checkpoint()
    budget = RequestBudget(root / 'reports/v4_baostock/request_ledger.json')
    def budget_total():
        if not budget.path.exists():return 0
        return sum(row['count'] for row in json.loads(budget.path.read_bytes())['by_shanghai_date'].values())
    budget_before=budget_total()
    def query(client, method, **params):
        key = digest(json.dumps([method, params], sort_keys=True).encode())
        target = folder / 'queries' / (key + '.json')
        if target.exists():
            prior = json.loads(target.read_bytes())
            if prior['status'] == 'BAOSTOCK_FOUND':
                return prior['rows']
        for attempt in range(2):
            record = dict(method=method, params=params, requested_at=now(), attempt=attempt,
                          query_identity=key, lineage='RECONSTRUCTED_CORRECTED')
            try:
                if not hasattr(client.sdk, method):
                    record.update(status='SOURCE_CONTRACT_BLOCKED', error='SDK_METHOD_UNSUPPORTED', request_count=0)
                    receipt['queries'].append(record); checkpoint(); return []
                time.sleep(0.15)
                rows, meta = client.query_rows('r4_' + method, method, max_rows=20000, max_pages=10, **params)
                record.update(status='BAOSTOCK_FOUND' if rows else 'PROVIDER_EMPTY_CONFIRMED',
                              rows=rows, metadata=meta, hash=digest(json.dumps(rows, sort_keys=True).encode()),
                              received_at=now(), row_count=len(rows))
                record['source_revision']=record['hash']
            except Exception as exc:
                record.update(status='PROVIDER_CALL_ERROR', error=client._safe_message(f'{type(exc).__name__}:{exc}'),
                              metadata=dict(client.last_query_result), received_at=now())
                receipt['queries'].append(record); checkpoint()
                continue
            # Persistence failure is not a provider failure or a reason to
            # repeat an already successful network call.
            revision_path=folder/'queries'/(key+'-'+digest(json.dumps(record,sort_keys=True).encode())+'.json')
            if not revision_path.exists():write(revision_path,record)
            # Only the resume checkpoint is mutable; every receipted response
            # points to immutable version bytes, including confirmed empties.
            write(target, record)
            receipt['queries'].append({k: v for k, v in record.items() if k != 'rows'} | dict(path=str(revision_path)))
            checkpoint(); return rows
        return []
    for attempt in range(2):
        client = BaoStockClient(budget, auth_mode='PUBLIC_ANONYMOUS', timeout=30)
        session = dict(attempt=attempt, requested_at=now())
        try:
            with client:
                session.update(status='LOGIN_SUCCESS', login=client.login_result, endpoint=client.runtime_endpoint)
                receipt['session_attempts'].append(session); checkpoint()
                query(client, 'query_trade_dates', start_date=min(dates), end_date=max(dates))
                universes = {}
                for day in sorted(dates, reverse=True):
                    universes[day] = query(client, 'query_all_stock', day=day)
                    query(client, 'query_daily_history_k_AStock', date=day)
                    query(client, 'query_daily_adjust_factor', date=day)
                # Three separate coordinates/capabilities; never infer QFQ from RAW.
                codes = sorted(set(gap_codes))
                smoke = codes[:1] or ['sh.600000']
                smoke_ok = True
                for code in smoke:
                    for flag in ('3', '2'):
                        smoke_ok &= bool(query(client, 'query_history_k_data_plus', code=code, fields=FIELDS,
                            start_date=min(dates), end_date=max(dates), frequency='d', adjustflag=flag))
                    query(client, 'query_adjust_factor', code=code, start_date='2026-01-01', end_date=max(dates))
                if smoke_ok:
                    # Full date batch remains distinct; per-stock fallback covers available Oct08 identities if batch absent.
                    latest = max(dates)
                    latest_batch = next((q for q in receipt['queries'] if q['method']=='query_daily_history_k_AStock'
                                         and q['params'].get('date')==latest and q['status']=='BAOSTOCK_FOUND'), None)
                    if not latest_batch:
                        codes = sorted(set(codes) | {r['code'] for r in universes[latest] if is_stock_code(r.get('code',''))})
                    for code in codes:
                        for flag in ('3', '2'):
                            query(client, 'query_history_k_data_plus', code=code, fields=FIELDS,
                                  start_date=min(dates), end_date=max(dates), frequency='d', adjustflag=flag)
                        query(client, 'query_adjust_factor', code=code, start_date='2026-01-01', end_date=max(dates))
                for day in dates:
                    query(client, 'query_stock_industry', date=day)
            session['logout'] = client.logout_result
            break
        except Exception as exc:
            session.update(status='PROVIDER_CALL_ERROR', error=client._safe_message(f'{type(exc).__name__}:{exc}'),
                           login=client.login_result, endpoint=client.runtime_endpoint, received_at=now())
            if session not in receipt['session_attempts']:
                receipt['session_attempts'].append(session)
            checkpoint()
    receipt['completed_at'] = now()
    receipt['baostock_request_count_this_run']=budget_total()-budget_before
    receipt['status'] = 'CAPTURE_OBSERVATIONS_READY' if any(q['status']=='BAOSTOCK_FOUND' for q in receipt['queries']) else 'SOURCE_CAPTURE_BLOCKED'
    checkpoint()
    return receipt
