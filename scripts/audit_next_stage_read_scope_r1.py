"""Bounded current-service read QA. No scheduler, service reload or source write."""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from workbench_analysis.v4_14_replay_io import publish, ref

OUT = 'docs/evidence/next_stage_after_audit_r1_20261010'
BASE = 'http://127.0.0.1:28765'
HEADS = ('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json', 'data/v4/V4_DATA_ACCEPTED_HEAD.json')


def main():
    for name in ('TMP', 'TEMP', 'TMPDIR'):
        os.environ[name] = 'G:/codex_tmp'
    receipts, failures = [], []
    before = {p: ref(ROOT, p) for p in HEADS}
    token = None

    def get(path, params=None, expected=200):
        url = BASE + path + ('?' + urllib.parse.urlencode(params) if params else '')
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(url, timeout=25) as response:
                code, raw = response.status, response.read()
        except urllib.error.HTTPError as error:
            code, raw = error.code, error.read()
        except (OSError, TimeoutError) as error:
            receipts.append(dict(url=url, status='TRANSPORT_FAILURE', error=str(error)))
            failures.append(dict(url=url, reason='TRANSPORT_FAILURE'))
            return {}
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError):
            data = {}
        statuses = {}
        def cells(value):
            if isinstance(value, dict):
                if 'quality' in value:
                    quality = str(value['quality'])
                    statuses[quality] = statuses.get(quality, 0) + 1
                for k, v in value.items():
                    if k not in ('context', 'source', 'sources', 'source_publications'):
                        cells(v)
            elif isinstance(value, list):
                for v in value:
                    cells(v)
        cells(data)
        receipts.append(dict(url=url, status=code, expected=expected, passed=code == expected,
            bytes=len(raw), raw_sha256=hashlib.sha256(raw).hexdigest(),
            elapsed_ms=round((time.perf_counter()-start)*1000, 2),
            business_status=data.get('status'), reason=data.get('reason'),
            total=data.get('total'), field_qualities=statuses,
            gaps=data.get('gaps', data.get('gap')), source=data.get('source'),
            context_token=data.get('context_token'),
            source_incomplete_does_not_mean_http_failure=data.get('status') == 'SOURCE_INCOMPLETE'))
        if code != expected:
            failures.append(dict(url=url, reason='HTTP_STATUS', actual=code, expected=expected))
        if code == 200 and path.startswith('/api/v4/') and token and data.get('context_token') not in (None, token):
            failures.append(dict(url=url, reason='TOKEN_MISMATCH'))
        return data

    context = get('/api/v4/context')
    token = context['context_token']
    day = context['context']['trade_date']
    q = dict(context_token=token, trade_date=day, limit=3)
    stocks = get('/api/v4/stocks', q)
    sectors = get('/api/v4/sectors', q)
    focus = get('/api/v4/focus', q)
    sid, sector, fid = [rows['items'][0]['entity_id'] for rows in (stocks, sectors, focus)]
    for route in ('home', 'market', 'market/breadth', 'market/indices', 'market/limits',
                  'market/ladders', 'events', 'focus/events', 'forward', 'forward/statistics',
                  'forward/plans', 'forward/fep', 'forward/settlement', 'sources',
                  'diagnostics/health', 'diagnostics/sources', 'diagnostics/contracts',
                  'diagnostics/jobs', 'diagnostics/legacy', 'diagnostics/shadow', 'diagnostics/fep'):
        get('/api/v4/' + route, q)
    details = [('stocks/' + sid, ('', '/profile', '/timeline', '/why-not')),
               ('sectors/' + sector, ('', '/members', '/timeline', '/overlap')),
               ('focus/' + fid, ('/episodes', '/timeline', '/anchors', '/observations', '/outcomes'))]
    for prefix, suffixes in details:
        for suffix in suffixes:
            get('/api/v4/' + prefix + suffix, q)
    charts = []
    for period in ('D', 'W', 'M'):
        for basis in ('RAW', 'QFQ'):
            data = get('/api/v4/stocks/' + sid + '/chart', dict(q, period=period, price_basis=basis, limit=120))
            bars = data.get('items', [])
            valid = bool(bars) and all(r['trade_date'] <= day for r in bars) and all(
                isinstance(r.get('close'), (int, float)) for r in bars if r.get('quality') == 'KNOWN')
            charts.append(dict(period=period, basis=basis, bars=len(bars), passed=valid,
                as_of=data.get('as_of'), last=bars[-1] if bars else None, source=data.get('source')))
            if not valid:
                failures.append(dict(reason='CHART_FACTS', period=period, basis=basis))
    search = []
    for term in (stocks['items'][0]['symbol'].split('.')[-1], stocks['items'][0]['display_name']):
        rows = get('/api/v4/stocks', dict(q, q=term))
        found = sid in {r['entity_id'] for r in rows.get('items', [])}
        search.append(dict(term=term, found=found, entity_id=sid))
        if not found:
            failures.append(dict(reason='SEARCH', term=term))
    historical = []
    for date in ('2026-09-30', '2026-10-08'):
        data = get('/api/v4/stocks', dict(q, trade_date=date))
        bound = data.get('context', {}).get('trade_date') == date and all(r['trade_date'] == date for r in data.get('items', []))
        historical.append(dict(trade_date=date, passed=bound, total=data.get('total')))
        if not bound:
            failures.append(dict(reason='HISTORICAL_DATE_BINDING', trade_date=date))
    for route in ('replay', 'compare'):
        get('/api/v4/' + route, dict(q, as_of='2026-10-08', view='corrected', left=sid, mode='stock-market'))
    candidate = get('/api/v4/candidates/cohort', q)
    cand = candidate.get('candidate_research', {})
    if cand.get('formal_consumer_enabled') is not False or cand.get('observed_count') is not None or cand.get('matured_count') is not None:
        failures.append(dict(reason='RESEARCH_COUNT_PROMOTED_TO_FORMAL'))
    get('/api/v4/candidates/sectors/' + sector, q)
    get('/api/v4/candidates/cohort', dict(q, trade_date='2026-10-08'))
    get('/api/v4/stocks', dict(q, context_token='0'*64), expected=409)
    get('/api/v4/stocks', dict(q, trade_date='2026-10-12'), expected=400)
    get('/api/v4/candidates/cohort', dict(q, trade_date='2026-10-12'), expected=400)
    pages = []
    for route in ('home', 'stocks', 'sectors', 'focus', 'market', 'diagnostics'):
        get('/v4/research/' + route)
        pages.append(dict(route=route, live_dom='NOT_OBSERVED_BROWSER_TRANSPORT_BLOCKED'))
    assets = []
    for name in ('app.js', 'api.js', 'components.js', 'stock.js', 'replay.js', 'labels.js'):
        get('/v4/assets/' + name)
        local = ref(ROOT, 'src/workbench_service/static/core-product-r1/' + name)
        assets.append(dict(name=name, local=local, served_sha256=receipts[-1]['raw_sha256'],
            same_bytes=local['sha256'] == receipts[-1]['raw_sha256']))
    after = {p: ref(ROOT, p) for p in HEADS}
    assert before == after, 'PROTECTED_HEAD_CHANGED'
    publish(ROOT, OUT + '/D_HTTP_READBACK.json', dict(contract_id='FP13_CURRENT_RESEARCH_READ_QA_R1',
        observed_at=datetime.now(timezone.utc).isoformat(), context=context,
        receipts=receipts, charts=charts, search=search, historical=historical, assets=assets,
        pages=pages, failures=failures, selected_ids=dict(stock=sid, sector=sector, focus=fid),
        candidate_semantics=cand, production_restarted=False, independent_external_acceptance=False,
        acceptance='PASS_SCOPED_HTTP_FACTS' if not failures else 'FAIL_SCOPED_HTTP',
        browser_viewports={str(w):'BLOCKED_NO_LOCAL_BROWSER_SURFACE' for w in (1366,1920)}))
    publish(ROOT, OUT + '/PROTECTED_HEAD_READBACK.json', dict(before=before, after=after, unchanged=True))
    print(json.dumps(dict(requests=len(receipts), failures=failures, charts=len(charts), heads_unchanged=True)), flush=True)


if __name__ == '__main__':
    main()
