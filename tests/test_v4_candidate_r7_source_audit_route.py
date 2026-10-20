def test_pg_candidate_cohort_includes_trade_date_scoped_r7_audit(monkeypatch, tmp_path):
    import workbench_db.forward_r7_store as store_module
    from workbench_service.research_bff import ResearchBFF

    expected = dict(contract_id='V4_FORWARD_CANDIDATE_SOURCE_AUDIT_READ_R1',contract_version='1.0.0',
                    status='READY', items=[dict(trade_date='2026-09-30', groups=[])],
                    total=1, binding='CANDIDATE_TRADE_DATE_ONLY_INDEPENDENT_R7_PUBLISHED_FACT',
                    evidence_class='RETROSPECTIVE_RESEARCH', strict_t0_pit=False)
    calls = []

    def audit(cls, root, *, trade_date, limit, offset):
        calls.append((root, trade_date, limit, offset))
        return expected

    monkeypatch.setattr(store_module.ForwardR7Store, 'read_candidate_source_audit', classmethod(audit))

    class Reader:
        is_pg_candidate = True
        context = dict(source_mode='PG_CANDIDATE_SNAPSHOT', accepted_trade_date='2026-09-30')
        def query(self, route, query):
            return dict(status='READY', items=[dict(entity_id='candidate-1')], total=1)
        def envelope(self, **kwargs):
            return dict(**kwargs)

    code, payload = ResearchBFF(tmp_path).get_with_reader(
        'candidates/cohort', {'limit':'7','offset':'3'}, Reader())

    assert code == 200
    assert calls == [(tmp_path, '2026-09-30', 7, 3)]
    assert payload['candidate_research']['r7_source_audit'] == expected
    assert payload['r7_source_audit'] == expected
    assert payload['PIT_ELIGIBLE'] is False
    assert payload['production_accepted'] is False


def test_candidate_r7_audit_rejects_invalid_date_without_pg_access(tmp_path):
    import pytest
    from workbench_db.forward_r7_store import ForwardR7Store

    with pytest.raises(ValueError, match='INVALID_CANDIDATE_TRADE_DATE'):
        ForwardR7Store.read_candidate_source_audit(tmp_path, trade_date='2026-02-30')


def test_candidate_r7_audit_rejects_unbounded_paging_without_pg_access(tmp_path):
    import pytest
    from workbench_db.forward_r7_store import ForwardR7Store

    with pytest.raises(ValueError, match='INVALID_QUERY_BOUND'):
        ForwardR7Store.read_candidate_source_audit(tmp_path, trade_date='2026-09-30', limit=1000)
