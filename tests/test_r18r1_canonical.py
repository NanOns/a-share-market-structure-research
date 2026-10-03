import json
from pathlib import Path
from copy import deepcopy
import pytest
from scripts.v4_14_independent_edge_oracle_r18r1 import EdgeOracle,read
ROOT=Path(__file__).resolve().parents[1]

def gate():return json.loads((ROOT/'reports/r18r1b/final_full_dag_gate.json').read_bytes())

def test_canonical_r4_complete_process_trajectory():
    o=EdgeOracle(ROOT);g=gate();assert o.canonical(ROOT,g)
    assert len(g['persisted_e2e']['records'])==22
    for record in g['persisted_e2e']['records']:
        m=read(ROOT,record['publication']);assert len(m['output']['edge_receipts'])==30

@pytest.mark.parametrize('namespace',['full_dag','full_dag_r2','full_dag_r3'])
def test_superseded_attempt_cannot_be_canonical(namespace):
    g=deepcopy(gate());g['candidate_namespace']='reports/v4_14_replay_r18/'+namespace
    with pytest.raises(ValueError):EdgeOracle(ROOT).canonical(ROOT,g)

def test_oracle_never_imports_runtime_expected():
    text=(ROOT/'scripts/v4_14_independent_edge_oracle_r18r1.py').read_text()
    assert 'v4_14_owner_edge_runtime' not in text and 'from workbench_analysis' not in text

def test_real_recheck_keeps_historical_boundary():
    r=json.loads((ROOT/'reports/r18r1c/real_scoped_recheck.json').read_bytes())
    assert r['AS_RECORDED'] is False and r['knowledge_lineage']=='RECONSTRUCTED_CORRECTED'
    assert r['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED'

@pytest.mark.parametrize('mutation',['future_source','after_cutoff','future_membership','current_as_historical','wrong_previous','r2_to_r1','prior_digest','same_pid','producer_not_exited','revision_logical_key','persistent_actionable','duplicate_episode','unknown_false','stale_authority','old_bytes_overwrite','different_output_digest'])
def test_inherited_perturbations_on_current_canonical(mutation,tmp_path):
    from tests.test_r18c_oracle import test_mandatory_perturbations
    o=EdgeOracle(ROOT);g=gate()['persisted_e2e'];m=read(ROOT,g['records'][-1]['publication']);p=read(ROOT,g['records'][-2]['execution']);c=read(ROOT,g['records'][-1]['execution'])
    test_mandatory_perturbations((o,g,m,p,c),mutation,tmp_path)

@pytest.mark.parametrize('producer,consumer',[('C','D0'),('D3_CONTEXT','D3')])
def test_required_producer_receipt_cannot_disappear(producer,consumer):
    o=EdgeOracle(ROOT);m=read(ROOT,gate()['persisted_e2e']['records'][-1]['publication']);m=deepcopy(m)
    rows=m['output']['edge_receipts'];rows.remove(next(r for r in rows if r['producer']==producer and r['consumer']==consumer))
    with pytest.raises(ValueError):o.edges(ROOT,m)
