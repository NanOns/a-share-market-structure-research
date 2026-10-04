"""Synthetic supplied-ledger assertions, never settlement runtime tests."""
import json
from pathlib import Path
import pytest
from reports.r30.design_ledger import CAPS,LANES,PARTITION,fixture,readback,scenario,validate,vector_result

ROOT=Path(__file__).resolve().parents[1]
C=json.loads((ROOT/'config/v4_21_continued_forward_observation_contract_v1.json').read_text(encoding='utf8'))


@pytest.mark.parametrize('i',range(1,21),ids=lambda i:f'F21-{i:02}')
def test_twenty_design_vectors(i):
    r=vector_result(i)
    assert r['actual_real_rows_written']==0 and r['production_grant'] is False
    assert r['status']==C['vectors'][i-1]['expected_status']
    if i in (8,18,19):
        assert {8:'DUPLICATE_ORIGINAL_ENROLLMENT',18:'OBSERVATION_HEAD_CAS_CONFLICT',19:'SAME_DAY_OUTCOME_FEEDBACK_FORBIDDEN'}[i] in r['errors']; return
    rows=r['breakdown']; first=rows[0]
    if i==1: assert first['real_accepted_sessions']==first['events']==first['observed']==1
    if i in (2,3,4): assert sum(x['real_accepted_sessions']+x['events']+x['observed'] for x in rows)==0
    if i in (5,6): assert first['session_denominator']==2 and first['real_accepted_sessions']==1 and first['consecutive_accepted_sessions']==0
    if i in (1,5,6):
        session=scenario(i)['sessions'][-1]
        assert session['native_session_status']==('MISSED_OBSERVATION_SLOT' if i==5 else 'ACCEPTED_ON_TIME')
        assert session['projection_evaluable']==(i==1)
        if i==6: assert session['missed_reason'] is None and session['projection_evaluable_reason']
    if i==7: assert first['events']==first['hidden_eligible']==1
    if i==9: assert first['observed']==0 and first['pending']==first['due_denominator']==1
    if i==10: assert first['observed']==first['pending']==0 and first['right_censored']==1 and 'failure' not in first
    if i==11: assert first['due_denominator']==first['observed']==1 and r['first_observed_revision_view'][0]['revision']==1 and r['latest_corrected_revision_view'][0]['revision']==2
    if i==12: assert len(rows)==2 and sum(x['session_denominator'] for x in rows)==2 and all(x['consecutive_accepted_sessions']==1 for x in rows)
    if i==13:
        stock=[x for x in rows if x['capability']=='STOCK_CORE']; sector=[x for x in rows if x['capability']=='SECTOR_STAGE']
        assert len(stock)==2 and all(x['consecutive_accepted_sessions']==1 for x in stock)
        assert len(sector)==1 and sector[0]['consecutive_accepted_sessions']==2
    if i==14: assert not r['sector_counts_borrowed'] and r['sector_real_events']==0
    if i in (15,16,20):
        assert {x['evidence_lane'] for x in rows}=={'SHADOW_REAL','PRODUCTION_REAL'}
        assert all(x['events']==x['observed']==1 for x in rows)
        assert len({(x['capability'],x['model_contract_id'],x['parameter_digest'],x['state_lineage_id']) for x in rows})==1
    if i==17: assert r['identical_rerun_same_digest'] and first['events']==first['due_denominator']==1


def test_current_zero_and_gate_owners_read_only():
    assert C['current_state']['REAL_SHADOW_OBSERVATIONS']==C['current_state']['PIT_OBSERVED_REAL_SAMPLES']==0
    assert C['current_state']['REAL_CONTINUED_FORWARD_OBSERVATION']=='NOT_STARTED'
    assert not any(C['current_state']['production_permission'].values())
    assert C['receipt_schema']['current_real_receipt'] is None
    assert C['implementation_entry']['receipts']==[None]*4 and C['implementation_entry']['status']=='BLOCKED_WAIT_REAL_OBSERVATION'
    assert C['gate_readback']['read_only'] and not C['gate_readback']['auto_grant']
    assert C['gate_readback']['owners']['production_permission']=='V4_19'


def test_owner_native_statuses_and_immutable_contract_refs():
    for ledger in ('session_ledger','event_cohort_ledger','due_outcome_ledger'):
        assert set(C[ledger]['identity_key']) <= set(C[ledger]['required'])
    owner=json.loads((ROOT/'config/v4_15_outcome_status_contract_v1.json').read_text(encoding='utf8'))
    assert C['right_censor']['native_statuses']==owner['states']
    assert 'MATURED_DATA_MISSING' in C['right_censor']['preserve_native']
    assert C['continuity']['lanes_remain_distinct'] and not C['recovery']['implemented']
    assert C['partition_keys']==list(PARTITION) and set(C['evidence_lanes'])==set(LANES)


@pytest.mark.parametrize('ledger,field',[('sessions','market_session_id'),('events','enrollment_id'),('outcomes','due_id')])
def test_missing_ledger_identity_fails_closed(ledger,field):
    v=fixture(); del v[ledger][0][field]
    assert readback(v)['errors']==['LEDGER_SCHEMA_INCOMPLETE']


def test_identical_rows_do_not_inflate_denominators_and_conflicts_rejected():
    ordered=scenario(5); ordered['sessions'].reverse()
    assert readback(ordered)['breakdown'][0]['consecutive_accepted_sessions']==0
    v=fixture()
    for name in ('sessions','events','outcomes'): v[name].append(dict(v[name][0]))
    r=readback(v)['breakdown'][0]
    assert r['session_denominator']==r['events']==r['due_denominator']==1
    v['outcomes'][1]['source_identity']='CONFLICT'
    assert 'CONFLICTING_OUTCOME_REVISION' in validate(v)


def test_native_missing_is_not_promoted_observed_or_censor():
    mismatch=fixture(); mismatch['events'][0]['publication_capability']='SECTOR_STAGE'
    assert 'PUBLICATION_CAPABILITY_MISMATCH' in validate(mismatch)
    v=fixture(); v['outcomes'][0]['native_status']='MATURED_DATA_MISSING'
    assert 'NATIVE_STATUS_CANNOT_PROMOTE_OBSERVED' in validate(v)
    v['outcomes'][0]['status']='PENDING_SOURCE_UNAVAILABLE'
    r=readback(v)['breakdown'][0]
    assert r['pending']==1 and r['observed']==r['right_censored']==0
    assert r['native_status_breakdown']=={'MATURED_DATA_MISSING':1}
