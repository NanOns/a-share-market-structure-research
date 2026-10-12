"""Bounded six-entry/HTTP/capacity measurements; errors never count as fast success."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import threading
import time
import urllib.error
import urllib.request


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--pid', type=int, required=True)
    p.add_argument('--timeout', type=float, default=15)
    p.add_argument('--rounds', type=int, default=1)
    a = p.parse_args()
    out = Path(a.out).resolve()
    if out.drive.upper() != 'G:': raise SystemExit('G_STORAGE_REQUIRED')
    out.mkdir(parents=True, exist_ok=True)
    import psutil
    process = psutil.Process(a.pid)
    records, samples = [], []
    accepted_context = {}
    running = threading.Event(); running.set()
    def monitor():
        while running.is_set():
            try: samples.append(dict(time=time.time(), rss=process.memory_info().rss, cpu_seconds=sum(process.cpu_times()[:2])))
            except psutil.Error: break
            running.wait(.25) if not running.is_set() else time.sleep(.25)
    thread = threading.Thread(target=monitor, daemon=True); thread.start()
    def request(route):
        requested_route = route
        if route.startswith('/api/v4/') and not route.startswith('/api/v4/context') and accepted_context:
            from urllib.parse import urlencode
            route += ('&' if '?' in route else '?') + urlencode(dict(context_token=accepted_context['context_token'], trade_date=accepted_context['context']['trade_date']))
        start = time.perf_counter(); raw = b''; code = None; error = None
        try:
            with urllib.request.urlopen(a.base + route, timeout=a.timeout) as response:
                code = response.status; raw = response.read()
        except urllib.error.HTTPError as exc: code = exc.code; raw = exc.read(); error = str(exc)
        except (OSError, TimeoutError) as exc: error = type(exc).__name__ + ': ' + str(exc)
        item = dict(route=route, requested_route=requested_route, http=code, seconds=time.perf_counter()-start, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), error=error)
        if raw:
            sha = item['sha256']; (out / (sha + '.response')).write_bytes(raw)
            try:
                data = json.loads(raw)
                item.update(status=data.get('status'), reason=data.get('reason') or data.get('code'), context_token=data.get('context_token'), context=data.get('context'), total=data.get('total'))
                if requested_route == '/api/v4/context' and code == 200:
                    accepted_context.update(data)
            except (ValueError, AttributeError): pass
        records.append(item); return item
    routes = ['/v4/research/'+x for x in ('home','sectors','stocks','focus','market','diagnostics')]
    routes += ['/v4/assets/'+x for x in ('app.js','api.js','components.js','style.css')]
    routes += ['/api/v4/'+x for x in ('context','home','stocks?limit=30','sectors?limit=30','focus?limit=30','market','diagnostics')]
    for route in routes: request(route)
    groups = []
    for concurrency in (1,4,8):
        for route in ('/api/v4/home','/api/v4/stocks?limit=30','/api/v4/focus?limit=30','/api/v4/replay?as_of=2026-10-09'):
            start = time.perf_counter()
            with ThreadPoolExecutor(max_workers=concurrency) as pool: rows = list(pool.map(request, [route]*concurrency*max(1,a.rounds)))
            elapsed = time.perf_counter()-start
            values = sorted(r['seconds'] for r in rows if r['http']==200 and not r['error'])
            def percentile(frac): return values[min(len(values)-1, int((len(values)-1)*frac))] if values else None
            groups.append(dict(concurrency=concurrency, route=route, requests=len(rows), errors=sum(r['http']!=200 or bool(r['error']) for r in rows), error_rate=sum(r['http']!=200 or bool(r['error']) for r in rows)/len(rows), success_p50_seconds=percentile(.5), success_p95_seconds=percentile(.95), success_p99_seconds=percentile(.99), throughput_success=sum(r['http']==200 and not r['error'] for r in rows)/elapsed, elapsed_seconds=elapsed, rounds=max(1,a.rounds), percentile_limit='BOUNDED_BATCH; NO_STEADY_STATE_OR_LONG_DURATION_CLAIM'))
    running.clear(); thread.join(timeout=1)
    result = dict(contract='V4_CLOSEOUT_BOUNDED_HTTP_CAPACITY_DIAGNOSTIC_V1', observed_at=datetime.now(timezone.utc).isoformat(), base=a.base,pid=a.pid,platform=platform.platform(), logical_cpus=psutil.cpu_count(),physical_cpus=psutil.cpu_count(logical=False),ram_bytes=psutil.virtual_memory().total,records=records,capacity=groups,process_samples=samples,peak_rss_bytes=max((s['rss'] for s in samples),default=None), acceptance='FAIL' if any(r['http']!=200 for r in records) else 'HTTP_ONLY_PASS_UI_AND_PRODUCERS_NOT_ACCEPTED', production_budget=dict(status='PROPOSED_NOT_PREVIOUSLY_APPROVED', errors=0, hot_interactive_p95_seconds=2, cold_interactive_p95_seconds=10, peak_rss_bytes=3*1024**3, rationale='Local single-user research UI must respond before retry; full integrity remains enabled'), limitations=['Frozen runtime diagnosis only','No chart source identity acceptance','No PG SQL timings captured by this script','UI DOM requires actual browser evidence','No Windows packaged default startup acceptance'])
    (out/'HTTP_CAPACITY.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(result=result['acceptance'],requests=len(records),errors=sum(r['http']!=200 for r in records),peak_rss_bytes=result['peak_rss_bytes'])))


if __name__ == '__main__': main()
