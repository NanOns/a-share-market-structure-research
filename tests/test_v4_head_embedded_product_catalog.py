"""New catalogue identity controls, independent of current production admission."""
from copy import deepcopy
import pytest
from workbench_service.native_product_catalog_v3 import KEY,CONTRACT,load
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.r43_owner_replay import ref
from workbench_db.v4_forward_pg_r1 import canonical,digest

def fixture(root):
    source=root/'raw.json';atomic_json(root,source,dict(rows=[]));source_binding=ref(root,source)
    candidate=dict(owners={'2026-10-12':dict(raw=source_binding)},published_sessions=['2026-10-12'])
    manifest=root/'manifest.json';atomic_json(root,manifest,dict(T0='2026-10-12',fact_token='a'*64,
        history_index=dict(T0='2026-10-12',head_token='a'*64),source_bindings=dict(raw=source_binding)))
    authority=dict(contract_id=CONTRACT,source_owners=candidate['owners'],owner_source_digest=digest(canonical(candidate['owners'])),
        dates={'2026-10-12':ref(root,manifest)},PIT_ELIGIBLE=False,AS_RECORDED=False,historical_PIT_permission=False)
    path=root/'catalog.json';atomic_json(root,path,authority);candidate[KEY]=ref(root,path)
    return candidate,authority,path

def test_catalog_reuses_facts_across_current_head_metadata_changes(tmp_path):
    candidate,authority,_=fixture(tmp_path);candidate['current_head_metadata']='NEXT'
    assert load(tmp_path,candidate)==authority

def test_catalog_rejects_other_owner_source_even_when_ui_date_matches(tmp_path):
    candidate,_,_=fixture(tmp_path);candidate=deepcopy(candidate)
    candidate['owners']['2026-10-12']['raw']['sha256']='b'*64
    with pytest.raises(ValueError,match='CATALOG_SOURCE_MISMATCH'):load(tmp_path,candidate)

def test_catalog_rejects_missing_date_from_complete_head_denominator(tmp_path):
    candidate,authority,path=fixture(tmp_path);authority['dates']={};atomic_json(tmp_path,path,authority);candidate[KEY]=ref(tmp_path,path)
    with pytest.raises(ValueError,match='DATE_DENOMINATOR'):load(tmp_path,candidate)
