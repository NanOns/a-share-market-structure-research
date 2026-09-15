import json
from pathlib import Path
import pytest
from workbench_service.research_bundle_v3_3 import build_bundle,activate_bundle,read_active,validate_bundle,ResearchBundleError
def identity():return {k:k+'-1' for k in ('publication_id','snapshot_id','membership_snapshot_id','research_run_id','parameter_hash','dependency_lock_hash')}|{'trade_date':'2026-09-14'}
def test_complete_bundle_is_idempotent_and_readable(tmp_path):
 a=build_bundle(tmp_path/'bundles',identity(),[{'security_id':'SZ.000001'}],{'factor':'v1'});b=build_bundle(tmp_path/'bundles',identity(),[{'security_id':'SZ.000001'}],{'factor':'v1'});assert a['output_digest']==b['output_digest'] and b['reused'];p=activate_bundle(tmp_path/a['path'],tmp_path/'active.json');assert read_active(tmp_path/'active.json')['output_digest']==p['output_digest']
def test_incomplete_identity_rejected(tmp_path):
 with pytest.raises(ResearchBundleError,match='IDENTITY_INCOMPLETE'):build_bundle(tmp_path,{},[],{})
def test_tamper_rejected(tmp_path):
 b=build_bundle(tmp_path,identity(),[{'x':1}],{});path=tmp_path/b['output_digest'];(path/'results.json').write_text('[{"x":2}]',encoding='utf-8')
 with pytest.raises(ResearchBundleError,match='HASH_MISMATCH'):validate_bundle(path)
def test_failure_before_swap_preserves_previous_pointer(tmp_path):
 a=build_bundle(tmp_path/'b',identity(),[{'x':1}],{});pointer=tmp_path/'active.json';activate_bundle(Path(a['path']),pointer);before=pointer.read_bytes();b=build_bundle(tmp_path/'b',identity()|{'research_run_id':'run-2'},[{'x':2}],{})
 def fail(_):raise RuntimeError('cut')
 with pytest.raises(RuntimeError):activate_bundle(Path(b['path']),pointer,failure_hook=fail)
 assert pointer.read_bytes()==before
