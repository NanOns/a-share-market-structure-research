import json
from pathlib import Path
from copy import deepcopy
import pytest
from scripts.v4_14_consumption_oracle_r18r1r1 import ConsumptionOracle,read
ROOT=Path(__file__).resolve().parents[1]

def gate():return json.loads((ROOT/'reports/r18r1r1b/final_full_dag_gate.json').read_bytes())

def test_current_r5_preexecution_process_trajectory():
    g=gate();assert ConsumptionOracle(ROOT).canonical(ROOT,g)
    assert len(g['persisted_e2e']['records'])==22 and len(g['EXPECTED_EDGE_SET'])==30
    for record in g['persisted_e2e']['records']:
        m=read(ROOT,record['publication']);assert len(m['output']['edge_receipts'])==30
        assert len(m['output']['node_records'])==14

@pytest.mark.parametrize('namespace',['full_dag','full_dag_r2','full_dag_r3','full_dag_r4'])
def test_historical_attempt_cannot_be_current(namespace):
    g=deepcopy(gate());g['candidate_namespace']='reports/v4_14_replay_r18/'+namespace
    with pytest.raises(ValueError):ConsumptionOracle(ROOT).canonical(ROOT,g)

@pytest.mark.parametrize('mutation',['future_source','after_cutoff','future_membership','current_as_historical','wrong_previous','r2_to_r1','prior_digest','same_pid','producer_not_exited','revision_logical_key','persistent_actionable','duplicate_episode','unknown_false','stale_authority','old_bytes_overwrite','different_output_digest'])
def test_existing_perturbations_on_current_r5(mutation,tmp_path):
    from tests.test_r18c_oracle import test_mandatory_perturbations
    o=ConsumptionOracle(ROOT);g=gate()['persisted_e2e'];m=read(ROOT,g['records'][-1]['publication']);p=read(ROOT,g['records'][-2]['execution']);c=read(ROOT,g['records'][-1]['execution'])
    test_mandatory_perturbations((o,g,m,p,c),mutation,tmp_path)

def test_current_oracle_expected_has_no_runtime_dependency():
    text=(ROOT/'scripts/v4_14_consumption_oracle_r18r1r1.py').read_text()
    assert 'v4_14_precall_runtime' not in text and 'evaluate_case(' not in text

def test_real_evidence_boundary_is_unchanged():
    r=json.loads((ROOT/'reports/r18r1r1c/real_scoped_recheck.json').read_bytes())
    assert r['evidence_class']=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED'
    assert r['AS_RECORDED'] is False and r['knowledge_lineage']=='RECONSTRUCTED_CORRECTED'
    assert r['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED'
