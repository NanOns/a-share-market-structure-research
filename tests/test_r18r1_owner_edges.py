"""Owner-edge closure and adversarial oracle tests from frozen expectations."""
import json
from pathlib import Path
from copy import deepcopy
import pytest
from scripts.v4_14_independent_edge_oracle_r18r1 import EdgeOracle,read,checksum
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def sample():
    gate=json.loads((ROOT/'reports/r18r1a/completion_gate.json').read_bytes());return EdgeOracle(ROOT),read(ROOT,gate['proof'])

def test_all_frozen_edges_accounted_exactly_once(sample):
    oracle,m=sample;assert oracle.manifest(ROOT,m)
    assert len(oracle.expected_owner_edges)==24 and len(oracle.expected_replay_edges)==6
    assert len(m['output']['edge_receipts'])==30
    assert m['output']['edge_completeness']['missing_edges']==m['output']['edge_completeness']['unexpected_edges']==[]

def test_actual_owner_calls_and_frozen_producer_inputs(sample):
    oracle,m=sample;n=m['output']['node_records']
    assert n['B0']['output']['model_contract_id']=='V4_08_SECTOR_PREWATCH_B0_V2'
    assert n['B1']['output']['output_state']=='UNKNOWN'
    assert n['B2']['output']['confirmed_raw']=='UNKNOWN'
    assert n['C']['input']['base_seed_state']==n['A']['output']['base_seed_state']
    assert n['D0']['input']['projection']['replay_prewatch_lineage']['producer_output_digest']==checksum(n['C']['output'])

@pytest.mark.parametrize('mutation',['delete_B0_edge','delete_B2_edge','delete_membership_context_edge','delete_D1_T_MINUS_1_edge','replace_B0_output_with_literal','replace_C_to_D0_lineage_with_unbound_fixture','wrong_edge_time_role','wrong_edge_owner_head','duplicate_edge_receipt','unexpected_feedback_edge'])
def test_edge_perturbations_rejected(sample,mutation):
    oracle,original=sample;m=deepcopy(original);out=m['output'];rows=out['edge_receipts'];nodes=out['node_records']
    predicate={
        'delete_B0_edge':lambda r:r['producer']=='B0',
        'delete_B2_edge':lambda r:r['consumer']=='B2',
        'delete_membership_context_edge':lambda r:r['producer']=='MEMBERSHIP',
        'delete_D1_T_MINUS_1_edge':lambda r:r['producer']==r['consumer']=='D1' and r['time_role']=='T_MINUS_1'}
    if mutation in predicate:rows.remove(next(r for r in rows if predicate[mutation](r)))
    elif mutation=='replace_B0_output_with_literal':
        # Also repair declared hashes and consumer echoes: owner-output semantics
        # must reject this, rather than only detecting an unrepaired checksum.
        nodes['B0']['output']=True
        for name in ['B1','B2']:nodes[name]['input']['b0']=True
        nodes['D3_CONTEXT']['input']['b0']=True
        for r in rows:
            if r['producer']=='B0':nodes[r['consumer']]['edge_inputs'][r['edge_id']]=True
            for reference,field in [('input_ref','input_digest'),('output_ref','output_digest'),('consumer_input_ref','consumer_input_digest')]:r[field]=checksum(oracle.resolve(ROOT,out,r[reference]))
    elif mutation=='replace_C_to_D0_lineage_with_unbound_fixture':nodes['D0']['input']['projection']['replay_prewatch_lineage']['fixture_package_ref']['sha256']='0'*64
    elif mutation=='wrong_edge_time_role':rows[0]['time_role']='T_MINUS_1'
    elif mutation=='wrong_edge_owner_head':rows[0]['owner_head_ref']=rows[-1]['owner_head_ref']
    elif mutation=='duplicate_edge_receipt':rows.append(deepcopy(rows[0]))
    elif mutation=='unexpected_feedback_edge':
        extra=deepcopy(rows[0]);extra.update(producer='D3',consumer='D0',field='feedback',edge_id=checksum(['D3','D0','feedback','T']));rows.append(extra)
    with pytest.raises(ValueError):oracle.edges(ROOT,m)

def test_emitted_expected_list_cannot_define_oracle_expected(sample):
    oracle,m=sample;m=deepcopy(m);m['output']['edge_receipts'].pop();m['output']['edge_completeness']['expected_active_edges']=[r['edge_id'] for r in m['output']['edge_receipts']]
    with pytest.raises(ValueError):oracle.edges(ROOT,m)
