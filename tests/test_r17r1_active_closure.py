"""Exact superseded references are rejected independently of byte integrity."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
import pytest
from scripts import validate_r17r1_active_closure as v
ROOT=Path(__file__).resolve().parents[1]
def ref(path):
    raw=(ROOT/path).read_bytes();return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def families():return v.read(v.CLOSURE)['families']
def test_complete_active_package():assert v.validate()['family_count']==14
@pytest.mark.parametrize('path',['config/v4_13_projection_v1.json','config/v4_13_projection_v1_1.json','config/v4_13_dag_edge_registry_v1_1.json','config/v4_13_rotation_structure_enrichment_schema_v1_1.json','config/v4_13_output_schema_v1_1.json','config/v4_13_field_registry_v1_1.json','config/v4_13_machine_vectors_v1_1.json','config/v4_13_accepted_entry_contract_v1.json'])
def test_exact_superseded_current_consumer_rejected(path):
    r=ref(path);v.exact(r)
    with pytest.raises(AssertionError,match='SUPERSEDED_CURRENT_BINDING'):v.walk({'runtime_consumer':r},families())
@pytest.mark.parametrize('role',['supersedes','derived_from','historical_lineage'])
def test_exact_old_contract_allowed_only_as_lineage(role):v.walk({role:ref('config/v4_13_projection_v1.json')},families())
@pytest.mark.parametrize('field',['contract_binding','structure_schema'])
def test_nested_exact_stale_projection_rejected(field):
    with pytest.raises(AssertionError):v.walk({'edges':[{'nested':{field:ref('config/v4_13_projection_v1.json')}}]},families())
def test_lineage_does_not_authorize_adjacent_consumer():
    r=ref('config/v4_13_projection_v1.json')
    with pytest.raises(AssertionError):v.walk({'supersedes':r,'consumer':r},families())
def test_active_member_admitted():v.walk(ref('config/v4_13_projection_v1_2.json'),families())
def test_immutable_head_not_current_authority():
    with pytest.raises(AssertionError):v.walk({'owner':ref('data/v4/V4_13_ACCEPTED_HEAD.json')},families())
