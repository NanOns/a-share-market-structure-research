import hashlib,types
import pytest
from workbench_analysis.operational_daily_exact_policy_v2 import verify_loaded_versions
from workbench_analysis.operational_component_source_conservation_v2 import ast_conservation

def test_src_alias_cannot_escape_declared_loaded_source_pin(tmp_path,monkeypatch):
    import sys
    path=tmp_path/'alias.py';path.write_text('changed=True',encoding='utf8')
    monkeypatch.setitem(sys.modules,'src.component_pin_probe',types.SimpleNamespace(__file__=str(path)))
    with pytest.raises(ValueError,match='LOADED_ALGORITHM_VERSION_MISMATCH'):verify_loaded_versions([dict(module_path='src/component_pin_probe.py',path='archive.py',sha256=hashlib.sha256(b'original=True').hexdigest())])

def test_script_alias_cannot_escape_declared_source_pin(tmp_path,monkeypatch):
    import sys
    path=tmp_path/'script.py';path.write_text('changed=True',encoding='utf8')
    monkeypatch.setitem(sys.modules,'scripts.component_pin_probe',types.SimpleNamespace(__file__=str(path)))
    with pytest.raises(ValueError,match='LOADED_ALGORITHM_VERSION_MISMATCH'):verify_loaded_versions([dict(module_path='scripts/component_pin_probe.py',path='archive.py',sha256=hashlib.sha256(b'original=True').hexdigest())])

def test_profile_correction_rejects_other_function_change():
    before='def extension_risk(x):\n return None\ndef other(x):\n return x\n'
    after='def extension_risk(x):\n return False\ndef other(x):\n return x+1\n'
    with pytest.raises(ValueError,match='OTHER_NUMERICAL_SOURCE_CHANGED'):ast_conservation(before,after)
