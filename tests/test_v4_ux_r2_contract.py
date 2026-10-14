import unittest

from workbench_db.v4_read_index_r2 import materialize_radar_rows, query_parts, summary, validate_home_response, validate_query
from workbench_service.core_product_bff_r1 import current_identity_presentation, home_summary


class UXR2RouteContractTests(unittest.TestCase):
    def setUp(self):
        self.token = 'a' * 64
        self.day = '2026-10-13'

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


if __name__ == '__main__':
    unittest.main()
