import json
import hashlib
import threading
import tempfile
import unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import patch

from workbench_service.core_product_bff_r1 import CoreProductBFFR1
from workbench_service.operational_successor_bff_v1 import OperationalSuccessorBFFV1
from workbench_db.v4_read_index_r2 import AUTHORITY, CONTRACT, ReadIndex, load
from workbench_service.core_product_server_r1 import make_product_handler


DAY = '2026-10-13'
TOKEN = 'a' * 64


class FakeAPI:
    def __init__(self, root):
        self.root = Path(root)
        self.token = TOKEN
        self.cache = {}
        self.candidate = dict(accepted_trade_date=DAY, published_sessions=[DAY],
            owners={DAY: {'forward': {'path': 'forward.json', 'sha256': 'b' * 64},
                          'focus': {'path': 'focus.json', 'sha256': 'c' * 64}}})


class FakeR2:
    def __init__(self, detail=None):
        self.detail_row = detail
        self.detail_calls = []
        self.page_calls = []

    def response(self, path):
        return {'context': {'trade_date': DAY}, 'context_token': TOKEN, 'production_accepted': False}

    def page(self, domain, query, **kwargs):
        self.page_calls.append((domain, dict(query)))
        return {'status': 'READY', 'items': [], 'total': 0, 'offset': 0, 'limit': 30,
                'has_next': False, 'domain': domain}

    def detail(self, domain, key):
        self.detail_calls.append((domain, key))
        return self.detail_row

    def response_and_detail(self, path, domain, key):
        return self.response(path), self.detail(domain, key)


def make_bff(root):
    bff = CoreProductBFFR1.__new__(CoreProductBFFR1)
    bff.api = FakeAPI(root)
    bff.legacy = None
    bff.isolated_history = None
    bff.building_read_index = False
    return bff


class UXR3RouteTests(unittest.TestCase):
    def setUp(self):
        Path('G:/codex_tmp/test_temp').mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir='G:/codex_tmp/test_temp')
        self.root = Path(self.temp.name)
        self.bff = make_bff(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_radar_default_and_empty_event_reach_r2_page(self):
        index = FakeR2()
        self.bff._read_index_r2 = lambda day: index
        for query in (
            {'context_token': TOKEN},
            {'context_token': TOKEN, 'event': ''},
            {'context_token': TOKEN, 'event': 'NEW'},
        ):
            code, response = self.bff.get('/api/v4/radar', query)
            self.assertEqual(code, 200)
            self.assertEqual(response['domain'], 'radar')
        self.assertEqual(len(index.page_calls), 3)
        with self.assertRaisesRegex(ValueError, 'INVALID_EVENT'):
            self.bff.get('/api/v4/radar', {'context_token': TOKEN, 'event': 'BOGUS'})

    def test_focus_events_empty_event_new_persistent_validity_and_paging(self):
        forward = {'events': [
            {'entity_id': 'SEC-1', 'event': 'NEW', 'validity': 'VALID', 'trade_date': DAY},
            {'entity_id': 'SEC-2', 'event': 'PERSISTENT', 'validity': 'UNKNOWN', 'trade_date': DAY},
        ]}
        self.bff.source = lambda domain, day: forward
        self.bff._read_index_r2 = lambda day: None
        self.bff._display_identity_map = lambda day, rows, **kwargs: {}
        self.bff.paged = lambda day, rows, query, **kw: (200, {
            'items': rows[int(query.get('offset', 0)):int(query.get('offset', 0))+int(query.get('limit', 30))],
            'total': len(rows), 'offset': int(query.get('offset', 0)), 'limit': int(query.get('limit', 30)),
            'has_next': int(query.get('offset', 0))+int(query.get('limit', 30)) < len(rows), **kw})
        queries = [
            {'context_token': TOKEN, 'event': ''},
            {'context_token': TOKEN, 'event': 'NEW'},
            {'context_token': TOKEN, 'event': 'PERSISTENT', 'validity': 'UNKNOWN'},
            {'context_token': TOKEN, 'offset': '1', 'limit': '1'},
        ]
        totals = []
        for query in queries:
            code, response = self.bff.get('/api/v4/focus/events', query)
            self.assertEqual(code, 200)
            totals.append(response['total'])
        self.assertEqual(totals, [2, 1, 1, 2])
        self.assertEqual(self.bff.get('/api/v4/focus/events', queries[3])[1]['items'][0]['event'], 'PERSISTENT')
        with self.assertRaisesRegex(ValueError, 'INVALID_EVENT'):
            self.bff.get('/api/v4/focus/events', {'context_token': TOKEN, 'event': 'BOGUS'})

    def test_unknown_limit_filter_and_cross_route_rejection(self):
        rows = [{'security_id': f'SEC-{i}', 'limit_state': 'UNKNOWN'} for i in range(21)]
        self.bff.pack = lambda day: ({}, {'limits': {'rows': rows, 'counts': {'UNKNOWN': 21}},
            'sources': {'limits_0': {'path': 'limits.json', 'sha256': 'd' * 64}}})
        self.bff.paged = lambda day, items, query, **kw: (200, {
            'items': items[int(query.get('offset', 0)):int(query.get('offset', 0))+int(query.get('limit', 30))],
            'total': len(items), 'offset': int(query.get('offset', 0)), 'limit': int(query.get('limit', 30)), **kw})
        code, first = self.bff.get('/api/v4/market/limits', {'context_token': TOKEN, 'limit_state': 'UNKNOWN', 'limit': '10'})
        self.assertEqual((code, first['total'], len(first['items'])), (200, 21, 10))
        code, second = self.bff.get('/api/v4/market/limits', {'context_token': TOKEN, 'limit_state': 'UNKNOWN', 'limit': '10', 'offset': '10'})
        self.assertEqual((code, second['total'], len(second['items'])), (200, 21, 10))
        for path in ('/api/v4/market/breadth', '/api/v4/stocks'):
            with self.assertRaisesRegex(ValueError, 'UNKNOWN_PARAMETER'):
                self.bff.get(path, {'context_token': TOKEN, 'limit_state': 'UNKNOWN'})

    def test_profile_route_reads_full_r2_detail_and_keeps_missing_quality(self):
        fields = {'scenario': {'value': 'NONE', 'quality': 'KNOWN'},
                  'scenario_status': {'value': 'UNKNOWN', 'quality': 'SOURCE_INCOMPLETE', 'reason': 'DETECTOR_NOT_RUN'},
                  'final_eligibility': {'value': None, 'quality': 'UNKNOWN'},
                  'matched_predicates': {'value': [], 'quality': 'KNOWN'},
                  'identity_status': {'value': 'CONFIRMED_CURRENT_IDENTITY', 'quality': 'KNOWN'}}
        detail = {'entity_id': 'SEC-1', 'symbol': 'SZ.301660', 'fields': fields}
        index = FakeR2(detail)
        self.bff._read_index_r2 = lambda day: index
        self.bff.resolve_dated_object = lambda domain, day, key: detail

        def base_get(instance, path, query):
            payload = instance.page('stocks', DAY, query, entity='SEC-1')
            if payload['items']:
                payload['item'] = payload['items'][0]
            payload['owner_explanations'] = {}
            return 200, payload

        with patch.object(OperationalSuccessorBFFV1, 'get', base_get):
            code, response = self.bff.get('/api/v4/stocks/SZ.301660/profile', {'context_token': TOKEN})
        self.assertEqual(code, 200)
        self.assertEqual(index.detail_calls, [('stocks', 'SEC-1')])
        self.assertEqual(response['selection_explanation']['d2']['scenario'], 'NONE')
        self.assertEqual(response['selection_explanation']['d2']['scenario_status']['reason'], 'DETECTOR_NOT_RUN')
        self.assertEqual(response['item']['fields']['identity_status']['value'], 'CONFIRMED_CURRENT_IDENTITY')
        self.assertNotIn(('stocks', {'context_token': TOKEN}), index.page_calls)

    def test_sector_detail_does_not_load_unrelated_focus_projection(self):
        self.bff._read_index_r2 = lambda day: None
        self.bff._get_product = lambda path, query: (200, {'context': {}, 'item': {'entity_id': 'INDUSTRY:T0101'}})
        self.bff.focus_projection = lambda day: self.fail('sector detail must not load the Focus projection')
        code, response = self.bff.get('/api/v4/sectors/INDUSTRY:T0101', {'context_token': TOKEN})
        self.assertEqual(code, 200)
        self.assertEqual(response['item']['entity_id'], 'INDUSTRY:T0101')

    def test_sector_detail_uses_indexed_rotation_explanation_without_owner_reload(self):
        why_now = {'current_state': 'RISING', 'reason_codes': ['BREADTH_IMPROVED']}
        detail = {'entity_id': 'INDUSTRY:T0101', 'symbol': 'T0101', 'fields': {}, 'why_now': why_now}
        index = FakeR2(detail)
        self.bff._read_index_r2 = lambda day: index
        self.bff.source = lambda domain, day: self.fail('indexed sector detail must not reload the rotation owner')

        def base_get(instance, path, query):
            page = instance.page('sectors', DAY, query, entity='INDUSTRY:T0101')
            return 200, {'context': {}, 'item': page['item']}

        with patch.object(OperationalSuccessorBFFV1, 'get', base_get):
            code, response = self.bff.get('/api/v4/sectors/INDUSTRY:T0101', {'context_token': TOKEN})
        self.assertEqual(code, 200)
        self.assertEqual(response['why_now'], why_now)
        self.assertEqual(index.detail_calls, [('sectors', 'INDUSTRY:T0101')])

    def test_focus_entity_route_attaches_full_r2_detail(self):
        detail = {'entity_id': 'SEC-2', 'fields': {'validity': {'value': 'UNKNOWN', 'quality': 'SOURCE_INCOMPLETE',
            'reason': 'NO_DATED_VALIDITY_OWNER'}}}
        index = FakeR2(detail)
        self.bff._read_index_r2 = lambda day: index
        self.bff.source = lambda domain, day: {'episodes': [{'entity_id': 'SEC-2', 'episode_id': 'EP-1', 'observations': []}]}
        self.bff.paged = lambda day, rows, query, **kw: (200, {'items': rows, 'total': len(rows), **kw})
        code, response = self.bff.get('/api/v4/focus/SEC-2', {'context_token': TOKEN})
        self.assertEqual(code, 200)
        self.assertEqual(response['focus_item'], detail)
        self.assertEqual(index.detail_calls, [('stocks', 'SEC-2'), ('focus', 'SEC-2')])

    def test_display_name_join_preserves_owner_source_and_unknown_reason(self):
        source = {'path': 'identity/display-names.json', 'sha256': 'e' * 64}
        rows = [{'entity_id': 'SEC-1'}, {'entity_id': 'SEC-2'}]
        self.bff._display_identity_map = lambda day, selected, **kwargs: {
            'SEC-1': {'symbol': 'SZ.000001', 'display_name': '甲公司',
                      'display_name_source': source, 'name_quality': 'KNOWN'}
        }
        result = self.bff._enrich_display_names(DAY, rows)
        self.assertEqual(result[0]['display_name'], '甲公司')
        self.assertEqual(result[0]['display_name_source'], source)
        self.assertEqual(result[1]['name_quality'], 'UNKNOWN')
        self.assertEqual(result[1]['name_reason'], 'ACCEPTED_STOCK_IDENTITY_NOT_FOUND')

    def test_r2_authority_missing_token_and_schema_are_distinguished(self):
        authority_path = self.root / AUTHORITY
        authority_path.parent.mkdir(parents=True, exist_ok=True)
        authority_path.write_text(json.dumps({'contract_id': 'V4_READ_INDEX_R2', 'versions': {}}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'READ_INDEX_TOKEN_NOT_PREPARED'):
            load(self.root, TOKEN, DAY)
        authority_path.write_text(json.dumps({'contract_id': 'V4_READ_INDEX_R2', 'versions': []}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'READ_INDEX_AUTHORITY_SCHEMA_INVALID'):
            load(self.root, TOKEN, DAY)

    def test_r2_missing_date_and_pg_digest_conflict_fail_closed(self):
        authority_path = self.root / AUTHORITY
        authority_path.parent.mkdir(parents=True, exist_ok=True)
        authority_path.write_text(json.dumps({'contract_id': CONTRACT, 'versions': {TOKEN: {}}}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'READ_INDEX_DATE_NOT_PREPARED'):
            load(self.root, TOKEN, DAY)
        self.assertIsNone(load(self.root, 'z' * 64, DAY, allow_missing=True))

        index = object.__new__(ReadIndex)
        index.binding = {'database_identity': {'system_identifier': 'test'}, 'digest': 'expected-digest'}
        index.token = TOKEN
        index.day = DAY

        class FakeCursor:
            def fetchone(self):
                return ('wrong-digest', CONTRACT, True)

        class FakePG:
            def execute(self, *_args):
                return FakeCursor()

        with patch('workbench_db.v4_read_index_r2.ForwardFactStore._database_identity',
                   return_value={'system_identifier': 'test'}):
            with self.assertRaisesRegex(ValueError, 'READ_INDEX_VERSION_DIGEST_MISMATCH'):
                index.attest(FakePG())

        with self.assertRaisesRegex(ValueError, 'READ_INDEX_SCHEMA_MISMATCH'):
            ReadIndex(self.root, {'contract_id': CONTRACT, 'engine': 'postgresql', 'schema': 'wrong',
                'head_token': TOKEN, 'T0': DAY, 'digest': 'd', 'counts': {},
                'database_identity': {}}, TOKEN, DAY)

    def test_http_handler_routes_through_bff_without_blank_filter_failure(self):
        def bind_file(relative, payload):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = json.dumps(payload).encode('utf-8')
            path.write_bytes(raw)
            return {'path': relative, 'sha256': hashlib.sha256(raw).hexdigest()}

        identity_ref = bind_file('data/identity.json', {'records': []})
        registry_ref = bind_file('config/registry.json', {'fields': []})
        forward_ref = bind_file('data/forward.json', {'events': []})
        focus_ref = bind_file('data/focus.json', {'items': []})
        bind_file('data/v4/V4_DATA_ACCEPTED_HEAD.json', {'identity': identity_ref})
        bind_file(AUTHORITY, {'contract_id': CONTRACT, 'versions': {}})
        api = FakeAPI(self.root)
        api.snapshot = {}
        api.candidate['registry'] = registry_ref
        api.candidate['owners'][DAY]['forward'] = forward_ref
        api.candidate['owners'][DAY]['focus'] = focus_ref

        class HTTPR2(FakeR2):
            def page(self, domain, query, **kwargs):
                self.page_calls.append((domain, dict(query)))
                offset = int(query.get('offset', 0)); limit = int(query.get('limit', 30))
                return {'status': 'READY', 'items': [], 'total': 63, 'offset': offset,
                    'limit': limit, 'has_next': offset + limit < 63, 'domain': domain}

        index = HTTPR2()
        forward = {'events': [
            {'entity_id': 'SEC-1', 'event': 'NEW', 'validity': 'VALID', 'trade_date': DAY},
            {'entity_id': 'SEC-2', 'event': 'PERSISTENT', 'validity': 'UNKNOWN', 'trade_date': DAY},
        ]}
        limit_rows = [{'security_id': f'SEC-{i}', 'limit_state': 'UNKNOWN'} for i in range(21)]
        patches = [
            patch('workbench_service.core_product_server_r1.make_daily_handler', return_value=BaseHTTPRequestHandler),
            patch('workbench_service.core_product_server_r1.accepted_api', return_value=api),
            patch.object(CoreProductBFFR1, '_read_index_r2', lambda _self, day: index),
            patch.object(CoreProductBFFR1, 'source', lambda _self, domain, day: forward),
            patch.object(CoreProductBFFR1, 'pack', lambda _self, day: ({}, {'limits': {
                'rows': limit_rows, 'counts': {'UNKNOWN': 21}}, 'sources': {
                'limits_0': {'path': 'data/limits.json', 'sha256': 'f' * 64}}})),
            patch.object(CoreProductBFFR1, '_display_identity_map', lambda _self, day, rows, **kwargs: {}),
            patch.object(CoreProductBFFR1, 'paged', lambda _self, day, rows, query, **kw: (200, {
                'items': rows[int(query.get('offset', 0)):int(query.get('offset', 0))+int(query.get('limit', 30))],
                'total': len(rows), 'offset': int(query.get('offset', 0)), 'limit': int(query.get('limit', 30)),
                'has_next': int(query.get('offset', 0))+int(query.get('limit', 30)) < len(rows), **kw})),
        ]
        for item in patches:
            item.start()
        server = ThreadingHTTPServer(('127.0.0.1', 0), make_product_handler(self.root, None))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f'http://127.0.0.1:{server.server_address[1]}'
        try:
            try:
                with urlopen(base + f'/api/v4/radar?context_token={TOKEN}', timeout=5) as response:
                    radar = json.loads(response.read())
            except HTTPError as exc:
                raise AssertionError(exc.read().decode('utf-8')) from exc
            self.assertEqual((radar['domain'], radar['total']), ('radar', 63))

            with urlopen(base + f'/api/v4/radar?context_token={TOKEN}&offset=30&event=UPGRADED&validity=VALID', timeout=5) as response:
                radar_page_two = json.loads(response.read())
            self.assertEqual((radar_page_two['domain'], radar_page_two['offset'], radar_page_two['total']), ('radar', 30, 63))
            self.assertEqual(index.page_calls[-1][1]['event'], 'UPGRADED')

            with urlopen(base + f'/api/v4/focus/events?context_token={TOKEN}&event=', timeout=5) as response:
                events = json.loads(response.read())
            self.assertEqual(events['total'], 2)

            with urlopen(base + f'/api/v4/focus/events?context_token={TOKEN}&event=NEW&validity=VALID', timeout=5) as response:
                selected = json.loads(response.read())
            self.assertEqual((selected['total'], selected['items'][0]['event']), (1, 'NEW'))

            with urlopen(base + f'/api/v4/market/limits?context_token={TOKEN}&limit_state=UNKNOWN&limit=10', timeout=5) as response:
                unknown_limits = json.loads(response.read())
            self.assertEqual((unknown_limits['total'], len(unknown_limits['items']), unknown_limits['filter_state']), (21, 10, 'UNKNOWN'))

            try:
                urlopen(base + f'/api/v4/focus/events?context_token={TOKEN}&event=INVALID', timeout=5)
            except HTTPError as exc:
                self.assertEqual(exc.code, 400)
                self.assertEqual(json.loads(exc.read())['reason'], 'INVALID_EVENT')
            else:
                self.fail('invalid event filter unexpectedly passed HTTP validation')

            try:
                urlopen(base + f'/api/v4/stocks?context_token={TOKEN}&limit_state=UNKNOWN', timeout=5)
            except HTTPError as exc:
                self.assertEqual(exc.code, 400)
                self.assertEqual(json.loads(exc.read())['reason'], 'UNKNOWN_PARAMETER')
            else:
                self.fail('cross-route limit_state unexpectedly passed HTTP validation')
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)
            for item in reversed(patches):
                item.stop()


if __name__ == '__main__':
    unittest.main()
