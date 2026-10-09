"""Synthetic protocol fixtures, not provider acceptance evidence."""
import json
import pytest
from workbench_analysis.operational_runtime_acceptance_v2 import prove_no_change,load,CONTRACT
from workbench_analysis.r43_owner_replay import ref

SDK={'package':'baostock','version':'fixture','installed_python_sources_sha256':'fixture'}

class Client:
    def query_rows(self,*args,**kwargs):
        return [],dict(error_code='0',fields=['code','dividOperateDate','foreAdjustFactor','backAdjustFactor'])

def fixture(root):
    proof=prove_no_change(root,'2026-10-09',[{'code':'sh.600000'},{'code':'sz.000001'}],Client(),SDK)
    smoke={'target_date':'2026-10-09','adjustment_factor':{'no_change_proof':proof}}
    receipt=root/'smoke.json';receipt.write_text(json.dumps(dict(status='PASS',runtime=SDK,live_smoke=smoke)))
    manifest=dict(contract_id=CONTRACT,runtime=SDK,live_smoke=smoke,smoke_receipt=ref(root,receipt))
    path=root/'manifest.json';path.write_text(json.dumps(manifest))
    return path,manifest

def test_exact_empty_response_coverage(tmp_path):
    path,manifest=fixture(tmp_path)
    assert load(path,project_root=tmp_path)==manifest

def test_missing_response_cannot_be_attested_by_code_list(tmp_path):
    path,manifest=fixture(tmp_path)
    proof_path=tmp_path/manifest['live_smoke']['adjustment_factor']['no_change_proof']['path']
    proof=json.loads(proof_path.read_text());proof['responses'].pop();proof_path.write_text(json.dumps(proof))
    manifest['live_smoke']['adjustment_factor']['no_change_proof']=ref(tmp_path,proof_path)
    receipt=tmp_path/'smoke.json';receipt.write_text(json.dumps(dict(status='PASS',runtime=SDK,live_smoke=manifest['live_smoke'])))
    manifest['smoke_receipt']=ref(tmp_path,receipt);path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='RESPONSE_COVERAGE'):load(path,project_root=tmp_path)

def test_nonempty_standard_response_blocks_empty_batch(tmp_path):
    class Changed(Client):
        def query_rows(self,*args,**kwargs):return [{'code':'sh.600000'}],{}
    with pytest.raises(ValueError,match='CONTRADICTS'):prove_no_change(tmp_path,'2026-10-09',[{'code':'sh.600000'}],Changed(),SDK)
