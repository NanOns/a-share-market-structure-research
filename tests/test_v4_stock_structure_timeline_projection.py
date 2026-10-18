from workbench_service.stock_views import timeline


class Reader:
    context = {'trade_date': '2026-09-30'}

    def envelope(self, **payload):
        return payload


def cell(value, quality='KNOWN', reason=None):
    return {'value': value, 'quality': quality, 'reason': reason}


def test_owner_timeline_known_empty_is_empty_valid():
    result = timeline(Reader(), {'fields': {
        'structure_events': cell([]),
        'anchor_view_asof_t': cell(None, reason='NO_ACTIVE_ANCHOR'),
    }}, {})
    assert result['status'] == 'EMPTY_VALID'
    assert result['items'] == []
    assert result['owner_specific_debt'] == []


def test_owner_timeline_emits_bound_events_and_anchor():
    event = {'event_id': 'e1', 'event_type': 'BULLISH_IMPULSE', 'created_trade_date': '2026-09-30'}
    anchor = {'anchor_id': 'a1', 'observation_trade_date': '2026-09-30'}
    result = timeline(Reader(), {'fields': {
        'structure_events': cell([event]),
        'anchor_view_asof_t': cell(anchor),
    }}, {})
    assert result['status'] == 'READY'
    assert [row['kind'] for row in result['items']] == ['STRUCTURE_EVENT', 'ANCHOR']


def test_owner_timeline_keeps_unknown_anchor_debt():
    result = timeline(Reader(), {'fields': {
        'structure_events': cell([]),
        'anchor_view_asof_t': cell(None, 'UNKNOWN', 'OWNER_PROJECTION_UNRESOLVED'),
    }}, {})
    assert result['status'] == 'SOURCE_INCOMPLETE'
    assert result['owner_specific_debt'] == [{
        'field': 'anchor_view_asof_t', 'owner': 'V4_12', 'reason': 'OWNER_PROJECTION_UNRESOLVED',
    }]
