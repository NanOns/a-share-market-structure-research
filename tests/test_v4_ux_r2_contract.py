import unittest

from workbench_db.v4_read_index_r2 import (
    materialize_radar_rows, query_parts, schema_binding_matches,
    schema_for_revision, summary, detail_payload, validate_home_response, validate_query,
)
from workbench_service.core_product_bff_r1 import (
    current_identity_presentation, home_summary, is_legacy_r1_home_fallback,
)


class UXR2RouteContractTests(unittest.TestCase):
    def setUp(self):
        self.token = 'a' * 64
        self.day = '2026-10-13'

    def test_detail_only_extras_are_expanded_but_never_leak_into_summary(self):
        row = {'entity_id': 'INDUSTRY:T0101', 'symbol': 'T0101', 'display_name': '测试行业',
               'fields': {'member_count': {'value': 3}},
               '__detail_extras__': {'why_now': {'current_state': 'RISING'}}}
        self.assertEqual(detail_payload(row)['why_now'], {'current_state': 'RISING'})
        self.assertNotIn('__detail_extras__', detail_payload(row))
        self.assertNotIn('why_now', summary(row, 'sectors'))
        self.assertNotIn('__detail_extras__', summary(row, 'sectors'))

    def test_limit_state_is_allowed_only_on_limits_route(self):
        query = {'trade_date': self.day, 'context_token': self.token, 'limit_state': 'UNKNOWN'}
        self.assertEqual(validate_query(query, self.token, [self.day], self.day, '/api/v4/market/limits'), self.day)
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_PARAMETER'):
            validate_query(query, self.token, [self.day], self.day, '/api/v4/market/breadth')

    def test_limit_state_rejects_non_enum_values(self):
        query = {'trade_date': self.day, 'context_token': self.token, 'limit_state': 'NOT_A_STATE'}
        with self.assertRaisesRegex(ValueError, 'INVALID_LIMIT_STATE'):
            validate_query(query, self.token, [self.day], self.day, '/api/v4/market/limits')

    def test_focus_event_filters_are_route_scoped(self):
        query = {'trade_date': self.day, 'context_token': self.token, 'event': 'PERSISTENT'}
        self.assertEqual(validate_query(query, self.token, [self.day], self.day, '/api/v4/focus/events'), self.day)
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_PARAMETER'):
            validate_query(query, self.token, [self.day], self.day, '/api/v4/stocks')

    def test_radar_filters_are_applied_before_sql_paging(self):
        where, args, order, offset, limit = query_parts(
            'radar', {'q': '600000', 'event': 'UPGRADED', 'validity': 'VALID', 'offset': '30', 'limit': '30'}
        )
        self.assertEqual(args, ['600000', 'UPGRADED', 'VALID'])
        self.assertEqual((offset, limit), (30, 30))
        self.assertIn('strpos', str(where))
        self.assertIn('entity_id', str(order))

    def test_radar_summary_links_to_stock_detail(self):
        row = {'entity_id': 'SEC-1', 'symbol': 'SZ.301660', 'display_name': '测试', 'fields': {}}
        self.assertEqual(summary(row, 'radar')['detail_href'], '/api/v4/stocks/SEC-1')

    def test_radar_materialization_deduplicates_and_excludes_rotation_coverage(self):
        stocks = {
            'SEC-1': {'entity_id': 'SEC-1', 'symbol': 'SZ.000001', 'display_name': '甲', 'fields': {}},
            'SEC-2': {'entity_id': 'SEC-2', 'symbol': 'SZ.000002', 'display_name': '乙', 'fields': {}},
        }
        focus = [{'entity_id': 'SEC-1', 'fields': {'validity': {'value': 'VALID'}}}]
        rows = materialize_radar_rows(stocks, focus, {'SECTOR-1': {'SEC-2'}},
            [{'entity_id': 'SECTOR-1'}],
            [{'entity_id': 'SEC-1', 'event': 'NEW'}, {'entity_id': 'SEC-1', 'event': 'WEAKENED'},
             {'entity_id': 'SEC-2', 'event': 'EXITED'}, {'entity_id': 'MISSING', 'event': 'NEW'}],
            {'path': 'forward.json', 'sha256': 'c' * 64}, self.day)
        self.assertEqual([row['entity_id'] for row in rows], ['SEC-1'])
        self.assertEqual(rows[0]['fields']['effective_event']['value'], 'WEAKENED')
        self.assertEqual(rows[0]['fields']['validity']['value'], 'VALID')
        self.assertEqual(rows[0]['source']['sha256'], 'c' * 64)

    def test_confirmed_ipo_identity_does_not_replace_code_status(self):
        identity = {'code_status': 'CONFIRMED_IPO', 'first_seen_date': self.day, 'list_date': self.day}
        status = current_identity_presentation(identity, {'path': 'identity.json', 'sha256': 'b' * 64}, self.day)
        self.assertEqual(status['value'], 'CONFIRMED_CURRENT_IDENTITY')
        self.assertEqual(identity['code_status'], 'CONFIRMED_IPO')

    def test_home_summary_preserves_rendered_fields_without_full_profile(self):
        row = {
            'entity_id': 'SEC-1', 'security_id': 'SEC-1', 'symbol': 'SZ.000001',
            'display_name': '测试', 'trade_date': self.day,
            'field_owner_bindings': {'private_detail': 'not-for-home'},
            'knowledge_lineage': {'many': 'details'}, 'search_aliases': ['000001'],
            'fields': {
                'effective_event': {'value': 'WEAKENED', 'quality': 'KNOWN', 'source': {'path': 'events.json'}},
                'trade_date': {'value': self.day, 'quality': 'KNOWN'},
                'scenario': {'value': 'NONE', 'quality': 'KNOWN'},
                'large_array': {'value': list(range(2000)), 'quality': 'KNOWN'},
            },
        }
        result = home_summary(row, {'effective_event', 'trade_date'})
        self.assertEqual(set(result['fields']), {'effective_event', 'trade_date'})
        self.assertEqual(result['fields']['effective_event']['quality'], 'KNOWN')
        self.assertNotIn('field_owner_bindings', result)
        self.assertNotIn('knowledge_lineage', result)
        self.assertNotIn('search_aliases', result)

    def test_home_response_guard_accepts_summary_and_rejects_full_detail(self):
        row = {'entity_id': 'SEC-1', 'symbol': 'SZ.000001', 'display_name': '测试',
               'fields': {'effective_event': {'value': 'NEW', 'quality': 'KNOWN'}}}
        payload = {'changes': [row], 'risks': [], 'rotations': [], 'sector_changes': []}
        self.assertGreater(validate_home_response(payload), 0)
        payload['changes'][0]['fields']['knowledge_lineage'] = {'value': 'large'}
        with self.assertRaisesRegex(ValueError, 'HOME_FULL_DETAIL_REGRESSION'):
            validate_home_response(payload)
        oversized = {'changes': [], 'risks': [], 'rotations': [], 'sector_changes': [],
                     'diagnostic': 'x' * (512 * 1024)}
        with self.assertRaisesRegex(ValueError, 'HOME_RESPONSE_SIZE_LIMIT_EXCEEDED'):
            validate_home_response(oversized)

    def test_legacy_r1_home_is_explicitly_marked_for_compatibility(self):
        legacy = {
            'read_index_status': 'LEGACY_R1_AUTHORITY_ONLY',
            'read_index_capability': 'R1 legacy summary; D2 detail fields may be unavailable',
        }
        self.assertTrue(is_legacy_r1_home_fallback(legacy))
        # R2 and unmarked responses must continue to meet the R2 size/shape guard.
        self.assertFalse(is_legacy_r1_home_fallback({
            **legacy, 'read_index_status': 'R2_AUTHORITY_BOUND',
        }))
        self.assertFalse(is_legacy_r1_home_fallback({'read_index_status': 'LEGACY_R1_AUTHORITY_ONLY'}))

    def test_read_index_digest_revision_uses_additive_schema(self):
        from pathlib import Path
        root = Path('G:/codex_tmp/test_temp/r4-index-root')
        digest_a = 'a' * 64
        digest_b = 'b' * 64
        schema_a = schema_for_revision(root, digest_a)
        schema_b = schema_for_revision(root, digest_b)
        self.assertNotEqual(schema_a, schema_b)
        self.assertTrue(schema_binding_matches(root, {
            'schema': schema_a, 'digest': digest_a,
        }))
        self.assertFalse(schema_binding_matches(root, {
            'schema': schema_a, 'digest': digest_b,
        }))
        # The old R2 schema remains readable; the producer never writes there.
        from workbench_db.v4_native import workspace_schema
        self.assertTrue(schema_binding_matches(root, {
            'schema': workspace_schema(root, 'read_index_r2'),
        }))

    def test_read_index_detail_uses_exact_primary_key_before_fallbacks(self):
        from unittest.mock import patch
        from workbench_db import v4_read_index_r2 as module
        from workbench_db.v4_read_index_r2 import ReadIndex, canonical

        row = {'entity_id': 'INDUSTRY:T0101', 'fields': {'maturity': {'value': None}}}
        detail_digest = __import__('hashlib').sha256(canonical(row)).hexdigest()

        class Result:
            def __init__(self, one=None, many=None):
                self.one, self.many = one, many or []

            def fetchone(self):
                return self.one

            def fetchall(self):
                return self.many

        class Pg:
            def __init__(self):
                self.calls = []

            def execute(self, statement, args=None):
                query = str(statement)
                self.calls.append(query)
                if 'SELECT digest,contract,sealed' in query:
                    return Result(one=('d' * 64, 'V4_READ_INDEX_R2', True))
                return Result(many=[(row, detail_digest)])

        pg = Pg()

        class Connection:
            def __enter__(self):
                return pg

            def __exit__(self, *_):
                return False

        binding = dict(contract_id='V4_READ_INDEX_R2', engine='postgresql', schema='v4_test',
                       head_token=self.token, T0=self.day, digest='d' * 64, counts={},
                       database_identity={'id': 1})
        with (patch.object(module, 'connection', return_value=Connection()),
              patch.object(module, 'schema_binding_matches', return_value=True),
              patch.object(module.ForwardFactStore, '_database_identity', return_value={'id': 1})):
            result = ReadIndex('root', binding, self.token, self.day).detail('sectors', row['entity_id'])

        self.assertEqual(result, row)
        self.assertEqual(len(pg.calls), 2)  # attest + one primary-key lookup
        self.assertIn('entity_id=%s LIMIT 2', pg.calls[1])
        self.assertNotIn(' OR ', pg.calls[1])

    def test_read_index_detail_reaches_symbol_fallback_only_after_primary_miss(self):
        from unittest.mock import patch
        from workbench_db import v4_read_index_r2 as module
        from workbench_db.v4_read_index_r2 import ReadIndex, canonical
        import hashlib

        row = {'entity_id': 'SEC-1', 'symbol': 'SH.600000'}
        detail_digest = hashlib.sha256(canonical(row)).hexdigest()

        class Result:
            def __init__(self, one=None, many=None):
                self.one, self.many = one, many or []

            def fetchone(self): return self.one
            def fetchall(self): return self.many

        class Pg:
            def __init__(self): self.calls = []
            def execute(self, statement, args=None):
                query = str(statement)
                self.calls.append(query)
                if 'SELECT digest,contract,sealed' in query:
                    return Result(one=('d' * 64, 'V4_READ_INDEX_R2', True))
                if 'entity_id=%s LIMIT 2' in query:
                    return Result(many=[])
                if 'upper(symbol)=upper(%s)' in query:
                    return Result(many=[(row, detail_digest)])
                self.fail('unexpected alias scan')

            def fail(self, message): raise AssertionError(message)

        pg = Pg()

        class Connection:
            def __enter__(self): return pg
            def __exit__(self, *_): return False

        binding = dict(contract_id='V4_READ_INDEX_R2', engine='postgresql', schema='v4_test',
                       head_token=self.token, T0=self.day, digest='d' * 64, counts={},
                       database_identity={'id': 1})
        with (patch.object(module, 'connection', return_value=Connection()),
              patch.object(module, 'schema_binding_matches', return_value=True),
              patch.object(module.ForwardFactStore, '_database_identity', return_value={'id': 1})):
            result = ReadIndex('root', binding, self.token, self.day).detail('stocks', 'SH.600000')

        self.assertEqual(result, row)
        self.assertEqual(len(pg.calls), 3)  # attest + exact key miss + symbol fallback

    def test_read_index_detail_and_context_share_one_attested_connection(self):
        from unittest.mock import patch
        from workbench_db import v4_read_index_r2 as module
        from workbench_db.v4_read_index_r2 import ReadIndex, canonical
        import hashlib

        context = {'context': {'trade_date': self.day}, 'context_token': self.token}
        row = {'entity_id': 'INDUSTRY:T0101', 'fields': {'member_count': {'value': 32}}}

        class Result:
            def __init__(self, one=None, many=None): self.one, self.many = one, many or []
            def fetchone(self): return self.one
            def fetchall(self): return self.many

        class Pg:
            def execute(self, statement, args=None):
                query = str(statement)
                if 'SELECT digest,contract,sealed' in query:
                    return Result(one=('d' * 64, 'V4_READ_INDEX_R2', True))
                if 'SELECT payload,payload_sha256' in query:
                    return Result(one=(context, hashlib.sha256(canonical(context)).hexdigest()))
                if 'entity_id=%s LIMIT 2' in query:
                    return Result(many=[(row, hashlib.sha256(canonical(row)).hexdigest())])
                raise AssertionError('unexpected query')

        pg = Pg()

        class Connection:
            def __enter__(self): return pg
            def __exit__(self, *_): return False

        binding = dict(contract_id='V4_READ_INDEX_R2', engine='postgresql', schema='v4_test',
                       head_token=self.token, T0=self.day, digest='d' * 64, counts={},
                       database_identity={'id': 1})
        with (patch.object(module, 'connection', return_value=Connection()) as connect,
              patch.object(module, 'schema_binding_matches', return_value=True),
              patch.object(module.ForwardFactStore, '_database_identity', return_value={'id': 1})):
            result_context, result_detail = ReadIndex('root', binding, self.token, self.day).response_and_detail(
                '/api/v4/context', 'sectors', row['entity_id'])

        self.assertEqual(result_context, context)
        self.assertEqual(result_detail, row)
        self.assertEqual(connect.call_count, 1)


if __name__ == '__main__':
    unittest.main()
