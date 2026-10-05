"""Explicit negative vectors; these are never historical population inputs."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from workbench_analysis.fep_e1.contracts import digest
from workbench_analysis.fep_e2.historical_dataset import (LINEAGE,admissible,feature_cutoff,freeze_window,
    verify_window,write_gzip,scoped_policy,verify_label,verify_stage_order)
from workbench_analysis.fep_e2.historical_owners import RecordStore
from workbench_analysis.fep_e2.support import diagnostics,discover,gate,BASE
from workbench_analysis.fep_e2.conditional import baseline
from tests.fep_e2.test_conditional import fixture,POLICY,CONTRACT,NOW


def real_shape():return dict(LINEAGE,source_kind='REAL_ACCEPTED_HISTORICAL_SOURCE')
def window_input():return dict(source_bindings={'source':'bound'},sessions=['2026-09-01','2026-09-02','2026-09-03'],
    warmup_sessions=1,maximum_enabled_horizon=1,owner_capability='ACCEPTED_OWNER')


def test_reject_synthetic():
    r=real_shape();r['source_kind']='ENGINEERING_SYNTHETIC'
    with pytest.raises(ValueError,match='SYNTHETIC'):admissible(r)


def test_reject_one_date_117_rows():
    d=fixture();rows=[dict(d['rows'][0],observation_id=str(i),entity_id=str(i)) for i in range(117)]
    p=deepcopy(POLICY);p['values'].update(rows=10,dates=2)
    assert gate(rows,rows,p)[0]=='THIN_DATES'


def test_reject_return_selected_window():
    d=window_input();d['weighted_mean']=.2
    with pytest.raises(ValueError,match='WINDOW_OUTCOME'):freeze_window(d)


def test_reject_future_feature():
    with pytest.raises(ValueError,match='FUTURE'):feature_cutoff([{'date':'2026-09-03'}],'2026-09-02')


def test_reject_label_revision_digest():
    out=dict(R_N=.2,outcome_revision_id='v1');row=dict(selected_label_digest=digest(.1),outcome_revision_id='v1')
    with pytest.raises(ValueError,match='LABEL_REVISION'):verify_label(row,out)


@pytest.mark.parametrize('flag',['FIRST_OBSERVED','REAL_OOS','AS_RECORDED'])
def test_reject_availability_overclaim(flag):
    r=real_shape();r[flag]=True
    with pytest.raises(ValueError,match='LINEAGE'):admissible(r)


@pytest.mark.parametrize('key,value',[('horizon',20),('target','FIRST_EXIT'),('signal_type','DAILY'),
    ('observation_scope','FEP_STOCK_DAILY_CORE'),('feature_variant','SUPPLEMENTAL'),('evidence_origin','FIRST_OBSERVED')])
def test_reject_policy_scope_reuse(key,value):
    p=deepcopy(POLICY);p['applicability'][key]=value
    d=fixture()
    with pytest.raises(ValueError,match='APPLICABILITY'):baseline(d,d['denominator'][0],p,CONTRACT,NOW)


def test_unavailable_representation_is_not_zero():
    d=fixture();diag=diagnostics(d['denominator'],d['rows'])
    assert diag['representativeness_total_variation']['sector'] is None
    assert diag['dimension_status']['sector']=='UNAVAILABLE_NOT_GATED'


def test_unavailable_condition_cannot_be_formal():
    d=fixture();p=deepcopy(POLICY);p['representation_dimensions']={'regime':'UNAVAILABLE_NOT_GATED','sector':'UNAVAILABLE_NOT_GATED'}
    a=baseline(d,d['denominator'][0],p,CONTRACT,NOW)
    assert a['selected_level']=='L1' and all(t['state']=='NOT_EVALUABLE_CONDITION_UNAVAILABLE' for t in a['backoff_trace'][:3])


def test_reject_post_statistics_freeze():
    with pytest.raises(ValueError,match='STAGE_ORDER'):verify_stage_order('2026-10-05T00:00:00Z','2026-10-05T00:01:00Z',
        '2026-10-05T00:03:00Z','2026-10-05T00:02:00Z')


def test_reject_performance_derived_policy():
    d=fixture();discovery=discover(d['denominator'],d['rows']);discovery['positive_rate']=1
    with pytest.raises(ValueError,match='PERFORMANCE'):scoped_policy(discovery,{},NOW)


def test_deterministic_rebuild(tmp_path):
    d=window_input();a=freeze_window(d);assert a==freeze_window(d)
    assert write_gzip(tmp_path/'a.gz',[a])==write_gzip(tmp_path/'b.gz',[a])
    changed=dict(a,end='2026-09-02')
    with pytest.raises(ValueError,match='RESELECTED'):verify_window(changed,d)


def test_current_heads_immutable_and_e2_isolated():
    root=Path(__file__).resolve().parents[2];heads=list((root/'data/v4').glob('*HEAD*.json'))
    protected=heads+[root/'config/fep_feature_owner_contract_v1.json',root/'config/v4_15_fep_label_time_authority_v1.json',
        root/'config/fep_e2_support_policy_v1.json']
    before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    store=RecordStore();ref=store.append('test-only','negative',{'value':1})
    store.read(ref)['value']=2
    assert store.read(ref)=={'value':1}
    with pytest.raises(ValueError,match='MUTATION'):store.append('test-only','negative',{'value':2})
    assert before=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}


def test_owner_business_ast_exact():
    from src.v4.confirmation_d2_candidate_r5 import adapter_ast_evidence
    evidence=adapter_ast_evidence()
    assert all(x['normalized_business_AST_exact'] for x in evidence['business_AST_comparisons'].values())


def test_historical_price_transport_never_backdates_availability():
    from workbench_analysis.fep_e2.historical_labels import HistoricalPriceSource
    slots=[dict(date=d,price_basis='FIXED',adjustment_source_revision='revision',has_actual_bar=True,
        identity_verified=True,close=10,high=11,low=9) for d in ('2026-09-01','2026-09-02')]
    source=HistoricalPriceSource('test-only',slots,'2026-09-01',{'sha256':'negative-only'},NOW)
    assert source.read('test-only','2026-09-02','2026-09-02','2026-09-02')['available_at']==NOW
    assert source.read('test-only','2026-09-02','2026-09-02','2026-09-02')['first_available_at_target_proven'] is False
    with pytest.raises(ValueError,match='FUTURE'):source.read('test-only','2026-09-02','2026-09-02','2026-09-01')


def test_historical_basis_mismatch_fails_closed_in_actual_owner():
    from workbench_analysis.fep_e2.historical_labels import HistoricalPriceSource
    from workbench_analysis.v4_15_settlement import price_path
    slots=[dict(date='2026-09-01',price_basis='FIXED',adjustment_source_revision='v1',has_actual_bar=True,
                identity_verified=True,close=10,high=11,low=9),
           dict(date='2026-09-02',price_basis='FIXED',adjustment_source_revision='v2',has_actual_bar=True,
                identity_verified=True,close=12,high=13,low=11)]
    source=HistoricalPriceSource('test-only',slots,'2026-09-01',{'sha256':'negative-only'},NOW)
    row=source.read('test-only','2026-09-02','2026-09-02','2026-09-02')
    assert price_path(10,[row],'2026-09-02')['outcome_status']=='ADJUSTMENT_UNKNOWN'
