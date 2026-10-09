"""Read real frozen objects; separate arithmetic from production calculators.

Engineering verification only: cannot grant external acceptance or publication.
"""
import csv
import gzip
import hashlib
import io
import json
import struct
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from workbench_analysis.tdx_official_daily_source import _atomic_write

OUT = ROOT / 'docs/evidence/r4_1_audit_repair_r1_20261009'


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def bound(binding):
    p = (ROOT / binding['path']).resolve()
    p.relative_to(ROOT)
    if sha(p) != binding['sha256'] or ('bytes' in binding and p.stat().st_size != binding['bytes']):
        raise ValueError('OBJECT_BINDING_FAILED:' + binding['path'])
    return p


def rows(path):
    with gzip.open(path, 'rt', encoding='utf8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def write(name, value):
    _atomic_write(OUT / name, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode(),
                  tdx_root=Path('D:/new_tdx'))


def main():
    protected = {p: sha(ROOT / p) for p in ('config/v4_joint_release_authority_v1.json',
                 'data/v4/V4_DATA_ACCEPTED_HEAD.json')}
    replay = read(ROOT / 'docs/evidence/source_acquisition_r4_20261009/owner_repair_v1/CORE_REPLAY.json')
    owners = replay['owners']; dates = [o['trade_date'] for o in owners]
    package = bound(owners[0]['sources']['package'])
    facts_path = ROOT / 'reports/v4_01/baostock_lifecycle_facts_R4_20260925.json'
    facts = defaultdict(list)
    for f in read(facts_path)['facts']:
        facts[f['source_security_key'].lower()].append(f)
    bse_path = ROOT / 'reports/v4_01/bse_source_closure_receipt_R5_20260925.json'
    bse = defaultdict(list)
    for r in read(bse_path)['records']:
        bse[r['source_security_key'].lower()].append(r)
    identity = read(bound(owners[0]['sources']['identity']))['rows']
    identities = {r['source_security_key'].lower(): r for r in identity}
    official = {}; inventories = Counter()
    with zipfile.ZipFile(package) as z:
        bad = z.testzip()
        if bad:
            raise ValueError('ZIP_CRC_FAILED:' + bad)
        for name in z.namelist():
            parts = name.lower().replace('\\', '/').split('/'); leaf = parts[-1]
            market = next((p for p in parts if p in ('sh', 'sz', 'bj')), None)
            if not market or not leaf.endswith('.day'):
                continue
            code = market + '.' + leaf[-10:-4]
            data = z.read(name)
            if len(data) % 32:
                raise ValueError('DAY_RECORD_LENGTH:' + name)
            for bar in struct.iter_unpack('<IIIIIfII', data):
                s = str(bar[0]); day = s[:4] + '-' + s[4:6] + '-' + s[6:]
                if day in dates:
                    if (day, code) in official:
                        raise ValueError('DUPLICATE_OFFICIAL_KEY:' + code)
                    official[day, code] = bar
                    inventories[day] += 1
    print('Actual ZIP SHA/size/CRC and records verified', flush=True)
    unbound = []; invalid_entries = []
    from workbench_analysis.tdx_snapshot_delta import _records, TDXDeltaError
    with zipfile.ZipFile(package) as z:
        for name in z.namelist():
            if not name.lower().endswith('.day'):
                continue
            try:
                _records(z.read(name))
            except TDXDeltaError as error:
                invalid_entries.append(dict(path=name, reason=str(error)))
    write('OFFICIAL_PACKAGE_STRICT_DELTA_BLOCKERS.json', dict(entries=invalid_entries,
        status='BLOCKED_STRICT_DELTA_VALIDATION' if invalid_entries else 'PASS',
        policy='NO_INVALID_ENTRY_SILENTLY_DROPPED; VERSIONED_SCOPED_SUCCESSOR_REQUIRED'))
    # Classify evidence, never invent canonical IDs from code prefixes.
    stock_scope = lambda c: (c.startswith(('sh.600', 'sh.601', 'sh.603', 'sh.605', 'sh.688',
        'sh.689', 'sz.000', 'sz.001', 'sz.002', 'sz.003', 'sz.300', 'sz.301', 'bj.')))
    for (day, code), bar in sorted(official.items()):
        if code in identities or not stock_scope(code):
            continue
        fs = facts.get(code, [])
        if code in ('bj.899050', 'bj.899601'):
            category = 'INDEX_EXCLUDED'
        elif len(fs) > 1:
            category = 'MULTIPLE_LIFECYCLES_REQUIRES_ALIAS_REVIEW'
        elif fs:
            f = fs[0]; start = f.get('listed_from'); end = f.get('listed_to_provider_reported')
            category = ('PROVIDER_NON_STOCK' if f.get('security_type_provider') != '1' else
                        'PRE_LISTING_BAR_CONFLICT' if start and day < start else
                        'POST_DELIST_BAR_REQUIRES_REVIEW' if end and day > end else
                        'PROVIDER_STOCK_INTERVAL_CANDIDATE_CANONICAL_UNBOUND')
        else:
            candidates = bse.get(code, [])
            valid_candidates = [r for r in candidates if r.get('symbol_effective_from') and
                r['symbol_effective_from'] <= day and (not r.get('symbol_effective_to') or day <= r['symbol_effective_to'])]
            category = ('BSE_STABLE_ENTITY_CANDIDATE_NOT_ACCEPTED' if any(r.get('disposition') == 'MAPPED_STABLE_BSE_ENTITY' for r in valid_candidates) else
                        'BSE_ALIAS_OUTSIDE_EFFECTIVE_INTERVAL' if candidates and not valid_candidates and
                        all(r.get('symbol_effective_from') for r in candidates) else
                        'BSE_EXPLICIT_UNRESOLVED_SOURCE' if candidates else
                        'BSE_LIFECYCLE_SOURCE_REQUIRED' if code.startswith('bj.') else 'LIFECYCLE_FACT_MISSING')
        unbound.append(dict(trade_date=day, source_security_key=code, classification=category,
            lifecycle_facts=fs, security_id=None, accepted=False,
            bse_candidates=bse.get(code, []), bse_candidate_source_sha256=sha(bse_path),
            source_sha256=sha(facts_path), historical_first_available='UNKNOWN'))
    write('UNBOUND_IDENTITY_CLASSIFICATION.json', dict(rows=unbound,
          counts={d: dict(Counter(r['classification'] for r in unbound if r['trade_date'] == d)) for d in dates},
          contract='SECURITY_ENTITY_IDENTITY_V1 + SECURITY_LIFECYCLE_HISTORY_V1',
          status='CLASSIFIED_OBSERVATIONS_NOT_CANONICAL_ADMISSION'))
    numeric = []; errors = []; samples = []; sample_categories = Counter()
    for owner in owners:
        day = owner['trade_date']
        current = {r['security_id']: r for r in rows(bound(owner['core']))}
        prior = {r['security_id']: r for r in rows(bound(owner['prior_core']))}
        raw = {r['security_id']: r for r in rows(bound(owner['raw']))}
        checks = Counter()
        for history in rows(bound(owner['history'])):
            sid = history['security_id']; code = current[sid]['source_security_key'].lower()
            bars = history['bars']
            category = ('SUSPENDED_NO_CURRENT_BAR' if sid not in raw else
                        'SHORT_OR_UNKNOWN_WINDOW' if current[sid]['fields']['atr20']['value'] is None else
                        'ADJUSTED_WINDOW' if any(b['qfq_ohlc'] and b['qfq_ohlc'] != b['raw_ohlc'] for b in bars[-75:]) else
                        'NORMAL_WINDOW')
            sample_key = day + ':' + category
            take_sample = sample_categories[sample_key] < 10
            pair = []
            if sid in raw:
                b = official[day, code]; r = raw[sid]
                expected = [v / 100 for v in b[1:5]] + [b[5], b[6]]
                actual = [r[k] for k in ('open', 'high', 'low', 'close', 'amount', 'volume')]
                checks['raw_ohlcva'] += 6
                if expected != actual:
                    errors.append(dict(day=day, sid=sid, error='RAW_OHLCVA'))
            for endpoint, row in (('current', current[sid]), ('prior', prior[sid])):
                for field in ('ma20', 'atr20'):
                    cell = row['fields'].get(field, {})
                    if cell.get('value') is None:
                        checks[endpoint + '_' + field + '_unknown'] += 1
                        if take_sample:
                            pair.append(dict(endpoint=endpoint, field=field, value=None, reason=cell.get('unknown_reason')))
                        continue
                    bs = [b for b in history['bars'] if cell['window_start_trade_date'] <= b['trade_date'] <= cell['window_end_trade_date']]
                    prices = [b['qfq_ohlc'] for b in bs]
                    need = 20 if field == 'ma20' else 21
                    valid = len(prices) == need and all(p is not None for p in prices)
                    value = None
                    if valid:
                        value = (sum(p[3] for p in prices) / 20 if field == 'ma20' else
                                 sum(max(b[1]-b[2], abs(b[1]-a[3]), abs(b[2]-a[3]))
                                     for a, b in zip(prices, prices[1:])) / 20)
                    checks[endpoint + '_' + field] += 1
                    if not valid or abs(value - cell['value']) > 1e-9:
                        errors.append(dict(day=day, sid=sid, endpoint=endpoint, field=field,
                                           expected=value, actual=cell['value']))
                    if endpoint == 'prior' and row.get('price_basis_id') != current[sid]['price_basis_id']:
                        errors.append(dict(day=day, sid=sid, error='PRIOR_COORDINATE_MIX'))
                    if take_sample:
                        pair.append(dict(day=day, sid=sid, endpoint=endpoint, field=field,
                            start=cell['window_start_trade_date'], end=cell['window_end_trade_date'],
                            expected=value, actual=cell['value'], window=bs))
            if take_sample:
                samples.append(dict(day=day, security_id=sid, code=code, category=category, pair=pair))
                sample_categories[sample_key] += 1
        numeric.append(dict(trade_date=day, checks=dict(checks)))
        print(json.dumps(numeric[-1]), flush=True)
    write('NUMERIC_SAMPLES.json', samples)
    from workbench_service.current_v4_context import CurrentAcceptedV4Reader
    context = CurrentAcceptedV4Reader(ROOT).load_context()
    preserved = {p: sha(ROOT / p) == h for p, h in protected.items()}
    if not all(preserved.values()):
        errors.append('PRODUCTION_POINTER_CHANGED')
    result = dict(contract='R4_1_AUDIT_R1_BYTES_NUMERIC_V1', observed_at=datetime.now(timezone.utc).isoformat(),
        head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        execution_scope='LOCAL_ENGINEERING_REEXECUTION_NOT_EXTERNAL_ACCEPTANCE',
        package=owners[0]['sources']['package'], zip_crc='PASS', official_all_instrument_bars=dict(inventories),
        numeric=numeric, errors=errors, protected=preserved, live_context=context,
        paired_sample_categories=dict(sample_categories), strict_delta_invalid_entries=len(invalid_entries),
        acceptance='PASS_SCOPED_LOCAL_BYTES_AND_WINDOW_ARITHMETIC' if not errors else 'FAIL',
        limitation='MA/ATR independently recomputed from hash-verified corrected OHLC; event semantics and full adjustment oracle remain external review objects',
        production='BLOCKED_SCOPED_EXTERNAL_OWNER_ADMISSION', source_requests_this_run=0,
        next_stage='EXTERNAL_SOURCE_IDENTITY_COORDINATE_AND_OWNER_ADMISSION')
    write('BYTE_NUMERIC_READBACK.json', result)
    return 2 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
