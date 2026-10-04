"""R31R1 independent counterfactuals; all receipts are design simulations."""
from copy import deepcopy
import pytest
from tests.test_v4_22_independent_audit_contract import C, ROOT, ledger, evaluate, future_simulation
from reports.r31.audit_oracle import digest, final_verdict, validate_contract


def closed_future():
    c,items,gates=future_simulation()
    closures={}
    for item in c['open_items']:
        if item['item_id']=='OPEN-09': continue
        r=dict(item_id=item['item_id'],capability_scope=item['capability_scope'],explicit_disposition='INDEPENDENTLY_DISPOSED',exact_evidence=[dict(path='SIM_ONLY',sha256='SIM_ONLY')],authority=item['authority'],date_source='SIM_20261005_INDEPENDENT_AUTHORITY',independent_recheck=True)
        closures[item['item_id']]=r
        c['open_item_closure_bindings'][item['item_id']]=dict(item_id=item['item_id'],capability_scope=item['capability_scope'],canonical_sha256=digest(r),authority=item['authority'])
    return c,items,gates,closures


@pytest.mark.parametrize('vector',range(1,7),ids=[f'R31R1-FINAL-{i:02}' for i in range(1,7)])
def test_final(vector):
    c,items,gates,closures=closed_future()
    if vector==1: closures.pop('OPEN-01')
    if vector==2: closures['OPEN-01'].pop('exact_evidence')
    if vector==3: closures['OPEN-01']['capability_scope']=['STOCK_CORE']
    if vector==4: c['open_item_closure_bindings']['OPEN-01']['canonical_sha256']='WRONG'
    if vector==6: closures.pop('OPEN-10')
    r=final_verdict(c,items,gates,dict(status='PASS'),open_item_receipts=closures)
    assert (r['formula_result']=='V4_22_FINAL_PASS') == (vector==5)
    assert r['acceptance_granted'] is False and r['production_grant'] is False
    assert c['open_items'][8]['current_status']=='OPEN_NONBLOCKING_DEBT'


@pytest.mark.parametrize('vector',range(1,9),ids=[f'R31R1-REFINT-{i:02}' for i in range(1,9)])
def test_parent(vector):
    v=ledger()
    if vector==1: v['events'][0]['source_publication']='OTHER'
    if vector==2: v['events'][0]['source_digest']='OTHER'
    if vector==3: v['sessions'][0].pop('market_session_id')
    if vector==4:
        for k in ('trade_date','publication_id','session_receipt_id'): v['sessions'][0].pop(k)
    if vector==5: v['events'][0]['T0']='2026-10-04'
    if vector==6: v['outcomes'][0]['source_publication']='OTHER'
    if vector==7: v['sessions'][0].update(projection_evaluable=False,projection_evaluable_reason='SIM_NOT_EVALUABLE')
    if vector==8:
        for name in ('sessions','events','outcomes'):
            v[name][0].update(evidence_lane='PRODUCTION_REAL',execution_mode='PRODUCTION')
    r=evaluate(v)
    assert r['status']==('PASS_DESIGN_ONLY' if vector==7 else 'BLOCKED_AFFECTED_SCOPE')
    if vector==7: assert r['design_countable_sessions']==0


@pytest.mark.parametrize('vector',range(1,7),ids=[f'R31R1-AUTH-{i:02}' for i in range(1,7)])
def test_authority(vector):
    c=deepcopy(C)
    if vector==1: c['audit_items'][0]['authority'][0]['sha256']='WRONG'
    if vector==2: c['audit_items'][0]['authority'][0]['path']='../OUTSIDE'
    if vector==3: c['open_items'][0]['evidence_refs'][0]['sha256']='WRONG'
    if vector==4: c['audit_items'][0]['authority']=deepcopy(c['audit_domains'][2]['authority_bindings'][0])
    if vector==5: c['audit_items'][0]['authority'][0]['contract_id']='WRONG'
    if vector==6: c['open_items'][0]['authority']['sha256']='WRONG'
    assert 'ITEM_AUTHORITY_BINDING_INVALID' in validate_contract(c,ROOT)


def test_outcome_due_date_is_not_processing_date():
    v=ledger(); v['outcomes'][0]['due_date']='2026-09-30'
    assert evaluate(v)['status']=='PASS_DESIGN_ONLY'
