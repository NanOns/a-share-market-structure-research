from copy import deepcopy
import pytest
from scripts.repair_v4_13_r1_1 import read,ref,introduced_lineage
from scripts.validate_v4_13_r1_1 import validate_lineage
@pytest.mark.parametrize('name,predecessor',[('sector_context_state_schema','output_schema'),('rotation_structure_enrichment_schema','field_registry')])
def test_cross_family_first_introduction_rejected(name,predecessor):
    obj=read('config/v4_13_'+name+'_v1_1.json');obj['supersedes']=ref('config/v4_13_'+predecessor+'_v1.json')
    with pytest.raises(AssertionError):validate_lineage(obj)
def test_same_family_upgrade_accepted():
    assert validate_lineage(read('config/v4_13_field_registry_v1_1.json'))
@pytest.mark.parametrize('name,sources',[('sector_context_state_schema',['output_schema','field_registry']),('rotation_structure_enrichment_schema',['field_registry','dag_edge_registry'])])
def test_new_introduced_contract_and_generator_determinism(name,sources):
    obj=read('config/v4_13_'+name+'_v1_1.json');assert validate_lineage(obj)
    old=deepcopy(obj);old['supersedes']=ref('config/v4_13_'+sources[0]+'_v1.json');old.pop('introduced_in');old.pop('derived_from')
    paths=['config/v4_13_'+s+'_v1.json' for s in sources]
    assert introduced_lineage(old,paths)==obj==introduced_lineage(old,paths)
def test_exact_predecessor_hash_but_wrong_identity_rejected():
    obj=read('config/v4_13_field_registry_v1_1.json');obj['supersedes']=ref('config/v4_13_output_schema_v1.json')
    with pytest.raises(AssertionError,match='CONTRACT_ID_MISMATCH'):validate_lineage(obj)
def test_nonincreasing_version_rejected():
    obj=read('config/v4_13_field_registry_v1_1.json');obj['version']='1.0.0'
    with pytest.raises(AssertionError,match='VERSION_MUST_INCREASE'):validate_lineage(obj)
def test_corrupt_hash_rejected():
    obj=read('config/v4_13_field_registry_v1_1.json');obj['supersedes']['sha256']='0'*64
    with pytest.raises(AssertionError):validate_lineage(obj)
def test_missing_introduction_rejected():
    obj=read('config/v4_13_sector_context_state_schema_v1_1.json');obj.pop('introduced_in')
    with pytest.raises(AssertionError):validate_lineage(obj)
