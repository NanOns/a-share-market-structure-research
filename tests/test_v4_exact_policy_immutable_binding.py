"""New immutable policy path controls; no replay of existing gate suites."""
import pytest
from workbench_analysis.r43_owner_replay import ref
from workbench_analysis.operational_daily_exact_policy_v2 import PATH,immutable_policy_binding

def _configure_tdx(root):
    tdx=root/'readonly-tdx';(root/'config').mkdir(exist_ok=True)
    (root/'config/paths.yaml').write_text(f'tdx:\n  source_root: "{tdx.as_posix()}"\n',encoding='utf-8')

def test_policy_binding_retains_exact_bytes_across_canonical_update(tmp_path):
    _configure_tdx(tmp_path)
    p=tmp_path/PATH;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'{"version":1}\n')
    first=immutable_policy_binding(tmp_path)
    p.write_bytes(b'{"version":2}\n')
    assert (tmp_path/first['path']).read_bytes()==b'{"version":1}\n'
    assert immutable_policy_binding(tmp_path,first)==first
    assert immutable_policy_binding(tmp_path)!=first

def test_policy_binding_rejects_other_in_root_path(tmp_path):
    _configure_tdx(tmp_path)
    p=tmp_path/'other.json';p.write_bytes(b'{}\n')
    with pytest.raises(ValueError,match='POLICY_PATH_REQUIRED'):immutable_policy_binding(tmp_path,ref(tmp_path,p))
