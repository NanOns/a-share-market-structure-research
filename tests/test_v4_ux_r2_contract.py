import unittest
import hashlib
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from workbench_db.v4_read_index_r2 import (
    materialize_radar_rows, query_parts, schema_binding_matches,
    schema_for_revision, summary, detail_payload, validate_home_response, validate_query, ReadIndex, canonical,
)
from workbench_service.core_product_bff_r1 import (
    annotate_home_readiness, code_status_presentation, current_identity_presentation, home_summary,
    is_legacy_r1_home_fallback, normalize_indexed_code_status, quarantine_incomplete_sector_home,
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

    def test_focus_ui_event_filter_does_not_leak_into_focus_list_request(self):
        from workbench_service.core_product_bff_r1 import CoreProductBFFR1
        query = {'trade_date': self.day, 'context_token': self.token, 'event_state': 'INVALIDATED',
                 'events_offset': '30', 'offset': '0', 'limit': '30'}
        self.assertEqual(CoreProductBFFR1._base_query(query),
                         {'trade_date': self.day, 'context_token': self.token,
                          'offset': '0', 'limit': '30'})
        base_route_query = {k: v for k, v in query.items() if k not in ('event_state', 'events_offset')}
        self.assertEqual(validate_query(base_route_query, self.token, [self.day], self.day,
                                        '/api/v4/focus'), self.day)

    def test_read_index_identity_join_is_domain_scoped_and_exposes_stock_industry_id(self):
        details = {
            'SEC-1': {'fields': {'primary_industry': {'value': 'INDUSTRY:T0101'}}},
            'INDUSTRY:T0101': {'fields': {'sector_type': {'value': 'INDUSTRY'}}},
        }
        class FakePG:
            def execute(self, query, args):
                domain = args[2]
                entity_id = args[3][0]
                detail = details[entity_id]
                row = (entity_id, entity_id, '电气设备' if domain == 'sectors' else '示例证券',
                       detail, hashlib.sha256(canonical(detail)).hexdigest())
                return SimpleNamespace(fetchall=lambda: [row])
        @contextmanager
        def fake_connection(*args, **kwargs):
            yield FakePG()
        index = ReadIndex.__new__(ReadIndex)
        index.binding = {'schema': 'isolated_schema'}
        index.token, index.day = self.token, self.day
        with patch('workbench_db.v4_read_index_r2.connection', fake_connection), \
             patch.object(index, 'attest'):
            stock = index.display_identities('stocks', ['SEC-1'])['SEC-1']
            sector = index.display_identities('sectors', ['INDUSTRY:T0101'])['INDUSTRY:T0101']
        self.assertEqual(stock['primary_industry_id'], 'INDUSTRY:T0101')
        self.assertNotIn('primary_industry_id', sector)
        self.assertEqual(sector['display_name'], '电气设备')

    def test_thin_pg_corrections_forward_external_workspace_root(self):
        from workbench_db import v4_profile_dependent_corrections_pg_v1 as dependent
        from workbench_db import v4_profile_semantic_corrections_pg_v1 as semantic
        workspace = Path('G:/codex work/v4-production-20261012')
        dependent_entry = {'descriptor': {'path': 'descriptor.json'}, 'fact_token': 'a' * 64,
                           'source': {'path': 'source.json'}, 'entity_ids': []}
        dependent_authority = {'dates': {self.day: {'focus': dependent_entry}}}
        with patch.object(dependent, 'load', return_value=dependent_authority), \
             patch.object(dependent, 'read_fact', return_value=[]) as read_dependent:
            self.assertEqual(dependent.apply(Path('.'), {}, self.day, 'focus', [],
                                             workspace_root=workspace), [])
        self.assertEqual(read_dependent.call_args.kwargs['workspace_root'], workspace)
        semantic_entry = {'descriptor': {'path': 'descriptor.json'}, 'fact_token': 'b' * 64,
                          'source': {'path': 'source.json'}, 'security_ids': []}
        semantic_authority = {'dates': {self.day: semantic_entry}}
        with patch.object(semantic, 'load', return_value=semantic_authority), \
             patch.object(semantic, 'read_fact', return_value=[]) as read_semantic:
            self.assertEqual(semantic.apply(Path('.'), {}, self.day, [],
                                            workspace_root=workspace), [])
        self.assertEqual(read_semantic.call_args.kwargs['workspace_root'], workspace)

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
        self.assertEqual(status['value'], 'CURRENT_IDENTITY_PRESENT')
        self.assertEqual(identity['code_status'], 'CONFIRMED_IPO')

    def test_code_status_uses_dated_identity_and_never_marks_every_row_new(self):
        source = {'path': 'identity.json', 'sha256': 'b' * 64}
        old = code_status_presentation({'symbol': 'SH.600703', 'list_date': '1996-05-28', 'code_status':'NEW_CODE_OBSERVED'}, source, self.day)
        new = code_status_presentation({'symbol': 'SZ.301660', 'list_date': self.day, 'first_seen_date':self.day}, source, self.day)
        missing = code_status_presentation({}, source, self.day)
        self.assertEqual((old['value'], old['quality']), ('EXISTING_VERIFIED_IDENTITY', 'KNOWN'))
        self.assertEqual((new['value'], new['quality']), ('NEW_CODE_OBSERVED', 'KNOWN'))
        self.assertEqual((missing['value'], missing['quality']), ('UNKNOWN', 'SOURCE_INCOMPLETE'))

    def test_identity_dates_are_separate_from_raw_owner_code_status(self):
        from workbench_service.core_product_bff_r1 import identity_date_statuses
        source={'path':'identity.json','sha256':'b'*64}
        old=identity_date_statuses({'list_date':'1996-05-28','first_seen_date':'1996-05-28','code_status':'NEW_CODE_OBSERVED'},source,self.day)
        ipo=identity_date_statuses({'list_date':self.day,'first_seen_date':self.day,'code_status':'NEW_CODE_OBSERVED'},source,self.day)
        self.assertEqual(old['listing_status']['value'],'LISTED_BEFORE')
        self.assertEqual(old['first_seen_status']['value'],'OBSERVED_BEFORE')
        self.assertEqual(old['owner_code_status']['value'],'NEW_CODE_OBSERVED')
        self.assertEqual(ipo['listing_status']['value'],'LISTED_TODAY')
        self.assertEqual(ipo['first_seen_status']['value'],'FIRST_OBSERVED_TODAY')
        self.assertEqual(ipo['ipo_confirmation_status']['value'],'IPO_NOT_INDEPENDENTLY_CONFIRMED')

    def test_indexed_stock_page_recomputes_code_status_from_dated_identity(self):
        payload = {'items': [
            {'identity_observation': {'list_date': '1996-05-28', 'code_status':'NEW_CODE_OBSERVED',
              'owner_code_status':{'value':'NEW_CODE_OBSERVED','quality':'KNOWN','source':{'path':'profile.json','sha256':'c'*64}}},
             'fields': {'code_status': {'value': 'NEW_CODE_OBSERVED'}}},
            {'identity_observation': {'first_seen_date': self.day}, 'fields': {'code_status': {'value': 'NEW_CODE_OBSERVED'}}},
        ], 'item': {'identity_observation': {'list_date': '1996-05-28'},
                   'fields': {'code_status': {'value': 'NEW_CODE_OBSERVED'}}}}
        result = normalize_indexed_code_status(payload, self.day)
        self.assertEqual(result['items'][0]['fields']['code_status']['value'], 'EXISTING_VERIFIED_IDENTITY')
        self.assertEqual(result['items'][0]['fields']['owner_code_status']['value'],'NEW_CODE_OBSERVED')
        self.assertEqual(result['items'][0]['fields']['owner_code_status']['source']['path'],'profile.json')
        self.assertEqual(result['items'][1]['fields']['code_status']['value'], 'NEW_CODE_OBSERVED')
        self.assertEqual(result['item']['fields']['code_status']['value'], 'EXISTING_VERIFIED_IDENTITY')

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

    def test_home_readiness_overlays_prebuilt_responses_without_promoting_partial_risk(self):
        source = {'market': {'regime_publication_status': 'ACCEPTED', 'row': {'stress_level': 'LOW'}},
                  'risks': [{'entity_id': 'SEC-1', 'fields': {'effective_event': {'value': 'WEAKENED'}}}],
                  'counts': {'forward': {'value': 15}}}
        result = annotate_home_readiness(source)
        self.assertEqual(result['market']['regime_publication_status'], 'ACCEPTED')
        self.assertEqual(result['market']['formal_risk_status'], 'SOURCE_INCOMPLETE')
        self.assertEqual(result['risks'], [])
        self.assertEqual(result['focus_risk_events'], source['risks'])
        self.assertEqual(result['risk_families']['SECTOR_ECOLOGY_RISK']['value'], None)
        self.assertIsNone(result['counts']['forward']['value'])
        self.assertEqual(source['market']['regime_publication_status'], 'ACCEPTED')
        self.assertEqual(source['risks'], result['focus_risk_events'])

    def test_r2_prebuilt_home_uses_readiness_overlay_before_early_return(self):
        from workbench_service.core_product_bff_r1 import CoreProductBFFR1
        token='a'*64;day='2026-10-13'
        row={'entity_id':'SEC-1','symbol':'SZ.000001','display_name':'测试','fields':
             {'effective_event':{'value':'WEAKENED','quality':'KNOWN'}}}
        payload={'context':{},'context_token':token,'production_accepted':True,
            'market':{'regime_publication_status':'ACCEPTED','row':{'stress_level':'LOW'}},
            'risks':[row],'counts':{'forward':{'value':12},'radar':{'value':1},'sectors':400},
            'changes':[],'rotations':[{'entity_id':'INDUSTRY:TEST'}],
            'rotation_total':2,'sector_changes':[{'item':{'entity_id':'INDUSTRY:TEST'}}],
            'sector_change_total':2}
        class Index:
            def response(self,path):
                if path=='/api/v4/sectors-meta':
                    return {'status':'SOURCE_INCOMPLETE','source_gap':{'classification':'SOURCE_MISSING',
                        'reason_code':'DATED_INDUSTRY_QUERY_MISSING_OR_AMBIGUOUS:2026-10-13',
                        'required_source':'EXACT_DATE_BAO_STOCK_INDUSTRY_QUERY'}}
                return payload
        api=SimpleNamespace(root=Path('G:/codex_tmp/test_temp'),token=token,cache={},
            candidate={'published_sessions':[day],'accepted_trade_date':day,'owners':{day:{'validation_cohort':None}}})
        bff=CoreProductBFFR1(api,None)
        bff._read_index_r2=lambda _:Index()
        bff._rotation_owner_summary=lambda _day:{}
        code,result=bff.get('/api/v4/home',{'trade_date':day,'context_token':token})
        self.assertEqual(code,200)
        self.assertEqual(result['market']['regime_publication_status'],'SOURCE_INCOMPLETE')
        self.assertEqual(result['market']['row']['stress_level'],'UNKNOWN')
        self.assertEqual(result['market']['consumer_disposition'],
            'QUARANTINED_PENDING_DATED_SOURCE_AND_RECOMPUTE')
        self.assertEqual(result['risks'],[])
        self.assertEqual(len(result['focus_risk_events']),1)
        self.assertIsNone(result['counts']['forward']['value'])
        self.assertIsNone(result['counts']['sectors'])
        self.assertEqual(result['sector_source_status'],'SOURCE_INCOMPLETE')
        self.assertEqual(result['sector_source_gap']['reason_code'],
            'DATED_INDUSTRY_QUERY_MISSING_OR_AMBIGUOUS:2026-10-13')
        self.assertEqual(result['rotations'],[])
        self.assertEqual(result['sector_changes'],[])
        self.assertGreater(validate_home_response(result),0)

    def test_indexed_empty_sector_page_preserves_exact_source_gap(self):
        from workbench_service.core_product_bff_r1 import CoreProductBFFR1
        day='2026-10-20'; token='b'*64
        gap={'status':'SOURCE_INCOMPLETE','gap':'DATED_INDUSTRY_QUERY_MISSING_OR_AMBIGUOUS',
             'source_gap':{'classification':'SOURCE_MISSING',
                           'reason_code':'DATED_INDUSTRY_QUERY_MISSING_OR_AMBIGUOUS:2026-10-20'}}
        class Index:
            def response(self,path):
                if path=='/api/v4/context':
                    return {'context':{'trade_date':day},'context_token':token,
                            'production_accepted':False}
                if path=='/api/v4/sectors-meta': return gap
                return None
            def page(self,domain,query,entity=None,sector=None):
                return {'status':'EMPTY_VALID','items':[],'total':0,'offset':0,
                        'limit':30,'has_next':False,'domain':domain,'gap':None}
        api=SimpleNamespace(token=token,candidate={'published_sessions':[day]})
        bff=CoreProductBFFR1.__new__(CoreProductBFFR1)
        bff.api=api; bff._read_index_r2=lambda _day:Index()
        bff._apply_rotation_auto_acceptance=lambda response,_day:response
        result=bff.page('sectors',day,{'trade_date':day,'context_token':token})
        self.assertEqual(result['status'],'SOURCE_INCOMPLETE')
        self.assertEqual(result['source_gap'],gap['source_gap'])
        self.assertEqual(result['items'],[])

    def test_home_quarantines_numeric_sector_cards_when_dated_membership_is_missing(self):
        reason='DATED_INDUSTRY_QUERY_MISSING_OR_AMBIGUOUS:2026-10-13'
        home={'counts':{'stocks':5225,'sectors':400},'rotation_total':27,
            'rotations':[{'entity_id':'INDUSTRY:TEST','fields':{'sector_rs5':{'value':88.0}}}],
            'sector_change_total':27,'sector_changes':[{'item':{'entity_id':'INDUSTRY:TEST'}}],
            'rotation_owner_summary':{'owner_bound':True,'total':400},
            'risk_families':{'SECTOR_ECOLOGY_RISK':{'status':'PARTIAL','value':0.2}},
            'risks':[{'fields':{'risk_family':{'value':'SECTOR_ECOLOGY_RISK'}}}],'gaps':[]}
        meta={'status':'SOURCE_INCOMPLETE','source_gap':{'classification':'SOURCE_MISSING',
            'reason_code':reason,'required_source':'EXACT_DATE_BAO_STOCK_INDUSTRY_QUERY'}}
        result=quarantine_incomplete_sector_home(home,meta)
        self.assertIsNone(result['counts']['sectors'])
        self.assertIsNone(result['rotation_total'])
        self.assertIsNone(result['sector_change_total'])
        self.assertEqual(result['rotations'],[])
        self.assertEqual(result['sector_changes'],[])
        self.assertEqual(result['sector_source_gap']['reason_code'],reason)
        self.assertEqual(result['risk_families']['SECTOR_ECOLOGY_RISK']['status'],'SOURCE_INCOMPLETE')
        self.assertEqual(result['risks'],[])
        self.assertEqual(home['counts']['sectors'],400)

    def test_latest_tdx_membership_fallback_requires_exact_dated_core_pair_reconciliation(self):
        from workbench_service.core_product_bff_r1 import reconcile_latest_tdx_membership, apply_sector_membership_meta
        snapshot={'membership_mode':'TDX_LATEST_MEMBER_RETRO_V1','taxonomy':'TDX_INDUSTRY_CONCEPT',
            'PIT_ELIGIBLE':False,'AS_RECORDED':False,'HISTORICAL_FIRST_AVAILABLE_PROVEN':False,
            'knowledge_lineage':'RECONSTRUCTED_LATEST_MEMBERSHIP','survivorship_bias_risk':True,
            'membership_snapshot_id':'snapshot-derived-from-input','membership_observed_at':'observed-at',
            'member_set_asof':'observed-at'}
        members=[{'sector_id':'INDUSTRY:EXAMPLE','security_id':'SEC-A','identity_status':'MAPPED'},
            {'sector_id':'INDUSTRY:EXAMPLE','security_id':'SEC-OUTSIDE','identity_status':'MAPPED'},
            {'sector_id':'THEME:EXAMPLE','security_id':'SEC-B','identity_status':'MAPPED'}]
        sectors=[{'sector_id':'INDUSTRY:EXAMPLE','member_ids':['SEC-A'],
            'membership_snapshot_id':'snapshot-derived-from-input','membership_mode':'TDX_LATEST_MEMBER_RETRO_V1',
            'member_set_asof':'observed-at','PIT_ELIGIBLE':False},
            {'sector_id':'THEME:EXAMPLE','member_ids':['SEC-B'],
            'membership_snapshot_id':'snapshot-derived-from-input','membership_mode':'TDX_LATEST_MEMBER_RETRO_V1',
            'member_set_asof':'observed-at','PIT_ELIGIBLE':False}]
        bindings=[{'sha256':'a'*64} for _ in range(3)]
        result=reconcile_latest_tdx_membership('input-day',snapshot,members,sectors,
            ['SEC-A','SEC-B'],membership_source=bindings[0],sector_owner=bindings[1],core_owner=bindings[2])
        self.assertEqual(result['status'],'READY_WITH_NON_PIT_FALLBACK')
        self.assertEqual(result['trade_date'],'input-day')
        self.assertEqual(result['sector_count'],2)
        self.assertEqual(result['mapped_relation_count'],2)
        self.assertFalse(result['PIT_ELIGIBLE'])
        self.assertFalse(result['AS_RECORDED'])
        home=apply_sector_membership_meta({'counts':{'sectors':2}},result)
        self.assertEqual(home['sector_source_status'],'READY_WITH_NON_PIT_FALLBACK')
        self.assertEqual(home['sector_membership_basis']['member_set_asof'],'observed-at')
        self.assertEqual(home['counts']['sectors'],2)
        with self.assertRaisesRegex(ValueError,'LATEST_TDX_SECTOR_OWNER_MEMBER_PARITY_FAILED'):
            reconcile_latest_tdx_membership('input-day',snapshot,members,sectors[:1],
                ['SEC-A','SEC-B'],membership_source=bindings[0],sector_owner=bindings[1],core_owner=bindings[2])

    def test_indexed_response_binds_current_formal_head_scope_without_mutating_source(self):
        from workbench_service.core_product_bff_r1 import CoreProductBFFR1
        bff=object.__new__(CoreProductBFFR1)
        bff.api=SimpleNamespace(context=lambda:dict(production_accepted=False,
            read_scope='DEVELOPMENT_CANDIDATE_PREVIEW',formal_head_match=False,
            formal_head_date='2026-10-09',independent_external_acceptance=False))
        indexed={'context':{'read_scope':'USER_AUTHORIZED_OPERATIONAL_DAILY',
                            'formal_head_match':True,'production_accepted':True},
                 'production_accepted':True,'context_token':'candidate-token'}
        response=bff._bind_live_head_scope(indexed)
        self.assertFalse(response['production_accepted'])
        self.assertFalse(response['context']['formal_head_match'])
        self.assertEqual(response['context']['formal_head_date'],'2026-10-09')
        self.assertEqual(response['context']['read_scope'],'DEVELOPMENT_CANDIDATE_PREVIEW')
        self.assertTrue(indexed['production_accepted'])
        self.assertTrue(indexed['context']['formal_head_match'])

    def test_dated_product_envelope_separates_snapshot_and_historical_data_context(self):
        from workbench_service.core_product_bff_r1 import CoreProductBFFR1
        bff=object.__new__(CoreProductBFFR1)
        bff.api=SimpleNamespace(token='snapshot-token',candidate={
            'accepted_trade_date':'2026-10-21',
            'owners':{'2026-10-20':{'core':{'sha256':'dated-owner-sha'}}}})
        bff._get_dated_product=lambda _path,_query:(200,{
            'context_token':'snapshot-token',
            'context':{'trade_date':'2026-10-20','accepted_trade_date':'2026-10-20'},
            'items':[{'trade_date':'2026-10-20'}]})
        code,payload=bff.get('/api/v4/stocks',{
            'trade_date':'2026-10-20','context_token':'snapshot-token'})
        self.assertEqual(code,200)
        self.assertEqual(payload['snapshot_context_token'],'snapshot-token')
        self.assertEqual(payload['snapshot_context_trade_date'],'2026-10-21')
        self.assertEqual(payload['data_trade_date'],'2026-10-20')
        self.assertEqual(payload['dated_owner_bindings'],{'core':{'sha256':'dated-owner-sha'}})

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

    def test_sector_rotation_filter_uses_dedicated_query_and_preserves_unknown(self):
        where_none, args_none, *_ = query_parts('sectors', {'rotation': 'NONE'})
        where_unknown, args_unknown, *_ = query_parts('sectors', {'rotation': 'UNKNOWN'})
        self.assertEqual(args_none, ['NONE'])
        self.assertEqual(args_unknown, ['UNKNOWN'])
        self.assertIn("output_state", str(where_none))
        self.assertIn("output_state", str(where_unknown))
        app = Path(__file__).resolve().parents[1] / 'src/workbench_service/static/core-product-r1/app.js'
        ui = app.read_text(encoding='utf-8')
        self.assertIn("const stateFilterParam=domain==='sectors'?'rotation':'state'", ui)
        self.assertIn("params.get(stateFilterParam)", ui)
        self.assertIn("if(domain==='sectors')params.delete('state')", ui)
        self.assertIn("sectorSourceIncomplete=d.sector_source_status==='SOURCE_INCOMPLETE'", ui)
        self.assertIn("domain==='sectors'&&sectorSourceIncomplete?'来源不足'", ui)
        self.assertIn("sectorSourceIncomplete?[]:await Promise.all", ui)
        self.assertIn("按日板块来源不足，轮动数据已隔离。", ui)
        self.assertIn("fact.status==='SOURCE_INCOMPLETE'?'来源不足'", ui)


if __name__ == '__main__':
    unittest.main()
