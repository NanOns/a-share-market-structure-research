"""Current Replay bindings reject exact predecessor contracts recursively."""
from copy import deepcopy
import pytest
from scripts import validate_r17r1_refreeze as v
from scripts import validate_r17r1_active_closure as closure
import hashlib
def ref(path):
    raw=(v.ROOT/path).read_bytes();return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
@pytest.mark.parametrize('path',['config/v4_13_projection_v1.json','config/v4_13_dag_edge_registry_v1_1.json','config/v4_13_rotation_structure_enrichment_schema_v1_1.json','data/v4/V4_13_ACCEPTED_HEAD.json']+[f'config/v4_14_{n}_v1.json' for n in ['replay_gate_b_contract','replay_case_registry','temporal_non_edge_registry','quality_degradation','machine_vectors']])
def test_exact_stale_ref_rejected_in_current_replay_consumer(path):
    bundle=deepcopy(v.load());r=ref(path);v.exact(r)
    bundle[v.NAMES[0]]['runtime_consumer']={'nested':[r]}
    with pytest.raises(AssertionError):v.validate_bundle(bundle)
def test_original_contracts_and_literal_vectors_preserved():
    for name in v.NAMES:
        obj=v.load()[name];old=closure.read(obj['supersedes']['path'])
        assert obj['contract_id']==old['contract_id'] and obj['version']=='1.1.0'
    assert v.load()[v.NAMES[4]]['vectors']==closure.read('config/v4_14_machine_vectors_v1.json')['vectors']
    v.preserve_authority_only(v.load())
def test_whole_contract_semantic_change_is_rejected():
    bundle=deepcopy(v.load());bundle[v.NAMES[0]]['runtime_completion_requirements'].append('UNAUTHORIZED_NEW_BEHAVIOR')
    with pytest.raises(AssertionError,match='REPLAY_SEMANTICS_CHANGED'):v.preserve_authority_only(bundle)
def test_lineage_is_not_current_runtime_authority():
    bundle=deepcopy(v.load());r=ref('config/v4_13_dag_edge_registry_v1_1.json')
    bundle[v.NAMES[0]]['historical_lineage']={'old_dag':r}
    v.validate_bundle(bundle)
    bundle[v.NAMES[0]]['current_owner']=r
    with pytest.raises(AssertionError):v.validate_bundle(bundle)
