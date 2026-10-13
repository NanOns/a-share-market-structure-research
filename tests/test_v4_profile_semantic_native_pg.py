import copy
import pytest
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.r43_owner_replay import ref
from v4.state_identity import digest
from workbench_db.v4_profile_semantic_corrections_pg_v1 import CONTRACT,prepare,apply

def fixture(root,invalid_state=False):
    def save(name,value):
        path=root/name;atomic_json(root,path,value);return ref(root,path)
    day='2026-10-12'
    def cell(value,evidence,reason):
        result=dict(value=value,evidence=evidence,unknown_reason=reason,parameter_set_id='V4_04_CORE_PROFILE_PARAMETER_SET_V1',source_digest='original',contract_digest='original',input_digest=digest(evidence))
        result['output_digest']=digest(result);return result
    row=dict(security_id='TEST',trade_date=day,states=dict(core_extension_risk=cell('UNKNOWN',dict(bias20_atr=1,amount_ratio20=1,ret5=None),'REQUIRED_INPUT_UNKNOWN'),severe_extension=cell(None,dict(core_extension_risk='UNKNOWN'),'REQUIRED_INPUT_UNKNOWN'),unchanged=cell('KNOWN',{},None)),profile_component_status='PARTIAL',profile_quality='PARTIAL_UNKNOWN')
    row['output_digest']=digest(row);replacement=copy.deepcopy(row)
    replacement['states']['core_extension_risk']=cell('LOW',row['states']['core_extension_risk']['evidence'],None)
    replacement['states']['severe_extension']=cell(False,dict(core_extension_risk='LOW'),None)
    if invalid_state:replacement['states']['unchanged']['value']='ALTERED'
    replacement.update(profile_component_status='READY',profile_quality='COMPLETE');replacement.pop('output_digest');replacement['output_digest']=digest(replacement)
    original=save('profile.json',dict(rows=[row]));source=save('producer.json',dict(contract='fixture'))
    patch=save('patch.json',dict(contract_id=CONTRACT,T0=day,original_profile=original,source=source,rows=[dict(security_id='TEST',original_row_digest=digest(row),replacement=replacement)],publication_ready=False,PIT_ELIGIBLE=False,AS_RECORDED=False))
    candidate=dict(owners={day:dict(profile=original)})
    prepare(root,candidate,{day:patch});return candidate,row,day

def test_actual_pg_patch_read_without_business_patch_file_load(tmp_path,monkeypatch):
    candidate,row,day=fixture(tmp_path)
    from workbench_db import v4_profile_semantic_corrections_pg_v1 as module
    original=module.checked
    def checked(root,binding):
        path=original(root,binding)
        if path.name=='patch.json':
            class MetadataOnly:
                def read_bytes(self):raise AssertionError('BUSINESS_PATCH_JSON_READ_FORBIDDEN')
            return MetadataOnly()
        return path
    monkeypatch.setattr(module,'checked',checked)
    result=apply(tmp_path,candidate,day,[row])
    assert result[0]['states']['core_extension_risk']['value']=='LOW'
    assert result[0]['states']['severe_extension']['value'] is False

def test_changed_original_row_rejected(tmp_path):
    candidate,row,day=fixture(tmp_path);row['profile_quality']='ALTERED'
    with pytest.raises(ValueError,match='ORIGINAL_ROW_CHANGED'):apply(tmp_path,candidate,day,[row])

def test_unrelated_state_correction_rejected(tmp_path):
    candidate,row,day=fixture(tmp_path,invalid_state=True)
    with pytest.raises(ValueError,match='UNRELATED_STATE_CHANGED'):apply(tmp_path,candidate,day,[row])
