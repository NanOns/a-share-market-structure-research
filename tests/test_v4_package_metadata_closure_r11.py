import json,hashlib
import pytest
from scripts.build_windows_package_v1 import exact_metadata_resources

def bound(root,name,raw):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))

def test_signed_small_closure_skips_bulk_without_loading_it(tmp_path):
    code=bound(tmp_path,'archive/code.py',b'print(1)')
    bulk=bound(tmp_path,'data/bulk.gz',b'bulk')
    child=bound(tmp_path,'data/gate.json',json.dumps({'gates':{}}).encode())
    policy={'admission_evidence':child,'accepted_algorithm_bindings':[code,bulk]};top=bound(tmp_path,'data/POLICY.json',json.dumps(policy).encode())
    files,skipped=exact_metadata_resources(tmp_path,top,policy)
    assert {p.name for p in files}=={'POLICY.json','gate.json','code.py'}
    assert skipped==[dict(path='data/bulk.gz',reason='BULK_WORKSPACE_INPUT')]


def test_closure_rejects_relative_escape(tmp_path):
    policy={'accepted_algorithm_bindings':[dict(path='../outside.json',sha256='a'*64)]}
    top=bound(tmp_path,'POLICY.json',json.dumps(policy).encode())
    with pytest.raises(ValueError,match='PATH_ESCAPE'):exact_metadata_resources(tmp_path,top,policy)


def test_closure_rejects_modified_signed_small_metadata(tmp_path):
    child=bound(tmp_path,'gate.json',b'{}');(tmp_path/'gate.json').write_bytes(b'{"changed":1}')
    policy={'admission_evidence':child};top=bound(tmp_path,'POLICY.json',json.dumps(policy).encode())
    with pytest.raises(ValueError):exact_metadata_resources(tmp_path,top,policy)
