from copy import deepcopy
from pathlib import Path
import json
import pytest
from scripts import validate_r17b_promotion as v
from workbench_analysis.v4_13_accepted_contract_package import AcceptedContracts
ROOT=Path(__file__).resolve().parents[1]
def test_independent_p01_p15_promotion_gate():
    result=v.validate();assert result['status']=='PASS' and len(result['checks'])==15 and all(result['checks'].values())
@pytest.mark.parametrize('field,value,check',[
 ('external_authority',{'path':'missing','sha256':'0'*64},'P01_EXTERNAL_AUDIT_EXACT'),
 ('audited_sealed_head','wrong','P02_AUDITED_SEALED_HEAD_EXACT'),
 ('tested_runtime_source','wrong','P03_TESTED_SOURCE_EXACT'),
 ('runtime_source_bindings',[],'P03_TESTED_SOURCE_EXACT'),
 ('candidate',{'path':'reports/v4_13_runtime_r16/real/2026-09-30/r5/manifest.json','sha256':'0'*64},'P04_R6_MANIFEST_EXACT'),
 ('artifact_refs',[],'P05_R6_ARTIFACT_REFS_EXACT'),
 ('contract_refs',[],'P06_CONTRACT_PACKAGE_EXACT'),
 ('contract_digest','wrong','P06_CONTRACT_PACKAGE_EXACT'),
 ('formal_entry_contract',{'path':'missing','sha256':'0'*64},'P06_CONTRACT_PACKAGE_EXACT'),
 ('r17a_gate',{'path':'missing','sha256':'0'*64},'P08_R17A_GATE_PASS'),
 ('global_head_parent_archive',{'path':'data/v4/V4_STAGE_ACCEPTED_HEAD.json','sha256':'0'*64},'P09_PARENT_STAGE_ARCHIVE_EXACT'),
 ('global_head_parent',{},'P09_PARENT_STAGE_ARCHIVE_EXACT'),
 ('protected_head_bindings',{},'P11_DATA_HEAD_BYTE_IDENTICAL'),
 ('production',True,'P13_NO_PRODUCTION_SHADOW_FOCUS'),
 ('shadow',True,'P13_NO_PRODUCTION_SHADOW_FOCUS'),
 ('focus',True,'P13_NO_PRODUCTION_SHADOW_FOCUS'),
 ('global_mandatory_adoption',True,'P13_NO_PRODUCTION_SHADOW_FOCUS'),
 ('capabilities',{'V4_13_REAL_SIGNAL_CAPABILITY':'READY'},'P14_DEGRADATION_NOT_OVERCLAIMED'),
 ('ALGORITHM_STATE_REPLAY_PASS','PASS','P15_V4_14_NOT_ACCEPTED')])
def test_major_authority_mutations_rejected_at_relevant_gate(field,value,check):
    h=deepcopy(v.read(v.HEAD));h[field]=value;r=v.validate(h)
    assert r['status']=='FAIL' and r['checks'][check] is False
@pytest.mark.parametrize('mutation',['head_sha','stage_range','prior_scope','permissions'])
def test_new_stage_authority_mutation_rejected(monkeypatch,mutation):
    stage=deepcopy(v.read(v.STAGE));original=v.read
    if mutation=='head_sha':stage['v4_13_binding']['sha256']='0'*64
    if mutation=='stage_range':stage['accepted_stage_range']='V4_00_TO_V4_12_ACCEPTED'
    if mutation=='prior_scope':stage['v4_12_status']='READY'
    if mutation=='permissions':stage['production_permission']=True
    monkeypatch.setattr(v,'read',lambda p:stage if p==v.STAGE else original(p))
    r=v.validate();assert r['status']=='FAIL'
    assert r['checks']['P13_NO_PRODUCTION_SHADOW_FOCUS' if mutation=='permissions' else 'P10_NEW_STAGE_PREDECESSOR_EXACT'] is False
def test_formal_reader_does_not_consult_informal_receipt(monkeypatch):
    original=Path.read_bytes
    def read(path):
        if path.name=='contract_amendment_decision.json':raise AssertionError('INFORMAL_RECEIPT_MUST_NOT_BE_AUTHORITY')
        return original(path)
    monkeypatch.setattr(Path,'read_bytes',read)
    pkg=AcceptedContracts(ROOT)
    assert pkg.config['projection']['version']=='1.2.0' and pkg.digest==v.read(v.HEAD)['contract_digest']
    assert pkg.refs==v.read(v.MANIFEST)['contract_refs']
def test_formal_reader_missing_or_wrong_head_fails_closed(tmp_path):
    (tmp_path/'data/v4').mkdir(parents=True)
    (tmp_path/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').write_text(json.dumps(dict(accepted_stage_range='V4_00_TO_V4_13_ACCEPTED',v4_13_binding=dict(path=v.HEAD,sha256='0'*64))),encoding='utf8')
    with pytest.raises((ValueError,FileNotFoundError)):AcceptedContracts(tmp_path)
def test_formal_reader_resolves_stage_without_changing_frozen_contract_or_binder():
    pkg=AcceptedContracts(ROOT)
    receipt=pkg.binding_resolution_receipt
    assert receipt['original_namespace']==pkg.frozen_config['membership_consumer_route']['stage_binding']
    assert receipt['original_namespace']['path']=='data/v4/V4_STAGE_ACCEPTED_HEAD.json'
    assert receipt['archive']['sha256']==receipt['original_namespace']['sha256']
    from workbench_analysis.v4_13_input_binder import AcceptedInputBinder
    binder=AcceptedInputBinder(pkg,'2026-09-30','2026-10-03T00:00:00+08:00')
    assert binder.membership_complete and len(binder.memberships)==50162 and all(x==0 for x in binder.counters.values())
@pytest.mark.parametrize('mutation',['capability','r5','package','audit','entry'])
def test_self_consistent_wrong_formal_head_is_rejected(tmp_path,mutation):
    h=deepcopy(v.read(v.HEAD));s=deepcopy(v.read(v.STAGE))
    for p in [h['external_authority']['path'],h['r17a_gate']['path'],h['candidate']['path'],h['formal_entry_contract']['path']]:
        t=tmp_path/p;t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes((ROOT/p).read_bytes())
    if mutation=='capability':h['capabilities']['V4_13_REAL_SIGNAL_CAPABILITY']='READY'
    if mutation=='r5':h['candidate']['sha256']='0'*64
    if mutation=='package':h['contract_refs']=[]
    if mutation=='audit':h['external_authority']['sha256']='0'*64
    if mutation=='entry':h['formal_entry_contract']['path']='missing'
    from workbench_analysis.v4_13_io import canonical,file_ref
    (tmp_path/'data/v4').mkdir(parents=True,exist_ok=True)
    (tmp_path/v.HEAD).write_bytes(canonical(h));s['v4_13_binding']=file_ref(tmp_path,v.HEAD)
    (tmp_path/v.STAGE).write_bytes(canonical(s))
    with pytest.raises((ValueError,FileNotFoundError)):AcceptedContracts(tmp_path)
