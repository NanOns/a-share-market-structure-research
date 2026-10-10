"""Read-only bounded production token replay; never stops or starts the server."""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode
import hashlib, json, os, sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from workbench_analysis.operational_daily_storage_v1 import atomic_json

ROUTES = ('home', 'stocks', 'sectors', 'focus', 'market', 'diagnostics/sources',
          'forward/statistics', 'forward/settlement', 'forward/fep')

def read(route, query=None):
    url = 'http://127.0.0.1:28765/api/v4/' + route
    if query is not None:
        url += '?' + urlencode(query)
    request = Request(url, headers={'Accept': 'application/json'})
    try:
        response = urlopen(request, timeout=45)
    except HTTPError as exc:
        response = exc
    with response:
        raw = response.read()
        return dict(url=url, request_headers=dict(request.header_items()),
                    http_status=response.code, response_headers=dict(response.headers),
                    response_body=raw.decode('utf-8'), bytes=len(raw),
                    sha256=hashlib.sha256(raw).hexdigest())

def main():
    for key in ('TMP', 'TEMP', 'TMPDIR'):
        os.environ[key] = 'G:/codex_tmp'
    evidence = ROOT / 'docs/evidence/v4_r4_post_audit_repair_20261010/01_E_RUNTIME'
    context = read('context')
    body = json.loads(context['response_body'])
    token = body['context_token']
    records = []
    for route in ROUTES:
        for mode, value in [('empty', ''), ('exact_current', token),
                            ('expired', '38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40')]:
            record = read(route, {'context_token': value})
            record.update(route=route, token_mode=mode, context_token=value,
                          expected_http=200 if mode == 'exact_current' else 409)
            record['expected_matches_actual'] = record['http_status'] == record['expected_http']
            records.append(record)
    atomic_json(ROOT, evidence / 'E_409_ROOT_CAUSE_AND_REPLAY.json', dict(
        contract_id='R4_POST_AUDIT_PRODUCTION_TOKEN_REPLAY_V1',
        captured_at=datetime.now(timezone.utc).isoformat(), context_first_response=context,
        scope='ACTUAL_28765_OLD_PROCESS_READ_ONLY', records=records,
        root_cause='EXPLICIT_EMPTY_OR_STALE_TOKEN_REJECTED; exact current token replay recorded per route; previous request URLs were not retained, so original caller token cannot be proven'))
    atomic_json(ROOT, evidence / 'E_LIVE_28765_API_FIELD_SAMPLES.json', dict(
        scope='ACTUAL_28765_OLD_PROCESS_NOT_NEW_CODE', context=body,
        records=[dict(route=r['route'], url=r['url'], http_status=r['http_status'],
                      payload=json.loads(r['response_body']))
                 for r in records if r['token_mode'] == 'exact_current']))
    print(json.dumps([dict(route=r['route'], mode=r['token_mode'], actual=r['http_status'],
                           matched=r['expected_matches_actual']) for r in records]))

if __name__ == '__main__':
    main()
