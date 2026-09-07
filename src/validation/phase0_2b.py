"""Versioned, validation-only Phase 0.2B diagnostics. No production writes."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import socket
import ssl
import tempfile
import urllib.error
import urllib.parse
import urllib.request

VERSION = 'raw-ab-diagnosis-v1'
FIELDS = ('open', 'high', 'low', 'close')


def atomic(path, data, forbidden):
    path, forbidden = Path(path).resolve(), Path(forbidden).resolve()
    if path == forbidden or forbidden in path.parents:
        raise ValueError('TDX source is read only')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.phase0_2b_')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2, default=str).encode('utf-8')


class FrozenRun:
    def __init__(self, base, forbidden):
        self.forbidden = Path(forbidden).resolve()
        base = Path(base).resolve()
        if base == self.forbidden or self.forbidden in base.parents:
            raise ValueError('TDX source is read only')
        base.mkdir(parents=True, exist_ok=True)
        for index in range(1, 100000):
            self.path = base / f'run_{index:03d}'
            try:
                self.path.mkdir()
                break
            except FileExistsError:
                continue
        else:
            raise RuntimeError('run ids exhausted')

    def put(self, name, value):
        target = (self.path / name).resolve()
        if target.parent != self.path or target.exists() or (self.path / 'FROZEN.json').exists():
            raise FileExistsError(name)
        # Exclusive claim also protects concurrent writers; the completed file is atomic.
        claim = self.path / (name + '.lock')
        with claim.open('x'):
            atomic(target, encoded(value), self.forbidden)
        claim.unlink()

    def freeze(self):
        manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.path.iterdir() if p.is_file()}
        self.put('FROZEN.json', manifest)


def read_frozen(path, name):
    path = Path(path)
    manifest = json.loads((path / 'FROZEN.json').read_text('utf-8'))
    payload = (path / name).read_bytes()
    if hashlib.sha256(payload).hexdigest() != manifest[name]:
        raise ValueError('frozen evidence hash mismatch')
    return json.loads(payload)


def fit_ab(raw, qfq):
    x = [Decimal(str(raw[f])) for f in FIELDS]
    y = [Decimal(str(qfq[f])) for f in FIELDS]
    if not all(v.is_finite() for v in x + y):
        raise ValueError('nonfinite OHLC')
    xm, ym = sum(x) / 4, sum(y) / 4
    denominator = sum((v - xm) ** 2 for v in x)
    if not denominator:
        return {'status': 'UNIDENTIFIABLE_CONSTANT_RAW', 'fit_A': None, 'fit_B': None}
    a = sum((u - xm) * (v - ym) for u, v in zip(x, y)) / denominator
    b = ym - a * xm
    residuals = {f'fit_residual_{f}': v - (a * u + b) for f, u, v in zip(FIELDS, x, y)}
    # Price-output uncertainty of <=0.01 per endpoint; narrow ranges cannot identify A tightly.
    return {'status': 'FIT', 'fit_A': a, 'fit_B': b, **residuals,
            'fit_max_abs_residual': max(abs(v) for v in residuals.values()),
            'A_resolution_bound': Decimal('0.02') / (max(x) - min(x))}


def raw_gate(local, external):
    if external is None:
        return {'raw_match': None, 'max_abs_diff': None, 'status': 'RAW_UNAVAILABLE'}
    diffs = {f'diff_{f}': Decimal(str(local[f])) - Decimal(str(external[f])) for f in FIELDS}
    maximum = max(abs(v) for v in diffs.values())
    return {**diffs, 'raw_match': maximum == 0, 'max_abs_diff': maximum,
            'status': 'RAW_MATCH' if maximum == 0 else 'RAW_BASIS_DIFFERENCE'}


def classify(local_a, local_b, fit, gate):
    if gate['raw_match'] is not True:
        return gate['status']
    if fit.get('fit_A') is None:
        return 'AB_UNIDENTIFIABLE'
    if fit['fit_max_abs_residual'] > Decimal('0.01'):
        return 'EXTERNAL_NON_AFFINE_OR_DATA_INCONSISTENT'
    if abs(Decimal(str(local_a)) - fit['fit_A']) > fit['A_resolution_bound']:
        return 'MULTIPLICATIVE_EVENT_CHAIN_DIFFERENCE'
    # A-compatible is not proof of equal slopes; intercept alone is unstable for narrow ranges.
    if abs(Decimal(str(local_b)) - fit['fit_B']) > Decimal('0.01'):
        return 'BASIS_DIFFERENCE_IN_CASH_ADJUSTMENT_CHAIN'
    return 'AFFINE_COMPATIBLE'


def root_gate(local_bug=False, fixed=False, provider_evidence=False):
    if local_bug:
        return 'LOCAL_ALGORITHM_BUG_FOUND_AND_FIXED' if fixed else 'LOCAL_ALGORITHM_BUG_UNRESOLVED'
    if provider_evidence:
        return 'EXTERNAL_PROVIDER_BASIS_DIFFERENCE'
    return 'EXTERNAL_SOURCE_INCONCLUSIVE'


class Budget:
    def __init__(self):
        self.count = Counter()
        self.failures = Counter()
        self.stopped = set()
        self.gate_a_count = 0

    def take(self, source, gate_a=False):
        limit = {'EASTMONEY': 30, 'TENCENT': 30, 'OTHER': 20}[source]
        if source in self.stopped or self.count[source] >= limit or sum(self.count.values()) >= 80:
            return False
        if gate_a and self.gate_a_count >= 12:
            return False
        self.count[source] += 1
        self.gate_a_count += int(gate_a)
        return True

    def result(self, source, success, status=None):
        self.failures[source] = 0 if success else self.failures[source] + 1
        if self.failures[source] >= 3 or status in {400, 401, 403, 404, 429, 501}:
            self.stopped.add(source)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Every HTTP request must consume budget.


class EvidenceClient:
    def __init__(self, run, prior_records=()):
        self.run, self.budget, self.audit = run, Budget(), []
        self.opener = urllib.request.build_opener(NoRedirect)
        for record in prior_records:
            if not self.budget.take(record['source'], record.get('gate_a', False)):
                raise ValueError('prior evidence already exceeds budget or circuit')
            self.budget.result(record['source'], record['success'], record['http_status'])

    def get(self, source, endpoint, params, *, gate_a=False, headers=None, validator=None):
        if not self.budget.take(source, gate_a):
            return None
        headers = headers or {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/',
                              'Accept': 'application/json,text/plain,*/*'}
        url = endpoint + '?' + urllib.parse.urlencode(params)
        record = {'source': source, 'url': url, 'parameters': params, 'headers': headers, 'gate_a': gate_a,
                  'requested_at': datetime.now(timezone.utc).isoformat(),
                  'dns_status': 'NOT_TESTED', 'tls_status': 'NOT_OBSERVED', 'http_status': None,
                  'content_type': None, 'body_prefix': None, 'json_parse_status': 'NOT_ATTEMPTED',
                  'api_code': None, 'api_msg': None, 'success': False}
        payload = None
        try:
            host = urllib.parse.urlparse(endpoint).hostname
            record['dns_addresses'] = sorted({a[4][0] for a in socket.getaddrinfo(host, 443)})
            record['dns_status'] = 'PASS'
            try:
                response = self.opener.open(urllib.request.Request(url, headers=headers), timeout=12)
            except urllib.error.HTTPError as exc:
                response = exc
            with response:
                record['http_status'] = response.code
                record['tls_status'] = 'PASS_HTTPS_RESPONSE'
                record['content_type'] = response.headers.get('Content-Type')
                body = response.read(2000000).decode('utf-8', errors='replace')
                record['body_prefix'] = body[:500]
                record['body'] = body
            try:
                payload = json.loads(body)
                record['json_parse_status'] = 'PASS'
                if not isinstance(payload, dict):
                    raise ValueError('expected JSON object')
                record['api_code'] = payload.get('rc', payload.get('code'))
                record['api_msg'] = payload.get('msg', payload.get('message'))
                record['success'] = record['http_status'] == 200 and record['api_code'] == 0 and bool(payload.get('data') or payload.get('result'))
                if record['success'] and validator is not None:
                    record['schema_status'] = 'PASS' if validator(payload) else 'FAIL_OR_TARGET_MISSING'
                    record['success'] = record['schema_status'] == 'PASS'
            except (ValueError, TypeError) as exc:
                record['json_parse_status'] = 'FAIL'
                record['error'] = str(exc)
        except Exception as exc:
            record['error'] = f'{type(exc).__name__}: {exc}'
            if isinstance(exc, socket.gaierror):
                record['dns_status'] = 'FAIL'
            if isinstance(exc, ssl.SSLError) or isinstance(getattr(exc, 'reason', None), ssl.SSLError):
                record['tls_status'] = 'FAIL'
        self.budget.result(source, record['success'], record['http_status'])
        self.audit.append(record)
        self.run.put(f'request_{len(self.audit):03d}.json', record)
        return payload if record['success'] else None


def connectivity_status(records, raw_ok, qfq_ok):
    if raw_ok and qfq_ok:
        return 'EASTMONEY_OK'
    if any(r['http_status'] in {401, 403, 404, 429, 501} or (r['http_status'] or 0) >= 500 for r in records):
        return 'EASTMONEY_HTTP_BLOCKED'
    if any(r['http_status'] == 400 or r.get('api_code') not in (None, 0) for r in records):
        return 'EASTMONEY_PARAM_ERROR'
    if any(r['http_status'] == 200 for r in records):
        return 'EASTMONEY_RESPONSE_SCHEMA_CHANGED'
    if records and all(r['http_status'] is None for r in records):
        return 'EASTMONEY_ENV_NETWORK_BLOCKED'
    return 'EASTMONEY_UNKNOWN_FAILURE'
