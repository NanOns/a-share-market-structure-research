from workbench_service.research_bff import ResearchBFF


def test_sector_overlap_page_does_not_offset_identity_lookup(monkeypatch, tmp_path):
    class Reader:
        def query(self, domain, query, **kwargs):
            if kwargs.get('entity'):
                assert query == {'context_token': 'accepted'}
                return {'total': 1, 'items': [{'entity_id': 'THEME:880572'}]}
            return {}

    bff = ResearchBFF(tmp_path)
    monkeypatch.setattr(bff, 'current', lambda: Reader())
    monkeypatch.setattr('workbench_service.research_bff.sector_view',
        lambda r, item, kind, query: {'entity': item['entity_id'], 'offset': query['offset']})
    code, payload = bff.get('/api/v4/sectors/THEME:880572/overlap',
        {'context_token': 'accepted', 'limit': '200', 'offset': '200'})
    assert code == 200
    assert payload == {'entity': 'THEME:880572', 'offset': '200'}
