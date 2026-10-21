from workbench_analysis.r6_candidate_market_stress import (
    adapt_candidate_trend_reference, candidate_breadth_formula_comparison,
)
from workbench_analysis.r6_reason_attribution import evaluate_d0_source_seal
from workbench_analysis.r8_candidate_append_comparator import compare_candidate_append
from workbench_analysis.r8_candidate_derived_cache import cache_path, read_snapshot, write_snapshot


def test_s02_keeps_distinct_formula_values_and_candidate_semantics():
    result = candidate_breadth_formula_comparison([(0.1, -0.1), (0.0, 0.1)], boundary=0.05)
    assert result['contract_id'] == 'S02_BREADTH_FORMULA_COMPARISON_R1'
    assert result['positive_indicator']['value'] == 0
    assert result['signed']['value'] == 0.5
    assert result['adjudication_status'] == 'BUSINESS_SEMANTICS_PENDING'


def test_s02_trend_adapter_requires_same_date_time_permission_and_series_identity():
    ref = dict(trade_date='2026-10-21', series_id='IDX-A', price_basis_id='QFQ-T0',
        source_sha256='a'*64, market_calendar_id='CAL-1', index_close=12,
        index_ma20=11, index_ma20_t_minus_5=10, source_available_at='2026-10-21T15:01:00+08:00',
        knowledge_cutoff='2026-10-21T15:05:00+08:00', time_role='AS_OF_T0',input_publication_id='PUB-1',
        permission_chain=dict(permission_id='PERM-1',owner_id='OWNER-1',role='candidate_reader',
            permission='READ_CANDIDATE',source_binding_sha256='a'*64,input_publication_id='PUB-1',chain_sha256='c'*64))
    result=adapt_candidate_trend_reference(ref,t0='2026-10-21',knowledge_cutoff='2026-10-21T15:10:00+08:00')
    assert result['value']=='STRONG' and result['quality']=='OBSERVED'
    assert adapt_candidate_trend_reference({**ref,'trade_date':'2026-10-20'},t0='2026-10-21',
        knowledge_cutoff='2026-10-21T15:10:00+08:00')['value']=='UNKNOWN'
    assert adapt_candidate_trend_reference({**ref,'source_available_at':'2026-10-21T15:11:00+08:00'},
        t0='2026-10-21',knowledge_cutoff='2026-10-21T15:10:00+08:00')['value']=='UNKNOWN'
    assert adapt_candidate_trend_reference({**ref,'permission_chain':{}},t0='2026-10-21',
        knowledge_cutoff='2026-10-21T15:10:00+08:00')['value']=='UNKNOWN'
    assert adapt_candidate_trend_reference({k:v for k,v in ref.items() if k!='index_ma20'},t0='2026-10-21',
        knowledge_cutoff='2026-10-21T15:10:00+08:00')['value']=='UNKNOWN'


def test_d0_seal_is_driven_by_explicit_clock_and_permission_facts():
    cutoff='2026-10-21T15:05:00+08:00'
    evidence=dict(source_available_at='2026-10-21T15:00:00+08:00',knowledge_cutoff=cutoff,
        input_publication_id='PUB-1',time_role='AS_OF_T0',permission_chain_proven=True,
        source_sha256='b'*64,trade_date='2026-10-21',permission_chain=dict(permission_id='PERM-1',
            owner_id='OWNER-1',role='candidate_reader',permission='READ_CANDIDATE',
            source_binding_sha256='b'*64,input_publication_id='PUB-1',chain_sha256='c'*64))
    assert evaluate_d0_source_seal(evidence,knowledge_cutoff=cutoff)['status']=='CANDIDATE_SEAL_PROVEN'
    assert evaluate_d0_source_seal({**evidence,'source_available_at':'2026-10-21T15:06:00+08:00'},
        knowledge_cutoff=cutoff)['status']=='SEAL_TIME_REJECTED'
    assert evaluate_d0_source_seal({**evidence,'permission_chain_proven':False},
        knowledge_cutoff=cutoff)['status']=='SEAL_PERMISSION_UNPROVEN'
    assert evaluate_d0_source_seal({**evidence,'trade_date':'2026-10-22'},
        knowledge_cutoff=cutoff)['status']=='SEAL_TIME_REJECTED'
    assert evaluate_d0_source_seal({'source_sha256':'b'*64},knowledge_cutoff=cutoff)['status']=='HISTORICAL_SEAL_NOT_PROVEN'


def test_candidate_snapshot_cache_is_atomic_content_and_identity_bound(tmp_path):
    identity={'token':'candidate-token','inputs':[{'sha256':'c'*64,'bytes':10}], 'version':'r1'}
    payload={'rows':[{'id':'x','value':1}]}
    path=cache_path(tmp_path,'priority',identity)
    write_snapshot(path,identity,payload)
    assert read_snapshot(path,identity)==payload
    assert read_snapshot(path,{**identity,'token':'other'}) is None
    path.write_text('{"payload": {"rows": []}}',encoding='utf-8')
    assert read_snapshot(path,identity) is None


def test_s06p_comparator_separates_formal_and_non_pit_candidate_predecessors():
    reference={'business_values':{'stocks':5225,'sectors':400},'historical_identity':{'episode':'old-1'}}
    candidate={**reference}
    ok=compare_candidate_append(formal_predecessor={'accepted':True,'head_sha256':'d'*64},
        candidate_predecessor={'accepted':False,'evidence_class':'NON_PIT'},reference_snapshot=reference,
        candidate_snapshot=candidate,target_session='2026-10-15',compute_sessions=['2026-10-15'],
        source_bindings=[{'owner':'core','sha256':'e'*64}])
    assert ok['status']=='PASS' and ok['candidate_predecessor_used_as_formal'] is False
    rejected=compare_candidate_append(formal_predecessor={'accepted':False,'head_sha256':'d'*64},
        candidate_predecessor={'accepted':False,'evidence_class':'NON_PIT'},reference_snapshot=reference,
        candidate_snapshot=candidate,target_session='2026-10-15',compute_sessions=['2026-10-15'],
        source_bindings=[{'owner':'core','sha256':'e'*64}])
    assert rejected['status']=='FAIL_CLOSED'
    revised=compare_candidate_append(formal_predecessor={'accepted':True,'head_sha256':'d'*64},
        candidate_predecessor={'accepted':False,'evidence_class':'NON_PIT'},reference_snapshot=reference,
        candidate_snapshot=candidate,target_session='2026-10-15',compute_sessions=['2026-10-15'],
        source_bindings=[{'owner':'core','sha256':'e'*64}],revisions_detected=True)
    assert 'REVISION_REQUIRES_RANGE_REPAIR' in revised['errors']
