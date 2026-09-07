from pathlib import Path
from common.paths import resolve_tdx_root

def test_configured_tdx_root_has_priority_over_environment(tmp_path,monkeypatch):
    configured=tmp_path/"configured";configured.mkdir();fallback=tmp_path/"environment";fallback.mkdir()
    (tmp_path/"config").mkdir();(tmp_path/"config/paths.yaml").write_text(f'tdx:\n  root: "{configured.as_posix()}"\n',encoding="utf8")
    monkeypatch.setenv("TDX_ROOT",str(fallback))
    assert resolve_tdx_root(tmp_path)==configured.resolve()

def test_environment_is_used_when_config_has_no_root(tmp_path,monkeypatch):
    candidate=tmp_path/"environment";candidate.mkdir();monkeypatch.setenv("TDX_ROOT",str(candidate))
    assert resolve_tdx_root(tmp_path)==candidate.resolve()
