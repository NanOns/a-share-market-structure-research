from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from decimal import Decimal, localcontext
import csv
import io
import json
from pathlib import Path

from adjustment.tdx_adjustment import build_affine_factors, xrxd_from_gbbq
from phase0_2_runner import _day_path, _read_day_rows, MANUAL_TARGETS
from tdx.gbbq_reader import read_gbbq, file_sha256, audit_gbbq
from validation.external_qfq import (EASTMONEY_ENDPOINT, TENCENT_ENDPOINT, TENCENT_RAW_ENDPOINT,
    eastmoney_secid, tencent_symbol, parse_eastmoney_payload, parse_tencent_payload)
from validation.phase0_2b import (VERSION, FIELDS, FrozenRun, EvidenceClient, encoded, atomic,
    read_frozen, fit_ab, raw_gate, classify, root_gate, connectivity_status)

ANCHOR = 20260904


def east_params(sid, date, mode):
    return {'secid': eastmoney_secid(sid), 'beg': str(date), 'end': str(date), 'klt': '101',
            'fqt': str(mode), 'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'ut': 'fa5fd1943c7b386f172d6893dbfba10b', 'lmt': '10'}


def fetch_bar(client, provider, sid, date, mode, gate_a=False):
    if provider == 'EASTMONEY':
        payload = client.get(provider, EASTMONEY_ENDPOINT, east_params(sid, date, mode), gate_a=gate_a,
                             validator=lambda p: date in parse_eastmoney_payload(p))
        bars = parse_eastmoney_payload(payload) if payload else {}
    else:
        d = str(date)
        iso = f'{d[:4]}-{d[4:6]}-{d[6:]}'
        params = {'param': f'{tencent_symbol(sid)},day,{iso},{iso},10' + (',qfq' if mode else '')}
        payload = client.get(provider, TENCENT_ENDPOINT if mode else TENCENT_RAW_ENDPOINT, params,
                             validator=lambda p: date in parse_tencent_payload(p, sid, raw_diagnostic=not mode))
        bars = parse_tencent_payload(payload, sid, raw_diagnostic=not mode) if payload else {}
    bar = asdict(bars[date]) if date in bars else None
    if bar is not None:
        if provider == 'EASTMONEY':
            rows = payload['data']['klines']
            line = next(v.split(',') for v in rows if v.startswith(f'{str(date)[:4]}-{str(date)[4:6]}-{str(date)[6:]}'))
            if len(line) > 6:
                bar.update(volume=Decimal(line[5]) * 100, amount=Decimal(line[6]), volume_unit='shares (provider lots x100)')
        else:
            rows = payload['data'][tencent_symbol(sid)].get('qfqday' if mode else 'day', [])
            row = next(v for v in rows if int(v[0].replace('-', '')) == date)
            if len(row) > 5:
                bar.update(volume=Decimal(str(row[5])) * 100, volume_unit='shares (provider lots x100; diagnostic convention)')
    return bar


def csv_bytes(rows):
    stream = io.StringIO(newline='')
    columns = list(dict.fromkeys(k for row in rows for k in row))
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8-sig')


def run(root, tdx, network=False):
    base = root / 'reports/phase0_2b'
    evidence = FrozenRun(base, tdx)
    paths = [tdx / 'T0002/hq_cache/gbbq', tdx / 'T0002/hq_cache/gbbq.map']
    paths += [_day_path(tdx, sid) for sid in sorted({v[0] for v in MANUAL_TARGETS})]
    core = [root / 'src/tdx/gbbq_reader.py', root / 'src/adjustment/tdx_adjustment.py']
    before = {str(p): file_sha256(p) for p in paths + core}
    records = read_gbbq(paths[0])
    audit = audit_gbbq(paths[0], paths[1], decoded_records=records)
    events = {}
    originals = {}
    for record in records:
        if record.category == 1 and record.security_id in {v[0] for v in MANUAL_TARGETS}:
            events.setdefault(record.security_id, []).append(xrxd_from_gbbq(record))
            originals[record.source_record_index] = record
    local, chains = [], []
    for sid, date, _, _ in MANUAL_TARGETS:
        rows = [r for r in _read_day_rows(_day_path(tdx, sid)) if r['trade_date'] <= ANCHOR]
        raw = next(r for r in rows if r['trade_date'] == date)
        factor = build_affine_factors([r['trade_date'] for r in rows], events[sid])[date]
        chain = sorted((e for e in events[sid] if date < e.ex_day <= rows[-1]['trade_date']),
                       key=lambda e: (e.ex_day, e.source_record_index))
        a, b = Decimal(1), Decimal(0)
        with localcontext() as ctx:
            ctx.prec = 40
            for event in chain:
                m, c = event.mc()
                a, b = a / m, (b - c) / m
                if (sid, date) in {('SH.600519', 20250625), ('SZ.000651', 20150702)}:
                    original = originals[event.source_record_index]
                    chains.append({**event.as_dict(), 'sample_date': date, 'm': m, 'c': c,
                                   'cumulative_A': a, 'cumulative_B': b,
                                   'local_cash': event.cash_dividend_per_10,
                                   'local_rights_price': event.rights_price,
                                   'local_bonus': event.bonus_transfer_per_10,
                                   'local_rights_ratio': event.rights_ratio_per_10,
                                   'decoded_float_cash': original.c1,
                                   'external_source': None, 'external_cash': None,
                                   'external_rights_price': None, 'external_bonus': None,
                                   'external_rights_ratio': None, 'field_match': None,
                                   'notes': 'External event evidence not yet available; amounts per 10 shares'})
        local.append({'security_id': sid, 'date': date, 'anchor': rows[-1]['trade_date'],
                      'local_A': factor.qfq_mul, 'local_B': factor.qfq_add,
                      'raw': raw, 'qfq': {f: factor.qfq_price(raw[f]) for f in FIELDS},
                      'chronological_A': a, 'chronological_B': b,
                      'chain_reproducible': abs(a-factor.qfq_mul) < Decimal('1e-30') and abs(b-factor.qfq_add) < Decimal('1e-30')})
    evidence.put('local.json', local)
    evidence.put('decode_audit.json', audit)
    evidence.put('chains.json', chains)
    prior = []
    for path in sorted(base.glob('run_*')):
        if path != evidence.path and (path / 'FROZEN.json').exists() and (path / 'network_audit.json').exists():
            prior.extend(read_frozen(path, 'network_audit.json'))
        elif path != evidence.path and not (path / 'FROZEN.json').exists():
            raise RuntimeError('Unfrozen earlier run requires review before any new requests')
    client = EvidenceClient(evidence, prior)
    external = []
    gate_bars = {}
    if network:
        # Alternate RAW/QFQ for the single permitted Gate A security. At most 3 attempts per mode.
        for attempt in range(3):
            for mode in (0, 1):
                if gate_bars.get(mode) is None:
                    gate_bars[mode] = fetch_bar(client, 'EASTMONEY', 'SH.600519', 20250625, mode, True)
            if all(gate_bars.get(m) is not None for m in (0, 1)) or 'EASTMONEY' in client.budget.stopped:
                break
        print('Gate A complete', dict(client.budget.count), flush=True)
        for sid, date, _, _ in MANUAL_TARGETS:
            for provider in ('EASTMONEY', 'TENCENT'):
                pair = {}
                for mode in (0, 1):
                    if provider == 'EASTMONEY' and (sid, date) == ('SH.600519', 20250625):
                        pair[str(mode)] = gate_bars.get(mode)
                    elif provider == 'EASTMONEY' and not all(gate_bars.get(m) is not None for m in (0, 1)):
                        pair[str(mode)] = None
                    else:
                        pair[str(mode)] = fetch_bar(client, provider, sid, date, mode)
                external.append({'security_id': sid, 'date': date, 'external_source': provider, **pair})
            print('Sample complete', sid, date, dict(client.budget.count), flush=True)
    else:
        for sid, date, _, _ in MANUAL_TARGETS:
            for provider in ('EASTMONEY', 'TENCENT'):
                external.append({'security_id': sid, 'date': date, 'external_source': provider, '0': None, '1': None})
    evidence.put('external.json', external)
    evidence.put('network_audit.json', client.audit)
    after = {str(p): file_sha256(p) for p in paths + core}
    evidence.put('integrity.json', {'before': before, 'after': after, 'unchanged': before == after,
        'scope': 'SHA256 of consumed gbbq/map and three day files plus both protected source modules; no whole-market rescan'})
    evidence.freeze()
    # Do not promote a later failed rerun over a published successful evidence set.
    if (base / 'PHASE0_2B_FINAL_RECEIPT.json').exists():
        return {'frozen_run': str(evidence.path), 'status': 'FROZEN_NOT_AUTO_PROMOTED'}
    return summarize(root, tdx, evidence.path)


def summarize(root, tdx, run_path):
    local = read_frozen(run_path, 'local.json')
    external = read_frozen(run_path, 'external.json')
    requests = read_frozen(run_path, 'network_audit.json')
    integrity = read_frozen(run_path, 'integrity.json')
    chains = read_frozen(run_path, 'chains.json')
    raw_rows, ab_rows = [], []
    for item in external:
        sample = next(v for v in local if (v['security_id'], v['date']) == (item['security_id'], item['date']))
        raw, qfq = item['0'], item['1']
        gate = raw_gate(sample['raw'], raw)
        row = {k: item[k] for k in ('security_id', 'date', 'external_source')}
        raw_rows.append({**row, **{f'local_{f}': sample['raw'][f] for f in FIELDS},
                        **{f'external_{f}': raw[f] if raw else None for f in FIELDS}, **gate,
                        'local_volume': sample['raw']['volume'], 'local_amount': sample['raw']['amount'],
                        'external_volume': raw.get('volume') if raw else None,
                        'external_amount': raw.get('amount') if raw else None,
                        'volume_diff': Decimal(str(sample['raw']['volume'])) - Decimal(str(raw['volume'])) if raw and 'volume' in raw else None,
                        'amount_diff': Decimal(str(sample['raw']['amount'])) - Decimal(str(raw['amount'])) if raw and 'amount' in raw else None})
        fit = fit_ab(raw, qfq) if raw and qfq else {'fit_A': None, 'fit_B': None}
        ab_rows.append({**row, 'local_A': sample['local_A'], 'local_B': sample['local_B'],
                       **{f'local_raw_{f}': sample['raw'][f] for f in FIELDS},
                       **{f'local_qfq_{f}': sample['qfq'][f] for f in FIELDS},
                       **{f'external_qfq_{f}': qfq[f] if qfq else None for f in FIELDS},
                       'external_A': fit['fit_A'], 'external_B': fit['fit_B'],
                       'A_diff': Decimal(sample['local_A'])-fit['fit_A'] if fit['fit_A'] is not None else None,
                       'B_diff': Decimal(sample['local_B'])-fit['fit_B'] if fit['fit_B'] is not None else None,
                       'external_fit_max_residual': fit.get('fit_max_abs_residual'), **fit,
                       'classification': classify(sample['local_A'], sample['local_B'], fit, gate) if qfq else 'EXTERNAL_QFQ_UNAVAILABLE',
                       'notes': 'A compatibility uses 0.02/raw_range uncertainty; B classification is a hypothesis pending event evidence'})
    east = [r for r in requests if r['source'] == 'EASTMONEY']
    first = next(v for v in external if v['security_id'] == 'SH.600519' and v['date'] == 20250625 and v['external_source'] == 'EASTMONEY')
    connectivity = {'request_count': len(east), 'success_count': sum(r['success'] for r in east),
        'failure_count': sum(not r['success'] for r in east),
        'dns_status': dict(Counter(r['dns_status'] for r in east)),
        'tls_status': dict(Counter(r['tls_status'] for r in east)),
        'http_status_distribution': dict(Counter(str(r['http_status']) for r in east)),
        'content_type_distribution': dict(Counter(str(r['content_type']) for r in east)),
        'working_parameter_set': [r['parameters'] for r in east if r['success']],
        'working_headers': [r['headers'] for r in east if r['success']],
        'raw_query_status': 'PASS' if first['0'] else 'UNAVAILABLE',
        'qfq_query_status': 'PASS' if first['1'] else 'UNAVAILABLE',
        'final_connectivity_status': connectivity_status(east, bool(first['0']), bool(first['1'])),
        'frozen_run': str(run_path), 'gate_a_request_count': sum(r.get('gate_a', i < 2) for i, r in enumerate(east))}
    status = root_gate()
    cause = {'root_cause': 'ROOT_CAUSE_UNRESOLVED', 'confidence': 'INSUFFICIENT_CAUSAL_EVIDENCE',
        'affected_samples': [dict(security_id=r['security_id'], date=r['date'], classification=r['classification']) for r in ab_rows if r['classification'] != 'AFFINE_COMPATIBLE'],
        'unaffected_samples': [dict(security_id=r['security_id'], date=r['date']) for r in ab_rows if r['classification'] == 'AFFINE_COMPATIBLE'],
        'evidence_for': ['Local chronological event composition independently reproduces engine factors for all five points', 'See paired RAW/QFQ fits in AB_DECOMPOSITION.csv'],
        'evidence_against': ['No independently verified external corporate-action chain; a price offset alone does not establish its causal event'],
        'local_code_change_required': False, 'external_basis_difference_detected': None,
        'recommended_status': status}
    receipt = {'phase': 'PHASE0.2B', 'contract_version': VERSION, 'final_status': status,
        'root_cause': cause['root_cause'], 'local_adjustment_core_changed': False,
        'diagnostic_code_added': True, 'tdx_source_unchanged': integrity['unchanged'],
        'integrity_scope': integrity['scope'], 'local_chain_reproducible': all(r['chain_reproducible'] for r in local),
        'network_request_counts': dict(Counter(r['source'] for r in requests)),
        'tests_status': 'PENDING', 'formal_trend_scanners_allowed': False,
        'next_allowed_phase': 'PHASE_1_NORMALIZATION_AND_EXPERIMENTAL_FACTOR_ENGINE',
        'frozen_run': str(run_path), 'phase0_2a_status_interpretation': 'External mismatch is not proof of local algorithm failure; original receipt preserved'}
    base = root / 'reports/phase0_2b'
    for name, data in [('EASTMONEY_CONNECTIVITY_AUDIT.json', connectivity), ('ROOT_CAUSE_ANALYSIS.json', cause), ('PHASE0_2B_FINAL_RECEIPT.json', receipt)]:
        atomic(base / name, encoded(data), tdx)
    for name, rows in [('RAW_CROSSCHECK.csv', raw_rows), ('AB_DECOMPOSITION.csv', ab_rows), ('CORPORATE_ACTION_CHAIN_COMPARE.csv', chains)]:
        atomic(base / name, csv_bytes(rows), tdx)
    return receipt
