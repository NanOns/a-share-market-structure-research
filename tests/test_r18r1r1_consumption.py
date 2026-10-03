"""Adversarial pre-call argument, field projection and ordering checks."""
import json
from pathlib import Path
from copy import deepcopy
import pytest
from scripts.v4_14_consumption_oracle_r18r1r1 import ConsumptionOracle,read,checksum
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def sample():
    gate=json.loads((ROOT/'reports/r18r1r1a/completion_gate_r2.json').read_bytes())
    return ConsumptionOracle(ROOT),read(ROOT,gate['proof'])

def test_field_precise_preexecution_proof(sample):
    o,m=sample;assert o.manifest(ROOT,m)
    assert len(m['output']['edge_receipts'])==30
    assert all('edge_inputs' not in node for node in m['output']['node_records'].values())

@pytest.mark.parametrize('mutation',[
 'F0_D1_receipt_present_but_D1_argument_unbound','D0_EVENT_receipt_present_but_event_argument_unbound',
 'F0_A_whole_node_substituted_for_base_seed_primitives','F0_C_whole_node_substituted_for_stock_core',
 'A_C_whole_node_substituted_for_base_seed_raw','D0_D2_wrong_confirmation_projection','C_D2_wrong_stock_raw_projection',
 'consumer_argument_changed_after_receipt','receipt_changed_to_match_posthoc_echo','precall_envelope_created_after_output','degraded_edge_fabricates_known_value'])
def test_mandatory_consumption_perturbations(sample,mutation):
    o,original=sample;m=deepcopy(original);out=m['output'];nodes=out['node_records'];rows=out['edge_receipts']
    args=lambda name:nodes[name]['invocation']['invocation_input']
    if mutation=='F0_D1_receipt_present_but_D1_argument_unbound':args('D1').pop('core_facts')
    elif mutation=='D0_EVENT_receipt_present_but_event_argument_unbound':args('EVENT_DIFF').pop('confirmation_facts')
    elif mutation=='F0_A_whole_node_substituted_for_base_seed_primitives':args('A')['seed_facts']=nodes['F0']['output']
    elif mutation=='F0_C_whole_node_substituted_for_stock_core':args('C')['stock_core']=nodes['F0']['output']
    elif mutation=='A_C_whole_node_substituted_for_base_seed_raw':args('C')['base_seed_raw']=nodes['A']['output']
    elif mutation=='D0_D2_wrong_confirmation_projection':args('D2')['values']['CONFIRMED']=nodes['D0']['output']
    elif mutation=='C_D2_wrong_stock_raw_projection':args('D2')['values']['PREWATCH']=nodes['C']['output']
    elif mutation=='consumer_argument_changed_after_receipt':args('D1')['core_facts']['prior_separated_sessions']=999
    elif mutation=='receipt_changed_to_match_posthoc_echo':
        r=next(r for r in rows if r['consumer']=='A');nodes['A']['edge_inputs']={r['edge_id']:nodes['F0']['output']};r['consumer_input_ref']['pointer']='/node_records/A/edge_inputs/'+r['edge_id'];r['consumer_argument_digest']=checksum(nodes['F0']['output']);r['consumer_input_digest']=r['consumer_argument_digest']
    elif mutation=='precall_envelope_created_after_output':nodes['D1']['invocation']['prepared_sequence']=nodes['D1']['output_sequence']+1
    elif mutation=='degraded_edge_fabricates_known_value':
        r=next(r for r in rows if r['status']=='DEGRADED_ACCEPTED_CAPABILITY');args(r['consumer'])['capabilities'][r['edge_id']].update(value=True,quality='KNOWN')
    with pytest.raises((ValueError,KeyError)):o.edges(ROOT,m)

@pytest.mark.parametrize('mutation',['missing_B0','missing_B2','missing_membership','missing_D1_previous','wrong_owner','wrong_time_role','duplicate_edge','unexpected_edge','wrong_projection','unbound_D0_lineage'])
def test_retained_edge_perturbations(sample,mutation):
    o,m=sample;m=deepcopy(m);rows=m['output']['edge_receipts']
    if mutation.startswith('missing_'):
        predicate={'missing_B0':lambda r:r['producer']=='B0','missing_B2':lambda r:r['producer']=='B2','missing_membership':lambda r:r['producer']=='MEMBERSHIP','missing_D1_previous':lambda r:r['producer']==r['consumer']=='D1'}[mutation];rows.remove(next(r for r in rows if predicate(r)))
    elif mutation=='wrong_owner':rows[0]['owner_head_ref']=rows[-1]['owner_head_ref']
    elif mutation=='wrong_time_role':rows[0]['time_role']='T_MINUS_1'
    elif mutation=='duplicate_edge':rows.append(deepcopy(rows[0]))
    elif mutation=='unexpected_edge':rows[0]['edge_id']='0'*64
    elif mutation=='wrong_projection':rows[0]['producer_payload_ref']['pointer']='/node_records/F0/output'
    elif mutation=='unbound_D0_lineage':m['output']['node_records']['D0']['invocation']['invocation_input']['projection']['replay_prewatch_lineage']['value']='FALSE'
    with pytest.raises((ValueError,KeyError)):o.edges(ROOT,m)

def test_actual_callable_reads_persisted_envelope_before_output(tmp_path):
    from workbench_analysis.v4_14_precall_runtime import Invocations
    from workbench_analysis.v4_14_authority import ReplayAuthority
    from workbench_analysis.v4_14_replay_io import ref
    a=ReplayAuthority(ROOT);date='2026-09-29';e=dict(target_trade_date=date,target_revision='r1',previous_market_session=a.previous(date),cutoff=date+'T16:00:00+00:00',owner_inputs=dict(consumption_mapping_ref=ref(ROOT,'config/v4_14_precall_consumption_mapping_r18r1r1_v1.json'),invocation_storage=dict(artifact_root=str(tmp_path),namespace='proof')))
    calls=Invocations(a,e,None)
    def producer(x):
        p=tmp_path/'proof/invocations/2026-09-29/r1/F0.json';assert p.exists()
        assert json.loads(p.read_bytes())['invocation_input']==x
        assert 'F0' not in calls.nodes
        return dict(base_seed_primitives={'p':False})
    calls.call('F0',dict(fixture=True),producer,a.data_ref)
    def consumer(x):
        p=tmp_path/'proof/invocations/2026-09-29/r1/A.json';assert p.exists();assert json.loads(p.read_bytes())['invocation_input']==x
        assert x['seed_facts']=={'p':False} and 'A' not in calls.nodes
        return dict(base_seed_state='FALSE')
    calls.call('A',dict(seed_facts={'p':False}),consumer,a.owners['v4_07'])

def test_callable_cannot_mutate_frozen_argument(tmp_path):
    from workbench_analysis.v4_14_precall_runtime import Invocations
    from workbench_analysis.v4_14_authority import ReplayAuthority
    from workbench_analysis.v4_14_replay_io import ref
    a=ReplayAuthority(ROOT);e=dict(target_trade_date='2026-09-29',target_revision='r1',previous_market_session='2026-09-28',cutoff='2026-09-29T16:00:00+00:00',owner_inputs=dict(consumption_mapping_ref=ref(ROOT,'config/v4_14_precall_consumption_mapping_r18r1r1_v1.json'),invocation_storage=dict(artifact_root=str(tmp_path),namespace='proof')))
    calls=Invocations(a,e,None)
    def malicious(x):x['fixture']=False;return {}
    with pytest.raises(ValueError,match='OWNER_MUTATED'):calls.call('F0',dict(fixture=True),malicious,a.data_ref)
